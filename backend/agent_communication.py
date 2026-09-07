"""
Complete Agent Communication Flow
Discovery → Verification → Knowledge Request → Knowledge Share
"""

import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional
from backend.complete_discovery import get_discovery
from backend.complete_verification import get_verification

class AgentCommunication:
    """Complete communication flow for agents"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.discovery = get_discovery(agent_name)
        self.verification = get_verification()
        self.knowledge_exchange = []
        self.communication_log = []
        
        print(f"\n📡 Initializing Communication for {agent_name}")
        print("="*50)
        # ============================================
    # ADD THIS METHOD HERE
    # ============================================
    
    def _log_communication(self, comm_type: str, target: str, message: str, response_time: int = 0):
        """Log communication to database"""
        try:
            from backend.utils.db_helper import get_db_connection
            conn = get_db_connection()
            if conn is None:
                return
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO communication_log (agent_name, communication_type, target_agent, message, response_time_ms)
                VALUES (%s, %s, %s, %s, %s)
            """, (self.agent_name, comm_type, target, message, response_time))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error logging communication: {e}")
            
    def discover_agents(self) -> List[Dict]:
        """Step 1: Discover other agents"""
        print(f"\n🔍 {self.agent_name} discovering agents...")
        agents = self.discovery.discover_all()
        
        for agent in agents:
            self.communication_log.append({
                'type': 'DISCOVERY',
                'agent': agent.get('agent_name'),
                'method': agent.get('method'),
                'timestamp': datetime.now().isoformat()
            })
        
        return agents
    
    def request_knowledge(self, target_agent: str, topic: str) -> Optional[Dict]:
        """Step 2: Request knowledge from verified agent"""
        
        # First verify the agent
        if not self._verify_agent(target_agent):
            print(f"⚠️ Cannot request from {target_agent} - verification failed")
            return None
        
        # Create request with signature
        timestamp = datetime.now().isoformat()
        signature = hashlib.sha256(f"{self.agent_name}{topic}{timestamp}secret".encode()).hexdigest()[:32]
        
        request = {
            'from_agent': self.agent_name,
            'topic': topic,
            'timestamp': timestamp,
            'signature': signature
        }
        
        # Simulate knowledge response
        knowledge = self._get_knowledge_response(target_agent, topic)
        
        if knowledge:
            # Verify the received knowledge
            verification = self.verification.verify_knowledge(
                knowledge, target_agent, knowledge.get('signature', ''), knowledge.get('timestamp', '')
            )
            
            if verification['verified']:
                print(f"✅ Received VERIFIED knowledge from {target_agent}")
                self.knowledge_exchange.append({
                    'from': target_agent,
                    'to': self.agent_name,
                    'topic': topic,
                    'knowledge': knowledge,
                    'verification_score': verification['overall_score'],
                    'timestamp': datetime.now().isoformat()
                })
                return knowledge
            else:
                print(f"⚠️ Knowledge from {target_agent} FAILED verification")
                return None
        
        return None
    
    def share_knowledge(self, target_agent: str, knowledge: Dict) -> bool:
        """Step 3: Share verified knowledge with another agent"""
        
        # Verify the knowledge before sharing
        timestamp = datetime.now().isoformat()
        signature = hashlib.sha256(f"{self.agent_name}{knowledge.get('topic', '')}{timestamp}secret".encode()).hexdigest()[:32]
        
        verification = self.verification.verify_knowledge(knowledge, self.agent_name, signature, timestamp)
        
        if not verification['verified']:
            print(f"⚠️ Cannot share - knowledge failed verification (score: {verification['overall_score']:.2f})")
            return False
        
        # Add signature to knowledge
        knowledge['signature'] = signature
        knowledge['timestamp'] = timestamp
        knowledge['source'] = self.agent_name
        
        # Simulate sharing
        print(f"📤 Sharing VERIFIED knowledge with {target_agent}")
        print(f"   Topic: {knowledge.get('topic')}")
        print(f"   Verification Score: {verification['overall_score']*100:.0f}%")
        
        self.knowledge_exchange.append({
            'from': self.agent_name,
            'to': target_agent,
            'topic': knowledge.get('topic'),
            'knowledge': knowledge,
            'verification_score': verification['overall_score'],
            'timestamp': datetime.now().isoformat()
        })
        
        return True
    
    def _verify_agent(self, agent_name: str) -> bool:
        """Verify agent identity"""
        # Check if agent was discovered
        discovered = self.discovery.discovered_agents
        
        for agent in discovered.values():
            if agent.get('agent_name') == agent_name:
                return True
        
        return False
    
    def _get_knowledge_response(self, agent: str, topic: str) -> Optional[Dict]:
        """Simulate knowledge response (in production, would be actual API call)"""
        
        knowledge_base = {
            'RSI Divergence': {
                'topic': 'RSI Divergence',
                'content': 'When price makes lower low but RSI makes higher low, it indicates bullish divergence and potential reversal.',
                'confidence': 0.85,
                'source': agent
            },
            'MACD Crossover': {
                'topic': 'MACD Crossover',
                'content': 'When MACD line crosses above signal line, it generates a bullish signal.',
                'confidence': 0.75,
                'source': agent
            },
            'Fibonacci Levels': {
                'topic': 'Fibonacci Levels',
                'content': 'Key Fibonacci retracement levels are 0.382, 0.5, 0.618, and 0.786.',
                'confidence': 0.9,
                'source': agent
            }
        }
        
        if topic in knowledge_base:
            knowledge = knowledge_base[topic]
            timestamp = datetime.now().isoformat()
            knowledge['signature'] = hashlib.sha256(f"{agent}{topic}{timestamp}secret".encode()).hexdigest()[:32]
            knowledge['timestamp'] = timestamp
            return knowledge
        
        return None
    
    def get_communication_summary(self) -> Dict:
        """Get communication summary"""
        return {
            'agent': self.agent_name,
            'discovered_agents': len(self.discovery.discovered_agents),
            'knowledge_exchanges': len(self.knowledge_exchange),
            'verification_stats': self.verification.get_stats()
        }


def demonstrate_communication():
    """Demonstrate complete agent communication flow"""
    
    print("\n" + "="*80)
    print("🤝 AGENT COMMUNICATION FLOW DEMONSTRATION")
    print("="*80)
    
    # Create communication instances for two agents
    agent_a = AgentCommunication("Agent_A")
    agent_b = AgentCommunication("Agent_B")
    
    # Step 1: Discover agents
    print("\n📡 STEP 1: DISCOVERY")
    print("-"*40)
    agent_a.discover_agents()
    agent_b.discover_agents()
    
    # Step 2: Request knowledge
    print("\n📡 STEP 2: KNOWLEDGE REQUEST")
    print("-"*40)
    knowledge = agent_a.request_knowledge("Agent_B", "RSI Divergence")
    
    if knowledge:
        print(f"\n✅ Received knowledge: {knowledge['topic']}")
        print(f"   Content: {knowledge['content'][:100]}...")
        print(f"   Confidence: {knowledge['confidence']*100:.0f}%")
    
    # Step 3: Share knowledge
    print("\n📡 STEP 3: KNOWLEDGE SHARING")
    print("-"*40)
    
    test_knowledge = {
        'topic': 'Fibonacci Levels',
        'content': 'The 61.8% retracement level is the most important Fibonacci level for reversals.',
        'confidence': 0.88
    }
    
    agent_a.share_knowledge("Agent_B", test_knowledge)
    
    # Summary
    print("\n📡 COMMUNICATION SUMMARY")
    print("-"*40)
    print(f"Agent_A: {agent_a.get_communication_summary()}")
    print(f"Agent_B: {agent_b.get_communication_summary()}")
    
    return agent_a, agent_b

if __name__ == "__main__":
    demonstrate_communication()
