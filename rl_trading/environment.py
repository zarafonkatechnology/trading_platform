# ============================================================
# environment.py - Custom Gymnasium Environment
# ============================================================

import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, List, Tuple, Optional
import logging
from collections import deque
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpreadArbitrageEnv(gym.Env):
    """
    Custom Gymnasium Environment for Spread Arbitrage Trading.
    
    State: Normalized Z-score, spread, beta, rolling mu, rolling sigma, position
    Action: BUY, SELL, HOLD
    Reward: Sharpe Ratio (risk-adjusted)
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, data: pd.DataFrame, config=None, seed=None):
        super(SpreadArbitrageEnv, self).__init__()
        
        self.data = data
        self.config = config
        
        # ===== HISTORICAL DATA =====
        self.spx_prices = data['spx'].values
        self.ndx_prices = data['ndx'].values
        self.spread_values = data['spread'].values
        self.z_scores = data['z_score'].values
        self.dates = data.index.values
        
        self.n_steps = len(self.spread_values)
        
        # ===== STATE SPACE =====
        # [z_score, spread, beta, mu, sigma, position]
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(6,),
            dtype=np.float32
        )
        
        # ===== ACTION SPACE =====
        # 0: SELL, 1: HOLD, 2: BUY
        self.action_space = spaces.Discrete(3)
        
        # ===== TRACKING =====
        self.current_step = 0
        self.position = 0  # -1: short, 0: neutral, 1: long
        self.entry_price = 0
        self.entry_spread = 0
        self.trades = []
        self.returns = []
        self.rolling_returns = deque(maxlen=100)
        
        # ===== PARAMETERS =====
        self.beta = 1.05
        self.spread_history = []
        self.mu = 0.0
        self.sigma = 0.0
        
        # ===== REWARD TRACKING =====
        self.episode_returns = []
        self.cumulative_pnl = 0
        self.trades_count = 0
        
        # Set seed if provided
        if seed is not None:
            np.random.seed(seed)
        
        logger.info("✅ SpreadArbitrageEnv initialized")
        logger.info(f"   Data points: {self.n_steps}")
        logger.info(f"   State shape: {self.observation_space.shape}")
        logger.info(f"   Actions: {self.action_space.n}")
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment to start of episode.
        
        Args:
            seed: Random seed
            options: Additional options
        """
        # Set seed if provided
        if seed is not None:
            np.random.seed(seed)
        
        self.current_step = 0
        self.position = 0
        self.entry_price = 0
        self.entry_spread = 0
        self.trades = []
        self.returns = []
        self.rolling_returns = deque(maxlen=100)
        self.episode_returns = []
        self.cumulative_pnl = 0
        self.trades_count = 0
        self.spread_history = []
        self.mu = 0.0
        self.sigma = 0.0
        
        return self._get_state(), {}
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one step in the environment."""
        # ===== GET CURRENT STATE =====
        current_spread = self.spread_values[self.current_step]
        current_z = self.z_scores[self.current_step]
        current_price = self.spx_prices[self.current_step]
        
        # ===== UPDATE ROLLING STATISTICS =====
        self.spread_history.append(current_spread)
        if len(self.spread_history) > 300:
            self.spread_history.pop(0)
        
        if len(self.spread_history) >= 30:
            self.mu = np.mean(self.spread_history)
            self.sigma = np.std(self.spread_history)
        
        # ===== EXECUTE ACTION =====
        reward = 0
        done = False
        truncated = False
        
        # Map action: 0=SELL, 1=HOLD, 2=BUY
        action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        action_type = action_map[action]
        
        # ===== TRADE LOGIC =====
        if action_type == 'BUY' and self.position <= 0:
            # Enter long position
            self.entry_price = current_price
            self.entry_spread = current_spread
            self.position = 1
            self.trades_count += 1
            logger.debug(f"📈 ENTRY: BUY at Z={current_z:.2f}")
            
        elif action_type == 'SELL' and self.position >= 0:
            # Enter short position
            self.entry_price = current_price
            self.entry_spread = current_spread
            self.position = -1
            self.trades_count += 1
            logger.debug(f"📉 ENTRY: SELL at Z={current_z:.2f}")
            
        elif action_type == 'HOLD' and self.position != 0:
            # Check if we should exit based on Z-score reversion
            if abs(current_z) < 0.5:
                # Calculate P&L
                if self.position == 1:
                    pnl = (current_price - self.entry_price) * 0.02 * 100000
                else:
                    pnl = (self.entry_price - current_price) * 0.02 * 100000
                
                self.returns.append(pnl)
                self.rolling_returns.append(pnl)
                self.cumulative_pnl += pnl
                
                trade_record = {
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'entry_z': self.z_scores[max(0, self.current_step - 1)],
                    'exit_z': current_z,
                    'pnl': pnl,
                    'position': self.position
                }
                self.trades.append(trade_record)
                self.episode_returns.append(pnl)
                
                logger.debug(f"🔚 EXIT: P&L=${pnl:.2f}, Z={current_z:.2f}")
                
                # Reset position
                self.position = 0
        
        # ===== CALCULATE REWARD =====
        if len(self.rolling_returns) > 10:
            reward = self._calculate_sharpe_reward()
        else:
            reward = 0.0
        
        # ===== MOVE TO NEXT STEP =====
        self.current_step += 1
        
        # Check if episode is done
        if self.current_step >= self.n_steps - 1:
            done = True
        
        # ===== GET NEXT STATE =====
        state = self._get_state()
        
        # ===== INFO =====
        info = {
            'position': self.position,
            'current_z': current_z,
            'current_spread': current_spread,
            'trades': self.trades_count,
            'cumulative_pnl': self.cumulative_pnl
        }
        
        return state, reward, done, truncated, info
    
    def _get_state(self) -> np.ndarray:
        """Get current state vector."""
        if self.current_step < self.n_steps:
            current_z = self.z_scores[self.current_step]
            current_spread = self.spread_values[self.current_step]
        else:
            current_z = 0
            current_spread = 0
        
        # State: [z_score, spread, beta, mu, sigma, position]
        state = np.array([
            float(current_z),
            float(current_spread),
            float(self.beta),
            float(self.mu),
            float(self.sigma),
            float(self.position)
        ], dtype=np.float32)
        
        return state
    
    def _calculate_sharpe_reward(self) -> float:
        """Calculate Sharpe Ratio based reward."""
        if len(self.rolling_returns) < 10:
            return 0.0
        
        returns = np.array(self.rolling_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns) + 1e-8
        
        risk_free = getattr(self.config, 'RISK_FREE_RATE', 0.02)
        sharpe = (mean_return - risk_free) / std_return
        
        return np.clip(sharpe, -10, 10)
    
    def render(self, mode='human'):
        """Render environment state."""
        if mode == 'human':
            print(f"Step: {self.current_step}/{self.n_steps}")
            print(f"Position: {self.position}")
            print(f"Z-Score: {self.z_scores[self.current_step]:.3f}")
            print(f"Spread: {self.spread_values[self.current_step]:.6f}")
            print(f"Trades: {self.trades_count}")
            print(f"Cumulative P&L: ${self.cumulative_pnl:.2f}")
            print("-" * 40)


# ============================================================
# DATA LOADER
# ============================================================

class DataLoader:
    """Load and prepare data for RL training."""
    
    @staticmethod
    def generate_training_data(years: int = 3) -> pd.DataFrame:
        """
        Generate realistic training data for RL.
        """
        logger.info(f"📊 Generating {years} years of training data...")
        
        # Generate date range (1-minute intervals)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        all_dates = pd.date_range(start=start_date, end=end_date, freq='1min')
        
        # Filter to trading hours (9:30 AM - 4:00 PM EST)
        hours = np.array([d.hour + d.minute/60 for d in all_dates])
        session_mask = (hours >= 9.5) & (hours <= 16)
        dates = all_dates[session_mask]
        
        n = len(dates)
        
        # Generate mean-reverting spread (Ornstein-Uhlenbeck)
        theta = 0.05
        mu = 0.0
        sigma = 0.002
        
        spread = np.zeros(n)
        spread[0] = np.random.normal(0, 0.001)
        
        for i in range(1, n):
            dt = 1/60
            dW = np.random.normal(0, np.sqrt(dt))
            spread[i] = spread[i-1] + theta * (mu - spread[i-1]) * dt + sigma * dW
        
        # Generate prices
        spx_returns = np.random.normal(0, 0.00015, n)
        ndx_returns = spx_returns + np.random.normal(0, 0.0001, n)
        ndx_returns += np.diff(np.concatenate([[0], spread])) * 0.5
        
        spx_prices = 6000 * np.exp(np.cumsum(spx_returns))
        ndx_prices = 22000 * np.exp(np.cumsum(ndx_returns))
        
        # Calculate Z-score
        z_scores = []
        hist = []
        for s in spread:
            hist.append(s)
            if len(hist) > 60:
                hist.pop(0)
            if len(hist) >= 30:
                mu_local = np.mean(hist)
                sigma_local = np.std(hist)
                if sigma_local > 0:
                    z_scores.append((s - mu_local) / sigma_local)
                else:
                    z_scores.append(0)
            else:
                z_scores.append(0)
        
        df = pd.DataFrame({
            'spx': spx_prices,
            'ndx': ndx_prices,
            'spread': spread,
            'z_score': z_scores
        }, index=dates)
        
        logger.info(f"   ✅ Generated {len(df)} data points")
        logger.info(f"   Spread range: {df['spread'].min():.4f} to {df['spread'].max():.4f}")
        logger.info(f"   Z-score range: {df['z_score'].min():.2f} to {df['z_score'].max():.2f}")
        
        return df
    
    @staticmethod
    def load_data(file_path: str) -> pd.DataFrame:
        """Load data from CSV file."""
        return pd.read_csv(file_path, index_col=0, parse_dates=True)