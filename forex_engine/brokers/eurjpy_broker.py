# C:\trading_platform\forex_engine\brokers\eurjpy_broker.py

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

class EURJPYBroker(BaseBroker):
    """
    EUR/JPY Broker - Fibonacci + Risk Sentiment + Seasonality.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURJPY",
            config=config,
            agent_type="Fibonacci + Risk Sentiment",
            specialization="Fibonacci Levels + VIX + Seasonality",
            name="EURJPY_Broker"
        )
        
        # ===== EURJPY-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 15)
        self.tp_pips = config.get('tp_pips', 30)
        self.volume_multiplier = 0.8
        self.max_position_size = 3
        self.gear_type = 'CROSS'
        self.min_position_size = 0.01
        
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
        
        # ===== RANGE TRACKING =====
        self.range_high = 0.0
        self.range_low = 0.0
        self.range_width = 0.0
        self.is_ranging = True
        self.range_lookback = config.get('range_lookback', 50)
        
        # ===== FIBONACCI TRACKING =====
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.current_fib_level = 0.0
        
        # ===== RISK TRACKING =====
        self.vix = 15.0
        self.risk_sentiment = 0.0
        self.yield_spread = 0.0
        self.volatility_rating = 'NORMAL'
        self.volatility_adjustment = 1.0
        self.risk_adjustment_factor = 1.0
        self.seasonality_multiplier = 1.0
        self.seasonality_score = 50.0
        
        # ===== SEASONALITY =====
        self.monthly_bias = {
            1: {"name": "January", "bias": "neutral", "strength": 50, "saying": "January effect"},
            2: {"name": "February", "bias": "neutral", "strength": 50, "saying": "Post-January calm"},
            3: {"name": "March", "bias": "neutral", "strength": 50, "saying": "Japanese fiscal year end"},
            4: {"name": "April", "bias": "neutral", "strength": 50, "saying": "Start of new fiscal year"},
            5: {"name": "May", "bias": "neutral", "strength": 50, "saying": "Golden Week holidays"},
            6: {"name": "June", "bias": "neutral", "strength": 50, "saying": "Mid-year positioning"},
            7: {"name": "July", "bias": "neutral", "strength": 50, "saying": "Summer start"},
            8: {"name": "August", "bias": "neutral", "strength": 50, "saying": "Summer lull"},
            9: {"name": "September", "bias": "neutral", "strength": 50, "saying": "Autumn start"},
            10: {"name": "October", "bias": "neutral", "strength": 50, "saying": "Q4 start"},
            11: {"name": "November", "bias": "neutral", "strength": 50, "saying": "Year-end positioning"},
            12: {"name": "December", "bias": "neutral", "strength": 50, "saying": "Santa Rally"},
        }
        
        self.day_patterns = {
            0: {"bias": "neutral", "note": "Monday"},
            1: {"bias": "neutral", "note": "Tuesday"},
            2: {"bias": "neutral", "note": "Wednesday"},
            3: {"bias": "neutral", "note": "Thursday"},
            4: {"bias": "neutral", "note": "Friday"},
        }
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        logger.info(f"✅ EURJPY Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
            'pair': self.pair,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': reason,
            'z_score': self.z_score,
            'position': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_range(self, closes: List[float]) -> Dict:
        """Detect if EURJPY is in a range."""
        if len(closes) < self.range_lookback:
            return {'is_ranging': True, 'high': 0, 'low': 0, 'width': 0}
        
        recent = closes[-self.range_lookback:]
        high = max(recent)
        low = min(recent)
        width = high - low
        
        is_ranging = width < 0.01
        
        return {
            'is_ranging': is_ranging,
            'high': high,
            'low': low,
            'width': width
        }
    
    def _calculate_fibonacci(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict:
        """Calculate Fibonacci retracement and extension levels."""
        if len(closes) < 50:
            return {
                'current_level': 0.0,
                'retracement': 0.0,
                'direction': 'NEUTRAL',
                'levels': {},
                'message': 'Insufficient data for Fibonacci'
            }
        
        swing_high = max(highs[-50:])
        swing_low = min(lows[-50:])
        current_price = closes[-1]
        
        range_high_low = swing_high - swing_low
        
        if range_high_low == 0:
            return {
                'current_level': 0.0,
                'retracement': 0.0,
                'direction': 'NEUTRAL',
                'levels': {},
                'message': 'No range for Fibonacci'
            }
        
        fib_levels = {
            0.0: swing_high,
            0.236: swing_high - range_high_low * 0.236,
            0.382: swing_high - range_high_low * 0.382,
            0.5: swing_high - range_high_low * 0.5,
            0.618: swing_high - range_high_low * 0.618,
            0.786: swing_high - range_high_low * 0.786,
            1.0: swing_low
        }
        
        retracement = (swing_high - current_price) / range_high_low if range_high_low > 0 else 0
        retracement = max(0, min(1, retracement))
        
        nearest_level = min(fib_levels.keys(), key=lambda x: abs(retracement - x))
        
        if len(closes) >= 10:
            trend = closes[-1] - closes[-10]
            direction = 'UP' if trend > 0 else 'DOWN' if trend < 0 else 'NEUTRAL'
        else:
            direction = 'NEUTRAL'
        
        return {
            'current_level': retracement * 100,
            'nearest_level': nearest_level,
            'retracement': retracement,
            'direction': direction,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'levels': fib_levels,
            'message': f"Price at {retracement*100:.1f}% Fibonacci retracement"
        }
    
    def _analyze_seasonality(self) -> Dict:
        """Analyze seasonal patterns for EURJPY."""
        current_date = datetime.now()
        month = current_date.month
        day = current_date.day
        weekday = current_date.weekday()
        
        monthly = self.monthly_bias.get(month, {"name": "Unknown", "bias": "neutral", "strength": 50, "saying": ""})
        day_bias = self.day_patterns.get(weekday, {"bias": "neutral", "note": ""})
        
        score = monthly["strength"]
        
        if day_bias["bias"] == "bullish":
            score += 5
        elif day_bias["bias"] == "bearish":
            score -= 5
        
        # Japanese fiscal year end (March)
        if month == 3 and day >= 20:
            score -= 15
        
        # Golden Week (late April - early May)
        if (month == 4 and day >= 29) or (month == 5 and day <= 5):
            score -= 10
        
        # Summer lull (August)
        if month == 8:
            score -= 10
        
        # Year-end rally (December)
        if month == 12:
            score += 10
        
        if score > 65:
            multiplier = 1.2
        elif score > 55:
            multiplier = 1.0
        elif score > 45:
            multiplier = 0.8
        else:
            multiplier = 0.5
        
        self.seasonality_score = score
        self.seasonality_multiplier = multiplier
        
        return {
            'month': month,
            'month_name': monthly["name"],
            'bias': monthly["bias"],
            'strength': monthly["strength"],
            'score': max(0, min(100, score)),
            'multiplier': multiplier,
            'saying': monthly["saying"],
            'day_bias': day_bias["bias"],
            'day_note': day_bias["note"],
        }
    
    def _calculate_volatility_rating(self, closes: List[float]) -> str:
        """Calculate volatility rating for EURJPY."""
        if len(closes) < 20:
            return 'NORMAL'
        
        returns = [abs((closes[i] - closes[i-1]) / closes[i-1]) for i in range(1, len(closes))]
        recent_vol = np.mean(returns[-20:]) * 100 * 100
        
        if recent_vol > 0.8:
            return 'EXTREME'
        elif recent_vol > 0.5:
            return 'HIGH'
        elif recent_vol > 0.25:
            return 'NORMAL'
        else:
            return 'LOW'
    
    def _calculate_risk_adjustment(self) -> float:
        """Calculate overall risk adjustment factor."""
        adjustment = 1.0
        
        if self.vix > 25:
            adjustment *= 0.6
        elif self.vix > 20:
            adjustment *= 0.8
        elif self.vix < 12:
            adjustment *= 1.1
        
        if self.risk_sentiment < -0.5:
            adjustment *= 0.7
        elif self.risk_sentiment > 0.5:
            adjustment *= 1.1
        
        adjustment *= self.volatility_adjustment
        adjustment *= self.seasonality_multiplier
        
        self.risk_adjustment_factor = max(0.2, min(2.0, adjustment))
        return self.risk_adjustment_factor
    
    def _generate_eurjpy_signal(self, current_price: float, fib_result: Dict, 
                                seasonality_result: Dict) -> Dict:
        """Generate EURJPY-specific signal combining all factors."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== FIBONACCI SIGNAL =====
        retracement = fib_result['retracement']
        fib_direction = fib_result['direction']
        
        if retracement > 0.786:
            if fib_direction == 'UP':
                action = 'BUY'
                confidence = 75
                reasoning.append(f"Fibonacci deep retracement ({retracement*100:.1f}%) - BUY")
            elif fib_direction == 'DOWN':
                action = 'SELL'
                confidence = 75
                reasoning.append(f"Fibonacci deep retracement ({retracement*100:.1f}%) - SELL")
        
        elif retracement < 0.236:
            if fib_direction == 'UP':
                action = 'BUY'
                confidence = 70
                reasoning.append(f"Fibonacci shallow retracement ({retracement*100:.1f}%) - BUY continuation")
            elif fib_direction == 'DOWN':
                action = 'SELL'
                confidence = 70
                reasoning.append(f"Fibonacci shallow retracement ({retracement*100:.1f}%) - SELL continuation")
        
        # ===== SEASONALITY SIGNAL =====
        season_score = seasonality_result['score']
        
        if season_score > 65:
            if action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append(f"Strong seasonality: {seasonality_result['saying']}")
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 65
                reasoning.append(f"Seasonality: {seasonality_result['saying']}")
        
        elif season_score < 35:
            if action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append(f"Bearish seasonality: {seasonality_result['saying']}")
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 65
                reasoning.append(f"Seasonality: {seasonality_result['saying']}")
        
        # ===== RISK SENTIMENT =====
        if self.risk_sentiment > 0.5 and action == 'BUY':
            confidence = min(95, confidence + 10)
            reasoning.append("Risk-on sentiment supports EURJPY")
        elif self.risk_sentiment < -0.5 and action == 'SELL':
            confidence = min(95, confidence + 10)
            reasoning.append("Risk-off sentiment supports JPY")
        elif self.risk_sentiment < -0.5 and action == 'BUY':
            confidence = max(40, confidence - 15)
            reasoning.append("Risk-off contradicts BUY")
            if confidence < 50:
                action = 'HOLD'
                reasoning.append("Risk-off overrides BUY signal")
        elif self.risk_sentiment > 0.5 and action == 'SELL':
            confidence = max(40, confidence - 15)
            reasoning.append("Risk-on contradicts SELL")
            if confidence < 50:
                action = 'HOLD'
                reasoning.append("Risk-on overrides SELL signal")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
            reasoning = ["EURJPY: No clear signal from Fibonacci, seasonality, or risk"]
        
        return {
            'vote': action,
            'confidence': min(95, confidence),
            'reasoning': '; '.join(reasoning) if reasoning else 'EURJPY seasonality analysis'
        }
    
    def analyze(self, signal_data: Dict) -> Dict:
        """EURJPY-specific analysis with Fibonacci + Risk Sentiment."""
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
            
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURJPY-specific data =====
            candles = signal_data.get('candles', [])
            
            if not candles:
                return base_result
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 20:
                return base_result
            
            # Update histories
            self.close_history.extend(closes)
            self.high_history.extend(highs)
            self.low_history.extend(lows)
            
            # ===== STEP 3: Get external data =====
            self.vix = signal_data.get('VIX', 15.0)
            self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
            self.yield_spread = signal_data.get('yield_spread', 0.0)
            
            # ===== STEP 4: Detect range =====
            range_info = self._detect_range(closes)
            self.is_ranging = range_info['is_ranging']
            self.range_high = range_info['high']
            self.range_low = range_info['low']
            self.range_width = range_info['width']
            
            # ===== STEP 5: Calculate Fibonacci =====
            fib_result = self._calculate_fibonacci(closes, highs, lows)
            self.current_fib_level = fib_result['current_level']
            
            # ===== STEP 6: Calculate volatility rating =====
            self.volatility_rating = self._calculate_volatility_rating(closes)
            volatility_adjustments = {'LOW': 1.2, 'NORMAL': 1.0, 'HIGH': 0.7, 'EXTREME': 0.4}
            self.volatility_adjustment = volatility_adjustments.get(self.volatility_rating, 1.0)
            
            # ===== STEP 7: Analyze seasonality =====
            seasonality_result = self._analyze_seasonality()
            
            # ===== STEP 8: Calculate risk adjustment =====
            self._calculate_risk_adjustment()
            
            # ===== STEP 9: Generate EURJPY signal =====
            eurjpy_result = self._generate_eurjpy_signal(current_price, fib_result, seasonality_result)
            
            # ===== STEP 10: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and eurjpy_result['vote'] != 'HOLD' and eurjpy_result['confidence'] >= 60:
                base_result['vote'] = eurjpy_result['vote']
                base_result['confidence'] = eurjpy_result['confidence']
                base_result['reasoning'] = f"{eurjpy_result['reasoning']} (EURJPY override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and eurjpy_result['vote'] != 'HOLD':
                if eurjpy_result['confidence'] > base_conf + 10:
                    base_result['vote'] = eurjpy_result['vote']
                    base_result['confidence'] = eurjpy_result['confidence']
                    base_result['reasoning'] = f"{eurjpy_result['reasoning']} (stronger than base)"
            
            # ===== STEP 11: Add EURJPY-specific data =====
            base_result['fib_level'] = self.current_fib_level
            base_result['fib_result'] = fib_result
            base_result['seasonality'] = seasonality_result
            base_result['volatility_rating'] = self.volatility_rating
            base_result['risk_adjustment_factor'] = self.risk_adjustment_factor
            base_result['vix'] = self.vix
            base_result['risk_sentiment'] = self.risk_sentiment
            base_result['yield_spread'] = self.yield_spread
            base_result['seasonality_score'] = self.seasonality_score
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['is_ranging'] = self.is_ranging
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURJPY Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for EURJPY."""
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
            return {'vote': 'BUY', 'confidence': probs['above_cloud'], 'probabilities': probs}
        elif probs['below_cloud'] > 60:
            return {'vote': 'SELL', 'confidence': probs['below_cloud'], 'probabilities': probs}
        return {'vote': 'HOLD', 'confidence': probs['inside_cloud'], 'probabilities': probs}
    
    def predict(self, signal_data: Dict, market_features: Dict = None) -> tuple:
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_status(self) -> Dict:
        return {
            'name': self.name,
            'pair': self.pair,
            'signal': self.signal,
            'confidence': self.confidence,
            'z_score': self.z_score,
            'fib_level': self.current_fib_level,
            'volatility_rating': self.volatility_rating,
            'risk_adjustment_factor': self.risk_adjustment_factor,
            'seasonality_score': self.seasonality_score,
            'vix': self.vix,
            'risk_sentiment': self.risk_sentiment,
            'yield_spread': self.yield_spread,
            'timestamp': datetime.now().isoformat()
        }