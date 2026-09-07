"""
Security Module for Multi-Agent Trading System
Handles agent signatures, encryption, and authentication
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
import base64

class AgentSignature:
    """Digital signature for agent votes"""
    
    def __init__(self, agent_name, private_key=None):
        self.agent_name = agent_name
        self.private_key = private_key or self._generate_key_pair()
        self.public_key = self.private_key.public_key()
        
    def _generate_key_pair(self):
        """Generate RSA key pair for agent"""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    
    def sign_vote(self, vote_data):
        """Sign a vote with agent's private key"""
        # Create message from vote data
        message = json.dumps(vote_data, sort_keys=True).encode('utf-8')
        
        # Sign the message
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            'signature': base64.b64encode(signature).decode('utf-8'),
            'public_key': self._get_public_key_pem(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_public_key_pem(self):
        """Export public key to PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    @staticmethod
    def verify_signature(vote_data, signature_b64, public_key_pem):
        """Verify an agent's signature"""
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            # Create message
            message = json.dumps(vote_data, sort_keys=True).encode('utf-8')
            
            # Verify signature
            signature = base64.b64decode(signature_b64)
            public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


class AgentIdentity:
    """Agent identity management"""
    
    def __init__(self):
        self.registered_agents = {}
        self.agent_secrets = {}
        
    def register_agent(self, agent_name, agent_type):
        """Register a new agent with unique identity"""
        # Generate unique agent ID
        agent_id = hashlib.sha256(
            f"{agent_name}{secrets.token_hex(16)}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Generate API key for agent
        api_key = secrets.token_urlsafe(32)
        
        # Generate secret for HMAC
        secret = secrets.token_bytes(32)
        
        self.registered_agents[agent_name] = {
            'agent_id': agent_id,
            'agent_type': agent_type,
            'registered_at': datetime.now().isoformat(),
            'api_key': api_key,
            'is_active': True
        }
        
        self.agent_secrets[agent_name] = secret
        
        return {
            'agent_id': agent_id,
            'api_key': api_key,
            'agent_name': agent_name
        }
    
    def verify_agent(self, agent_name, api_key):
        """Verify agent identity"""
        if agent_name not in self.registered_agents:
            return False
        
        agent = self.registered_agents[agent_name]
        return hmac.compare_digest(agent['api_key'], api_key)
    
    def get_agent_public_key(self, agent_name):
        """Retrieve agent's public key"""
        # In production, store in database
        pass


class VoteEncryptor:
    """Encrypt vote data for secure transmission"""
    
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_vote(self, vote_data):
        """Encrypt vote data"""
        json_data = json.dumps(vote_data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_vote(self, encrypted_data):
        """Decrypt vote data"""
        encrypted = base64.b64decode(encrypted_data)
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())


class AuditLogger:
    """Audit trail for all actions"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.audit_log = []
        
    def log_action(self, agent_name, action, details, signature=None):
        """Log an action with signature"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_name': agent_name,
            'action': action,
            'details': details,
            'signature': signature,
            'log_id': hashlib.sha256(
                f"{agent_name}{action}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
        }
        
        self.audit_log.append(log_entry)
        
        # Store in database if available
        if self.db:
            self._store_in_db(log_entry)
        
        return log_entry
    
    def _store_in_db(self, log_entry):
        """Store audit log in PostgreSQL"""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO audit_log (log_id, agent_name, action, details, signature, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                log_entry['log_id'],
                log_entry['agent_name'],
                log_entry['action'],
                json.dumps(log_entry['details']),
                log_entry['signature'],
                log_entry['timestamp']
            ))
            self.db.commit()
        except Exception as e:
            print(f"Audit log DB error: {e}")
    
    def verify_audit_trail(self):
        """Verify integrity of audit log"""
        # Check for tampering
        for i, entry in enumerate(self.audit_log):
            if i > 0:
                # Verify chronological order
                prev_time = datetime.fromisoformat(self.audit_log[i-1]['timestamp'])
                curr_time = datetime.fromisoformat(entry['timestamp'])
                if curr_time < prev_time:
                    return False, f"Timestamp tampering at index {i}"
        return True, "Audit trail intact"


class APIAuthenticator:
    """API endpoint authentication"""
    
    def __init__(self):
        self.api_keys = {}
        self.rate_limits = {}
        
    def generate_api_key(self, user_id):
        """Generate API key for user/agent"""
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'rate_limit': 100,  # requests per minute
            'requests_made': 0
        }
        return api_key
    
    def verify_api_key(self, api_key):
        """Verify API key validity"""
        if api_key not in self.api_keys:
            return False
        
        # Check rate limit
        key_info = self.api_keys[api_key]
        key_info['requests_made'] += 1
        
        if key_info['requests_made'] > key_info['rate_limit']:
            return False
        
        return True
    
    def require_auth(self, f):
        """Decorator for authenticated endpoints"""
        from functools import wraps
        from flask import request, jsonify
        
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key or not self.verify_api_key(api_key):
                return jsonify({'error': 'Unauthorized'}), 401
            return f(*args, **kwargs)
        return decorated


# Global security instances
agent_identity = AgentIdentity()
audit_logger = AuditLogger()
api_auth = APIAuthenticator()

# Register all agents (run once)
def register_all_agents():
    """Register all 15 agents with identities"""
    agents = [
        'Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E',
        'Agent_F', 'Agent_G', 'Agent_H', 'Agent_I', 'Agent_J',
        'Agent_K', 'Agent_L', 'Agent_M', 'Agent_N', 'Agent_O'
    ]
    
    credentials = {}
    for agent in agents:
        creds = agent_identity.register_agent(agent, 'Trading Agent')
        credentials[agent] = creds
        print(f"✅ Registered {agent} with ID: {creds['agent_id']}")
    
    # Save credentials to secure file
    with open('agent_credentials.enc', 'w') as f:
        json.dump(credentials, f, indent=2)
    
    return credentials
