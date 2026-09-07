"""
Agent Discovery Protocol - Safe version
"""

import threading
import time
from datetime import datetime
from typing import Dict, List

class SafeDiscoveryProtocol:
    """Safe discovery protocol"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.discovered_agents = []
        self.is_running = False
    
    def start(self):
        """Start discovery"""
        self.is_running = True
        # Simulate discovering other agents
        known_agents = ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E', 'Agent_F']
        for agent in known_agents:
            if agent != self.agent_name:
                if agent not in [d['name'] for d in self.discovered_agents]:
                    self.discovered_agents.append({
                        'name': agent,
                        'discovered_at': datetime.now().isoformat(),
                        'status': 'active'
                    })
        return True
    
    def get_discovered_agents(self) -> List[Dict]:
        """Get discovered agents"""
        return self.discovered_agents


_discovery_registry = {}

def get_discovery(agent_name: str):
    """Get or create discovery instance"""
    if agent_name not in _discovery_registry:
        _discovery_registry[agent_name] = SafeDiscoveryProtocol(agent_name)
    return _discovery_registry[agent_name]
