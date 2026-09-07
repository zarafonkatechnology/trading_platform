# backend/training/ha3c_trainer.py
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from collections import deque
from agent_r_rl import RLPolicy
from backend.utils.world_model import WorldModel, MonteCarloSimulator
# In your ha3c_pretrain.py, replace CSV loading with:
from feature_store import FeatureStore

def load_expert_data_from_store(min_confidence=70):
    store = FeatureStore("trading_features.db")
    df = store.get_expert_dataset(min_confidence=min_confidence)
    
    if df.empty:
        print("⚠️ No expert data available. Run trading cycles first.")
        return None, None
    
    # Prepare features and targets
    feature_cols = ['rsi', 'volume_ratio', 'volatility', 'supply_distance',
                    'demand_distance', 'manipulation_score', 'zone_strength',
                    'touches', 'hidden_funds_estimate']
    
    X = df[feature_cols].values
    y = df['consensus_action'].map({'BUY': 0, 'SELL': 1, 'HOLD': 2}).values
    
    return X, y
class A2CTrainer:
    def __init__(self, policy_net, value_net, lr_policy=0.001, lr_value=0.001, gamma=0.99):
        self.policy = policy_net
        self.value = value_net
        self.optim_policy = optim.Adam(self.policy.parameters(), lr=lr_policy)
        self.optim_value = optim.Adam(self.value.parameters(), lr=lr_value)
        self.gamma = gamma
    
    def compute_returns(self, rewards, dones):
        returns = []
        R = 0
        for r, done in zip(reversed(rewards), reversed(dones)):
            if done:
                R = 0
            R = r + self.gamma * R
            returns.insert(0, R)
        return torch.tensor(returns, dtype=torch.float32)
    
    def train_episode(self, env, max_steps=100):
        states, actions, rewards, dones = [], [], [], []
        state = env.reset()
        for _ in range(max_steps):
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            probs = self.policy(state_t)
            action = torch.multinomial(probs, 1).item()
            next_state, reward, done, _ = env.step(action)
            
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            dones.append(done)
            
            state = next_state
            if done:
                break
        
        # Convert to tensors
        states_t = torch.tensor(np.array(states), dtype=torch.float32)
        actions_t = torch.tensor(actions, dtype=torch.long)
        returns_t = self.compute_returns(rewards, dones)
        
        # Value loss
        values = self.value(states_t).squeeze()
        value_loss = nn.MSELoss()(values, returns_t.detach())
        
        # Policy loss (A2C)
        advantages = returns_t - values.detach()
        log_probs = torch.log(self.policy(states_t).gather(1, actions_t.unsqueeze(1)).squeeze())
        policy_loss = -(log_probs * advantages).mean()
        
        # Total loss
        total_loss = policy_loss + 0.5 * value_loss
        
        self.optim_policy.zero_grad()
        self.optim_value.zero_grad()
        total_loss.backward()
        self.optim_policy.step()
        self.optim_value.step()
        
        return total_loss.item(), np.sum(rewards)
