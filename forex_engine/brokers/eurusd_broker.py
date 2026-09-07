# C:\trading_platform\forex_engine\brokers\eurusd_broker.py

import logging
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional

try:
    from brokers.base_broker import BaseBroker
except ImportError:
    from base_broker import BaseBroker

logger = logging.getLogger(__name__)

class EURUSDBroker(BaseBroker):
    """
    EUR/USD Broker - Trend Follower with ECB/Fed policy.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURUSD",
            config=config,
            agent_type="Trend Follower",
            specialization="Adaptive Moving Average with Zero Error Filter",
            name="EURUSD_Broker"
        )
        
        # ===== EURUSD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 10)
        self.tp_pips = config.get('tp_pips', 20)
        self.volume_multiplier = 1.2
        self.max_position_size = 5
        self.gear_type = 'INVERSE'
        self.fastest_period = 5
        self.slowest_period = 200
        
        # ===== HISTORY =====
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        
        # ===== PATTERN DETECTION =====
        self.pattern_info = None
        self.squeeze_detected = False
        self.volume_spike = False
        self.support_level = 0.0
        self.resistance_level = 0.0
        
        # ===== THRESHOLDS =====
        self.er_high_threshold = config.get('er_high_threshold', 0.7)
        self.er_low_threshold = config.get('er_low_threshold', 0.3)
        self.atr_multiplier = config.get('atr_multiplier', 1.5)
        
        # ===== STATE =====
        self.consecutive_outside = 0
        self.samples = 0
        self.z_score = 0.0
        
        # ===== POLICY TRACKING =====
        self.ecb_policy = 'NEUTRAL'
        self.fed_policy = 'NEUTRAL'
        self.interest_rate_diff = 0.0
        
        # ===== SIGNAL STATE =====
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "EURUSD_Broker"
        self.agent_type = "Trend Follower"
        self.specialization = "Adaptive Moving Average with Zero Error Filter"
        
        logger.info(f"✅ EURUSD Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")

    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
            'pair': self.pair,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': reason,
            'z_score': getattr(self, 'z_score', 0),
            'position': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        """
        EURUSD-specific logic:
        - ECB vs Fed policy divergence
        - Interest rate differential
        """
        self.ecb_policy = market_data.get('ecb_policy', 'NEUTRAL')
        self.fed_policy = market_data.get('fed_policy', 'NEUTRAL')
        self.interest_rate_diff = market_data.get('eurusd_rate_diff', 0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'EURUSD: '
        
        # Policy divergence
        if self.ecb_policy == 'HAWKISH' and self.fed_policy == 'DOVISH':
            confidence_boost = 15
            bias = 'BUY'
            reasoning += 'ECB hawkish vs Fed dovish → EUR strength'
        elif self.ecb_policy == 'DOVISH' and self.fed_policy == 'HAWKISH':
            confidence_boost = 15
            bias = 'SELL'
            reasoning += 'ECB dovish vs Fed hawkish → USD strength'
        elif self.ecb_policy == 'HAWKISH' and self.fed_policy == 'HAWKISH':
            confidence_boost = 5
            reasoning += 'Both hawkish → focus on differential'
        else:
            reasoning += 'Neutral policy'
        
        # Interest rate differential
        if abs(self.interest_rate_diff) > 0.5:
            if self.interest_rate_diff > 0:
                reasoning += f', rate diff {self.interest_rate_diff:.2f}% favors EUR'
                if bias == 'NEUTRAL':
                    bias = 'BUY'
                    confidence_boost = 10
            else:
                reasoning += f', rate diff {self.interest_rate_diff:.2f}% favors USD'
                if bias == 'NEUTRAL':
                    bias = 'SELL'
                    confidence_boost = 10
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'ecb_policy': self.ecb_policy,
            'fed_policy': self.fed_policy,
            'rate_diff': self.interest_rate_diff
        }
    
    def _get_pair_confidence_boost(self) -> float:
        """EURUSD has higher confidence due to liquidity."""
        return 5.0
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Adaptive Moving Average with Zero Error Filter:
        1. Multi-Timeframe Confirmation (adaptive, 21, 50)
        2. Volatility Zone (ATR filter)
        3. Kaufman Efficiency Ratio (adaptive speed)
        4. EURUSD-specific ECB/Fed policy
        """
        try:
            # ===== FIX: Get price with fallbacks =====
            current_price = signal_data.get('price') or signal_data.get('current_price') or 0
            
            # If no price, try to get from candles
            if current_price == 0:
                candles = signal_data.get('candles', [])
                if candles:
                    current_price = candles[-1].get('close', 0)
            
            if current_price == 0:
                return self._hold_response("No price data")
            
            # Get candlestick data
            candles = signal_data.get('candles', [])
            if not candles:
                return self._hold_response("No candle data")
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 20:
                return self._hold_response(f"Insufficient data ({len(closes)}/20)")
            
            # Update history
            self.close_history.extend(closes)
            self.high_history.extend(highs)
            self.low_history.extend(lows)
            self.current_price = current_price
            self.price_history.append(current_price)
            
            # ============================================
            # STEP 1: Kaufman Efficiency Ratio
            # ============================================
            efficiency_ratio = self.calculate_kaufman_efficiency_ratio(
                self.close_history[-50:] if len(self.close_history) > 50 else self.close_history, 
                period=20
            )
            adaptive_period = self.calculate_adaptive_period(efficiency_ratio)
            
            # ============================================
            # STEP 2: Multi-Timeframe Moving Averages
            # ============================================
            ma_periods = {
                'fast': adaptive_period,
                'medium': 21,
                'slow': 50
            }
            mas = self.calculate_moving_averages(self.close_history, ma_periods)
            
            ma_fast = mas.get('fast', current_price)
            ma_medium = mas.get('medium', current_price)
            ma_slow = mas.get('slow', current_price)
            
            # Determine trend direction
            bullish_alignment = ma_fast > ma_medium > ma_slow
            bearish_alignment = ma_fast < ma_medium < ma_slow
            
            # ============================================
            # STEP 3: Volatility Zone (ATR Filter)
            # ============================================
            atr = self.calculate_atr(self.high_history, self.low_history, self.close_history, period=14)
            atr_zone = atr * self.atr_multiplier
            
            # Check if price is outside ATR zone
            price_above_zone = current_price > ma_slow + atr_zone
            price_below_zone = current_price < ma_slow - atr_zone
            
            if price_above_zone or price_below_zone:
                self.consecutive_outside += 1
            else:
                self.consecutive_outside = 0
            
            # ============================================
            # STEP 4: EURUSD-SPECIFIC EXTERNAL DATA
            # ============================================
            self.ecb_policy = signal_data.get('ecb_policy', 'NEUTRAL')
            self.fed_policy = signal_data.get('fed_policy', 'NEUTRAL')
            self.interest_rate_diff = signal_data.get('eurusd_rate_diff', 0)
            
            # ============================================
            # STEP 5: Zero Error Filter - Signal Logic
            # ============================================
            action = 'HOLD'
            confidence = 50
            reasons = []
            
            # High Efficiency - Strong Trend
            if efficiency_ratio > self.er_high_threshold:
                if bullish_alignment and price_above_zone:
                    if self.consecutive_outside >= 2:
                        action = 'BUY'
                        confidence = 85
                        reasons = [
                            f"Strong uptrend (ER={efficiency_ratio:.2f})",
                            f"MA: {ma_fast:.4f} > {ma_medium:.4f} > {ma_slow:.4f}"
                        ]
                    else:
                        action = 'HOLD'
                        confidence = 60
                        reasons = [f"Waiting for confirmation ({self.consecutive_outside}/2)"]
                
                elif bearish_alignment and price_below_zone:
                    if self.consecutive_outside >= 2:
                        action = 'SELL'
                        confidence = 85
                        reasons = [
                            f"Strong downtrend (ER={efficiency_ratio:.2f})",
                            f"MA: {ma_fast:.4f} < {ma_medium:.4f} < {ma_slow:.4f}"
                        ]
                    else:
                        action = 'HOLD'
                        confidence = 60
                        reasons = [f"Waiting for confirmation ({self.consecutive_outside}/2)"]
                else:
                    self.consecutive_outside = 0
                    action = 'HOLD'
                    confidence = 55
                    reasons = ["Price within ATR zone - NOISE FILTERED"]
            
            # Low Efficiency - Ranging
            elif efficiency_ratio < self.er_low_threshold:
                action = 'HOLD'
                confidence = 55
                reasons = [f"Low efficiency market (ER={efficiency_ratio:.2f})"]
            
            # Medium Efficiency
            else:
                if bullish_alignment and current_price > ma_slow:
                    action = 'BUY'
                    confidence = 70
                    reasons = ["Moderate uptrend with MA confirmation"]
                elif bearish_alignment and current_price < ma_slow:
                    action = 'SELL'
                    confidence = 70
                    reasons = ["Moderate downtrend with MA confirmation"]
                else:
                    action = 'HOLD'
                    confidence = 55
                    reasons = ["MAs overlapping - NOISE"]
            
            # ============================================
            # STEP 6: EURUSD-SPECIFIC POLICY ADJUSTMENTS
            # ============================================
            
            # Policy divergence
            if self.ecb_policy == 'HAWKISH' and self.fed_policy == 'DOVISH':
                if action == 'BUY':
                    confidence = min(95, confidence + 10)
                    reasons.append("ECB hawkish vs Fed dovish")
                elif action == 'SELL':
                    confidence = max(40, confidence - 10)
                    if confidence < 50:
                        action = 'HOLD'
                    reasons.append("ECB hawkish vs Fed dovish - reducing SELL")
            
            elif self.ecb_policy == 'DOVISH' and self.fed_policy == 'HAWKISH':
                if action == 'SELL':
                    confidence = min(95, confidence + 10)
                    reasons.append("ECB dovish vs Fed hawkish")
                elif action == 'BUY':
                    confidence = max(40, confidence - 10)
                    if confidence < 50:
                        action = 'HOLD'
                    reasons.append("ECB dovish vs Fed hawkish - reducing BUY")
            
            # Interest rate differential
            if abs(self.interest_rate_diff) > 0.5:
                rate_bias = 'BUY' if self.interest_rate_diff > 0 else 'SELL'
                if action == rate_bias and confidence < 70:
                    confidence = min(75, confidence + 10)
                    reasons.append(f"Rate diff {self.interest_rate_diff:.2f}% supports {rate_bias}")
            
            # ============================================
            # STEP 7: UPDATE STATE
            # ============================================
            self.signal = action
            self.confidence = confidence
            
            # Calculate Z-score
            if len(self.close_history) > 20:
                z_result = self.calculate_z_score(self.close_history[-20:])
                self.z_score = z_result['z_score']
                self.samples = z_result['samples']
            
            return {
                'pair': self.pair,
                'vote': action,
                'confidence': round(min(95, confidence), 1),
                'reasoning': '; '.join(reasons) if reasons else 'EURUSD trend analysis',
                'z_score': self.z_score,
                'z_score_ema': self.z_score,
                'persistence': 1 if abs(self.z_score) > self.entry_threshold else 0,
                'samples': self.samples,
                'ma_fast': ma_fast,
                'ma_medium': ma_medium,
                'ma_slow': ma_slow,
                'atr': atr,
                'efficiency_ratio': efficiency_ratio,
                'adaptive_period': adaptive_period,
                'consecutive_outside': self.consecutive_outside,
                'ecb_policy': self.ecb_policy,
                'fed_policy': self.fed_policy,
                'interest_rate_diff': self.interest_rate_diff,
                'timestamp': datetime.now().isoformat()
            }
             
        except Exception as e:
            logger.error(f"EURUSD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def calculate_kaufman_efficiency_ratio(self, prices, period=10) -> float:
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
        fastest = self.fastest_period
        slowest = self.slowest_period
        adaptive_period = slowest - (efficiency_ratio * (slowest - fastest))
        period = int(round(adaptive_period))
        return max(fastest, min(slowest, period))
    
    def calculate_moving_averages(self, prices: List[float], periods: Dict) -> Dict:
        mas = {}
        for name, period in periods.items():
            if len(prices) >= period:
                mas[name] = sum(prices[-period:]) / period
            else:
                mas[name] = prices[-1] if prices else 0
        return mas
    
    def calculate_atr(self, highs: List[float], lows: List[float], 
                      closes: List[float], period: int = 14) -> float:
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
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            final_price = price
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            if final_price > cloud_top:
                outcomes['above_cloud'] += 1
            elif final_price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        probabilities = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        if probabilities['above_cloud'] > 60:
            vote = 'BUY'
            conf = probabilities['above_cloud']
        elif probabilities['below_cloud'] > 60:
            vote = 'SELL'
            conf = probabilities['below_cloud']
        else:
            vote = 'HOLD'
            conf = probabilities['inside_cloud']
        return {'vote': vote, 'confidence': conf, 'probabilities': probabilities}
    
    def predict(self, signal_data: Dict, market_features: Dict = None) -> tuple:
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_status(self) -> Dict:
        return {
            'name': 'EURUSD_Broker',
            'pair': self.pair,
            'agent_type': 'Trend Follower',
            'signal': self.signal,
            'confidence': self.confidence,
            'z_score': self.z_score,
            'consecutive_outside': self.consecutive_outside,
            'ecb_policy': self.ecb_policy,
            'fed_policy': self.fed_policy,
            'interest_rate_diff': self.interest_rate_diff,
            'timestamp': datetime.now().isoformat()
        }