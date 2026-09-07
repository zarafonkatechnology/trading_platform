#!/usr/bin/env python3
"""
A2C Fine‑tuning for HA3C Phase 2
Loads pretrained policy and continues training with RL in Monte Carlo environment.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import os

# ============================================================
# 1. Load pretrained policy (from HA3C pretraining)
# ============================================================
def load_pretrained_policy(path='pretrained_policy.pt'):
    """Load pretrained policy network, scaler, and metadata."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Pretrained model {path} not found. Run ha3c_pretrain.py first.")
    checkpoint = torch.load(path, weights_only=False)
    return checkpoint

# ============================================================
# 2. Define Policy and Value Networks
# ============================================================
class PolicyNetwork(nn.Module):
    def __init__(self, input_dim=9, hidden_dim=64, output_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
    def forward(self, x):
        return self.net(x)

class ValueNetwork(nn.Module):
    def __init__(self, input_dim=9, hidden_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    def forward(self, x):
        return self.net(x).squeeze(-1)

# ============================================================
# 3. Trading Environment (Monte Carlo world model)
# ============================================================
class TradingEnvironment:
    def __init__(self, initial_price=1.0950, horizon=20):
        self.price = initial_price
        self.horizon = horizon
        self.current_step = 0  # Renamed from 'step' to avoid conflict
        self.position = 0
        self.volume_ratio = 1.0
        self.volatility = 0.005
        self.supply_distance = 0.01
        self.demand_distance = 0.01
        self.manipulation_score = 0.65
        self.zone_strength = 70
        self.touches = 3
        self.hidden_funds = 45000
        
    def reset(self):
        self.price = 1.0950
        self.current_step = 0
        self.position = 0
        self.volume_ratio = 1.0
        self.volatility = 0.005
        self.supply_distance = 0.01
        self.demand_distance = 0.01
        self.manipulation_score = 0.65
        self.zone_strength = 70
        self.touches = 3
        self.hidden_funds = 45000
        return self._get_state()
    
    def _get_state(self):
        return np.array([
            self.price / 1000,
            self.volume_ratio,
            self.volatility,
            self.supply_distance,
            self.demand_distance,
            self.manipulation_score,
            self.zone_strength / 100,
            min(1.0, self.touches / 10),
            self.hidden_funds / 100000
        ], dtype=np.float32)
    
    def step(self, action):
        self.current_step += 1
        price_change = np.random.normal(0, self.volatility)
        next_price = self.price * (1 + price_change)
        
        reward = 0
        done = False
        
        # Manipulation penalty
        if self.manipulation_score < 0.6 and action != 2:
            reward -= 50
        
        # Position management
        if action == 0 and self.position == 0:   # open long
            self.position = 1
            reward -= 1
        elif action == 1 and self.position == 0: # open short
            self.position = -1
            reward -= 1
        elif action == 0 and self.position == -1: # cover short
            pnl = (self.price - next_price) / self.price
            reward += pnl * 100
            self.position = 0
        elif action == 1 and self.position == 1:  # close long
            pnl = (next_price - self.price) / self.price
            reward += pnl * 100
            self.position = 0
        elif action == 2 and self.position != 0:
            if self.position == 1:
                pnl = (next_price - self.price) / self.price
            else:
                pnl = (self.price - next_price) / self.price
            reward += pnl * 50
        
        # Update state
        self.price = next_price
        self.volume_ratio = max(0.5, min(2.0, self.volume_ratio + np.random.normal(0, 0.05)))
        self.volatility = max(0.002, min(0.02, self.volatility + np.random.normal(0, 0.0005)))
        self.supply_distance = max(0.001, self.supply_distance + np.random.normal(0, 0.0005))
        self.demand_distance = max(0.001, self.demand_distance + np.random.normal(0, 0.0005))
        self.manipulation_score = min(1.0, max(0.0, self.manipulation_score + np.random.normal(0, 0.05)))
        self.zone_strength = min(100, max(0, self.zone_strength + np.random.randint(-5, 5)))
        self.touches = min(10, max(0, self.touches + np.random.randint(-1, 2)))
        self.hidden_funds = max(1000, self.hidden_funds + np.random.randint(-5000, 5000))
        
        if self.current_step >= self.horizon:
            done = True
        
        return self._get_state(), reward, done, {}

# ============================================================
# 4. A2C Trainer
# ============================================================
class A2CTrainer:
    def __init__(self, policy_net, value_net, lr_policy=0.0001, lr_value=0.0005, gamma=0.99):
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
    
    def train_episode(self, env, max_steps=20):
        states, actions, rewards, dones = [], [], [], []
        state = env.reset()
        for _ in range(max_steps):
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            logits = self.policy(state_t)
            probs = torch.softmax(logits, dim=-1)
            action = torch.multinomial(probs, 1).item()
            
            next_state, reward, done, _ = env.step(action)
            
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            dones.append(done)
            
            state = next_state
            if done:
                break
        
        if len(states) == 0:
            return 0, 0
        
        states_t = torch.tensor(np.array(states), dtype=torch.float32)
        actions_t = torch.tensor(actions, dtype=torch.long)
        returns_t = self.compute_returns(rewards, dones)
        
        values = self.value(states_t)
        value_loss = nn.MSELoss()(values, returns_t.detach())
        
        advantages = returns_t - values.detach()
        log_probs = torch.log_softmax(self.policy(states_t), dim=-1)
        selected_log_probs = log_probs.gather(1, actions_t.unsqueeze(1)).squeeze()
        policy_loss = -(selected_log_probs * advantages).mean()
        
        entropy = -(torch.exp(log_probs) * log_probs).sum(-1).mean()
        entropy_bonus = -0.01 * entropy
        
        total_loss = policy_loss + 0.5 * value_loss + entropy_bonus
        
        self.optim_policy.zero_grad()
        self.optim_value.zero_grad()
        total_loss.backward()
        self.optim_policy.step()
        self.optim_value.step()
        
        return total_loss.item(), np.sum(rewards)

# ============================================================
# 5. Main fine‑tuning loop
# ============================================================
def main():
    print("="*60)
    print("A2C Fine‑tuning (HA3C Phase 2)")
    print("="*60)
    
    # Load pretrained policy
    try:
        checkpoint = load_pretrained_policy()
        print(f"✅ Loaded pretrained policy (val_acc: {checkpoint.get('val_acc', 'N/A')}%)")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Please run ha3c_pretrain.py first to create pretrained_policy.pt")
        return
    
    input_dim = len(checkpoint['feature_cols'])
    output_dim = len(checkpoint['action_map'])
    
    # Initialize policy with pretrained weights
    policy = PolicyNetwork(input_dim=input_dim, output_dim=output_dim)
    policy.load_state_dict(checkpoint['model_state_dict'])
    print("✅ Policy loaded with pretrained weights")
    
    # Initialize value network from scratch
    value_net = ValueNetwork(input_dim=input_dim)
    
    # Create environment
    env = TradingEnvironment()
    
    # Create trainer
    trainer = A2CTrainer(policy, value_net, lr_policy=0.0001, lr_value=0.0005, gamma=0.99)
    
    # Fine‑tuning loop
    n_episodes = 500
    print(f"\n🚀 Starting A2C fine‑tuning for {n_episodes} episodes...")
    
    for ep in range(1, n_episodes + 1):
        loss, total_reward = trainer.train_episode(env, max_steps=20)
        if ep % 50 == 0:
            print(f"Episode {ep:3d} | Loss: {loss:.4f} | Total Reward: {total_reward:.2f}")
    
    # Save fine‑tuned model
    torch.save({
        'policy_state_dict': policy.state_dict(),
        'value_state_dict': value_net.state_dict(),
        'scaler': checkpoint['scaler'],
        'feature_cols': checkpoint['feature_cols'],
        'action_map': checkpoint['action_map']
    }, 'finetuned_policy.pt')
    
    print("\n✅ Fine‑tuned policy saved to 'finetuned_policy.pt'")
    print("\n📊 You can now deploy this policy in live trading.")

if __name__ == '__main__':
    main()
