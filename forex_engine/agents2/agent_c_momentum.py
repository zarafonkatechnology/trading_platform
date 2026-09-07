# backend/agents/agent_c_momentum.py
"""
Agent_C - Momentum / Pair Agent (FOREX ADAPTED)
Now serves as Pair Agent for Forex with momentum-based trading
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
import logging
import numpy as np
import random
from datetime import datetime
import sys
import os

# ============================================
# HANDLE BASE AGENT IMPORT
# ============================================
try:
    from .base_agent import BaseAgent
except ImportError:
    try:
        from backend.agents.base_agent import BaseAgent
    except ImportError:
        try:
            from base_agent import BaseAgent
        except ImportError:
            # Create minimal BaseAgent if not found
            class BaseAgent:
                def __init__(self, name="BaseAgent", agent_type="General", specialization="General"):
                    self.name = name
                    self.agent_type = agent_type
                    self.specialization = specialization
                    self.xp_points = 0
                    self.token_balance = 0
                    self.trust_weight = 1.0
                    self.total_votes = 0
                    self.correct_votes = 0
                    self.vote_accuracy = 0.0
                    self.knowledge_shared_count = 0
                    self.timeframe = None
                    self.role = None
                
                def get_status(self):
                    return {
                        'name': self.name,
                        'type': self.agent_type,
                        'specialization': self.specialization,
                        'xp_points': self.xp_points,
                        'token_balance': self.token_balance,
                        'trust_weight': self.trust_weight
                    }
                
                def update_from_reward(self, was_correct, xp_gained=0, xp_lost=0, asset=None, timeframe=None):
                    if was_correct:
                        self.xp_points += xp_gained or 10
                        self.correct_votes += 1
                    else:
                        self.xp_points = max(0, self.xp_points - (xp_lost or 5))
                    self.total_votes += 1
                    if self.total_votes > 0:
                        self.vote_accuracy = self.correct_votes / self.total_votes
                    return {'success': True}
            
            print("⚠️ BaseAgent not found - using minimal BaseAgent")

# Try importing price helpers
try:
    from price_cache_manager import get_price_for_agent, get_any_price
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    try:
        from backend.utils.price_cache_manager import get_price_for_agent, get_any_price
        from backend.utils.price_helper import get_price_with_fallback, get_price_with_details
    except ImportError:
        def get_price_for_agent(agent_name, symbol):
            return None
        def get_any_price(symbol):
            return None
        def get_price_with_fallback(symbol, agent_name):
            return 0
        def get_price_with_details(symbol, agent_name):
            return {'mid': 0}
        print("⚠️ Price helpers not found - using dummy functions")

logger = logging.getLogger(__name__)

class AgentCMomentum(BaseAgent):
    """
    Agent C - Momentum / Pair Agent (FOREX)
    Handles Forex pair trading with momentum-based strategies:
    1. Multi-timeframe momentum analysis
    2. RSI divergence detection
    3. MACD momentum confirmation
    4. Rate of Change (ROC) analysis
    5. Momentum breakout detection
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_C",
            agent_type="Pair Agent",
            specialization="Forex Momentum & Pair Trading"
        )
        
        # ============================================
        # FOREX PAIRS CONFIGURATION
        # ============================================
        self.forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY']
        self.current_pair = "EURUSD"
        
        # ============================================
        # PAIR STATE MANAGEMENT
        # ============================================
        self.pair_states = {}
        for pair in self.forex_pairs:
            self.pair_states[pair] = {
                'price_history': deque(maxlen=200),
                'close_history': deque(maxlen=200),
                'high_history': deque(maxlen=200),
                'low_history': deque(maxlen=200),
                'momentum_history': deque(maxlen=100),
                'rsi_history': deque(maxlen=50),
                'macd_history': deque(maxlen=50),
                'position': 0,
                'entry_price': 0.0,
                'signal': 'HOLD',
                'confidence': 50,
                'momentum_score': 0.0,
                'rsi_value': 50.0,
                'macd_value': 0.0,
                'macd_signal': 0.0,
                'consecutive_momentum': 0,
                'breakout_detected': False,
                'divergence_detected': False,
            }
        
        # ============================================
        # MOMENTUM PARAMETERS
        # ============================================
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.momentum_periods = [5, 10, 20, 50]
        self.breakout_period = 20
        self.momentum_threshold = 0.02  # 2% momentum threshold
        self.confidence_threshold = 60
        
        # ============================================
        # GEAR CONFIGURATION (from your gear system)
        # ============================================
        self.gear_config = {
            'EURUSD': {'gear_ratio': 1.2, 'gear_type': 'INVERSE'},
            'GBPUSD': {'gear_ratio': 1.1, 'gear_type': 'INVERSE'},
            'USDJPY': {'gear_ratio': 0.8, 'gear_type': 'DIRECT'},
            'AUDUSD': {'gear_ratio': 0.9, 'gear_type': 'INVERSE'},
            'USDCAD': {'gear_ratio': 0.7, 'gear_type': 'DIRECT'},
            'EURGBP': {'gear_ratio': 0.5, 'gear_type': 'CROSS'},
            'EURJPY': {'gear_ratio': 0.6, 'gear_type': 'CROSS'},
        }
        
        print(f"   ✅ {self.name} (Pair Agent) initialized")
        print(f"      Tracking {len(self.forex_pairs)} currency pairs")
        print(f"      Momentum periods: {self.momentum_periods}")
        print(f"      RSI period: {self.rsi_period}, MACD: {self.macd_fast}/{self.macd_slow}/{self.macd_signal}")
    
    # ============================================
    # CORE MOMENTUM INDICATORS
    # ============================================
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = 0
        losses = 0
        
        for i in range(len(prices) - period, len(prices) - 1):
            diff = prices[i+1] - prices[i]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)
        
        if losses == 0:
            return 100.0
        
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        
        return min(100, max(0, rsi))
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
        
        # Calculate EMAs
        def ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            multiplier = 2 / (period + 1)
            ema_value = data[0]
            for price in data[1:]:
                ema_value = (price * multiplier) + (ema_value * (1 - multiplier))
            return ema_value
        
        # Get MACD line
        fast_ema = ema(prices, fast)
        slow_ema = ema(prices, slow)
        macd_line = fast_ema - slow_ema
        
        # Get signal line
        signal_line = ema(prices, signal)  # Simplified
        
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_roc(self, prices: List[float], period: int) -> float:
        """Calculate Rate of Change"""
        if len(prices) < period + 1:
            return 0.0
        
        current = prices[-1]
        previous = prices[-period - 1]
        
        if previous == 0:
            return 0.0
        
        return (current - previous) / previous
    
    def calculate_momentum_score(self, prices: List[float]) -> float:
        """
        Calculate composite momentum score from multiple periods
        """
        if len(prices) < max(self.momentum_periods) + 1:
            return 0.0
        
        scores = []
        weights = [0.4, 0.3, 0.2, 0.1]  # Higher weight for shorter periods
        
        for period, weight in zip(self.momentum_periods, weights):
            roc = self.calculate_roc(prices, period)
            scores.append(roc * weight)
        
        return sum(scores)
    
    def detect_divergence(self, prices: List[float], rsi_values: List[float]) -> str:
        """
        Detect RSI divergence (bullish or bearish)
        """
        if len(prices) < 20 or len(rsi_values) < 20:
            return 'NONE'
        
        # Check for bullish divergence (price makes lower low, RSI makes higher low)
        price_lows = [prices[i] for i in range(-20, -1) if prices[i] < prices[i-1]]
        rsi_lows = [rsi_values[i] for i in range(-20, -1) if rsi_values[i] < rsi_values[i-1]]
        
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            if price_lows[-1] < price_lows[-2] and rsi_lows[-1] > rsi_lows[-2]:
                return 'BULLISH'
            elif price_lows[-1] > price_lows[-2] and rsi_lows[-1] < rsi_lows[-2]:
                return 'BEARISH'
        
        return 'NONE'
    
    def detect_breakout(self, prices: List[float], period: int = 20) -> Dict:
        """
        Detect momentum breakouts
        """
        if len(prices) < period + 1:
            return {'breakout': False, 'direction': 'NONE', 'strength': 0}
        
        recent_prices = prices[-period:]
        high = max(recent_prices)
        low = min(recent_prices)
        current = prices[-1]
        
        # Calculate breakout level
        range_size = (high - low) / low
        breakout_threshold = 0.01  # 1% breakout threshold
        
        if current > high * (1 + breakout_threshold):
            return {
                'breakout': True,
                'direction': 'BULLISH',
                'strength': min(100, (current / high - 1) * 100)
            }
        elif current < low * (1 - breakout_threshold):
            return {
                'breakout': True,
                'direction': 'BEARISH',
                'strength': min(100, (low / current - 1) * 100)
            }
        
        return {'breakout': False, 'direction': 'NONE', 'strength': 0}
    
    # ============================================
    # MAIN ANALYSIS METHOD
    # ============================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Main analysis function - analyzes momentum for all pairs
        """
        try:
            # Get current pair
            pair = signal_data.get('pair', 'EURUSD')
            current_price = signal_data.get('price', 0)
            
            if current_price == 0:
                current_price = signal_data.get('current_price', 0)
            
            # Get candles
            candles = signal_data.get('candles', [])
            if not candles:
                candles = signal_data.get(f'{pair}_candles', [])
            
            if not candles:
                return self._hold_response(pair, "No candle data available")
            
            # Extract OHLC
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 50:
                return self._hold_response(pair, f"Insufficient data ({len(closes)}/50)")
            
            # Update pair state
            state = self.pair_states[pair]
            state['close_history'].extend(closes)
            state['high_history'].extend(highs)
            state['low_history'].extend(lows)
            state['price_history'].append(current_price)
            
            # ============================================
            # CALCULATE MOMENTUM INDICATORS
            # ============================================
            
            # 1. RSI
            rsi = self.calculate_rsi(list(state['close_history']), self.rsi_period)
            state['rsi_value'] = rsi
            state['rsi_history'].append(rsi)
            
            # 2. MACD
            macd_data = self.calculate_macd(
                list(state['close_history']),
                self.macd_fast,
                self.macd_slow,
                self.macd_signal
            )
            state['macd_value'] = macd_data['macd']
            state['macd_signal'] = macd_data['signal']
            state['macd_history'].append(macd_data['macd'])
            
            # 3. Momentum Score
            momentum_score = self.calculate_momentum_score(list(state['close_history']))
            state['momentum_score'] = momentum_score
            state['momentum_history'].append(momentum_score)
            
            # 4. Breakout Detection
            breakout = self.detect_breakout(list(state['close_history']), self.breakout_period)
            state['breakout_detected'] = breakout['breakout']
            
            # 5. Divergence Detection
            divergence = self.detect_divergence(
                list(state['close_history']),
                list(state['rsi_history'])
            )
            state['divergence_detected'] = divergence != 'NONE'
            
            # ============================================
            # GENERATE SIGNAL
            # ============================================
            
            signal = self._generate_momentum_signal(pair, state)
            
            # Update position
            if signal['action'] == 'BUY':
                state['position'] = 1
                state['entry_price'] = current_price
            elif signal['action'] == 'SELL':
                state['position'] = -1
                state['entry_price'] = current_price
            elif signal['action'] == 'CLOSE':
                state['position'] = 0
            
            state['signal'] = signal['action']
            state['confidence'] = signal['confidence']
            
            # ============================================
            # BUILD RESULT
            # ============================================
            
            result = {
                'agent': self.name,
                'type': self.agent_type,
                'pair': pair,
                'vote': signal['action'],
                'confidence': signal['confidence'],
                'reasoning': signal['reason'],
                'momentum_score': round(momentum_score, 4),
                'rsi': round(rsi, 1),
                'macd': round(macd_data['macd'], 4),
                'macd_signal': round(macd_data['signal'], 4),
                'macd_histogram': round(macd_data['histogram'], 4),
                'breakout': breakout,
                'divergence': divergence,
                'position': state['position'],
                'entry_price': state['entry_price'],
                'current_price': current_price,
                'gear_ratio': self.gear_config.get(pair, {}).get('gear_ratio', 1.0),
                'gear_type': self.gear_config.get(pair, {}).get('gear_type', 'INVERSE'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Log decision
            if signal['action'] != 'HOLD':
                print(f"📊 {self.name} ({pair}): {signal['action']} ({signal['confidence']:.0f}%) - {signal['reason']}")
            
            return result
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return self._hold_response(signal_data.get('pair', 'EURUSD'), f"Error: {str(e)}")
    
    def _generate_momentum_signal(self, pair: str, state: Dict) -> Dict:
        """
        Generate momentum-based trading signal
        """
        action = 'HOLD'
        confidence = 50
        reasons = []
        
        momentum = state['momentum_score']
        rsi = state['rsi_value']
        macd = state['macd_value']
        macd_signal = state['macd_signal']
        
        # ============================================
        # SIGNAL GENERATION LOGIC
        # ============================================
        
        # Check for BULLISH signals
        bullish_signals = 0
        bearish_signals = 0
        
        # 1. Momentum Score
        if momentum > self.momentum_threshold:
            bullish_signals += 1
            reasons.append(f"Momentum positive ({momentum:.3f})")
        elif momentum < -self.momentum_threshold:
            bearish_signals += 1
            reasons.append(f"Momentum negative ({momentum:.3f})")
        
        # 2. RSI
        if rsi < self.rsi_oversold:
            bullish_signals += 1
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > self.rsi_overbought:
            bearish_signals += 1
            reasons.append(f"RSI overbought ({rsi:.1f})")
        
        # 3. MACD
        if macd > macd_signal and macd > 0:
            bullish_signals += 1
            reasons.append(f"MACD bullish ({macd:.4f} > {macd_signal:.4f})")
        elif macd < macd_signal and macd < 0:
            bearish_signals += 1
            reasons.append(f"MACD bearish ({macd:.4f} < {macd_signal:.4f})")
        
        # 4. Divergence
        if state.get('divergence_detected'):
            divergence = self.detect_divergence(
                list(state['close_history']),
                list(state['rsi_history'])
            )
            if divergence == 'BULLISH':
                bullish_signals += 2  # Higher weight for divergence
                reasons.append("Bullish divergence detected")
            elif divergence == 'BEARISH':
                bearish_signals += 2
                reasons.append("Bearish divergence detected")
        
        # 5. Breakout
        if state.get('breakout_detected'):
            breakout = self.detect_breakout(list(state['close_history']), self.breakout_period)
            if breakout['direction'] == 'BULLISH':
                bullish_signals += 1
                reasons.append(f"Bullish breakout ({breakout['strength']:.0f}%)")
            elif breakout['direction'] == 'BEARISH':
                bearish_signals += 1
                reasons.append(f"Bearish breakout ({breakout['strength']:.0f}%)")
        
        # ============================================
        # COMBINE SIGNALS
        # ============================================
        
        total_signals = bullish_signals + bearish_signals
        
        if total_signals >= 3:
            if bullish_signals > bearish_signals:
                action = 'BUY'
                confidence = min(90, 60 + (bullish_signals / total_signals) * 30)
                reasons.append(f"Strong bullish momentum ({bullish_signals}/{total_signals} signals)")
            elif bearish_signals > bullish_signals:
                action = 'SELL'
                confidence = min(90, 60 + (bearish_signals / total_signals) * 30)
                reasons.append(f"Strong bearish momentum ({bearish_signals}/{total_signals} signals)")
            else:
                action = 'HOLD'
                confidence = 50
                reasons.append("Mixed signals")
        elif total_signals >= 2:
            if bullish_signals > bearish_signals:
                action = 'BUY'
                confidence = 65
                reasons.append(f"Moderate bullish ({bullish_signals}/{total_signals} signals)")
            elif bearish_signals > bullish_signals:
                action = 'SELL'
                confidence = 65
                reasons.append(f"Moderate bearish ({bearish_signals}/{total_signals} signals)")
            else:
                action = 'HOLD'
                confidence = 50
                reasons.append("Mixed signals")
        else:
            action = 'HOLD'
            confidence = 50
            reasons.append("No clear momentum signals")
        
        # Check if in position and should exit
        if state['position'] != 0:
            # Exit if momentum weakens
            if abs(momentum) < self.momentum_threshold / 2:
                action = 'CLOSE'
                confidence = 70
                reasons.append("Momentum weakening - closing position")
            # Exit if RSI reaches extreme
            elif rsi > 85 or rsi < 15:
                action = 'CLOSE'
                confidence = 80
                reasons.append("Extreme RSI - closing position")
        
        return {
            'action': action,
            'confidence': confidence,
            'reason': '; '.join(reasons)
        }
    
    def _hold_response(self, pair: str, reason: str) -> Dict:
        """Generate HOLD response"""
        return {
            'agent': self.name,
            'type': self.agent_type,
            'pair': pair,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': reason,
            'momentum_score': 0.0,
            'rsi': 50.0,
            'macd': 0.0,
            'macd_signal': 0.0,
            'macd_histogram': 0.0,
            'breakout': {'breakout': False, 'direction': 'NONE', 'strength': 0},
            'divergence': 'NONE',
            'position': self.pair_states.get(pair, {}).get('position', 0),
            'entry_price': self.pair_states.get(pair, {}).get('entry_price', 0),
            'current_price': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    # ============================================
    # COMPATIBILITY METHODS
    # ============================================
    
    def predict(self, signal_data: Dict, market_features: Dict) -> Tuple[str, float]:
        """
        Original predict method - maintained for compatibility
        """
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def vote(self, signal_data: Dict, market_features: Dict) -> Dict:
        """
        Vote method for the agent voting system
        """
        result = self.analyze(signal_data)
        return {
            'agent': self.name,
            'pair': signal_data.get('pair', 'EURUSD'),
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_signal(self, signal_data: Dict = None) -> Dict:
        """
        Analyze signal for the trading cycle
        """
        if signal_data is None:
            signal_data = {}
        
        result = self.analyze(signal_data)
        
        return {
            'agent': self.name,
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'pair': signal_data.get('pair', 'EURUSD'),
            'momentum_score': result.get('momentum_score', 0),
            'rsi': result.get('rsi', 50),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict:
        """
        Get status of all tracked pairs
        """
        status = {
            'name': self.name,
            'type': self.agent_type,
            'pairs': {}
        }
        
        for pair, state in self.pair_states.items():
            status['pairs'][pair] = {
                'signal': state['signal'],
                'confidence': state['confidence'],
                'position': state['position'],
                'momentum_score': state['momentum_score'],
                'rsi': state['rsi_value'],
                'macd': state['macd_value'],
                'entry_price': state['entry_price'],
                'breakout_detected': state['breakout_detected'],
                'divergence_detected': state['divergence_detected']
            }
        
        return status
    
    def get_pair_status(self, pair: str) -> Dict:
        """Get status for a specific pair"""
        if pair not in self.pair_states:
            return {'error': f'Pair {pair} not tracked'}
        
        state = self.pair_states[pair]
        return {
            'pair': pair,
            'signal': state['signal'],
            'confidence': state['confidence'],
            'position': state['position'],
            'momentum_score': state['momentum_score'],
            'rsi': state['rsi_value'],
            'macd': state['macd_value'],
            'macd_signal': state['macd_signal'],
            'entry_price': state['entry_price'],
            'breakout_detected': state['breakout_detected'],
            'divergence_detected': state['divergence_detected'],
            'price_history_length': len(state['price_history'])
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        for pair in self.pair_states:
            self.pair_states[pair]['position'] = 0
            self.pair_states[pair]['entry_price'] = 0.0
            self.pair_states[pair]['consecutive_momentum'] = 0
        
        print(f"🔄 {self.name} daily stats reset")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Monte Carlo forecast for price direction probability
        """
        outcomes = {'above': 0, 'inside': 0, 'below': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above'] += 1
            elif price < cloud_bottom:
                outcomes['below'] += 1
            else:
                outcomes['inside'] += 1
        
        probabilities = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probabilities['above'] > 60:
            vote = 'BUY'
            conf = probabilities['above']
        elif probabilities['below'] > 60:
            vote = 'SELL'
            conf = probabilities['below']
        else:
            vote = 'HOLD'
            conf = probabilities['inside']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probabilities}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get price with automatic fallback to cache"""
        try:
            result = get_any_price(symbol)
            if result and result.get('mid'):
                return result['mid']
        except:
            pass
        return None


# ============================================
# BACKWARD COMPATIBILITY
# ============================================

class AgentC(AgentCMomentum):
    """
    Backward compatibility alias
    """
    def __init__(self):
        super().__init__()
        print("   ✅ Agent_C (Pair Agent) initialized (backward compatibility)")


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("TESTING AGENT_C - PAIR AGENT (MOMENTUM)")
    print("="*60 + "\n")
    
    # Create agent
    agent = AgentCMomentum()
    
    # Test data with candles
    test_data = {
        'pair': 'EURUSD',
        'price': 1.1000,
        'current_price': 1.1000,
        'candles': [
            {'high': 1.1020 + i*0.0005, 'low': 1.0980 + i*0.0005, 'close': 1.1000 + i*0.001}
            for i in range(60)
        ]
    }
    
    print("📊 Testing analysis...")
    result = agent.analyze(test_data)
    
    print(f"\n📈 Analysis Result:")
    print(f"   Agent: {result.get('agent', 'Unknown')}")
    print(f"   Pair: {result.get('pair', 'Unknown')}")
    print(f"   Vote: {result.get('vote', 'HOLD')}")
    print(f"   Confidence: {result.get('confidence', 0)}%")
    print(f"   Momentum Score: {result.get('momentum_score', 0):.4f}")
    print(f"   RSI: {result.get('rsi', 50):.1f}")
    print(f"   MACD: {result.get('macd', 0):.4f}")
    print(f"   MACD Signal: {result.get('macd_signal', 0):.4f}")
    print(f"   Breakout: {result.get('breakout', {}).get('direction', 'NONE')}")
    print(f"   Divergence: {result.get('divergence', 'NONE')}")
    print(f"   Position: {result.get('position', 0)}")
    
    print("\n✅ Test complete!")