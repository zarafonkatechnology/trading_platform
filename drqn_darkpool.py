"""
Deep Recurrent Q-Network (DRQN) for Dark Pool Agents
- LSTM memory for temporal pattern recognition
- Infer hidden liquidity from price/volume sequences
- Shared architecture for Agents P, Q, G
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import json
import os


class LSTMMemory(nn.Module):
    """
    LSTM-based Q-network for dark pool inference.
    Maintains internal state across time steps.
    """
    
    def __init__(self, input_dim: int = 12, hidden_dim: int = 128, 
                 output_dim: int = 3, num_layers: int = 2):
        """
        Args:
            input_dim: Number of input features
            hidden_dim: LSTM hidden dimension
            output_dim: Number of actions (BUY/SELL/HOLD)
            num_layers: Number of LSTM layers
        """
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0
        )
        
        # Feature attention mechanism
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
        
        # Output layers
        self.fc1 = nn.Linear(hidden_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, output_dim)
        
        self.dropout = nn.Dropout(0.2)
        self.relu = nn.ReLU()
    
    def forward(self, x, hidden=None):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor (batch, seq_len, input_dim)
            hidden: Previous hidden state (num_layers, batch, hidden_dim)
        
        Returns:
            q_values: Q-values for each action
            hidden: New hidden state
        """
        # LSTM forward
        lstm_out, hidden = self.lstm(x, hidden)
        
        # Apply attention to focus on important time steps
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Take last output
        last_out = attn_out[:, -1, :]
        
        # Fully connected layers
        x = self.relu(self.fc1(last_out))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        q_values = self.fc3(x)
        
        return q_values, hidden
    
    def init_hidden(self, batch_size: int = 1, device: str = 'cpu'):
        """Initialize hidden state with zeros"""
        return (torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(device),
                torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(device))


class DRQNAgent:
    """
    Deep Recurrent Q-Network Agent for Dark Pool Trading
    """
    
    def __init__(self, name: str, learning_rate: float = 0.001, 
                 gamma: float = 0.95, epsilon: float = 0.1,
                 memory_size: int = 10000, batch_size: int = 32,
                 sequence_length: int = 10):
        
        self.name = name
        self.gamma = gamma
        self.epsilon = epsilon
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize networks
        self.policy_net = LSTMMemory().to(self.device)
        self.target_net = LSTMMemory().to(self.device)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # Experience replay buffer
        self.memory = deque(maxlen=memory_size)
        
        # Sequence buffer for current episode
        self.state_buffer = deque(maxlen=sequence_length)
        self.hidden_state = None
        
        # Training metrics
        self.total_steps = 0
        self.episode_rewards = []
        
        # Load existing model if available
        self._load_model()
        
        # Copy target network
        self.update_target_network()
        
        print(f"🤖 {self.name} DRQN initialized (device: {self.device})")
    
    def update_target_network(self):
        """Copy policy network weights to target network"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def _extract_features(self, observation: Dict) -> np.ndarray:
        """
        Extract features from market observation for dark pool inference.
        
        Features:
        1. Price normalized
        2. Volume ratio
        3. Bid-ask spread
        4. Dark pool volume (estimated)
        5. Volume profile at level
        6. Price acceleration
        7. Order book imbalance
        8. Trade size distribution
        9. Time since last large trade
        10. Volatility
        11. Supply/demand distance
        12. Manipulation score
        """
        features = np.array([
            observation.get('price', 1.0950) / 1000,           # Normalized price
            min(2.0, observation.get('volume_ratio', 1.0)),    # Volume ratio
            observation.get('spread', 0.0001) * 10000,         # Spread in pips
            min(1.0, observation.get('dark_volume_ratio', 0) / 100),  # Dark pool ratio
            observation.get('volume_profile', 0.5),            # Volume at level
            observation.get('price_acceleration', 0),          # Price momentum
            observation.get('order_imbalance', 0),             # Order book delta
            min(1.0, observation.get('trade_size', 0) / 1000000),  # Trade size ($M)
            observation.get('time_since_last_trade', 0) / 3600,     # Hours since
            observation.get('volatility', 0.01) * 100,         # Volatility %
            observation.get('supply_distance', 0.01),          # Distance to supply
            observation.get('manipulation_score', 0.5)         # M score
        ], dtype=np.float32)
        
        return features
    
    def get_state_tensor(self, observation_sequence: List[np.ndarray]) -> torch.Tensor:
        """Convert observation sequence to tensor"""
        seq_array = np.array(observation_sequence)
        return torch.tensor(seq_array, dtype=torch.float32).unsqueeze(0).to(self.device)
    
    def act(self, observation: Dict, training: bool = True) -> Tuple[int, float]:
        """
        Select action based on current observation sequence.
        
        Returns:
            action: 0=BUY, 1=SELL, 2=HOLD
            confidence: Agent's confidence in this action
        """
        # Update sequence buffer
        features = self._extract_features(observation)
        self.state_buffer.append(features)
        
        # Need enough history for inference
        if len(self.state_buffer) < self.sequence_length:
            # Random action during warm-up
            action = random.randint(0, 2)
            confidence = 0.5
        else:
            # Get state tensor
            state_seq = list(self.state_buffer)[-self.sequence_length:]
            state_tensor = self.get_state_tensor(state_seq)
            
            # Forward pass
            with torch.no_grad():
                q_values, self.hidden_state = self.policy_net(state_tensor, self.hidden_state)
                q_values = q_values.cpu().numpy()[0]
            
            # Epsilon-greedy action selection
            if training and random.random() < self.epsilon:
                action = random.randint(0, 2)
            else:
                action = np.argmax(q_values)
            
            # Calculate confidence from Q-value spread
            q_probs = np.exp(q_values) / np.sum(np.exp(q_values))
            confidence = q_probs[action]
        
        return action, confidence
    
    def remember(self, observation: Dict, action: int, reward: float, 
                 next_observation: Dict, done: bool):
        """Store experience in replay buffer"""
        features = self._extract_features(observation)
        next_features = self._extract_features(next_observation)
        
        self.memory.append((features, action, reward, next_features, done))
    
    def replay(self) -> float:
        """Train on batch of experiences"""
        if len(self.memory) < self.batch_size:
            return 0.0
        
        # Sample batch
        batch = random.sample(self.memory, self.batch_size)
        
        # Prepare sequences
        states = []
        actions = []
        rewards = []
        next_states = []
        dones = []
        
        for features, action, reward, next_features, done in batch:
            states.append(features)
            actions.append(action)
            rewards.append(reward)
            next_states.append(next_features)
            dones.append(done)
        
        # Create sequences (using last N steps - simplified, use proper sequence memory)
        states_t = torch.tensor(np.array(states), dtype=torch.float32).unsqueeze(1).to(self.device)
        next_states_t = torch.tensor(np.array(next_states), dtype=torch.float32).unsqueeze(1).to(self.device)
        actions_t = torch.tensor(actions, dtype=torch.long).unsqueeze(1).to(self.device)
        rewards_t = torch.tensor(rewards, dtype=torch.float32).to(self.device)
        dones_t = torch.tensor(dones, dtype=torch.float32).to(self.device)
        
        # Compute current Q values
        q_values, _ = self.policy_net(states_t)
        current_q = q_values.gather(1, actions_t).squeeze()
        
        # Compute target Q values
        with torch.no_grad():
            next_q_values, _ = self.target_net(next_states_t)
            max_next_q = next_q_values.max(1)[0]
            target_q = rewards_t + self.gamma * max_next_q * (1 - dones_t)
        
        # Compute loss
        loss = nn.MSELoss()(current_q, target_q)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=1.0)
        self.optimizer.step()
        
        self.total_steps += 1
        
        # Periodically update target network
        if self.total_steps % 100 == 0:
            self.update_target_network()
        
        return loss.item()
    
    def reset_episode(self):
        """Reset hidden state for new episode"""
        self.hidden_state = None
        self.state_buffer.clear()
    
    def record_episode_reward(self, total_reward: float):
        """Record episode reward for tracking"""
        self.episode_rewards.append(total_reward)
        if len(self.episode_rewards) > 100:
            self.episode_rewards = self.episode_rewards[-100:]
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            'name': self.name,
            'total_steps': self.total_steps,
            'epsilon': self.epsilon,
            'memory_size': len(self.memory),
            'avg_reward_last_100': np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0,
            'device': str(self.device)
        }
    
    def _load_model(self):
        """Load saved model if exists"""
        model_path = f"drqn_{self.name.lower()}.pt"
        if os.path.exists(model_path):
            try:
                checkpoint = torch.load(model_path, map_location=self.device)
                self.policy_net.load_state_dict(checkpoint['policy_net'])
                self.update_target_network()
                self.total_steps = checkpoint.get('total_steps', 0)
                print(f"✅ Loaded DRQN model for {self.name}")
            except Exception as e:
                print(f"⚠️ Failed to load model for {self.name}: {e}")
    
    def save_model(self):
        """Save model to disk"""
        model_path = f"drqn_{self.name.lower()}.pt"
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'total_steps': self.total_steps,
            'timestamp': datetime.now().isoformat()
        }, model_path)
        print(f"💾 Saved DRQN model for {self.name}")


# ============================================================
# Dark Pool Agent Wrappers
# ============================================================

class DarkPoolAgentWrapper:
    """
    Wrapper for Agents P, Q, G to use DRQN
    """
    
    def __init__(self, agent_name: str):
        self.name = agent_name
        self.drqn = DRQNAgent(agent_name)
        self.use_drqn = True
        self.last_action = 2  # HOLD
        self.last_confidence = 0.5
    
    def analyze(self, observation: Dict) -> Dict:
        """
        Analyze market using DRQN inference.
        
        Returns:
            Dictionary with vote, confidence, and reasoning
        """
        if not self.use_drqn:
            return self._fallback_analysis(observation)
        
        # Get action from DRQN
        action_idx, confidence = self.drqn.act(observation, training=False)
        
        actions = ['BUY', 'SELL', 'HOLD']
        vote = actions[action_idx]
        
        self.last_action = action_idx
        self.last_confidence = confidence
        
        # Build reasoning
        dark_ratio = observation.get('dark_volume_ratio', 0)
        if dark_ratio > 40:
            pattern = "high dark pool activity"
        elif dark_ratio > 20:
            pattern = "moderate dark pool activity"
        else:
            pattern = "low dark pool activity"
        
        reasoning = f"DRQN inference: {vote} with {confidence:.0%} confidence ({pattern})"
        
        return {
            'agent': self.name,
            'vote': vote,
            'confidence': confidence * 100,
            'reasoning': reasoning,
            'drqn_used': True,
            'dark_volume_ratio': dark_ratio
        }
    
    def _fallback_analysis(self, observation: Dict) -> Dict:
        """Fallback rule-based analysis when DRQN disabled"""
        dark_ratio = observation.get('dark_volume_ratio', 0)
        volume_ratio = observation.get('volume_ratio', 1.0)
        
        if dark_ratio > 40 and volume_ratio > 1.2:
            vote = 'BUY'
            confidence = 70
            reasoning = "High dark pool volume with volume surge - whale accumulation"
        elif dark_ratio > 40:
            vote = 'HOLD'
            confidence = 50
            reasoning = "High dark pool activity but awaiting confirmation"
        else:
            vote = 'HOLD'
            confidence = 40
            reasoning = "Normal dark pool activity"
        
        return {
            'agent': self.name,
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'drqn_used': False
        }
    
    def record_outcome(self, reward: float):
        """Record trade outcome for training"""
        # This would be called after trade closes
        # Requires storing the observation sequence
        pass
    
    def train(self):
        """Train the DRQN model"""
        loss = self.drqn.replay()
        return loss


# ============================================================
# Dark Pool Team Coordinator
# ============================================================

class DarkPoolTeam:
    """
    Coordinates Agents P, Q, G (the dark pool team)
    """
    
    def __init__(self):
        self.agents = {
            'Agent_P': DarkPoolAgentWrapper('Agent_P'),  # Whisper Analyst
            'Agent_Q': DarkPoolAgentWrapper('Agent_Q'),  # Dark Pool Whale
            'Agent_G': DarkPoolAgentWrapper('Agent_G')   # Whale Tracker
        }
        self.consensus_threshold = 0.6
    
    def analyze(self, observation: Dict) -> Dict:
        """
        Get analysis from all dark pool agents and compute consensus.
        """
        results = {}
        votes = []
        confidences = []
        
        for name, agent in self.agents.items():
            result = agent.analyze(observation)
            results[name] = result
            votes.append(result['vote'])
            confidences.append(result['confidence'])
        
        # Calculate consensus
        buy = votes.count('BUY')
        sell = votes.count('SELL')
        hold = votes.count('HOLD')
        
        if buy > sell and buy > hold:
            consensus = 'BUY'
            confidence = np.mean([c for c, v in zip(confidences, votes) if v == 'BUY'])
        elif sell > buy and sell > hold:
            consensus = 'SELL'
            confidence = np.mean([c for c, v in zip(confidences, votes) if v == 'SELL'])
        else:
            consensus = 'HOLD'
            confidence = np.mean([c for c, v in zip(confidences, votes) if v == 'HOLD'])
        
        # Check if consensus is strong enough
        is_strong = (buy + sell) / len(self.agents) > self.consensus_threshold
        
        return {
            'dark_pool_consensus': consensus,
            'confidence': round(confidence, 1),
            'is_strong': is_strong,
            'individual_votes': results,
            'vote_counts': {'BUY': buy, 'SELL': sell, 'HOLD': hold},
            'reasoning': f"Dark pool team: {buy}B, {sell}S, {hold}H → {consensus}"
        }
    
    def train_all(self):
        """Train all dark pool agents"""
        losses = {}
        for name, agent in self.agents.items():
            loss = agent.train()
            losses[name] = loss
        return losses
    
    def save_models(self):
        """Save all DRQN models"""
        for agent in self.agents.values():
            agent.drqn.save_model()
    
    def get_stats(self) -> Dict:
        """Get statistics for all agents"""
        return {name: agent.drqn.get_stats() for name, agent in self.agents.items()}


# ============================================================
# Training Environment (Mock)
# ============================================================

class DarkPoolEnvironment:
    """
    Simulated environment for training DRQN agents
    """
    
    def __init__(self):
        self.step = 0
        self.max_steps = 100
        self.dark_pool_active = False
        self.whale_detected = False
    
    def reset(self) -> Dict:
        """Reset environment"""
        self.step = 0
        self.dark_pool_active = random.random() > 0.7
        self.whale_detected = random.random() > 0.8
        return self._get_observation()
    
    def _get_observation(self) -> Dict:
        """Get current observation"""
        return {
            'price': 100 + random.gauss(0, 1),
            'volume_ratio': random.uniform(0.5, 2.5),
            'spread': random.uniform(0.0001, 0.0005),
            'dark_volume_ratio': random.uniform(0, 80) if self.dark_pool_active else random.uniform(0, 20),
            'volume_profile': random.uniform(0, 1),
            'price_acceleration': random.gauss(0, 0.5),
            'order_imbalance': random.gauss(0, 0.3),
            'trade_size': random.uniform(10000, 5000000),
            'time_since_last_trade': random.uniform(0, 7200),
            'volatility': random.uniform(0.005, 0.02),
            'supply_distance': random.uniform(0.001, 0.01),
            'manipulation_score': random.uniform(0, 1)
        }
    
    def step(self, action: int) -> Tuple[Dict, float, bool]:
        """
        Take action and get reward.
        
        Reward structure:
        - Correctly identifying whale activity: +10
        - Missing whale activity: -5
        - False alarm: -3
        """
        self.step += 1
        
        # Calculate reward based on action and hidden state
        reward = 0
        
        if self.whale_detected:
            if action == 0:  # BUY (follow whale)
                reward = 10
            elif action == 1:  # SELL (opposite)
                reward = -5
            else:  # HOLD (missed)
                reward = -2
        else:
            if action == 0 or action == 1:  # False alarm
                reward = -3
            else:
                reward = 1
        
        done = self.step >= self.max_steps
        
        # Update hidden state
        self.dark_pool_active = random.random() > 0.7
        self.whale_detected = random.random() > 0.8
        
        next_obs = self._get_observation()
        
        return next_obs, reward, done


# ============================================================
# Training Script
# ============================================================

def train_dark_pool_agents(episodes: int = 1000):
    """Train all dark pool agents"""
    print("=" * 60)
    print("TRAINING DARK POOL AGENTS (DRQN)")
    print("=" * 60)
    
    team = DarkPoolTeam()
    env = DarkPoolEnvironment()
    
    for episode in range(episodes):
        obs = env.reset()
        team.agents['Agent_P'].drqn.reset_episode()
        team.agents['Agent_Q'].drqn.reset_episode()
        team.agents['Agent_G'].drqn.reset_episode()
        
        total_reward = 0
        done = False
        
        while not done:
            # Get actions from each agent
            actions = {}
            for name, agent in team.agents.items():
                action, _ = agent.drqn.act(obs, training=True)
                actions[name] = action
            
            # Simulate step (simplified: use consensus action)
            consensus_action = max(set(actions.values()), key=list(actions.values()).count)
            next_obs, reward, done = env.step(consensus_action)
            
            # Store experiences
            for name, agent in team.agents.items():
                agent.drqn.remember(obs, actions[name], reward, next_obs, done)
                agent.drqn.replay()
            
            total_reward += reward
            obs = next_obs
        
        team.agents['Agent_P'].drqn.record_episode_reward(total_reward)
        team.agents['Agent_Q'].drqn.record_episode_reward(total_reward)
        team.agents['Agent_G'].drqn.record_episode_reward(total_reward)
        
        if (episode + 1) % 100 == 0:
            print(f"Episode {episode + 1}/{episodes}")
            stats = team.get_stats()
            for name, stat in stats.items():
                print(f"   {name}: avg reward = {stat['avg_reward_last_100']:.2f}")
    
    # Save trained models
    team.save_models()
    print("\n✅ Training complete! Models saved.")
    
    return team


if __name__ == '__main__':
    # Train the dark pool agents
    team = train_dark_pool_agents(episodes=500)
    
    # Test inference
    print("\n" + "=" * 60)
    print("TESTING DARK POOL AGENTS")
    print("=" * 60)
    
    test_obs = {
        'price': 2385.50,
        'volume_ratio': 1.8,
        'spread': 0.0002,
        'dark_volume_ratio': 45,
        'volume_profile': 0.7,
        'price_acceleration': 0.3,
        'order_imbalance': 0.2,
        'trade_size': 2500000,
        'time_since_last_trade': 300,
        'volatility': 0.012,
        'supply_distance': 0.003,
        'manipulation_score': 0.25
    }
    
    result = team.analyze(test_obs)
    print(f"\n📊 Dark Pool Team Analysis:")
    print(f"   Consensus: {result['dark_pool_consensus']}")
    print(f"   Confidence: {result['confidence']}%")
    print(f"   Strong: {result['is_strong']}")
    print(f"   Vote counts: {result['vote_counts']}")
    
    for name, vote in result['individual_votes'].items():
        print(f"   {name}: {vote['vote']} ({vote['confidence']:.0f}%)")
