"""
ADVANCED TRADING STRATEGY
With Volume Confirmation, Trend Filter, Support/Resistance, News Filter, and DOLLAR ENGINE
"""
import sys
import os
import logging
import time
import json
import math
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
from filter_data_manager import FilterDataManager
import random
# At the top of advanced_trading_strategy.py
from zscore_engine import SingleZScoreEngine

# advanced_trading_strategy.py - ADD THESE IMPORTS AT THE TOP
# ===== AGENT IMPORTS =====
from agent_u_liquidity import AgentU_Liquidity
from agent_p_crosspair import AgentP_CrossPair
from agent_d_bbands import AgentD_BBands  # ← CHANGE THIS
from core.ewma_zscore import EWMAZScore
# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import core modules
from core.price_service import price_service
from core.risk_manager import RiskManager
from core.signal_service import signal_service
LOG_LEVEL = 2
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleHourlyTrendFilter:
    """
    Simple 1-hour trend check.
    Stores both price and timestamp for accurate 1-hour comparison.
    """
    
    def __init__(self, lookback=20):
        self.lookback = lookback
        # ✅ Store tuples of (timestamp, price)
        self.price_history = {}  # symbol -> deque of (timestamp, price) tuples
    
    def update_price(self, symbol: str, price: float):
        """Update price with current timestamp"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        # ✅ Store tuple (timestamp, price)
        self.price_history[symbol].append((datetime.now(), price))
    
    def get_price_1h_ago(self, symbol: str) -> Optional[float]:
        """Find closest price to 1 hour ago"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return None
        
        now = datetime.now()
        target_time = now - timedelta(hours=1)
        
        # ✅ Iterate over tuples correctly
        closest_price = None
        min_diff = float('inf')
        
        for ts, price in self.price_history[symbol]:
            diff = abs((ts - target_time).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_price = price
        
        return closest_price
    
    def check_trend(self, symbol: str, action: str) -> Dict:
        """
        Simple trend check with accurate 1-hour comparison.
        
        Args:
            symbol: Trading symbol
            action: 'BUY' or 'SELL'
            
        Returns:
            Dict with 'allowed' (bool) and 'message' (str)
        """
        # ✅ Get prices from stored tuples
        if symbol not in self.price_history:
            return {'allowed': True, 'message': 'No history yet'}
        
        # Extract prices from tuples
        prices = [price for _, price in self.price_history[symbol]]
        
        if len(prices) < 4:
            return {'allowed': True, 'message': f'Building history: {len(prices)}/4'}
        
        current = prices[-1]
        one_hour_ago = self.get_price_1h_ago(symbol)
        
        if one_hour_ago is None:
            # Fallback: use 4th last price
            one_hour_ago = prices[-4] if len(prices) >= 4 else prices[0]
        
        # 0.15% threshold (0.9985 = -0.15%, 1.0015 = +0.15%)
        if action == 'BUY':
            if current < one_hour_ago * 0.9985:
                return {
                    'allowed': False,
                    'message': f'1H downtrend: {current:.5f} < {one_hour_ago:.5f} * 0.9985'
                }
            return {
                'allowed': True,
                'message': f'1H supports BUY: {current:.5f} >= {one_hour_ago:.5f} * 0.9985'
            }
        
        elif action == 'SELL':
            if current > one_hour_ago * 1.0015:
                return {
                    'allowed': False,
                    'message': f'1H uptrend: {current:.5f} > {one_hour_ago:.5f} * 1.0015'
                }
            return {
                'allowed': True,
                'message': f'1H supports SELL: {current:.5f} <= {one_hour_ago:.5f} * 1.0015'
            }
        
        return {'allowed': True, 'message': 'No action'}
    
    def get_trend_status(self, symbol: str) -> Dict:
        """Get detailed trend status for a symbol"""
        if symbol not in self.price_history:
            return {
                'has_history': False,
                'samples': 0,
                'current_price': 0,
                'price_1h_ago': 0,
                'change_pct': 0,
                'trend': 'NEUTRAL'
            }
        
        prices = [price for _, price in self.price_history[symbol]]
        if not prices:
            return {'has_history': False, 'samples': 0}
        
        current = prices[-1]
        one_hour_ago = self.get_price_1h_ago(symbol) or prices[-4] if len(prices) >= 4 else prices[0]
        
        change_pct = ((current - one_hour_ago) / one_hour_ago) * 100 if one_hour_ago > 0 else 0
        
        if change_pct > 0.15:
            trend = 'UP'
        elif change_pct < -0.15:
            trend = 'DOWN'
        else:
            trend = 'SIDEWAYS'
        
        return {
            'has_history': True,
            'samples': len(prices),
            'current_price': current,
            'price_1h_ago': one_hour_ago,
            'change_pct': change_pct,
            'trend': trend
        }
# ============================================================
# 1. DOLLAR ENGINE - USD Strength Index
# ============================================================

class DollarEngine:
    """
    Dollar Engine analyzes USD strength across major pairs.
    Filters forex signals based on USD direction.
    """
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.price_history = {}  # pair -> deque of prices
        self.usd_index = 100.0
        self.usd_strength = 0.0  # -100 to +100
        self.usd_direction = 'NEUTRAL'  # 'STRONG', 'WEAK', 'NEUTRAL'
        self.last_update = 0
        
        # Major pairs and their correlation with USD
        self.pairs = {
            'EURUSD': -1,   # Inverse correlation
            'GBPUSD': -1,   # Inverse correlation
            'USDJPY': 1,    # Direct correlation
            'USDCHF': 1,    # Direct correlation
            'AUDUSD': -1,   # Inverse correlation
            'USDCAD': 1,    # Direct correlation
            'NZDUSD': -1,   # Inverse correlation
        }
        
        self.weights = {
            'EURUSD': 0.25,
            'USDJPY': 0.20,
            'GBPUSD': 0.15,
            'USDCHF': 0.10,
            'AUDUSD': 0.10,
            'USDCAD': 0.10,
            'NZDUSD': 0.10
        }
        
        # Cross pairs (for reference only)
        self.cross_pairs = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
    
    def _get_weight(self, pair: str) -> float:
        """Get weight for each pair"""
        return self.weights.get(pair, 0.10)
    
    def update_prices(self, prices: Dict):
        """Update price history for all pairs"""
        for pair in self.pairs.keys():
            if pair in prices and prices[pair] > 0:
                if pair not in self.price_history:
                    self.price_history[pair] = deque(maxlen=self.lookback)
                self.price_history[pair].append(prices[pair])
        
        # Calculate USD Index
        self._calculate_usd_index(prices)
    
    def _calculate_usd_index(self, prices: Dict):
        """Calculate USD strength index"""
        # Need at least 5 samples for each pair
        if not self.price_history:
            return
        
        total_change = 0.0
        total_weight = 0.0
        
        for pair, direction in self.pairs.items():
            if pair in self.price_history and len(self.price_history[pair]) >= 5:
                history = list(self.price_history[pair])
                # ✅ FIXED: Proper 5-period change check
                change = (history[-1] - history[-5]) / history[-5]
                # Apply direction (inverse correlation gives negative)
                weighted_change = change * direction * 100
                weight = self._get_weight(pair)
                total_change += weighted_change * weight
                total_weight += weight
        
        if total_weight > 0:
            self.usd_strength = total_change / total_weight
            self.usd_strength = max(-100, min(100, self.usd_strength))
            
            # Determine direction with hysteresis (avoid flickering)
            if self.usd_strength > 0.5:
                self.usd_direction = 'STRONG'
            elif self.usd_strength < -0.5:
                self.usd_direction = 'WEAK'
            else:
                self.usd_direction = 'NEUTRAL'
            
            # Calculate USD Index (normalized)
            self.usd_index = 100 + self.usd_strength * 2
            
            self.last_update = time.time()
    
    def get_status(self) -> Dict:
        """Get current USD engine status"""
        return {
            'usd_index': self.usd_index,
            'usd_strength': self.usd_strength,
            'usd_direction': self.usd_direction,
            'last_update': datetime.fromtimestamp(self.last_update).strftime('%H:%M:%S') if self.last_update else 'Never'
        }
    
    def check_signal(self, symbol: str, signal_action: str) -> Dict:
        """
        Check if signal aligns with USD direction.
        
        USD STRONG:
        - BUY: USDJPY, USDCHF, USDCAD (direct pairs)
        - SELL: EURUSD, GBPUSD, AUDUSD, NZDUSD (inverse pairs)
        
        USD WEAK:
        - BUY: EURUSD, GBPUSD, AUDUSD, NZDUSD (inverse pairs)
        - SELL: USDJPY, USDCHF, USDCAD (direct pairs)
        """
        # ===== 1. NEUTRAL: Always allow trades =====
        if self.usd_direction == 'NEUTRAL':
            return {
                'aligned': True,
                'usd_direction': self.usd_direction,
                'usd_strength': self.usd_strength,
                'message': f'✅ USD {self.usd_direction} - no direction bias'
            }
        
        # ===== 2. USD PAIRS (direct correlation) =====
        if symbol.startswith('USD'):
            if self.usd_direction == 'STRONG' and signal_action == 'BUY':
                return {
                    'aligned': True,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'✅ BUY aligns with USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
            elif self.usd_direction == 'WEAK' and signal_action == 'SELL':
                return {
                    'aligned': True,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'✅ SELL aligns with USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
            else:
                return {
                    'aligned': False,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'❌ {signal_action} against USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
        
        # ===== 3. QUOTE PAIRS (inverse correlation) =====
        elif symbol.endswith('USD'):
            if self.usd_direction == 'STRONG' and signal_action == 'SELL':
                return {
                    'aligned': True,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'✅ SELL aligns with USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
            elif self.usd_direction == 'WEAK' and signal_action == 'BUY':
                return {
                    'aligned': True,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'✅ BUY aligns with USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
            else:
                return {
                    'aligned': False,
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f'❌ {signal_action} against USD {self.usd_direction} (strength: {self.usd_strength:.1f})'
                }
        
        # ===== 4. CROSS PAIRS (EURGBP, EURJPY, etc.) =====
        elif symbol in self.cross_pairs:
            return self._check_cross_pair(symbol, signal_action)
        
        # ===== 5. NON-FOREX (Indices, Metals, Energy) =====
        else:
            return {
                'aligned': True,
                'usd_direction': self.usd_direction,
                'usd_strength': self.usd_strength,
                'message': 'Non-forex symbol - USD engine not applicable'
            }
    
    def _check_cross_pair(self, symbol: str, signal_action: str) -> Dict:
        """
        ✅ IMPROVED: Cross pair logic with pair-specific behavior
        """
        # Extract base and quote currencies
        # EURGBP → base=EUR, quote=GBP
        base = symbol[:3]
        quote = symbol[3:]
        
        # Get USD correlation for each currency (simplified)
        usd_correlation = {
            'EUR': -0.8,  # EUR inverse to USD
            'GBP': -0.7,  # GBP inverse to USD
            'JPY': 0.6,   # JPY direct to USD
            'CAD': 0.7,   # CAD direct to USD
            'AUD': -0.6,  # AUD inverse to USD
            'NZD': -0.5,  # NZD inverse to USD
            'CHF': 0.8,   # CHF direct to USD
        }
        
        base_corr = usd_correlation.get(base, 0)
        quote_corr = usd_correlation.get(quote, 0)
        
        # Net USD effect on cross pair
        # If USD strengthens, base weakens (if base_corr < 0) and quote weakens (if quote_corr < 0)
        net_effect = base_corr - quote_corr  # Positive = USD strength pushes pair UP
        
        # Determine expected direction
        if self.usd_direction == 'STRONG' and net_effect > 0:
            expected = 'BUY'
        elif self.usd_direction == 'STRONG' and net_effect < 0:
            expected = 'SELL'
        elif self.usd_direction == 'WEAK' and net_effect > 0:
            expected = 'SELL'
        elif self.usd_direction == 'WEAK' and net_effect < 0:
            expected = 'BUY'
        else:
            expected = 'NEUTRAL'
        
        # Check alignment
        aligned = (expected == signal_action) or (expected == 'NEUTRAL')
        
        return {
            'aligned': aligned,
            'usd_direction': self.usd_direction,
            'usd_strength': self.usd_strength,
            'message': f"{'✅' if aligned else '❌'} USD {self.usd_direction} - expected {expected}, signal {signal_action}"
        }
    
    def get_pair_direction(self, symbol: str) -> Tuple[str, float]:
        """
        ✅ FIXED: Get expected direction based on USD engine.
        Returns: (expected_direction, confidence 0-100)
        """
        if self.usd_direction == 'NEUTRAL':
            return 'NEUTRAL', 0
        
        # Use absolute strength as confidence (0-100 scale)
        confidence = min(100, abs(self.usd_strength) * 2)  # 0.5 → 1%, 50 → 100%
        
        if symbol.startswith('USD'):
            # Direct pairs
            if self.usd_direction == 'STRONG':
                return 'BUY', confidence
            else:
                return 'SELL', confidence
        
        elif symbol.endswith('USD'):
            # Inverse pairs
            if self.usd_direction == 'STRONG':
                return 'SELL', confidence
            else:
                return 'BUY', confidence
        
        elif symbol in self.cross_pairs:
            # Cross pairs - use simplified correlation
            base = symbol[:3]
            quote = symbol[3:]
            usd_correlation = {'EUR': -0.8, 'GBP': -0.7, 'JPY': 0.6, 'CAD': 0.7, 'AUD': -0.6, 'NZD': -0.5, 'CHF': 0.8}
            net_effect = usd_correlation.get(base, 0) - usd_correlation.get(quote, 0)
            
            if self.usd_direction == 'STRONG':
                return ('BUY' if net_effect > 0 else 'SELL'), confidence * 0.7
            else:
                return ('SELL' if net_effect > 0 else 'BUY'), confidence * 0.7
        
        return 'NEUTRAL', 0
# ============================================================
# 6. Z-SCORE ENGINE WITH THRESHOLDS - FIXED
# ============================================================

from collections import deque
import math
from typing import Dict, Tuple, Optional

class ZScoreEngineWithThresholds:
    """Z-Score Engine with Rolling Window (Option 1)"""
    
    def __init__(self, lookback: int = 50, entry_threshold: float = 2.0, exit_threshold: float = 0.5):
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        
        # Price history and statistics
        self.price_history = {}
        self.mean = {}
        self.std = {}
        self.z_score = {}
        self.samples = {}
        
        # Rolling window std history for adaptive thresholds
        self._std_history = {}
        
        # Asset class definitions (FIX: defined locally)
        self.forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
                           'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
        self.indices = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', 
                        '#FTSE100', '#NIKKEI225', '#AMAZON', '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD' ]
        self.metals = ['GOLD', 'SILVER']
        self.energy = ['BRENT_OIL', 'CrudeOIL']
        
        # Symbol-specific thresholds
        self.thresholds = {
            # Indices
            '#NASDAQ100': {'entry': 2.7, 'exit': 0.5},
            '#DJ30': {'entry': 2.5, 'exit': 0.5},
            '#S&P500': {'entry': 2.5, 'exit': 0.5},
            '#RUSS2000': {'entry': 2.7, 'exit': 0.5},
            '#CAC40': {'entry': 2.2, 'exit': 0.5},
            '#DAX40': {'entry': 2.5, 'exit': 0.5},
            '#FTSE100': {'entry': 2.7, 'exit': 0.5},
            '#NIKKEI225': {'entry': 2.2, 'exit': 0.5},
            # NEW INDICES - Stock/Equity indices need wider thresholds (more volatile)
            '#AMAZON': {'entry': 2.5, 'exit': 0.5},
            "#MICROSOFT": {'entry': 2.5, 'exit': 0.5},
            "#VISA": {'entry': 2.5, 'exit': 0.5},
            "#MASTERCARD": {'entry': 2.5, 'exit': 0.5},
            '#APPLE': {'entry': 2.5, 'exit': 0.5},
            '#SPACEX': {'entry': 2.7, 'exit': 0.6},  # High volatility
            # Metals
            'GOLD': {'entry': 2.0, 'exit': 0.5},
            'SILVER': {'entry': 2.0, 'exit': 0.5},
            # Energy
            'BRENT_OIL': {'entry': 2.0, 'exit': 0.5},
            'CrudeOIL': {'entry': 2.0, 'exit': 0.5},
            # Forex Majors
            'EURUSD': {'entry': 1.8, 'exit': 0.4},
            'GBPUSD': {'entry': 1.8, 'exit': 0.4},
            'USDJPY': {'entry': 1.8, 'exit': 0.4},
            'USDCHF': {'entry': 1.6, 'exit': 0.4},
            'AUDUSD': {'entry': 1.8, 'exit': 0.4},
            'USDCAD': {'entry': 1.8, 'exit': 0.4},
            'NZDUSD': {'entry': 1.8, 'exit': 0.4},
            # Forex Crosses
            'EURGBP': {'entry': 2.0, 'exit': 0.4},
            'EURJPY': {'entry': 1.6, 'exit': 0.4},
            'EURCAD': {'entry': 1.6, 'exit': 0.4},
            'EURNZD': {'entry': 1.6, 'exit': 0.4},
            'EURCHF': {'entry': 1.8, 'exit': 0.4},
            # Dollar Index
            # '#DOLLAR_IND': {'entry': 2.2, 'exit': 0.5}
        }
        self.regime_detector = MarketRegimeDetector(lookback=50)  # ← This exists
        self.trend_multiplier = 0.7
        self.counter_multiplier = 1.5
    
    def get_thresholds(self, symbol: str) -> Tuple[float, float]:
        """Get symbol-specific thresholds"""
        if symbol in self.thresholds:
            return self.thresholds[symbol].get('entry', self.entry_threshold), \
                   self.thresholds[symbol].get('exit', self.exit_threshold)
        return self.entry_threshold, self.exit_threshold
    # Add this method to ZScoreEngineWithThresholds class

    def update_price(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        self.price_history[symbol].append(price)
        self.samples[symbol] = len(self.price_history[symbol])
    
    def get_adaptive_threshold(self, symbol: str) -> Tuple[float, float]:
        """Get adaptive thresholds based on rolling volatility"""
        base_entry, base_exit = self.get_thresholds(symbol)
        
        # ✅ FIX: Proper indentation (4 spaces)
        if symbol not in self._std_history or len(self._std_history[symbol]) < 10:
            return base_entry, base_exit
        
        # Calculate average std
        avg_std = sum(self._std_history[symbol]) / len(self._std_history[symbol])
        current_std = self.std.get(symbol, 0.001)
        
        # Volatility ratio
        vol_ratio = current_std / avg_std if avg_std > 0 else 1.0
        
        # Adjust thresholds
        if vol_ratio > 1.5:
            entry = base_entry * min(1.3, vol_ratio * 0.8)
            exit_val = base_exit * min(1.3, vol_ratio * 0.8)
        elif vol_ratio < 0.7:
            entry = base_entry * max(0.7, vol_ratio * 0.8)
            exit_val = base_exit * max(0.7, vol_ratio * 0.8)
        else:
            entry = base_entry
            exit_val = base_exit
        
        return round(entry, 2), round(exit_val, 2)
    
    def get_lookback(self, symbol: str) -> int:
        """Get appropriate lookback based on asset class"""
        # ✅ FIX: Use local definitions
        if symbol in self.forex_pairs:
            return 50  # 12.5 hours with M15
        elif symbol in self.indices:
            return 100  # 25 hours - more volatile
        elif symbol in self.metals:
            return 75  # 18.75 hours
        elif symbol in self.energy:
            return 50  # 12.5 hours
        else:
            return 50  # Default
    
    def calculate_zscore(self, symbol: str, price: float) -> Dict:
        """
        Calculate Z-Score with adaptive thresholds based on market regime.
        Phase 1 implementation - only adaptive thresholds, no divergence/hysteresis yet.
        """
        # Update price history
        self.update_price(symbol, price)
        
        # Update regime detector
        self.regime_detector.update_price(symbol, price)
        
        # Check if we have enough samples
        if self.samples.get(symbol, 0) < 20:
                return {
                        'z_score': 0,
                        'action': 'HOLD',
                        'confidence': 0,
                        'samples': self.samples.get(symbol, 0),
                        'regime': 'RANGE',
                        'trend_strength': 0,
                        'reasoning': f'Building history: {self.samples.get(symbol, 0)}/20'
                }
        
        # ===== STANDARD Z-SCORE CALCULATION =====
        history = list(self.price_history[symbol])
        lookback = min(30, len(history))
        recent_history = history[-lookback:]
        
        mean = sum(recent_history) / len(recent_history)
        variance = sum((x - mean) ** 2 for x in recent_history) / len(recent_history)
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        self.mean[symbol] = mean
        self.std[symbol] = std
        
        if symbol not in self._std_history:
                self._std_history[symbol] = deque(maxlen=50)
        self._std_history[symbol].append(std)
        
        z_score = (price - mean) / std if std > 0 else 0
        self.z_score[symbol] = z_score
        
        # ===== GET REGIME =====
        regime, strength = self.regime_detector.detect_regime(symbol)
        
        # ===== ADAPTIVE THRESHOLDS (PHASE 1) =====
        base_entry, base_exit = self.get_thresholds(symbol)
        
        # Start with conservative multipliers
        trend_multiplier = getattr(self, 'trend_multiplier', 0.7)          # Easier WITH trend
        counter_multiplier = getattr(self, 'counter_multiplier', 1.5)  # Harder AGAINST trend
        
        if regime == 'TREND_UP':
                # In UPTREND: Easier to BUY, harder to SELL
                buy_threshold = -base_entry * trend_multiplier        # -2.0 → -1.4
                sell_threshold = base_entry * counter_multiplier   # +2.0 → +3.0
                
        elif regime == 'TREND_DOWN':
                # In DOWNTREND: Easier to SELL, harder to BUY
                sell_threshold = base_entry * trend_multiplier         # +2.0 → +1.4
                buy_threshold = -base_entry * counter_multiplier   # -2.0 → -3.0
                
        else:  # RANGE
                buy_threshold = -base_entry
                sell_threshold = base_entry
        
        # ===== DECISION LOGIC =====
        if z_score < buy_threshold:
                action = 'BUY'
                confidence = min(95, 70 + (-z_score + buy_threshold) * 12)
                reasoning = f'BUY: Z={z_score:.2f} (threshold: {buy_threshold:.2f}) [{regime}]'
                
        elif z_score > sell_threshold:
                action = 'SELL'
                confidence = min(95, 70 + (z_score - sell_threshold) * 12)
                reasoning = f'SELL: Z={z_score:.2f} (threshold: {sell_threshold:.2f}) [{regime}]'
                
        else:
                action = 'HOLD'
                confidence = max(30, 50 - abs(z_score) * 5)
                reasoning = f'HOLD: Z={z_score:.2f} [{regime}]'
        
        # ===== DEBUG LOGGING =====
        if abs(z_score) > 1.0:
                logger.debug(f'📊 {symbol}: Z={z_score:+.2f} | Regime={regime} ({strength:.0f}%) | '
                                         f'BUY≤{buy_threshold:.2f} SELL≥{sell_threshold:.2f} | {action}')
        
        return {
                'z_score': z_score,
                'action': action,
                'confidence': confidence,
                'mean': mean,
                'std': std,
                'samples': self.samples.get(symbol, 0),
                'entry_threshold_buy': round(buy_threshold, 2),
                'entry_threshold_sell': round(sell_threshold, 2),
                'exit_threshold': round(base_exit, 2),
                'regime': regime,
                'trend_strength': round(strength, 1),
                'reasoning': reasoning
        }
    def peek_zscore(self, symbol: str, price: float) -> Dict:
        """
        Peek Z-Score with adaptive thresholds (READ ONLY - doesn't update history)
        """
        if self.samples.get(symbol, 0) < 20:
                return {
                        'z_score': 0,
                        'action': 'HOLD',
                        'confidence': 0,
                        'samples': self.samples.get(symbol, 0),
                        'regime': 'RANGE',
                        'trend_strength': 0,
                        'reasoning': f'Building history: {self.samples.get(symbol, 0)}/20'
                }
        
        history = list(self.price_history[symbol])
        lookback = min(30, len(history))
        recent_history = history[-lookback:]
        
        mean = sum(recent_history) / len(recent_history)
        variance = sum((x - mean) ** 2 for x in recent_history) / len(recent_history)
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        z_score = (price - mean) / std if std > 0 else 0
        
        # Get regime
        regime, strength = self.regime_detector.detect_regime(symbol)
        
        # Adaptive thresholds
        base_entry, base_exit = self.get_thresholds(symbol)
        
        trend_multiplier = getattr(self, 'trend_multiplier', 0.7)
        counter_multiplier = getattr(self, 'counter_multiplier', 1.5)
        
        if regime == 'TREND_UP':
                buy_threshold = -base_entry * trend_multiplier
                sell_threshold = base_entry * counter_multiplier
        elif regime == 'TREND_DOWN':
                sell_threshold = base_entry * trend_multiplier
                buy_threshold = -base_entry * counter_multiplier
        else:
                buy_threshold = -base_entry
                sell_threshold = base_entry
        
        # Decision
        if z_score < buy_threshold:
                action = 'BUY'
                confidence = min(95, 70 + (-z_score + buy_threshold) * 12)
                reasoning = f'BUY: Z={z_score:.2f} [{regime}]'
        elif z_score > sell_threshold:
                action = 'SELL'
                confidence = min(95, 70 + (z_score - sell_threshold) * 12)
                reasoning = f'SELL: Z={z_score:.2f} [{regime}]'
        else:
                action = 'HOLD'
                confidence = max(30, 50 - abs(z_score) * 5)
                reasoning = f'HOLD: Z={z_score:.2f} [{regime}]'
        
        return {
                'z_score': z_score,
                'action': action,
                'confidence': confidence,
                'samples': self.samples.get(symbol, 0),
                'regime': regime,
                'trend_strength': round(strength, 1),
                'buy_threshold': round(buy_threshold, 2),
                'sell_threshold': round(sell_threshold, 2),
                'reasoning': reasoning
        }
    
    def get_warmup_status(self) -> Dict:
        """Get warmup status for all symbols"""
        status = {}
        total_warmup_needed = 0
        total_completed = 0
        
        for symbol, samples in self.samples.items():
                if samples >= 20:
                        status[symbol] = {'status': 'READY', 'samples': samples}
                        total_completed += 1
                else:
                        status[symbol] = {'status': 'WARMING', 'samples': samples, 
                                                         'needed': 20 - samples}
                        total_warmup_needed += 1
        
        return {
                'status': 'COMPLETE' if total_warmup_needed == 0 else 'WARMING',
                'symbols': status,
                'total_symbols': len(self.samples),
                'ready_symbols': total_completed,
                'warming_symbols': total_warmup_needed
    }
class DashboardAPIClient:
    """HTTP client for forex_dashboard.py with retry logic"""
    
    def __init__(self, url='http://localhost:5002', timeout=5, max_retries=3):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.prices = {}
        self.balance = 0
        self.equity = 0
        self.timestamp = ''
        self.connected = False
        self.last_update = 0
        self._last_error = ''
    
    def fetch_prices(self) -> bool:
        """
        Fetch prices from dashboard with retry logic.
        Returns: True if successful, False otherwise.
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    f'{self.url}/api/all_data',
                    timeout=self.timeout,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('success', False):
                        self.connected = True
                        self._last_error = ''
                        
                        # ✅ Extract prices
                        if 'prices' in data:
                            raw_prices = data['prices']
                            self.prices = {}
                            for symbol, price_data in raw_prices.items():
                                if isinstance(price_data, dict):
                                    self.prices[symbol] = price_data.get('price', 0)
                                else:
                                    self.prices[symbol] = float(price_data) if price_data else 0
                        
                        # ✅ Extract account info
                        if 'balance' in data:
                            self.balance = data['balance']
                        if 'equity' in data:
                            self.equity = data['equity']
                        if 'timestamp' in data:
                            self.timestamp = data['timestamp']
                        
                        self.last_update = time.time()
                        return True
                    
                    else:
                        self._last_error = f"API returned success=False: {data.get('message', 'Unknown error')}"
                
                else:
                    self._last_error = f"HTTP {response.status_code}: {response.text[:100]}"
            
            except requests.exceptions.Timeout:
                self._last_error = f"Timeout after {self.timeout}s (attempt {attempt+1}/{self.max_retries})"
            
            except requests.exceptions.ConnectionError:
                self._last_error = f"Connection error (attempt {attempt+1}/{self.max_retries})"
            
            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s
        
        # All retries failed
        self.connected = False
        logger.warning(f"Failed to fetch prices: {self._last_error}")
        return False
    
    def get_price(self, symbol: str) -> float:
        """Get price for a specific symbol"""
        return self.prices.get(symbol, 0.0)
    
    def get_all_prices(self) -> Dict:
        """Get copy of all prices"""
        return self.prices.copy()
    
    def get_timestamp(self) -> str:
        """Get last update timestamp"""
        return self.timestamp
    
    def get_last_update_seconds(self) -> float:
        """Get seconds since last successful update"""
        if self.last_update == 0:
            return float('inf')
        return time.time() - self.last_update
    
    def is_connected(self) -> bool:
        """Check if connected and data is fresh"""
        if not self.connected:
            return False
        
        # Consider disconnected if no update in 60 seconds
        if self.get_last_update_seconds() > 60:
            return False
        
        return True
    
    def is_data_fresh(self, max_age_seconds: int = 10) -> bool:
        """
        Check if data is fresh enough for trading.
        Args:
            max_age_seconds: Maximum acceptable age of data
        """
        if not self.connected:
            return False
        
        age = self.get_last_update_seconds()
        if age > max_age_seconds:
            logger.debug(f"Data is stale: {age:.1f}s old (max: {max_age_seconds}s)")
            return False
        
        return True
    
    def force_reconnect(self) -> bool:
        """Force a reconnection attempt"""
        self.connected = False
        return self.fetch_prices()
    
    def get_status(self) -> Dict:
        """Get detailed status of client"""
        return {
            'url': self.url,
            'connected': self.connected,
            'data_age_seconds': self.get_last_update_seconds() if self.last_update else None,
            'data_age_formatted': f"{self.get_last_update_seconds():.1f}s" if self.last_update else 'Never',
            'symbols_loaded': len(self.prices),
            'balance': self.balance,
            'equity': self.equity,
            'timestamp': self.timestamp,
            'last_error': self._last_error
        }

class AdvancedTradingController:
    """✅ COMPLETE FIXED: Trading controller with SINGLE Z-Score Engine"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # ===== LOG LEVEL from config =====
        self.log_level = self.config.get('log_level', LOG_LEVEL)
        
        # ===== DASHBOARD CLIENT =====
        self.dashboard = DashboardAPIClient()
        self.last_healthy_cycle = 0
        self.health_check_interval = 10

        # ===== TRADING STRATEGY =====
        self.strategy = AdvancedTradingStrategy(config)
        if not hasattr(self.strategy, 'agent_u'):
            from agent_u_liquidity import AgentU_Liquidity
            from agent_p_crosspair import AgentP_CrossPair
            from agent_d_bbands import AgentD_BBands
            
            self.strategy.agent_u = AgentU_Liquidity()
            self.strategy.agent_p = AgentP_CrossPair()
            self.strategy.agent_d = AgentD_BBands()
            print("✅ Agents created in controller (fallback)")
        # ===== SINGLE Z-SCORE ENGINE (FIXED) =====
        # Use ONLY this Z-Score Engine - remove all others
        self.zscore_engine = SingleZScoreEngine(
            lookback=config.get('zscore_lookback', 50),
            entry_threshold=config.get('zscore_entry', 2.0),
            exit_threshold=config.get('zscore_exit', 0.5),
            warmup_cycles=config.get('warmup_cycles', 50)
        )
        
        print(f"   ✅ Agents initialized: U, P, D")
        self.strategy = AdvancedTradingStrategy(config, zscore_engine=self.zscore_engine)
        # ===== EWMA Z-SCORE (Secondary - for reference only) =====
        self.ewma_zscore = EWMAZScore(alpha=config.get('ewma_alpha', 0.1))

        # ===== DOLLAR ENGINE =====
        self.dollar_engine = DollarEngine(lookback=config.get('dollar_lookback', 20))
        
        # ===== 1-HOUR TREND FILTER =====
        self.hourly_trend = SimpleHourlyTrendFilter()
        
        # ===== RISK MANAGER =====
        self.risk_manager = RiskManager(self.config)
        self.data_manager = FilterDataManager()
        
        # ===== STATE =====
        self.is_running = False
        self.cycle_count = 0
        self.cycle_interval = self.config.get('cycle_interval', 3)  # 5 minutes
        self.total_signals = 0
        self.all_symbols = price_service.all_symbols if hasattr(price_service, 'all_symbols') else []
        self.warmup_complete = False
        self.active_positions = {}
        self.trade_history = []
        
        # ===== MT4 COMMAND PATH =====
        self.mt4_path = self.config.get('mt4_path', 
            "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/")
        self.command_file = os.path.join(self.mt4_path, "AI_Commands.txt")
        
        # ===== CONNECT TO DASHBOARD =====
        self._connect_to_dashboard()
        
        # ===== LOG STARTUP =====
        self._log_startup_info()
        
        # ===== INITIALIZE FILTERS =====
        self._initialize_filters()
    
    def _connect_to_dashboard(self):
        """Connect to dashboard and initialize data"""
        print('\n🔌 Connecting to forex_dashboard.py...')
        success = self.dashboard.fetch_prices()
        
        if success:
            print(f'✅ Connected! Received {len(self.dashboard.prices)} prices')
            print(f'   Balance: ${self.dashboard.balance:.2f}')

            loaded_filters = self.data_manager.load_all(self)
            if loaded_filters:
                print(f'📂 Loaded filter data: {", ".join(loaded_filters)}')
            else:
                print('📊 No existing filter data - initializing from current prices')
                self._init_filter_data()
            
            # Initialize all engines
            self._warm_up_zscore_history()
            self._force_initialize_all_symbols()
            self._load_history_from_json()
            self._warm_up_zscore()
            
            # Try to load M15 history
            print('\n' + '=' * 60)
            print('📊 LOADING M15 HISTORY FROM MT4')
            print('=' * 60)
            
            if self._load_m15_from_mt4():
                print('✅ Using REAL M15 data from MT4')
            else:
                print('⚠️ No M15 data available - using synthetic data')
                self._generate_synthetic_history()
    
            # Print status
            self.print_zscore_status()
            self.strategy.update_dollar_engine(self.dashboard.prices)
            dollar_status = self.strategy.dollar_engine.get_status()
            print(f'   USD Index: {dollar_status["usd_index"]:.1f} ({dollar_status["usd_direction"]})')
        else:
            print('❌ Cannot connect to forex_dashboard.py')
    
    def _log_startup_info(self):
        """Log startup information"""
        logger.info('=' * 60)
        logger.info('🚀 ADVANCED TRADING CONTROLLER (Single Z-Score)')
        logger.info('=' * 60)
        logger.info(f'   Z-Score Lookback: {self.config.get("zscore_lookback", 50)}')
        logger.info(f'   Z-Score Entry: {self.config.get("zscore_entry", 2.0)}')
        logger.info(f'   Warmup Cycles: {self.config.get("warmup_cycles", 50)}')
        logger.info(f'   Total Symbols: {len(self.all_symbols)}')
        logger.info(f'   Filters: Dollar Engine, Volume, Trend, S/R, News')
        logger.info(f'   Cycle Interval: {self.cycle_interval} minutes')
        logger.info('=' * 60)
        self._force_cold_start_complete()
    
    def _initialize_filters(self):
        """Initialize all filters"""
        # Already initialized in __init__
        pass
    
    def _init_filter_data(self):
        """Initialize Z-Score history with synthetic data"""
        prices = self.dashboard.get_all_prices()
        if not prices:
            return
        logger.info('📊 Initializing Filter Data...')
        
        for symbol, current_price in prices.items():
            if current_price <= 0:
                continue
            
            # Volume filter
            for i in range(10):
                volume = 1000 + random.randint(0, 1000)
                self.strategy.volume_filter.update_volume(symbol, volume)
            
            # Determine volatility
            volatility = self._get_volatility(symbol)
            
            # Trend filter
            price = current_price
            for i in range(30):
                if i < 15:
                    price = price * (1 + (i - 15) / 30 * volatility * (0.5 + random.random() * 0.5))
                else:
                    price = price * (1 - (i - 15) / 30 * volatility * 0.3 * (0.5 + random.random() * 0.5))
                price = price * (1 + (random.random() - 0.5) * volatility * 0.5)
                self.strategy.trend_filter.update_price(symbol, price)
        
            # S/R Data
            for i in range(50):
                if i < 15:
                    sr_price = current_price * (1 + 0.005 * (i % 5))
                elif i < 30:
                    sr_price = current_price * (1 - 0.005 * (i % 5))
                else:
                    sr_price = current_price * (1 + 0.005 * (i % 5))
                self.strategy.sr_filter.update_price(symbol, sr_price)
            
            # Z-Score samples
            for i in range(30):
                variation = (i - 15) / 15 * volatility * 0.5
                hist_price = current_price * (1 + variation)
                self.zscore_engine.update_price(symbol, hist_price)
            
            # Debug log for first 3 forex
            if hasattr(price_service, 'forex_pairs') and symbol in price_service.forex_pairs[:3]:
                z_samples = self.zscore_engine.samples.get(symbol, 0)
                trend_samples = len(self.strategy.trend_filter.price_history.get(symbol, []))
                sr_samples = len(self.strategy.sr_filter.price_history.get(symbol, []))
                logger.info(f'   ✅ {symbol}: Z={z_samples}, Trend={trend_samples}, S/R={sr_samples}')
        
        logger.info(f'✅ Z-Score history initialized for {len(prices)} symbols')
    
    def _get_volatility(self, symbol: str) -> float:
        """Get volatility based on symbol type"""
        if hasattr(price_service, 'forex_pairs') and symbol in price_service.forex_pairs:
            return 0.002
        elif hasattr(price_service, 'indices') and symbol in price_service.indices:
            return 0.01
        elif hasattr(price_service, 'metals') and symbol in price_service.metals:
            return 0.005
        elif hasattr(price_service, 'energy') and symbol in price_service.energy:
            return 0.008
        else:
            return 0.005
    
    def _force_cold_start_complete(self):
        """Force cold start complete for immediate trading"""
        logger.info('🔓 Forcing Cold Start Complete...')
        
        self.risk_manager.cold_start_active = False
        self.risk_manager.cold_start_samples = [
            {'win': True, 'pnl': 0.50, 'symbol': 'DEMO', 'action': 'BUY', 'timestamp': datetime.now().isoformat()},
            {'win': False, 'pnl': -0.30, 'symbol': 'DEMO', 'action': 'SELL', 'timestamp': datetime.now().isoformat()},
            {'win': True, 'pnl': 0.75, 'symbol': 'DEMO', 'action': 'BUY', 'timestamp': datetime.now().isoformat()}
        ]
        self.risk_manager.cold_start_wins = 2
        self.risk_manager.cold_start_losses = 1
        self.risk_manager.cold_start_threshold = 3
        self.risk_manager.cold_start_min_win_rate = 0.4
        
        self.risk_manager._save_cold_start_state()
        
        try:
            state = {
                'samples': self.risk_manager.cold_start_samples,
                'wins': self.risk_manager.cold_start_wins,
                'losses': self.risk_manager.cold_start_losses,
                'active': False,
                'timestamp': datetime.now().isoformat()
            }
            with open('cold_start_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except:
            pass
        
        logger.info('✅ Cold Start COMPLETE - Real trading enabled!')
        logger.info(f'   Samples: {len(self.risk_manager.cold_start_samples)}')
        logger.info(f'   Wins: {self.risk_manager.cold_start_wins}')
        logger.info(f'   Losses: {self.risk_manager.cold_start_losses}')
        logger.info(f'   Win Rate: {(self.risk_manager.cold_start_wins / len(self.risk_manager.cold_start_samples) * 100):.1f}%')
    
    def _load_m15_from_mt4(self):
        """Load M15 data directly from MT4's m15_history.json"""
        mt4_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
        history_file = os.path.join(mt4_path, "m15_history.json")
        
        if not os.path.exists(history_file):
            logger.warning('⚠️ M15 history file not found')
            return False
        
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
            
            loaded = 0
            for symbol, history in data.items():
                if isinstance(history, list) and len(history) >= 20:
                    self.zscore_engine.price_history[symbol] = deque(history, maxlen=100)
                    self.zscore_engine.samples[symbol] = len(history)
                    loaded += 1
            
            logger.info(f'✅ Loaded M15 data for {loaded} symbols from MT4')
            return loaded > 0
            
        except Exception as e:
            logger.error(f'❌ Failed to load M15 history: {e}')
            return False
    
    def _load_history_from_json(self):
        """Load historical data from JSON file"""
        logger.info('📂 Loading historical data from JSON...')
        
        if not hasattr(self, 'data_manager'):
            logger.warning('⚠️ No data manager found')
            return False
        
        loaded = self.data_manager.load_zscore_history(self.zscore_engine)
        
        if loaded:
            symbols_with_data = 0
            for symbol in self.all_symbols:
                samples = self.zscore_engine.samples.get(symbol, 0)
                if samples >= 20:
                    symbols_with_data += 1
            
            logger.info(f'✅ Loaded Z-Score history: {symbols_with_data}/{len(self.all_symbols)} symbols have data')
            return True
        
        return False
    
    def _generate_missing_history(self):
        """Generate synthetic history for missing symbols"""
        prices = self.dashboard.get_all_prices()
        if not prices:
            return
        
        generated = 0
        
        for symbol, current_price in prices.items():
            if current_price <= 0:
                continue
            
            samples = self.zscore_engine.samples.get(symbol, 0)
            if samples >= 20:
                continue
            
            volatility = self._get_volatility(symbol)
            
            history = []
            price = current_price
            for i in range(30):
                if i < 15:
                    price = price * (1 + (i - 15) / 30 * volatility * (0.5 + random.random() * 0.5))
                else:
                    price = price * (1 - (i - 15) / 30 * volatility * 0.3 * (0.5 + random.random() * 0.5))
                price = price * (1 + (random.random() - 0.5) * volatility * 0.5)
                history.append(price)
            
            for hist_price in history:
                self.zscore_engine.update_price(symbol, hist_price)
            
            generated += 1
        
        if generated > 0:
            logger.info(f'✅ Generated {generated} synthetic histories')
    
    def _generate_synthetic_history(self):
        """Generate synthetic historical data as fallback"""
        logger.info('📊 Generating synthetic historical data...')
        
        prices = self.dashboard.get_all_prices()
        if not prices:
            return False
        
        symbols_generated = 0
        
        for symbol, current_price in prices.items():
            if current_price <= 0:
                continue
            
            volatility = self._get_volatility(symbol)
            
            history = []
            price = current_price
            for i in range(50):
                if i < 25:
                    variation = (i - 12.5) / 25 * volatility * 0.5
                    price = price * (1 + variation)
                else:
                    variation = -(i - 25) / 25 * volatility * 0.3
                    price = price * (1 + variation)
                price = price * (1 + (0.5 - (i % 10) / 10) * volatility * 0.5)
                history.append(price)
            
            for hist_price in history:
                self.zscore_engine.update_price(symbol, hist_price)
            
            symbols_generated += 1
        
        logger.info(f'✅ Generated synthetic history for {symbols_generated} symbols')
        return True
    
    def _warm_up_zscore(self):
        """Warm up Z-score with historical data"""
        logger.info('🔧 Warming up Z-score...')
        return self._load_historical_data()
    
    def _load_historical_data(self) -> bool:
        """Load historical data from forex_dashboard.py"""
        try:
            logger.info('📊 Loading historical data from forex_dashboard...')
            
            response = requests.get('http://localhost:5002/api/history_all?count=100', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    history_data = data.get('history', {})
                    symbols_loaded = 0
                    
                    for symbol, history in history_data.items():
                        if history and len(history) > 0:
                            for price in history:
                                self.zscore_engine.update_price(symbol, price)
                            symbols_loaded += 1
                    
                    logger.info(f'✅ Loaded historical data for {symbols_loaded} symbols')
                    return True
            
            logger.warning('⚠️ No historical data available')
            return self._generate_synthetic_history()
            
        except Exception as e:
            logger.error(f'❌ Failed to load historical data: {e}')
            return self._generate_synthetic_history()
    
    def _warm_up_zscore_history(self):
        """Warm up Z-Score with historical data"""
        logger.info('📊 Warming up Z-Score with historical data...')
        
        prices = self.dashboard.get_all_prices()
        if not prices:
            logger.warning('⚠️ No prices available for warm-up')
            return
        
        for symbol, current_price in prices.items():
            if current_price <= 0:
                continue
            
            volatility = self._get_volatility(symbol)
            
            history = []
            price = current_price
            for i in range(30):
                if i < 15:
                    price = price * (1 + (i - 15) / 30 * volatility * (0.5 + random.random() * 0.5))
                else:
                    price = price * (1 - (i - 15) / 30 * volatility * 0.3 * (0.5 + random.random() * 0.5))
                price = price * (1 + (random.random() - 0.5) * volatility * 0.5)
                history.append(price)
            
            for hist_price in history:
                self.zscore_engine.update_price(symbol, hist_price)
        
        logger.info('✅ Z-Score warm-up complete')
    
    def _force_initialize_all_symbols(self):
        """Force initialize ALL symbols with synthetic history"""
        logger.info('📊 Force initializing ALL symbols with history...')
        
        prices = self.dashboard.get_all_prices()
        if not prices:
            return
        
        for symbol, current_price in prices.items():
            if current_price <= 0:
                continue
            
            samples = self.zscore_engine.samples.get(symbol, 0)
            if samples >= 20:
                continue
            
            volatility = self._get_volatility(symbol)
            
            history = []
            price = current_price
            for i in range(30):
                if i < 15:
                    price = price * (1 + (i - 15) / 30 * volatility * (0.5 + random.random() * 0.5))
                else:
                    price = price * (1 - (i - 15) / 30 * volatility * 0.3 * (0.5 + random.random() * 0.5))
                price = price * (1 + (random.random() - 0.5) * volatility * 0.5)
                history.append(price)
            
            for hist_price in history:
                self.zscore_engine.update_price(symbol, hist_price)
        
        logger.info('✅ Force initialization complete')
    
    def get_price(self, symbol: str) -> float:
        return self.dashboard.get_price(symbol)
    
    def get_all_prices(self) -> Dict:
        return self.dashboard.get_all_prices()
    
    def print_zscore_status(self):
        """Print current Z-score status for all symbols"""
        print('\n' + '=' * 60)
        print('📊 Z-SCORE STATUS')
        print('=' * 60)
        print(f'{"Symbol":<15} {"Price":<12} {"Z-Score":<10} {"Samples":<10} {"Status":<10}')
        print('-' * 60)

        for symbol in self.all_symbols:
            price = self.dashboard.get_price(symbol)
            if price <= 0:
                continue

            result = self.zscore_engine.peek_zscore(symbol, price)
            z_score = result.get('z_score', 0)
            samples = result.get('samples', 0)

            if samples >= 50:
                status = '✅ Ready'
            else:
                status = f'⏳ {samples}/50'

            print(f'{symbol:<15} {price:<12.5f} {z_score:+.2f}         {samples:<10} {status:<10}')

        print('=' * 60 + '\n')
    
    def get_symbol_config(self, symbol: str) -> Dict:
        configs = {
            'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40},
            'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'GOLD': {'pip': 0.1, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            # NEW INDICES - Stocks/Equities (wider stops due to volatility)
            '#AMAZON': {'pip': 0.01, 'digits': 2, 'sl_pips': 200, 'tp_pips': 400},
            '#APPLE': {'pip': 0.01, 'digits': 2, 'sl_pips': 200, 'tp_pips': 400},
            '#SPACEX': {'pip': 0.01, 'digits': 2, 'sl_pips': 300, 'tp_pips': 600},  # Higher vol
            '#MICROSOFT': {'pip': 0.01, 'digits': 2, 'sl_pips': 200, 'tp_pips': 400},
            '#VISA': {'pip': 0.01, 'digits': 2, 'sl_pips': 200, 'tp_pips': 400},
            '#MASTERCARD': {'pip': 0.01, 'digits': 2, 'sl_pips': 200, 'tp_pips': 400},
            # Existing indices
            '#NASDAQ100': {'pip': 0.01, 'digits': 2, 'sl_pips': 150, 'tp_pips': 300},
            '#DJ30': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            '#S&P500': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            '#RUSS2000': {'pip': 0.01, 'digits': 2, 'sl_pips': 150, 'tp_pips': 300},
            '#CAC40': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            '#DAX40': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            '#FTSE100': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            '#NIKKEI225': {'pip': 0.01, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            # '#DOLLAR_IND': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40}
        }
        
        clean = symbol.replace('#', '')
        if clean in configs:
            return configs[clean]
        if symbol in configs:
            return configs[symbol]
        return {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30}
    
    def get_signal(self, symbol: str, price: float) -> Dict:
        """Get trading signal with all filters"""
        if price <= 0:
            return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'Invalid price'}

        zscore_result = self.zscore_engine.peek_zscore(symbol, price)

        if zscore_result['action'] == 'HOLD':
            return {
                'action': 'HOLD',
                'confidence': 0,
                'zscore': zscore_result,
                'reasoning': zscore_result.get('reasoning', 'Z-score in range')
            }
        
        prices = self.dashboard.get_all_prices()
        if not prices:
            return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'No price data'}
        
        self.dollar_engine.update_prices(prices)
        dollar_result = self.dollar_engine.check_signal(symbol, zscore_result['action'])
        
        if not dollar_result['aligned']:
            return {
                'action': 'HOLD',
                'confidence': 0,
                'zscore': zscore_result,
                'reasoning': dollar_result['message']
            }
        
        self.hourly_trend.update_price(symbol, price)
        trend_result = self.hourly_trend.check_trend(symbol, zscore_result['action'])
        
        if not trend_result['allowed']:
            return {
                'action': 'HOLD',
                'confidence': 0,
                'zscore': zscore_result,
                'reasoning': trend_result['message']
            }
        
        return {
            'action': zscore_result['action'],
            'confidence': zscore_result['confidence'],
            'zscore': zscore_result,
            'price': price,
            'symbol': symbol,
            'reasoning': f'{zscore_result["reasoning"]} | {dollar_result["message"]} | {trend_result["message"]}'
        }
    
    def execute_trade(self, symbol: str, signal: Dict) -> Dict:
        """Execute trade with full signal analysis"""
        action = signal.get('action', 'HOLD')
        confidence = signal.get('confidence', 0)
        price = signal.get('price', 0)
        zscore = signal.get('zscore', {}).get('z_score', 0)
        
        # ===== ✅ FIX: Get reasoning from signal =====
        reasoning = signal.get('reasoning', f'{action} signal on {symbol}')

        logger.info(f'🔍 EXECUTE_TRADE CALLED: {symbol} {action} ({confidence:.0f}%)')
        
        if action == 'HOLD':
                return {'status': 'SKIPPED', 'reason': 'Action is HOLD'}
        
        if confidence < self.config.get('min_confidence', 60):
                return {'status': 'SKIPPED', 'reason': f'Low confidence: {confidence:.0f}%'}
        
        if symbol in self.active_positions:
                return {'status': 'SKIPPED', 'reason': f'Already have position in {symbol}'}
        
        allowed, reason = self.risk_manager.check_trade_allowed(symbol)
        if not allowed:
                return {'status': 'BLOCKED', 'reason': reason}
        
        config = self.get_symbol_config(symbol)
        pip = config.get('pip', 0.0001)
        digits = config.get('digits', 5)
        sl_pips = config.get('sl_pips', 20)
        tp_pips = config.get('tp_pips', 40)
        
        if action == 'BUY':
                sl = price - (sl_pips * pip)
                tp = price + (tp_pips * pip)
        else:
                sl = price + (sl_pips * pip)
                tp = price - (tp_pips * pip)
        
        price = round(price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)
        volume = self.risk_manager.calculate_position_size(confidence, 0.02, symbol)
        
        result = self._send_mt4_order(symbol, action, volume, price, sl, tp)
        
        if result.get('success'):
                self.active_positions[symbol] = {
                        'direction': action,
                        'entry_price': price,
                        'volume': volume,
                        'sl': sl,
                        'tp': tp,
                        'signal': signal,
                        'entry_time': datetime.now().isoformat()
                }
                
                # ===== ✅ NOW 'reasoning' IS DEFINED =====
                signal_service.add_signal(
                        symbol=symbol,
                        signal_type=action,
                        confidence=confidence,
                        price=price,
                        z_score=zscore,
                        source='ADVANCED_STRATEGY',
                        sl=sl,
                        tp=tp,
                        reasoning=reasoning  # ← NOW THIS WORKS!
                )
                
                # ===== ✅ Also log the reasoning for debugging =====
                logger.info(f'💾 Signal saved: {symbol} {action} | Reasoning: {reasoning[:50]}...')
                
                self.save_signals_to_file()
                
                return {
                        'status': 'EXECUTED', 
                        'symbol': symbol, 
                        'action': action, 
                        'price': price, 
                        'volume': volume,
                        'reasoning': reasoning
                }
        else:
                logger.error(f'❌ {symbol} order failed: {result.get("error", "Unknown")}')
                return {'status': 'FAILED', 'reason': result.get('error', 'Unknown error')}
    def _send_mt4_order(self, symbol: str, action: str, volume: float,
                        price: float, sl: float, tp: float) -> Dict:
        try:
            os.makedirs(os.path.dirname(self.command_file), exist_ok=True)
            
            config = self.get_symbol_config(symbol)
            digits = config.get('digits', 5)
            order = {
                "command": "ORDER",
                "symbol": symbol,
                "type": action,
                "volume": round(volume, 2),
                "sl": round(sl, digits),
                "tp": round(tp, digits)
            }
            
            with open(self.command_file, 'w') as f:
                json.dump(order, f)
            
            logger.info(f'📤 ORDER SENT: {symbol} {action} {volume:.2f} lots')
            time.sleep(1)
            return {'success': True, 'ticket': int(time.time())}
                
        except Exception as e:
            logger.error(f'❌ Order failed: {e}')
            return {'success': False, 'error': str(e)}
    
    def check_cold_start_status(self):
        """Check and display cold start status"""
        status = self.risk_manager.get_status()
        samples = status.get('cold_start_samples', 0)
        is_active = status.get('cold_start_active', True)
        
        if not is_active:
            return True
        
        if samples >= self.config.get('cold_start_threshold', 3):
            wins = status.get('cold_start_wins', 0)
            win_rate = wins / samples if samples > 0 else 0
            if win_rate >= self.config.get('cold_start_min_win_rate', 0.4):
                self.risk_manager.cold_start_active = False
                self.risk_manager._save_cold_start_state()
                logger.info('✅ COLD START COMPLETE')
                return True
        
        return False
    
    def add_demo_trade(self, symbol: str, action: str, confidence: float, z_score: float, price: float):
        """Add a demo trade during cold start"""
        win_probability = min(0.9, 0.4 + (confidence / 100) * 0.3 + abs(z_score) / 10)
        was_win = random.random() < win_probability
        
        pips = random.uniform(5, 20) if was_win else -random.uniform(5, 15)
        pnl = pips * 0.10
        
        sample = {
            'win': was_win,
            'pnl': pnl,
            'symbol': symbol,
            'action': action,
            'z_score': z_score,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
        
        self.risk_manager.add_cold_start_sample(sample)
        logger.info(f'🧪 DEMO: {symbol} {action} | {"✅ WIN" if was_win else "❌ LOSS"} | ${pnl:.2f}')
        return sample
    
    def save_signals_to_file(self):
        """Save recent signals to file for dashboard - APPEND MODE"""
        try:
                # Get recent signals from signal_service
                signals = signal_service.get_recent_signals(20)
                signal_data = []
                
                for s in signals:
                        if s.get('signal_type') != 'HOLD':
                                signal_data.append({
                                        'symbol': s.get('symbol', 'Unknown'),
                                        'signal_type': s.get('signal_type', 'UNKNOWN'),
                                        'confidence': int(s.get('confidence', 0)),
                                        'entry_price': float(s.get('entry_price', 0)),
                                        'sl': float(s.get('sl', 0)),
                                        'tp': float(s.get('tp', 0)),
                                        'reasoning': s.get('reasoning', 'No reasoning provided'),
                                        'source': s.get('source', 'ADVANCED_STRATEGY'),
                                        'created_at': s.get('created_at', datetime.now().isoformat()),
                                        'status': s.get('status', 'active'),
                                        'z_score': float(s.get('z_score', 0))
                                })
                
                if not signal_data:
                        return
                
                # ===== FIX: READ EXISTING SIGNALS FIRST =====
                existing_signals = []
                if os.path.exists('signals.json'):
                        try:
                                with open('signals.json', 'r') as f:
                                        content = f.read().strip()
                                        if content:
                                                existing_signals = json.loads(content)
                                                if not isinstance(existing_signals, list):
                                                        existing_signals = []
                        except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f'⚠️ Corrupted signals.json, starting fresh: {e}')
                                existing_signals = []
                
                # ===== MERGE: Add new signals (avoid duplicates) =====
                # Track existing signal IDs (using symbol + created_at as unique key)
                existing_keys = set()
                for sig in existing_signals:
                        key = f"{sig.get('symbol', '')}_{sig.get('created_at', '')}"
                        existing_keys.add(key)
                
                # Add only new signals
                new_count = 0
                for new_sig in signal_data:
                        key = f"{new_sig.get('symbol', '')}_{new_sig.get('created_at', '')}"
                        if key not in existing_keys:
                                existing_signals.append(new_sig)
                                new_count += 1
                
                # ===== KEEP LAST 200 SIGNALS (prevent unlimited growth) =====
                if len(existing_signals) > 200:
                        existing_signals = existing_signals[-200:]
                
                # ===== SAVE MERGED LIST =====
                with open('signals.json', 'w') as f:
                        json.dump(existing_signals, f, indent=2)
                
                if new_count > 0:
                        logger.info(f'💾 Added {new_count} new signals to signals.json (total: {len(existing_signals)})')
                
        except Exception as e:
                logger.error(f'❌ Signals save error: {e}')
                import traceback
                traceback.print_exc()
    def save_dollar_status(self):
        """Save dollar status for dashboard"""
        try:
            dollar_status = self.strategy.dollar_engine.get_status()
            with open('dollar_status.json', 'w') as f:
                json.dump(dollar_status, f)
        except Exception as e:
            logger.debug(f'Dollar status save error: {e}')
    
    def monitor_positions(self):
        """Monitor active positions for SL/TP"""
        if not self.active_positions:
            return
        
        prices = self.get_all_prices()
        if not prices:
            return
        
        for symbol in list(self.active_positions.keys()):
            pos = self.active_positions[symbol]
            current_price = prices.get(symbol, 0)
            
            if current_price <= 0:
                continue
            
            if pos['direction'] == 'BUY':
                if current_price <= pos['sl']:
                    self._close_position(symbol, current_price, 'STOP_LOSS')
                elif current_price >= pos['tp']:
                    self._close_position(symbol, current_price, 'TAKE_PROFIT')
            else:
                if current_price >= pos['sl']:
                    self._close_position(symbol, current_price, 'STOP_LOSS')
                elif current_price <= pos['tp']:
                    self._close_position(symbol, current_price, 'TAKE_PROFIT')
    
    def _close_position(self, symbol: str, price: float, reason: str):
        if symbol not in self.active_positions:
            return
        
        pos = self.active_positions.pop(symbol)
        
        if pos['direction'] == 'BUY':
            pnl = (price - pos['entry_price']) * pos['volume'] * 100000
        else:
            pnl = (pos['entry_price'] - price) * pos['volume'] * 100000
        
        was_win = pnl > 0
        self.risk_manager.update_risk_metrics(pnl, was_win)
        
        logger.info(f'🔚 {symbol} closed {"✅" if was_win else "❌"} ${pnl:.2f} ({reason})')
        
        self.trade_history.append({
            'symbol': symbol,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': price,
            'pnl': pnl,
            'reason': reason,
            'exit_time': datetime.now().isoformat()
        })
    
    def print_full_diagnostics(self, prices: Dict, signals: Dict):
        """Print full diagnostic table with regime info"""
        print('\n' + '=' * 140)
        print(f'📊 FULL DIAGNOSTICS - CYCLE {self.cycle_count} - {datetime.now().strftime("%H:%M:%S")}')
        print('=' * 140)

        print(f'{"Symbol":<12} {"Price":<12} {"Z-Score":<10} {"Regime":<10} {"Action":<8} {"Conf":<6} {"Buy≤":<6} {"Sell≥":<6} {"Samples":<6}')
        print('-' * 140)

        for symbol in self.all_symbols:
                price = prices.get(symbol, 0)
                if price <= 0:
                        continue

                # Get Z-Score with regime info
                zscore_result = self.zscore_engine.peek_zscore(symbol, price)
                z_score = zscore_result.get('z_score', 0)
                samples = zscore_result.get('samples', 0)
                regime = zscore_result.get('regime', 'RANGE')
                buy_th = zscore_result.get('buy_threshold', -2.0)
                sell_th = zscore_result.get('sell_threshold', 2.0)
                
                # Get signal if available
                signal = signals.get(symbol, {})
                action = signal.get('action', 'HOLD')
                confidence = signal.get('confidence', 0)

                # Color coding
                if abs(z_score) > 2.5:
                        z_color = '🔴'
                elif abs(z_score) > 1.5:
                        z_color = '🟡'
                else:
                        z_color = '🟢'

                if action == 'BUY':
                        action_display = '🟢 BUY'
                elif action == 'SELL':
                        action_display = '🔴 SELL'
                else:
                        action_display = '⚪ HOLD'

                print(f'{symbol:<12} {price:<12.5f} {z_color}{z_score:+.2f}         {regime:<10} {action_display:<8} {confidence:<6.0f}% {buy_th:<6.2f} {sell_th:<6.2f} {samples:<6}')

        print('=' * 140)
        
        total_signals = sum(1 for s in signals.values() if s.get('action') != 'HOLD')
        print(f'\n📊 SUMMARY: Total Signals: {total_signals} | Positions: {len(self.active_positions)}')
        print('=' * 140 + '\n')
    # ===== USE AGENTS DIRECTLY =====
    def check_agents(self, symbol: str, action: str, price: float, prices: Dict) -> Dict:
        """Check all agents and return confirmation"""
        confirmations = 0
        agent_results = {}
        
        # Agent_U
        if hasattr(self, 'agent_u'):
                result = self.agent_u.analyze(symbol, price, 
                                                                           usd_direction=self.dollar_engine.usd_direction,
                                                                           usd_strength=self.dollar_engine.usd_strength)
                agent_results['U'] = result
                if result.get('vote') == action and result.get('confidence', 0) > 60:
                        confirmations += 1
        
        # Agent_P
        if hasattr(self, 'agent_p') and prices:
                result = self.agent_p.analyze(symbol, prices)
                agent_results['P'] = result
                if result.get('vote') == action and result.get('confidence', 0) > 60:
                        confirmations += 1
        
        # Agent_D
        if hasattr(self, 'agent_d'):
                result = self.agent_d.analyze(symbol, price)
                agent_results['D'] = result
                if result.get('vote') == action and result.get('confidence', 0) > 60:
                        confirmations += 1
        
        return {
                'confirmations': confirmations,
                'agents': agent_results,
                'confirmed': confirmations >= 1
        }
    def process_cycle(self) -> Dict:
        """Process one trading cycle with DEBUG logging"""
        self.cycle_count += 1
        
        # ===== 1. CHECK COLD START =====
        if self.risk_manager.cold_start_active:
                if len(self.risk_manager.cold_start_samples) >= self.risk_manager.cold_start_threshold:
                        win_rate = self.risk_manager.cold_start_wins / len(self.risk_manager.cold_start_samples)
                        if win_rate >= self.risk_manager.cold_start_min_win_rate:
                                self.risk_manager.cold_start_active = False
                                self.risk_manager._save_cold_start_state()
                                logger.info('✅ COLD START COMPLETE')
        
        max_trades_per_cycle = self.config.get('max_trades_per_cycle', 999)
        trades_this_cycle = 0
        
        # ===== 2. FETCH PRICES =====
        self.dashboard.fetch_prices()
        prices = self.dashboard.get_all_prices()
        if not prices:
                logger.warning('⚠️ No prices available')
                return {'status': 'ERROR', 'reason': 'No prices'}
        
        # ===== 3. UPDATE Z-SCORE =====
        for symbol, price in prices.items():
                if price > 0:
                        self.zscore_engine.update_price(symbol, price)
                        self.ewma_zscore.update(symbol, price)
        
        # ===== 4. CHECK WARMUP =====
        warmup_status = self.zscore_engine.get_warmup_status()
        
        if not self.warmup_complete:
                ready = warmup_status['ready_symbols']
                total = warmup_status['total_symbols']
                
                logger.info(f'🔄 Warmup: {ready}/{total} symbols ready')
                
                if warmup_status['status'] == 'COMPLETE':
                        self.warmup_complete = True
                        logger.info('✅ WARMUP COMPLETE! Starting live trading...')
                else:
                        return {
                                'status': 'WARMING',
                                'cycle': self.cycle_count,
                                'progress': f"{ready}/{total}",
                                'time_elapsed': f"{self.cycle_count * self.cycle_interval} minutes"
                        }
        
        # ===== 5. UPDATE ENGINES =====
        self.dollar_engine.update_prices(prices)
        self.strategy.update_dollar_engine(prices)
        self.monitor_positions()
        cold_start_complete = self.check_cold_start_status()
        
        # ===== 6. CHECK TRADING HOURS =====
        # Get current time
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_time_decimal = current_hour + current_minute / 60.0
        
        # Define no-trade hours: 10:00 PM (22:00) to 2:00 AM
        NO_TRADE_START = 1.0  # 10:00 PM
        NO_TRADE_END = 5.0         # 2:00 AM
        
        # Check if we're in no-trade window
        is_no_trade_time = False
        if NO_TRADE_START <= current_time_decimal < NO_TRADE_END:
            is_no_trade_time = True
        
        # ===== 7. PRINT Z-SCORE STATUS (Every 5 cycles for debugging) =====
        if self.cycle_count % 5 == 0 or self.cycle_count == 1:
                self.print_zscore_status()
        
        # ===== 8. RESULTS =====
        results = {
                'cycle': self.cycle_count,
                'timestamp': datetime.now().isoformat(),
                'signals': {},
                'trades': [],
                'active_positions': len(self.active_positions),
                'dashboard_connected': self.dashboard.is_connected(),
                'dollar_status': self.strategy.dollar_engine.get_status(),
                'cold_start_complete': cold_start_complete,
                'is_no_trade_time': is_no_trade_time
        }
        
        dollar_status = results['dollar_status']
        
        if is_no_trade_time:
            logger.info(f'⏰ NO-TRADE WINDOW: {current_hour:02d}:{current_minute:02d} (01:00-05:00) - ANALYZING ONLY, NO TRADES') 
        else:
            logger.info(f'✅ TRADING HOURS: {current_hour:02d}:{current_minute:02d}')
        
        if self.log_level >= 2:
                logger.info(f'\n🔄 CYCLE {self.cycle_count} - {datetime.now().strftime("%H:%M:%S")}')
                logger.info(f'   💵 USD: {dollar_status["usd_direction"]} | Active: {len(self.active_positions)}')
        
        # ===== 9. DEBUG: CHECK FOR EXTREME Z-SCORES FIRST =====
        extreme_symbols = []
        for symbol in self.all_symbols:
                price = self.get_price(symbol)
                if price <= 0:
                        continue
                zscore_result = self.zscore_engine.peek_zscore(symbol, price)
                z_score = zscore_result.get('z_score', 0)
                if abs(z_score) > 2.0:
                        extreme_symbols.append((symbol, z_score, price))
        
        if extreme_symbols:
                logger.warning(f'🚨 FOUND {len(extreme_symbols)} SYMBOLS WITH |Z| > 2.0:')
                for symbol, z_score, price in extreme_symbols[:5]:
                        logger.warning(f'   📊 {symbol}: Z={z_score:+.2f} | Price={price:.5f}')
        
        # ===== 10. PROCESS EACH SYMBOL =====
        signal_count = 0
        blocked_count = 0
        
        for symbol in self.all_symbols:
                if symbol in self.active_positions:
                        continue
                
                price = self.get_price(symbol)
                if price <= 0:
                        continue
                
                # ===== GET Z-SCORE =====
                zscore_result = self.zscore_engine.peek_zscore(symbol, price)
                z_score = zscore_result.get('z_score', 0)
                
                # ===== ANALYZE SIGNAL =====
                signal = self.strategy.analyze_signal(symbol, price, volume=1000, prices=prices)
                results['signals'][symbol] = signal
                
                action = signal.get('action', 'HOLD')
                confidence = signal.get('confidence', 0)
                reasoning = signal.get('reasoning', '')
                filter_details = signal.get('filter_details', '')
                
                # ===== LOG SIGNAL OR BLOCK =====
                if action != 'HOLD':
                        signal_count += 1
                        if self.log_level >= 2:
                                logger.info(f'🎯 {symbol}: {action} ({confidence:.0f}%) | Z={z_score:+.2f}')
                elif abs(z_score) > 2.0:
                        blocked_count += 1
                        logger.warning(f'⛔ {symbol} BLOCKED: Z={z_score:+.2f}')
                        logger.warning(f'   Reasoning: {reasoning}')
                        if filter_details:
                                logger.warning(f'   Filter Details: {filter_details}')
                        
                        # ===== CHECK EACH FILTER =====
                        filters = signal.get('filters', {})
                        
                        dollar_result = filters.get('dollar', {})
                        if not dollar_result.get('aligned', True):
                                logger.warning(f'   ❌ DOLLAR blocked: {dollar_result.get("message", "Unknown reason")}')
                        
                        trend_result = filters.get('trend', {})
                        if not trend_result.get('aligned', True):
                                logger.warning(f'   ❌ TREND blocked: {trend_result.get("message", "Unknown reason")}')
                        
                        sr_result = filters.get('sr', {})
                        if not sr_result.get('safe', True):
                                logger.warning(f'   ❌ S/R blocked: {sr_result.get("message", "Unknown reason")}')
                        
                        news_result = filters.get('news', {})
                        if not news_result.get('safe', True):
                                logger.warning(f'   ❌ NEWS blocked: {news_result.get("message", "Unknown reason")}')
                        
                        volume_result = filters.get('volume', {})
                        if not volume_result.get('confirmed', True):
                                logger.warning(f'   ❌ VOLUME blocked: {volume_result.get("message", "Unknown reason")}')
                
                # ===== COLD START HANDLING =====
                if not cold_start_complete:
                        if action != 'HOLD' and confidence >= 50:
                                self.add_demo_trade(symbol, action, confidence, z_score, price)
                        continue
                
                # ===== REAL TRADING =====
                # ⭐ KEY CHANGE: Check if trading is allowed based on time
                if action != 'HOLD' and confidence >= self.config.get('min_confidence', 60):
                        
                        # ===== TRADING HOURS CHECK =====
                        if is_no_trade_time:
                                # Still save the signal but don't execute
                                signal_service.add_signal(
                                        symbol=symbol,
                                        signal_type=action,
                                        confidence=confidence,
                                        price=price,
                                        z_score=z_score,
                                        source='ADVANCED_STRATEGY',
                                        sl=signal.get('sl', 0),
                                        tp=signal.get('tp', 0),
                                        reasoning=f'⏰ NO-TRADE WINDOW: {reasoning}'
                                )
                                self.save_signals_to_file()
                                if self.log_level >= 2:
                                        logger.info(f'⏰ {symbol}: {action} signal SAVED but NOT EXECUTED (no-trade window)')
                                continue  # Skip execution
                        
                        # ===== NORMAL TRADING EXECUTION =====
                        if trades_this_cycle >= max_trades_per_cycle:
                                if self.log_level >= 2:
                                        logger.info(f'⏸️ Max trades per cycle reached: {max_trades_per_cycle}')
                                break
                        
                        risk_allowed, risk_reason = self.risk_manager.check_trade_allowed(symbol)
                        
                        if not risk_allowed:
                                if self.log_level >= 2:
                                        logger.info(f'⏸️ {symbol}: Risk blocked - {risk_reason}')
                                continue
                        
                        trade_result = self.execute_trade(symbol, signal)
                        results['trades'].append(trade_result)
                        trades_this_cycle += 1
                        if trade_result.get('status') == 'EXECUTED':
                                if self.log_level >= 2:
                                        logger.info(f'✅ {symbol} {action} executed')
                        else:
                                if self.log_level >= 1:
                                        logger.error(f'❌ {symbol} trade failed: {trade_result.get("reason", "Unknown")}')
        
        # ===== 11. SUMMARY =====
        trade_status = "⏰ NO-TRADE" if is_no_trade_time else "✅ TRADING"
        logger.info(f'📊 Cycle {self.cycle_count}: {trade_status} | Signals={signal_count}, Blocked={blocked_count}, Positions={len(self.active_positions)}')
        
        risk_status = self.risk_manager.get_status()
        
        if self.log_level >= 2:
                cold_start_display = "✅ Complete" if not risk_status.get('cold_start_active', True) else f"❄️ {risk_status.get('cold_start_samples', 0)}/{self.config.get('cold_start_threshold', 3)}"
                logger.info(f'\n📊 Positions: {len(self.active_positions)} | P&L: ${risk_status["daily_pnl"]:.2f} | Trades: {risk_status["trades_today"]} | Cold: {cold_start_display}')
        
        # ===== 12. SAVE DATA =====
        self.save_signals_to_file()
        self.save_dollar_status()
        
        if self.cycle_count % 10 == 0:
                self.data_manager.save_all(self)
        
        if self.cycle_count % 5 == 0:
                self.print_full_diagnostics(prices, results.get('signals', {}))
        
        return results
        # In advanced_trading_controller.py, add after startup:
    def is_trading_hours(self) -> Tuple[bool, str]:
        """
        Check if current time is within trading hours.
        Returns: (is_allowed, message)
        """
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_time_decimal = current_hour + current_minute / 60.0
        
        # No-trade window: 10:00 PM (22:00) to 2:00 AM
        NO_TRADE_START = 1.0  # 10:00 PM
        NO_TRADE_END = 5.0         # 2:00 AM
        
        is_no_trade = NO_TRADE_START <= current_time_decimal < NO_TRADE_END
        
        if is_no_trade:
                # Calculate time until trading resumes
                if current_time_decimal >= NO_TRADE_START:
                        minutes_until = (24.0 - current_time_decimal + NO_TRADE_END) * 60
                else:
                        minutes_until = (NO_TRADE_END - current_time_decimal) * 60
                
                return False, f"No-trade window until {int(minutes_until)} min"
        else:
                return True, "Trading hours"
    def print_trading_status(self):
        """Print current trading hours status"""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        NO_TRADE_START = 1.0
        NO_TRADE_END = 5.0
        current_time_decimal = current_hour + current_minute / 60.0
        
        is_no_trade = NO_TRADE_START <= current_time_decimal < NO_TRADE_END
        
        status = "⏰ NO-TRADE" if is_no_trade else "✅ TRADING"
        
        if is_no_trade:
                if current_time_decimal >= NO_TRADE_START:
                        minutes_until = (24.0 - current_time_decimal + NO_TRADE_END) * 60
                else:
                        minutes_until = (NO_TRADE_END - current_time_decimal) * 60
                print(f'⏰ {status} - Trading resumes in {int(minutes_until)} minutes')
        else:
                print(f'✅ {status} - {current_hour:02d}:{current_minute:02d}')
    def create_test_signal(self):
        """Create a test signal to verify dashboard connection"""
        test_signal = {
                'symbol': 'EURUSD',
                'signal_type': 'BUY',
                'confidence': 85,
                'entry_price': 1.15000,
                'reasoning': 'TEST SIGNAL - Z-Score oversold',
                'source': 'ADVANCED_STRATEGY',
                'created_at': datetime.now().isoformat(),
                'status': 'active',
                'z_score': -2.50
        }
        
        try:
                # Read existing signals
                signals = []
                if os.path.exists('signals.json'):
                        with open('signals.json', 'r') as f:
                                signals = json.load(f)
                                if not isinstance(signals, list):
                                        signals = []
                
                # Add test signal
                signals.append(test_signal)
                
                # Keep last 50
                signals = signals[-50:]
                
                with open('signals.json', 'w') as f:
                        json.dump(signals, f, indent=2)
                
                logger.info('🧪 Test signal written to signals.json')
                return True
        except Exception as e:
                logger.error(f'❌ Test signal failed: {e}')
                return False
    def run(self):
        """Run the trading controller"""
        self.is_running = True
        logger.info('🚀 Starting Advanced Trading Controller...')
        logger.info('   Filters: Dollar Engine, Volume, Trend, S/R, News')
        logger.info(f'   Cycle Interval: {self.cycle_interval} minutes')
        
        try:
            while self.is_running:
                self.process_cycle()
                
                # Sleep for the interval (in seconds)
                sleep_seconds = self.cycle_interval * 60
                for _ in range(sleep_seconds):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logger.error(f'❌ Fatal error: {e}')
            self.stop()
    
    def stop(self):
        """Stop the trading controller"""
        self.is_running = False
        logger.info('✅ Stopped')
# ============================================================
# MARKET REGIME DETECTOR - PHASE 1
# ============================================================

class MarketRegimeDetector:
    """
    Simple market regime detector using linear regression slope.
    Detects: TREND_UP, TREND_DOWN, or RANGE with strength 0-100.
    Phase 1 implementation - minimal and robust.
    """
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
        self.price_history = {}
        self.regime_cache = {}
        self.strength_cache = {}
        self.last_update = {}
        
        logger.info(f'✅ MarketRegimeDetector initialized (lookback={lookback})')
    
    def update_price(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if price <= 0:
            return
        
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        self.price_history[symbol].append(price)
        self.last_update[symbol] = datetime.now()
    
    def detect_regime(self, symbol: str) -> Tuple[str, float]:
        """
        Detect market regime for a symbol
        
        Returns:
            (regime, strength)
            regime: 'TREND_UP' | 'TREND_DOWN' | 'RANGE'
            strength: 0.0 to 100.0
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 30:
            return 'RANGE', 0.0
        
        prices = list(self.price_history[symbol])
        n = len(prices)
        
        # Linear regression: price = slope * x + intercept
        x = list(range(n))
        mean_x = sum(x) / n
        mean_y = sum(prices) / n
        
        numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
        
        # R-squared (how well does the line fit = trend quality)
        intercept = mean_y - slope * mean_x
        ss_res = sum((prices[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((p - mean_y) ** 2 for p in prices)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Normalize slope as % per bar
        avg_price = mean_y
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        # Trend strength = slope magnitude * R² * scaling
        raw_strength = abs(slope_pct) * 100 * max(0, r_squared)
        
        # Classify (conservative thresholds)
        if raw_strength > 15 and slope_pct > 0.01:
            regime = 'TREND_UP'
        elif raw_strength > 15 and slope_pct < -0.01:
            regime = 'TREND_DOWN'
        else:
            regime = 'RANGE'
            raw_strength = max(0, raw_strength * 0.4)
        
        strength = min(100.0, raw_strength)
        
        self.regime_cache[symbol] = regime
        self.strength_cache[symbol] = strength
        
        return regime, strength
    
    def get_regime(self, symbol: str) -> str:
        """Get cached regime for a symbol"""
        return self.regime_cache.get(symbol, 'RANGE')
    
    def get_strength(self, symbol: str) -> float:
        """Get cached strength for a symbol"""
        return self.strength_cache.get(symbol, 0.0)
    
    def get_status(self, symbol: str) -> Dict:
        """Get detailed status for a symbol"""
        regime = self.get_regime(symbol)
        strength = self.get_strength(symbol)
        samples = len(self.price_history.get(symbol, []))
        
        return {
            'symbol': symbol,
            'regime': regime,
            'strength': round(strength, 1),
            'samples': samples,
            'last_update': self.last_update.get(symbol, '').isoformat() if self.last_update.get(symbol) else 'Never'
        }
# ============================================================
# 2. VOLUME CONFIRMATION - FIXED
# ============================================================
class VolumeConfirmation:
    """
    Volume-based filter for trade confirmation.
    Confirms signals with volume spikes above average.
    """
    
    def __init__(self, lookback: int = 20, volume_threshold: float = 1.5, min_samples: int = 10):
        """
        Args:
            lookback: Number of bars to consider for average volume
            volume_threshold: Minimum volume ratio to confirm (e.g., 1.5 = 150% of average)
            min_samples: Minimum samples needed before calculating average
        """
        self.lookback = lookback
        self.volume_threshold = volume_threshold
        self.min_samples = min_samples
        self.volume_history = {}  # symbol -> deque of volumes
        self.avg_volume = {}      # symbol -> average volume
        self.max_volume = {}      # symbol -> max volume for normalization
        self.last_update = {}     # symbol -> timestamp
    
    def update_volume(self, symbol: str, volume: float):
        """
        Update volume history for a symbol.
        
        Args:
            symbol: Trading symbol
            volume: Current volume
        """
        if volume <= 0:
            return
        
        # Initialize if needed
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=self.lookback)
            self.last_update[symbol] = 0
        
        # Add volume
        self.volume_history[symbol].append(volume)
        self.last_update[symbol] = __import__('time').time()
        
        # Update average if we have enough samples
        if len(self.volume_history[symbol]) >= self.min_samples:
            avg = sum(self.volume_history[symbol]) / len(self.volume_history[symbol])
            self.avg_volume[symbol] = avg
            
            # Track max volume
            if symbol not in self.max_volume:
                self.max_volume[symbol] = volume
            else:
                self.max_volume[symbol] = max(self.max_volume[symbol], volume)
    
    def get_avg_volume(self, symbol: str) -> float:
        """Get current average volume for a symbol"""
        return self.avg_volume.get(symbol, 0.0)
    
    def get_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """
        Calculate volume ratio (current / average).
        Returns 0 if no average available.
        """
        avg = self.get_avg_volume(symbol)
        if avg <= 0 or current_volume <= 0:
            return 0.0
        return current_volume / avg
    
    def check_volume(self, symbol: str, current_volume: float) -> Dict:
        """
        Check if volume confirms a trade signal.
        
        Args:
            symbol: Trading symbol
            current_volume: Current volume
            
        Returns:
            Dict with:
                - confirmed: bool
                - volume_ratio: float
                - message: str
                - avg_volume: float
                - samples: int
        """
        # Check if we have enough data
        if symbol not in self.volume_history:
            return {
                'confirmed': True,
                'volume_ratio': 0.0,
                'avg_volume': 0.0,
                'samples': 0,
                'message': '⚠️ No volume data yet - confirming by default'
            }
        
        samples = len(self.volume_history[symbol])
        
        if samples < self.min_samples:
            return {
                'confirmed': True,  # Allow trades with limited data
                'volume_ratio': 0.0,
                'avg_volume': 0.0,
                'samples': samples,
                'message': f'⏳ Building volume history: {samples}/{self.min_samples}'
            }
        
        avg = self.avg_volume.get(symbol, 0.0)
        
        if avg <= 0:
            return {
                'confirmed': True,
                'volume_ratio': 0.0,
                'avg_volume': 0.0,
                'samples': samples,
                'message': '⚠️ Average volume zero - confirming by default'
            }
        
        volume_ratio = current_volume / avg if current_volume > 0 else 0.0
        
        # Determine confirmation status with more granular levels
        if volume_ratio >= self.volume_threshold:
            return {
                'confirmed': True,
                'volume_ratio': volume_ratio,
                'avg_volume': avg,
                'samples': samples,
                'message': f'✅ Strong volume confirmation: {volume_ratio:.1f}x'
            }
        elif volume_ratio >= 1.0:
            return {
                'confirmed': True,  # Still confirmed, but weaker
                'volume_ratio': volume_ratio,
                'avg_volume': avg,
                'samples': samples,
                'message': f'⚠️ Average volume: {volume_ratio:.1f}x'
            }
        elif volume_ratio >= 0.5:
            return {
                'confirmed': False,
                'volume_ratio': volume_ratio,
                'avg_volume': avg,
                'samples': samples,
                'message': f'⚠️ Below average volume: {volume_ratio:.1f}x'
            }
        else:
            return {
                'confirmed': False,
                'volume_ratio': volume_ratio,
                'avg_volume': avg,
                'samples': samples,
                'message': f'❌ Very low volume: {volume_ratio:.1f}x'
            }
    
    def check_volume_for_signal(self, symbol: str, current_volume: float, 
                                signal_action: str, z_score: float = 0) -> Dict:
        """
        Enhanced volume check that considers signal direction.
        
        Args:
            symbol: Trading symbol
            current_volume: Current volume
            signal_action: 'BUY' or 'SELL'
            z_score: Z-score for additional context
            
        Returns:
            Dict with detailed volume analysis
        """
        result = self.check_volume(symbol, current_volume)
        
        # Add extra context based on Z-score
        if abs(z_score) > 2.5 and result['confirmed']:
            result['message'] += ' 🔥 Extreme Z-score + volume spike!'
        elif abs(z_score) > 1.5 and result['confirmed']:
            result['message'] += ' 📈 Significant Z-score + volume'
        
        return result
    
    def get_volume_status(self, symbol: str) -> Dict:
        """
        Get detailed volume status for a symbol.
        """
        if symbol not in self.volume_history:
            return {
                'has_data': False,
                'samples': 0,
                'avg_volume': 0.0,
                'max_volume': 0.0,
                'latest_volume': 0.0,
                'volume_ratio': 0.0
            }
        
        history = self.volume_history[symbol]
        latest = history[-1] if history else 0
        
        return {
            'has_data': True,
            'samples': len(history),
            'avg_volume': self.avg_volume.get(symbol, 0.0),
            'max_volume': self.max_volume.get(symbol, 0.0),
            'latest_volume': latest,
            'volume_ratio': latest / self.avg_volume.get(symbol, 1.0) if self.avg_volume.get(symbol, 0) > 0 else 0.0
        }
    
    def clear_history(self, symbol: Optional[str] = None):
        """
        Clear volume history.
        
        Args:
            symbol: If provided, clear only this symbol; otherwise clear all
        """
        if symbol:
            self.volume_history.pop(symbol, None)
            self.avg_volume.pop(symbol, None)
            self.max_volume.pop(symbol, None)
            self.last_update.pop(symbol, None)
        else:
            self.volume_history.clear()
            self.avg_volume.clear()
            self.max_volume.clear()
            self.last_update.clear()
    def _get_volume_threshold(self, symbol: str) -> float:
        """Get symbol-specific volume threshold"""
        # Stocks/Equities have higher volume variability
        stock_indices = [
                '#AMAZON', '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD'
        ]
        
        if symbol in stock_indices:
                return 1.3  # Lower threshold for stocks (more noise)
        elif symbol.startswith('#') and symbol not in stock_indices:
                return 1.5  # Standard indices
        elif symbol in ['GOLD', 'SILVER', 'BRENT_OIL', 'CrudeOIL']:
                return 1.4  # Commodities
        else:
                return self.volume_threshold  # Forex (1.5)
    def get_stats(self) -> Dict:
        """Get overall volume filter statistics"""
        return {
            'symbols_tracked': len(self.volume_history),
            'symbols_with_avg': len(self.avg_volume),
            'lookback': self.lookback,
            'volume_threshold': self.volume_threshold,
            'min_samples': self.min_samples
        }
# ============================================================
# 3. TREND FILTER - FIXED
# ============================================================

class TrendFilter:
    """
    Improved Trend-based filter with proper sideways detection.
    Uses EMA crossovers and slope analysis for trend identification.
    """
    
    def __init__(self, lookback: int = 50, ema_fast: int = 10, ema_slow: int = 30,
                 sideways_threshold: float = 0.15, slope_threshold: float = 0.05):
        """
        Args:
            lookback: Maximum history to keep
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period  
            sideways_threshold: EMA diff % threshold for sideways detection
            slope_threshold: Minimum slope % for trend detection
        """
        self.lookback = lookback
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.sideways_threshold = sideways_threshold  # 0.15% = 0.0015
        self.slope_threshold = slope_threshold  # 0.05% = 0.0005
        self.price_history = {}
        self.trend = {}
        self._ema_cache = {}  # Cache for performance
        self.last_update = {}
    
    def update_price(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        self.price_history[symbol].append(price)
        self.last_update[symbol] = __import__('time').time()
    
    def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """
        Calculate Exponential Moving Average.
        ✅ FIXED: Proper initialization with SMA.
        """
        if not prices:
            return 0
        
        if len(prices) < period:
            return prices[-1]
        
        # ✅ FIX: Start with SMA for first value
        sma = self.calculate_sma(prices[:period], period)
        multiplier = 2 / (period + 1)
        ema = sma
        
        # Apply EMA formula starting from period+1
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_slope(self, prices: List[float], period: int = 5) -> float:
        """
        Calculate price slope over period.
        Returns: Percentage change over period.
        """
        if len(prices) < period:
            return 0
        return (prices[-1] - prices[-period]) / prices[-period] * 100
    
    def get_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate volatility (standard deviation of returns)"""
        if len(prices) < period:
            return 0.001  # Default
        
        returns = []
        for i in range(1, min(period, len(prices))):
            ret = (prices[-i] - prices[-i-1]) / prices[-i-1]
            returns.append(ret)
        
        if not returns:
            return 0.001
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance) if variance > 0 else 0.001
    
    def get_trend(self, symbol: str) -> Dict:
        """
        Get trend direction and strength for a symbol.
        Returns: Dict with direction, strength, message, and technical values.
        """
        if symbol not in self.price_history:
            return {
                'direction': 'NEUTRAL',
                'strength': 0,
                'message': 'No price data',
                'slope': 0,
                'ema_fast': 0,
                'ema_slow': 0
            }
        
        prices = list(self.price_history[symbol])
        
        if len(prices) < self.ema_slow:
            return {
                'direction': 'NEUTRAL',
                'strength': 30,
                'message': f'Building trend history: {len(prices)}/{self.ema_slow}',
                'slope': 0,
                'ema_fast': 0,
                'ema_slow': 0
            }
        
        # Calculate EMAs
        ema_fast = self.calculate_ema(prices, self.ema_fast)
        ema_slow = self.calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        # Calculate slope
        slope = self.calculate_slope(prices, 5)
        
        # Calculate volatility for adaptive thresholds
        volatility = self.get_volatility(prices)
        adapt_threshold = self.sideways_threshold * (1 + volatility * 100)
        
        # ===== IMPROVED: Check if price is actually trending =====
        # EMAs close together = sideways
        ema_diff = abs(ema_fast - ema_slow) / ema_slow * 100 if ema_slow > 0 else 0
        
        # ✅ FIX: Use adaptive threshold based on volatility
        is_sideways = (
            abs(slope) < self.slope_threshold or
            ema_diff < adapt_threshold or
            (current_price < max(ema_fast, ema_slow) * 1.001 and 
             current_price > min(ema_fast, ema_slow) * 0.999)
        )
        
        # ===== Determine Trend =====
        if is_sideways:
            direction = 'SIDEWAYS'
            strength = 30
            message = f'📊 Sideways (slope: {slope:.2f}%, EMA diff: {ema_diff:.2f}%)'
        elif current_price > ema_fast and ema_fast > ema_slow and slope > 0:
            # Strong uptrend
            direction = 'UP'
            strength = min(100, 60 + abs(slope) * 2)
            message = f'📈 Strong uptrend (slope: {slope:.2f}%)'
        elif current_price < ema_fast and ema_fast < ema_slow and slope < 0:
            # Strong downtrend
            direction = 'DOWN'
            strength = min(100, 60 + abs(slope) * 2)
            message = f'📉 Strong downtrend (slope: {slope:.2f}%)'
        elif current_price > ema_slow and slope > 0:
            # Weak uptrend
            direction = 'UP'
            strength = min(100, 45 + abs(slope) * 1.5)
            message = f'📈 Weak uptrend (slope: {slope:.2f}%)'
        elif current_price < ema_slow and slope < 0:
            # Weak downtrend
            direction = 'DOWN'
            strength = min(100, 45 + abs(slope) * 1.5)
            message = f'📉 Weak downtrend (slope: {slope:.2f}%)'
        else:
            # Default sideways
            direction = 'SIDEWAYS'
            strength = 30
            message = f'📊 Sideways (slope: {slope:.2f}%)'
        
        # Cache the result
        self.trend[symbol] = {
            'direction': direction,
            'strength': strength,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'slope': slope,
            'volatility': volatility,
            'message': message
        }
        
        return self.trend[symbol]
    
    def check_trend(self, symbol: str, signal_action: str) -> Dict:
        """
        Check if signal action aligns with the trend.
        
        Args:
            symbol: Trading symbol
            signal_action: 'BUY' or 'SELL'
            
        Returns:
            Dict with:
                - aligned: bool
                - trend: Dict with trend details
                - message: str
        """
        trend = self.get_trend(symbol)
        
        if trend['direction'] == 'NEUTRAL':
            return {
                'aligned': True,
                'trend': trend,
                'message': '⏳ No trend data, allowing trade'
            }
        
        # ===== IMPROVED: Smart trend alignment =====
        if trend['direction'] == 'SIDEWAYS':
            # In sideways markets, both BUY and SELL are allowed with caution
            return {
                'aligned': True,
                'trend': trend,
                'message': f'⚠️ Sideways market - {signal_action} allowed with caution (strength: {trend["strength"]:.0f}%)'
            }
        
        elif signal_action == 'BUY':
            if trend['direction'] == 'UP':
                # Strong alignment
                if trend['strength'] >= 70:
                    return {
                        'aligned': True,
                        'trend': trend,
                        'message': f'✅ BUY strongly aligns with {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                    }
                else:
                    return {
                        'aligned': True,
                        'trend': trend,
                        'message': f'✅ BUY aligns with {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                    }
            else:
                return {
                    'aligned': False,
                    'trend': trend,
                    'message': f'❌ BUY against {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                }
        
        elif signal_action == 'SELL':
            if trend['direction'] == 'DOWN':
                if trend['strength'] >= 70:
                    return {
                        'aligned': True,
                        'trend': trend,
                        'message': f'✅ SELL strongly aligns with {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                    }
                else:
                    return {
                        'aligned': True,
                        'trend': trend,
                        'message': f'✅ SELL aligns with {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                    }
            else:
                return {
                    'aligned': False,
                    'trend': trend,
                    'message': f'❌ SELL against {trend["direction"]} trend (strength: {trend["strength"]:.0f}%)'
                }
        
        return {
            'aligned': True,
            'trend': trend,
            'message': f'{signal_action} allowed (HOLD signal)'
        }
    
    def get_trend_strength(self, symbol: str) -> float:
        """Get trend strength as a percentage (0-100)"""
        trend = self.get_trend(symbol)
        return trend.get('strength', 0)
    
    def get_trend_direction(self, symbol: str) -> str:
        """Get trend direction: 'UP', 'DOWN', 'SIDEWAYS', or 'NEUTRAL'"""
        trend = self.get_trend(symbol)
        return trend.get('direction', 'NEUTRAL')
    
    def is_uptrend(self, symbol: str) -> bool:
        """Check if symbol is in uptrend"""
        return self.get_trend_direction(symbol) == 'UP'
    
    def is_downtrend(self, symbol: str) -> bool:
        """Check if symbol is in downtrend"""
        return self.get_trend_direction(symbol) == 'DOWN'
    
    def is_sideways(self, symbol: str) -> bool:
        """Check if symbol is in sideways market"""
        direction = self.get_trend_direction(symbol)
        return direction == 'SIDEWAYS' or direction == 'NEUTRAL'
    
    def get_trend_summary(self, symbol: str) -> Dict:
        """Get a comprehensive trend summary for a symbol"""
        trend = self.get_trend(symbol)
        
        return {
            'symbol': symbol,
            'direction': trend.get('direction', 'NEUTRAL'),
            'strength': trend.get('strength', 0),
            'slope': trend.get('slope', 0),
            'ema_fast': trend.get('ema_fast', 0),
            'ema_slow': trend.get('ema_slow', 0),
            'message': trend.get('message', ''),
            'samples': len(self.price_history.get(symbol, []))
        }
    
    def get_status(self) -> Dict:
        """Get overall trend filter status"""
        return {
            'symbols_tracked': len(self.price_history),
            'lookback': self.lookback,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'sideways_threshold': self.sideways_threshold,
            'slope_threshold': self.slope_threshold
        }
    
    def clear_history(self, symbol: Optional[str] = None):
        """Clear price history"""
        if symbol:
            self.price_history.pop(symbol, None)
            self.trend.pop(symbol, None)
            self._ema_cache.pop(symbol, None)
        else:
            self.price_history.clear()
            self.trend.clear()
            self._ema_cache.clear()
# ============================================================
# 4. SUPPORT/RESISTANCE - COMPLETE FIXED VERSION
# ============================================================

class SupportResistance:
    """
    Support/Resistance filter with breakout detection.
    Detects key price levels and provides trade guidance.
    """
    
    def __init__(self, lookback: int = 50, min_touches: int = 2, 
                 tolerance: float = 0.003, level_decay_days: int = 7):
        """
        Args:
            lookback: Number of bars to analyze
            min_touches: Minimum touches to confirm a level
            tolerance: Clustering tolerance (0.003 = 0.3%)
            level_decay_days: Days before levels expire
        """
        self.lookback = lookback
        self.min_touches = min_touches
        self.tolerance = tolerance
        self.level_decay_days = level_decay_days
        self.price_history = {}  # symbol -> deque of prices
        self.levels = {}         # symbol -> level data
        self._detected_levels = {}  # symbol -> bool
        self._level_touches = {}    # symbol -> {level: touches}
        self._level_timestamps = {} # symbol -> {level: timestamp}
    
    def update_price(self, symbol: str, price: float):
        """Update price history and detect levels periodically"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        self.price_history[symbol].append(price)
        
        # Detect levels every 5 bars after minimum history
        if len(self.price_history[symbol]) >= 20 and len(self.price_history[symbol]) % 5 == 0:
            self._detect_levels(symbol)
    
    def _detect_levels(self, symbol: str):
        """
        Improved level detection with clustering and touch counting.
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return
        
        prices = list(self.price_history[symbol])
        
        # ===== 1. Find swing highs and lows =====
        highs = []
        lows = []
        
        for i in range(2, len(prices) - 2):
            # Swing high: price is higher than 2 bars on both sides
            if (prices[i] >= prices[i-1] and prices[i] >= prices[i-2] and
                prices[i] >= prices[i+1] and prices[i] >= prices[i+2]):
                highs.append(prices[i])
            # Swing low: price is lower than 2 bars on both sides
            elif (prices[i] <= prices[i-1] and prices[i] <= prices[i-2] and
                  prices[i] <= prices[i+1] and prices[i] <= prices[i+2]):
                lows.append(prices[i])
        
        # Fallback if no swings found
        if not highs and not lows:
            highs = [max(prices[-10:])]
            lows = [min(prices[-10:])]
        
        # ===== 2. Cluster support levels (lows) =====
        support_levels = []
        for low in lows:
            if low <= 0:
                continue
            
            # Check if similar level already exists
            found = False
            for idx, level in enumerate(support_levels):
                if abs(low - level) / max(level, 0.001) < self.tolerance:
                    found = True
                    # Update touch count
                    if symbol not in self._level_touches:
                        self._level_touches[symbol] = {}
                    self._level_touches[symbol][level] = self._level_touches[symbol].get(level, 0) + 1
                    break
            
            if not found:
                support_levels.append(low)
                if symbol not in self._level_touches:
                    self._level_touches[symbol] = {}
                self._level_touches[symbol][low] = 1
        
        # ===== 3. Cluster resistance levels (highs) =====
        resistance_levels = []
        for high in highs:
            if high <= 0:
                continue
            
            found = False
            for idx, level in enumerate(resistance_levels):
                if abs(high - level) / max(level, 0.001) < self.tolerance:
                    found = True
                    if symbol not in self._level_touches:
                        self._level_touches[symbol] = {}
                    self._level_touches[symbol][level] = self._level_touches[symbol].get(level, 0) + 1
                    break
            
            if not found:
                resistance_levels.append(high)
                if symbol not in self._level_touches:
                    self._level_touches[symbol] = {}
                self._level_touches[symbol][high] = 1
        
        # ===== 4. Filter by minimum touches =====
        filtered_support = []
        for level in support_levels:
            touches = self._level_touches.get(symbol, {}).get(level, 0)
            if touches >= self.min_touches:
                filtered_support.append(level)
            else:
                # Keep as weak support if no other levels
                filtered_support.append(level)
        
        filtered_resistance = []
        for level in resistance_levels:
            touches = self._level_touches.get(symbol, {}).get(level, 0)
            if touches >= self.min_touches:
                filtered_resistance.append(level)
            else:
                filtered_resistance.append(level)
        
        # ===== 5. Sort and limit =====
        filtered_support = sorted(set(filtered_support))[:5]
        filtered_resistance = sorted(set(filtered_resistance), reverse=True)[:5]
        
        # Fallback if no levels found
        if not filtered_support:
            filtered_support = [min(prices) * 0.998]
        if not filtered_resistance:
            filtered_resistance = [max(prices) * 1.002]
        
        # ===== 6. Store levels =====
        self.levels[symbol] = {
            'support': filtered_support,
            'resistance': filtered_resistance,
            'last_update': datetime.now().isoformat(),
            'support_count': len(filtered_support),
            'resistance_count': len(filtered_resistance)
        }
        
        self._detected_levels[symbol] = True
        
        # Update timestamps for decay
        if symbol not in self._level_timestamps:
            self._level_timestamps[symbol] = {}
        for level in filtered_support + filtered_resistance:
            self._level_timestamps[symbol][level] = datetime.now()
    
    def _clean_old_levels(self, symbol: str):
        """Remove levels that haven't been touched recently"""
        if symbol not in self._level_timestamps:
            return
        
        now = datetime.now()
        expired_levels = []
        for level, timestamp in self._level_timestamps[symbol].items():
            age = (now - timestamp).days
            if age > self.level_decay_days:
                expired_levels.append(level)
        
        if expired_levels and symbol in self.levels:
            for level in expired_levels:
                if level in self.levels[symbol].get('support', []):
                    self.levels[symbol]['support'].remove(level)
                if level in self.levels[symbol].get('resistance', []):
                    self.levels[symbol]['resistance'].remove(level)
                
                # Also clean touches
                if symbol in self._level_touches:
                    self._level_touches[symbol].pop(level, None)
                if symbol in self._level_timestamps:
                    self._level_timestamps[symbol].pop(level, None)
    
    def check_levels(self, symbol: str, price: float, action: str) -> Dict:
        """
        Check if price is near support/resistance.
        
        Args:
            symbol: Trading symbol
            price: Current price
            action: 'BUY' or 'SELL'
            
        Returns:
            Dict with:
                - safe: bool (True = trade allowed)
                - level_type: 'SUPPORT', 'RESISTANCE', 'BREAKOUT', 'BREAKDOWN', or 'NONE'
                - nearest_level: float
                - distance: float (percentage distance)
                - message: str
        """
        # ===== 1. Check if levels exist =====
        if symbol not in self.levels or not self.levels[symbol]:
            if symbol in self.price_history and len(self.price_history[symbol]) >= 10:
                self._detect_levels(symbol)
            
            if symbol not in self.levels or not self.levels[symbol]:
                return {
                    'safe': True,
                    'safe_reason': 'NO_LEVELS',
                    'level_type': 'NONE',
                    'nearest_level': 0,
                    'distance': 0,
                    'message': 'No levels detected, allowing trade'
                }
        
        # ===== 2. Clean old levels =====
        self._clean_old_levels(symbol)
        
        # ===== 3. Get levels =====
        levels = self.levels[symbol]
        support = levels.get('support', [])
        resistance = levels.get('resistance', [])
        
        if not support and not resistance:
            return {
                'safe': True,
                'safe_reason': 'NO_LEVELS',
                'level_type': 'NONE',
                'nearest_level': 0,
                'distance': 0,
                'message': 'No support/resistance levels found'
            }
        
        # ===== 4. Find nearest levels =====
        nearest_support = min(support, key=lambda x: abs(price - x)) if support else None
        nearest_resistance = min(resistance, key=lambda x: abs(price - x)) if resistance else None
        
        # ===== 5. Calculate distances =====
        support_distance = abs(price - nearest_support) / max(price, 0.0001) if nearest_support else 999
        resistance_distance = abs(price - nearest_resistance) / max(price, 0.0001) if nearest_resistance else 999
        
        # Use adaptive tolerance based on price
        adaptive_tolerance = self.tolerance * 2 if price > 100 else self.tolerance
        
        near_support = support_distance < adaptive_tolerance and nearest_support is not None
        near_resistance = resistance_distance < adaptive_tolerance and nearest_resistance is not None
        
        # ===== 6. Check for breakouts =====
        if resistance and price > max(resistance) * 1.005:
            return {
                'safe': True,
                'safe_reason': 'BREAKOUT',
                'level_type': 'BREAKOUT',
                'nearest_level': max(resistance),
                'distance': (price - max(resistance)) / max(resistance) * 100,
                'message': f'✅ Breakout above resistance {max(resistance):.5f}'
            }
        
        if support and price < min(support) * 0.995:
            return {
                'safe': True,
                'safe_reason': 'BREAKDOWN',
                'level_type': 'BREAKDOWN',
                'nearest_level': min(support),
                'distance': (min(support) - price) / min(support) * 100,
                'message': f'✅ Breakdown below support {min(support):.5f}'
            }
        
        # ===== 7. Determine nearest level type =====
        nearest_level = 0
        level_type = 'NONE'
        distance = 0
        
        if near_support and near_resistance:
            if support_distance < resistance_distance:
                nearest_level = nearest_support
                level_type = 'SUPPORT'
                distance = support_distance
            else:
                nearest_level = nearest_resistance
                level_type = 'RESISTANCE'
                distance = resistance_distance
        elif near_support:
            nearest_level = nearest_support
            level_type = 'SUPPORT'
            distance = support_distance
        elif near_resistance:
            nearest_level = nearest_resistance
            level_type = 'RESISTANCE'
            distance = resistance_distance
        
        # ===== 8. Trade decision =====
        if action == 'BUY':
            if level_type == 'SUPPORT':
                return {
                    'safe': True,
                    'safe_reason': 'SUPPORT',
                    'level_type': 'SUPPORT',
                    'nearest_level': nearest_level,
                    'distance': distance,
                    'message': f'✅ BUY near support {nearest_level:.5f} (distance: {distance:.2%})'
                }
            elif level_type == 'RESISTANCE':
                return {
                    'safe': False,
                    'safe_reason': 'RESISTANCE',
                    'level_type': 'RESISTANCE',
                    'nearest_level': nearest_level,
                    'distance': distance,
                    'message': f'❌ BUY near resistance {nearest_level:.5f} (distance: {distance:.2%})'
                }
        
        elif action == 'SELL':
            if level_type == 'RESISTANCE':
                return {
                    'safe': True,
                    'safe_reason': 'RESISTANCE',
                    'level_type': 'RESISTANCE',
                    'nearest_level': nearest_level,
                    'distance': distance,
                    'message': f'✅ SELL near resistance {nearest_level:.5f} (distance: {distance:.2%})'
                }
            elif level_type == 'SUPPORT':
                return {
                    'safe': False,
                    'safe_reason': 'SUPPORT',
                    'level_type': 'SUPPORT',
                    'nearest_level': nearest_level,
                    'distance': distance,
                    'message': f'❌ SELL near support {nearest_level:.5f} (distance: {distance:.2%})'
                }
        
        # ===== 9. No strong S/R nearby =====
        return {
            'safe': True,
            'safe_reason': 'NO_SR',
            'level_type': 'NONE',
            'nearest_level': 0,
            'distance': 0,
            'message': f'No strong S/R nearby, allowing {action}'
        }
    
    def get_nearest_level(self, symbol: str, price: float) -> Tuple[float, str]:
        """
        Get nearest support/resistance level and its type.
        
        Returns:
            (level_price, level_type) where level_type is 'SUPPORT' or 'RESISTANCE'
        """
        if symbol not in self.levels:
            return (0, 'NONE')
        
        levels = self.levels[symbol]
        support = levels.get('support', [])
        resistance = levels.get('resistance', [])
        
        nearest_support = min(support, key=lambda x: abs(price - x)) if support else None
        nearest_resistance = min(resistance, key=lambda x: abs(price - x)) if resistance else None
        
        if nearest_support is None and nearest_resistance is None:
            return (0, 'NONE')
        
        if nearest_support is None:
            return (nearest_resistance, 'RESISTANCE')
        if nearest_resistance is None:
            return (nearest_support, 'SUPPORT')
        
        support_dist = abs(price - nearest_support)
        resistance_dist = abs(price - nearest_resistance)
        
        if support_dist < resistance_dist:
            return (nearest_support, 'SUPPORT')
        else:
            return (nearest_resistance, 'RESISTANCE')
    
    def get_level_summary(self, symbol: str) -> Dict:
        """Get a summary of support/resistance levels"""
        if symbol not in self.levels:
            return {
                'has_levels': False,
                'support': [],
                'resistance': [],
                'last_update': None
            }
        
        levels = self.levels[symbol]
        return {
            'has_levels': True,
            'support': levels.get('support', []),
            'resistance': levels.get('resistance', []),
            'support_count': levels.get('support_count', 0),
            'resistance_count': levels.get('resistance_count', 0),
            'last_update': levels.get('last_update', None)
        }
    
    def get_status(self) -> Dict:
        """Get overall filter status"""
        return {
            'symbols_tracked': len(self.price_history),
            'symbols_with_levels': len([s for s in self.levels if self.levels[s]]),
            'lookback': self.lookback,
            'min_touches': self.min_touches,
            'tolerance': self.tolerance,
            'level_decay_days': self.level_decay_days
        }
    
    def clear_history(self, symbol: Optional[str] = None):
        """Clear price history"""
        if symbol:
            self.price_history.pop(symbol, None)
            self.levels.pop(symbol, None)
            self._detected_levels.pop(symbol, None)
            self._level_touches.pop(symbol, None)
            self._level_timestamps.pop(symbol, None)
        else:
            self.price_history.clear()
            self.levels.clear()
            self._detected_levels.clear()
            self._level_touches.clear()
            self._level_timestamps.clear()
# ============================================================
# 5. NEWS FILTER - COMPLETE FIXED VERSION
# ============================================================

class NewsFilter:
    """
    News/event filter with JSON file persistence.
    Blocks trades during high-impact news events.
    """
    
    def __init__(self, news_file: str = 'filter_data/news_events.json', 
                 buffer_minutes: int = 30, warning_minutes: int = 60,
                 timezone_offset: int = 0):
        """
        Args:
            news_file: Path to JSON file for storing events
            buffer_minutes: Minutes before/after event to block trading
            warning_minutes: Minutes before event to show warning
            timezone_offset: Hours offset from UTC (e.g., +2 for CEST)
        """
        self.news_file = news_file
        self.buffer_minutes = buffer_minutes
        self.warning_minutes = warning_minutes
        self.timezone_offset = timezone_offset
        
        # High impact event keywords per currency
        self.high_impact_events = {
            'EUR': ['ECB Rate Decision', 'Eurozone GDP', 'German CPI', 'ECB Press Conference',
                    'ECB Monetary Policy', 'Eurozone CPI', 'German GDP', 'French CPI'],
            'USD': ['FOMC Meeting', 'Non-Farm Payrolls', 'CPI', 'Fed Rate Decision', 'GDP',
                    'FOMC Statement', 'Fed Chair Speech', 'PPI', 'Retail Sales', 'Unemployment'],
            'GBP': ['BOE Rate Decision', 'UK GDP', 'CPI', 'BOE Meeting Minutes',
                    'BOE Monetary Policy', 'UK CPI', 'UK Unemployment'],
            'JPY': ['BOJ Rate Decision', 'Japan GDP', 'CPI', 'BOJ Press Conference',
                    'BOJ Monetary Policy', 'Japan CPI'],
            'CHF': ['SNB Rate Decision', 'Swiss GDP', 'SNB Press Conference',
                    'Swiss CPI', 'SNB Monetary Policy'],
            'AUD': ['RBA Rate Decision', 'Australia GDP', 'CPI', 'RBA Meeting Minutes',
                    'RBA Monetary Policy', 'Australia CPI'],
            'CAD': ['BOC Rate Decision', 'Canada GDP', 'CPI', 'BOC Press Conference',
                    'BOC Monetary Policy', 'Canada CPI'],
            'NZD': ['RBNZ Rate Decision', 'New Zealand GDP', 'CPI', 'RBNZ Press Conference',
                    'RBNZ Monetary Policy', 'NZ CPI']
        }
        
        self.event_calendar = {}  # date -> list of events
        self.last_update = 0
        self._load_events()
    
    def _load_events(self):
        """Load events from JSON file or create default"""
        today = datetime.now().date()
        today_str = today.isoformat()
        
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(self.news_file), exist_ok=True)
        except:
            pass
        
        # Try to load from file
        try:
            if os.path.exists(self.news_file):
                with open(self.news_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convert string keys back to date objects
                    for date_str, events in data.items():
                        try:
                            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            self.event_calendar[event_date] = events
                        except:
                            continue
                    
                    # Clean up old events (older than 7 days)
                    self._clean_old_events()
                    
                    today_events = len(self.event_calendar.get(today, []))
                    if today_events > 0:
                        logger.info(f'✅ Loaded {today_events} news events for today from file')
                        return
        except Exception as e:
            logger.debug(f'News file load error: {e}')
        
        # Create default events if file doesn't exist or empty
        self._create_default_events()
    
    def _clean_old_events(self, days_to_keep: int = 7):
        """Remove events older than days_to_keep"""
        cutoff = datetime.now().date() - timedelta(days=days_to_keep)
        old_dates = [d for d in self.event_calendar.keys() if d < cutoff]
        
        for date in old_dates:
            del self.event_calendar[date]
            logger.debug(f'Removed old events for {date}')
        
        if old_dates:
            self._save_events()
    
    def _create_default_events(self):
        """Create default events file if it doesn't exist"""
        today = datetime.now().date()
        today_str = today.isoformat()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        # Get current month's known events (simplified)
        default_events = {
            today_str: [
                {'time': '08:30', 'currency': 'USD', 'event': 'CPI', 'impact': 'HIGH'},
                {'time': '14:00', 'currency': 'USD', 'event': 'FOMC Meeting', 'impact': 'HIGH'},
            ],
            tomorrow.isoformat(): [
                {'time': '08:30', 'currency': 'USD', 'event': 'GDP', 'impact': 'HIGH'},
                {'time': '04:00', 'currency': 'EUR', 'event': 'ECB Rate Decision', 'impact': 'HIGH'},
            ],
            day_after.isoformat(): [
                {'time': '04:00', 'currency': 'EUR', 'event': 'ECB Press Conference', 'impact': 'HIGH'},
            ],
        }
        
        # Only add events that are in the future
        for date_str, events in default_events.items():
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if event_date >= today:
                    self.event_calendar[event_date] = events
            except:
                continue
        
        self._save_events()
        logger.info(f'✅ Created default news events file: {self.news_file}')
    
    def _save_events(self):
        """Save events to JSON file"""
        try:
            # Convert date keys to strings
            events_dict = {}
            for date, events in self.event_calendar.items():
                if events:  # Only save non-empty event lists
                    events_dict[date.isoformat()] = events
            
            os.makedirs(os.path.dirname(self.news_file), exist_ok=True)
            with open(self.news_file, 'w') as f:
                json.dump(events_dict, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f'Could not save news file: {e}')
    
    def _get_currencies(self, symbol: str) -> Set[str]:
        """
        ✅ FIXED: Returns currencies relevant to the symbol.
        For forex: returns both currencies in the pair.
        For indices/metals: returns empty set (no currency-specific news blocking).
        """
        currencies = set()
        
        # Forex pairs
        forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 
                       'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'EURCAD',
                       'EURNZD', 'EURCHF']
        
        if symbol in forex_pairs:
            # Extract currencies from pair
            if symbol.startswith('EUR'):
                currencies.add('EUR')
            if symbol.endswith('USD'):
                currencies.add('USD')
            if 'GBP' in symbol:
                currencies.add('GBP')
            if 'JPY' in symbol:
                currencies.add('JPY')
            if 'CHF' in symbol:
                currencies.add('CHF')
            if 'AUD' in symbol:
                currencies.add('AUD')
            if 'CAD' in symbol:
                currencies.add('CAD')
            if 'NZD' in symbol:
                currencies.add('NZD')
        elif symbol.startswith('#'):
            # Indices - no specific currency blocking
            pass
        elif symbol in ['GOLD', 'SILVER']:
            # Metals - USD news can affect them
            currencies.add('USD')
        elif symbol in ['BRENT_OIL', 'CrudeOIL']:
            # Energy - USD news can affect them
            currencies.add('USD')
        
        return currencies
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """
        ✅ FIXED: Parse time string with or without leading zeros.
        """
        time_str = time_str.strip()
        
        # Try different formats
        formats = [
            "%H:%M",      # 08:30
            "%-H:%M",     # 8:30 (Unix)
            "%I:%M %p",   # 08:30 AM
            "%-I:%M %p",  # 8:30 AM
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        
        # Fallback: try to parse manually
        try:
            if ':' in time_str:
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1].split()[0]) if parts[1] else 0
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        except:
            pass
        
        return None
    
    def check_news(self, symbol: str) -> Dict:
        """
        Check if any high-impact news is approaching.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with:
                - safe: bool (True = trade allowed)
                - warning: bool (True = approaching event)
                - event: str (event name)
                - currency: str (affected currency)
                - time_until: str (time until event)
                - message: str (human readable message)
        """
        now = datetime.now()
        today = now.date()
        
        # ===== 1. Get relevant currencies for this symbol =====
        currencies = self._get_currencies(symbol)
        
        # ===== 2. If no currencies, check if symbol is affected by news =====
        if not currencies:
            # For indices, check if any major news
            if symbol.startswith('#'):
                # Check for USD news (major indices affected by USD)
                currencies = {'USD'}
            else:
                # Unknown symbol - allow trading
                return {
                    'safe': True,
                    'warning': False,
                    'message': 'No news filtering for this symbol'
                }
        
        # ===== 3. Check events for today =====
        if today not in self.event_calendar or not self.event_calendar[today]:
            return {
                'safe': True,
                'warning': False,
                'message': 'No known events today'
            }
        
        # ===== 4. Check each event =====
        for event in self.event_calendar[today]:
            # Check if event affects this symbol
            if event['currency'] not in currencies:
                continue
            
            # Check if event is HIGH impact (or MEDIUM if we want to be cautious)
            impact = event.get('impact', 'HIGH')
            if impact not in ['HIGH', 'MEDIUM']:
                continue
            
            # Parse event time
            event_time = self._parse_time(event['time'])
            if event_time is None:
                continue
            
            # Create full datetime for today
            event_datetime = datetime.combine(today, event_time.time())
            
            # Apply timezone offset if needed
            if self.timezone_offset != 0:
                event_datetime = event_datetime + timedelta(hours=self.timezone_offset)
            
            # Calculate time difference in minutes
            time_diff = (event_datetime - now).total_seconds() / 60
            
            # ===== 5. Event is in the past =====
            if time_diff < -self.buffer_minutes:
                # Event already passed
                continue
            
            # ===== 6. Event is happening NOW or within buffer =====
            if abs(time_diff) < self.buffer_minutes:
                minutes_abs = abs(time_diff)
                if time_diff < 0:
                    time_str = f"{minutes_abs:.0f} min ago"
                else:
                    time_str = f"{minutes_abs:.0f} min"
                
                return {
                    'safe': False,
                    'warning': False,
                    'event': event['event'],
                    'currency': event['currency'],
                    'impact': impact,
                    'time_until': time_str,
                    'message': f'⚠️ HIGH IMPACT: {event["event"]} ({event["currency"]}) - {time_str}'
                }
            
            # ===== 7. Event is approaching (warning) =====
            if time_diff < self.warning_minutes and time_diff > 0:
                return {
                    'safe': True,
                    'warning': True,
                    'event': event['event'],
                    'currency': event['currency'],
                    'impact': impact,
                    'time_until': f"{time_diff:.0f} min",
                    'message': f'⚠️ Event soon: {event["event"]} ({event["currency"]}) in {time_diff:.0f} min'
                }
        
        # ===== 8. No relevant events =====
        return {
            'safe': True,
            'warning': False,
            'message': 'No high-impact news in the next hour'
        }
    
    def add_event(self, date: str, time: str, currency: str, event: str, impact: str = 'HIGH'):
        """
        Manually add a news event.
        
        Args:
            date: Date in 'YYYY-MM-DD' format
            time: Time in 'HH:MM' format
            currency: Currency code ('USD', 'EUR', etc.)
            event: Event name
            impact: 'HIGH', 'MEDIUM', or 'LOW'
        """
        try:
            event_date = datetime.strptime(date, "%Y-%m-%d").date()
            
            if event_date not in self.event_calendar:
                self.event_calendar[event_date] = []
            
            # Check for duplicate
            for existing in self.event_calendar[event_date]:
                if (existing['time'] == time and 
                    existing['currency'] == currency and 
                    existing['event'] == event):
                    logger.info(f'Event already exists: {date} {time} {currency} {event}')
                    return
            
            self.event_calendar[event_date].append({
                'time': time,
                'currency': currency,
                'event': event,
                'impact': impact
            })
            
            self._save_events()
            logger.info(f'✅ Added news event: {date} {time} {currency} {event} ({impact})')
        except Exception as e:
            logger.warning(f'Failed to add news event: {e}')
    
    def remove_event(self, date: str, time: str, currency: str, event: str):
        """Remove a news event"""
        try:
            event_date = datetime.strptime(date, "%Y-%m-%d").date()
            
            if event_date in self.event_calendar:
                self.event_calendar[event_date] = [
                    e for e in self.event_calendar[event_date]
                    if not (e['time'] == time and e['currency'] == currency and e['event'] == event)
                ]
                
                # Remove empty date entries
                if not self.event_calendar[event_date]:
                    del self.event_calendar[event_date]
                
                self._save_events()
                logger.info(f'✅ Removed news event: {date} {time} {currency} {event}')
        except Exception as e:
            logger.warning(f'Failed to remove news event: {e}')
    
    def get_today_events(self) -> List[Dict]:
        """Get all events for today"""
        today = datetime.now().date()
        return self.event_calendar.get(today, [])
    
    def get_upcoming_events(self, hours: int = 24) -> List[Dict]:
        """Get upcoming events within the next hours"""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        today = now.date()
        
        upcoming = []
        
        for date, events in self.event_calendar.items():
            if date < today or date > cutoff.date():
                continue
            
            for event in events:
                event_time = self._parse_time(event['time'])
                if event_time is None:
                    continue
                
                event_datetime = datetime.combine(date, event_time.time())
                if event_datetime > now and event_datetime <= cutoff:
                    upcoming.append({
                        'date': date.isoformat(),
                        'time': event['time'],
                        'currency': event['currency'],
                        'event': event['event'],
                        'impact': event.get('impact', 'HIGH')
                    })
        
        return sorted(upcoming, key=lambda x: x['date'] + ' ' + x['time'])
    
    def get_status(self) -> Dict:
        """Get overall filter status"""
        today = datetime.now().date()
        return {
            'today_events': len(self.event_calendar.get(today, [])),
            'total_events': sum(len(events) for events in self.event_calendar.values()),
            'buffer_minutes': self.buffer_minutes,
            'warning_minutes': self.warning_minutes,
            'timezone_offset': self.timezone_offset,
            'file_path': self.news_file
        }
    
    def clear_history(self, days: Optional[int] = None):
        """
        Clear old events.
        
        Args:
            days: If provided, keep only events from the last 'days' days
        """
        if days is None:
            # Clear all events
            self.event_calendar.clear()
            self._save_events()
            logger.info('✅ All news events cleared')
            return
        
        cutoff = datetime.now().date() - timedelta(days=days)
        old_dates = [d for d in self.event_calendar.keys() if d < cutoff]
        
        for date in old_dates:
            del self.event_calendar[date]
        
        self._save_events()
        logger.info(f'✅ Cleared events older than {days} days')
    
    def __str__(self) -> str:
        """String representation"""
        total = sum(len(events) for events in self.event_calendar.values())
        return f"NewsFilter(total_events={total}, buffer={self.buffer_minutes}m)"
# ============================================================
# 7. COMPLETE ADVANCED STRATEGY WITH DOLLAR ENGINE - FIXED
# ============================================================

class AdvancedTradingStrategy:
    """
    Complete trading strategy with ALL filters:
    1. Z-Score (entry signal)
    2. Dollar Engine (USD strength filter)
    3. Volume Confirmation
    4. Trend Filter
    5. Support/Resistance
    6. News Filter
    """
    
    def __init__(self, config: Dict = None, risk_manager: Any = None, zscore_engine=None):
        """
        Args:
            config: Configuration dictionary
            risk_manager: Optional RiskManager instance for cold start checks
        """
        self.config = config or {}
        self.risk_manager = risk_manager  # ✅ FIX: Store reference
        if zscore_engine:
            self.zscore_engine = zscore_engine  # ← USE CONTROLLER'S ENGINE
        else:
            # Z-Score Engine
            self.zscore_engine = ZScoreEngineWithThresholds(
                lookback=config.get('zscore_lookback', 50),
                entry_threshold=config.get('zscore_entry', 2.0),
                exit_threshold=config.get('zscore_exit', 0.5)
            )
            self.zscore_engine.regime_detector = MarketRegimeDetector(lookback=50)
            self.zscore_engine.trend_multiplier = 0.7
            self.zscore_engine.counter_multiplier = 1.5
            self.strategy = AdvancedTradingStrategy(config, zscore_engine=self.zscore_engine)
        
        # DOLLAR ENGINE
        self.dollar_engine = DollarEngine(lookback=config.get('dollar_lookback', 20))
        # ===== CREATE AGENTS =====
        print("\n📊 Initializing Trading Agents...")
        self.agent_u = AgentU_Liquidity()
        self.agent_p = AgentP_CrossPair()
        self.agent_d = AgentD_BBands()
        print("✅ All agents initialized!")
        # 1-Hour Trend Filter
        self.hourly_trend = SimpleHourlyTrendFilter()
        
        # Other filters
        self.volume_filter = VolumeConfirmation(
            lookback=config.get('volume_lookback', 20),
            volume_threshold=config.get('volume_threshold', 1.5)
        )
        
        self.trend_filter = TrendFilter(
            lookback=config.get('trend_lookback', 50),
            ema_fast=config.get('ema_fast', 10),
            ema_slow=config.get('ema_slow', 30)
        )
        
        self.sr_filter = SupportResistance(
            lookback=config.get('sr_lookback', 100),
            min_touches=config.get('sr_min_touches', 2),
            tolerance=config.get('sr_tolerance', 0.002)
        )
        
        self.news_filter = NewsFilter()
        
        # Filter weights
        self.filter_weights = {
            'dollar': config.get('dollar_weight', 0.35),
            'trend': config.get('trend_weight', 0.30),
            'volume': config.get('volume_weight', 0.15),
            'sr': config.get('sr_weight', 0.15),
            'news': config.get('news_weight', 0.05)
        }
        
        logger.info('=' * 60)
        logger.info('✅ ADVANCED STRATEGY INITIALIZED (with Dollar Engine)')
        logger.info('=' * 60)
        logger.info(f'   Filters: Dollar Engine, Volume, Trend, S/R, News')
        logger.info(f'   Filter Weights: {self.filter_weights}')
        logger.info(f'   Symbols: {len(self.zscore_engine.thresholds)}')
        logger.info('=' * 60)
    
    def update_dollar_engine(self, prices: Dict):
        """Update Dollar Engine with latest prices"""
        self.dollar_engine.update_prices(prices)
    
    def _is_cold_start(self) -> bool:
        """Check if we're in cold start mode"""
        if self.risk_manager is None:
            return False
        try:
            status = self.risk_manager.get_status()
            return status.get('cold_start_active', False)
        except:
            return False
    
    def analyze_signal(self, symbol: str, price: float, volume: float = 0, 
                   prices: Dict = None) -> Dict:
        """
        Full signal analysis with RELAXED filters (less restrictive).
        """
        # Update Dollar Engine if prices provided
        if prices:
               self.dollar_engine.update_prices(prices)
        
        # Update hourly trend
        self.hourly_trend.update_price(symbol, price)
        
        # 1. Get Z-Score signal
        zscore_result = self.zscore_engine.peek_zscore(symbol, price)
        
        # DEBUG: Log Z-score for extreme values
        if abs(zscore_result.get('z_score', 0)) > 1.5:
               logger.debug(f'🔍 {symbol}: Z={zscore_result.get("z_score", 0):+.2f} | Action={zscore_result.get("action", "HOLD")} | Confidence={zscore_result.get("confidence", 0)}')
        
        forced_signal = None
        
        # If Z-score is HOLD, check for forced signal
        if zscore_result['action'] == 'HOLD':
               forced_signal = self.get_smart_forced_signal(symbol, zscore_result)
               
               if forced_signal:
                     logger.info(f'⚡ SMART FORCED SIGNAL: {symbol} {forced_signal["action"]} | {forced_signal["force_reason"]}')
                     logger.info(f'   Confidence: {forced_signal["confidence"]:.0f}%')
                     logger.info(f'   {forced_signal["reasoning"]}')
                     
                     zscore_result['action'] = forced_signal['action']
                     zscore_result['confidence'] = forced_signal['confidence']
                     zscore_result['reasoning'] = forced_signal['reasoning']
                     zscore_result['forced'] = True
        
        # If still HOLD, return early
        if zscore_result['action'] == 'HOLD':
               return {
                     'action': 'HOLD',
                     'confidence': 0,
                     'price': price,
                     'symbol': symbol,
                     'zscore': zscore_result,
                     'filters': {},
                     'total_score': 0,
                     'reasoning': f'No Z-score signal: {zscore_result["reasoning"]}'
               }
        
        # 2. Check all filters (RELAXED)
        filter_results = {}
        filter_scores = []
        
        # ===== DOLLAR ENGINE FILTER - RELAXED =====
        dollar_result = self.dollar_engine.check_signal(symbol, zscore_result['action'])
        filter_results['dollar'] = dollar_result
        
        # ✅ RELAXED: Only block if USD is STRONG and strongly misaligned
        if not dollar_result['aligned']:
               usd_strength = abs(self.dollar_engine.usd_strength)
               if usd_strength > 20:  # Only block on strong USD movement
                     if not self._is_cold_start():
                          return {
                                  'action': 'HOLD',
                                  'confidence': 0,
                                  'price': price,
                                  'symbol': symbol,
                                  'zscore': zscore_result,
                                  'filters': filter_results,
                                  'total_score': 0,
                                  'all_filters_pass': False,
                                  'reasoning': f'Strong USD blocks: {dollar_result["message"]}',
                                  'filter_details': f"💵 {dollar_result['message']}",
                                  'dollar_status': self.dollar_engine.get_status()
                          }
               else:
                     # ✅ Allow trades even if slightly misaligned
                     logger.debug(f'⚠️ USD misaligned but weak ({usd_strength:.1f}) - allowing {symbol} {zscore_result["action"]}')
                     dollar_result['aligned'] = True  # Force pass for weak misalignment
                     dollar_result['message'] = f'⚠️ {dollar_result["message"]} (weak USD - allowing)'
        
        filter_scores.append({
               'name': 'dollar',
               'pass': dollar_result['aligned'],
               'score': abs(self.dollar_engine.usd_strength) / 100 if dollar_result['aligned'] else 0.3
        })
        
        # ===== VOLUME FILTER - RELAXED =====
        if volume > 0:
               volume_result = self.volume_filter.check_volume(symbol, volume)
               filter_results['volume'] = volume_result
               
               # ✅ RELAXED: Lower threshold from 1.5 to 1.0
               if volume_result['confirmed'] or volume_result.get('volume_ratio', 0) >= 0.7:
                     volume_result['confirmed'] = True
                     if volume_result.get('volume_ratio', 0) < 1.0:
                          volume_result['message'] = f'⚠️ Low but acceptable volume: {volume_result.get("volume_ratio", 0):.1f}x'
               
               filter_scores.append({
                     'name': 'volume',
                     'pass': volume_result['confirmed'],
                     'score': min(1.0, volume_result.get('volume_ratio', 0) / 1.0) if volume_result['confirmed'] else 0
               })
        else:
               if symbol in self.volume_filter.avg_volume:
                     avg_vol = self.volume_filter.avg_volume[symbol]
                     volume_result = self.volume_filter.check_volume(symbol, avg_vol * 1.0)
                     filter_results['volume'] = volume_result
                     
                     # ✅ RELAXED: Allow lower volume
                     if volume_result['confirmed'] or volume_result.get('volume_ratio', 0) >= 0.7:
                          volume_result['confirmed'] = True
                     
                     filter_scores.append({
                          'name': 'volume',
                          'pass': volume_result['confirmed'],
                          'score': min(1.0, volume_result.get('volume_ratio', 0.5) / 1.0)
                     })
               else:
                     filter_results['volume'] = {'confirmed': True, 'message': 'No volume data'}
                     filter_scores.append({'name': 'volume', 'pass': True, 'score': 0.7})
        
        # ===== TREND FILTER - RELAXED =====
        self.trend_filter.update_price(symbol, price)
        trend_result = self.trend_filter.check_trend(symbol, zscore_result['action'])
        filter_results['trend'] = trend_result
        
        # ✅ RELAXED: Allow trades in sideways or weak trends
        if not trend_result['aligned']:
               trend_strength = trend_result['trend']['strength']
               trend_direction = trend_result['trend']['direction']
               
               # Only block if trend is VERY strong (>80%) and clearly opposite
               if trend_strength > 80 and trend_direction != 'NEUTRAL':
                     if not self._is_cold_start():
                          return {
                                  'action': 'HOLD',
                                  'confidence': 0,
                                  'price': price,
                                  'symbol': symbol,
                                  'zscore': zscore_result,
                                  'filters': filter_results,
                                  'total_score': 0,
                                  'all_filters_pass': False,
                                  'reasoning': f'Strong trend blocks: {trend_result["message"]}',
                                  'filter_details': f"📈 {trend_result['message']}",
                                  'dollar_status': self.dollar_engine.get_status()
                          }
               else:
                     # ✅ Allow trade with warning
                     logger.debug(f'⚠️ Trend misaligned but weak ({trend_strength:.0f}%) - allowing {symbol} {zscore_result["action"]}')
                     trend_result['aligned'] = True
                     trend_result['message'] = f'⚠️ {trend_result["message"]} (weak trend - allowing)'
        
        filter_scores.append({
               'name': 'trend',
               'pass': trend_result['aligned'] or trend_result['trend']['direction'] == 'NEUTRAL',
               'score': trend_result['trend']['strength'] / 100 if trend_result['aligned'] else 0.4
        })
        
        # ===== HOURLY TREND FILTER - RELAXED =====
        hourly_result = self.hourly_trend.check_trend(symbol, zscore_result['action'])
        filter_results['hourly_trend'] = hourly_result
        
        # ✅ RELAXED: Use wider threshold (0.5% instead of 0.15%)
        # Check if price is EXTREMELY against trend (>0.5%)
        if not hourly_result['allowed']:
               if symbol in self.hourly_trend.price_history:
                     prices_list = [p for _, p in self.hourly_trend.price_history[symbol]]
                     if len(prices_list) >= 4:
                          current = prices_list[-1]
                          one_hour_ago = self.hourly_trend.get_price_1h_ago(symbol) or prices_list[-4]
                          
                          if one_hour_ago and one_hour_ago > 0:
                                  change_pct = ((current - one_hour_ago) / one_hour_ago) * 100
                                  # Only block if change is > 0.5% (was 0.15%)
                                  if abs(change_pct) > 0.5:
                                         if not self._is_cold_start():
                                               return {
                                                    'action': 'HOLD',
                                                    'confidence': 0,
                                                    'price': price,
                                                    'symbol': symbol,
                                                    'zscore': zscore_result,
                                                    'filters': filter_results,
                                                    'total_score': 0,
                                                    'all_filters_pass': False,
                                                    'reasoning': f'Strong hourly trend blocks: {hourly_result["message"]}',
                                                    'filter_details': f"⏰ {hourly_result['message']}",
                                                    'dollar_status': self.dollar_engine.get_status()
                                               }
                                  else:
                                         # ✅ Allow if change is minor
                                         hourly_result['allowed'] = True
                                         hourly_result['message'] = f'⚠️ {hourly_result["message"]} (small change - allowing)'
        
        filter_scores.append({
               'name': 'hourly_trend',
               'pass': hourly_result['allowed'],
               'score': 0.8 if hourly_result['allowed'] else 0.3
        })
        
        # ===== SUPPORT/RESISTANCE FILTER - RELAXED =====
        self.sr_filter.update_price(symbol, price)
        sr_result = self.sr_filter.check_levels(symbol, price, zscore_result['action'])
        filter_results['sr'] = sr_result
        
        # ✅ RELAXED: Use wider tolerance for S/R
        if not sr_result['safe']:
               # Check distance - only block if VERY close to level (<0.1%)
               distance = sr_result.get('distance', 1.0)
               if distance < 0.001:  # 0.1%
                     if not self._is_cold_start():
                          return {
                                  'action': 'HOLD',
                                  'confidence': 0,
                                  'price': price,
                                  'symbol': symbol,
                                  'zscore': zscore_result,
                                  'filters': filter_results,
                                  'total_score': 0,
                                  'all_filters_pass': False,
                                  'reasoning': f'Very close to S/R: {sr_result["message"]}',
                                  'filter_details': f"📉 {sr_result['message']}",
                                  'dollar_status': self.dollar_engine.get_status()
                          }
               else:
                     # ✅ Allow with warning
                     sr_result['safe'] = True
                     sr_result['message'] = f'⚠️ {sr_result["message"]} (not too close - allowing)'
        
        filter_scores.append({
               'name': 'sr',
               'pass': sr_result['safe'],
               'score': 0.7 if sr_result['safe'] else 0.4
        })
        
        # ===== NEWS FILTER - RELAXED =====
        news_result = self.news_filter.check_news(symbol)
        filter_results['news'] = news_result
        
        # ✅ RELAXED: Only block if news is IMMINENT (<15 minutes)
        if not news_result['safe']:
               time_until = news_result.get('time_until', '')
               if 'min' in time_until:
                     try:
                          minutes = float(time_until.split()[0])
                          if minutes < 15:  # Only block if <15 minutes away
                                  return {
                                         'action': 'HOLD',
                                         'confidence': 0,
                                         'price': price,
                                         'symbol': symbol,
                                         'zscore': zscore_result,
                                         'filters': filter_results,
                                         'total_score': 0,
                                         'all_filters_pass': False,
                                         'reasoning': f'Imminent news: {news_result["message"]}',
                                         'filter_details': f"📰 {news_result['message']}",
                                         'dollar_status': self.dollar_engine.get_status()
                                  }
                     except:
                          pass
               # ✅ Allow if news is further away
               news_result['safe'] = True
               news_result['message'] = f'⚠️ {news_result["message"]} (not imminent - allowing)'
        
        filter_scores.append({
               'name': 'news',
               'pass': news_result['safe'],
               'score': 0.8 if news_result['safe'] else 0.4
        })
        
        # ===== 3. Calculate total score =====
        total_score = 0
        total_weight = 0
        
        for fs in filter_scores:
               weight = self.filter_weights.get(fs['name'], 0.20)
               score = fs['score'] * weight if fs['pass'] else 0
               total_score += score
               total_weight += weight
        
        if total_weight > 0:
               total_score = (total_score / total_weight) * 100
        
        # ===== 4. Decision =====
        all_filters_pass = all(fs['pass'] for fs in filter_scores)
        
        # Calculate confidence
        base_confidence = zscore_result.get('confidence', 50)
        if total_score >= 50:
               boosted_confidence = min(95, base_confidence + (total_score - 50) * 0.2)
        else:
               boosted_confidence = base_confidence * (0.5 + total_score / 200)
        
        # Boost if Z-score is extreme
        z_score = zscore_result.get('z_score', 0)
        if boosted_confidence < 60 and abs(z_score) > 2.0:
               boosted_confidence = min(95, 60 + abs(z_score) * 5)
        
        # ✅ RELAXED: Lower confidence threshold from 50 to 40
        if boosted_confidence < 40:
               return {
                     'action': 'HOLD',
                     'confidence': 0,
                     'price': price,
                     'symbol': symbol,
                     'zscore': zscore_result,
                     'filters': filter_results,
                     'total_score': total_score,
                     'all_filters_pass': all_filters_pass,
                     'reasoning': f'Low confidence: {boosted_confidence:.0f}%',
                     'filter_details': self._format_filter_details(filter_results),
                     'dollar_status': self.dollar_engine.get_status()
               }
        
        return {
               'action': zscore_result['action'],
               'confidence': boosted_confidence,
               'price': price,
               'symbol': symbol,
               'zscore': zscore_result,
               'filters': filter_results,
               'total_score': total_score,
               'all_filters_pass': all_filters_pass,
               'reasoning': f'Z={z_score:+.2f} | Score: {total_score:.0f}%',
               'filter_details': self._format_filter_details(filter_results),
               'dollar_status': self.dollar_engine.get_status()
        }
    
    def check_reversal_potential(self, symbol: str, signal_action: str) -> Dict:
        """Check if price is showing reversal signals"""
        if symbol not in self.trend_filter.price_history:
            return {'confirmed': True, 'message': 'No trend data'}
        
        prices = list(self.trend_filter.price_history[symbol])
        if len(prices) < 10:
            return {'confirmed': True, 'message': 'Insufficient data'}
        
        current_price = prices[-1]
        prev_price = prices[-2] if len(prices) >= 2 else current_price
        
        if signal_action == 'BUY':
            recent_lows = min(prices[-5:])
            if current_price > recent_lows and current_price > prev_price:
                return {'confirmed': True, 'message': 'Bullish reversal pattern detected'}
            else:
                return {'confirmed': False, 'message': 'No bullish reversal pattern'}
        
        elif signal_action == 'SELL':
            recent_highs = max(prices[-5:])
            if current_price < recent_highs and current_price < prev_price:
                return {'confirmed': True, 'message': 'Bearish reversal pattern detected'}
            else:
                return {'confirmed': False, 'message': 'No bearish reversal pattern'}
        
        return {'confirmed': True, 'message': 'No action'}
    
    def get_smart_forced_signal(self, symbol: str, zscore_result: Dict) -> Optional[Dict]:
        """
        Smart forced signal detection.
        Only forces signals when Z-score exceeds threshold + buffer.
        """
        z_score = zscore_result.get('z_score', 0)
        entry_threshold = zscore_result.get('entry_threshold', 2.0)
        
        # Need at least 30 samples
        if zscore_result.get('samples', 0) < 30:
            return None
        
        # Force only if Z-score exceeds threshold by significant margin
        force_buffer = 0.5
        
        # Check trend alignment before forcing
        if hasattr(self, 'trend_filter') and symbol in self.trend_filter.price_history:
            self.trend_filter.update_price(symbol, self.zscore_engine.price_history.get(symbol, [None])[-1] if symbol in self.zscore_engine.price_history and self.zscore_engine.price_history[symbol] else None)
            if self.zscore_engine.price_history.get(symbol):
                trend_result = self.trend_filter.get_trend(symbol)
                if trend_result['direction'] != 'NEUTRAL' and trend_result['strength'] > 70:
                    if (z_score > 0 and trend_result['direction'] == 'UP') or (z_score < 0 and trend_result['direction'] == 'DOWN'):
                        return None
        
        # Check news
        if hasattr(self, 'news_filter'):
            news_result = self.news_filter.check_news(symbol)
            if not news_result['safe']:
                return None
        # ===== DOLLAR ENGINE WITH AGENTS =====
        if hasattr(self, 'dollar_engine') and hasattr(self.dollar_engine, 'check_signal_with_agents'):
                dollar_result = self.dollar_engine.check_signal_with_agents(
                        symbol=symbol,
                        signal_action=zscore_result['action'],
                        price=price,
                        prices=prices,
                        agent_u=self.agent_u if hasattr(self, 'agent_u') else None,
                        agent_p=self.agent_p if hasattr(self, 'agent_p') else None,
                        agent_d=self.agent_d if hasattr(self, 'agent_d') else None
                )
        else:
                # Fallback: regular dollar engine
                dollar_result = self.dollar_engine.check_signal(symbol, zscore_result['action'])
    
        # Check volume
        if hasattr(self, 'volume_filter'):
            if symbol in self.volume_filter.avg_volume:
                avg_vol = self.volume_filter.avg_volume[symbol]
                vol_result = self.volume_filter.check_volume(symbol, avg_vol * 1.2)
                if not vol_result['confirmed']:
                    return None
        
        # Force signal if extreme
        if z_score > entry_threshold + force_buffer:
            confidence = min(95, 80 + (z_score - entry_threshold - force_buffer) * 10)
            if confidence < 70:
                return None
            
            return {
                'action': 'SELL',
                'confidence': confidence,
                'reasoning': f'Extreme overbought: Z={z_score:.2f} (threshold: {entry_threshold})',
                'forced': True,
                'force_reason': f'Z={z_score:.2f} > {entry_threshold} + {force_buffer}'
            }
        
        elif z_score < -entry_threshold - force_buffer:
            confidence = min(95, 80 + (-z_score - entry_threshold - force_buffer) * 10)
            if confidence < 70:
                return None
            
            return {
                'action': 'BUY',
                'confidence': confidence,
                'reasoning': f'Extreme oversold: Z={z_score:.2f} (threshold: {entry_threshold})',
                'forced': True,
                'force_reason': f'Z={z_score:.2f} < -{entry_threshold} - {force_buffer}'
            }
        
        return None
    
    def _format_filter_details(self, filter_results: Dict) -> str:
        """Format filter results for display"""
        details = []
        for name, result in filter_results.items():
            if name == 'dollar':
                details.append(f"💵 {result.get('message', 'USD OK')}")
            elif name == 'volume':
                details.append(f"📊 {result.get('message', 'Volume OK')}")
            elif name == 'trend':
                details.append(f"📈 {result.get('message', 'Trend OK')}")
            elif name == 'hourly_trend':
                details.append(f"⏰ {result.get('message', 'Hourly OK')}")
            elif name == 'sr':
                details.append(f"📉 {result.get('message', 'S/R OK')}")
            elif name == 'news':
                details.append(f"📰 {result.get('message', 'News OK')}")
        return ' | '.join(details)
    
    def get_filter_status(self, symbol: str) -> Dict:
        """Get status of all filters for a symbol"""
        return {
            'zscore': self.zscore_engine.samples.get(symbol, 0),
            'dollar': self.dollar_engine.get_status(),
            'volume': self.volume_filter.get_volume_status(symbol) if hasattr(self.volume_filter, 'get_volume_status') else {},
            'trend': self.trend_filter.get_trend(symbol) if hasattr(self.trend_filter, 'get_trend') else {},
            'sr': self.sr_filter.get_level_summary(symbol) if hasattr(self.sr_filter, 'get_level_summary') else {},
        }
# ============================================================
# MAIN - FIXED
# ============================================================

if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('🚀 ADVANCED TRADING CONTROLLER (All Filters + Dollar Engine)')
    print('=' * 60)
    
    # ===== CONFIGURATION =====
    config = {
        'cycle_interval': 3,
        'min_confidence': 50,
        'daily_loss_limit': 999999,
        'weekly_loss_limit': 999999, # Effectively unlimited
        'max_positions': 20,
        'zscore_lookback': 50,
        'zscore_entry': 2.0,
        'zscore_exit': 0.5,
        'dollar_lookback': 20,
        'volume_lookback': 20,
        'volume_threshold': 1.5,
        'max_consecutive_losses': 999, 
        'trend_lookback': 50,
        'ema_fast': 10,
        'ema_slow': 30,
        'sr_lookback': 100,
        'sr_min_touches': 2,
        'sr_tolerance': 0.002,
        'dollar_weight': 0.35,
        'volume_weight': 0.15,
        'trend_weight': 0.30,
        'sr_weight': 0.15,
        'news_weight': 0.05,
        'cold_start_threshold': 3,
        'cold_start_min_win_rate': 0.4,
        'max_trades_per_day': 999,
        'log_level': 2,  # Verbose logging
        'max_trades_per_cycle': 999  # ← ADD THIS TO CONFIG
    }
    
    # ===== INITIALIZE CONTROLLER =====
    controller = AdvancedTradingController(config)
    
    # ===== FORCE RESET CORRUPTED P&L =====
    print('\n🔧 RESETTING CORRUPTED P&L...')
    try:
        controller.risk_manager.daily_pnl = 0.0
        controller.risk_manager.trades_today = 0
        controller.risk_manager.consecutive_losses = 0
        controller.risk_manager.daily_loss_limit = config.get('daily_loss_limit', 999999)
        controller.risk_manager.max_positions = config.get('max_positions', 20)
        print(f'✅ P&L Reset: ${controller.risk_manager.daily_pnl:.2f}')
        print(f'✅ Daily Loss Limit: ${controller.risk_manager.daily_loss_limit}')
        print(f'✅ Max Positions: {controller.risk_manager.max_positions}')
    except AttributeError as e:
        print(f'⚠️ Could not reset all risk attributes: {e}')
    
    # ===== FORCE COLD START COMPLETE =====
    print('\n🔧 FORCING COLD START COMPLETE...')
    try:
        # Override the controller's cold start state
        controller.risk_manager.cold_start_active = False
        controller.risk_manager.cold_start_samples = [
            {'win': True, 'pnl': 0.50, 'symbol': 'DEMO', 'action': 'BUY', 'timestamp': datetime.now().isoformat()},
            {'win': False, 'pnl': -0.30, 'symbol': 'DEMO', 'action': 'SELL', 'timestamp': datetime.now().isoformat()},
            {'win': True, 'pnl': 0.75, 'symbol': 'DEMO', 'action': 'BUY', 'timestamp': datetime.now().isoformat()}
        ]
        controller.risk_manager.cold_start_wins = 2
        controller.risk_manager.cold_start_losses = 1
        controller.risk_manager.cold_start_threshold = config.get('cold_start_threshold', 3)
        controller.risk_manager.cold_start_min_win_rate = config.get('cold_start_min_win_rate', 0.4)
        
        # Save state
        if hasattr(controller.risk_manager, '_save_cold_start_state'):
            controller.risk_manager._save_cold_start_state()
        
        print(f'✅ Cold Start Active: {controller.risk_manager.cold_start_active}')
        print(f'✅ Samples: {len(controller.risk_manager.cold_start_samples)}')
        print(f'✅ Win Rate: {(controller.risk_manager.cold_start_wins / len(controller.risk_manager.cold_start_samples) * 100):.0f}%')
    except AttributeError as e:
        print(f'⚠️ Could not set cold start state: {e}')
    
    # ===== TEST MT4 COMMUNICATION (Optional) =====
    print('\n🧪 TESTING MT4 COMMUNICATION...')
    try:
        test_symbol = 'EURUSD'
        test_price = controller.dashboard.get_price(test_symbol)
        
        if test_price > 0:
            print(f'   ✅ Got price for {test_symbol}: {test_price:.5f}')
            
            # Uncomment to actually send a test order
            # test_signal = {
            #     'action': 'BUY',
            #     'confidence': 85,
            #     'price': test_price,
            #     'symbol': test_symbol,
            #     'zscore': {'z_score': -2.5},
            #     'reasoning': 'TEST TRADE - Force execution',
            #     'filter_details': 'Test trade - bypassing filters'
            # }
            # result = controller.execute_trade(test_symbol, test_signal)
            # print(f'   📤 Test trade result: {result}')
        else:
            print(f'   ⚠️ Could not get price for {test_symbol}')
    except Exception as e:
        print(f'   ❌ MT4 test failed: {e}')
    
    print('\n' + '=' * 60)
    print('✅ Controller ready. Starting...')
    print('=' * 60 + '\n')
    
    # ===== RUN CONTROLLER =====
    try:
        controller.run()
    except KeyboardInterrupt:
        print('\n🛑 Stopped by user')
    except Exception as e:
        print(f'\n❌ Controller crashed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        controller.stop()
        print('\n✅ Controller stopped')