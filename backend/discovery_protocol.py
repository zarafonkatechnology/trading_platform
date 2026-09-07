"""
Agent Discovery Protocol with Knowledge Verification
"""

import hashlib
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from backend.knowledge_verification import get_verification_system

class VerifiedDiscoveryProtocol:
    """Discovery protocol with 5-layer verification"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.discovered_agents = []
        self.knowledge_cache = {}
        self.verification = get_verification_system()
        self.is_running = False
    
    def start(self):
        """Start discovery"""
        self.is_running = True
        self._discover_agents()
        return True
    
    def _discover_agents(self):
        """Discover other agents with verification"""
        known_agents = ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E', 'Agent_F', 'Agent_G', 'Agent_H']
        
        for agent in known_agents:
            if agent != self.agent_name:
                # Create signature for verification
                timestamp = datetime.now().isoformat()
                signature = hashlib.sha256(f"{agent}{timestamp}secret".encode()).hexdigest()[:32]
                
                # Verify source before adding
                is_valid, msg = self.verification.verify_source(agent, signature, timestamp)
                
                if is_valid:
                    if agent not in [d['name'] for d in self.discovered_agents]:
                        self.discovered_agents.append({
                            'name': agent,
                            'discovered_at': timestamp,
                            'status': 'verified',
                            'reputation': self.verification.get_reputation(agent),
                            'signature': signature
                        })
                        print(f"🔍 {self.agent_name} discovered verified agent: {agent}")
    
    def share_verified_knowledge(self, target_agent: str, knowledge: Dict) -> Dict:
        """Share knowledge with verification"""
        # Create signature
        timestamp = datetime.now().isoformat()
        signature = hashlib.sha256(f"{self.agent_name}{knowledge.get('topic', '')}{timestamp}secret".encode()).hexdigest()[:32]
        
        # Verify knowledge before sharing
        verification_result = self.verification.verify_knowledge(
            knowledge, self.agent_name, signature, timestamp
        )
        
        if verification_result['verified']:
            return {
                'success': True,
                'knowledge': knowledge,
                'verification': verification_result,
                'message': f"Knowledge verified with {verification_result['final_score']*100:.0f}% confidence"
            }
        else:
            return {
                'success': False,
                'error': f"Knowledge failed verification: {verification_result['layers_failed']}",
                'verification': verification_result
            }
    
    def receive_verified_knowledge(self, from_agent: str, knowledge: Dict, signature: str, timestamp: str) -> Dict:
        """Receive and verify knowledge from another agent"""
        verification_result = self.verification.verify_knowledge(
            knowledge, from_agent, signature, timestamp
        )
        
        if verification_result['verified']:
            # Store verified knowledge
            topic = knowledge.get('topic', 'unknown')
            self.knowledge_cache[topic] = {
                'knowledge': knowledge,
                'source': from_agent,
                'verified_at': datetime.now().isoformat(),
                'verification_score': verification_result['final_score']
            }
            print(f"✅ {self.agent_name} received VERIFIED knowledge from {from_agent}")
            return {'success': True, 'verification': verification_result}
        else:
            print(f"⚠️ {self.agent_name} REJECTED knowledge from {from_agent} - verification failed")
            return {'success': False, 'verification': verification_result}
    
    def get_discovered_agents(self) -> List[Dict]:
        """Get discovered agents with their reputation"""
        return self.discovered_agents
    
    def get_verification_summary(self) -> Dict:
        """Get verification summary"""
        return self.verification.get_verification_summary()


_discovery_registry = {}

def get_discovery(agent_name: str):
    """Get or create discovery instance"""
    if agent_name not in _discovery_registry:
        _discovery_registry[agent_name] = VerifiedDiscoveryProtocol(agent_name)
    return _discovery_registry[agent_name]
