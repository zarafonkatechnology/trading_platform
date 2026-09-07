"""
Gatekeeper Agent - Final authentication before execution
"""

import logging

logger = logging.getLogger(__name__)

class GatekeeperAgent:
    """Gatekeeper that verifies three pillars before execution"""
    
    def __init__(self):
        self.gates_opened = 0
        self.gates_blocked = 0
        
    def verify(self, trade_request):
        """
        Verify trade request against three pillars
        Returns: (passed, reason, details)
        """
        details = {
            'pillar1_identity': False,
            'pillar2_logic': False,
            'pillar3_resource': False
        }
        
        # Pillar 1: Identity Verification
        agent_name = trade_request.get('agent_name')
        if agent_name and agent_name.startswith('Agent_'):
            details['pillar1_identity'] = True
        else:
            self.gates_blocked += 1
            return False, "Identity verification failed", details
        
        # Pillar 2: Logic Sanity
        quantity = trade_request.get('quantity', 0)
        if 0 < quantity <= 10000:
            details['pillar2_logic'] = True
        else:
            self.gates_blocked += 1
            return False, f"Invalid quantity: {quantity}", details
        
        # Pillar 3: Resource Check
        price = trade_request.get('price', 0)
        cost = price * quantity
        if cost <= 100000:
            details['pillar3_resource'] = True
        else:
            self.gates_blocked += 1
            return False, f"Trade cost exceeds limit: {cost}", details
        
        # All pillars passed
        self.gates_opened += 1
        
        return True, "All pillars verified", details
    
    def get_status(self):
        """Get gatekeeper status"""
        total = self.gates_opened + self.gates_blocked
        block_rate = (self.gates_blocked / total * 100) if total > 0 else 0
        
        return {
            'gates_opened': self.gates_opened,
            'gates_blocked': self.gates_blocked,
            'block_rate': round(block_rate, 2),
            'status': 'active'
        }
