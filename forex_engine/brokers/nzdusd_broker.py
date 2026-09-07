# C:\trading_platform\forex_engine\brokers\nzdusd_broker.py

import logging
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

try:
    from brokers.base_broker import BaseBroker
except ImportError:
    from base_broker import BaseBroker

logger = logging.getLogger(__name__)

class NZDUSDBroker(BaseBroker):
    """
    NZD/USD Broker - Whale Tracker + Dairy Prices.
    Strategy: Whale detection + dairy prices + RBNZ policy.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="NZDUSD",
            config=config,
            agent_type="Whale Tracker",
            specialization="Whale Detection + Dairy Prices + RBNZ Policy",
            name="NZDUSD_Broker"
        )
        
        # ===== NZDUSD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 0.7
        self.max_position_size = 2
        self.gear_type = 'INVERSE'
        self.whale_alert_threshold = config.get('whale_alert_threshold', 0.7)
        
        # ===== HISTORY =====
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        self.whale_history = deque(maxlen=20)
        
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
        
        # ===== WHALE TRACKING =====
        self.whale_detected = False
        self.whale_direction = 'NEUTRAL'
        self.whale_confidence = 0.0
        
        # ===== DAIRY TRACKING =====
        self.dairy_price = 0.0
        self.dairy_change_pct = 0.0
        self.whole_milk_powder = 0.0
        self.skim_milk_powder = 0.0
        
        # ===== POLICY TRACKING =====
        self.rbnz_policy = 'NEUTRAL'
        self.rbnz_rate = 5.0
        
        # ===== INTERMARKET TRACKING =====
        self.dxy_trend = 'neutral'
        self.vix = 15.0
        self.risk_sentiment = 0.0
        self.china_demand_index = 50.0
        self.risk_score = 50.0
        self.regime = 'MIXED'
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "NZDUSD_Broker"
        self.agent_type = "Whale Tracker"
        self.specialization = "Whale Detection + Dairy Prices + RBNZ Policy"
        
        logger.info(f"✅ NZDUSD Broker initialized")
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
        """Detect if NZDUSD is in a range."""
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
    
    def _detect_whale_activity(self, closes: List[float], signal_data: Dict) -> Dict:
        """Detect whale activity in NZDUSD."""
        if len(closes) < 10:
            return {'detected': False, 'direction': 'NEUTRAL', 'confidence': 0}
        
        volume = signal_data.get('volume', 1000)
        avg_volume = signal_data.get('avg_volume', 5000)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        recent_price_change = abs(closes[-1] - closes[-2]) / closes[-2] if len(closes) >= 2 else 0
        
        if volume_ratio > 2.0 and recent_price_change > 0.002:
            if closes[-1] > closes[-2]:
                direction = 'BUY'
                confidence = min(90, 60 + (volume_ratio - 2) * 20 + recent_price_change * 100)
            else:
                direction = 'SELL'
                confidence = min(90, 60 + (volume_ratio - 2) * 20 + recent_price_change * 100)
            
            self.whale_history.append({
                'timestamp': datetime.now(),
                'direction': direction,
                'confidence': confidence,
                'volume_ratio': volume_ratio
            })
            
            return {'detected': True, 'direction': direction, 'confidence': confidence}
        
        if len(self.whale_history) >= 3:
            recent_whales = list(self.whale_history)[-3:]
            buy_count = sum(1 for w in recent_whales if w['direction'] == 'BUY')
            sell_count = len(recent_whales) - buy_count
            
            if buy_count >= 3:
                return {'detected': True, 'direction': 'BUY', 'confidence': 75}
            elif sell_count >= 3:
                return {'detected': True, 'direction': 'SELL', 'confidence': 75}
        
        return {'detected': False, 'direction': 'NEUTRAL', 'confidence': 0}
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        """NZDUSD-specific logic: Whale detection + dairy prices."""
        self.dairy_price = market_data.get('dairy_price', 0)
        self.dairy_change_pct = market_data.get('dairy_change_pct', 0)
        self.whole_milk_powder = market_data.get('whole_milk_powder', 0)
        self.skim_milk_powder = market_data.get('skim_milk_powder', 0)
        self.rbnz_policy = market_data.get('rbnz_policy', 'NEUTRAL')
        self.rbnz_rate = market_data.get('rbnz_rate', 5.0)
        self.china_demand_index = market_data.get('china_demand_index', 50.0)
        
        whale_detected = market_data.get('whale_detected', False)
        whale_confidence = market_data.get('whale_confidence', 0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'NZDUSD: '
        
        # Whale detection
        if whale_detected and whale_confidence > self.whale_alert_threshold:
            whale_direction = market_data.get('whale_direction', 'NEUTRAL')
            if whale_direction == 'BUY':
                bias = 'BUY'
                confidence_boost = 25
                reasoning += f'Whale BUY detected ({whale_confidence:.0f}%) → FOLLOW'
            elif whale_direction == 'SELL':
                bias = 'SELL'
                confidence_boost = 25
                reasoning += f'Whale SELL detected ({whale_confidence:.0f}%) → FOLLOW'
            else:
                reasoning += 'Whale detected but direction unknown'
        
        # Dairy prices
        if bias == 'NEUTRAL' and abs(self.dairy_change_pct) > 0.5:
            if self.dairy_change_pct > 0:
                bias = 'BUY'
                confidence_boost = 15
                reasoning += f'Dairy up {self.dairy_change_pct:.1f}% → NZD strength → BUY'
            else:
                bias = 'SELL'
                confidence_boost = 15
                reasoning += f'Dairy down {self.dairy_change_pct:.1f}% → NZD weakness → SELL'
        
        # RBNZ Policy
        if self.rbnz_policy == 'HAWKISH':
            if bias == 'NEUTRAL':
                bias = 'BUY'
                confidence_boost = 10
                reasoning += 'RBNZ hawkish → NZD strength'
            elif bias == 'BUY':
                confidence_boost += 10
                reasoning += ', RBNZ hawkish confirms'
        elif self.rbnz_policy == 'DOVISH':
            if bias == 'NEUTRAL':
                bias = 'SELL'
                confidence_boost = 10
                reasoning += 'RBNZ dovish → NZD weakness'
            elif bias == 'SELL':
                confidence_boost += 10
                reasoning += ', RBNZ dovish confirms'
        
        if bias == 'NEUTRAL':
            reasoning += 'No strong signals'
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'dairy_price': self.dairy_price,
            'dairy_change_pct': self.dairy_change_pct,
            'whale_detected': whale_detected,
            'whale_confidence': whale_confidence,
            'rbnz_policy': self.rbnz_policy,
            'china_demand_index': self.china_demand_index
        }
    
    def _get_pair_confidence_boost(self) -> float:
        """NZDUSD confidence based on whale detection."""
        if self.whale_detected:
            return 20.0
        if abs(self.dairy_change_pct) > 0.5:
            return 10.0
        return 5.0
    
    def analyze(self, signal_data: Dict) -> Dict:
        """NZDUSD-specific analysis using base class."""
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
            
            # ===== STEP 2: Get NZDUSD-specific data =====
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
            self.dxy_trend = signal_data.get('dxy_trend', 'neutral')
            self.rbnz_policy = signal_data.get('rbnz_policy', 'NEUTRAL')
            self.rbnz_rate = signal_data.get('rbnz_rate', 5.0)
            self.china_demand_index = signal_data.get('china_demand_index', 50.0)
            
            # ===== STEP 4: Detect range =====
            range_info = self._detect_range(closes)
            self.is_ranging = range_info['is_ranging']
            self.range_high = range_info['high']
            self.range_low = range_info['low']
            self.range_width = range_info['width']
            
            # ===== STEP 5: Detect whale activity =====
            whale_result = self._detect_whale_activity(closes, signal_data)
            self.whale_detected = whale_result['detected']
            self.whale_direction = whale_result['direction']
            self.whale_confidence = whale_result['confidence']
            
            # ===== STEP 6: Apply NZDUSD-specific logic =====
            nzdusd_result = self._apply_pair_specific_logic(signal_data)
            
            # ===== STEP 7: Generate NZDUSD signal =====
            action = base_result.get('vote', 'HOLD')
            confidence = base_result.get('confidence', 50)
            reasoning = base_result.get('reasoning', '')
            
            # Override if whale detected
            if self.whale_detected and self.whale_confidence > 70:
                if base_result.get('vote') == 'HOLD' or self.whale_confidence > confidence + 10:
                    action = self.whale_direction
                    confidence = self.whale_confidence
                    reasoning = f"🐋 Whale {self.whale_direction} detected ({self.whale_confidence:.0f}%) (NZDUSD override)"
            
            # Apply NZDUSD-specific override
            if nzdusd_result['bias'] != 'NEUTRAL':
                if action == 'HOLD':
                    action = nzdusd_result['bias']
                    confidence = min(90, 60 + nzdusd_result['confidence_boost'])
                    reasoning = nzdusd_result['reasoning'] + " (NZDUSD override)"
                elif action == nzdusd_result['bias']:
                    confidence = min(95, confidence + nzdusd_result['confidence_boost'])
                    reasoning = reasoning + " | " + nzdusd_result['reasoning']
                else:
                    confidence = max(40, confidence - 10)
                    reasoning = reasoning + " | " + nzdusd_result['reasoning'] + " (contradicts)"
                    if confidence < 50:
                        action = 'HOLD'
            
            # ===== STEP 8: Add NZDUSD-specific data =====
            base_result['vote'] = action
            base_result['confidence'] = min(95, confidence)
            base_result['reasoning'] = reasoning
            base_result['whale_detected'] = self.whale_detected
            base_result['whale_direction'] = self.whale_direction
            base_result['whale_confidence'] = self.whale_confidence
            base_result['dairy_price'] = self.dairy_price
            base_result['dairy_change_pct'] = self.dairy_change_pct
            base_result['rbnz_policy'] = self.rbnz_policy
            base_result['rbnz_rate'] = self.rbnz_rate
            base_result['china_demand_index'] = self.china_demand_index
            base_result['vix'] = self.vix
            base_result['risk_sentiment'] = self.risk_sentiment
            base_result['dxy_trend'] = self.dxy_trend
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['is_ranging'] = self.is_ranging
            
            return base_result
            
        except Exception as e:
            logger.error(f"NZDUSD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for NZDUSD."""
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
            'whale_detected': self.whale_detected,
            'whale_direction': self.whale_direction,
            'whale_confidence': self.whale_confidence,
            'dairy_change_pct': self.dairy_change_pct,
            'rbnz_policy': self.rbnz_policy,
            'vix': self.vix,
            'risk_sentiment': self.risk_sentiment,
            'dxy_trend': self.dxy_trend,
            'timestamp': datetime.now().isoformat()
        }