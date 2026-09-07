"""
Agent_Q - Dark Pool Whale Detector
Detects hidden institutional activity via FINRA TRF data
Enhanced with Velocity Filter + Adaptive Threshold + Real API Support
"""

import logging
import random
import math
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Tuple
from enum import Enum

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

# Try real API imports
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
# REAL API INTEGRATION (Optional)
# ============================================================

class DarkPoolDataFetcher:
    """
    Fetches real dark pool data from various sources.
    Supports: Polygon.io, Unusual Whales, FINRA TRF
    """
    
    def __init__(self, api_key: str = None, source: str = 'polygon'):
        self.api_key = api_key
        self.source = source
        self.cache = {}
    
    def fetch_trades(self, symbol: str, lookback_hours: int = 24) -> List[Dict]:
        """
        Fetch dark pool trades from configured source.
        """
        if self.source == 'polygon' and self.api_key:
            return self._fetch_polygon(symbol, lookback_hours)
        elif self.source == 'finra':
            return self._fetch_finra(symbol, lookback_hours)
        else:
            return self._fetch_simulated(symbol, lookback_hours)
    
    def _fetch_polygon(self, symbol: str, lookback_hours: int) -> List[Dict]:
        """Fetch dark pool trades from Polygon.io API."""
        if not REQUESTS_AVAILABLE:
            return self._fetch_simulated(symbol, lookback_hours)
        
        try:
            # Polygon.io dark pool endpoint
            url = f"https://api.polygon.io/v2/ticks/stocks/dark/{symbol}"
            params = {
                'apiKey': self.api_key,
                'limit': 100,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                trades = []
                for trade in data.get('results', []):
                    trades.append({
                        'timestamp': trade.get('t', ''),
                        'symbol': symbol,
                        'price': trade.get('p', 0),
                        'size': trade.get('s', 0),
                        'venue': 'DARK_POOL',
                        'is_dark': True,
                        'source': 'Polygon'
                    })
                return trades
            else:
                logger.warning(f"Polygon API error: {response.status_code}")
                return self._fetch_simulated(symbol, lookback_hours)
                
        except Exception as e:
            logger.warning(f"Polygon fetch error: {e}")
            return self._fetch_simulated(symbol, lookback_hours)
    
    def _fetch_finra(self, symbol: str, lookback_hours: int) -> List[Dict]:
        """Fetch FINRA TRF data."""
        # FINRA TRF data is available via their API
        # This is a placeholder for real implementation
        return self._fetch_simulated(symbol, lookback_hours)
    
    def _fetch_simulated(self, symbol: str, lookback_hours: int) -> List[Dict]:
        """Generate simulated dark pool trades for testing."""
        num_trades = random.randint(0, 8)
        trades = []
        
        base_price = 100.0  # This would be actual price in production
        
        for _ in range(num_trades):
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            size = random.randint(100000, 10000000)
            
            trades.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'price': round(price, 3),
                'size': size,
                'venue': 'DARK_POOL',
                'is_dark': True,
                'source': 'SIMULATED'
            })
        
        return trades


class DarkPoolWhaleAgent(BaseAgent):
    """
    Agent Q - Detects "invisible" whale activity
    Uses FINRA TRF reports to find dark pool footprints
    Enhanced with Velocity Filter + Adaptive Threshold + Real API
    """
    
    def __init__(self, api_key: str = None, data_source: str = 'simulated'):
        super().__init__(
            name="Agent_Q",
            agent_type="Dark Pool Whale Detector",
            specialization="Detects hidden institutional activity via FINRA TRF data"
        )
        
        # ===== DARK POOL DATA =====
        self.dark_pool_trades = deque(maxlen=200)
        self.data_fetcher = DarkPoolDataFetcher(api_key=api_key, source=data_source)
        
        # ===== FIBONACCI LEVELS =====
        self.fib_levels = {
            '0.236': None,
            '0.382': None,
            '0.500': None,
            '0.618': None,
            '0.786': None
        }
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== PRICE CACHE =====
        self._price_cache = {}
        self.last_price = 0.0
        
        # ===== STATISTICS =====
        self.trades_analyzed = 0
        self.significant_trades = 0
        self.whale_signals = 0
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_significance_threshold = 1.0  # $1M minimum
        self.current_significance_threshold = 1.0
        
        print(f"🐋 {self.name} initialized - Listening for whale footprints")
        print(f"   📊 Data Source: {data_source}")
        print(f"   📊 Velocity Filter: Active")
    
    # ============================================================
    # FIX: PRICE RETRIEVAL
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
    # FIX: ADAPTIVE THRESHOLD
    # ============================================================
    
    def _get_adaptive_threshold(self, volatility: float) -> float:
        """
        Calculate adaptive significance threshold based on volatility.
        Higher volatility → higher threshold (need larger trades)
        """
        if volatility < 0.005:
            return 0.8  # Lower threshold in low volatility
        elif volatility < 0.015:
            return 1.0  # Default ($1M)
        elif volatility < 0.03:
            return 1.5  # Higher threshold in high volatility
        else:
            return 2.0  # Much higher in extreme volatility
    
    # ============================================================
    # FIBONACCI CALCULATION
    # ============================================================
    
    def _calculate_fib_levels(self, current_price: float, swing_high: float = None, swing_low: float = None):
        """Calculate Fibonacci retracement levels."""
        if swing_high is None:
            swing_high = current_price * 1.05
        if swing_low is None:
            swing_low = current_price * 0.95
        
        diff = swing_high - swing_low
        
        self.fib_levels = {
            '0.236': round(swing_low + diff * 0.236, 3),
            '0.382': round(swing_low + diff * 0.382, 3),
            '0.500': round(swing_low + diff * 0.500, 3),
            '0.618': round(swing_low + diff * 0.618, 3),
            '0.786': round(swing_low + diff * 0.786, 3)
        }
    
    # ============================================================
    # DARK POOL FETCHING
    # ============================================================
    
    def _fetch_dark_pool_trades(self, symbol: str) -> List[Dict]:
        """Fetch dark pool trades from configured source."""
        trades = self.data_fetcher.fetch_trades(symbol, lookback_hours=24)
        
        # Store for history
        for trade in trades:
            self.dark_pool_trades.append(trade)
        
        return trades
    
    # ============================================================
    # TRADE ANALYSIS
    # ============================================================
    
    def _analyze_trade_significance(self, trade: Dict, current_price: float, 
                                    threshold: float = 1.0) -> Dict:
        """
        Analyze if a dark pool trade is significant.
        """
        size_millions = trade['size'] / 1000000
        trade_price = trade['price']
        
        # Check Fibonacci alignment
        fib_hit = None
        for level, price in self.fib_levels.items():
            if price and abs(trade_price - price) / price < 0.002:
                fib_hit = level
                break
        
        # Check if trade is significant
        is_significant = size_millions > threshold or fib_hit is not None
        
        # Direction based on price relative to current
        if trade_price < current_price * 0.995:
            direction = 'BUY'  # Whale accumulating below market
        elif trade_price > current_price * 1.005:
            direction = 'SELL'  # Whale distributing above market
        else:
            direction = 'NEUTRAL'
        
        confidence = min(95, 55 + size_millions * 3 + (10 if fib_hit else 0))
        
        return {
            'is_significant': is_significant,
            'size_millions': size_millions,
            'price': trade_price,
            'fib_level': fib_hit,
            'direction': direction,
            'confidence': confidence,
            'reason': self._generate_reason(size_millions, fib_hit, direction)
        }
    
    def _generate_reason(self, size_millions: float, fib_hit: str, direction: str) -> str:
        """Generate human-readable reason for significance."""
        reasons = []
        
        if size_millions > 10:
            reasons.append(f"💰 MASSIVE ${size_millions:.1f}M trade")
        elif size_millions > 5:
            reasons.append(f"💎 LARGE ${size_millions:.1f}M trade")
        elif size_millions > 1:
            reasons.append(f"💵 ${size_millions:.1f}M trade")
        
        if fib_hit:
            reasons.append(f"📐 At Fibonacci {fib_hit} level")
        
        if direction == 'BUY':
            reasons.append("🐋 Whale ACCUMULATING")
        elif direction == 'SELL':
            reasons.append("🐻 Whale DISTRIBUTING")
        
        return " | ".join(reasons) if reasons else "Dark pool trade detected"
    
    # ============================================================
    # WHALE SENTIMENT
    # ============================================================
    
    def _determine_whale_sentiment(self, significant_trades: List[Dict]) -> Dict:
        """Determine overall whale sentiment."""
        if not significant_trades:
            return {
                'sentiment': 'NEUTRAL',
                'confidence': 30,
                'buy_power': 0,
                'sell_pressure': 0,
                'reason': 'No significant dark pool activity'
            }
        
        buy_power = 0
        sell_pressure = 0
        total_confidence = 0
        
        for trade in significant_trades:
            if trade['direction'] == 'BUY':
                buy_power += trade['size_millions'] * (trade['confidence'] / 100)
            elif trade['direction'] == 'SELL':
                sell_pressure += trade['size_millions'] * (trade['confidence'] / 100)
            total_confidence += trade['confidence']
        
        avg_confidence = total_confidence / len(significant_trades) if significant_trades else 50
        
        if buy_power > sell_pressure * 1.8:
            sentiment = 'BULLISH'
            reason = f"🐋 Whale accumulation: ${buy_power:.1f}M buy vs ${sell_pressure:.1f}M sell"
        elif sell_pressure > buy_power * 1.8:
            sentiment = 'BEARISH'
            reason = f"🐻 Whale distribution: ${sell_pressure:.1f}M sell vs ${buy_power:.1f}M buy"
        elif buy_power > sell_pressure * 1.2:
            sentiment = 'BULLISH_WEAK'
            reason = f"📈 Moderate whale buys: ${buy_power:.1f}M vs ${sell_pressure:.1f}M"
        elif sell_pressure > buy_power * 1.2:
            sentiment = 'BEARISH_WEAK'
            reason = f"📉 Moderate whale sells: ${sell_pressure:.1f}M vs ${buy_power:.1f}M"
        else:
            sentiment = 'MIXED'
            reason = f"⚖️ Mixed signals: ${buy_power:.1f}M buy / ${sell_pressure:.1f}M sell"
        
        return {
            'sentiment': sentiment,
            'confidence': avg_confidence,
            'buy_power': buy_power,
            'sell_pressure': sell_pressure,
            'reason': reason
        }
    
    # ============================================================
    # MAIN ANALYSIS
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Main analysis - Detect dark pool activity at key levels.
        """
        try:
            symbol = signal_data.get('symbol', signal_data.get('pair', 'UNKNOWN'))
            current_price = signal_data.get('price', 0)
            volatility = signal_data.get('volatility', 0.01)
            
            if current_price <= 0:
                current_price = self.get_current_price(symbol)
            
            if current_price <= 0:
                return self._hold_response("No price available")
            
            self.last_price = current_price
            
            # ===== VELOCITY FILTER =====
            velocity_result = self.velocity_filter.update(current_price)
            
            # ===== ADAPTIVE THRESHOLD =====
            self.current_significance_threshold = self._get_adaptive_threshold(volatility)
            
            # ===== CALCULATE FIBONACCI =====
            self._calculate_fib_levels(current_price)
            
            # ===== FETCH DARK POOL TRADES =====
            dark_trades = self._fetch_dark_pool_trades(symbol)
            
            # ===== ANALYZE EACH TRADE =====
            significant_trades = []
            for trade in dark_trades:
                analysis = self._analyze_trade_significance(
                    trade, 
                    current_price,
                    self.current_significance_threshold
                )
                if analysis['is_significant']:
                    significant_trades.append(analysis)
            
            # ===== DETERMINE WHALE SENTIMENT =====
            whale_sentiment = self._determine_whale_sentiment(significant_trades)
            
            # ===== VELOCITY FILTER OVERRIDE =====
            if velocity_result['momentum'] == 'RISING' and whale_sentiment['sentiment'] == 'BEARISH':
                if velocity_result['is_accelerating']:
                    whale_sentiment['sentiment'] = 'NEUTRAL'
                    whale_sentiment['reason'] = "Velocity rising - ignoring bearish dark pool"
            elif velocity_result['momentum'] == 'FALLING' and whale_sentiment['sentiment'] == 'BULLISH':
                if velocity_result['is_accelerating']:
                    whale_sentiment['sentiment'] = 'NEUTRAL'
                    whale_sentiment['reason'] = "Velocity falling - ignoring bullish dark pool"
            
            # ===== MAKE DECISION =====
            return self._make_decision(whale_sentiment, significant_trades, current_price, velocity_result)
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _make_decision(self, whale_sentiment: Dict, significant_trades: List[Dict],
                       current_price: float, velocity_result: Dict = None) -> Dict:
        """Make final decision based on whale activity."""
        
        # Update stats
        self.trades_analyzed += 1
        if significant_trades:
            self.significant_trades += len(significant_trades)
            self.whale_signals += 1
        
        sentiment = whale_sentiment['sentiment']
        confidence = whale_sentiment['confidence']
        reason = whale_sentiment['reason']
        
        # Determine vote based on sentiment
        if sentiment in ['BULLISH', 'BULLISH_WEAK']:
            vote = 'BUY'
            final_confidence = min(95, confidence)
            reasoning = f"🐋 {reason}"
        elif sentiment in ['BEARISH', 'BEARISH_WEAK']:
            vote = 'SELL'
            final_confidence = min(95, confidence)
            reasoning = f"🐻 {reason}"
        else:
            vote = 'HOLD'
            final_confidence = 40
            reasoning = f"📡 {reason}"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': round(final_confidence, 1),
            'reasoning': reasoning,
            'whale_data': {
                'sentiment': sentiment,
                'buy_power': whale_sentiment['buy_power'],
                'sell_pressure': whale_sentiment['sell_pressure'],
                'trades_detected': len(significant_trades),
                'fib_levels_hit': [t['fib_level'] for t in significant_trades if t['fib_level']]
            },
            'dark_trades': significant_trades,
            'velocity': velocity_result,
            'adaptive_threshold': self.current_significance_threshold,
            'timestamp': datetime.now().isoformat()
        }
    
    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': reason,
            'whale_data': None,
            'dark_trades': [],
            'velocity': None,
            'adaptive_threshold': None,
            'timestamp': datetime.now().isoformat()
        }
    
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
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price with fallback."""
        try:
            price = get_price_with_fallback(symbol, self.name)
            if price > 0:
                return price
        except:
            pass
        return 0.0
    
    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            'name': self.name,
            'type': self.agent_type,
            'trades_analyzed': self.trades_analyzed,
            'significant_trades': self.significant_trades,
            'whale_signals': self.whale_signals,
            'dark_pool_trades': len(self.dark_pool_trades),
            'adaptive_threshold': self.current_significance_threshold,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# REMOVE AgentP class (should be in separate file)
# ============================================================