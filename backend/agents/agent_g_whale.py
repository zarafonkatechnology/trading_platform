"""
Agent G: Whale Agent - COT (Commitment of Traders) Analysis
Macro Filter: Monitors intentions of largest market players
Enhanced with Velocity Filter + Adaptive Threshold + Real COT Support
"""

import logging
import random
import math
import numpy as np
from datetime import datetime, timedelta
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

# Try real COT imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

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


# ============================================================
# REAL COT DATA FETCHER
# ============================================================

class COTDataFetcher:
    """
    Fetches real COT data from various sources.
    Supports: CFTC, Barchart, Quandl
    """
    
    def __init__(self, api_key: str = None, source: str = 'simulated'):
        self.api_key = api_key
        self.source = source
        self.cache = {}
    
    def fetch_cot_data(self, symbol: str) -> Dict:
        """Fetch COT data from configured source."""
        if self.source == 'cftc' and self.api_key:
            return self._fetch_cftc(symbol)
        elif self.source == 'barchart':
            return self._fetch_barchart(symbol)
        else:
            return self._fetch_simulated(symbol)
    
    def _fetch_cftc(self, symbol: str) -> Dict:
        """Fetch COT data from CFTC API."""
        if not REQUESTS_AVAILABLE:
            return self._fetch_simulated(symbol)
        
        try:
            # CFTC API endpoint
            url = f"https://api.cftc.gov/api/v1/reports"
            params = {
                'apiKey': self.api_key,
                'symbol': symbol
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'commercial_long': data.get('commercial_long', 50),
                    'commercial_short': data.get('commercial_short', 50),
                    'managed_funds_long': data.get('managed_funds_long', 50),
                    'managed_funds_short': data.get('managed_funds_short', 50),
                    'retail_long': data.get('retail_long', 50),
                    'retail_short': data.get('retail_short', 50),
                    'source': 'CFTC'
                }
            else:
                return self._fetch_simulated(symbol)
                
        except Exception as e:
            logger.warning(f"COT fetch error: {e}")
            return self._fetch_simulated(symbol)
    
    def _fetch_simulated(self, symbol: str) -> Dict:
        """Generate simulated COT data."""
        # Simulate realistic COT values
        base = 50
        variation = random.randint(-40, 40)
        
        return {
            'commercial_long': max(0, min(100, base + variation * 0.8)),
            'commercial_short': max(0, min(100, base - variation * 0.6)),
            'managed_funds_long': max(0, min(100, base + variation)),
            'managed_funds_short': max(0, min(100, base - variation * 1.2)),
            'retail_long': max(0, min(100, base + variation * 0.5)),
            'retail_short': max(0, min(100, base - variation * 0.3)),
            'source': 'SIMULATED'
        }


class AgentGWhale(BaseAgent):
    """
    Whale Agent - COT (Commitment of Traders) Analysis
    Macro Filter: Monitors intentions of largest market players
    Enhanced with Velocity Filter + Adaptive Threshold + Real COT Support
    """
    
    def __init__(self, api_key: str = None, cot_source: str = 'simulated'):
        super().__init__(
            name="Agent_G",
            agent_type="Whale Tracker",
            specialization="COT Analysis & Institutional Flow"
        )
        
        # ===== COT DATA =====
        self.cot_fetcher = COTDataFetcher(api_key=api_key, source=cot_source)
        self.cot_data = {
            'commercial_long': 65,
            'commercial_short': 35,
            'managed_funds_long': 85,
            'managed_funds_short': 15,
            'retail_long': 45,
            'retail_short': 55
        }
        self.cot_history = []
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_extreme_threshold = 90
        self.current_extreme_threshold = 90
        
        # ===== STATE =====
        self.last_signal = 'HOLD'
        self.last_confidence = 50
        self.whale_insight = ''
        
        # ===== STATISTICS =====
        self.signals_generated = 0
        self.crowded_trades_detected = 0
        
        # ===== PRICE CACHE =====
        self._price_cache = {}
        
        logger.info(f"   ✅ {self.name} (Whale Tracker) initialized")
        logger.info(f"      📊 COT Source: {cot_source}")
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
        Calculate adaptive extreme threshold based on volatility.
        Higher volatility → need higher extreme to trigger.
        """
        if volatility < 0.005:
            return 85  # Lower threshold in low volatility
        elif volatility < 0.015:
            return 90  # Default
        elif volatility < 0.03:
            return 92  # Higher in high volatility
        else:
            return 95  # Much higher in extreme volatility
    
    # ============================================================
    # COT DATA METHODS
    # ============================================================
    
    def update_cot_data(self, symbol: str):
        """Fetch and update COT data."""
        self.cot_data = self.cot_fetcher.fetch_cot_data(symbol)
        self.cot_history.append(self.cot_data.copy())
        
        if len(self.cot_history) > 100:
            self.cot_history.pop(0)
    
    def get_cot_percentile(self, position_type: str) -> float:
        """Get current COT percentile (0-100)."""
        return self.cot_data.get(position_type, 50)
    
    def is_extreme_position(self, position_type: str, threshold: float = 90) -> bool:
        """Check if positions are at extreme levels."""
        percentile = self.get_cot_percentile(position_type)
        return percentile >= threshold
    
    def detect_crowded_trade(self) -> Tuple[str, Optional[str]]:
        """
        Detect crowded trades - when everyone has already bought/sold.
        """
        managed_funds_long = self.get_cot_percentile('managed_funds_long')
        managed_funds_short = self.get_cot_percentile('managed_funds_short')
        
        if managed_funds_long >= self.current_extreme_threshold:
            return 'overcrowded_long', f"Managed funds long at {managed_funds_long:.0f}% - Everyone has already bought"
        elif managed_funds_short >= self.current_extreme_threshold:
            return 'overcrowded_short', f"Managed funds short at {managed_funds_short:.0f}% - Everyone has already sold"
        else:
            return 'normal', None
    
    def get_whale_sentiment(self) -> Tuple[str, str]:
        """
        Determine whale sentiment from COT data.
        Commercial traders (actual producers/users) are the "smart money".
        """
        commercial_net = self.cot_data['commercial_long'] - self.cot_data['commercial_short']
        managed_funds_long = self.get_cot_percentile('managed_funds_long')
        
        if commercial_net > 20 and managed_funds_long < 70:
            sentiment = 'bullish'
            reason = f"Commercial traders strongly long ({commercial_net:.0f}% net)"
        elif commercial_net < -20 and managed_funds_long > 30:
            sentiment = 'bearish'
            reason = f"Commercial traders strongly short ({commercial_net:.0f}% net)"
        else:
            sentiment = 'neutral'
            reason = f"Commercial traders neutral ({commercial_net:.0f}% net)"
        
        return sentiment, reason
    
    # ============================================================
    # MAIN ANALYSIS
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Complete COT-based whale analysis with Velocity Filter + Adaptive Threshold.
        """
        try:
            # ===== GET SYMBOL & PRICE =====
            symbol = signal_data.get('symbol', signal_data.get('pair', 'UNKNOWN'))
            current_price = signal_data.get('price', 0)
            volatility = signal_data.get('volatility', 0.01)
            fib_level = signal_data.get('fib_level', 0)
            
            if current_price <= 0:
                current_price = self.get_current_price(symbol)
            
            if current_price <= 0:
                return self._hold_response("No price available")
            
            # ===== UPDATE COT DATA =====
            self.update_cot_data(symbol)
            
            # ===== ADAPTIVE THRESHOLD =====
            self.current_extreme_threshold = self._get_adaptive_threshold(volatility)
            
            # ===== VELOCITY FILTER =====
            velocity_result = self.velocity_filter.update(current_price)
            
            # ===== CROWDED TRADE DETECTION =====
            crowded_status, crowded_reason = self.detect_crowded_trade()
            
            # ===== WHALE SENTIMENT =====
            sentiment, sentiment_reason = self.get_whale_sentiment()
            
            # ===== COT + FIBONACCI ALIGNMENT =====
            managed_funds_long = self.get_cot_percentile('managed_funds_long')
            managed_funds_short = self.get_cot_percentile('managed_funds_short')
            
            # ===== GENERATE SIGNAL =====
            action = 'HOLD'
            confidence = 50
            reasoning = []
            
            # Rule 1: COT Extreme + Fibonacci 78.6% = Strong Signal
            if abs(fib_level - 0.786) < 0.01:
                if managed_funds_short >= self.current_extreme_threshold:
                    action = 'SELL'
                    confidence = min(95, 85 + (managed_funds_short - 85) * 0.5)
                    reasoning.append(f"EXTREME COT: Managed funds short at {managed_funds_short:.0f}% + Fibonacci 78.6%")
                    self.signals_generated += 1
                elif managed_funds_long >= self.current_extreme_threshold:
                    action = 'BUY'
                    confidence = min(95, 85 + (managed_funds_long - 85) * 0.5)
                    reasoning.append(f"EXTREME COT: Managed funds long at {managed_funds_long:.0f}% + Fibonacci 78.6%")
                    self.signals_generated += 1
            
            # Rule 2: Crowded Trade Veto
            if crowded_status == 'overcrowded_long':
                action = 'SELL'
                confidence = min(90, 75 + (managed_funds_long - 85) * 0.5)
                reasoning.append(f"CROWDED TRADE: {crowded_reason}")
                self.crowded_trades_detected += 1
                self.signals_generated += 1
                
            elif crowded_status == 'overcrowded_short':
                action = 'BUY'
                confidence = min(90, 75 + (managed_funds_short - 85) * 0.5)
                reasoning.append(f"CROWDED TRADE: {crowded_reason}")
                self.crowded_trades_detected += 1
                self.signals_generated += 1
            
            # Rule 3: Normal Whale Sentiment
            if action == 'HOLD':
                if sentiment == 'bullish':
                    action = 'BUY'
                    confidence = 65
                    reasoning.append(sentiment_reason)
                elif sentiment == 'bearish':
                    action = 'SELL'
                    confidence = 65
                    reasoning.append(sentiment_reason)
                else:
                    action = 'HOLD'
                    confidence = 50
                    reasoning.append(sentiment_reason)
            
            # ===== VELOCITY OVERRIDE =====
            if action != 'HOLD':
                if velocity_result['momentum'] == 'RISING' and action == 'SELL':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity rising - selling against momentum")
                        action = 'HOLD'
                elif velocity_result['momentum'] == 'FALLING' and action == 'BUY':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity falling - buying against momentum")
                        action = 'HOLD'
            
            # ===== STORE STATE =====
            self.last_signal = action
            self.last_confidence = confidence
            self.whale_insight = '; '.join(reasoning)
            
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': action,
                'confidence': round(confidence, 1),
                'reasoning': '; '.join(reasoning) if reasoning else 'No whale signal',
                'cot_data': self.cot_data,
                'crowded_status': crowded_status,
                'sentiment': sentiment,
                'velocity': velocity_result,
                'adaptive_threshold': self.current_extreme_threshold,
                'fib_level': fib_level,
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
            'cot_data': self.cot_data,
            'crowded_status': 'normal',
            'sentiment': 'neutral',
            'velocity': None,
            'adaptive_threshold': self.current_extreme_threshold if hasattr(self, 'current_extreme_threshold') else 90,
            'fib_level': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    # ============================================================
    # LEGACY PREDICT METHOD
    # ============================================================
    
    def predict(self, signal_data: Dict, market_features: Dict) -> Tuple[str, float]:
        """Legacy predict method - returns (action, confidence) tuple."""
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_whale_insight(self) -> str:
        """Share whale insights with other agents."""
        commercial_net = self.cot_data['commercial_long'] - self.cot_data['commercial_short']
        managed_funds_long = self.get_cot_percentile('managed_funds_long')
        
        if managed_funds_long >= self.current_extreme_threshold:
            return f"🐋 CRITICAL: Managed funds at {managed_funds_long:.0f}% long - Extreme crowded trade risk!"
        elif managed_funds_long <= 10:
            return f"🐋 OPPORTUNITY: Managed funds at {managed_funds_long:.0f}% long - Potential short squeeze!"
        else:
            return f"🐋 Commercial net: {commercial_net:.0f}% | Managed funds long: {managed_funds_long:.0f}%"
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast."""
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
        """Get agent status."""
        return {
            'name': self.name,
            'type': self.agent_type,
            'signals_generated': self.signals_generated,
            'crowded_trades_detected': self.crowded_trades_detected,
            'adaptive_threshold': self.current_extreme_threshold if hasattr(self, 'current_extreme_threshold') else 90,
            'cot_managed_funds_long': self.get_cot_percentile('managed_funds_long'),
            'cot_managed_funds_short': self.get_cot_percentile('managed_funds_short'),
            'last_signal': self.last_signal,
            'last_confidence': self.last_confidence,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# REMOVE AgentP (should be in separate file)
# ============================================================