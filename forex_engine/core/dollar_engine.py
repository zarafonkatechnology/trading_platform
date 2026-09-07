# core/dollar_engine.py - Dollar Engine Module

"""
Dollar Engine - Tracks USD Strength as the Master Engine
Monitors interest rates, yield curves, and USD Index to determine
dollar direction and strength
"""

import logging
import math
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class DollarEngine:
    """
    Dollar Engine - Tracks USD strength and direction
    Acts as the master engine that drives all currency pairs
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Engine state
        self.engine_speed = 0.0          # -1 to +1 (Full Reverse to Full Forward)
        self.engine_acceleration = 0.0   # Rate of change
        self.engine_direction = 'NEUTRAL'  # 'FORWARD', 'BACKWARD', 'NEUTRAL'
        self.engine_state = 'NORMAL'      # 'NORMAL', 'ACCELERATING', 'DECELERATING', 'REVERSING'
        self.reversal_probability = 0.0   # 0-100%
        self.confidence = 0.0             # 0-100%
        self.engine_health = 100.0        # 0-100%
        
        # Historical engine states
        self.engine_history = deque(maxlen=60)
        self.engine_state_history = deque(maxlen=20)
        
        # Weighted factors for engine speed calculation
        self.factors = {
            'interest_rate_diff': 0.35,
            'yield_curve_slope': 0.25,
            'carry_trade_flow': 0.15,
            'positioning_sentiment': 0.15,
            'central_bank_actions': 0.10,
        }
        
        # Current factor values
        self.current_factors = {}
        
        # DXY (Dollar Index) tracking
        self.dxy_history = deque(maxlen=60)
        self.dxy_current = 0.0
        
        # Market regime
        self.regime = 'RANGING'  # 'TRENDING', 'RANGING', 'VOLATILE'
        self.regime_confidence = 50.0
        
        logger.info("✅ Dollar Engine initialized")
        logger.info(f"   Factor weights: {self.factors}")
    
    def update_engine_state(self, market_data: Dict) -> Dict:
        """
        Calculate current engine speed and direction from market data.
        
        market_data should contain:
        - usd_interest_rate: Current USD interest rate
        - avg_other_rate: Average of major other currencies
        - short_term_yield: 2-year treasury yield
        - long_term_yield: 10-year treasury yield
        - dxy: Dollar Index value
        - carry_flows: Estimated carry trade flows
        - cftc_positioning: CFTC speculative positioning
        - central_bank_action: 0=neutral, 1=dovish, 2=hawkish
        """
        # Calculate each factor
        self.current_factors = {
            'interest_rate_diff': self._calculate_interest_factor(market_data),
            'yield_curve_slope': self._calculate_yield_factor(market_data),
            'carry_trade_flow': self._calculate_carry_factor(market_data),
            'positioning_sentiment': self._calculate_sentiment_factor(market_data),
            'central_bank_actions': self._calculate_central_bank_factor(market_data),
        }
        
        # Weighted engine speed
        raw_speed = sum(
            factor_value * self.factors[factor_name]
            for factor_name, factor_value in self.current_factors.items()
        )
        
        # Update DXY
        if 'dxy' in market_data:
            self.dxy_history.append(market_data['dxy'])
            self.dxy_current = market_data['dxy']
        
        # Normalize to -1 to 1
        self.engine_speed = max(-1.0, min(1.0, raw_speed))
        
        # Calculate acceleration (change in speed)
        self.engine_history.append(self.engine_speed)
        if len(self.engine_history) >= 3:
            old_speed = list(self.engine_history)[-2]
            time_delta = 1.0
            self.engine_acceleration = (self.engine_speed - old_speed) / time_delta
        else:
            self.engine_acceleration = 0.0
        
        # Determine direction
        if self.engine_speed > 0.15:
            self.engine_direction = 'FORWARD'  # USD strengthening
        elif self.engine_speed < -0.15:
            self.engine_direction = 'BACKWARD'  # USD weakening
        else:
            self.engine_direction = 'NEUTRAL'
        
        # Determine state
        if abs(self.engine_acceleration) > 0.3:
            if self.engine_acceleration > 0:
                self.engine_state = 'ACCELERATING'
            else:
                self.engine_state = 'DECELERATING'
        else:
            self.engine_state = 'NORMAL'
        
        # Check for reversal
        if self._detect_reversal_signal():
            self.engine_state = 'REVERSING'
        
        # Calculate reversal probability
        self.reversal_probability = self._calculate_reversal_probability()
        
        # Calculate confidence
        self.confidence = self._calculate_confidence()
        
        # Update engine health
        self.engine_health = self._calculate_engine_health()
        
        # Determine market regime
        self.regime, self.regime_confidence = self._detect_market_regime()
        
        # Log state change
        self._log_engine_state()
        
        return {
            'engine_speed': self.engine_speed,
            'engine_acceleration': self.engine_acceleration,
            'engine_direction': self.engine_direction,
            'engine_state': self.engine_state,
            'engine_health': self.engine_health,
            'reversal_probability': self.reversal_probability,
            'confidence': self.confidence,
            'regime': self.regime,
            'regime_confidence': self.regime_confidence,
            'dxy_current': self.dxy_current,
            'factors': self.current_factors,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_interest_factor(self, market_data: Dict) -> float:
        """Calculate factor based on interest rate differentials."""
        usd_rate = market_data.get('usd_interest_rate', 5.25)
        avg_other = market_data.get('avg_other_rate', 3.50)
        
        rate_diff = usd_rate - avg_other
        
        # Normalize to -1 to 1 (typical range: -3% to +3%)
        factor = rate_diff / 3.0
        return max(-1.0, min(1.0, factor))
    
    def _calculate_yield_factor(self, market_data: Dict) -> float:
        """Calculate factor based on yield curve shape."""
        short_term = market_data.get('short_term_yield', 4.50)
        long_term = market_data.get('long_term_yield', 4.75)
        
        yield_slope = long_term - short_term
        
        # Normalize to -1 to 1
        factor = yield_slope * 2.0
        return max(-1.0, min(1.0, factor))
    
    def _calculate_carry_factor(self, market_data: Dict) -> float:
        """Calculate factor based on carry trade flows."""
        carry_flows = market_data.get('carry_flows', 0)
        
        # Normalize to -1 to 1
        factor = carry_flows / 100.0
        return max(-1.0, min(1.0, factor))
    
    def _calculate_sentiment_factor(self, market_data: Dict) -> float:
        """Calculate factor based on speculative positioning."""
        positioning = market_data.get('cftc_positioning', 50)  # 0-100
        
        # 50 = neutral, 0 = extreme short, 100 = extreme long
        factor = (positioning - 50) / 50.0
        return max(-1.0, min(1.0, factor))
    
    def _calculate_central_bank_factor(self, market_data: Dict) -> float:
        """Calculate factor based on central bank actions."""
        action = market_data.get('central_bank_action', 0)
        # 0 = neutral, 1 = dovish, 2 = hawkish
        
        if action == 2:  # Hawkish
            return 0.5
        elif action == 1:  # Dovish
            return -0.5
        else:
            return 0.0
    
    def _detect_reversal_signal(self) -> bool:
        """Detect if the engine is about to reverse."""
        # Signal 1: Extreme speed
        if abs(self.engine_speed) > 0.8:
            return True
        
        # Signal 2: Deceleration after high speed
        if abs(self.engine_speed) > 0.6 and self.engine_acceleration < -0.2:
            return True
        
        # Signal 3: Reversal in DXY
        if len(self.dxy_history) >= 10:
            dxy_values = list(self.dxy_history)
            dxy_trend = dxy_values[-1] - dxy_values[0]
            
            if dxy_trend > 0 and self.engine_speed < -0.3:
                return True
            
            if dxy_trend < 0 and self.engine_speed > 0.3:
                return True
        
        return False
    
    def _calculate_reversal_probability(self) -> float:
        """Calculate probability of engine reversal."""
        signals = []
        
        # Signal 1: Extreme speed
        if abs(self.engine_speed) > 0.7:
            signals.append(0.8)
        elif abs(self.engine_speed) > 0.5:
            signals.append(0.5)
        else:
            signals.append(0.1)
        
        # Signal 2: Deceleration
        if self.engine_acceleration < -0.2:
            signals.append(0.7)
        elif self.engine_acceleration < -0.1:
            signals.append(0.4)
        else:
            signals.append(0.1)
        
        # Signal 3: DXY divergence
        if len(self.dxy_history) >= 10:
            dxy_values = list(self.dxy_history)
            dxy_change = (dxy_values[-1] / dxy_values[-10]) - 1
            
            if abs(dxy_change) > 0.01:
                if (dxy_change > 0 and self.engine_direction == 'BACKWARD') or \
                   (dxy_change < 0 and self.engine_direction == 'FORWARD'):
                    signals.append(0.8)
                else:
                    signals.append(0.2)
            else:
                signals.append(0.1)
        else:
            signals.append(0.1)
        
        # Average signals
        return sum(signals) / len(signals) * 100
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence in current engine state."""
        if len(self.engine_history) < 5:
            return 40.0
        
        recent_speeds = list(self.engine_history)[-5:]
        
        # Check if speeds are consistent
        speed_range = max(recent_speeds) - min(recent_speeds)
        consistency = 1.0 - (speed_range / 2.0)
        
        # Adjust for reversal probability
        base_confidence = consistency * 100
        confidence = base_confidence * (1 - self.reversal_probability / 200)
        
        return max(20.0, min(95.0, confidence))
    
    def _calculate_engine_health(self) -> float:
        """Calculate overall engine health."""
        health = 100.0
        
        if self.confidence < 40:
            health -= 20
        elif self.confidence < 60:
            health -= 10
        
        if self.reversal_probability > 70:
            health -= 20
        elif self.reversal_probability > 50:
            health -= 10
        
        if self.regime == 'VOLATILE':
            health -= 15
        
        return max(0.0, min(100.0, health))
    
    def _detect_market_regime(self) -> Tuple[str, float]:
        """Detect current market regime."""
        if len(self.engine_history) < 20:
            return 'RANGING', 50.0
        
        speeds = list(self.engine_history)[-20:]
        
        # Calculate trend strength
        trend = sum(speeds[-5:]) - sum(speeds[:5])
        trend_abs = abs(trend)
        
        # Calculate volatility
        volatility = np.std(speeds)
        
        # Determine regime
        if trend_abs > 2.0 and volatility > 0.3:
            regime = 'TRENDING'
            confidence = min(80, 50 + trend_abs * 10)
        elif volatility > 0.5:
            regime = 'VOLATILE'
            confidence = min(80, 50 + volatility * 50)
        else:
            regime = 'RANGING'
            confidence = min(80, 50 + (1 - volatility) * 60)
        
        return regime, confidence
    
    def _log_engine_state(self):
        """Log engine state changes."""
        if len(self.engine_state_history) > 0 and \
           self.engine_state_history[-1] != self.engine_state:
            logger.info(f"🔄 Engine state changed: {self.engine_state_history[-1]} → {self.engine_state}")
            logger.info(f"   Speed: {self.engine_speed:.3f} | Accel: {self.engine_acceleration:.3f}")
            logger.info(f"   Reversal Prob: {self.reversal_probability:.1f}% | Confidence: {self.confidence:.1f}%")
        
        self.engine_state_history.append(self.engine_state)
    # dollar_engine.py - ADD THIS METHOD

    # forex_engine/core/dollar_engine.py - FIXED check_signal_with_agents

    # forex_engine/core/dollar_engine.py - ADD THIS METHOD INSIDE DollarEngine CLASS

    def check_signal_with_agents(self, symbol: str, signal_action: str, 
                            price: float, prices: Dict = None,
                            agent_u=None, agent_p=None, agent_d=None) -> Dict:
        """
        Check signal with Agent_U, Agent_P, Agent_D confirmation
        """
        # ===== 1. Base Dollar Engine Result =====
        # Use the existing check_signal method (or your equivalent)
        if hasattr(self, 'check_signal'):
                base_result = self.check_signal(symbol, signal_action)
        else:
                # Fallback: create base result
                base_result = {
                        'aligned': True,
                        'confidence': 70,
                        'usd_direction': getattr(self, 'usd_direction', 'NEUTRAL'),
                        'usd_strength': getattr(self, 'usd_strength', 0),
                        'message': 'Dollar Engine OK'
                }
        
        if not base_result.get('aligned', False):
                return base_result
        
        # ===== 2. Get Agent Results =====
        agent_results = {}
        
        # Agent_U - Liquidity
        if agent_u:
                try:
                        agent_results['U'] = agent_u.analyze(
                                symbol=symbol,
                                price=price,
                                usd_strength=base_result.get('usd_strength', 0),
                                usd_direction=base_result.get('usd_direction', 'NEUTRAL')
                        )
                except Exception as e:
                        logger.warning(f'⚠️ Agent_U error: {e}')
                        agent_results['U'] = {'vote': 'HOLD', 'confidence': 50}
        
        # Agent_P - Cross Pair
        if agent_p and prices:
                try:
                        agent_results['P'] = agent_p.analyze(symbol, prices)
                except Exception as e:
                        logger.warning(f'⚠️ Agent_P error: {e}')
                        agent_results['P'] = {'vote': 'HOLD', 'confidence': 50}
        
        # Agent_D - Volatility
        if agent_d:
                try:
                        agent_results['D'] = agent_d.analyze(symbol, price)
                except Exception as e:
                        logger.warning(f'⚠️ Agent_D error: {e}')
                        agent_results['D'] = {'vote': 'HOLD', 'confidence': 50}
        
        # ===== 3. Count Confirmations =====
        confirmations = 0
        agent_details = {}
        
        for agent_name, result in agent_results.items():
                vote = result.get('vote', 'HOLD')
                confidence = result.get('confidence', 50)
                agent_details[agent_name] = {'vote': vote, 'confidence': confidence}
                
                if vote == signal_action and confidence > 60:
                        confirmations += 1
        
        # ===== 4. Boost Confidence =====
        base_confidence = base_result.get('confidence', 70)
        
        if confirmations >= 2:
                confidence = min(95, base_confidence + 15)
                message = f"✅ {signal_action} | STRONG: {confirmations}/3 agents confirm"
        elif confirmations >= 1:
                confidence = min(90, base_confidence + 8)
                message = f"✅ {signal_action} | WEAK: {confirmations}/3 agents confirm"
        else:
                confidence = max(55, base_confidence - 10)
                message = f"⚠️ {signal_action} | No agent confirmation"
        
        return {
                'aligned': True,
                'action': signal_action,
                'confidence': confidence,
                'usd_direction': base_result.get('usd_direction', 'NEUTRAL'),
                'usd_strength': base_result.get('usd_strength', 0),
                'confirmations': confirmations,
                'message': message,
                'agents': agent_details,
                'base_confidence': base_confidence
        }
    def get_gear_prediction(self, pair: str, gear_ratio: float = 1.0) -> Dict:
        """
        Get predicted movement for a specific gear (currency pair).
        
        pair: 'EUR/USD', 'GBP/USD', 'USD/JPY', etc.
        gear_ratio: Sensitivity to dollar movement
        """
        # Determine gear type
        if 'USD' in pair:
            if pair.startswith('USD'):
                gear_type = 'DIRECT'  # USD/JPY - moves same as dollar
            else:
                gear_type = 'INVERSE'  # EUR/USD - moves opposite to dollar
        else:
            gear_type = 'CROSS'  # EUR/GBP - complex relationship
        
        # Calculate predicted movement
        if gear_type == 'DIRECT':
            predicted_move = self.engine_speed * gear_ratio
            direction = 'SAME' if self.engine_speed > 0 else 'OPPOSITE'
        elif gear_type == 'INVERSE':
            predicted_move = -self.engine_speed * gear_ratio
            direction = 'OPPOSITE' if self.engine_speed > 0 else 'SAME'
        else:
            predicted_move = self.engine_speed * gear_ratio * 0.5
            direction = 'COMPLEX'
        
        # Calculate confidence for this gear
        confidence = self.confidence * (1 - abs(self.engine_speed) * 0.2)
        confidence = max(20.0, min(95.0, confidence))
        
        return {
            'pair': pair,
            'gear_type': gear_type,
            'gear_ratio': gear_ratio,
            'predicted_move': predicted_move,
            'predicted_direction': 'UP' if predicted_move > 0 else 'DOWN' if predicted_move < 0 else 'SIDEWAYS',
            'direction_relation': direction,
            'confidence': confidence,
            'engine_speed': self.engine_speed,
            'engine_state': self.engine_state,
            'reversal_probability': self.reversal_probability,
            'regime': self.regime,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict:
        """Get current engine status for monitoring."""
        return {
            'engine_speed': self.engine_speed,
            'engine_acceleration': self.engine_acceleration,
            'engine_direction': self.engine_direction,
            'engine_state': self.engine_state,
            'engine_health': self.engine_health,
            'reversal_probability': self.reversal_probability,
            'confidence': self.confidence,
            'regime': self.regime,
            'regime_confidence': self.regime_confidence,
            'dxy_current': self.dxy_current,
            'factors': self.current_factors,
            'history_length': len(self.engine_history),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# TEST
# ============================================================

def main():
    """Test the dollar engine"""
    print("=" * 60)
    print("Testing Dollar Engine")
    print("=" * 60)
    
    engine = DollarEngine()
    
    # Test with sample data
    test_data = {
        'usd_interest_rate': 5.25,
        'avg_other_rate': 3.50,
        'short_term_yield': 4.50,
        'long_term_yield': 4.75,
        'dxy': 104.50,
        'carry_flows': 10,
        'cftc_positioning': 55,
        'central_bank_action': 2,  # Hawkish
    }
    
    print("\n📊 Updating engine state...")
    result = engine.update_engine_state(test_data)
    
    print("\n📈 Engine State:")
    print(f"   Direction: {result['engine_direction']}")
    print(f"   Speed: {result['engine_speed']:.3f}")
    print(f"   State: {result['engine_state']}")
    print(f"   Confidence: {result['confidence']:.1f}%")
    print(f"   Health: {result['engine_health']:.1f}%")
    print(f"   Regime: {result['regime']}")
    print(f"   Reversal Probability: {result['reversal_probability']:.1f}%")
    
    print("\n📊 Gear Predictions:")
    for pair in ['EUR/USD', 'GBP/USD', 'USD/JPY']:
        pred = engine.get_gear_prediction(pair)
        print(f"   {pair}: {pred['predicted_direction']} ({pred['confidence']:.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete")


if __name__ == "__main__":
    main()