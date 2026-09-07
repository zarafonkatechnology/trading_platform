# ============================================================
# train_agent_final.py - COMPLETE WORKING VERSION
# ============================================================

import os
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpreadTradingEnv(gym.Env):
    """
    Clean, working environment for spread trading RL.
    """
    
    def __init__(self, n_steps=20000):
        super(SpreadTradingEnv, self).__init__()
        
        self.n_steps = n_steps
        self.current_step = 0
        
        # Generate realistic data
        self._generate_data()
        
        # State: [z_score, position, entry_z, unrealized_pnl]
        self.observation_space = spaces.Box(
            low=-5, high=5, shape=(4,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)  # 0=SELL, 1=HOLD, 2=BUY
        
        self.reset()
    
    def _generate_data(self):
        """Generate realistic mean-reverting data."""
        np.random.seed(42)
        
        n = self.n_steps
        
        # Ornstein-Uhlenbeck process (mean-reverting)
        theta = 0.05
        mu = 0.0
        sigma = 0.0015
        dt = 1.0
        
        # Generate spread
        self.spread = np.zeros(n)
        self.spread[0] = 0.0
        
        for i in range(1, n):
            dW = np.random.normal(0, np.sqrt(dt))
            self.spread[i] = self.spread[i-1] + theta * (mu - self.spread[i-1]) * dt + sigma * dW
        
        # Calculate Z-score with rolling window
        self.z_scores = np.zeros(n)
        window = 50
        for i in range(window, n):
            mu_local = np.mean(self.spread[i-window:i])
            sigma_local = np.std(self.spread[i-window:i])
            if sigma_local > 0.0001:
                self.z_scores[i] = (self.spread[i] - mu_local) / sigma_local
            else:
                self.z_scores[i] = 0
        
        # Cap Z-scores to realistic range
        self.z_scores = np.clip(self.z_scores, -3.5, 3.5)
        
        # Generate price (correlated with spread)
        self.prices = 6000 + np.cumsum(np.random.normal(0, 0.0001, n)) * 6000
        self.prices += self.spread * 500
        
        logger.info(f"   Z-score range: {self.z_scores.min():.2f} to {self.z_scores.max():.2f}")
        logger.info(f"   Spread range: {self.spread.min():.4f} to {self.spread.max():.4f}")
    
    def reset(self, seed=None, options=None):
        self.current_step = 0
        self.position = 0
        self.entry_price = 0
        self.entry_z = 0
        self.trades = []
        self.pnls = []
        self.total_pnl = 0
        return self._get_state(), {}
    
    def step(self, action):
        z = self.z_scores[self.current_step]
        price = self.prices[self.current_step]
        
        reward = 0
        done = False
        truncated = False
        
        # ===== TRADE LOGIC =====
        if action == 2 and self.position == 0:  # BUY
            if z < -1.5:  # Only buy when oversold
                self.position = 1
                self.entry_price = price
                self.entry_z = z
                reward = 0.05
            else:
                reward = -0.02  # Small penalty for bad entry
                
        elif action == 0 and self.position == 0:  # SELL
            if z > 1.5:  # Only sell when overbought
                self.position = -1
                self.entry_price = price
                self.entry_z = z
                reward = 0.05
            else:
                reward = -0.02
                
        elif action == 1 and self.position != 0:  # HOLD with position
            # Calculate unrealized P&L
            if self.position == 1:
                pnl = (price - self.entry_price) * 100
            else:
                pnl = (self.entry_price - price) * 100
            
            # Exit on mean reversion (Z-score near 0)
            if abs(z) < 0.3:
                # Close trade
                self.trades.append({
                    'entry_z': self.entry_z,
                    'exit_z': z,
                    'pnl': pnl
                })
                self.pnls.append(pnl)
                self.total_pnl += pnl
                
                # Reward based on P&L
                reward = np.clip(pnl / 50, -1, 1)
                self.position = 0
                
            # Exit if spread widens against us
            elif abs(z) > abs(self.entry_z) + 0.8:
                self.trades.append({
                    'entry_z': self.entry_z,
                    'exit_z': z,
                    'pnl': pnl
                })
                self.pnls.append(pnl)
                self.total_pnl += pnl
                reward = -0.3
                self.position = 0
            
            # Small reward for holding profitable position
            elif pnl > 0:
                reward = 0.01
        
        # ===== MOVE FORWARD =====
        self.current_step += 1
        
        if self.current_step >= self.n_steps - 1:
            done = True
        
        # ===== GET NEXT STATE =====
        state = self._get_state()
        
        info = {
            'position': self.position,
            'z_score': z,
            'total_pnl': self.total_pnl,
            'trades': len(self.trades),
            'reward': reward
        }
        
        return state, reward, done, truncated, info
    
    def _get_state(self):
        if self.current_step < self.n_steps:
            z = self.z_scores[self.current_step]
            # Calculate unrealized P&L if in position
            if self.position != 0 and self.entry_price > 0:
                price = self.prices[self.current_step]
                if self.position == 1:
                    unrealized = (price - self.entry_price) * 100
                else:
                    unrealized = (self.entry_price - price) * 100
            else:
                unrealized = 0
            
            return np.array([
                float(np.clip(z, -3.5, 3.5)),
                float(self.position),
                float(self.entry_z if self.position != 0 else 0),
                float(np.clip(unrealized / 100, -1, 1))
            ], dtype=np.float32)
        
        return np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)


def train():
    print("=" * 70)
    print("🤖 RL TRADER - FINAL WORKING VERSION")
    print("=" * 70)
    print()
    
    # Create environment
    print("📊 Creating environment...")
    env = SpreadTradingEnv(n_steps=30000)
    eval_env = SpreadTradingEnv(n_steps=2000)
    
    # Wrap with Monitor
    env = Monitor(env)
    eval_env = Monitor(eval_env)
    
    # Vectorize
    vec_env = DummyVecEnv([lambda: env])
    eval_vec_env = DummyVecEnv([lambda: eval_env])
    
    # Create model
    print("🧠 Creating PPO model...")
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.9,
        verbose=1,
        tensorboard_log="./logs"
    )
    
    # Train
    print("\n🎯 Training...")
    model.learn(
        total_timesteps=150000,
        progress_bar=False
    )
    
    # Save
    os.makedirs("models", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f"models/final_model_{timestamp}.zip"
    model.save(model_path)
    print(f"\n✅ Model saved to {model_path}")
    
    # ===== EVALUATE =====
    print("\n" + "=" * 60)
    print("📊 EVALUATING MODEL")
    print("=" * 60)
    
    eval_env = SpreadTradingEnv(n_steps=3000)
    obs, _ = eval_env.reset()
    done = False
    total_reward = 0
    total_pnl = 0
    trades = 0
    wins = 0
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = eval_env.step(action)
        total_reward += reward
        if len(eval_env.trades) > trades:
            trades = len(eval_env.trades)
            total_pnl = eval_env.total_pnl
            if eval_env.trades[-1]['pnl'] > 0:
                wins += 1
    
    win_rate = (wins / max(1, trades)) * 100
    
    print(f"\n   📊 Results:")
    print(f"   Total Trades:  {trades}")
    print(f"   Win Rate:      {win_rate:.1f}%")
    print(f"   Total P&L:     ${total_pnl:.2f}")
    print(f"   Total Reward:  {total_reward:.2f}")
    print(f"   Status:        {'✅ SUCCESS' if trades > 5 and win_rate > 50 else '⚠️ NEEDS MORE TRAINING'}")
    print("=" * 60)
    
    return model


if __name__ == "__main__":
    train()