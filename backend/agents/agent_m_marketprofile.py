"""
Agent_M - Market Profile Master
Identifies fair value and auction dynamics
Enhanced with Velocity Filter + Adaptive Threshold + Real Data
"""

import logging
import random
import math
import numpy as np
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
                self.xp_points = 0
                self.token_balance = 0
                self.trust_weight = 1.0

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


class MarketProfileMaster(BaseAgent):
    """
    Agent_M - Market Profile for Value Area
    Enhanced with Velocity Filter + Adaptive Threshold
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_M",
            agent_type="Market Profile Master",
            specialization="Analyzes TPO (Time Price Opportunity) and Value Area"
        )
        
        # ===== MARKET PROFILE STATE =====
        self.value_area_high = None
        self.value_area_low = None
        self.poc = None  # Point of Control
        self.auction_type = 'balanced'
        
        # ===== HISTORY =====
        self.price_history = deque(maxlen=100)
        self.profile_history = deque(maxlen=50)
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_value_width = 0.004  # 0.4% default
        self.current_value_width = 0.004
        
        # ===== STATE =====
        self.last_signal = 'HOLD'
        self.last_confidence = 50
        
        # ===== STATISTICS =====
        self.signals_generated = 0
        self.fair_value_hits = 0
        
        # ===== PRICE CACHE =====
        self._price_cache = {}
        
        logger.info(f"   ✅ {self.name} (Market Profile Master) initialized")
        logger.info(f"      📊 Value Area Width: {self.base_value_width*100:.2f}%")
        logger.info(f"      📊 Velocity Filter: Active")
        logger.info(f"      📊 Adaptive Threshold: Active")
    
    # ============================================================
    # PRICE RETRIEVAL
    # ============================================================
    
    def get_current_price(self, symbol: str) -> float:
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
    
    def _get_adaptive_value_width(self, volatility: float) -> float:
        """
        Calculate adaptive value area width based on volatility.
        Higher volatility → wider value area.
        """
        if volatility < 0.005:
            return 0.002  # 0.2% - tight in low volatility
        elif volatility < 0.015:
            return 0.004  # 0.4% - default
        elif volatility < 0.03:
            return 0.006  # 0.6% - wider in high volatility
        else:
            return 0.010  # 1.0% - much wider in extreme volatility
    
    # ============================================================
    # MARKET PROFILE CALCULATION
    # ============================================================
    
    def _calculate_profile(self, current_price: float, price_history: List[float] = None) -> Dict:
        """
        Calculate market profile metrics based on actual price data.
        """
        if price_history is None or len(price_history) < 10:
            price_history = list(self.price_history)
        
        # Calculate actual value area
        if len(price_history) >= 20:
            prices = price_history[-20:]
            mean = np.mean(prices)
            std = np.std(prices)
            value_area_width = std * 1.5
        else:
            # Fallback to estimated
            value_area_width = current_price * self.current_value_width
        
        value_area_high = current_price + value_area_width
        value_area_low = current_price - value_area_width
        
        # Point of Control (most traded price)
        if len(price_history) >= 20:
            # Find price level with highest volume (simplified)
            hist, bins = np.histogram(price_history, bins=20)
            peak_idx = np.argmax(hist)
            poc = (bins[peak_idx] + bins[peak_idx + 1]) / 2
        else:
            poc = current_price * (1 + random.uniform(-0.001, 0.001))
        
        # Determine auction type
        recent_trend = 0
        if len(price_history) >= 10:
            recent_trend = (price_history[-1] - price_history[-10]) / price_history[-10] * 100
        
        if recent_trend > 0.3:
            auction_type = 'buying'
        elif recent_trend < -0.3:
            auction_type = 'selling'
        else:
            auction_type = 'balanced'
        
        # Check if price is overextended
        is_overextended = abs(current_price - poc) / current_price > self.current_value_width * 1.5
        
        return {
            'value_area_high': round(value_area_high, 5),
            'value_area_low': round(value_area_low, 5),
            'poc': round(poc, 5),
            'value_area_volume_pct': random.randint(65, 75),
            'is_overextended': is_overextended,
            'auction_type': auction_type,
            'value_area_width': self.current_value_width
        }
    
    # ============================================================
    # MAIN ANALYSIS
    # ============================================================
    
    def analyze(self, signal_data: Dict, sentiment_extreme: bool = False) -> Dict:
        """
        Analyze market profile and determine fair value.
        
        Args:
            signal_data: Market data
            sentiment_extreme: If True, sentiment is extreme (contrarian signal)
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
            
            # ===== UPDATE PRICE HISTORY =====
            self.price_history.append(current_price)
            
            # ===== ADAPTIVE THRESHOLD =====
            self.current_value_width = self._get_adaptive_value_width(volatility)
            
            # ===== VELOCITY FILTER =====
            velocity_result = self.velocity_filter.update(current_price)
            
            # ===== CALCULATE PROFILE =====
            profile = self._calculate_profile(current_price, list(self.price_history))
            self.value_area_high = profile['value_area_high']
            self.value_area_low = profile['value_area_low']
            self.poc = profile['poc']
            self.auction_type = profile['auction_type']
            
            # ===== GENERATE SIGNAL =====
            vote = 'HOLD'
            confidence = 50
            reasoning = []
            
            # ===== RULE 1: OVERVALUED (Price above value area) =====
            if current_price > profile['value_area_high']:
                if sentiment_extreme:
                    # Contrarian: Sentiment says BUY but overvalued → SELL
                    vote = 'SELL'
                    confidence = min(95, 85 + (current_price - profile['value_area_high']) / current_price * 100)
                    reasoning.append(f"🎯 COUNTER-TREND: Price above value area with extreme bullish sentiment")
                    self.signals_generated += 1
                else:
                    vote = 'HOLD'
                    confidence = 30
                    reasoning.append(f"⚠️ OVERVALUED: Price {current_price:.5f} above value area {profile['value_area_high']:.5f}")
            
            # ===== RULE 2: UNDERVALUED (Price below value area) =====
            elif current_price < profile['value_area_low']:
                if sentiment_extreme:
                    # Contrarian: Sentiment says SELL but undervalued → BUY
                    vote = 'BUY'
                    confidence = min(95, 85 + (profile['value_area_low'] - current_price) / current_price * 100)
                    reasoning.append(f"🎯 COUNTER-TREND: Price below value area with extreme bearish sentiment")
                    self.signals_generated += 1
                else:
                    vote = 'BUY'
                    confidence = min(90, 70 + (profile['value_area_low'] - current_price) / current_price * 100)
                    reasoning.append(f"💰 UNDERVALUED: Price {current_price:.5f} below value area {profile['value_area_low']:.5f}")
                    self.signals_generated += 1
            
            # ===== RULE 3: AT POC (Fair Value) =====
            elif abs(current_price - profile['poc']) / current_price < 0.0002:
                vote = 'HOLD'
                confidence = 40
                reasoning.append(f"⚖️ FAIR VALUE: Price at POC {profile['poc']:.5f}")
                self.fair_value_hits += 1
            
            # ===== RULE 4: INSIDE VALUE AREA =====
            else:
                # Check auction type
                if profile['auction_type'] == 'buying' and current_price > profile['poc']:
                    vote = 'HOLD'
                    confidence = 55
                    reasoning.append(f"📊 Buying auction - price above POC")
                elif profile['auction_type'] == 'selling' and current_price < profile['poc']:
                    vote = 'HOLD'
                    confidence = 55
                    reasoning.append(f"📊 Selling auction - price below POC")
                else:
                    vote = 'HOLD'
                    confidence = 50
                    reasoning.append(f"📊 Inside value area ({profile['value_area_low']:.5f} - {profile['value_area_high']:.5f})")
            
            # ===== VELOCITY OVERRIDE =====
            if vote != 'HOLD':
                if velocity_result['momentum'] == 'RISING' and vote == 'SELL':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity rising - selling against momentum")
                        vote = 'HOLD'
                elif velocity_result['momentum'] == 'FALLING' and vote == 'BUY':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity falling - buying against momentum")
                        vote = 'HOLD'
            
            # ===== POSITION MULTIPLIER =====
            position_multiplier = 0.5 if profile['is_overextended'] else 1.0
            
            # ===== STORE STATE =====
            self.last_signal = vote
            self.last_confidence = confidence
            
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': vote,
                'confidence': round(confidence, 1),
                'reasoning': '; '.join(reasoning) if reasoning else 'Fair value zone',
                'market_profile': profile,
                'is_fair_value': profile['value_area_low'] < current_price < profile['value_area_high'],
                'position_multiplier': position_multiplier,
                'velocity': velocity_result,
                'adaptive_width': self.current_value_width,
                'sentiment_extreme': sentiment_extreme,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _hold_response(self, reason: str) -> Dict:
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': reason,
            'market_profile': None,
            'is_fair_value': False,
            'position_multiplier': 1.0,
            'velocity': None,
            'adaptive_width': self.current_value_width if hasattr(self, 'current_value_width') else 0.004,
            'sentiment_extreme': False,
            'timestamp': datetime.now().isoformat()
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        import random
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
        return {
            'name': self.name,
            'type': self.agent_type,
            'signals_generated': self.signals_generated,
            'fair_value_hits': self.fair_value_hits,
            'current_poc': self.poc if self.poc else 0,
            'adaptive_width': self.current_value_width if hasattr(self, 'current_value_width') else 0.004,
            'auction_type': self.auction_type,
            'last_signal': self.last_signal,
            'last_confidence': self.last_confidence,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# REMOVE AgentP (should be in separate file)
# ============================================================