"""
Reinforcement Learning Agent - Learns from data, not rules
Uses Q-Learning with experience replay
"""

import numpy as np
import random
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import deque
from backend.agents.agent_i_sentiment import SentimentMaster
from backend.agents.agent_j_volume import VolumeMaster
from backend.agents.agent_k_ichimoku import IchimokuExpert
from backend.agents.agent_l_economic import EconomicCalendarMaster
logger = logging.getLogger(__name__)

class RLAgent:
    """
    Reinforcement Learning Agent
    - Takes actions based on STATE (market features)
    - Receives REWARD (+XP for profit, -XP for loss)
    - Learns optimal policy via Q-Learning
    """
    
    def __init__(self, name: str, agent_type: str, learning_rate: float = 0.1):
        self.name = name
        self.agent_type = agent_type
        self.learning_rate = learning_rate
        self.discount_factor = 0.95
        self.exploration_rate = 0.3
        self.exploration_min = 0.05
        self.exploration_decay = 0.995
        
        self.actions = ['BUY', 'SELL', 'HOLD']
        self.q_table = {}  # State -> Action values
        self.memory = deque(maxlen=10000)  # Experience replay buffer
        
        # Tracking
        self.total_reward = 0
        self.episode_trades = 0
        self.winning_trades = 0
        
        logger.info(f"🧠 RL Agent {name} ({agent_type}) initialized")
    
    def _get_state_key(self, features: Dict) -> str:
        """
        Convert continuous features to discrete state
        Discretizes Z-Score, RSI, and Trend Strength into buckets
        """
        z_score = int(features.get('z_score_20', 0) * 10)  # -20 to 20 range
        rsi = int(features.get('rsi_14', 50) / 10)          # 0 to 10 range
        trend = int(features.get('trend_strength', 0) / 20)  # 0 to 5 range
        
        return f"Z{z_score}_R{rsi}_T{trend}"
    
    def get_action(self, features: Dict, training: bool = True) -> Tuple[str, float]:
        """
        Choose action using epsilon-greedy policy
        Returns: (action, confidence)
        """
        state = self._get_state_key(features)
        
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        
        # Exploration: random action
        if training and random.random() < self.exploration_rate:
            action = random.choice(self.actions)
            confidence = 50 + random.randint(0, 30)
            return action, confidence
        
        # Exploitation: best known action
        best_action = max(self.q_table[state], key=self.q_table[state].get)
        q_value = self.q_table[state][best_action]
        confidence = min(95, 60 + q_value * 10)
        
        return best_action, confidence
    
    def update_from_reward(self, state_features: Dict, action: str, 
                           reward: float, next_state_features: Dict, 
                           xp_change: int):
        """
        Q-Learning update: Q(s,a) = Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
        """
        state = self._get_state_key(state_features)
        next_state = self._get_state_key(next_state_features) if next_state_features else state
        
        # Initialize if not exists
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0 for a in self.actions}
        
        # Current Q-value
        current_q = self.q_table[state].get(action, 0)
        
        # Max future Q-value
        max_future_q = max(self.q_table[next_state].values())
        
        # Q-Learning update
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_future_q - current_q)
        
        # Update Q-table
        self.q_table[state][action] = new_q
        
        # Store in experience buffer
        self._store_experience(state_features, action, reward, next_state_features, xp_change)
        
        # Update totals
        self.total_reward += reward
        if action != 'HOLD':
            self.episode_trades += 1
            if reward > 0:
                self.winning_trades += 1
        
        # Decay exploration rate
        self.exploration_rate = max(self.exploration_min, self.exploration_rate * self.exploration_decay)
    
    def _store_experience(self, state: Dict, action: str, reward: float, 
                          next_state: Dict, xp_change: int):
        """Store experience in buffer for mini-batch learning"""
        self.memory.append({
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'xp_change': xp_change,
            'timestamp': datetime.now().isoformat()
        })
    
    def mini_batch_update(self, batch_size: int = 32):
        """
        Mini-batch update from experience replay
        This is the key learning method - every 5 minutes
        """
        if len(self.memory) < batch_size:
            return 0
        
        batch = random.sample(list(self.memory), batch_size)
        total_loss = 0
        
        for experience in batch:
            state = experience['state']
            action = experience['action']
            reward = experience['reward']
            next_state = experience['next_state']
            
            state_key = self._get_state_key(state)
            next_state_key = self._get_state_key(next_state) if next_state else state_key
            
            if state_key not in self.q_table:
                self.q_table[state_key] = {a: 0 for a in self.actions}
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = {a: 0 for a in self.actions}
            
            current_q = self.q_table[state_key][action]
            max_future_q = max(self.q_table[next_state_key].values())
            
            td_target = reward + self.discount_factor * max_future_q
            td_error = td_target - current_q
            
            self.q_table[state_key][action] = current_q + self.learning_rate * td_error
            total_loss += abs(td_error)
        
        return total_loss / batch_size
    
    def get_best_action(self, features: Dict) -> str:
        """Get best action without exploration (for live trading)"""
        state = self._get_state_key(features)
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        return max(self.q_table[state], key=self.q_table[state].get)
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        win_rate = (self.winning_trades / self.episode_trades * 100) if self.episode_trades > 0 else 0
        return {
            'name': self.name,
            'type': self.agent_type,
            'q_table_size': len(self.q_table),
            'exploration_rate': round(self.exploration_rate, 3),
            'total_reward': round(self.total_reward, 2),
            'total_trades': self.episode_trades,
            'winning_trades': self.winning_trades,
            'win_rate': round(win_rate, 1)
        }
    
    def save_weights(self, version: int):
        """Save Q-table as policy weights"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rl_policy_weights (agent_name, layer_name, weight_values, version)
                VALUES (%s, %s, %s, %s)
            """, (self.name, 'q_table', json.dumps(self.q_table), version))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"💾 Saved weights for {self.name}, version {version}")
        except Exception as e:
            logger.warning(f"Could not save weights: {e}")
