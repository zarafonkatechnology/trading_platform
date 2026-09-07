#!/usr/bin/env python3
"""
COMPLETE REINFORCEMENT LEARNING SYSTEM - Swiss SMI Trading Agents
================================================================
Parts 1-5 Fully Integrated | 5-Minute Cycles | Q-Learning | Feature Engineering

Architecture:
- Part 1: Database Schema for RL Training
- Part 2: Sentinel ML Role - Feature Engineering (Z-Score, RSI Slope, etc.)
- Part 3: Reinforcement Learning Agent (Q-Learning)
- Part 4: 5-Minute Cycle Manager
- Part 5: Complete System Initialization
"""

import sqlite3
import numpy as np
import pandas as pd
import random
import json
import threading
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque
from dataclasses import dataclass
from enum import Enum

# ============================================
# CONFIGURATION
# ============================================

DB_PATH = 'trading_rl.db'
LOG_LEVEL = logging.INFO
CYCLE_INTERVAL_SECONDS = 300  # 5 minutes
BATCH_SIZE = 32
LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.95
EXPLORATION_START = 0.3
EXPLORATION_MIN = 0.05
EXPLORATION_DECAY = 0.995

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - 🧠 RL - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# PART 1: DATABASE SCHEMA FOR RL TRAINING
# ============================================

class RLDatabase:
    """Complete database schema for Reinforcement Learning"""
    
    @staticmethod
    def init_tables():
        """Initialize all RL tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. RL Episodes table
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
        
        # 2. Experience Buffer (every 5-minute cycle)
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
        
        # 3. Policy Weights (learned parameters)
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
        
        # 4. 5-minute cycle metrics
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
        
        # 5. Engineered features table (prepared by Sentinel)
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
                current_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 6. Agent performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                cycle_number INTEGER,
                xp_total INTEGER,
                tokens_total INTEGER,
                trades_count INTEGER,
                wins_count INTEGER,
                win_rate REAL,
                q_table_size INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Part 1: RL Database initialized")
        print("✅ Database tables created")


# ============================================
# PART 2: SENTINEL ML ROLE - FEATURE ENGINEERING
# ============================================

class SentinelFeatureEngineer:
    """
    Sentinel prepares the data before agents learn.
    Key Features for Swiss SMI agents:
    - Z-Score (Bollinger-like): How far is price from mean?
    - RSI Slope: Is momentum accelerating or slowing down?
    - Volume Z-Score: Detects unusual volume spikes
    - Trend Strength: ADX-like metric (0-100)
    """
    
    def __init__(self):
        self.price_history = {}
        self.volume_history = {}
        self.last_features = {}
    
    def calculate_z_score(self, prices: List[float], period: int) -> float:
        """
        Z-Score: How far is the price from the mean?
        Like Bollinger Bands but normalized.
        
        Z-Score = (current_price - mean) / std_dev
        - 0 = at the mean
        - +2 = 2 standard deviations above mean (overbought)
        - -2 = 2 standard deviations below mean (oversold)
        """
        if len(prices) < period:
            return 0.0
        
        recent_prices = prices[-period:]
        mean = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        if std == 0:
            return 0.0
        
        current_price = prices[-1]
        z_score = (current_price - mean) / std
        
        return round(z_score, 4)
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Standard RSI calculation (0-100)"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 1
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_rsi_slope(self, rsi_values: List[float], period: int) -> float:
        """
        RSI Slope: Is momentum accelerating or slowing down?
        
        Positive slope = momentum increasing
        Negative slope = momentum decreasing
        """
        if len(rsi_values) < period:
            return 0.0
        
        recent_rsi = rsi_values[-period:]
        x = np.arange(len(recent_rsi))
        slope, _ = np.polyfit(x, recent_rsi, 1)
        
        return round(slope, 4)
    
    def calculate_volume_zscore(self, volumes: List[int]) -> float:
        """Volume Z-Score: Detects unusual volume spikes"""
        if len(volumes) < 20:
            return 0.0
        
        mean_vol = np.mean(volumes[-20:])
        std_vol = np.std(volumes[-20:])
        
        if std_vol == 0:
            return 0.0
        
        current_vol = volumes[-1]
        return round((current_vol - mean_vol) / std_vol, 4)
    
    def calculate_spread_ratio(self, high: float, low: float, close: float) -> float:
        """(high - low) / close - normalized intraday volatility"""
        if close == 0:
            return 0.0
        return round((high - low) / close, 4)
    
    def calculate_trend_strength(self, prices: List[float], period: int = 14) -> float:
        """
        Trend Strength using simplified ADX calculation
        Returns 0-100: 
        0-25: Ranging market
        25-50: Weak trend
        50-75: Strong trend
        75+: Very strong trend
        """
        if len(prices) < period + 1:
            return 0.0
        
        # Calculate directional movements
        moves = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Positive and negative directional movement
        plus_dm = [max(m, 0) for m in moves]
        minus_dm = [max(-m, 0) for m in moves]
        
        # Smoothed averages
        avg_plus = np.mean(plus_dm[-period:]) if plus_dm else 0
        avg_minus = np.mean(minus_dm[-period:]) if minus_dm else 0
        
        # True Range (simplified)
        tr = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_tr = np.mean(tr[-period:]) if tr else 1
        
        # Directional indicators
        plus_di = 100 * (avg_plus / avg_tr) if avg_tr > 0 else 0
        minus_di = 100 * (avg_minus / avg_tr) if avg_tr > 0 else 0
        
        # DX and simplified ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        return round(dx, 2)
    
    def engineer_features(self, symbol: str, price_data: List[Dict]) -> Optional[Dict]:
        """
        Engineer all features for RL state
        Called by Sentinel every 5 minutes
        """
        if len(price_data) < 50:
            logger.warning(f"Insufficient price data for {symbol}: {len(price_data)} points")
            return None
        
        # Extract price arrays
        closes = [p['close'] for p in price_data]
        highs = [p['high'] for p in price_data]
        lows = [p['low'] for p in price_data]
        volumes = [p['volume'] for p in price_data]
        
        # Calculate RSI history for slope calculation
        rsi_history = []
        for i in range(14, len(closes)):
            rsi_val = self.calculate_rsi(closes[:i+1], 14)
            rsi_history.append(rsi_val)
        
        # Engineered Features
        features = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            
            # Z-Scores (Bollinger-like)
            'z_score_20': self.calculate_z_score(closes, 20),
            'z_score_50': self.calculate_z_score(closes, 50),
            'z_score_200': self.calculate_z_score(closes, 200),
            
            # RSI and Slope (momentum acceleration)
            'rsi_14': self.calculate_rsi(closes, 14),
            'rsi_slope_5': self.calculate_rsi_slope(rsi_history, 5) if len(rsi_history) >= 5 else 0,
            'rsi_slope_10': self.calculate_rsi_slope(rsi_history, 10) if len(rsi_history) >= 10 else 0,
            
            # Volume analysis
            'volume_zscore': self.calculate_volume_zscore(volumes),
            
            # Volatility
            'spread_ratio': self.calculate_spread_ratio(highs[-1], lows[-1], closes[-1]),
            
            # Trend strength
            'trend_strength': self.calculate_trend_strength(closes, 14),
            
            # Current price
            'current_price': closes[-1]
        }
        
        # Store in database
        self._store_features(features)
        
        # Cache for quick access
        self.last_features[symbol] = features
        
        return features
    
    def _store_features(self, features: Dict):
        """Store engineered features in database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO engineered_features 
            (timestamp, symbol, z_score_20, z_score_50, z_score_200, 
             rsi_14, rsi_slope_5, rsi_slope_10, volume_zscore, 
             spread_ratio, trend_strength, current_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            features['timestamp'], features['symbol'],
            features['z_score_20'], features['z_score_50'], features['z_score_200'],
            features['rsi_14'], features['rsi_slope_5'], features['rsi_slope_10'],
            features['volume_zscore'], features['spread_ratio'], 
            features['trend_strength'], features['current_price']
        ))
        conn.commit()
        conn.close()
    
    def get_latest_features(self, symbol: str) -> Optional[Dict]:
        """Get latest engineered features for a symbol"""
        if symbol in self.last_features:
            return self.last_features[symbol]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM engineered_features 
            WHERE symbol = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'timestamp', 'symbol', 'z_score_20', 'z_score_50', 'z_score_200',
                      'rsi_14', 'rsi_slope_5', 'rsi_slope_10', 'volume_zscore', 
                      'spread_ratio', 'trend_strength', 'current_price', 'created_at']
            return dict(zip(columns, row))
        
        return None


# ============================================
# PART 3: REINFORCEMENT LEARNING AGENT
# ============================================

class RLTrader:
    """
    Reinforcement Learning Trading Agent
    Uses Q-Learning to learn optimal trading actions
    """
    
    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.xp = 0
        self.tokens = 1000
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Q-Learning parameters
        self.q_table = {}
        self.learning_rate = LEARNING_RATE
        self.discount_factor = DISCOUNT_FACTOR
        self.exploration_rate = EXPLORATION_START
        self.exploration_min = EXPLORATION_MIN
        self.exploration_decay = EXPLORATION_DECAY
        
        self.actions = ['BUY', 'SELL', 'HOLD']
        self.memory = deque(maxlen=10000)
        self.episode_rewards = []
        
        # Load previous weights if exist
        self._load_weights()
        
        logger.info(f"🤖 Part 3: RL Agent {name} ({agent_type}) initialized")
    
    def _get_state_key(self, features: Dict) -> str:
        """
        Convert continuous features to discrete state for Q-table
        Discretizes: Z-Score, RSI, and Trend Strength
        """
        z_score = int(features.get('z_score_20', 0) * 10)
        rsi = int(features.get('rsi_14', 50) / 10)
        trend = int(features.get('trend_strength', 0) / 20)
        return f"Z{z_score}_R{rsi}_T{trend}"
    
    def act(self, features: Dict, training: bool = True) -> Tuple[str, float]:
        """
        Choose action using epsilon-greedy policy
        
        Args:
            features: Current market features (state)
            training: If True, uses exploration; if False, exploits only
        
        Returns:
            action: 'BUY', 'SELL', or 'HOLD'
            confidence: 0-100 confidence level
        """
        state = self._get_state_key(features)
        
        # Initialize Q-values for new state
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
    
    def learn(self, state_features: Dict, action: str, reward: float, 
              next_state_features: Dict, xp_change: int):
        """
        Update Q-values using Q-learning algorithm
        
        Formula: Q(s,a) = Q(s,a) + α[R + γ max Q(s',a') - Q(s,a)]
        """
        state = self._get_state_key(state_features)
        next_state = self._get_state_key(next_state_features) if next_state_features else state
        
        # Initialize Q-values for new states
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0 for a in self.actions}
        
        # Q-learning update
        current_q = self.q_table[state][action]
        max_future_q = max(self.q_table[next_state].values())
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_future_q - current_q)
        self.q_table[state][action] = new_q
        
        # Store experience in buffer
        self._store_experience(state_features, action, reward, next_state_features, xp_change)
        
        # Update agent statistics
        self.xp += xp_change
        self.tokens = max(0, self.tokens + (xp_change // 2))
        
        if action != 'HOLD':
            self.total_trades += 1
            if reward > 0:
                self.winning_trades += 1
            elif reward < 0:
                self.losing_trades += 1
        
        # Decay exploration rate
        self.exploration_rate = max(self.exploration_min, self.exploration_rate * self.exploration_decay)
    
    def _store_experience(self, state: Dict, action: str, reward: float, 
                          next_state: Dict, xp_change: int):
        """Store experience in database for later mini-batch updates"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_experience_buffer 
            (agent_name, timestamp, state_features, action, reward, xp_change, next_state_features)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.name, datetime.now(), json.dumps(state), action, 
            reward, xp_change, json.dumps(next_state) if next_state else None
        ))
        conn.commit()
        conn.close()
    
    def _load_weights(self):
        """Load previously saved Q-table weights"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT weight_values, version FROM rl_policy_weights 
            WHERE agent_name = ? ORDER BY version DESC LIMIT 1
        ''', (self.name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            self.q_table = json.loads(row[0])
            logger.info(f"  Loaded weights for {self.name} (version {row[1]})")
    
    def save_weights(self, version: int):
        """Save current Q-table as policy weights"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rl_policy_weights (agent_name, layer_name, weight_values, version)
            VALUES (?, ?, ?, ?)
        ''', (self.name, 'q_table', json.dumps(self.q_table), version))
        conn.commit()
        conn.close()
        logger.info(f"💾 Saved weights for {self.name} (version {version})")
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        return {
            'name': self.name,
            'type': self.agent_type,
            'xp': self.xp,
            'tokens': self.tokens,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(win_rate, 1),
            'exploration_rate': round(self.exploration_rate, 3),
            'q_table_size': len(self.q_table)
        }


# ============================================
# PART 4: 5-MINUTE CYCLE MANAGER
# ============================================

class FiveMinuteCycleManager:
    """
    Manages the 5-minute training cycles:
    1. Engineer features from latest market data
    2. Agents take actions based on state
    3. Calculate rewards based on outcomes
    4. Mini-batch update to database
    """
    
    def __init__(self, agents: List[RLTrader], feature_engineer: SentinelFeatureEngineer):
        self.agents = agents
        self.feature_engineer = feature_engineer
        self.cycle_number = 0
        self.is_running = False
        self.last_cycle_time = None
        
        # Market symbols to track
        self.symbols = ['XAU/USD', 'XAG/USD', 'BCO/USD', 'S&P500/USD', 'EURUSD']
        
        # Base prices for simulation (in production, from OANDA API)
        self.base_prices = {
            'XAU/USD': 2385.50,
            'XAG/USD': 28.45,
            'BCO/USD': 89.75,
            'S&P500/USD': 5200.50,
            'EURUSD': 1.0725
        }
        
        logger.info("🔄 Part 4: 5-Minute Cycle Manager initialized")
    
    def start(self):
        """Start the 5-minute cycle loop"""
        self.is_running = True
        thread = threading.Thread(target=self._cycle_loop, daemon=True)
        thread.start()
        logger.info("✅ 5-Minute Cycle Manager started")
    
    def _cycle_loop(self):
        """Main cycle loop - runs every 5 minutes"""
        while self.is_running:
            try:
                self.cycle_number += 1
                cycle_start = datetime.now()
                
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 CYCLE #{self.cycle_number} STARTED at {cycle_start.strftime('%H:%M:%S')}")
                logger.info(f"{'='*70}")
                
                # Step 1: Get market data and engineer features
                features_by_symbol = self._get_engineered_features()
                
                if not features_by_symbol:
                    logger.warning("No features generated, waiting for next cycle")
                    time.sleep(60)
                    continue
                
                # Step 2: Each agent takes action for each symbol
                all_actions = self._collect_agent_actions(features_by_symbol)
                
                # Step 3: Calculate rewards and update agents
                self._process_rewards_and_learn(all_actions)
                
                # Step 4: Mini-batch update from experience buffer
                self._mini_batch_update()
                
                cycle_end = datetime.now()
                duration = (cycle_end - cycle_start).total_seconds()
                
                # Step 5: Store cycle metrics
                self._store_cycle_metrics(cycle_start, cycle_end, duration)
                
                # Step 6: Save agent performance
                self._save_agent_performance()
                
                logger.info(f"✅ CYCLE #{self.cycle_number} COMPLETED in {duration:.1f}s")
                self._print_summary()
                
                # Wait for next cycle (5 minutes)
                wait_time = max(0, CYCLE_INTERVAL_SECONDS - duration)
                logger.info(f"⏳ Waiting {wait_time:.0f}s for next cycle...\n")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)
    
    def _get_engineered_features(self) -> Dict:
        """Get market data and engineer features for all symbols"""
        features_by_symbol = {}
        
        for symbol in self.symbols:
            # Generate simulated price data (100 candles)
            # In production, this would fetch from OANDA API
            price_data = self._generate_price_data(symbol)
            
            # Engineer features using Sentinel
            features = self.feature_engineer.engineer_features(symbol, price_data)
            
            if features:
                features_by_symbol[symbol] = features
                logger.debug(f"  Features for {symbol}: Z={features['z_score_20']:.2f}, "
                           f"RSI={features['rsi_14']:.1f}, Trend={features['trend_strength']:.1f}")
        
        return features_by_symbol
    
    def _generate_price_data(self, symbol: str, num_candles: int = 100) -> List[Dict]:
        """Generate simulated price data for demonstration"""
        base_price = self.base_prices.get(symbol, 100)
        prices = []
        current_price = base_price
        
        for i in range(num_candles):
            # Random walk with slight drift
            change = random.uniform(-0.01, 0.01)
            current_price = current_price * (1 + change)
            
            prices.append({
                'timestamp': datetime.now() - timedelta(minutes=num_candles - i),
                'open': current_price * random.uniform(0.998, 1.002),
                'high': current_price * random.uniform(1.001, 1.005),
                'low': current_price * random.uniform(0.995, 0.999),
                'close': current_price,
                'volume': random.randint(1000, 10000)
            })
        
        return prices
    
    def _collect_agent_actions(self, features_by_symbol: Dict) -> List[Dict]:
        """Have each agent take actions based on features"""
        all_actions = []
        
        for agent in self.agents:
            for symbol, features in features_by_symbol.items():
                action, confidence = agent.act(features, training=True)
                
                action_data = {
                    'agent': agent,
                    'agent_name': agent.name,
                    'symbol': symbol,
                    'action': action,
                    'confidence': confidence,
                    'features': features,
                    'price': features['current_price']
                }
                all_actions.append(action_data)
                
                logger.info(f"  {agent.name} on {symbol}: {action} ({confidence:.0f}%) @ ${features['current_price']:.2f}")
        
        return all_actions
    
    def _process_rewards_and_learn(self, all_actions: List[Dict]):
        """Calculate rewards and update agents via Q-learning"""
        
        for action_data in all_actions:
            # Simulate market outcome (in production, use actual price movement)
            # Random price movement between -2% and +3%
            actual_move_pct = random.uniform(-2, 3)
            actual_move = actual_move_pct / 100
            
            # Calculate reward based on action and market movement
            action = action_data['action']
            reward, xp_change = self._calculate_reward(action, actual_move, action_data['confidence'])
            
            # Update agent using Q-learning
            agent = action_data['agent']
            agent.learn(
                state_features=action_data['features'],
                action=action,
                reward=reward,
                next_state_features=action_data['features'],  # Simplified
                xp_change=xp_change
            )
            
            # Log outcome
            outcome = "WIN" if reward > 0 else "LOSS" if reward < 0 else "NEUTRAL"
            logger.debug(f"    {agent.name}: {action} → {outcome} (reward={reward:.2f}, XP={xp_change:+,d})")
    
    def _calculate_reward(self, action: str, actual_move: float, confidence: float) -> Tuple[float, int]:
        """
        Calculate reward based on action and market movement
        
        Returns:
            reward: Continuous reward value
            xp_change: Discrete XP change for agent
        """
        # Base reward calculations
        if action == 'BUY':
            if actual_move > 0:
                # Profit: positive reward
                reward = min(1.0, actual_move * 10)
                xp_change = 25 + int(actual_move * 200)
            else:
                # Loss: negative penalty
                reward = max(-1.0, actual_move * 10)
                xp_change = -20 + int(actual_move * 100)
        
        elif action == 'SELL':
            if actual_move < 0:
                # Profit on sell (price went down)
                reward = min(1.0, abs(actual_move) * 10)
                xp_change = 25 + int(abs(actual_move) * 200)
            else:
                # Loss on sell (price went up)
                reward = max(-1.0, -actual_move * 10)
                xp_change = -20 - int(actual_move * 100)
        
        else:  # HOLD
            # Small penalty for holding when market moves significantly
            if abs(actual_move) > 0.01:
                reward = -0.05
                xp_change = -5
            else:
                reward = 0
                xp_change = 0
        
        # Bonus for high confidence correct predictions
        if (action == 'BUY' and actual_move > 0) or (action == 'SELL' and actual_move < 0):
            if confidence > 80:
                reward += 0.1
                xp_change += 10
        
        return reward, xp_change
    
    def _mini_batch_update(self):
        """Perform mini-batch update from experience buffer"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for agent in self.agents:
            # Get recent experiences for this agent
            cursor.execute('''
                SELECT state_features, action, reward, next_state_features 
                FROM rl_experience_buffer 
                WHERE agent_name = ? 
                ORDER BY id DESC LIMIT 100
            ''', (agent.name,))
            
            experiences = cursor.fetchall()
            
            if len(experiences) >= BATCH_SIZE:
                # Sample mini-batch
                batch = random.sample(experiences, BATCH_SIZE)
                total_loss = 0
                
                for exp in batch:
                    state = json.loads(exp[0])
                    action = exp[1]
                    reward = exp[2]
                    next_state = json.loads(exp[3]) if exp[3] else state
                    
                    # Q-learning update
                    state_key = agent._get_state_key(state)
                    next_state_key = agent._get_state_key(next_state)
                    
                    if state_key not in agent.q_table:
                        agent.q_table[state_key] = {a: 0 for a in agent.actions}
                    if next_state_key not in agent.q_table:
                        agent.q_table[next_state_key] = {a: 0 for a in agent.actions}
                    
                    current_q = agent.q_table[state_key][action]
                    max_future_q = max(agent.q_table[next_state_key].values())
                    td_target = reward + agent.discount_factor * max_future_q
                    td_error = td_target - current_q
                    
                    agent.q_table[state_key][action] = current_q + agent.learning_rate * td_error
                    total_loss += abs(td_error)
                
                avg_loss = total_loss / BATCH_SIZE
                logger.info(f"  📚 {agent.name}: Mini-batch update complete (loss={avg_loss:.3f})")
        
        conn.close()
    
    def _store_cycle_metrics(self, start_time: datetime, end_time: datetime, duration: float):
        """Store cycle metrics in database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for agent in self.agents:
            cursor.execute('''
                INSERT INTO rl_cycle_metrics 
                (cycle_number, start_time, end_time, agent_name, avg_reward, total_xp, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.cycle_number, start_time, end_time, agent.name, 0, agent.xp, 1))
        
        conn.commit()
        conn.close()
    
    def _save_agent_performance(self):
        """Save agent performance metrics"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for agent in self.agents:
            stats = agent.get_stats()
            win_rate = stats['win_rate']
            
            cursor.execute('''
                INSERT INTO rl_agent_performance 
                (agent_name, cycle_number, xp_total, tokens_total, trades_count, 
                 wins_count, win_rate, q_table_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (agent.name, self.cycle_number, stats['xp'], stats['tokens'],
                  stats['total_trades'], stats['winning_trades'], win_rate, stats['q_table_size']))
        
        conn.commit()
        conn.close()
    
    def _print_summary(self):
        """Print cycle summary to console"""
        logger.info(f"\n📊 CYCLE #{self.cycle_number} SUMMARY:")
        logger.info("-" * 50)
        
        for agent in self.agents:
            stats = agent.get_stats()
            logger.info(f"  {agent.name}: XP={stats['xp']:,} | "
                       f"Trades={stats['total_trades']} | "
                       f"Win Rate={stats['win_rate']}% | "
                       f"Explore={stats['exploration_rate']:.2f}")
        
        logger.info("-" * 50)


# ============================================
# PART 5: COMPLETE SYSTEM INITIALIZATION
# ============================================

class RLSystem:
    """
    Complete Reinforcement Learning Trading System
    Integrates all 5 parts:
    - Database Schema
    - Sentinel Feature Engineering
    - RL Agents (Q-Learning)
    - 5-Minute Cycle Manager
    - System Initialization
    """
    
    def __init__(self):
        print("\n" + "=" * 70)
        print("🧠 COMPLETE REINFORCEMENT LEARNING TRADING SYSTEM")
        print("Swiss SMI Agents | 5-Minute Cycles | Q-Learning")
        print("=" * 70)
        
        # Part 1: Initialize Database
        print("\n[Part 1] Initializing Database...")
        RLDatabase.init_tables()
        print("✅ Database ready")
        
        # Part 2: Initialize Sentinel Feature Engineer
        print("\n[Part 2] Initializing Sentinel Feature Engineer...")
        self.feature_engineer = SentinelFeatureEngineer()
        print("✅ Feature Engineer ready")
        
        # Part 3: Create RL Agents
        print("\n[Part 3] Creating Reinforcement Learning Agents...")
        self.agents = [
            RLTrader("Agent_A", "Trend Follower"),
            RLTrader("Agent_B", "Mean Reversion"),
            RLTrader("Agent_C", "Momentum"),
            RLTrader("Agent_D", "Volatility"),
            RLTrader("Agent_E", "Microstructure")
        ]
        print(f"✅ {len(self.agents)} RL Agents created")
        
        # Part 4: Initialize Cycle Manager
        print("\n[Part 4] Initializing 5-Minute Cycle Manager...")
        self.cycle_manager = FiveMinuteCycleManager(self.agents, self.feature_engineer)
        print("✅ Cycle Manager ready")
        
        # Part 5: System Ready
        print("\n" + "=" * 70)
        print("✅ PART 5: SYSTEM READY")
        print("=" * 70)
        print("\n📋 System Configuration:")
        print(f"   - Cycle Interval: {CYCLE_INTERVAL_SECONDS} seconds (5 minutes)")
        print(f"   - Batch Size: {BATCH_SIZE}")
        print(f"   - Learning Rate: {LEARNING_RATE}")
        print(f"   - Discount Factor: {DISCOUNT_FACTOR}")
        print(f"   - Exploration Start: {EXPLORATION_START}")
        print(f"   - Exploration Min: {EXPLORATION_MIN}")
        print("\n📊 Monitored Symbols:")
        for symbol in self.cycle_manager.symbols:
            print(f"   - {symbol}")
        print("\n🤖 Commands:")
        print("   - Ctrl+C: Stop the system gracefully")
        print("   - System runs automatically every 5 minutes")
        print("=" * 70)
    
    def start(self):
        """Start the complete RL system"""
        logger.info("🚀 Starting RL Trading System...")
        print("\n🟢 SYSTEM RUNNING - Press Ctrl+C to stop\n")
        
        try:
            self.cycle_manager.start()
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the system and save final statistics"""
        print("\n\n" + "=" * 70)
        print("🛑 STOPPING RL TRADING SYSTEM")
        print("=" * 70)
        
        self.cycle_manager.is_running = False
        self._save_final_stats()
        
        print("\n✅ System stopped successfully")
        print("=" * 70)
    
    def _save_final_stats(self):
        """Save final agent statistics and weights"""
        print("\n📊 FINAL AGENT STATISTICS")
        print("-" * 50)
        
        for agent in self.agents:
            stats = agent.get_stats()
            print(f"\n🤖 {stats['name']} ({stats['type']})")
            print(f"   ├─ XP: {stats['xp']:,}")
            print(f"   ├─ Tokens: {stats['tokens']:,}")
            print(f"   ├─ Total Trades: {stats['total_trades']}")
            print(f"   ├─ Wins/Losses: {stats['winning_trades']}/{stats['losing_trades']}")
            print(f"   ├─ Win Rate: {stats['win_rate']}%")
            print(f"   ├─ Q-Table Size: {stats['q_table_size']}")
            print(f"   └─ Exploration Rate: {stats['exploration_rate']:.3f}")
            
            # Save final weights
            agent.save_weights(999)
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for agent in self.agents:
            stats = agent.get_stats()
            cursor.execute('''
                INSERT INTO rl_episodes 
                (agent_name, end_time, total_reward, total_xp_gained, total_trades, win_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (agent.name, datetime.now(), 0, stats['xp'], stats['total_trades'], stats['win_rate']))
        
        conn.commit()
        conn.close()


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    # Create and start the system
    system = RLSystem()
    system.start()
