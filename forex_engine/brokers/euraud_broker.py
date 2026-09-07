# C:\trading_platform\forex_engine\brokers\euraud_broker.py

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

class EURAUDBroker(BaseBroker):
    """
    EURAUD Broker - Commodity-driven cross pair.
    Combines Euro (ECB) with Australian Dollar (RBA, Gold, Iron Ore).
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURAUD",
            config=config,
            agent_type="Commodity Cross",
            specialization="Gold & Iron Ore Correlation with Policy Divergence",
            name="EURAUD_Broker"
        )
        
        # ===== EURAUD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 15)
        self.tp_pips = config.get('tp_pips', 30)
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
        
        # ===== GOLD TRACKING =====
        self.gold_price = 0.0
        self.gold_change_pct = 0.0
        self.gold_correlation = 0.6  # AUD moves with Gold
        
        # ===== IRON ORE TRACKING =====
        self.iron_ore_price = 0.0
        self.iron_ore_change_pct = 0.0
        
        # ===== POLICY TRACKING =====
        self.ecb_policy = config.get('ecb_policy', 'NEUTRAL')
        self.rba_policy = config.get('rba_policy', 'NEUTRAL')
        self.policy_divergence = 0.0  # Positive = ECB more hawkish
        
        # ===== RISK SENTIMENT =====
        self.risk_sentiment = 0.0
        self.aud_risk_sensitivity = 0.8
        self.vix = 15.0
        
        # ===== CHINA DATA =====
        self.china_pmi = 50.0
        self.china_demand = 0.0
        
        # ===== RANGE TRACKING =====
        self.range_high = 0.0
        self.range_low = 0.0
        self.range_position = 0.5
        self.is_ranging = False
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        self.position = 0
        
        # ===== OTHER =====
        self.name = "EURAUD_Broker"
        self.agent_type = "Commodity Cross"
        self.specialization = "Gold & Iron Ore Correlation with Policy Divergence"
        
        logger.info(f"✅ {self.name} initialized for EURAUD")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def analyze(self, signal_data: Dict) -> Dict:
        """EURAUD analysis using base class with commodity logic."""
        try:
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURAUD-specific data =====
            current_price = signal_data.get('price', signal_data.get('current_price', 0))
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
            self.gold_price = signal_data.get('GOLD', 0)
            self.gold_change_pct = signal_data.get('gold_change_pct', 0)
            self.iron_ore_price = signal_data.get('iron_ore_price', 0)
            self.iron_ore_change_pct = signal_data.get('iron_ore_change_pct', 0)
            self.ecb_policy = signal_data.get('ecb_policy', 'NEUTRAL')
            self.rba_policy = signal_data.get('rba_policy', 'NEUTRAL')
            self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
            self.vix = signal_data.get('VIX', 15.0)
            self.china_pmi = signal_data.get('china_pmi', 50.0)
            
            # ===== STEP 4: Calculate policy divergence =====
            self.policy_divergence = self._calculate_policy_divergence()
            
            # ===== STEP 5: Detect range =====
            self._detect_range(closes)
            
            # ===== STEP 6: Detect candlestick patterns =====
            candle_pattern = self._detect_candlestick_pattern(closes, highs, lows)
            if candle_pattern:
                self.pattern_info = candle_pattern
            
            # ===== STEP 7: Generate EURAUD signal =====
            euraud_result = self._generate_euraud_signal(current_price)
            
            # ===== STEP 8: Apply gold correlation adjustment =====
            euraud_result = self._adjust_for_gold_correlation(euraud_result)
            
            # ===== STEP 9: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and euraud_result['vote'] != 'HOLD' and euraud_result['confidence'] >= 60:
                base_result['vote'] = euraud_result['vote']
                base_result['confidence'] = euraud_result['confidence']
                base_result['reasoning'] = f"{euraud_result['reasoning']} (EURAUD override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and euraud_result['vote'] != 'HOLD':
                if euraud_result['confidence'] > base_conf + 10:
                    base_result['vote'] = euraud_result['vote']
                    base_result['confidence'] = euraud_result['confidence']
                    base_result['reasoning'] = f"{euraud_result['reasoning']} (stronger than base)"
            
            # ===== STEP 10: Add EURAUD-specific data =====
            base_result['gold_price'] = self.gold_price
            base_result['gold_change_pct'] = self.gold_change_pct
            base_result['iron_ore_price'] = self.iron_ore_price
            base_result['iron_ore_change_pct'] = self.iron_ore_change_pct
            base_result['ecb_policy'] = self.ecb_policy
            base_result['rba_policy'] = self.rba_policy
            base_result['policy_divergence'] = self.policy_divergence
            base_result['risk_sentiment'] = self.risk_sentiment
            base_result['vix'] = self.vix
            base_result['china_pmi'] = self.china_pmi
            base_result['pattern_info'] = self.pattern_info
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['range_position'] = self.range_position
            base_result['is_ranging'] = self.is_ranging
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURAUD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def _calculate_policy_divergence(self) -> float:
        """Calculate ECB vs RBA policy divergence."""
        policy_map = {'HAWKISH': 1, 'NEUTRAL': 0, 'DOVISH': -1}
        ecb_score = policy_map.get(self.ecb_policy, 0)
        rba_score = policy_map.get(self.rba_policy, 0)
        return ecb_score - rba_score  # Positive = ECB more hawkish
    
    def _detect_range(self, closes: List[float]):
        """Detect if EURAUD is in a range."""
        if len(closes) < 50:
            self.is_ranging = True
            return
        
        recent = closes[-50:]
        self.range_high = max(recent)
        self.range_low = min(recent)
        range_width = self.range_high - self.range_low
        
        # EURAUD can range or trend
        self.is_ranging = range_width < 0.015  # 150 pips
        self.range_position = (closes[-1] - self.range_low) / range_width if range_width > 0 else 0.5
    
    def _detect_candlestick_pattern(self, closes: List[float], highs: List[float], 
                                   lows: List[float]) -> Optional[Dict]:
        """Detect candlestick patterns for EURAUD."""
        if len(closes) < 3:
            return None
        
        c1, c2, c3 = closes[-3], closes[-2], closes[-1]
        h1, h2, h3 = highs[-3], highs[-2], highs[-1]
        l1, l2, l3 = lows[-3], lows[-2], lows[-1]
        
        body3 = abs(c3 - c2)
        upper_shadow3 = h3 - max(c3, c2)
        lower_shadow3 = min(c3, c2) - l3
        
        # Doji
        if body3 < 0.0002:
            return {'pattern': 'Doji', 'direction': 'NEUTRAL', 'confidence': 60, 'message': 'Doji detected - indecision'}
        
        # Bullish Engulfing
        if c3 > c2 and c2 < c1 and c3 > c1 and c2 > c1:
            return {'pattern': 'Bullish Engulfing', 'direction': 'BUY', 'confidence': 80, 'message': 'Bullish engulfing'}
        
        # Bearish Engulfing
        if c3 < c2 and c2 > c1 and c3 < c1 and c2 < c1:
            return {'pattern': 'Bearish Engulfing', 'direction': 'SELL', 'confidence': 80, 'message': 'Bearish engulfing'}
        
        return None
    
    def _adjust_for_gold_correlation(self, result: Dict) -> Dict:
        """Adjust signal based on gold price correlation."""
        if abs(self.gold_change_pct) > 0.3:
            if self.gold_change_pct > 0:
                # Gold up → AUD strength → EURAUD down
                if result['vote'] == 'SELL':
                    result['confidence'] = min(95, result['confidence'] + 15)
                    result['reasoning'] += " | Gold up confirms SELL"
                elif result['vote'] == 'BUY':
                    result['confidence'] = max(40, result['confidence'] - 15)
                    result['reasoning'] += " | Gold up contradicts BUY"
                    if result['confidence'] < 50:
                        result['vote'] = 'HOLD'
            else:
                # Gold down → AUD weakness → EURAUD up
                if result['vote'] == 'BUY':
                    result['confidence'] = min(95, result['confidence'] + 15)
                    result['reasoning'] += " | Gold down confirms BUY"
                elif result['vote'] == 'SELL':
                    result['confidence'] = max(40, result['confidence'] - 15)
                    result['reasoning'] += " | Gold down contradicts SELL"
                    if result['confidence'] < 50:
                        result['vote'] = 'HOLD'
        
        return result
    
    def _generate_euraud_signal(self, current_price: float) -> Dict:
        """Generate EURAUD-specific signal."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== 1. GOLD CORRELATION =====
        if abs(self.gold_change_pct) > 0.3:
            if self.gold_change_pct > 0:
                # Gold up → AUD strength → EURAUD down
                if action == 'HOLD':
                    action = 'SELL'
                    confidence = 65
                    reasoning.append(f"Gold up {self.gold_change_pct:.1f}% → AUD strength → EURAUD down")
                elif action == 'BUY':
                    confidence = max(40, confidence - 15)
                    reasoning.append(f"Gold up contradicts BUY")
                else:
                    confidence = min(95, confidence + 10)
                    reasoning.append(f"Gold up confirms SELL")
            else:
                # Gold down → AUD weakness → EURAUD up
                if action == 'HOLD':
                    action = 'BUY'
                    confidence = 65
                    reasoning.append(f"Gold down {self.gold_change_pct:.1f}% → AUD weakness → EURAUD up")
                elif action == 'SELL':
                    confidence = max(40, confidence - 15)
                    reasoning.append(f"Gold down contradicts SELL")
                else:
                    confidence = min(95, confidence + 10)
                    reasoning.append(f"Gold down confirms BUY")
        
        # ===== 2. POLICY DIVERGENCE =====
        if self.policy_divergence > 0.5:
            # ECB more hawkish → EUR strength → EURAUD up
            if action == 'BUY':
                confidence = min(95, confidence + 15)
                reasoning.append("ECB hawkish vs RBA dovish → EUR strength")
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 70
                reasoning.append("ECB hawkish vs RBA dovish → BUY")
            elif action == 'SELL':
                confidence = max(40, confidence - 15)
                reasoning.append("ECB hawkish contradicts SELL")
                if confidence < 50:
                    action = 'HOLD'
        elif self.policy_divergence < -0.5:
            # RBA more hawkish → AUD strength → EURAUD down
            if action == 'SELL':
                confidence = min(95, confidence + 15)
                reasoning.append("RBA hawkish vs ECB dovish → AUD strength")
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 70
                reasoning.append("RBA hawkish vs ECB dovish → SELL")
            elif action == 'BUY':
                confidence = max(40, confidence - 15)
                reasoning.append("RBA hawkish contradicts BUY")
                if confidence < 50:
                    action = 'HOLD'
        
        # ===== 3. RISK SENTIMENT =====
        if self.risk_sentiment > 0.5:
            if action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append("Risk-on confirms AUD strength")
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 60
                reasoning.append("Risk-on → SELL EURAUD")
            elif action == 'BUY':
                confidence = max(40, confidence - 10)
                reasoning.append("Risk-on contradicts BUY")
                if confidence < 50:
                    action = 'HOLD'
        elif self.risk_sentiment < -0.5:
            if action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append("Risk-off confirms AUD weakness")
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 60
                reasoning.append("Risk-off → BUY EURAUD")
            elif action == 'SELL':
                confidence = max(40, confidence - 10)
                reasoning.append("Risk-off contradicts SELL")
                if confidence < 50:
                    action = 'HOLD'
        
        # ===== 4. CHINA PMI =====
        if self.china_pmi > 52:
            if action == 'SELL':
                confidence = min(95, confidence + 5)
                reasoning.append(f"China PMI strong ({self.china_pmi:.1f}) → AUD strength")
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 55
                reasoning.append(f"China PMI strong ({self.china_pmi:.1f}) → AUD strength")
        elif self.china_pmi < 48:
            if action == 'BUY':
                confidence = min(95, confidence + 5)
                reasoning.append(f"China PMI weak ({self.china_pmi:.1f}) → AUD weakness")
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 55
                reasoning.append(f"China PMI weak ({self.china_pmi:.1f}) → AUD weakness")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
            reasoning = ["EURAUD: No clear signal - await commodity or policy catalyst"]
        
        return {
            'vote': action,
            'confidence': min(95, confidence),
            'reasoning': '; '.join(reasoning) if reasoning else 'EURAUD commodity analysis'
        }
    
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
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005,
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for EURAUD."""
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
            'gold_change_pct': self.gold_change_pct,
            'iron_ore_change_pct': self.iron_ore_change_pct,
            'policy_divergence': self.policy_divergence,
            'risk_sentiment': self.risk_sentiment,
            'timestamp': datetime.now().isoformat()
        }