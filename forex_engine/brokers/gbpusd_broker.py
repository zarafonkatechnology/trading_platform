# C:\trading_platform\forex_engine\brokers\gbpusd_broker.py

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

class GBPUSDBroker(BaseBroker):
    """
    GBP/USD Broker - Pattern Specialist with BoE Policy.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="GBPUSD",
            config=config,
            agent_type="Pattern Specialist",
            specialization="Head & Shoulders + Double Top/Bottom + BoE Policy",
            name="GBPUSD_Broker"
        )
        
        # ===== GBPUSD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 1.0
        self.max_position_size = 4
        self.gear_type = 'INVERSE'
        self.volatility_filter = config.get('volatility_filter', 0.015)
        
        # ===== HISTORY =====
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        
        # ===== PATTERN DETECTION =====
        self.pattern_info = None
        self.pattern_detected = None
        self.pattern_confidence = 0.0
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
        
        # ===== POLICY TRACKING =====
        self.boe_policy = 'NEUTRAL'
        self.brexit_sentiment = 0.0
        self.uk_economic = 0.0
        
        # ===== RISK TRACKING =====
        self.vix = 15.0
        self.risk_sentiment = 0.0
        self.geopolitical_risk = 0.0
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "GBPUSD_Broker"
        self.agent_type = "Pattern Specialist"
        self.specialization = "Head & Shoulders + Double Top/Bottom + BoE Policy"
        
        logger.info(f"✅ GBPUSD Broker initialized")
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
    
    def _detect_range(self, closes: List[float]) -> Dict:
        """Detect if GBPUSD is in a range."""
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
    
    def _find_peaks_troughs(self, data: List[float], window: int = 3) -> tuple:
        """Find local peaks and troughs."""
        peaks = []
        troughs = []
        
        for i in range(window, len(data) - window):
            # Check for peak
            is_peak = True
            for j in range(1, window + 1):
                if data[i] <= data[i - j] or data[i] <= data[i + j]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((i, data[i]))
            
            # Check for trough
            is_trough = True
            for j in range(1, window + 1):
                if data[i] >= data[i - j] or data[i] >= data[i + j]:
                    is_trough = False
                    break
            if is_trough:
                troughs.append((i, data[i]))
        
        return peaks, troughs
    
    def _detect_pattern(self, closes: List[float]) -> Optional[Dict]:
        """Detect patterns using price history."""
        if len(closes) < 30:
            return None
        
        prices = list(closes)[-30:]
        recent_high = max(prices[-10:])
        recent_low = min(prices[-10:])
        
        # Check for double top (two similar highs)
        highs = [p for p in prices[-20:] if p > recent_high * 0.998]
        if len(highs) >= 2:
            first_high_idx = prices.index(highs[0])
            second_high_idx = prices.index(highs[1])
            if second_high_idx > first_high_idx:
                valley = min(prices[first_high_idx:second_high_idx])
                if valley < recent_high * 0.995:
                    return {
                        'pattern': 'DOUBLE_TOP',
                        'direction': 'SELL',
                        'confidence': 75,
                        'message': 'Double Top detected - bearish reversal'
                    }
        
        # Check for double bottom (two similar lows)
        lows = [p for p in prices[-20:] if p < recent_low * 1.002]
        if len(lows) >= 2:
            first_low_idx = prices.index(lows[0])
            second_low_idx = prices.index(lows[1])
            if second_low_idx > first_low_idx:
                peak = max(prices[first_low_idx:second_low_idx])
                if peak > recent_low * 1.005:
                    return {
                        'pattern': 'DOUBLE_BOTTOM',
                        'direction': 'BUY',
                        'confidence': 75,
                        'message': 'Double Bottom detected - bullish reversal'
                    }
        
        # Check for head and shoulders (simplified)
        if len(prices) >= 50:
            peaks, _ = self._find_peaks_troughs(prices, window=3)
            if len(peaks) >= 3:
                left = peaks[-3] if len(peaks) >= 3 else None
                head = peaks[-2] if len(peaks) >= 2 else None
                right = peaks[-1] if len(peaks) >= 1 else None
                if left and head and right:
                    if head[1] > left[1] and head[1] > right[1]:
                        return {
                            'pattern': 'HEAD_SHOULDERS_TOP',
                            'direction': 'SELL',
                            'confidence': 85,
                            'message': 'Head & Shoulders Top detected - strong bearish reversal'
                        }
        
        return None
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        """GBPUSD-specific logic: Brexit sentiment + pattern detection."""
        self.brexit_sentiment = market_data.get('brexit_sentiment', 0.0)
        self.boe_policy = market_data.get('boe_policy', 'NEUTRAL')
        self.uk_economic = market_data.get('uk_economic', 0.0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'GBPUSD: '
        
        # Brexit sentiment
        if self.brexit_sentiment < -0.3:
            confidence_boost += 10
            bias = 'SELL'
            reasoning += 'Brexit negative → GBP weakness'
        elif self.brexit_sentiment > 0.3:
            confidence_boost += 10
            bias = 'BUY'
            reasoning += 'Brexit positive → GBP strength'
        else:
            reasoning += 'Neutral Brexit sentiment'
        
        # BoE Policy
        if self.boe_policy == 'HAWKISH':
            reasoning += ', BoE hawkish → GBP strength'
            if bias == 'NEUTRAL':
                bias = 'BUY'
                confidence_boost += 10
        elif self.boe_policy == 'DOVISH':
            reasoning += ', BoE dovish → GBP weakness'
            if bias == 'NEUTRAL':
                bias = 'SELL'
                confidence_boost += 10
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'brexit_sentiment': self.brexit_sentiment,
            'boe_policy': self.boe_policy,
            'uk_economic': self.uk_economic
        }
    
    def _get_pair_confidence_boost(self) -> float:
        """GBPUSD confidence based on pattern strength."""
        if self.pattern_detected:
            if 'HEAD' in self.pattern_detected:
                return 15.0
            return 10.0
        return 0.0
    
    def analyze(self, signal_data: Dict) -> Dict:
        """GBPUSD-specific analysis using base class."""
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
            
            # ===== STEP 2: Get GBPUSD-specific data =====
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
            self.geopolitical_risk = signal_data.get('geopolitical_risk', 0.0)
            self.brexit_sentiment = signal_data.get('brexit_sentiment', 0.0)
            self.boe_policy = signal_data.get('boe_policy', 'NEUTRAL')
            self.uk_economic = signal_data.get('uk_economic', 0.0)
            
            # ===== STEP 4: Detect range =====
            range_info = self._detect_range(closes)
            self.is_ranging = range_info['is_ranging']
            self.range_high = range_info['high']
            self.range_low = range_info['low']
            self.range_width = range_info['width']
            
            # ===== STEP 5: Detect pattern =====
            pattern_result = self._detect_pattern(closes)
            if pattern_result:
                self.pattern_detected = pattern_result['pattern']
                self.pattern_confidence = pattern_result['confidence']
                self.pattern_info = pattern_result
            else:
                self.pattern_detected = None
                self.pattern_confidence = 0.0
                self.pattern_info = None
            
            # ===== STEP 6: Apply GBPUSD-specific logic =====
            gbpusd_result = self._apply_pair_specific_logic(signal_data)
            
            # ===== STEP 7: Generate GBPUSD signal =====
            action = base_result.get('vote', 'HOLD')
            confidence = base_result.get('confidence', 50)
            reasoning = base_result.get('reasoning', '')
            
            # Override if pattern detected
            if pattern_result and pattern_result['confidence'] > 70:
                if base_result.get('vote') == 'HOLD' or pattern_result['confidence'] > confidence + 10:
                    action = pattern_result['direction']
                    confidence = pattern_result['confidence']
                    reasoning = f"{pattern_result['message']} (GBPUSD pattern override)"
            
            # Apply GBPUSD-specific override
            if gbpusd_result['bias'] != 'NEUTRAL':
                if action == 'HOLD':
                    action = gbpusd_result['bias']
                    confidence = min(90, 60 + gbpusd_result['confidence_boost'])
                    reasoning = gbpusd_result['reasoning'] + " (GBPUSD override)"
                elif action == gbpusd_result['bias']:
                    confidence = min(95, confidence + gbpusd_result['confidence_boost'])
                    reasoning = reasoning + " | " + gbpusd_result['reasoning']
                else:
                    confidence = max(40, confidence - 10)
                    reasoning = reasoning + " | " + gbpusd_result['reasoning'] + " (contradicts)"
                    if confidence < 50:
                        action = 'HOLD'
            
            # ===== STEP 8: Add GBPUSD-specific data =====
            base_result['vote'] = action
            base_result['confidence'] = min(95, confidence)
            base_result['reasoning'] = reasoning
            base_result['pattern_detected'] = self.pattern_detected
            base_result['pattern_confidence'] = self.pattern_confidence
            base_result['pattern_info'] = self.pattern_info
            base_result['brexit_sentiment'] = self.brexit_sentiment
            base_result['boe_policy'] = self.boe_policy
            base_result['uk_economic'] = self.uk_economic
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['is_ranging'] = self.is_ranging
            base_result['vix'] = self.vix
            base_result['risk_sentiment'] = self.risk_sentiment
            base_result['geopolitical_risk'] = self.geopolitical_risk
            
            return base_result
            
        except Exception as e:
            logger.error(f"GBPUSD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for GBPUSD."""
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
            'pattern_detected': self.pattern_detected,
            'pattern_confidence': self.pattern_confidence,
            'brexit_sentiment': self.brexit_sentiment,
            'boe_policy': self.boe_policy,
            'vix': self.vix,
            'risk_sentiment': self.risk_sentiment,
            'timestamp': datetime.now().isoformat()
        }