# ============================================================
# train_agent.py - FIXED WITH PROPER REWARD STRUCTURE
# ============================================================

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
import logging
import gymnasium as gym
from gymnasium import spaces
from collections import deque
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SpreadArbitrageEnv(gym.Env):
    """
    Environment with PROPER REWARD STRUCTURE.
    Agent gets rewarded for:
    1. Entering trades at extreme Z-scores
    2. Exiting profitably at mean reversion
    3. Avoiding bad trades
    """
    
    def __init__(self, n_steps=50000, config=None):
        super(SpreadArbitrageEnv, self).__init__()
        
        self.n_steps = n_steps
        self.current_step = 0
        self.config = config
        
        # Generate data
        self._generate_data()
        
        # State: [z_score, position, entry_z, pnl_tracker]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)  # 0=SELL, 1=HOLD, 2=BUY
        
        self.position = 0
        self.entry_price = 0
        self.entry_z = 0
        self.trades = []
        self.returns = []
        self.total_pnl = 0
        self.episode_reward = 0
        self.step_counter = 0
        
        # Reward tracking
        self.reward_history = []
        
        logger.info(f"✅ Environment initialized: {self.n_steps} steps")
    
    def _generate_data(self):
        """Generate mean-reverting spread data with more extreme events."""
        np.random.seed(42)
        
        # Ornstein-Uhlenbeck process with occasional spikes
        theta = 0.03
        mu = 0.0
        sigma = 0.002
        dt = 1/60
        
        self.spread = np.zeros(self.n_steps)
        self.spread[0] = np.random.normal(0, 0.001)
        
        for i in range(1, self.n_steps):
            dW = np.random.normal(0, np.sqrt(dt))
            self.spread[i] = self.spread[i-1] + theta * (mu - self.spread[i-1]) * dt + sigma * dW
            
            # Add occasional spikes (like market events)
            if np.random.random() < 0.001:  # 0.1% chance
                self.spread[i] += np.random.choice([-0.02, 0.02])
        
        # Calculate Z-score with rolling window
        self.z_scores = np.zeros(self.n_steps)
        window = 50
        for i in range(window, self.n_steps):
            mu_local = np.mean(self.spread[i-window:i])
            sigma_local = np.std(self.spread[i-window:i])
            if sigma_local > 0:
                self.z_scores[i] = (self.spread[i] - mu_local) / sigma_local
            else:
                self.z_scores[i] = 0
        
        # Generate prices correlated with spread
        self.prices = 6000 + np.cumsum(np.random.normal(0, 0.0002, self.n_steps)) * 6000
        # Add spread influence to prices
        self.prices += self.spread * 1000
        
        logger.info(f"   Z-score range: {self.z_scores.min():.2f} to {self.z_scores.max():.2f}")
        logger.info(f"   Extreme events: {np.sum(np.abs(self.spread) > 0.01)}")
    
    def reset(self, seed=None, options=None):
        self.current_step = 0
        self.position = 0
        self.entry_price = 0
        self.entry_z = 0
        self.trades = []
        self.returns = []
        self.total_pnl = 0
        self.episode_reward = 0
        self.step_counter = 0
        self.reward_history = []
        return self._get_state(), {}
    
    def step(self, action):
        self.step_counter += 1
        
        current_z = self.z_scores[self.current_step]
        current_price = self.prices[self.current_step]
        current_spread = self.spread[self.current_step]
        
        reward = 0
        done = False
        truncated = False
        
        # === TRADE LOGIC ===
        if action == 2 and self.position == 0:  # BUY
            # Only enter if Z-score is extreme (<-1.5 for buy)
            if current_z < -1.5:
                self.position = 1
                self.entry_price = current_price
                self.entry_z = current_z
                # Small reward for entering a good trade
                reward = 0.1
            else:
                # Penalty for entering at bad time
                reward = -0.05
                
        elif action == 0 and self.position == 0:  # SELL
            # Only enter if Z-score is extreme (>1.5 for sell)
            if current_z > 1.5:
                self.position = -1
                self.entry_price = current_price
                self.entry_z = current_z
                reward = 0.1
            else:
                reward = -0.05
                
        elif action == 1 and self.position != 0:  # HOLD - check if we should exit
            # Calculate current P&L
            if self.position == 1:
                pnl = (current_price - self.entry_price) * 100
            else:
                pnl = (self.entry_price - current_price) * 100
            
            # Exit on mean reversion (Z-score crosses 0)
            if abs(current_z) < 0.5:
                # Successful trade!
                self.trades.append({
                    'entry_z': self.entry_z,
                    'exit_z': current_z,
                    'pnl': pnl
                })
                self.returns.append(pnl)
                self.total_pnl += pnl
                
                # Reward based on P&L (scaled)
                if pnl > 0:
                    reward = min(1.0, pnl / 50)  # Cap at 1.0
                else:
                    reward = max(-1.0, pnl / 50)  # Floor at -1.0
                
                self.position = 0
                
            # Exit on loss limit (Z-score moves against us)
            elif abs(current_z) > abs(self.entry_z) + 0.5:
                # Bad trade - spread widened further
                self.trades.append({
                    'entry_z': self.entry_z,
                    'exit_z': current_z,
                    'pnl': pnl
                })
                self.returns.append(pnl)
                self.total_pnl += pnl
                reward = -0.5  # Penalty for bad exit
                self.position = 0
            
            # Small reward for holding a profitable position
            elif pnl > 0:
                reward = 0.01  # Small encouragement
        
        # Small penalty for holding too long
        if self.position != 0 and self.step_counter % 100 == 0:
            reward -= 0.01
        
        # ===== STEP FORWARD =====
        self.current_step += 1
        self.episode_reward += reward
        
        if self.current_step >= self.n_steps - 1:
            done = True
        
        # ===== GET NEXT STATE =====
        state = self._get_state()
        
        # ===== INFO =====
        info = {
            'position': self.position,
            'current_z': current_z,
            'total_pnl': self.total_pnl,
            'trades': len(self.trades),
            'episode_reward': self.episode_reward
        }
        
        return state, reward, done, truncated, info
    
    def _get_state(self):
        if self.current_step < self.n_steps:
            return np.array([
                float(self.z_scores[self.current_step]),      # Current Z-score
                float(self.position),                          # Current position
                float(self.entry_z if self.position != 0 else 0),  # Entry Z
                float(len(self.trades) % 10)                   # Trade counter
            ], dtype=np.float32)
        return np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    
    def render(self, mode='human'):
        print(f"Step: {self.current_step}, Z: {self.z_scores[self.current_step]:.2f}, Pos: {self.position}")


# ============================================================
# CONFIG
# ============================================================

class Config:
    def __init__(self):
        self.TOTAL_TIMESTEPS = 200000  # Increased for better learning
        self.GAMMA = 0.9
        self.LEARNING_RATE = 0.0003
        self.BATCH_SIZE = 64
        self.N_STEPS = 50000
        self.MODELS_PATH = "models"
        self.LOGS_PATH = "logs"
        self.DATA_PATH = "data"


# ============================================================
# TRAINER
# ============================================================

class RLTrainer:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.env = None
        self.eval_env = None
        
        os.makedirs(self.config.MODELS_PATH, exist_ok=True)
        os.makedirs(self.config.LOGS_PATH, exist_ok=True)
        
        logger.info("🚀 RLTrainer initialized")
    
    def train(self):
        print("=" * 60)
        print("🎯 STARTING RL TRAINING (FIXED REWARD)")
        print("=" * 60)
        
        # Create environment
        self.env = SpreadArbitrageEnv(n_steps=self.config.N_STEPS)
        self.eval_env = SpreadArbitrageEnv(n_steps=1000)
        
        # Wrap with Monitor
        monitor_env = Monitor(self.env)
        eval_monitor = Monitor(self.eval_env)
        
        # Vectorize
        vec_env = DummyVecEnv([lambda: monitor_env])
        eval_vec_env = DummyVecEnv([lambda: eval_monitor])
        
        # Create model
        logger.info("🧠 Creating PPO model...")
        self.model = PPO(
            policy="MlpPolicy",
            env=vec_env,
            learning_rate=self.config.LEARNING_RATE,
            n_steps=2048,
            batch_size=self.config.BATCH_SIZE,
            n_epochs=10,
            gamma=self.config.GAMMA,
            verbose=1,
            tensorboard_log=os.path.join(self.config.LOGS_PATH, 'tensorboard')
        )
        
        # Setup evaluation callback
        eval_callback = EvalCallback(
            eval_vec_env,
            best_model_save_path=os.path.join(self.config.MODELS_PATH, 'best'),
            log_path=os.path.join(self.config.LOGS_PATH, 'evaluations'),
            eval_freq=10000,
            deterministic=True,
            render=False,
            n_eval_episodes=10
        )
        
        # Train
        logger.info(f"🎯 Training for {self.config.TOTAL_TIMESTEPS} timesteps...")
        
        self.model.learn(
            total_timesteps=self.config.TOTAL_TIMESTEPS,
            callback=eval_callback
        )
        
        # Save model
        model_path = os.path.join(self.config.MODELS_PATH, f'final_model_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        self.model.save(model_path)
        logger.info(f"💾 Model saved to {model_path}")
        
        # Evaluate
        self._evaluate()
        
        return self.model
    
    def _evaluate(self):
        """Evaluate the trained model."""
        print("\n" + "=" * 60)
        print("📊 EVALUATING MODEL")
        print("=" * 60)
        
        eval_env = SpreadArbitrageEnv(n_steps=2000)
        obs, _ = eval_env.reset()
        done = False
        total_reward = 0
        trades = 0
        total_pnl = 0
        
        while not done:
            action, _ = self.model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = eval_env.step(action)
            total_reward += reward
            if len(eval_env.trades) > trades:
                trades = len(eval_env.trades)
                total_pnl = eval_env.total_pnl
        
        print(f"   Total Reward: {total_reward:.2f}")
        print(f"   Total Trades: {trades}")
        print(f"   Total P&L: ${total_pnl:.2f}")
        print(f"   Win Rate: {len([t for t in eval_env.trades if t['pnl'] > 0]) / max(1, trades) * 100:.1f}%")
        print(f"   Status: {'✅ Successful' if trades > 0 and total_pnl > 0 else '⚠️ Needs more training'}")
        print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 REINFORCEMENT LEARNING TRADER (FIXED REWARD)")
    print("=" * 70)
    print()
    
    config = Config()
    trainer = RLTrainer(config)
    trainer.train()
    
    print("\n" + "=" * 70)
    print("✅ TRAINING COMPLETE!")
    print("=" * 70)