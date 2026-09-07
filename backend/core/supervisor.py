"""
Supervisor - Processes votes and makes final decisions
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Supervisor:
    """Supervisor that processes agent votes and makes final decisions"""
    
    def __init__(self):
        self.decision_history = []
    
    def process_votes(self, votes):
        """
        Process votes from all agents and determine final decision
        
        Args:
            votes: Dictionary of agent votes {'Agent_A': {'vote': 'BUY', 'confidence': 85}, ...}
        
        Returns:
            Dictionary with decision, confidence, and vote counts
        """
        # Count votes
        buy_count = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell_count = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        hold_count = sum(1 for v in votes.values() if v.get('vote') == 'HOLD')
        total = len(votes)
        
        # Calculate weighted scores based on confidence
        weighted_buy = sum(v.get('confidence', 0) for v in votes.values() if v.get('vote') == 'BUY')
        weighted_sell = sum(v.get('confidence', 0) for v in votes.values() if v.get('vote') == 'SELL')
        weighted_hold = sum(v.get('confidence', 0) for v in votes.values() if v.get('vote') == 'HOLD')
        
        # Determine final decision
        if weighted_buy > weighted_sell and weighted_buy > weighted_hold:
            final_decision = 'BUY'
            confidence = (weighted_buy / total) if total > 0 else 0
        elif weighted_sell > weighted_buy and weighted_sell > weighted_hold:
            final_decision = 'SELL'
            confidence = (weighted_sell / total) if total > 0 else 0
        else:
            final_decision = 'HOLD'
            confidence = (weighted_hold / total) if total > 0 else 50
        
        # Calculate percentages
        buy_percent = (buy_count / total) * 100 if total > 0 else 0
        sell_percent = (sell_count / total) * 100 if total > 0 else 0
        hold_percent = (hold_count / total) * 100 if total > 0 else 0
        
        result = {
            'decision': final_decision,
            'confidence': round(confidence, 1),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'buy_percent': round(buy_percent, 1),
            'sell_percent': round(sell_percent, 1),
            'hold_percent': round(hold_percent, 1),
            'total_votes': total,
            'timestamp': datetime.now().isoformat()
        }
        
        self.decision_history.append(result)
        logger.info(f"Supervisor decision: {final_decision} with {confidence:.1f}% confidence")
        
        return result
    
    def get_decision_history(self, limit=50):
        """Get recent decision history"""
        return self.decision_history[-limit:]
    
    def get_agent_accuracy(self, votes_history):
        """Calculate accuracy for each agent based on past votes"""
        # This would require tracking actual outcomes
        pass
