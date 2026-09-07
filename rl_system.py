#!/usr/bin/env python3
"""
REINFORCEMENT LEARNING SYSTEM for Swiss SMI Trading Agents
- State: Market features (Z-Score, RSI slope, etc.)
- Action: BUY/SELL/HOLD
- Reward: Risk-adjusted returns + exploration bonus
- Every 5 minutes: Mini-batch update with experience replay
"""

import sqlite3
import json
import threading
import time
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

# ===== FIX: Add missing imports =====
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - 🧠 RL - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'trading_system.db'

# ============================================
# PART 1: DATABASE SCHEMA FOR RL TRAINING
# ============================================

class RLDatabase:
    """Database schema for Reinforcement Learning"""
    
    @staticmethod
    def init_tables():
        """Initialize all RL tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # RL Training episodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_reward REAL,
                total_xp_gained INTEGER,
                total_trades INTEGER,
                win_rate REAL,
                sharpe_ratio REAL,
                policy_version TEXT
            )
        ''')
        
        # RL Experience Buffer
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_experience_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                timestamp TIMESTAMP,
                state_features TEXT,
                action TEXT,
                action_probability REAL,
                reward REAL,
                xp_change INTEGER,
                next_state_features TEXT,
                episode_id INTEGER,
                is_terminal INTEGER DEFAULT 0,
                priority REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Agent policy weights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_policy_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                layer_name TEXT,
                weight_values TEXT,
                bias_values TEXT,
                version INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5-minute cycle metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_cycle_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_number INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                agent_name TEXT,
                avg_reward REAL,
                total_xp INTEGER,
                action_distribution TEXT,
                policy_loss REAL,
                value_loss REAL,
                entropy REAL,
                processed INTEGER DEFAULT 0
            )
        ''')
        
        # Engineered features table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engineered_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                symbol TEXT,
                z_score_20 REAL,
                z_score_50 REAL,
                z_score_200 REAL,
                rsi_14 REAL,
                rsi_slope_5 REAL,
                rsi_slope_10 REAL,
                volume_zscore REAL,
                spread_ratio REAL,
                trend_strength REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== ADD: Agent performance tracking =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                timestamp TIMESTAMP,
                win_rate REAL,
                avg_reward REAL,
                total_trades INTEGER,
                q_table_size INTEGER,
                exploration_rate REAL,
                total_xp INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ RL Database tables initialized")


# ============================================
# PART 2: SENTINEL FEATURE ENGINEER (ENHANCED)
# ============================================

class SentinelFeatureEngineer:
    """
    Sentinel prepares the data before agents learn.
    Enhanced with more features and normalization.
    """
    
    def __init__(self):
        self.last_cycle_time = None
        self.cycle_counter = 0
        self.price_history = {}
        self.volume_history = {}
        self.feature_stats = {}  # For normalization
    
    # ===== FIX: Add numpy import fallback =====
    def _np_mean(self, data):
        try:
            return np.mean(data)
        except:
            return sum(data) / len(data) if data else 0
    
    def _np_std(self, data):
        try:
            return np.std(data)
        except:
            mean = self._np_mean(data)
            return (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5 if data else 1
    
    def calculate_z_score(self, prices: List[float], period: int) -> float:
        """Z-Score: How far is the price from the mean?"""
        if len(prices) < period:
            return 0.0
        
        recent_prices = prices[-period:]
        mean = self._np_mean(recent_prices)
        std = self._np_std(recent_prices)
        
        if std == 0:
            return 0.0
        
        current_price = prices[-1]
        return round((current_price - mean) / std, 4)
    
    def calculate_rsi_slope(self, rsi_values: List[float], period: int) -> float:
        """RSI Slope: Is momentum accelerating or slowing down?"""
        if len(rsi_values) < period:
            return 0.0
        
        recent_rsi = rsi_values[-period:]
        
        # Simple linear regression slope
        x = np.arange(len(recent_rsi)) if 'numpy' in globals() else list(range(len(recent_rsi)))
        if 'numpy' in globals():
            slope, intercept = np.polyfit(x, recent_rsi, 1)[:2]
        else:
            # Manual slope calculation
            n = len(recent_rsi)
            sum_x = sum(x)
            sum_y = sum(recent_rsi)
            sum_xy = sum(x[i] * recent_rsi[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        
        return round(slope, 4)
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Standard RSI calculation"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = []
        for i in range(1, len(prices)):
            deltas.append(prices[i] - prices[i-1])
        
        gains = [max(d, 0) for d in deltas]
        losses = [max(-d, 0) for d in deltas]
        
        avg_gain = self._np_mean(gains[-period:]) if gains else 0
        avg_loss = self._np_mean(losses[-period:]) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_volume_zscore(self, volumes: List[int]) -> float:
        """Volume Z-Score: Detects unusual volume spikes"""
        if len(volumes) < 20:
            return 0.0
        
        mean_vol = self._np_mean(volumes[-20:])
        std_vol = self._np_std(volumes[-20:])
        
        if std_vol == 0:
            return 0.0
        
        current_vol = volumes[-1]
        return round((current_vol - mean_vol) / std_vol, 4)
    
    def calculate_spread_ratio(self, high: float, low: float, close: float) -> float:
        """(high - low) / close - normalized volatility"""
        if close == 0:
            return 0.0
        return round((high - low) / close, 4)
    
    def calculate_trend_strength(self, prices: List[float], period: int = 14) -> float:
        """Trend Strength using simplified ADX calculation"""
        if len(prices) < period + 1:
            return 0.0
        
        moves = []
        for i in range(1, len(prices)):
            moves.append(prices[i] - prices[i-1])
        
        plus_dm = [max(m, 0) for m in moves]
        minus_dm = [max(-m, 0) for m in moves]
        
        avg_plus = self._np_mean(plus_dm[-period:]) if plus_dm else 0
        avg_minus = self._np_mean(minus_dm[-period:]) if minus_dm else 0
        
        tr = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_tr = self._np_mean(tr[-period:]) if tr else 1
        
        plus_di = 100 * (avg_plus / avg_tr) if avg_tr > 0 else 0
        minus_di = 100 * (avg_minus / avg_tr) if avg_tr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        return round(dx, 2)
    
    def engineer_features(self, symbol: str, price_data: List[Dict]) -> Dict:
        """Engineer all features for RL state."""
        if len(price_data) < 50:
            return None
        
        closes = [p['close'] for p in price_data]
        highs = [p['high'] for p in price_data]
        lows = [p['low'] for p in price_data]
        volumes = [p['volume'] for p in price_data]
        
        # Calculate RSI values for slope
        rsi_history = []
        for i in range(14, len(closes)):
            rsi_val = self.calculate_rsi(closes[:i+1], 14)
            rsi_history.append(rsi_val)
        
        features = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'z_score_20': self.calculate_z_score(closes, 20),
            'z_score_50': self.calculate_z_score(closes, 50),
            'z_score_200': self.calculate_z_score(closes, 200),
            'rsi_14': self.calculate_rsi(closes, 14),
            'rsi_slope_5': self.calculate_rsi_slope(rsi_history, 5) if len(rsi_history) >= 5 else 0,
            'rsi_slope_10': self.calculate_rsi_slope(rsi_history, 10) if len(rsi_history) >= 10 else 0,
            'volume_zscore': self.calculate_volume_zscore(volumes),
            'spread_ratio': self.calculate_spread_ratio(highs[-1], lows[-1], closes[-1]),
            'trend_strength': self.calculate_trend_strength(closes, 14),
            'current_price': closes[-1],
            'price_change_5': (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0,
            'price_change_10': (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) >= 11 else 0,
        }
        
        self._store_features(features)
        return features
    
    def _store_features(self, features: Dict):
        """Store engineered features in database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO engineered_features 
            (timestamp, symbol, z_score_20, z_score_50, z_score_200, 
             rsi_14, rsi_slope_5, rsi_slope_10, volume_zscore, 
             spread_ratio, trend_strength)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            features['timestamp'], features['symbol'],
            features['z_score_20'], features['z_score_50'], features['z_score_200'],
            features['rsi_14'], features['rsi_slope_5'], features['rsi_slope_10'],
            features['volume_zscore'], features['spread_ratio'], features['trend_strength']
        ))
        conn.commit()
        conn.close()
    
    def get_latest_features(self, symbol: str, limit: int = 1) -> List[Dict]:
        """Get latest engineered features for an agent"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM engineered_features 
            WHERE symbol = ? 
            ORDER BY timestamp DESC LIMIT ?
        ''', (symbol, limit))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in results]


# ============================================
# PART 3: REINFORCEMENT LEARNING AGENT (ENHANCED)
# ============================================

class RLAgent:
    """
    Reinforcement Learning Agent for Trading
    Enhanced with risk-adjusted rewards and exploration bonus.
    """
    
    def __init__(self, name: str, feature_engineer: SentinelFeatureEngineer):
        self.name = name
        self.feature_engineer = feature_engineer
        
        # Q-learning parameters
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.exploration_rate = 0.2
        self.exploration_decay = 0.995
        self.exploration_min = 0.05
        
        # Experience memory
        self.memory = deque(maxlen=10000)
        
        # Episode tracking
        self.current_episode = []
        self.total_reward = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        
        # Actions
        self.actions = ['BUY', 'SELL', 'HOLD']
        
        # Performance tracking
        self.performance_history = deque(maxlen=100)
        
        # ===== FIX: Add reward scaling =====
        self.reward_scale = 1.0
        
        # ===== FIX: Add action counts for exploration bonus =====
        self.action_counts = {a: 0 for a in self.actions}
        
        logger.info(f"🧠 RL Agent {name} initialized")
    
    def get_state_key(self, features: Dict) -> str:
        """Convert continuous features to discrete state for Q-learning"""
        z_score = features.get('z_score_20', 0)
        rsi = features.get('rsi_14', 50)
        trend = features.get('trend_strength', 0)
        volume = features.get('volume_zscore', 0)
        
        # Discretize
        z_bucket = max(-5, min(5, int(z_score)))
        rsi_bucket = int(rsi / 10)  # 0-10
        trend_bucket = int(trend / 20)  # 0-5
        vol_bucket = max(-3, min(3, int(volume)))
        
        return f"z{z_bucket}_r{rsi_bucket}_t{trend_bucket}_v{vol_bucket}"
    
    def get_action(self, features: Dict) -> Tuple[str, float]:
        """
        Choose action using epsilon-greedy policy with exploration bonus.
        """
        state = self.get_state_key(features)
        
        # Initialize state if not exists
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        
        # ===== FIX: Exploration with bonus for under-explored actions =====
        if random.random() < self.exploration_rate:
            # Choose action with exploration bonus
            action = self._choose_action_with_exploration_bonus(state)
            confidence = 50 + random.randint(0, 30)
            return action, confidence
        
        # Exploitation: best known action
        best_action = max(self.q_table[state], key=lambda a: self.q_table[state][a] + self._get_exploration_bonus(state, a))
        confidence = 60 + (self.q_table[state][best_action] * 10)
        
        return best_action, min(95, confidence)
    
    def _choose_action_with_exploration_bonus(self, state: str) -> str:
        """Choose action with exploration bonus for under-explored actions."""
        counts = [self.action_counts[a] for a in self.actions]
        min_count = min(counts) if counts else 0
        
        # Find least explored actions
        least_explored = [a for a, c in zip(self.actions, counts) if c == min_count]
        
        # If all actions equally explored, choose randomly
        if len(least_explored) == len(self.actions):
            return random.choice(self.actions)
        
        return random.choice(least_explored)
    
    def _get_exploration_bonus(self, state: str, action: str) -> float:
        """Bonus for exploring under-explored state-action pairs."""
        count = self.action_counts.get(action, 0)
        return 0.1 / (count + 1)
    
    def update_from_reward(self, state_features: Dict, action: str, 
                           reward: float, next_state_features: Dict, 
                           xp_change: int):
        """
        Update Q-values based on reward with risk adjustment.
        """
        # ===== FIX: Scale reward =====
        scaled_reward = reward * self.reward_scale
        
        state = self.get_state_key(state_features)
        next_state = self.get_state_key(next_state_features) if next_state_features else state
        
        # Initialize if not exists
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0 for a in self.actions}
        
        # Current Q-value
        current_q = self.q_table[state].get(action, 0)
        
        # Max future Q-value with exploration bonus
        max_future_q = max(self.q_table[next_state].values())
        
        # ===== FIX: Risk-adjusted TD target =====
        # Add penalty for high variance actions
        action_variance = self._get_action_variance(action)
        risk_penalty = action_variance * 0.1
        
        td_target = scaled_reward + self.discount_factor * max_future_q - risk_penalty
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (td_target - current_q)
        self.q_table[state][action] = new_q
        
        # Update action count
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        
        # Store experience
        self._store_experience(state_features, action, reward, next_state_features, xp_change)
        
        # Update totals
        self.total_reward += reward
        if action != 'HOLD':
            self.total_trades += 1
            if reward > 0:
                self.wins += 1
            else:
                self.losses += 1
        
        # Decay exploration rate
        self.exploration_rate *= self.exploration_decay
        self.exploration_rate = max(self.exploration_min, self.exploration_rate)
    
    def _get_action_variance(self, action: str) -> float:
        """Calculate variance for action (higher = more risky)."""
        action_risk = {
            'BUY': 0.3,
            'SELL': 0.3,
            'HOLD': 0.05
        }
        return action_risk.get(action, 0.1)
    
    def _store_experience(self, state: Dict, action: str, reward: float, 
                          next_state: Dict, xp_change: int):
        """Store experience in database buffer."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_experience_buffer 
            (agent_name, timestamp, state_features, action, 
             action_probability, reward, xp_change, next_state_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.name, datetime.now().isoformat(), json.dumps(state), action,
            self.exploration_rate, reward, xp_change, json.dumps(next_state) if next_state else None
        ))
        conn.commit()
        conn.close()
    
    def end_episode(self):
        """End current episode and save metrics."""
        if len(self.current_episode) == 0:
            return
        
        total_trades = self.total_trades
        win_rate = self.wins / total_trades if total_trades > 0 else 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_episodes 
            (agent_name, start_time, end_time, total_reward, total_xp_gained, total_trades, win_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.name, 
            self.current_episode[0].get('timestamp', datetime.now()),
            datetime.now(), 
            self.total_reward, 
            self.total_reward * 10,
            self.total_trades, 
            win_rate
        ))
        conn.commit()
        conn.close()
        
        # Reset episode
        self.current_episode = []
        self.total_reward = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        
        logger.info(f"📊 Episode ended for {self.name}: Reward={self.total_reward:.2f}, Win Rate={win_rate:.1%}")
    
    def get_best_action_for_state(self, features: Dict) -> str:
        """Get best action without exploration (for live trading)."""
        state = self.get_state_key(features)
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        return max(self.q_table[state], key=lambda a: self.q_table[state][a])
    
    def get_q_table_size(self) -> int:
        return len(self.q_table)
    
    def save_weights(self, version: int):
        """Save learned Q-table as policy weights."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_policy_weights (agent_name, layer_name, weight_values, version)
            VALUES (?, ?, ?, ?)
        ''', (self.name, 'q_table', json.dumps(self.q_table), version))
        conn.commit()
        conn.close()
        logger.info(f"💾 Saved weights for {self.name}, version {version}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for the agent."""
        total_trades = self.total_trades
        win_rate = self.wins / total_trades if total_trades > 0 else 0
        
        return {
            'agent': self.name,
            'total_reward': self.total_reward,
            'total_trades': total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'q_table_size': self.get_q_table_size(),
            'exploration_rate': self.exploration_rate,
            'action_counts': self.action_counts
        }


# ============================================
# PART 4: RL TRAINING CYCLE (ENHANCED)
# ============================================

class RLTrainer:
    """Manages RL training cycles every 5 minutes."""
    
    def __init__(self, agents: List[RLAgent], feature_engineer: SentinelFeatureEngineer):
        self.agents = agents
        self.feature_engineer = feature_engineer
        self.cycle_number = 0
        self.is_running = False
        self.trade_history = []
        self.agent_performance = {a.name: [] for a in agents}
    
    def start(self):
        """Start the 5-minute training cycle."""
        self.is_running = True
        thread = threading.Thread(target=self._training_loop, daemon=True)
        thread.start()
        logger.info("🔄 RL Training started (every 5 minutes)")
    
    def _training_loop(self):
        """Main training loop - runs every 5 minutes."""
        while self.is_running:
            try:
                self.cycle_number += 1
                cycle_start = datetime.now()
                
                logger.info(f"📚 RL Training Cycle #{self.cycle_number} started")
                
                # Run training for all agents
                for agent in self.agents:
                    self._train_agent(agent)
                    self._update_performance(agent)
                
                cycle_end = datetime.now()
                duration = (cycle_end - cycle_start).total_seconds()
                
                # Store cycle metrics
                self._store_cycle_metrics(cycle_start, cycle_end, duration)
                
                logger.info(f"✅ Cycle #{self.cycle_number} completed in {duration:.1f}s")
                
                # Wait for next cycle (5 minutes)
                time.sleep(300 - min(duration, 290))
                
            except Exception as e:
                logger.error(f"Training cycle error: {e}")
                time.sleep(60)
    
    def _train_agent(self, agent: RLAgent):
        """Train a single agent using experience replay with prioritized sampling."""
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT state_features, action, reward, next_state_features, priority
            FROM rl_experience_buffer 
            WHERE agent_name = ? 
            ORDER BY priority DESC, id DESC LIMIT 100
        ''', (agent.name,))
        
        experiences = cursor.fetchall()
        conn.close()
        
        if len(experiences) < 10:
            logger.info(f"  {agent.name}: Not enough experiences ({len(experiences)}/10)")
            return
        
        # ===== FIX: Prioritized experience replay =====
        priorities = [exp[4] for exp in experiences]
        total_priority = sum(priorities) if priorities else 1
        weights = [p / total_priority for p in priorities]
        
        # Sample with priority
        batch_size = min(32, len(experiences))
        batch_indices = np.random.choice(len(experiences), batch_size, p=weights, replace=False)
        batch = [experiences[i] for i in batch_indices]
        
        total_loss = 0
        for exp in batch:
            state = json.loads(exp[0])
            action = exp[1]
            reward = exp[2]
            next_state = json.loads(exp[3]) if exp[3] else None
            priority = exp[4]
            
            # Update Q-value with risk adjustment
            state_key = agent.get_state_key(state)
            next_state_key = agent.get_state_key(next_state) if next_state else state_key
            
            if state_key not in agent.q_table:
                agent.q_table[state_key] = {a: 0 for a in agent.actions}
            
            current_q = agent.q_table[state_key].get(action, 0)
            
            if next_state_key not in agent.q_table:
                agent.q_table[next_state_key] = {a: 0 for a in agent.actions}
            max_future_q = max(agent.q_table[next_state_key].values())
            
            td_target = reward + agent.discount_factor * max_future_q
            td_error = td_target - current_q
            
            agent.q_table[state_key][action] = current_q + agent.learning_rate * td_error
            total_loss += abs(td_error)
        
        avg_loss = total_loss / batch_size
        
        # Save weights every 10 cycles
        if self.cycle_number % 10 == 0:
            agent.save_weights(self.cycle_number)
        
        logger.info(f"  {agent.name}: Trained on {batch_size} samples, loss={avg_loss:.3f}, Q-size={agent.get_q_table_size()}")
    
    def _update_performance(self, agent: RLAgent):
        """Update agent performance metrics."""
        summary = agent.get_performance_summary()
        self.agent_performance[agent.name].append(summary)
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_agent_performance 
            (agent_name, timestamp, win_rate, avg_reward, total_trades, 
             q_table_size, exploration_rate, total_xp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent.name, datetime.now().isoformat(),
            summary['win_rate'], summary['total_reward'] / max(1, summary['total_trades']),
            summary['total_trades'], summary['q_table_size'],
            summary['exploration_rate'], summary['total_reward'] * 10
        ))
        conn.commit()
        conn.close()
    
    def _store_cycle_metrics(self, start_time: datetime, end_time: datetime, duration: float):
        """Store training cycle metrics in database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for agent in self.agents:
            summary = agent.get_performance_summary()
            cursor.execute('''
                INSERT INTO rl_cycle_metrics 
                (cycle_number, start_time, end_time, agent_name, avg_reward, 
                 total_xp, action_distribution, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.cycle_number, start_time, end_time, agent.name,
                summary['total_reward'] / max(1, summary['total_trades']),
                summary['total_reward'] * 10,
                json.dumps(summary['action_counts']),
                1
            ))
        
        conn.commit()
        conn.close()


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🧠 REINFORCEMENT LEARNING SYSTEM")
    print("Swiss SMI Trading Agents")
    print("=" * 60)
    
    # Initialize database
    RLDatabase.init_tables()
    
    # Initialize Sentinel feature engineer
    sentinel_features = SentinelFeatureEngineer()
    
    # ===== FIX: Create 9 agents matching your system =====
    agents = [
        RLAgent("Agent_X", sentinel_features),
        RLAgent("Agent_D", sentinel_features),
        RLAgent("Agent_R", sentinel_features),
        RLAgent("Agent_Q", sentinel_features),
        RLAgent("Agent_H", sentinel_features),
        RLAgent("Agent_G", sentinel_features),
        RLAgent("Agent_M", sentinel_features),
        RLAgent("Agent_I", sentinel_features),
        RLAgent("Agent_W", sentinel_features),
    ]
    
    # Create trainer
    trainer = RLTrainer(agents, sentinel_features)
    
    # Start training
    trainer.start()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 RL System stopped")