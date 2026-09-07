# backend/agents/agent_r_rl.py
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from backend.utils.world_model import WorldModel, MonteCarloSimulator

class RLPolicy(nn.Module):
    def __init__(self, state_dim=9, hidden_dim=64, action_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
    def forward(self, x):
        return self.net(x)

class ModelBasedAgentR:
    def __init__(self, name="Agent_R"):
        self.name = name
        self.policy = RLPolicy()
        self.optimizer = optim.Adam(self.policy.parameters(), lr=0.001)
        self.world_model = WorldModel()
        self.mc_sim = MonteCarloSimulator(self.world_model)
        self.constraint_threshold = 0.6  # M score must be >= 0.6 to trade
        
    def get_state(self, observation):
        # state: price, volume_ratio, supply_dist, demand_dist, manipulation_score,
        #        recent_volatility, zone_strength, touches, hidden_funds_estimate
        return np.array([
            observation['price'] / 1000,
            observation['volume_ratio'],
            observation['supply_distance'],
            observation['demand_distance'],
            observation['manipulation_score'],
            observation.get('volatility', 0.005),
            observation.get('zone_strength', 50) / 100,
            min(1.0, observation.get('touches', 0) / 10),
            observation.get('hidden_funds_estimate', 0) / 100000
        ], dtype=np.float32)
    
    def act(self, state_tensor):
        with torch.no_grad():
            probs = self.policy(state_tensor)
            action = torch.multinomial(probs, 1).item()
        return action
    
    def compute_reward(self, action, pnl, manipulation_score, constraints_violated):
        """RLHF‑style reward: profit * confidence * M, penalize constraints."""
        reward = pnl * 1000  # scale profit
        if manipulation_score < self.constraint_threshold:
            reward -= 50      # penalty for trading manipulated level
        if constraints_violated:
            reward -= 100
        return reward
    
    def train_step(self, memory_batch):
        # Standard A2C training loop (will be integrated later)
        pass
