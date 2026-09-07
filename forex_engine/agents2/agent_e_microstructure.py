# agents2/agent_e_microstructure.py
"""
Agent E - Microstructure / Base Pair Agent (FOREX ADAPTED)
Now serves as Base Pair Agent for Forex trading
"""

from typing import Dict, List, Optional
from collections import deque
import logging
import numpy as np
import random
from datetime import datetime
import sys
import os

# Try to import base agent
try:
    from .base_agent import BaseAgent
except ImportError:
    try:
        from backend.agents.base_agent import BaseAgent
    except ImportError:
        try:
            from base_agent import BaseAgent
        except ImportError:
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

logger = logging.getLogger(__name__)

class AgentEMicrostructure(BaseAgent):
    """
    Agent E - Microstructure / Base Pair Agent (FOREX)
    This is the Forex-adapted version that replaces the original
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_E",
            agent_type="Microstructure",
            specialization="Base Pair Agent - Forex Market Microstructure"
        )
        
        # Forex-specific parameters
        self.forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY']
        self.current_pair = "EURUSD"
        
        # Pair-specific state
        self.pair_states = {}
        for pair in self.forex_pairs:
            self.pair_states[pair] = {
                'position': 0,
                'price_history': deque(maxlen=200),
                'high_history': deque(maxlen=200),
                'low_history': deque(maxlen=200),
                'close_history': deque(maxlen=200),
                'spread_history': deque(maxlen=60),
                'z_score': 0.0,
                'z_score_ema': 0.0,
                'persistence': 0,
                'consecutive_outside': 0,
                'current_ma_fast': 0.0,
                'current_ma_medium': 0.0,
                'current_ma_slow': 0.0,
                'current_atr': 0.0,
                'current_efficiency_ratio': 0.5,
                'current_adaptive_period': 50,
                'entry_price': 0.0,
                'signal': 'HOLD',
                'confidence': 50
            }
        
        # Agent parameters
        self.fastest_period = 5
        self.slowest_period = 200
        self.atr_period = 14
        self.atr_multiplier = 1.8
        self.er_period = 20
        self.er_high_threshold = 0.55
        self.er_low_threshold = 0.25
        
        logger.info(f"   ✅ {self.name} (Forex Base Pair) initialized")
        logger.info(f"      Tracking pairs: {len(self.forex_pairs)}")
    
    # ============================================
    # CORE INDICATOR CALCULATIONS
    # ============================================
    
    def calculate_kaufman_efficiency_ratio(self, prices: List[float], period: int = 20) -> float:
        """Kaufman Efficiency Ratio - measures market efficiency"""
        if len(prices) < period:
            return 0.5
        
        recent_prices = prices[-period:]
        total_change = abs(recent_prices[-1] - recent_prices[0])
        sum_abs_change = sum(abs(recent_prices[i] - recent_prices[i-1]) 
                            for i in range(1, len(recent_prices)))
        
        if sum_abs_change == 0:
            return 0.5
        
        return round(total_change / sum_abs_change, 4)
    
    def calculate_adaptive_period(self, efficiency_ratio: float) -> int:
        """Adaptive period based on market efficiency"""
        adaptive_period = self.slowest_period - (efficiency_ratio * (self.slowest_period - self.fastest_period))
        period = int(round(adaptive_period))
        return max(self.fastest_period, min(self.slowest_period, period))
    
    def calculate_moving_averages(self, prices: List[float], periods: Dict) -> Dict:
        """Calculate multiple moving averages"""
        mas = {}
        for name, period in periods.items():
            if len(prices) >= period:
                mas[name] = sum(prices[-period:]) / period
            else:
                mas[name] = prices[-1] if prices else 0
        return mas
    
    def calculate_atr(self, highs: List[float], lows: List[float], 
                      closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_values.append(tr)
        
        return np.mean(tr_values[-period:]) if tr_values else 0
    
    def calculate_z_score(self, values: List[float]) -> Dict:
        """Calculate Z-score"""
        if len(values) < 10:
            return {'z_score': 0.0, 'mu': 0.0, 'sigma': 0.0, 'samples': len(values)}
        
        mu = sum(values) / len(values)
        variance = sum((x - mu) ** 2 for x in values) / len(values)
        sigma = np.sqrt(variance) if variance > 0 else 0.0001
        
        if sigma > 0:
            z_score = (values[-1] - mu) / sigma
        else:
            z_score = 0.0
        
        return {'z_score': z_score, 'mu': mu, 'sigma': sigma, 'samples': len(values)}
    
    # ============================================
    # MAIN ANALYSIS METHOD - FIXED
    # ============================================
    
    def analyze(self, market_data: Dict) -> Dict:
        """
        Main analyze method for compatibility with the controller
        """
        # Get pair from market_data
        pair = market_data.get('pair', 'EURUSD')
        
        # Call analyze_pair
        result = self.analyze_pair(pair, market_data)
        
        # Return in the format expected by the controller
        return {
            'pair': result.get('pair', pair),
            'vote': result.get('action', 'HOLD'),
            'confidence': result.get('confidence', 50),
            'reasoning': result.get('reason', ''),
            'position': result.get('position', 0),
            'z_score': result.get('z_score', 0),
            'z_score_ema': result.get('z_score_ema', 0),
            'persistence': result.get('persistence', 0),
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_pair(self, pair: str, market_data: Dict) -> Dict:
        """
        Analyze a single Forex pair
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            market_data: Market data dictionary
        
        Returns:
            Dictionary with analysis results
        """
        state = self.pair_states.get(pair, {})
        if not state:
            return self._hold_response(pair, "Pair not tracked")
        
        # Get price data
        current_price = market_data.get(pair, 0)
        
        # Get candles from market data
        candles = market_data.get('candles', [])
        if not candles:
            candles = market_data.get(f'{pair}_candles', [])
        
        if not candles:
            return self._hold_response(pair, "No candle data available")
        
        # Extract OHLC
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        if not closes or len(closes) < 50:
            return self._hold_response(pair, f"Insufficient data ({len(closes)}/50)")
        
        # Update state histories
        state['close_history'].extend(closes)
        state['high_history'].extend(highs)
        state['low_history'].extend(lows)
        
        # Get latest values
        current_price = closes[-1] if closes else current_price
        
        # ============================================
        # STEP 1: Kaufman Efficiency Ratio
        # ============================================
        efficiency_ratio = self.calculate_kaufman_efficiency_ratio(
            list(state['close_history']), period=self.er_period
        )
        state['current_efficiency_ratio'] = efficiency_ratio
        adaptive_period = self.calculate_adaptive_period(efficiency_ratio)
        state['current_adaptive_period'] = adaptive_period
        
        # ============================================
        # STEP 2: Multi-Timeframe MAs
        # ============================================
        ma_periods = {
            'fast': adaptive_period,
            'medium': 21,
            'slow': 50
        }
        mas = self.calculate_moving_averages(list(state['close_history']), ma_periods)
        
        state['current_ma_fast'] = mas.get('fast', current_price)
        state['current_ma_medium'] = mas.get('medium', current_price)
        state['current_ma_slow'] = mas.get('slow', current_price)
        
        # Check alignment
        bullish_alignment = (state['current_ma_fast'] > state['current_ma_medium'] > state['current_ma_slow'])
        bearish_alignment = (state['current_ma_fast'] < state['current_ma_medium'] < state['current_ma_slow'])
        
        # ============================================
        # STEP 3: ATR Zone
        # ============================================
        atr = self.calculate_atr(
            list(state['high_history']),
            list(state['low_history']),
            list(state['close_history']),
            period=self.atr_period
        )
        state['current_atr'] = atr
        atr_zone = atr * self.atr_multiplier
        
        price_above_zone = current_price > state['current_ma_slow'] + atr_zone
        price_below_zone = current_price < state['current_ma_slow'] - atr_zone
        
        # Update consecutive outside
        if price_above_zone or price_below_zone:
            state['consecutive_outside'] += 1
        else:
            state['consecutive_outside'] = 0
        
        # ============================================
        # STEP 4: Signal Logic
        # ============================================
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # High Efficiency - Strong Trend
        if efficiency_ratio > self.er_high_threshold:
            if bullish_alignment and price_above_zone:
                if state['consecutive_outside'] >= 2:
                    action = 'BUY'
                    confidence = 85
                    reasoning = [
                        f"Strong uptrend (ER={efficiency_ratio:.2f})",
                        f"Price above ATR zone ({state['consecutive_outside']} candles)"
                    ]
                else:
                    action = 'HOLD'
                    confidence = 60
                    reasoning = [f"Waiting for confirmation ({state['consecutive_outside']}/2)"]
            
            elif bearish_alignment and price_below_zone:
                if state['consecutive_outside'] >= 2:
                    action = 'SELL'
                    confidence = 85
                    reasoning = [
                        f"Strong downtrend (ER={efficiency_ratio:.2f})",
                        f"Price below ATR zone ({state['consecutive_outside']} candles)"
                    ]
                else:
                    action = 'HOLD'
                    confidence = 60
                    reasoning = [f"Waiting for confirmation ({state['consecutive_outside']}/2)"]
            else:
                action = 'HOLD'
                confidence = 55
                reasoning = ["Price within ATR zone - NOISE FILTERED"]
        
        # Low Efficiency - Ranging
        elif efficiency_ratio < self.er_low_threshold:
            action = 'HOLD'
            confidence = 55
            reasoning = [f"Low efficiency market (ER={efficiency_ratio:.2f}) - HOLD"]
        
        # Medium Efficiency
        else:
            if bullish_alignment and current_price > state['current_ma_slow']:
                action = 'BUY'
                confidence = 70
                reasoning = ["Moderate uptrend with MA confirmation"]
            elif bearish_alignment and current_price < state['current_ma_slow']:
                action = 'SELL'
                confidence = 70
                reasoning = ["Moderate downtrend with MA confirmation"]
            else:
                action = 'HOLD'
                confidence = 55
                reasoning = ["MAs overlapping - NOISE"]
        
        # Update state
        state['signal'] = action
        state['confidence'] = confidence
        
        # Update position
        if action == 'BUY':
            state['position'] = 1
            state['entry_price'] = current_price
        elif action == 'SELL':
            state['position'] = -1
            state['entry_price'] = current_price
        elif action == 'HOLD' and state['position'] != 0:
            if len(state['close_history']) > 20:
                z_result = self.calculate_z_score(list(state['close_history']))
                state['z_score'] = z_result['z_score']
                if abs(state['z_score']) < 0.3:
                    state['position'] = 0
        
        # Calculate Z-score for exit
        if len(state['close_history']) > 20:
            z_result = self.calculate_z_score(list(state['close_history']))
            state['z_score'] = z_result['z_score']
            
            if state['z_score_ema'] == 0:
                state['z_score_ema'] = state['z_score']
            else:
                state['z_score_ema'] = (0.3 * state['z_score']) + (0.7 * state['z_score_ema'])
            
            if abs(state['z_score_ema']) > 2.0:
                state['persistence'] += 1
            else:
                state['persistence'] = 0
        
        return {
            'pair': pair,
            'action': action,
            'confidence': confidence,
            'reason': '; '.join(reasoning) if reasoning else 'Normal',
            'z_score': state['z_score'],
            'z_score_ema': state['z_score_ema'],
            'persistence': state['persistence'],
            'position': state['position'],
            'ma_fast': state['current_ma_fast'],
            'ma_medium': state['current_ma_medium'],
            'ma_slow': state['current_ma_slow'],
            'atr': state['current_atr'],
            'efficiency_ratio': efficiency_ratio,
            'adaptive_period': adaptive_period,
            'consecutive_outside': state['consecutive_outside'],
            'entry_price': state['entry_price'],
            'current_price': current_price,
            'timestamp': datetime.now().isoformat()
        }
    
    def _hold_response(self, pair: str, reason: str) -> Dict:
        """Generate a HOLD response for a pair"""
        return {
            'pair': pair,
            'action': 'HOLD',
            'confidence': 50,
            'reason': reason,
            'z_score': 0,
            'z_score_ema': 0,
            'persistence': 0,
            'position': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    # ============================================
    # COMPATIBILITY METHODS
    # ============================================
    
    def predict(self, signal_data: Dict, market_features: Dict) -> tuple:
        """Original predict method - maintained for compatibility"""
        pair = signal_data.get('pair', 'EURUSD')
        market_data = {
            pair: signal_data.get('current_price', 0),
            'candles': market_features.get('candles', []),
            f'{pair}_candles': market_features.get('candles', [])
        }
        result = self.analyze_pair(pair, market_data)
        return result['action'], result['confidence']
    
    def vote(self, signal_data: Dict, market_features: Dict) -> Dict:
        """Vote method for the agent voting system"""
        action, confidence = self.predict(signal_data, market_features)
        pair = signal_data.get('pair', 'EURUSD')
        
        return {
            'agent': self.name,
            'pair': pair,
            'vote': action,
            'confidence': confidence,
            'reasoning': f"Microstructure Analysis: {action}",
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_signal(self, signal_data: Dict = None) -> Dict:
        """Analyze signal for the trading cycle"""
        if signal_data is None:
            signal_data = {}
        
        pair = signal_data.get('pair', 'EURUSD')
        
        # Use the analyze method
        result = self.analyze(signal_data)
        
        return {
            'agent': self.name,
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'pair': pair,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict:
        """Get status of all pairs"""
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
                'z_score': state['z_score'],
                'z_score_ema': state['z_score_ema'],
                'persistence': state['persistence'],
                'efficiency_ratio': state['current_efficiency_ratio'],
                'adaptive_period': state['current_adaptive_period'],
                'entry_price': state['entry_price']
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
            'z_score': state['z_score'],
            'z_score_ema': state['z_score_ema'],
            'persistence': state['persistence'],
            'ma_fast': state['current_ma_fast'],
            'ma_medium': state['current_ma_medium'],
            'ma_slow': state['current_ma_slow'],
            'atr': state['current_atr'],
            'efficiency_ratio': state['current_efficiency_ratio'],
            'adaptive_period': state['current_adaptive_period'],
            'consecutive_outside': state['consecutive_outside'],
            'entry_price': state['entry_price']
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics for all pairs"""
        for pair in self.pair_states:
            self.pair_states[pair]['consecutive_outside'] = 0
            self.pair_states[pair]['position'] = 0
            self.pair_states[pair]['entry_price'] = 0.0
        
        logger.info(f"🔄 {self.name} daily stats reset for all pairs")