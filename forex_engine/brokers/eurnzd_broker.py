# C:\trading_platform\forex_engine\brokers\eurnzd_broker.py

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

class EURNZDBroker(BaseBroker):
    """
    EUR/NZD Broker - Commodity-driven cross pair.
    Combines Euro (ECB) with New Zealand Dollar (RBNZ, Dairy, Risk Sentiment).
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURNZD",
            config=config,
            agent_type="Commodity Cross",
            specialization="Dairy Prices + RBNZ Policy + Risk Sentiment",
            name="EURNZD_Broker"
        )
        
        # ===== EURNZD-SPECIFIC PARAMETERS =====
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
        
        # ===== COMMODITY TRACKING =====
        self.dairy_price = 0.0
        self.dairy_change_pct = 0.0
        
        # ===== POLICY TRACKING =====
        self.ecb_policy = 'NEUTRAL'
        self.rbnz_policy = 'NEUTRAL'
        self.policy_divergence = 0.0
        
        # ===== RISK TRACKING =====
        self.risk_sentiment = 0.0
        self.vix = 15.0
        self.volatility_rating = 'NORMAL'
        self.volatility_adjustment = 1.0
        self.risk_adjustment_factor = 1.0
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        logger.info(f"✅ EURNZD Broker initialized")
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
        """Detect if EURNZD is in a range."""
        if len(closes) < self.range_lookback:
            return {'is_ranging': True, 'high': 0, 'low': 0, 'width': 0}
        
        recent = closes[-self.range_lookback:]
        high = max(recent)
        low = min(recent)
        width = high - low
        
        is_ranging = width < 0.015
        
        return {
            'is_ranging': is_ranging,
            'high': high,
            'low': low,
            'width': width
        }
    
    def _calculate_volatility_rating(self, closes: List[float]) -> str:
        """Calculate volatility rating for EURNZD."""
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
        
        self.risk_adjustment_factor = max(0.2, min(2.0, adjustment))
        return self.risk_adjustment_factor
    
    def _calculate_policy_divergence(self) -> float:
        """Calculate ECB vs RBNZ policy divergence."""
        policy_map = {'HAWKISH': 1, 'NEUTRAL': 0, 'DOVISH': -1}
        ecb_score = policy_map.get(self.ecb_policy, 0)
        rbnz_score = policy_map.get(self.rbnz_policy, 0)
        return ecb_score - rbnz_score
    
    def _generate_eurnzd_signal(self, current_price: float) -> Dict:
        """Generate EURNZD-specific signal combining all factors."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== POLICY DIVERGENCE =====
        self.policy_divergence = self._calculate_policy_divergence()
        
        if self.policy_divergence > 0.5:
            # ECB more hawkish → EUR strength → EURNZD up
            if action == 'HOLD':
                action = 'BUY'
                confidence = 70
                reasoning.append("ECB hawkish vs RBNZ dovish → EUR strength")
            elif action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append("ECB hawkish vs RBNZ dovish → EUR strength")
            elif action == 'SELL':
                confidence = max(40, confidence - 15)
                reasoning.append("ECB hawkish vs RBNZ dovish contradicts SELL")
                if confidence < 50:
                    action = 'HOLD'
        
        elif self.policy_divergence < -0.5:
            # RBNZ more hawkish → NZD strength → EURNZD down
            if action == 'HOLD':
                action = 'SELL'
                confidence = 70
                reasoning.append("RBNZ hawkish vs ECB dovish → NZD strength")
            elif action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append("RBNZ hawkish vs ECB dovish → NZD strength")
            elif action == 'BUY':
                confidence = max(40, confidence - 15)
                reasoning.append("RBNZ hawkish vs ECB dovish contradicts BUY")
                if confidence < 50:
                    action = 'HOLD'
        
        # ===== DAIRY PRICES =====
        if abs(self.dairy_change_pct) > 0.5:
            if self.dairy_change_pct > 0:
                # Dairy up → NZD strength → EURNZD down
                if action == 'SELL':
                    confidence = min(95, confidence + 10)
                    reasoning.append(f"Dairy up {self.dairy_change_pct:.1f}% → NZD strength")
                elif action == 'BUY':
                    confidence = max(40, confidence - 10)
                    reasoning.append(f"Dairy up contradicts BUY")
                    if confidence < 50:
                        action = 'HOLD'
                elif action == 'HOLD':
                    action = 'SELL'
                    confidence = 60
                    reasoning.append(f"Dairy up {self.dairy_change_pct:.1f}% → SELL EURNZD")
            else:
                # Dairy down → NZD weakness → EURNZD up
                if action == 'BUY':
                    confidence = min(95, confidence + 10)
                    reasoning.append(f"Dairy down {self.dairy_change_pct:.1f}% → NZD weakness")
                elif action == 'SELL':
                    confidence = max(40, confidence - 10)
                    reasoning.append(f"Dairy down contradicts SELL")
                    if confidence < 50:
                        action = 'HOLD'
                elif action == 'HOLD':
                    action = 'BUY'
                    confidence = 60
                    reasoning.append(f"Dairy down {self.dairy_change_pct:.1f}% → BUY EURNZD")
        
        # ===== RISK SENTIMENT =====
        if self.risk_sentiment > 0.5:
            # Risk-on → NZD strength (high beta) → EURNZD down
            if action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append("Risk-on → NZD strength")
            elif action == 'BUY':
                confidence = max(40, confidence - 10)
                reasoning.append("Risk-on contradicts BUY")
                if confidence < 50:
                    action = 'HOLD'
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 55
                reasoning.append("Risk-on → SELL EURNZD")
        
        elif self.risk_sentiment < -0.5:
            # Risk-off → NZD weakness (high beta) → EURNZD up
            if action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append("Risk-off → NZD weakness")
            elif action == 'SELL':
                confidence = max(40, confidence - 10)
                reasoning.append("Risk-off contradicts SELL")
                if confidence < 50:
                    action = 'HOLD'
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 55
                reasoning.append("Risk-off → BUY EURNZD")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
            reasoning = ["EURNZD: No clear signal - await policy or commodity catalyst"]
        
        return {
            'vote': action,
            'confidence': min(95, confidence),
            'reasoning': '; '.join(reasoning) if reasoning else 'EURNZD commodity analysis'
        }
    
    def analyze(self, signal_data: Dict) -> Dict:
        """EURNZD-specific analysis with Commodity + Policy."""
        try:
            # ===== FIX: Get price with fallbacks =====
            current_price = signal_data.get('price') or signal_data.get('current_price') or 0
            
            if current_price == 0:
                candles = signal_data.get('candles', [])
                if candles:
                    current_price = candles[-1].get('close', 0)
            
            if current_price == 0:
                return self._hold_response("No price data")
            
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURNZD-specific data =====
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
            self.dairy_price = signal_data.get('dairy_price', 0)
            self.dairy_change_pct = signal_data.get('dairy_change_pct', 0)
            self.ecb_policy = signal_data.get('ecb_policy', 'NEUTRAL')
            self.rbnz_policy = signal_data.get('rbnz_policy', 'NEUTRAL')
            self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
            self.vix = signal_data.get('VIX', 15.0)
            
            # ===== STEP 4: Detect range =====
            range_info = self._detect_range(closes)
            self.is_ranging = range_info['is_ranging']
            self.range_high = range_info['high']
            self.range_low = range_info['low']
            self.range_width = range_info['width']
            
            # ===== STEP 5: Calculate volatility rating =====
            self.volatility_rating = self._calculate_volatility_rating(closes)
            volatility_adjustments = {'LOW': 1.2, 'NORMAL': 1.0, 'HIGH': 0.7, 'EXTREME': 0.4}
            self.volatility_adjustment = volatility_adjustments.get(self.volatility_rating, 1.0)
            
            # ===== STEP 6: Calculate risk adjustment =====
            self._calculate_risk_adjustment()
            
            # ===== STEP 7: Generate EURNZD signal =====
            eurnzd_result = self._generate_eurnzd_signal(current_price)
            
            # ===== STEP 8: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and eurnzd_result['vote'] != 'HOLD' and eurnzd_result['confidence'] >= 60:
                base_result['vote'] = eurnzd_result['vote']
                base_result['confidence'] = eurnzd_result['confidence']
                base_result['reasoning'] = f"{eurnzd_result['reasoning']} (EURNZD override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and eurnzd_result['vote'] != 'HOLD':
                if eurnzd_result['confidence'] > base_conf + 10:
                    base_result['vote'] = eurnzd_result['vote']
                    base_result['confidence'] = eurnzd_result['confidence']
                    base_result['reasoning'] = f"{eurnzd_result['reasoning']} (stronger than base)"
            
            # ===== STEP 9: Add EURNZD-specific data =====
            base_result['dairy_price'] = self.dairy_price
            base_result['dairy_change_pct'] = self.dairy_change_pct
            base_result['ecb_policy'] = self.ecb_policy
            base_result['rbnz_policy'] = self.rbnz_policy
            base_result['policy_divergence'] = self.policy_divergence
            base_result['risk_sentiment'] = self.risk_sentiment
            base_result['vix'] = self.vix
            base_result['volatility_rating'] = self.volatility_rating
            base_result['risk_adjustment_factor'] = self.risk_adjustment_factor
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['is_ranging'] = self.is_ranging
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURNZD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for EURNZD."""
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
            'dairy_change_pct': self.dairy_change_pct,
            'policy_divergence': self.policy_divergence,
            'risk_sentiment': self.risk_sentiment,
            'vix': self.vix,
            'volatility_rating': self.volatility_rating,
            'risk_adjustment_factor': self.risk_adjustment_factor,
            'timestamp': datetime.now().isoformat()
        }