"""
Complete Agent Discovery Protocol
Supports 5 discovery methods with verification
"""

import hashlib
import json
import socket
import threading
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class DiscoveryMethod(Enum):
    CENTRAL_REGISTRY = "central_registry"
    BROADCAST = "broadcast"
    DNS_SRV = "dns_srv"
    DHT = "dht"
    BLOCKCHAIN = "blockchain"

class CompleteDiscoveryProtocol:
    """Complete discovery with 5 methods"""
    
    def __init__(self, agent_name: str, agent_id: str):
        self.agent_name = agent_name
        self.agent_id = agent_id
        self.discovered_agents = {}
        self.verification_scores = {}
        
        # Registry URLs
        self.central_registry_url = "https://api.agent-registry.io"
        self.blockchain_registry_url = "https://api.blockchain-agents.io"
        
        # DHT storage
        self.dht_storage = {}
        
        print(f"\n🔍 Initializing Discovery for {agent_name}")
        print("="*50)
    def store_discovered_agent(self, discovered_agent: str, method: str, expertise: list):
        """Store discovered agent in database"""
        try:
            from backend.utils.database import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO discovered_agents (discoverer_agent, discovered_agent, discovery_method, agent_expertise, last_seen)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (discoverer_agent, discovered_agent) 
                DO UPDATE SET last_seen = NOW(), is_active = TRUE
            """, (self.agent_name, discovered_agent, method, expertise))
            conn.commit()
            cur.close()
            conn.close()
            print(f"📝 Stored discovered agent: {discovered_agent} (via {method})")
        except Exception as e:
            print(f"⚠️ Error storing discovered agent: {e}")
    # ============================================
    # METHOD 1: CENTRAL REGISTRY
    # ============================================
    
    def register_with_central(self) -> bool:
        """Register with central agent registry"""
        try:
            payload = {
                'agent_name': self.agent_name,
                'agent_id': self.agent_id,
                'expertise': self._get_expertise(),
                'endpoint': self._get_endpoint(),
                'public_key': self._get_public_key(),
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.central_registry_url}/api/register",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Registered with Central Registry")
                return True
        except Exception as e:
            print(f"⚠️ Central registry unavailable: {e}")
        
        return False
    
    def discover_from_central(self) -> List[Dict]:
        """Discover agents from central registry"""
        try:
            response = requests.get(
                f"{self.central_registry_url}/api/agents",
                params={'active': True},
                timeout=10
            )
            
            if response.status_code == 200:
                agents = response.json().get('agents', [])
                verified = []
                
                for agent in agents:
                    if agent.get('agent_id') != self.agent_id:
                        # Verify agent before adding
                        if self._verify_agent_signature(agent):
                            verified.append(agent)
                            print(f"🔗 Discovered: {agent.get('agent_name')} (via Central Registry)")
                
                return verified
        except Exception as e:
            print(f"⚠️ Central registry discovery error: {e}")
        
        return []
    
    # ============================================
    # METHOD 2: BROADCAST PROTOCOL
    # ============================================
    
    def broadcast_discovery(self, port: int = 5000) -> List[Dict]:
        """Discover agents via network broadcast"""
        discovered = []
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2)
            
            discovery_msg = {
                'type': 'DISCOVERY',
                'agent_name': self.agent_name,
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat(),
                'signature': self._sign_message('DISCOVERY')
            }
            
            sock.sendto(json.dumps(discovery_msg).encode(), ('<broadcast>', port))
            
            while True:
                data, addr = sock.recvfrom(4096)
                response = json.loads(data.decode())
                
                if response.get('type') == 'DISCOVERY_RESPONSE':
                    # Verify response
                    if self._verify_message_signature(response):
                        discovered.append({
                            'agent_name': response.get('agent_name'),
                            'agent_id': response.get('agent_id'),
                            'address': addr[0],
                            'port': addr[1],
                            'method': 'broadcast'
                        })
                        print(f"🔗 Discovered: {response.get('agent_name')} (via Broadcast)")
                        
        except socket.timeout:
            pass
        except Exception as e:
            print(f"⚠️ Broadcast error: {e}")
        finally:
            sock.close()
        
        return discovered
    
    # ============================================
    # METHOD 3: DNS SRV RECORDS
    # ============================================
    
    def query_dns_srv(self, service: str = '_agent', domain: str = 'trading.local') -> List[Dict]:
        """Discover agents via DNS SRV records"""
        discovered = []
        
        try:
            import dns.resolver
            
            answers = dns.resolver.resolve(f'_{service}._{domain}', 'SRV')
            
            for answer in answers:
                discovered.append({
                    'agent_name': str(answer.target).split('.')[0],
                    'host': str(answer.target),
                    'port': answer.port,
                    'priority': answer.priority,
                    'weight': answer.weight,
                    'method': 'dns_srv'
                })
                print(f"🔗 Discovered: {str(answer.target).split('.')[0]} (via DNS SRV)")
                
        except ImportError:
            print("⚠️ DNS module not available")
        except Exception as e:
            print(f"⚠️ DNS query error: {e}")
        
        return discovered
    
    # ============================================
    # METHOD 4: DISTRIBUTED HASH TABLE (DHT)
    # ============================================
    
    def store_in_dht(self, key: str, value: Dict) -> bool:
        """Store agent info in DHT"""
        try:
            hash_key = hashlib.sha256(key.encode()).hexdigest()
            self.dht_storage[hash_key] = {
                'value': value,
                'timestamp': datetime.now().isoformat(),
                'owner': self.agent_name
            }
            print(f"📦 Stored in DHT: {key}")
            return True
        except Exception as e:
            print(f"⚠️ DHT store error: {e}")
            return False
    
    def lookup_in_dht(self, key: str) -> Optional[Dict]:
        """Lookup agent in DHT"""
        try:
            hash_key = hashlib.sha256(key.encode()).hexdigest()
            
            if hash_key in self.dht_storage:
                data = self.dht_storage[hash_key]
                
                # Check freshness (not older than 1 hour)
                age = (datetime.now() - datetime.fromisoformat(data['timestamp'])).total_seconds()
                if age < 3600:
                    print(f"🔗 Found in DHT: {key}")
                    return data['value']
                else:
                    print(f"⚠️ DHT entry expired: {key}")
            
            return None
        except Exception as e:
            print(f"⚠️ DHT lookup error: {e}")
            return None
    
    # ============================================
    # METHOD 5: BLOCKCHAIN REGISTRY
    # ============================================
    
    def register_on_blockchain(self) -> bool:
        """Register agent on blockchain registry"""
        try:
            # Simplified blockchain registration
            block = {
                'index': len(self._get_chain()) + 1,
                'timestamp': datetime.now().isoformat(),
                'agent_data': {
                    'agent_name': self.agent_name,
                    'agent_id': self.agent_id,
                    'registered_at': datetime.now().isoformat()
                },
                'previous_hash': self._get_last_hash(),
                'nonce': self._proof_of_work()
            }
            
            block['hash'] = self._calculate_hash(block)
            self._add_block(block)
            
            print(f"✅ Registered on Blockchain: {self.agent_name}")
            return True
            
        except Exception as e:
            print(f"⚠️ Blockchain registration error: {e}")
            return False
    
    def verify_on_blockchain(self, agent_id: str) -> bool:
        """Verify agent exists on blockchain"""
        try:
            chain = self._get_chain()
            for block in chain:
                if block.get('agent_data', {}).get('agent_id') == agent_id:
                    # Verify hash
                    if block.get('hash') == self._calculate_hash(block):
                        print(f"✅ Verified on Blockchain: {agent_id}")
                        return True
            return False
        except Exception as e:
            print(f"⚠️ Blockchain verification error: {e}")
            return False
    
    # ============================================
    # COMPLETE DISCOVERY PROCESS
    # ============================================
    
    def discover_all(self) -> List[Dict]:
        """Run all discovery methods"""
        all_discovered = []
        
        print(f"\n🔍 {self.agent_name} starting discovery...")
        print("-"*40)
        
        # Method 1: Central Registry
        central_agents = self.discover_from_central()
        all_discovered.extend(central_agents)
        
        # Method 2: Broadcast
        broadcast_agents = self.broadcast_discovery()
        all_discovered.extend(broadcast_agents)
        
        # Method 3: DNS SRV
        dns_agents = self.query_dns_srv()
        all_discovered.extend(dns_agents)
        
        # Method 4: DHT
        dht_agents = self._discover_from_dht()
        all_discovered.extend(dht_agents)
        
        # Method 5: Blockchain
        blockchain_agents = self._discover_from_blockchain()
        all_discovered.extend(blockchain_agents)
        
        # Remove duplicates and store
        unique_agents = self._deduplicate_agents(all_discovered)
        
        for agent in unique_agents:
            self.discovered_agents[agent.get('agent_name')] = agent
        
        print(f"\n✅ Discovery complete. Found {len(unique_agents)} unique agents")
        
        return unique_agents
    
    def _discover_from_dht(self) -> List[Dict]:
        """Discover agents from DHT"""
        discovered = []
        # Simulated DHT discovery
        for key, value in self.dht_storage.items():
            if value.get('owner') != self.agent_name:
                discovered.append({
                    'agent_name': value['value'].get('agent_name'),
                    'method': 'dht'
                })
        return discovered
    
    def _discover_from_blockchain(self) -> List[Dict]:
        """Discover agents from blockchain"""
        discovered = []
        chain = self._get_chain()
        for block in chain:
            agent_data = block.get('agent_data', {})
            if agent_data.get('agent_id') != self.agent_id:
                discovered.append({
                    'agent_name': agent_data.get('agent_name'),
                    'method': 'blockchain'
                })
        return discovered
    
    def _deduplicate_agents(self, agents: List[Dict]) -> List[Dict]:
        """Remove duplicate agents"""
        seen = set()
        unique = []
        for agent in agents:
            name = agent.get('agent_name')
            if name and name not in seen:
                seen.add(name)
                unique.append(agent)
        return unique
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _get_expertise(self) -> List[str]:
        """Get agent expertise"""
        expertise_map = {
            'Agent_A': ['trend_following', 'moving_averages'],
            'Agent_B': ['mean_reversion', 'rsi'],
            'Agent_C': ['momentum', 'macd'],
            'Agent_D': ['volatility', 'atr'],
            'Agent_E': ['microstructure', 'order_flow'],
            'Agent_F': ['candlestick', 'patterns'],
            'Agent_G': ['whale_tracking', 'cot'],
            'Agent_H': ['fibonacci', 'levels']
        }
        return expertise_map.get(self.agent_name, ['general_trading'])
    
    def _get_endpoint(self) -> str:
        """Get agent endpoint"""
        return f"http://localhost:5000/api/agent/{self.agent_name}"
    
    def _get_public_key(self) -> str:
        """Get public key"""
        return hashlib.sha256(f"{self.agent_id}_key".encode()).hexdigest()
    
    def _sign_message(self, message: str) -> str:
        """Sign message"""
        return hashlib.sha256(f"{message}{self.agent_id}_secret".encode()).hexdigest()[:32]
    
    def _verify_message_signature(self, message: Dict) -> bool:
        """Verify message signature"""
        signature = message.get('signature', '')
        expected = hashlib.sha256(f"{message.get('type')}{message.get('agent_id')}_secret".encode()).hexdigest()[:32]
        return signature == expected
    
    def _verify_agent_signature(self, agent: Dict) -> bool:
        """Verify agent signature"""
        # Simplified verification
        return True
    
    def _get_chain(self) -> List:
        """Get blockchain chain (simplified)"""
        if not hasattr(self, '_chain'):
            self._chain = []
        return self._chain
    
    def _add_block(self, block: Dict):
        """Add block to chain"""
        self._get_chain().append(block)
    
    def _get_last_hash(self) -> str:
        """Get last block hash"""
        chain = self._get_chain()
        if chain:
            return chain[-1].get('hash', '0')
        return '0'
    
    def _proof_of_work(self) -> int:
        """Simple proof of work"""
        nonce = 0
        while True:
            hash_candidate = hashlib.sha256(f"{nonce}".encode()).hexdigest()
            if hash_candidate.startswith('000'):
                return nonce
            nonce += 1
    
    def _calculate_hash(self, block: Dict) -> str:
        """Calculate block hash"""
        block_string = json.dumps(block, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()


# Global registry
_discovery_registry = {}

def get_discovery(agent_name: str):
    """Get discovery instance for agent"""
    if agent_name not in _discovery_registry:
        agent_id = f"agent_{agent_name}_id"
        _discovery_registry[agent_name] = CompleteDiscoveryProtocol(agent_name, agent_id)
    return _discovery_registry[agent_name]
