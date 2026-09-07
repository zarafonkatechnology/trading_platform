"""
Agent H: Fibonacci Agent - Identifies Fibonacci retracement and extension levels
Specializes in support/resistance using Fibonacci ratios
Enhanced with Velocity Filter + Adaptive Threshold + Trend Detection
"""

import logging
import random
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import deque

# Try imports with fallbacks
try:
    from backend.agents.base_agent import BaseAgent
except ImportError:
    try:
        from agents.base_agent import BaseAgent
    except ImportError:
        class BaseAgent:
            def __init__(self, name="BaseAgent", agent_type="General", specialization="General"):
                self.name = name
                self.agent_type = agent_type
                self.specialization = specialization

# Price imports with fallbacks
try:
    from price_cache_manager import get_price_for_agent, get_any_price, price_cache
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    def get_price_with_fallback(symbol, agent_name):
        return 0
    def get_any_price(symbol):
        return None
    class price_cache:
        @staticmethod
        def get_price(symbol, use_cache_fallback=True):
            return None
        @staticmethod
        def get_cached_price(symbol):
            return None

logger = logging.getLogger(__name__)


# ============================================================
# VELOCITY FILTER
# ============================================================

class VelocityFilter:
    """Prevents premature entries when momentum is still building."""
    
    def __init__(self, window: int = 5):
        self.window = window
        self.price_history = []
        self.velocity_history = []
    
    def update(self, price: float) -> Dict:
        """Update filter with new price."""
        self.price_history.append(price)
        if len(self.price_history) > self.window + 1:
            self.price_history.pop(0)
        
        if len(self.price_history) < 3:
            return {
                'velocity': 0.0,
                'momentum': 'STABLE',
                'is_accelerating': False,
                'can_enter': False
            }
        
        velocities = [self.price_history[i] - self.price_history[i-1] 
                      for i in range(1, len(self.price_history))]
        current_velocity = velocities[-1]
        self.velocity_history.append(current_velocity)
        
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[-2]
            is_accelerating = (current_velocity > 0 and acceleration > 0) or \
                              (current_velocity < 0 and acceleration < 0)
        else:
            acceleration = 0.0
            is_accelerating = False
        
        if current_velocity > 0.1:
            momentum = 'RISING'
        elif current_velocity < -0.1:
            momentum = 'FALLING'
        else:
            momentum = 'STABLE'
        
        can_enter = abs(current_velocity) < 0.05 or is_accelerating
        
        return {
            'velocity': current_velocity,
            'momentum': momentum,
            'is_accelerating': is_accelerating,
            'can_enter': can_enter
        }


# ============================================================
# TREND DETECTOR
# ============================================================

class TrendDetector:
    """Detects market trend using moving averages."""
    
    def __init__(self, period: int = 20):
        self.period = period
        self.prices = deque(maxlen=period)
    
    def update(self, price: float) -> Dict:
        """Update trend detector with new price."""
        self.prices.append(price)
        
        if len(self.prices) < self.period:
            return {'trend': 'NEUTRAL', 'strength': 0.0}
        
        prices = list(self.prices)
        sma = sum(prices) / len(prices)
        current = prices[-1]
        
        # Calculate trend strength
        deviation = (current - sma) / sma * 100
        
        if deviation > 0.5:
            trend = 'UP'
            strength = min(100, 50 + deviation * 10)
        elif deviation < -0.5:
            trend = 'DOWN'
            strength = min(100, 50 + abs(deviation) * 10)
        else:
            trend = 'SIDEWAYS'
            strength = 30
        
        return {
            'trend': trend,
            'strength': strength,
            'deviation': deviation,
            'sma': sma
        }


class AgentHFibonacci(BaseAgent):
    """
    Fibonacci Agent - Identifies Fibonacci retracement and extension levels
    Enhanced with Velocity Filter + Adaptive Threshold + Trend Detection
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_H",
            agent_type="Fibonacci Specialist",
            specialization="Fibonacci Retracement & Extension Levels"
        )
        
        # ===== FIBONACCI RATIOS =====
        self.FIB_RATIOS = {
            'retracement': [0.236, 0.382, 0.5, 0.618, 0.786],
            'extension': [1.272, 1.414, 1.618, 2.0, 2.618]
        }
        
        # ===== STATE =====
        self.last_high = 0.0
        self.last_low = 0.0
        self.current_levels = {}
        self.nearby_levels = []
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== TREND DETECTOR =====
        self.trend_detector = TrendDetector(period=20)
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_threshold = 0.5  # 0.5% default
        self.current_threshold = 0.5
        
        # ===== PRICE CACHE =====
        self._price_cache = {}
        
        # ===== STATISTICS =====
        self.levels_hit = 0
        self.signals_generated = 0
        
        logger.info(f"   ✅ {self.name} (Fibonacci Specialist) initialized")
        logger.info(f"      📊 Fibonacci Ratios: {len(self.FIB_RATIOS['retracement'])} retracement, {len(self.FIB_RATIOS['extension'])} extension")
        logger.info(f"      📊 Velocity Filter: Active")
        logger.info(f"      📊 Adaptive Threshold: Active")
    
    # ============================================================
    # PRICE RETRIEVAL
    # ============================================================
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price with fallback."""
        if symbol in self._price_cache:
            cached_time, cached_price = self._price_cache[symbol]
            if (datetime.now() - cached_time).seconds < 10:
                return cached_price
        
        try:
            price = get_price_with_fallback(symbol, self.name)
            if price > 0:
                self._price_cache[symbol] = (datetime.now(), price)
                return price
        except:
            pass
        
        return 0.0
    
    # ============================================================
    # ADAPTIVE THRESHOLD
    # ============================================================
    
    def _get_adaptive_threshold(self, volatility: float) -> float:
        """
        Calculate adaptive Fibonacci level proximity threshold.
        Higher volatility → wider tolerance for "near" levels.
        """
        if volatility < 0.005:
            return 0.3  # Tight tolerance in low volatility
        elif volatility < 0.015:
            return 0.5  # Default (0.5%)
        elif volatility < 0.03:
            return 0.8  # Wider tolerance in high volatility
        else:
            return 1.2  # Much wider in extreme volatility
    
    # ============================================================
    # FIBONACCI CALCULATIONS
    # ============================================================
    
    def calculate_fib_levels(self, high: float, low: float, direction: str = 'up') -> Dict:
        """
        Calculate Fibonacci levels based on swing high/low.
        """
        range_size = high - low
        levels = {}
        
        if direction == 'up' or direction == 'UP':
            # Uptrend - retracement from high
            for ratio in self.FIB_RATIOS['retracement']:
                levels[f'fib_{ratio}'] = high - (range_size * ratio)
            for ratio in self.FIB_RATIOS['extension']:
                levels[f'fib_ext_{ratio}'] = high + (range_size * (ratio - 1))
        else:
            # Downtrend - retracement from low
            for ratio in self.FIB_RATIOS['retracement']:
                levels[f'fib_{ratio}'] = low + (range_size * ratio)
            for ratio in self.FIB_RATIOS['extension']:
                levels[f'fib_ext_{ratio}'] = low - (range_size * (ratio - 1))
        
        return levels
    
    def find_key_levels(self, price: float, fib_levels: Dict, threshold: float = 0.5) -> List[Dict]:
        """
        Identify which Fibonacci levels are near current price.
        """
        nearby_levels = []
        
        for level_name, level_price in fib_levels.items():
            if level_price <= 0:
                continue
            
            distance_pct = abs((price - level_price) / price) * 100
            
            if distance_pct < threshold:
                # Determine level strength
                if '0.618' in level_name or '0.786' in level_name:
                    strength = 'STRONG'
                    confidence_boost = 15
                elif '0.382' in level_name or '0.5' in level_name:
                    strength = 'MEDIUM'
                    confidence_boost = 10
                elif 'extension' in level_name:
                    strength = 'EXTENSION'
                    confidence_boost = 5
                else:
                    strength = 'WEAK'
                    confidence_boost = 0
                
                nearby_levels.append({
                    'level': level_name,
                    'price': round(level_price, 4),
                    'distance': round(distance_pct, 2),
                    'strength': strength,
                    'confidence_boost': confidence_boost
                })
        
        # Sort by distance (closest first)
        nearby_levels.sort(key=lambda x: x['distance'])
        
        return nearby_levels
    
    def _detect_trend(self, high: float, low: float, current_price: float) -> str:
        """Detect trend based on price position relative to high/low."""
        range_size = high - low
        if range_size == 0:
            return 'SIDEWAYS'
        
        position = (current_price - low) / range_size
        
        if position > 0.7:
            return 'UP'
        elif position < 0.3:
            return 'DOWN'
        else:
            return 'SIDEWAYS'
    
    # ============================================================
    # MAIN ANALYSIS
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Complete Fibonacci analysis with Velocity Filter + Adaptive Threshold.
        """
        try:
            # ===== GET SYMBOL & PRICE =====
            symbol = signal_data.get('symbol', signal_data.get('pair', 'UNKNOWN'))
            current_price = signal_data.get('price', 0)
            volatility = signal_data.get('volatility', 0.01)
            
            if current_price <= 0:
                current_price = self.get_current_price(symbol)
            
            if current_price <= 0:
                return self._hold_response("No price available")
            
            # ===== GET HIGH/LOW =====
            candles = signal_data.get('candles', [])
            
            if candles and len(candles) > 0:
                highs = [c['high'] for c in candles[-20:] if c.get('high', 0) > 0]
                lows = [c['low'] for c in candles[-20:] if c.get('low', 0) > 0]
                
                if highs and lows:
                    self.last_high = max(highs)
                    self.last_low = min(lows)
                else:
                    self.last_high = current_price * 1.02
                    self.last_low = current_price * 0.98
            else:
                # Use price-based estimates
                self.last_high = current_price * 1.02
                self.last_low = current_price * 0.98
            
            # ===== DETECT TREND =====
            trend_result = self.trend_detector.update(current_price)
            trend = trend_result['trend']
            
            # If trend is neutral, use price position
            if trend == 'SIDEWAYS' or trend == 'NEUTRAL':
                trend = self._detect_trend(self.last_high, self.last_low, current_price)
            
            # ===== ADAPTIVE THRESHOLD =====
            self.current_threshold = self._get_adaptive_threshold(volatility)
            
            # ===== CALCULATE FIBONACCI LEVELS =====
            self.current_levels = self.calculate_fib_levels(
                self.last_high, 
                self.last_low, 
                trend
            )
            
            # ===== FIND NEARBY LEVELS =====
            self.nearby_levels = self.find_key_levels(
                current_price, 
                self.current_levels,
                self.current_threshold
            )
            
            # ===== VELOCITY FILTER =====
            velocity_result = self.velocity_filter.update(current_price)
            
            # ===== GENERATE SIGNAL =====
            action = 'HOLD'
            confidence = 50
            reasoning = "No key Fibonacci levels nearby"
            
            if self.nearby_levels:
                key_level = self.nearby_levels[0]
                level_name = key_level['level']
                level_price = key_level['price']
                distance = key_level['distance']
                strength = key_level['strength']
                boost = key_level['confidence_boost']
                
                # Check velocity
                can_enter = velocity_result['can_enter']
                
                # Generate signal based on level type
                if 'fib_ext' in level_name:
                    # Extension levels - potential reversal
                    if trend == 'UP':
                        action = 'SELL'  # Extended in uptrend
                        base_confidence = 70
                    else:
                        action = 'BUY'   # Extended in downtrend
                        base_confidence = 70
                    reasoning = f"Fibonacci Extension {level_name} at {level_price:.4f}"
                
                elif '0.618' in level_name or '0.786' in level_name:
                    # Strong retracement levels
                    if trend == 'UP':
                        action = 'BUY'   # Retracement support
                        base_confidence = 75
                    else:
                        action = 'SELL'  # Retracement resistance
                        base_confidence = 75
                    reasoning = f"Fibonacci {level_name} support/resistance at {level_price:.4f}"
                
                elif '0.382' in level_name or '0.5' in level_name:
                    # Medium levels
                    if trend == 'UP':
                        action = 'BUY'   # Support
                        base_confidence = 65
                    else:
                        action = 'SELL'  # Resistance
                        base_confidence = 65
                    reasoning = f"Fibonacci {level_name} level at {level_price:.4f}"
                
                else:
                    # Other levels
                    action = 'HOLD'
                    base_confidence = 55
                    reasoning = f"Near Fibonacci {level_name} at {level_price:.4f}"
                
                # Apply confidence boost
                confidence = min(95, base_confidence + boost)
                
                # Velocity override
                if action != 'HOLD':
                    if velocity_result['momentum'] == 'RISING' and action == 'SELL':
                        if velocity_result['is_accelerating']:
                            confidence = max(40, confidence - 20)
                            reasoning += " | ⚠️ Velocity rising - selling against momentum"
                            action = 'HOLD'
                    elif velocity_result['momentum'] == 'FALLING' and action == 'BUY':
                        if velocity_result['is_accelerating']:
                            confidence = max(40, confidence - 20)
                            reasoning += " | ⚠️ Velocity falling - buying against momentum"
                            action = 'HOLD'
                
                # Update stats
                self.levels_hit += 1
                if action != 'HOLD':
                    self.signals_generated += 1
            else:
                # No key levels nearby
                action = 'HOLD'
                confidence = 50
                reasoning = f"No Fibonacci levels within {self.current_threshold}%"
            
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': action,
                'confidence': round(confidence, 1),
                'reasoning': reasoning,
                'fib_levels': self.current_levels,
                'nearby_levels': self.nearby_levels,
                'trend': trend,
                'velocity': velocity_result,
                'adaptive_threshold': self.current_threshold,
                'high': self.last_high,
                'low': self.last_low,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': reason,
            'fib_levels': {},
            'nearby_levels': [],
            'trend': 'NEUTRAL',
            'velocity': None,
            'adaptive_threshold': self.current_threshold if hasattr(self, 'current_threshold') else 0.5,
            'high': 0,
            'low': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    # ============================================================
    # LEGACY PREDICT METHOD (for compatibility)
    # ============================================================
    
    def predict(self, signal_data: Dict, market_features: Dict) -> Tuple[str, float]:
        """
        Legacy predict method - returns (action, confidence) tuple.
        """
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast."""
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above_cloud'] += 1
            elif price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probs['above_cloud'] > 60:
            vote = 'BUY'
            conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    
    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            'name': self.name,
            'type': self.agent_type,
            'levels_hit': self.levels_hit,
            'signals_generated': self.signals_generated,
            'adaptive_threshold': self.current_threshold if hasattr(self, 'current_threshold') else 0.5,
            'last_high': self.last_high,
            'last_low': self.last_low,
            'nearby_levels': len(self.nearby_levels) if hasattr(self, 'nearby_levels') else 0,
            'timestamp': datetime.now().isoformat()
        }