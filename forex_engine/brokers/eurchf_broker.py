# C:\trading_platform\forex_engine\brokers\eurchf_broker.py

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

class EURCHFBroker(BaseBroker):
    """
    EUR/CHF Broker - Economic Calendar + SNB.
    Strategy: SNB intervention + economic data + safe-haven flows.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURCHF",
            config=config,
            agent_type="Economic Calendar + SNB",
            specialization="SNB Intervention + Safe-Haven Flow Analysis",
            name="EURCHF_Broker"
        )
        
        # ===== EURCHF-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.5)
        self.exit_threshold = config.get('exit_threshold', 0.2)
        self.sl_pips = config.get('sl_pips', 10)
        self.tp_pips = config.get('tp_pips', 20)
        self.volume_multiplier = 0.7
        self.max_position_size = 2
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
        self.range_position = 0.5
        self.is_ranging = False
        
        # ===== SNB TRACKING =====
        self.snb_intervention = False
        self.snb_intervention_level = 0.0
        self.snb_intervention_history = []  # ← FIX: Initialize
        self.snb_policy = 'NEUTRAL'
        
        # ===== ECB TRACKING =====
        self.ecb_policy = 'NEUTRAL'
        self.policy_divergence = 0.0
        
        # ===== SAFE HAVEN TRACKING =====
        self.safe_haven_flow = 0.0
        self.vix = 15.0
        self.risk_sentiment = 0.0
        self.geopolitical_risk = 0.0
        
        # ===== EXTERNAL DATA =====
        self.swiss_economic = 0.0
        self.eur_economic = 0.0
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "EURCHF_Broker"
        self.agent_type = "Economic Calendar + SNB"
        self.specialization = "SNB Intervention + Safe-Haven Flow Analysis"
        
        logger.info(f"✅ EURCHF Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        """EURCHF-specific logic for SNB and economic data."""
        snb_intervention = market_data.get('snb_intervention', False)
        swiss_economic = market_data.get('swiss_economic', 0)
        eur_economic = market_data.get('eur_economic', 0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'EURCHF: '
        
        if snb_intervention:
            reasoning += 'SNB intervention detected → CHF weakness'
            bias = 'BUY'
            confidence_boost = 25
        elif swiss_economic > eur_economic:
            reasoning += 'Swiss economy stronger → CHF strength'
            bias = 'SELL'
            confidence_boost = 15
        elif eur_economic > swiss_economic:
            reasoning += 'Euro economy stronger → EUR strength'
            bias = 'BUY'
            confidence_boost = 15
        else:
            reasoning += 'Neutral economic data'
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'snb_intervention': snb_intervention
        }
    
    def _get_pair_confidence_boost(self) -> float:
        """EURCHF-specific confidence boost."""
        # If SNB intervention detected, boost confidence
        if self.snb_intervention:
            return 20.0
        # If safe-haven flow is strong
        if abs(self.safe_haven_flow) > 0.5:
            return 10.0
        return 5.0
    
    def analyze(self, signal_data: Dict) -> Dict:
        """EURCHF-specific analysis using base class."""
        try:
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURCHF-specific data =====
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
            self.vix = signal_data.get('VIX', 15.0)
            self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
            self.geopolitical_risk = signal_data.get('geopolitical_risk', 0.0)
            self.safe_haven_flow = signal_data.get('safe_haven_flow', 0.0)
            self.snb_policy = signal_data.get('snb_policy', 'NEUTRAL')
            self.ecb_policy = signal_data.get('ecb_policy', 'NEUTRAL')
            self.swiss_economic = signal_data.get('swiss_economic', 0)
            self.eur_economic = signal_data.get('eur_economic', 0)
            
            # ===== STEP 4: Detect range =====
            self._detect_range(closes)
            
            # ===== STEP 5: Detect SNB intervention =====
            snb_intervention = self._detect_snb_intervention(closes, signal_data)
            self.snb_intervention = snb_intervention['detected']
            self.snb_intervention_level = snb_intervention['level']
            
            # ===== STEP 6: Calculate policy divergence =====
            self.policy_divergence = self._calculate_policy_divergence()
            
            # ===== STEP 7: Generate EURCHF signal =====
            eurchf_result = self._generate_eurchf_signal(current_price, snb_intervention)
            
            # ===== STEP 8: Apply pair-specific logic boost =====
            pair_specific = self._apply_pair_specific_logic(signal_data)
            if pair_specific['bias'] != 'NEUTRAL' and eurchf_result['vote'] == 'HOLD':
                eurchf_result['vote'] = pair_specific['bias']
                eurchf_result['confidence'] = min(90, 60 + pair_specific['confidence_boost'])
                eurchf_result['reasoning'] = pair_specific['reasoning']
            
            # ===== STEP 9: Apply confidence boost =====
            eurchf_result['confidence'] = min(95, eurchf_result['confidence'] + self._get_pair_confidence_boost())
            
            # ===== STEP 10: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and eurchf_result['vote'] != 'HOLD' and eurchf_result['confidence'] >= 60:
                base_result['vote'] = eurchf_result['vote']
                base_result['confidence'] = eurchf_result['confidence']
                base_result['reasoning'] = f"{eurchf_result['reasoning']} (EURCHF override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and eurchf_result['vote'] != 'HOLD':
                if eurchf_result['confidence'] > base_conf + 10:
                    base_result['vote'] = eurchf_result['vote']
                    base_result['confidence'] = eurchf_result['confidence']
                    base_result['reasoning'] = f"{eurchf_result['reasoning']} (stronger than base)"
            
            # ===== STEP 11: Add EURCHF-specific data =====
            base_result['range_high'] = self.range_high
            base_result['range_low'] = self.range_low
            base_result['range_position'] = self.range_position
            base_result['is_ranging'] = self.is_ranging
            base_result['snb_intervention'] = self.snb_intervention
            base_result['snb_intervention_level'] = self.snb_intervention_level
            base_result['safe_haven_flow'] = self.safe_haven_flow
            base_result['vix'] = self.vix
            base_result['policy_divergence'] = self.policy_divergence
            base_result['ecb_policy'] = self.ecb_policy
            base_result['snb_policy'] = self.snb_policy
            base_result['swiss_economic'] = self.swiss_economic
            base_result['eur_economic'] = self.eur_economic
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURCHF Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def _detect_range(self, closes: List[float]):
        """Detect if EURCHF is in a range (it usually is)."""
        if len(closes) < 50:
            self.is_ranging = True
            return
        
        recent = closes[-50:]
        self.range_high = max(recent)
        self.range_low = min(recent)
        range_width = self.range_high - self.range_low
        
        # EURCHF typically ranges in a tight channel
        self.is_ranging = range_width < 0.01
        self.range_position = (closes[-1] - self.range_low) / range_width if range_width > 0 else 0.5
    
    def _detect_snb_intervention(self, closes: List[float], signal_data: Dict) -> Dict:
        """Detect possible SNB intervention."""
        
        # ===== PRIORITY: Check direct flag from market_data =====
        if signal_data.get('snb_intervention', False):
               return {'detected': True, 'level': 0.8}
        
        if len(closes) < 5:
               return {'detected': False, 'level': 0.0}
        
        # Sudden large move with high volume = possible intervention
        recent = closes[-5:]
        max_move = max(recent) - min(recent)
        max_move_pct = max_move / closes[-6] if len(closes) >= 6 else 0
        
        volume_ratio = signal_data.get('volume_ratio', 1.0)
        
        if max_move_pct > 0.005 and volume_ratio > 2.0:
               self.snb_intervention_history.append(True)
               return {'detected': True, 'level': min(1.0, max_move_pct * 100)}
        
        if len(self.snb_intervention_history) >= 3 and sum(self.snb_intervention_history[-3:]) >= 2:
               return {'detected': True, 'level': 0.7}
        
        return {'detected': False, 'level': 0.0}
    def _calculate_policy_divergence(self) -> float:
        """Calculate ECB vs SNB policy divergence."""
        policy_map = {'HAWKISH': 1, 'NEUTRAL': 0, 'DOVISH': -1}
        ecb_score = policy_map.get(self.ecb_policy, 0)
        snb_score = policy_map.get(self.snb_policy, 0)
        return ecb_score - snb_score
    
    def _generate_eurchf_signal(self, current_price: float, snb_intervention: Dict) -> Dict:
        """Generate EURCHF-specific signal with correct priority."""
        action = 'HOLD'
        confidence = 50
        reasoning = []
        snb_override = False
        
        # ===== PRIORITY 1: SNB INTERVENTION (HIGHEST) =====
        if snb_intervention['detected']:
              action = 'BUY'
              confidence = 90
              reasoning.append(f"🏦 SNB INTERVENTION DETECTED - BUY EURCHF")
              snb_override = True
              return {
                      'vote': action,
                      'confidence': confidence,
                      'reasoning': '; '.join(reasoning),
                      'snb_override': snb_override
              }
        
        # ===== PRIORITY 2: RANGE TRADING =====
        if self.is_ranging and self.range_high > 0 and self.range_low > 0:
              range_width = self.range_high - self.range_low
              if range_width > 0:
                      position = (current_price - self.range_low) / range_width
                      self.range_position = position
                      
                      # Near range top → SELL
                      if position > 0.85:
                            action = 'SELL'
                            confidence = 80
                            reasoning.append(f"EURCHF at range top ({self.range_high:.5f}) - SELL")
                      # Near range bottom → BUY
                      elif position < 0.15:
                            action = 'BUY'
                            confidence = 80
                            reasoning.append(f"EURCHF at range bottom ({self.range_low:.5f}) - BUY")
                      # Middle of range → HOLD
                      else:
                            action = 'HOLD'
                            confidence = 50
                            reasoning.append(f"EURCHF in middle of range ({position:.0%}) - HOLD")
        
        # ===== PRIORITY 3: SAFE HAVEN FLOW =====
        if self.safe_haven_flow < -0.3:
              if action == 'SELL':
                      confidence = min(95, confidence + 10)
                      reasoning.append("Safe haven flow into CHF confirms SELL")
              elif action == 'HOLD':
                      action = 'SELL'
                      confidence = 60
                      reasoning.append("Safe haven flow into CHF → SELL")
              elif action == 'BUY':
                      confidence = max(40, confidence - 15)
                      reasoning.append("Safe haven flow contradicts BUY")
                      if confidence < 50:
                            action = 'HOLD'
        
        elif self.safe_haven_flow > 0.3:
              if action == 'BUY':
                      confidence = min(95, confidence + 10)
                      reasoning.append("Safe haven flow out of CHF confirms BUY")
              elif action == 'HOLD':
                      action = 'BUY'
                      confidence = 60
                      reasoning.append("Safe haven flow out of CHF → BUY")
              elif action == 'SELL':
                      confidence = max(40, confidence - 15)
                      reasoning.append("Safe haven flow contradicts SELL")
                      if confidence < 50:
                            action = 'HOLD'
        
        # ===== PRIORITY 4: VIX SPIKE =====
        if self.vix > 25:
              if action == 'SELL':
                      confidence = min(95, confidence + 10)
                      reasoning.append(f"VIX spike ({self.vix:.1f}) confirms CHF strength")
              elif action == 'HOLD':
                      action = 'SELL'
                      confidence = 60
                      reasoning.append(f"VIX spike ({self.vix:.1f}) → SELL")
              elif action == 'BUY':
                      confidence = max(40, confidence - 10)
                      reasoning.append("VIX spike contradicts BUY")
                      if confidence < 50:
                            action = 'HOLD'
        
        elif self.vix < 15:
              if action == 'BUY':
                      confidence = min(95, confidence + 10)
                      reasoning.append(f"Low VIX ({self.vix:.1f}) confirms CHF weakness")
              elif action == 'HOLD':
                      action = 'BUY'
                      confidence = 60
                      reasoning.append(f"Low VIX ({self.vix:.1f}) → BUY")
              elif action == 'SELL':
                      confidence = max(40, confidence - 10)
                      reasoning.append("Low VIX contradicts SELL")
                      if confidence < 50:
                            action = 'HOLD'
        
        # ===== PRIORITY 5: POLICY DIVERGENCE =====
        if abs(self.policy_divergence) > 0.5:
              if self.policy_divergence > 0:
                      if action == 'BUY':
                            confidence = min(95, confidence + 10)
                            reasoning.append("ECB more hawkish than SNB → EUR strength")
                      elif action == 'HOLD':
                            action = 'BUY'
                            confidence = 60
                            reasoning.append("ECB hawkish vs SNB dovish → BUY")
              else:
                      if action == 'SELL':
                            confidence = min(95, confidence + 10)
                            reasoning.append("SNB more hawkish than ECB → CHF strength")
                      elif action == 'HOLD':
                            action = 'SELL'
                            confidence = 60
                            reasoning.append("SNB hawkish vs ECB dovish → SELL")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
              reasoning = ["EURCHF: No clear signal - await range extreme or catalyst"]
        
        return {
              'vote': action,
              'confidence': min(95, confidence),
              'reasoning': '; '.join(reasoning) if reasoning else 'EURCHF safe haven analysis',
              'snb_override': snb_override
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
        """Monte Carlo forecast for EURCHF."""
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
            'is_ranging': self.is_ranging,
            'snb_intervention': self.snb_intervention,
            'safe_haven_flow': self.safe_haven_flow,
            'vix': self.vix,
            'policy_divergence': self.policy_divergence,
            'timestamp': datetime.now().isoformat()
        }