# train_rl.py - FIXED VERSION

import os
import json
import random
import numpy as np
import logging
from typing import Dict, List

from trading_controller2 import ForexTradingController, FOREX_PAIRS
from rl_trading_env import ForexTradingEnv
from rl_agent import RLAgent

# Make sure stable-baselines3 is installed
try:
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv
except ImportError:
    print("⚠️ stable-baselines3 not fully installed")
    # Fallback: define dummy VecEnv wrapper
    class DummyVecEnv:
        def __init__(self, env_fns):
            self.envs = [env_fn() for env_fn in env_fns]
            self.num_envs = len(self.envs)
            if self.config.get('simulation_mode', False):
                logger.info("🔄 SIMULATION MODE - No real orders will be sent")
                # Override the send_real_order method to just log orders
                self.send_real_order = self._simulate_order
        def reset(self):
            return self.envs[0].reset()
        def step(self, action):
            return self.envs[0].step(action)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_historical_data() -> Dict:
    """Load historical price data from dashboard file."""
    appdata = os.environ.get('APPDATA', '')
    possible_paths = [
        os.path.join(appdata, 'MetaQuotes', 'Terminal', 'Common', 'Files', 'dashboard_data.json'),
        "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/dashboard_data.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                logger.info(f"✅ Loaded data from {path}")
                return data.get('prices', {})
            except Exception as e:
                logger.warning(f"Error loading {path}: {e}")
    
    logger.warning("No historical data found. Using synthetic data only.")
    return {}


def generate_synthetic_episodes(n_episodes: int = 500, n_steps: int = 100) -> List[List[Dict]]:
    """Generate synthetic episodes using Monte Carlo simulation."""
    episodes = []
    pairs = FOREX_PAIRS
    
    for _ in range(n_episodes):
        episode = []
        base_price = random.uniform(0.8, 1.3)
        volatility = random.uniform(0.005, 0.03)
        drift = random.uniform(-0.002, 0.002)
        
        for step in range(n_steps):
            market_data = {}
            for pair in pairs:
                if step == 0:
                    price = base_price * (1 + random.uniform(-0.05, 0.05))
                else:
                    prev_price = episode[-1].get(pair, base_price)
                    shock = np.random.normal(0, volatility)
                    price = prev_price * (1 + drift + shock)
                    price = max(0.0001, price)
                market_data[pair] = price
            episode.append(market_data)
        
        episodes.append(episode)
    
    logger.info(f"✅ Generated {len(episodes)} synthetic episodes")
    return episodes


def create_episodes_from_history(price_history: Dict, n_episodes: int = 200, 
                                 episode_length: int = 50) -> List[List[Dict]]:
    """Create training episodes from historical price data."""
    episodes = []
    
    # Get the minimum length across all pairs
    lengths = []
    for v in price_history.values():
        if isinstance(v, list) and len(v) > 0:
            lengths.append(len(v))
    
    if not lengths:
        return []
    
    min_length = min(lengths)
    if min_length < episode_length + 10:
        return []
    
    for _ in range(n_episodes):
        start_idx = random.randint(0, min_length - episode_length - 5)
        episode = []
        
        for step in range(episode_length):
            market_data = {}
            for pair, prices in price_history.items():
                if isinstance(prices, list) and start_idx + step < len(prices):
                    market_data[pair] = prices[start_idx + step]
                else:
                    market_data[pair] = prices[-1] if isinstance(prices, list) and prices else 1.0
            episode.append(market_data)
        
        episodes.append(episode)
    
    logger.info(f"✅ Created {len(episodes)} episodes from historical data")
    return episodes


def train_rl():
    """Main training function."""
    
    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 60,
        'cycle_interval': 10,
        'rl_enabled': True,
        'load_rl_model': False,
        'rl_model_path': 'models/rl_model.zip',
        'simulation_mode': True, 
        'engine_config': {
            'factor_weights': {
                'interest_rate_diff': 0.35,
                'yield_curve_slope': 0.25,
                'carry_trade_flow': 0.15,
                'positioning_sentiment': 0.15,
                'central_bank_actions': 0.10,
            }
        }
    }
    
    logger.info("="*60)
    logger.info("🚀 STARTING RL TRAINING")
    logger.info("="*60)
    
    # ===== 1. INITIALIZE CONTROLLER =====
    logger.info("Initializing controller...")
    controller = ForexTradingController(config)
    
    # ===== 2. CREATE ENVIRONMENT =====
    # Create a single environment for training
    env = ForexTradingEnv(controller, config)
    logger.info("✅ Environment initialized")
    
    # ===== 3. LOAD/CREATE EPISODES =====
    all_episodes = []
    
    # Try loading historical data
    hist_data = load_historical_data()
    if hist_data:
        hist_episodes = create_episodes_from_history(hist_data, n_episodes=200, episode_length=50)
        all_episodes.extend(hist_episodes)
        logger.info(f"Added {len(hist_episodes)} historical episodes")
    
    # Generate synthetic episodes
    logger.info("Generating synthetic episodes (Monte Carlo)...")
    synthetic_episodes = generate_synthetic_episodes(n_episodes=500, n_steps=100)
    all_episodes.extend(synthetic_episodes)
    
    logger.info(f"📊 Total training episodes: {len(all_episodes)}")
    
    if not all_episodes:
        logger.error("❌ No episodes generated!")
        return
    
    # ===== 4. CREATE VEC ENV FOR SB3 =====
    # Wrap the environment in a DummyVecEnv for SB3 compatibility
    def make_env():
        return env
    
    vec_env = DummyVecEnv([make_env])
    logger.info("✅ VecEnv created for SB3")
    
    # ===== 5. INITIALIZE RL AGENT =====
    logger.info("Initializing RL Agent...")
    rl_agent = RLAgent(
        vec_env,  # Pass VecEnv, not the raw env
        model_path='models/rl_model.zip', 
        load_existing=False, 
        learning_rate=3e-4
    )
    logger.info("✅ RL Agent initialized")
    
    # ===== 6. TRAINING LOOP =====
    logger.info("\n" + "="*60)
    logger.info("🎯 STARTING TRAINING")
    logger.info("="*60)
    
    total_steps = 0
    epochs = 3
    
    for epoch in range(epochs):
        logger.info(f"\n📈 Epoch {epoch+1}/{epochs}")
        random.shuffle(all_episodes)
        
        epoch_rewards = []
        
        for ep_idx, ep_data in enumerate(all_episodes):
            # Set external data for the environment
            env.set_external_data(ep_data[0])  # Set first step
            
            # Reset the VecEnv
            obs = vec_env.reset()
            
            # If obs is a tuple (from Gymnasium), extract the observation
            if isinstance(obs, tuple):
                obs = obs[0]
            
            done = False
            step = 0
            episode_reward = 0
            
            while not done and step < len(ep_data):
                # Update external data for each step
                env.set_external_data(ep_data[step])
                
                # Get action from RL agent
                action = rl_agent.predict(obs, deterministic=False)
                
                # Step the VecEnv
                obs, reward, done, info = vec_env.step(action)
                
                # If obs is a tuple (from Gymnasium), extract the observation
                if isinstance(obs, tuple):
                    obs = obs[0]
                
                episode_reward += reward
                step += 1
                total_steps += 1
                
                # Periodic training
                if total_steps % 500 == 0:
                    rl_agent.train(total_timesteps=500)
                    logger.info(f"   Trained at step {total_steps}")
            
            epoch_rewards.append(episode_reward)
            
            # Log progress every 50 episodes
            if ep_idx % 50 == 0 and ep_idx > 0:
                avg_reward = np.mean(epoch_rewards[-50:])
                logger.info(f"   Episodes {ep_idx-50}-{ep_idx}: Avg Reward = {avg_reward:.2f}")
        
        # End of epoch - save model
        os.makedirs('models', exist_ok=True)
        rl_agent.save(f'models/rl_model_epoch_{epoch+1}.zip')
        avg_epoch_reward = np.mean(epoch_rewards) if epoch_rewards else 0
        logger.info(f"✅ Epoch {epoch+1} complete. Avg Reward: {avg_epoch_reward:.2f}")
    
    # ===== 7. FINAL SAVE =====
    os.makedirs('models', exist_ok=True)
    rl_agent.save('models/rl_model_final.zip')
    logger.info("\n" + "="*60)
    logger.info("✅ TRAINING COMPLETE!")
    logger.info(f"   Total steps: {total_steps}")
    logger.info(f"   Model saved to: models/rl_model_final.zip")
    logger.info("="*60)


if __name__ == "__main__":
    os.makedirs('models', exist_ok=True)
    train_rl()