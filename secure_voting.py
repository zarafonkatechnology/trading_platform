"""
Secure Voting System with Signature Verification
"""

import json
from datetime import datetime
from collections import defaultdict
from security import AgentSignature, audit_logger, agent_identity

class SecureVotingSystem:
    """Secure multi-agent voting with verification"""
    
    def __init__(self):
        self.votes = []
        self.verified_votes = []
        self.rejected_votes = []
        
    def submit_vote(self, agent_name, vote_package):
        """Submit a signed vote for verification"""
        vote_data = vote_package.get('vote_data', {})
        signature = vote_package.get('signature', {})
        public_key_pem = signature.get('public_key', '')
        signature_b64 = signature.get('signature', '')
        
        # Verify signature
        is_valid = AgentSignature.verify_signature(
            vote_data, signature_b64, public_key_pem
        )
        
        if is_valid:
            self.verified_votes.append({
                'vote': vote_data,
                'verification': 'PASSED',
                'verified_at': datetime.now().isoformat()
            })
            
            # Audit the verified vote
            audit_logger.log_action(
                agent_name=agent_name,
                action='VOTE_VERIFIED',
                details={'vote': vote_data.get('vote'), 'confidence': vote_data.get('confidence')}
            )
            
            return {'verified': True, 'vote': vote_data}
        else:
            self.rejected_votes.append({
                'vote': vote_data,
                'verification': 'FAILED',
                'reason': 'Invalid signature',
                'rejected_at': datetime.now().isoformat()
            })
            
            audit_logger.log_action(
                agent_name=agent_name,
                action='VOTE_REJECTED',
                details={'reason': 'Invalid signature'}
            )
            
            return {'verified': False, 'reason': 'Invalid signature'}
    
    def calculate_secure_consensus(self):
        """Calculate consensus only from verified votes"""
        if not self.verified_votes:
            return {'consensus': 'HOLD', 'confidence': 0, 'message': 'No verified votes'}
        
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0
        total_confidence = 0
        
        for vote in self.verified_votes:
            vote_action = vote['vote'].get('vote', 'HOLD')
            confidence = vote['vote'].get('confidence', 50)
            
            if vote_action == 'BUY':
                buy_votes += 1
                total_confidence += confidence
            elif vote_action == 'SELL':
                sell_votes += 1
                total_confidence += confidence
            else:
                hold_votes += 1
        
        total_votes = len(self.verified_votes)
        
        if buy_votes > sell_votes and buy_votes > hold_votes:
            consensus = 'BUY'
            confidence = (buy_votes / total_votes) * 100
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            consensus = 'SELL'
            confidence = (sell_votes / total_votes) * 100
        else:
            consensus = 'HOLD'
            confidence = (hold_votes / total_votes) * 100
        
        return {
            'consensus': consensus,
            'confidence': round(confidence, 2),
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'hold_votes': hold_votes,
            'total_verified_votes': total_votes,
            'total_rejected_votes': len(self.rejected_votes),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_audit_report(self):
        """Generate security audit report"""
        return {
            'total_votes_submitted': len(self.votes) + len(self.verified_votes) + len(self.rejected_votes),
            'verified_votes': len(self.verified_votes),
            'rejected_votes': len(self.rejected_votes),
            'verification_rate': (len(self.verified_votes) / max(1, len(self.verified_votes) + len(self.rejected_votes))) * 100,
            'recent_rejections': self.rejected_votes[-5:],
            'audit_integrity': audit_logger.verify_audit_trail()
        }
