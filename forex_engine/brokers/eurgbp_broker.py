# C:\trading_platform\forex_engine\brokers\eurgbp_broker.py

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

class EURGBPBroker(BaseBroker):
    """
    EUR/GBP Broker - Range-bound with strong mean reversion.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURGBP",
            config=config,
            agent_type="Mean Reversion Specialist",
            specialization="Range Trading with Mean Reversion",
            name="EURGBP_Broker"
        )
        
        # ===== EURGBP-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.5)
        self.exit_threshold = config.get('exit_threshold', 0.2)
        self.sl_pips = config.get('sl_pips', 10)
        self.tp_pips = config.get('tp_pips', 20)
        self.volume_multiplier = 0.8
        self.max_position_size = 3
        self.gear_type = 'CROSS'
        
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
        
        # ===== DIVERGENCE TRACKING =====
        self.rsi_history = []
        self.macd_histogram = []
        
        # ===== POLICY TRACKING =====
        self.ecb_boe_divergence = 0.0
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "EURGBP_Broker"
        self.agent_type = "Mean Reversion Specialist"
        self.specialization = "Range Trading with Mean Reversion"
        
        logger.info(f"✅ EURGBP Broker initialized")
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
    
    def _detect_range(self, prices: List[float]) -> Dict:
        """Detect if EURGBP is in a range"""
        if len(prices) < self.range_lookback:
            return {'is_ranging': True, 'high': 0, 'low': 0, 'width': 0}
        
        recent = prices[-self.range_lookback:]
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
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI for divergence detection"""
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
    
    def _detect_rsi_divergence(self, prices: List[float], rsi_values: List[float]) -> Optional[Dict]:
        """Detect RSI divergence"""
        if len(prices) < 20 or len(rsi_values) < 20:
            return None
        
        price_peaks = []
        price_troughs = []
        rsi_peaks = []
        rsi_troughs = []
        
        for i in range(2, len(prices) - 2):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_peaks.append((i, prices[i]))
                rsi_peaks.append((i, rsi_values[i]))
            
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                price_troughs.append((i, prices[i]))
                rsi_troughs.append((i, rsi_values[i]))
        
        # Bearish divergence
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            last_peak = price_peaks[-1]
            prev_peak = price_peaks[-2]
            last_rsi = rsi_peaks[-1]
            prev_rsi = rsi_peaks[-2]
            
            if last_peak[1] > prev_peak[1] and last_rsi[1] < prev_rsi[1]:
                return {'type': 'bearish', 'strength': 0.9, 'message': 'Bearish divergence'}
        
        # Bullish divergence
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            last_trough = price_troughs[-1]
            prev_trough = price_troughs[-2]
            last_rsi = rsi_troughs[-1]
            prev_rsi = rsi_troughs[-2]
            
            if last_trough[1] < prev_trough[1] and last_rsi[1] > prev_rsi[1]:
                return {'type': 'bullish', 'strength': 0.9, 'message': 'Bullish divergence'}
        
        return None
    
    def _detect_macd_divergence(self, prices: List[float], macd_histogram: List[float]) -> Optional[Dict]:
        """Detect MACD divergence"""
        if len(prices) < 20 or len(macd_histogram) < 20:
            return None
        
        price_peaks = []
        macd_at_peaks = []
        
        for i in range(2, len(prices) - 2):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_peaks.append((i, prices[i]))
                macd_at_peaks.append((i, macd_histogram[i]))
        
        if len(price_peaks) >= 2:
            last_peak = price_peaks[-1]
            prev_peak = price_peaks[-2]
            last_macd = macd_at_peaks[-1]
            prev_macd = macd_at_peaks[-2]
            
            if last_peak[1] > prev_peak[1] and last_macd[1] < prev_macd[1]:
                return {'type': 'bearish', 'strength': 0.85, 'message': 'MACD bearish divergence'}
        
        return None
    
    def _calculate_macd_histogram(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> List[float]:
        """Calculate MACD histogram"""
        if len(prices) < slow + signal:
            return [0.0] * len(prices)
        
        def ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            multiplier = 2 / (period + 1)
            ema_value = data[0]
            for price in data[1:]:
                ema_value = (price * multiplier) + (ema_value * (1 - multiplier))
            return ema_value
        
        histogram = []
        for i in range(slow, len(prices)):
            fast_ema = ema(prices[:i+1], fast)
            slow_ema = ema(prices[:i+1], slow)
            macd_line = fast_ema - slow_ema
            signal_line = ema([macd_line], signal)
            hist = macd_line - signal_line
            histogram.append(hist)
        
        while len(histogram) < len(prices):
            histogram.insert(0, 0.0)
        
        return histogram
    
    def _generate_eurgbp_signal(self, current_price: float, rsi_divergence: Optional[Dict], 
                                 macd_divergence: Optional[Dict]) -> Dict:
        """Generate EURGBP-specific signal."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # Check if in range
        if self.is_ranging and current_price > 0 and self.range_width > 0:
            range_position = (current_price - self.range_low) / self.range_width
            
            # ===== RANGE HIGH (SELL) =====
            if range_position > 0.85:
                action = 'SELL'
                confidence = 65  # Base confidence without divergence
                reasoning = [f"EURGBP at range high ({self.range_high:.5f}) - Mean reversion SELL"]
                
                # Boost confidence if divergence present
                if rsi_divergence and rsi_divergence['type'] == 'bearish':
                    confidence = 85
                    reasoning.append(f"RSI bearish divergence confirms")
                elif macd_divergence and macd_divergence['type'] == 'bearish':
                    confidence = 80
                    reasoning.append(f"MACD bearish divergence confirms")
            
            # ===== RANGE LOW (BUY) =====
            elif range_position < 0.15:
                action = 'BUY'
                confidence = 65  # Base confidence without divergence
                reasoning = [f"EURGBP at range low ({self.range_low:.5f}) - Mean reversion BUY"]
                
                # Boost confidence if divergence present
                if rsi_divergence and rsi_divergence['type'] == 'bullish':
                    confidence = 85
                    reasoning.append(f"RSI bullish divergence confirms")
                elif macd_divergence and macd_divergence['type'] == 'bullish':
                    confidence = 80
                    reasoning.append(f"MACD bullish divergence confirms")
            
            # ===== MIDDLE OF RANGE =====
            else:
                action = 'HOLD'
                confidence = 50
                reasoning = [f"EURGBP in middle of range ({range_position:.2f})"]
        
        else:
            # ===== NOT RANGING - Use divergence signals =====
            if rsi_divergence and rsi_divergence['type'] == 'bearish':
                action = 'SELL'
                confidence = 75
                reasoning = [f"RSI bearish divergence: {rsi_divergence['message']}"]
            elif rsi_divergence and rsi_divergence['type'] == 'bullish':
                action = 'BUY'
                confidence = 75
                reasoning = [f"RSI bullish divergence: {rsi_divergence['message']}"]
            elif macd_divergence and macd_divergence['type'] == 'bearish':
                action = 'SELL'
                confidence = 70
                reasoning = [f"MACD bearish divergence: {macd_divergence['message']}"]
            elif macd_divergence and macd_divergence['type'] == 'bullish':
                action = 'BUY'
                confidence = 70
                reasoning = [f"MACD bullish divergence: {macd_divergence['message']}"]
            else:
                action = 'HOLD'
                confidence = 50
                reasoning = ["No divergence detected"]
        
        # ===== ECB/BOE DIVERGENCE ADJUSTMENT =====
        if abs(self.ecb_boe_divergence) > 0.3:
            if self.ecb_boe_divergence > 0:  # ECB more hawkish
                if action == 'BUY':
                    confidence = min(95, confidence + 10)
                    reasoning.append("ECB hawkish vs BoE → EUR strength")
                elif action == 'SELL':
                    confidence = max(40, confidence - 10)
                    if confidence < 50:
                        action = 'HOLD'
                    reasoning.append("ECB hawkish vs BoE - reducing SELL")
                elif action == 'HOLD':
                    action = 'BUY'
                    confidence = 60
                    reasoning.append("ECB hawkish vs BoE → BUY EURGBP")
            else:  # BoE more hawkish
                if action == 'SELL':
                    confidence = min(95, confidence + 10)
                    reasoning.append("BoE hawkish vs ECB → GBP strength")
                elif action == 'BUY':
                    confidence = max(40, confidence - 10)
                    if confidence < 50:
                        action = 'HOLD'
                    reasoning.append("BoE hawkish vs ECB - reducing BUY")
                elif action == 'HOLD':
                    action = 'SELL'
                    confidence = 60
                    reasoning.append("BoE hawkish vs ECB → SELL EURGBP")
        
        return {
            'vote': action,
            'confidence': min(95, confidence),
            'reasoning': '; '.join(reasoning) if reasoning else 'EURGBP divergence analysis'
        }
    
    def analyze(self, signal_data: Dict) -> Dict:
        """EURGBP-specific analysis with RSI/MACD divergence."""
        try:
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURGBP-specific data =====
            current_price = signal_data.get('price', signal_data.get('current_price', 0))
            candles = signal_data.get('candles', [])
            
            if not candles:
                return base_result
            
            closes = [c['close'] for c in candles]
            
            if len(closes) < 30:
                return base_result
            
            # Update history
            self.close_history.extend(closes)
            
            # ===== STEP 3: Detect range =====
            range_info = self._detect_range(closes)
            self.is_ranging = range_info['is_ranging']
            self.range_high = range_info['high']
            self.range_low = range_info['low']
            self.range_width = range_info['width']
            
            # ===== STEP 4: Calculate RSI =====
            rsi_values = []
            for i in range(14, len(closes)):
                rsi = self._calculate_rsi(closes[:i+1], 14)
                rsi_values.append(rsi)
            self.rsi_history.extend(rsi_values)
            
            # ===== STEP 5: Calculate MACD histogram =====
            if len(closes) >= 26:
                macd_hist = self._calculate_macd_histogram(closes)
                self.macd_histogram.extend(macd_hist)
            
            # ===== STEP 6: Detect divergences =====
            rsi_divergence = None
            macd_divergence = None
            
            if len(self.rsi_history) >= 20:
                rsi_divergence = self._detect_rsi_divergence(
                    closes[-30:], 
                    self.rsi_history[-30:] if len(self.rsi_history) >= 30 else self.rsi_history
                )
            
            if len(self.macd_histogram) >= 20:
                macd_divergence = self._detect_macd_divergence(
                    closes[-30:],
                    self.macd_histogram[-30:] if len(self.macd_histogram) >= 30 else self.macd_histogram
                )
            
            # ===== STEP 7: Get external data =====
            self.ecb_boe_divergence = signal_data.get('ecb_boe_divergence', 0)
            
            # ===== STEP 8: Generate EURGBP signal =====
            eurgbp_result = self._generate_eurgbp_signal(
                current_price, rsi_divergence, macd_divergence
            )
            
            # ===== STEP 9: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and eurgbp_result['vote'] != 'HOLD' and eurgbp_result['confidence'] >= 60:
                base_result['vote'] = eurgbp_result['vote']
                base_result['confidence'] = eurgbp_result['confidence']
                base_result['reasoning'] = f"{eurgbp_result['reasoning']} (EURGBP override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and eurgbp_result['vote'] != 'HOLD':
                if eurgbp_result['confidence'] > base_conf + 10:
                    base_result['vote'] = eurgbp_result['vote']
                    base_result['confidence'] = eurgbp_result['confidence']
                    base_result['reasoning'] = f"{eurgbp_result['reasoning']} (stronger than base)"
            
            # ===== STEP 10: Add EURGBP-specific data =====
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['range_width'] = self.range_width
            base_result['is_ranging'] = self.is_ranging
            base_result['rsi_divergence'] = rsi_divergence
            base_result['macd_divergence'] = macd_divergence
            base_result['ecb_boe_divergence'] = self.ecb_boe_divergence
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURGBP Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for EURGBP."""
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
            'range_high': self.range_high,
            'range_low': self.range_low,
            'range_width': self.range_width,
            'is_ranging': self.is_ranging,
            'ecb_boe_divergence': self.ecb_boe_divergence,
            'timestamp': datetime.now().isoformat()
        }