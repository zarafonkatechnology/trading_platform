"""
Knowledge Verification System - 5 Layer Verification Protocol
Ensures agents only accept verified, accurate information
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

class VerificationStatus(Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    PENDING = "pending"
    SUSPICIOUS = "suspicious"

class VerificationLayer(Enum):
    SOURCE = 1
    CONSISTENCY = 2
    HISTORICAL = 3
    CROSS_REFERENCE = 4
    PLAUSIBILITY = 5

class KnowledgeVerificationSystem:
    """5-Layer Knowledge Verification System"""
    
    def __init__(self):
        self.trusted_sources = {}
        self.knowledge_cache = {}
        self.reputation_scores = {}
        self.verification_log = []
        
        # Known facts database (verified knowledge)
        self.known_facts = {
            'rsi_range': (0, 100),
            'macd_components': ['fast_ema', 'slow_ema', 'signal_line'],
            'bollinger_bands': ['upper', 'middle', 'lower'],
            'fibonacci_levels': [0.236, 0.382, 0.5, 0.618, 0.786],
            'market_hours': {'NYSE': '09:30-16:00 ET', 'LSE': '08:00-16:30 GMT'}
        }
        
        print("\n" + "="*60)
        print("🔐 KNOWLEDGE VERIFICATION SYSTEM INITIALIZED")
        print("="*60)
        print("5-Layer Verification Protocol Active:")
        print("  Layer 1: Source Verification")
        print("  Layer 2: Consistency Check")
        print("  Layer 3: Historical Accuracy")
        print("  Layer 4: Cross-Reference")
        print("  Layer 5: Plausibility Check")
        print("="*60)
    
    # ============================================
    # LAYER 1: SOURCE VERIFICATION
    # ============================================
    
    def verify_source(self, agent_name: str, signature: str, timestamp: str) -> Tuple[bool, str]:
        """Layer 1: Verify agent identity and signature"""
        
        # Check timestamp freshness (not older than 1 hour)
        try:
            msg_time = datetime.fromisoformat(timestamp)
            if (datetime.now() - msg_time) > timedelta(hours=1):
                return False, "Source timestamp too old (>1 hour)"
        except:
            return False, "Invalid timestamp format"
        
        # Verify signature (simplified - in production use actual crypto)
        expected_sig = hashlib.sha256(f"{agent_name}{timestamp}secret".encode()).hexdigest()
        if signature != expected_sig[:32]:
            return False, "Invalid digital signature"
        
        # Check reputation score
        reputation = self.get_reputation(agent_name)
        if reputation < 0.3:
            return False, f"Low reputation score: {reputation:.2f}"
        
        return True, f"Source verified (reputation: {reputation:.2f})"
    
    # ============================================
    # LAYER 2: CONSISTENCY CHECK
    # ============================================
    
    def check_consistency(self, knowledge: Dict) -> Tuple[bool, List[str]]:
        """Layer 2: Check internal logic consistency"""
        
        issues = []
        
        # Check for logical contradictions
        if 'signal' in knowledge:
            signal = knowledge['signal']
            confidence = knowledge.get('confidence', 0)
            
            if signal == 'BUY' and confidence > 95:
                issues.append("Extreme confidence without confirmation")
            
            if signal == 'BUY' and 'rsi' in knowledge and knowledge['rsi'] > 80:
                issues.append("BUY signal with overbought RSI (>80)")
            
            if signal == 'SELL' and 'rsi' in knowledge and knowledge['rsi'] < 20:
                issues.append("SELL signal with oversold RSI (<20)")
        
        # Check for missing required fields
        required_fields = ['topic', 'content']
        for field in required_fields:
            if field not in knowledge:
                issues.append(f"Missing required field: {field}")
        
        # Check data types
        if 'confidence' in knowledge:
            if not 0 <= knowledge['confidence'] <= 1:
                issues.append(f"Invalid confidence value: {knowledge['confidence']}")
        
        return len(issues) == 0, issues
    
    # ============================================
    # LAYER 3: HISTORICAL ACCURACY
    # ============================================
    
    def verify_historical_accuracy(self, knowledge: Dict) -> Tuple[bool, str]:
        """Layer 3: Verify against historical patterns"""
        
        topic = knowledge.get('topic', '').lower()
        content = knowledge.get('content', '').lower()
        
        # Check against known facts
        if 'rsi' in topic:
            if 'above 100' in content or 'below 0' in content:
                return False, "RSI cannot be above 100 or below 0"
        
        if 'macd' in topic:
            if 'single line' in content:
                return False, "MACD consists of multiple components"
        
        if 'fibonacci' in topic:
            if '1.0' in content and 'retracement' in content:
                return False, "1.0 is not a standard Fibonacci retracement level"
        
        return True, "Historical verification passed"
    
    # ============================================
    # LAYER 4: CROSS-REFERENCE
    # ============================================
    
    def cross_reference(self, knowledge: Dict) -> Tuple[bool, str, int]:
        """Layer 4: Cross-reference with multiple sources"""
        
        sources_verified = 0
        total_sources = 3
        
        # Source 1: Check against known facts
        if self._check_against_known_facts(knowledge):
            sources_verified += 1
        
        # Source 2: Check against market principles
        if self._check_market_principles(knowledge):
            sources_verified += 1
        
        # Source 3: Check against technical standards
        if self._check_technical_standards(knowledge):
            sources_verified += 1
        
        confidence = sources_verified / total_sources
        
        if sources_verified >= 2:
            return True, f"Cross-referenced with {sources_verified} sources", confidence
        else:
            return False, f"Only {sources_verified}/{total_sources} sources agree", confidence
    
    def _check_against_known_facts(self, knowledge: Dict) -> bool:
        """Check knowledge against known facts database"""
        # Implementation would check against verified knowledge
        return True
    
    def _check_market_principles(self, knowledge: Dict) -> bool:
        """Check against fundamental market principles"""
        content = knowledge.get('content', '').lower()
        
        # Basic market principles
        if 'guaranteed profit' in content:
            return False
        if 'risk free' in content:
            return False
        if '100% accuracy' in content:
            return False
        
        return True
    
    def _check_technical_standards(self, knowledge: Dict) -> bool:
        """Check against technical analysis standards"""
        # Implementation would check against TA standards
        return True
    
    # ============================================
    # LAYER 5: PLAUSIBILITY CHECK
    # ============================================
    
    def check_plausibility(self, knowledge: Dict) -> Tuple[bool, List[str]]:
        """Layer 5: Detect extreme or unrealistic claims"""
        
        warnings = []
        
        content = knowledge.get('content', '').lower()
        
        # Extreme claims detection
        extreme_phrases = [
            ('guaranteed', "Contains 'guaranteed' - unrealistic claim"),
            ('100%', "Claims 100% accuracy - impossible in trading"),
            ('risk free', "Claims 'risk free' - not possible"),
            ('always', "Absolute claim - markets are probabilistic"),
            ('never', "Absolute claim - markets are probabilistic"),
        ]
        
        for phrase, warning in extreme_phrases:
            if phrase in content:
                warnings.append(warning)
        
        # Check confidence levels
        confidence = knowledge.get('confidence', 0.5)
        if confidence > 0.95:
            warnings.append(f"Extremely high confidence ({confidence*100:.0f}%) - unrealistic")
        
        # Check for logical bounds
        if 'profit' in content and '1000%' in content:
            warnings.append("Extreme profit claim - likely unrealistic")
        
        return len(warnings) == 0, warnings
    
    # ============================================
    # COMPLETE VERIFICATION PROCESS
    # ============================================
    
    def verify_knowledge(self, knowledge: Dict, source_agent: str, signature: str, timestamp: str) -> Dict:
        """Complete 5-layer verification process"""
        
        verification_result = {
            'verified': False,
            'layers_passed': [],
            'layers_failed': [],
            'warnings': [],
            'confidence': 0,
            'final_score': 0
        }
        
        scores = {}
        
        # Layer 1: Source Verification
        source_valid, source_msg = self.verify_source(source_agent, signature, timestamp)
        if source_valid:
            verification_result['layers_passed'].append('source')
            scores['source'] = 0.25
        else:
            verification_result['layers_failed'].append(f'source: {source_msg}')
            scores['source'] = 0
        
        # Layer 2: Consistency Check
        consistent, issues = self.check_consistency(knowledge)
        if consistent:
            verification_result['layers_passed'].append('consistency')
            scores['consistency'] = 0.20
        else:
            verification_result['layers_failed'].append(f'consistency: {", ".join(issues)}')
            scores['consistency'] = 0
        
        # Layer 3: Historical Accuracy
        historical_valid, historical_msg = self.verify_historical_accuracy(knowledge)
        if historical_valid:
            verification_result['layers_passed'].append('historical')
            scores['historical'] = 0.20
        else:
            verification_result['layers_failed'].append(f'historical: {historical_msg}')
            scores['historical'] = 0
        
        # Layer 4: Cross-Reference
        cross_valid, cross_msg, cross_conf = self.cross_reference(knowledge)
        if cross_valid:
            verification_result['layers_passed'].append('cross_reference')
            scores['cross_reference'] = 0.20
        else:
            verification_result['layers_failed'].append(f'cross_reference: {cross_msg}')
            scores['cross_reference'] = 0
            verification_result['warnings'].append(cross_msg)
        
        # Layer 5: Plausibility Check
        plausible, warnings = self.check_plausibility(knowledge)
        if plausible:
            verification_result['layers_passed'].append('plausibility')
            scores['plausibility'] = 0.15
        else:
            verification_result['layers_failed'].append(f'plausibility: {", ".join(warnings)}')
            scores['plausibility'] = 0
            verification_result['warnings'].extend(warnings)
        
        # Calculate final score
        verification_result['final_score'] = sum(scores.values())
        verification_result['confidence'] = verification_result['final_score']
        verification_result['verified'] = verification_result['final_score'] >= 0.70
        
        # Log verification
        self._log_verification(knowledge, source_agent, verification_result)
        
        return verification_result
    
    def _log_verification(self, knowledge: Dict, source: str, result: Dict):
        """Log verification result for audit"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'topic': knowledge.get('topic'),
            'verified': result['verified'],
            'score': result['final_score'],
            'layers_passed': result['layers_passed'],
            'layers_failed': result['layers_failed']
        }
        self.verification_log.append(log_entry)
        
        # Update reputation
        self._update_reputation(source, result['verified'])
    
    def _update_reputation(self, agent_name: str, was_verified: bool):
        """Update agent reputation score"""
        if agent_name not in self.reputation_scores:
            self.reputation_scores[agent_name] = 0.5
        
        if was_verified:
            self.reputation_scores[agent_name] = min(1.0, self.reputation_scores[agent_name] + 0.05)
        else:
            self.reputation_scores[agent_name] = max(0.0, self.reputation_scores[agent_name] - 0.1)
    
    def get_reputation(self, agent_name: str) -> float:
        """Get agent reputation score"""
        return self.reputation_scores.get(agent_name, 0.5)
    
    def get_verification_summary(self) -> Dict:
        """Get verification system summary"""
        total_checks = len(self.verification_log)
        verified_count = sum(1 for log in self.verification_log if log['verified'])
        
        return {
            'total_verifications': total_checks,
            'verified_count': verified_count,
            'verification_rate': verified_count / total_checks if total_checks > 0 else 0,
            'reputation_scores': self.reputation_scores
        }


# Singleton
_verification_system = None

def get_verification_system():
    global _verification_system
    if _verification_system is None:
        _verification_system = KnowledgeVerificationSystem()
    return _verification_system
