"""
Sentinel ML Role - Feature Engineering for Reinforcement Learning
Prepares data before agents learn
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SentinelFeatureEngineer:
    """
    Sentinel prepares features for RL agents:
    - Z-Score (Bollinger-like): How far is price from mean?
    - RSI Slope: Is momentum accelerating or slowing down?
    - Volume Z-Score: Volume anomaly detection
    - Trend Strength: Trending vs Ranging
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.last_cycle_time = None
        self.cycle_counter = 0
        self.price_history = {}
        self.volume_history = {}
    
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
        """Standard RSI calculation"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
        slope, intercept, r_value, p_value, std_err = np.polyfit(x, recent_rsi, 1)
        
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
    
    def calculate_trend_strength(self, prices: List[float], period: int = 14) -> float:
        """Simplified ADX - Returns 0-100 (0-25 ranging, 25-50 weak, 50-75 strong, 75+ very strong)"""
        if len(prices) < period + 1:
            return 0.0
        
        moves = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        plus_dm = [max(m, 0) for m in moves]
        minus_dm = [max(-m, 0) for m in moves]
        
        avg_plus = np.mean(plus_dm[-period:]) if plus_dm else 0
        avg_minus = np.mean(minus_dm[-period:]) if minus_dm else 0
        
        tr = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_tr = np.mean(tr[-period:]) if tr else 1
        
        plus_di = 100 * (avg_plus / avg_tr) if avg_tr > 0 else 0
        minus_di = 100 * (avg_minus / avg_tr) if avg_tr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        return round(dx, 2)
    
    def engineer_features(self, symbol: str, price_data: List[Dict]) -> Optional[Dict]:
        """
        Engineer all features for RL state
        Called every 5 minutes by Sentinel
        """
        if len(price_data) < 50:
            return None
        
        closes = [p['close'] for p in price_data]
        highs = [p['high'] for p in price_data]
        lows = [p['low'] for p in price_data]
        volumes = [p['volume'] for p in price_data]
        
        # Calculate RSI history for slope
        rsi_history = []
        for i in range(14, len(closes)):
            rsi_val = self.calculate_rsi(closes[:i+1], 14)
            rsi_history.append(rsi_val)
        
        features = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'current_price': closes[-1],
            
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
            'spread_ratio': round((highs[-1] - lows[-1]) / closes[-1], 4) if closes[-1] > 0 else 0,
            
            # Trend strength
            'trend_strength': self.calculate_trend_strength(closes, 14)
        }
        
        self._store_features(features)
        return features
    
    def _store_features(self, features: Dict):
        """Store engineered features in database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO engineered_features 
                (timestamp, symbol, z_score_20, z_score_50, z_score_200, 
                 rsi_14, rsi_slope_5, rsi_slope_10, volume_zscore, spread_ratio, trend_strength, current_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                features['timestamp'], features['symbol'],
                features['z_score_20'], features['z_score_50'], features['z_score_200'],
                features['rsi_14'], features['rsi_slope_5'], features['rsi_slope_10'],
                features['volume_zscore'], features['spread_ratio'], features['trend_strength'],
                features['current_price']
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not store features: {e}")
