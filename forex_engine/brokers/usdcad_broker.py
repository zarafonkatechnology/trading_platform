# C:\trading_platform\forex_engine\brokers\usdcad_broker.py

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

class USDCADBroker(BaseBroker):
    """
    USD/CAD Broker - Oil correlation + Ichimoku Cloud.
    Strategy: Oil correlation + Ichimoku Cloud + BOC Policy.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="USDCAD",
            config=config,
            agent_type="Oil + Ichimoku Specialist",
            specialization="Oil Correlation + Ichimoku Cloud + BOC Policy",
            name="USDCAD_Broker"
        )
        
        # ===== USDCAD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 1.0
        self.max_position_size = 4
        self.gear_type = 'DIRECT'
        
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
        
        # ===== ICHIMOKU PARAMETERS =====
        self.tenkan_period = config.get('tenkan_period', 9)
        self.kijun_period = config.get('kijun_period', 26)
        self.senkou_b_period = config.get('senkou_b_period', 52)
        self.ichimoku_data = {}
        
        # ===== OIL TRACKING =====
        self.oil_price = 0.0
        self.oil_change_pct = 0.0
        
        # ===== POLICY TRACKING =====
        self.boc_policy = 'NEUTRAL'
        self.boc_rate = 4.75
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "USDCAD_Broker"
        self.agent_type = "Oil + Ichimoku Specialist"
        self.specialization = "Oil Correlation + Ichimoku Cloud + BOC Policy"
        
        logger.info(f"✅ USDCAD Broker initialized")
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
        """USDCAD-specific logic: Oil correlation + BOC Policy."""
        self.oil_price = market_data.get('CrudeOIL', 0)
        self.oil_change_pct = market_data.get('oil_change_pct', 0)
        self.boc_policy = market_data.get('boc_policy', 'NEUTRAL')
        self.boc_rate = market_data.get('boc_rate', 4.75)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'USDCAD: '
        
        # Oil correlation (USDCAD moves inverse to oil)
        if abs(self.oil_change_pct) > 0.5:
            if self.oil_change_pct > 0:
                confidence_boost = 15
                bias = 'SELL'
                reasoning += f'Oil up {self.oil_change_pct:.1f}% → CAD strength → SELL USDCAD'
            else:
                confidence_boost = 15
                bias = 'BUY'
                reasoning += f'Oil down {self.oil_change_pct:.1f}% → CAD weakness → BUY USDCAD'
        else:
            reasoning += f'Neutral oil ({self.oil_price:.2f})'
        
        # BOC Policy
        if self.boc_policy == 'HAWKISH':
            reasoning += ', BOC hawkish → CAD strength'
            if bias == 'NEUTRAL':
                bias = 'SELL'
                confidence_boost = 10
            elif bias == 'SELL':
                confidence_boost += 5
        elif self.boc_policy == 'DOVISH':
            reasoning += ', BOC dovish → CAD weakness'
            if bias == 'NEUTRAL':
                bias = 'BUY'
                confidence_boost = 10
            elif bias == 'BUY':
                confidence_boost += 5
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'oil_price': self.oil_price,
            'oil_change_pct': self.oil_change_pct,
            'boc_policy': self.boc_policy,
            'boc_rate': self.boc_rate
        }
    
    def _get_pair_confidence_boost(self) -> float:
        """USDCAD confidence based on oil movement."""
        if abs(self.oil_change_pct) > 1.0:
            return 15.0
        return 5.0
    
    def _calculate_ichimoku(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict:
        """
        Calculate Ichimoku Cloud components from price data.
        """
        current_price = closes[-1] if closes else 0
        
        # Tenkan-sen (Conversion Line)
        if len(highs) >= self.tenkan_period:
            tenkan_high = max(highs[-self.tenkan_period:])
            tenkan_low = min(lows[-self.tenkan_period:])
            tenkan = (tenkan_high + tenkan_low) / 2
        else:
            tenkan = current_price
        
        # Kijun-sen (Base Line)
        if len(highs) >= self.kijun_period:
            kijun_high = max(highs[-self.kijun_period:])
            kijun_low = min(lows[-self.kijun_period:])
            kijun = (kijun_high + kijun_low) / 2
        else:
            kijun = current_price
        
        # Senkou Span A
        senkou_a = (tenkan + kijun) / 2
        
        # Senkou Span B
        if len(highs) >= self.senkou_b_period:
            senkou_b_high = max(highs[-self.senkou_b_period:])
            senkou_b_low = min(lows[-self.senkou_b_period:])
            senkou_b = (senkou_b_high + senkou_b_low) / 2
        else:
            senkou_b = current_price
        
        # Cloud top and bottom
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        
        # Current price vs cloud
        if current_price > cloud_top:
            price_vs_cloud = "above"
        elif current_price < cloud_bottom:
            price_vs_cloud = "below"
        else:
            price_vs_cloud = "inside"
        
        # Cloud color
        cloud_color = "green" if senkou_a > senkou_b else "red"
        
        # Cloud direction
        if len(closes) > 30:
            old_cloud_top = max(
                (max(highs[-self.senkou_b_period-10:-self.senkou_b_period]) + 
                 min(lows[-self.senkou_b_period-10:-self.senkou_b_period])) / 2,
                (max(highs[-self.kijun_period-10:-self.kijun_period]) + 
                 min(lows[-self.kijun_period-10:-self.kijun_period])) / 2
            )
            if cloud_top > old_cloud_top * 1.001:
                cloud_direction = "rising"
            elif cloud_top < old_cloud_top * 0.999:
                cloud_direction = "falling"
            else:
                cloud_direction = "flat"
        else:
            cloud_direction = "flat"
        
        # TK Cross
        if tenkan > kijun:
            tk_cross = "bullish"
        elif tenkan < kijun:
            tk_cross = "bearish"
        else:
            tk_cross = "neutral"
        
        return {
            'tenkan': round(tenkan, 5),
            'kijun': round(kijun, 5),
            'senkou_a': round(senkou_a, 5),
            'senkou_b': round(senkou_b, 5),
            'cloud_top': round(cloud_top, 5),
            'cloud_bottom': round(cloud_bottom, 5),
            'price_vs_cloud': price_vs_cloud,
            'cloud_color': cloud_color,
            'cloud_direction': cloud_direction,
            'tk_cross': tk_cross,
            'current_price': current_price
        }
    
    def _generate_usdcad_signal(self, ichimoku: Dict, volume_ratio: float, 
                                volume_surge: bool, current_price: float) -> Dict:
        """Generate USDCAD signal using Ichimoku + Oil."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== ICHIMOKU RULES =====
        # Rule A: Breakout Confirmation
        if ichimoku['price_vs_cloud'] == "above":
            if volume_ratio > 1.1 or volume_surge:
                action = 'BUY'
                confidence = min(95, 70 + (volume_ratio - 1) * 50)
                reasoning.append(f"✅ Valid breakout above cloud ({ichimoku['cloud_top']:.5f}) with volume")
            else:
                action = 'HOLD'
                confidence = 30
                reasoning.append(f"⚠️ False breakout: low volume ({volume_ratio:.1f}x)")
        
        # Rule B: Breakdown Confirmation
        elif ichimoku['price_vs_cloud'] == "below":
            if volume_ratio > 1.1 or volume_surge:
                action = 'SELL'
                confidence = min(95, 70 + (volume_ratio - 1) * 50)
                reasoning.append(f"✅ Valid breakdown below cloud ({ichimoku['cloud_bottom']:.5f}) with volume")
            else:
                action = 'HOLD'
                confidence = 30
                reasoning.append(f"⚠️ False breakdown: low volume ({volume_ratio:.1f}x)")
        
        # Rule C: TK Cross
        if ichimoku['tk_cross'] == "bullish" and action == 'HOLD':
            if volume_ratio > 1.0:
                action = 'BUY'
                confidence = 85
                reasoning.append(f"✅ Golden cross confirmed with volume ({volume_ratio:.1f}x)")
            else:
                action = 'HOLD'
                confidence = 25
                reasoning.append(f"❌ Golden cross vetoed by low volume ({volume_ratio:.1f}x)")
        
        elif ichimoku['tk_cross'] == "bearish" and action == 'HOLD':
            if volume_ratio > 1.0:
                action = 'SELL'
                confidence = 85
                reasoning.append(f"✅ Death cross confirmed with volume ({volume_ratio:.1f}x)")
            else:
                action = 'HOLD'
                confidence = 25
                reasoning.append(f"⚠️ Death cross: low volume ({volume_ratio:.1f}x)")
        
        # Inside cloud
        if ichimoku['price_vs_cloud'] == "inside" and action == 'HOLD':
            action = 'HOLD'
            confidence = 50
            reasoning.append(f"⏸️ Price inside cloud - wait for breakout")
        
        # ===== OIL CORRELATION =====
        if abs(self.oil_change_pct) > 0.5:
            oil_signal = 'SELL' if self.oil_change_pct > 0 else 'BUY'
            
            if action == oil_signal:
                confidence = min(95, confidence + 10)
                reasoning.append(f"Oil {self.oil_change_pct:.1f}% confirms signal")
            elif action != 'HOLD':
                confidence = max(40, confidence - 10)
                reasoning.append(f"Oil {self.oil_change_pct:.1f}% contradicts signal")
                if confidence < 50:
                    action = 'HOLD'
                    reasoning.append("Oil overrides Ichimoku signal")
        
        # ===== BOC POLICY =====
        if self.boc_policy == 'HAWKISH':
            if action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append("BOC hawkish confirms SELL")
            elif action == 'BUY':
                confidence = max(40, confidence - 10)
                reasoning.append("BOC hawkish contradicts BUY")
                if confidence < 50:
                    action = 'HOLD'
        elif self.boc_policy == 'DOVISH':
            if action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append("BOC dovish confirms BUY")
            elif action == 'SELL':
                confidence = max(40, confidence - 10)
                reasoning.append("BOC dovish contradicts SELL")
                if confidence < 50:
                    action = 'HOLD'
        
        return {
            'vote': action,
            'confidence': min(95, max(30, confidence)),
            'reasoning': '; '.join(reasoning) if reasoning else 'USDCAD Ichimoku analysis'
        }
    
    def analyze(self, signal_data: Dict) -> Dict:
        """USDCAD-specific analysis using base class."""
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
            
            # ===== STEP 2: Get USDCAD-specific data =====
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
            self.oil_price = signal_data.get('CrudeOIL', 0)
            self.oil_change_pct = signal_data.get('oil_change_pct', 0)
            self.boc_policy = signal_data.get('boc_policy', 'NEUTRAL')
            self.boc_rate = signal_data.get('boc_rate', 4.75)
            
            volume_ratio = signal_data.get('volume_ratio', 1.0)
            volume_surge = signal_data.get('volume_surge', False)
            
            # ===== STEP 4: Calculate Ichimoku =====
            ichimoku = self._calculate_ichimoku(closes, highs, lows)
            self.ichimoku_data = ichimoku
            
            # ===== STEP 5: Apply USDCAD-specific logic =====
            usdcad_result = self._apply_pair_specific_logic(signal_data)
            
            # ===== STEP 6: Generate USDCAD signal =====
            usdcad_signal = self._generate_usdcad_signal(ichimoku, volume_ratio, volume_surge, current_price)
            
            # ===== STEP 7: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and usdcad_signal['vote'] != 'HOLD' and usdcad_signal['confidence'] >= 60:
                base_result['vote'] = usdcad_signal['vote']
                base_result['confidence'] = usdcad_signal['confidence']
                base_result['reasoning'] = f"{usdcad_signal['reasoning']} (USDCAD override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and usdcad_signal['vote'] != 'HOLD':
                if usdcad_signal['confidence'] > base_conf + 10:
                    base_result['vote'] = usdcad_signal['vote']
                    base_result['confidence'] = usdcad_signal['confidence']
                    base_result['reasoning'] = f"{usdcad_signal['reasoning']} (stronger than base)"
            
            # Apply USDCAD-specific override
            if usdcad_result['bias'] != 'NEUTRAL':
                if base_result.get('vote') == 'HOLD':
                    base_result['vote'] = usdcad_result['bias']
                    base_result['confidence'] = min(90, 60 + usdcad_result['confidence_boost'])
                    base_result['reasoning'] = usdcad_result['reasoning'] + " (USDCAD override)"
                elif base_result.get('vote') == usdcad_result['bias']:
                    base_result['confidence'] = min(95, base_result['confidence'] + usdcad_result['confidence_boost'])
            
            # ===== STEP 8: Add USDCAD-specific data =====
            base_result['oil_price'] = self.oil_price
            base_result['oil_change_pct'] = self.oil_change_pct
            base_result['boc_policy'] = self.boc_policy
            base_result['boc_rate'] = self.boc_rate
            base_result['ichimoku_data'] = ichimoku
            base_result['price_vs_cloud'] = ichimoku['price_vs_cloud']
            base_result['cloud_direction'] = ichimoku['cloud_direction']
            base_result['tk_cross'] = ichimoku['tk_cross']
            
            return base_result
            
        except Exception as e:
            logger.error(f"USDCAD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for USDCAD."""
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
            'oil_price': self.oil_price,
            'oil_change_pct': self.oil_change_pct,
            'boc_policy': self.boc_policy,
            'price_vs_cloud': self.ichimoku_data.get('price_vs_cloud', 'unknown'),
            'cloud_direction': self.ichimoku_data.get('cloud_direction', 'unknown'),
            'tk_cross': self.ichimoku_data.get('tk_cross', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }