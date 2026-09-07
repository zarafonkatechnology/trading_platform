"""
Supervisor - 4-Step Macro-to-Micro Validation
Step 1: Macro (Whale/COT) - Is Big Money positioned for this move?
Step 2: Structure (Fibonacci) - Are we at key levels?
Step 3: Pattern (Candlestick) - Is there a reversal pattern?
Step 4: Trigger (Volume/RSI) - Is there confirmation?
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Supervisor:
    def __init__(self, db_manager=None):
        self.decision_history = []
        self.step_results = {}
    
    def step1_macro_check(self, votes, market_features):
        """
        Step 1: MACRO - Whale Agent
        Is the "Big Money" positioned for this move?
        """
        whale_vote = votes.get('Agent_G', {})
        whale_action = whale_vote.get('vote', 'HOLD')
        whale_confidence = whale_vote.get('confidence', 50)
        
        # Get COT extreme condition
        cot_extreme = market_features.get('cot_extreme', False)
        cot_direction = market_features.get('cot_direction', 'neutral')
        
        result = {
            'passed': True,
            'weight': 1.0,
            'message': 'Macro check passed'
        }
        
        # VETO: If whale says SELL with high confidence, block everything
        if whale_action == 'SELL' and whale_confidence > 80:
            result['passed'] = False
            result['weight'] = 0
            result['message'] = f"VETO: Whale SELL with {whale_confidence}% confidence - Big money selling"
            return result
        
        # Boost if whale aligns with extreme COT
        if cot_extreme and cot_direction == 'bullish' and whale_action == 'BUY':
            result['weight'] = 1.5
            result['message'] = "EXTREME COT + Whale alignment - Macro strongly bullish"
        
        return result
    
    def step2_structure_check(self, votes, market_features):
        """
        Step 2: STRUCTURE - Fibonacci/TechnicalMaster
        Are we at 61.8% or 78.6% Fibonacci level?
        """
        fib_vote = votes.get('Agent_H', {})
        fib_action = fib_vote.get('vote', 'HOLD')
        fib_confidence = fib_vote.get('confidence', 50)
        
        fib_level = market_features.get('fib_level', 0)
        
        result = {
            'passed': True,
            'weight': 1.0,
            'message': 'Structure check passed'
        }
        
        # Best levels: 0.618 (Golden) and 0.786 (Deep Value)
        if fib_level in [0.618, 0.786]:
            result['weight'] = 1.3
            result['message'] = f"At optimal Fibonacci level: {fib_level*100:.1f}%"
        elif fib_level in [0.382, 0.5]:
            result['weight'] = 0.8
            result['message'] = f"At secondary Fibonacci level: {fib_level*100:.1f}%"
        else:
            result['weight'] = 0.5
            result['message'] = "Not at key Fibonacci level"
        
        return result
    
    def step3_pattern_check(self, votes, market_features):
        """
        Step 3: PATTERN - Candlestick/PatternAgent
        Is there a reversal pattern (Hammer, Engulfing, Morning Star)?
        """
        pattern_vote = votes.get('Agent_F', {})
        pattern_action = pattern_vote.get('vote', 'HOLD')
        pattern_confidence = pattern_vote.get('confidence', 50)
        
        concordance_score = market_features.get('concordance_score', 0)
        
        result = {
            'passed': True,
            'weight': 1.0,
            'message': 'Pattern check passed'
        }
        
        # High concordance = strong pattern confirmation
        if concordance_score >= 0.8:
            result['weight'] = 1.5
            result['message'] = f"EXCELLENT pattern: Concordance score {concordance_score:.2f}"
        elif concordance_score >= 0.6:
            result['weight'] = 1.2
            result['message'] = f"STRONG pattern: Concordance score {concordance_score:.2f}"
        elif concordance_score >= 0.4:
            result['weight'] = 0.8
            result['message'] = f"MODERATE pattern: Concordance score {concordance_score:.2f}"
        else:
            result['weight'] = 0.4
            result['message'] = f"WEAK pattern: Concordance score {concordance_score:.2f}"
        
        return result
    
    def step4_trigger_check(self, votes, market_features):
        """
        Step 4: TRIGGER - Volume/RSI
        Is there a volume spike or RSI divergence?
        """
        rsi_vote = votes.get('Agent_B', {})
        rsi_action = rsi_vote.get('vote', 'HOLD')
        rsi_confidence = rsi_vote.get('confidence', 50)
        
        volume_spike = market_features.get('volume_spike', False)
        rsi_divergence = market_features.get('rsi_divergence', False)
        
        result = {
            'passed': True,
            'weight': 1.0,
            'message': 'Trigger check passed'
        }
        
        # Volume spike confirms
        if volume_spike:
            result['weight'] = 1.3
            result['message'] = "Volume spike confirmation"
        
        # RSI divergence is strong confirmation
        if rsi_divergence:
            result['weight'] = 1.4
            result['message'] = "RSI divergence confirmation"
        
        # Both is excellent
        if volume_spike and rsi_divergence:
            result['weight'] = 1.6
            result['message'] = "Volume spike + RSI divergence - STRONG TRIGGER"
        
        return result
    def validate_pattern(self, pattern_result):
      """Validate structural pattern against stored rules"""
      if not pattern_result:
        return {'valid': False, 'reason': 'No pattern detected'}
    
      pattern_name = pattern_result.get('pattern')

      if pattern_name == 'head_and_shoulders':
        # Check 61.8% alignment
        if not pattern_result.get('rsi_divergence', False):
            return {'valid': False, 'reason': 'RSI divergence not confirmed'}
    
      elif pattern_name == 'double_top':
        # Check MACD weakening
        if not pattern_result.get('macd_weakening', False):
            return {'valid': False, 'reason': 'MACD not weakening at second peak'}
    
        return {'valid': True, 'reason': 'Pattern validated'}
    def calculate_final_weight(self, step_results):
        """
        Calculate final confidence weight based on all 4 steps
        """
        total_weight = 1.0
        for step in step_results.values():
            total_weight *= step['weight']
        
        return min(2.0, total_weight)
    
    def process_votes(self, votes, market_features=None):
        """
        Complete 4-step validation before any trade
        """
        if market_features is None:
            market_features = {}
        
        # Step 1: MACRO - Whale Agent
        step1 = self.step1_macro_check(votes, market_features)
        self.step_results['macro'] = step1
        
        # If macro fails, reject immediately
        if not step1['passed']:
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'rejection_reason': step1['message'],
                'step_failed': 'MACRO',
                'steps': self.step_results
            }
        
        # Step 2: STRUCTURE - Fibonacci
        step2 = self.step2_structure_check(votes, market_features)
        self.step_results['structure'] = step2
        
        # Step 3: PATTERN - Candlestick
        step3 = self.step3_pattern_check(votes, market_features)
        self.step_results['pattern'] = step3
        
        # Step 4: TRIGGER - Volume/RSI
        step4 = self.step4_trigger_check(votes, market_features)
        self.step_results['trigger'] = step4
        
        # Calculate final weight
        final_weight = self.calculate_final_weight(self.step_results)
        
        # Count votes
        buy_count = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell_count = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        hold_count = sum(1 for v in votes.values() if v.get('vote') == 'HOLD')
        total = len(votes)
        
        # Calculate weighted decision
        weighted_buy = sum(v.get('confidence', 0) for v in votes.values() if v.get('vote') == 'BUY')
        weighted_sell = sum(v.get('confidence', 0) for v in votes.values() if v.get('vote') == 'SELL')
        
        if weighted_buy > weighted_sell and buy_count > sell_count:
            final_decision = 'BUY'
            confidence = (weighted_buy / total) if total > 0 else 0
        elif weighted_sell > weighted_buy and sell_count > buy_count:
            final_decision = 'SELL'
            confidence = (weighted_sell / total) if total > 0 else 0
        else:
            final_decision = 'HOLD'
            confidence = 50
        
        # Apply final weight multiplier
        confidence = min(95, confidence * final_weight)
        
        result = {
            'decision': final_decision,
            'confidence': round(confidence, 1),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'final_weight': round(final_weight, 2),
            'steps': self.step_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log the 4-step validation
        logger.info(f"4-STEP VALIDATION:")
        logger.info(f"  Step1 (Macro/Whale): {step1['message']} (Weight: {step1['weight']})")
        logger.info(f"  Step2 (Structure/Fib): {step2['message']} (Weight: {step2['weight']})")
        logger.info(f"  Step3 (Pattern/Candle): {step3['message']} (Weight: {step3['weight']})")
        logger.info(f"  Step4 (Trigger/VolumeRSI): {step4['message']} (Weight: {step4['weight']})")
        logger.info(f"Final Decision: {final_decision} ({confidence:.1f}%) - Total Weight: {final_weight}")
        
        self.decision_history.append(result)
        
        return result
    
    def get_decision_history(self, limit=50):
        return self.decision_history[-limit:]
