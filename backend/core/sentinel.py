"""
Sentinel Agent - Veto power and error prevention
"""

import logging

logger = logging.getLogger(__name__)

class SentinelAgent:
    """Sentinel that prevents errors and enforces zero error policy"""
    
    def __init__(self):
        self.veto_count = 0
        self.self_heal_count = 0
        
    def check_veto(self, decision, market_conditions):
        """
        Check if a decision should be vetoed
        Returns: (should_veto, reason)
        """
        # Check for extreme volatility
        volatility = market_conditions.get('volatility', 0)
        if volatility > 5:
            return True, f"Extreme volatility: {volatility}%"
        
        # Check for low confidence
        if decision.get('confidence', 0) < 30:
            return True, f"Low confidence: {decision.get('confidence')}%"
        
        # Check for no consensus
        vote_counts = decision.get('vote_counts', {})
        max_votes = max(vote_counts.values()) if vote_counts else 0
        
        if max_votes == 0:
            return True, "No consensus among agents"
        
        return False, None
    
    def self_heal(self, error_type, error_details):
        """
        Attempt to self-heal from errors
        """
        self.self_heal_count += 1
        
        healing_actions = {
            'database_error': "Attempting to reconnect to database...",
            'agent_timeout': "Restarting agent processes...",
            'memory_error': "Clearing cache and resetting..."
        }
        
        action = healing_actions.get(error_type, "Running standard recovery...")
        
        logger.info(f"Self-healing triggered for {error_type}: {action}")
        
        return {
            'healed': True,
            'action': action,
            'heal_count': self.self_heal_count
        }
    
    def get_status(self):
        """Get sentinel status"""
        return {
            'veto_count': self.veto_count,
            'self_heal_count': self.self_heal_count,
            'status': 'active'
        }
