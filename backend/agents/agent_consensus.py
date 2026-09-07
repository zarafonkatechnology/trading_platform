"""
Consensus Agent - Weighted Arbiter with Veto Logic
- Signal Uniformity (-1.0 to 1.0 scale)
- Weighting Matrix (Whale=0.5, Fibonacci=0.3, MA=0.2)
- Veto Logic (Danger overrides everything)
- State Memory (prevents wavering)
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

"""
Consensus System with Dark Pool Whale Veto Power
Zero-Error Protection against Bull Traps
"""

class WhaleConsensus:
    """
    Enhanced consensus that includes Dark Pool Whale Agent
    with VETO power over technical signals
    """
    
    @staticmethod
    def evaluate_with_whale(technical_consensus, whale_signal, market_context):
        """
        Evaluate trade with whale veto power
        
        RULES:
        1. If technical says BUY and whale says BUY → STRONG_BUY (100% confidence)
        2. If technical says BUY and whale says SELL → VETO (Bull Trap)
        3. If technical says SELL and whale says SELL → STRONG_SELL (100% confidence)
        4. If technical says SELL and whale says BUY → VETO (Bear Trap)
        5. If whale is neutral → Follow technical with 30% size reduction
        """
        
        tech_vote = technical_consensus.get('consensus', 'HOLD')
        tech_confidence = technical_consensus.get('confidence', 50)
        whale_vote = whale_signal.get('vote', 'HOLD')
        whale_confidence = whale_signal.get('confidence', 50)
        
        # RULE 2 & 4: Whale VETO Power
        if tech_vote == 'BUY' and whale_vote == 'SELL':
            return {
                'final_vote': 'HOLD',
                'confidence': 15,
                'reasoning': f"⛔ BULL TRAP AVOIDED: Technicals say BUY but Dark Pool whales are SELLING. VETO activated.",
                'position_multiplier': 0,
                'risk_level': 'CRITICAL',
                'rule_applied': 'Whale Veto - Bull Trap'
            }
        
        if tech_vote == 'SELL' and whale_vote == 'BUY':
            return {
                'final_vote': 'HOLD',
                'confidence': 15,
                'reasoning': f"⛔ BEAR TRAP AVOIDED: Technicals say SELL but Dark Pool whales are BUYING. VETO activated.",
                'position_multiplier': 0,
                'risk_level': 'CRITICAL',
                'rule_applied': 'Whale Veto - Bear Trap'
            }
        
        # RULE 1 & 3: Whale Confirmation (100% confidence)
        if tech_vote == whale_vote and whale_vote != 'HOLD':
            final_confidence = min(100, (tech_confidence + whale_confidence) / 2 + 20)
            return {
                'final_vote': tech_vote,
                'confidence': round(final_confidence, 1),
                'reasoning': f"✅ WHALE CONFIRMATION: Technicals and Dark Pool whales AGREE on {tech_vote}. High probability trade.",
                'position_multiplier': 1.0,
                'risk_level': 'LOW',
                'rule_applied': 'Whale Confirmation'
            }
        
        # RULE 5: Whale Neutral - Follow technical with caution
        if whale_vote == 'HOLD':
            return {
                'final_vote': tech_vote,
                'confidence': tech_confidence * 0.7,
                'reasoning': f"⚠️ WHALE NEUTRAL: No dark pool confirmation. Following technicals with reduced confidence.",
                'position_multiplier': 0.5,
                'risk_level': 'MEDIUM',
                'rule_applied': 'Whale Neutral - Caution'
            }
        
        # Default
        return {
            'final_vote': 'HOLD',
            'confidence': 40,
            'reasoning': "Mixed signals. Wait for alignment.",
            'position_multiplier': 0,
            'risk_level': 'HIGH',
            'rule_applied': 'No Alignment'
        }
class ConsensusAgent:
    """
    Weighted Consensus Agent that aggregates signals from all specialized agents
    """
    
    # Weighting Matrix (Not all agents are equal)
    WEIGHT_MATRIX = {
        'Agent_G': 0.5,      # Whale Agent - Leader
        'Agent_H': 0.3,      # Fibonacci Agent - Map
        'Agent_A': 0.2,      # Moving Average - Confirmation
        'Agent_B': 0.15,     # Mean Reversion
        'Agent_C': 0.15,     # Momentum
        'Agent_D': 0.1,      # Volatility
        'Agent_E': 0.1,      # Microstructure
        'Agent_F': 0.1,      # Candlestick
    }
    
    # Veto agents (can stop everything)
    VETO_AGENTS = ['Agent_G', 'Agent_D']  # Whale and Volatility have veto power
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.decision_memory = []  # Last 5 decisions
        self.consensus_history = []
        
    def normalize_signal(self, vote: str, confidence: float) -> float:
        """
        Convert vote to normalized signal between -1.0 and 1.0
        -1.0 = Strong Sell
        0.0 = Neutral/Hold
        1.0 = Strong Buy
        """
        if vote == 'BUY':
            # Scale confidence (0-100) to (0.0-1.0)
            normalized = confidence / 100.0
        elif vote == 'SELL':
            # Negative for sell signals
            normalized = -confidence / 100.0
        else:  # HOLD
            normalized = 0.0
        
        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, normalized))
    
    def check_veto(self, votes: Dict) -> Tuple[bool, str]:
        """
        Veto Logic: If any veto agent says "Danger", stop everything
        """
        for agent_name in self.VETO_AGENTS:
            if agent_name in votes:
                vote_data = votes[agent_name]
                vote = vote_data.get('vote', 'HOLD')
                confidence = vote_data.get('confidence', 50)
                
                # Veto conditions
                if vote == 'SELL' and confidence > 85:
                    return True, f"VETO: {agent_name} issued SELL with {confidence}% confidence - High danger"
                elif vote == 'BUY' and confidence > 95:
                    return True, f"VETO: {agent_name} issued BUY with {confidence}% confidence - Extreme overbought"
                elif confidence > 98:
                    return True, f"VETO: {agent_name} extreme confidence ({confidence}%) - Requires manual review"
        
        return False, None
    
    def calculate_weighted_consensus(self, votes: Dict) -> Dict:
        """
        Calculate weighted consensus using the weighting matrix
        """
        total_weight = 0
        weighted_sum = 0
        active_agents = []
        
        for agent_name, vote_data in votes.items():
            if agent_name not in self.WEIGHT_MATRIX:
                continue
            
            weight = self.WEIGHT_MATRIX[agent_name]
            vote = vote_data.get('vote', 'HOLD')
            confidence = vote_data.get('confidence', 50)
            
            # Normalize signal
            signal = self.normalize_signal(vote, confidence)
            
            weighted_sum += signal * weight
            total_weight += weight
            active_agents.append({
                'name': agent_name,
                'weight': weight,
                'vote': vote,
                'confidence': confidence,
                'signal': signal
            })
        
        if total_weight == 0:
            return {'consensus': 0, 'decision': 'HOLD', 'confidence': 50}
        
        consensus_score = weighted_sum / total_weight
        
        # Convert consensus score to decision
        if consensus_score > 0.3:
            decision = 'BUY'
            confidence = min(95, 50 + consensus_score * 50)
        elif consensus_score < -0.3:
            decision = 'SELL'
            confidence = min(95, 50 + abs(consensus_score) * 50)
        else:
            decision = 'HOLD'
            confidence = 50
        
        return {
            'consensus_score': round(consensus_score, 3),
            'decision': decision,
            'confidence': round(confidence, 1),
            'active_agents': active_agents,
            'total_weight': total_weight
        }
    
    def prevent_wavering(self, new_decision: str, threshold: int = 2) -> bool:
        """
        State Memory: Prevents wavering (changing mind too quickly)
        Returns True if decision is stable, False if wavering detected
        """
        if len(self.decision_memory) < threshold:
            self.decision_memory.append(new_decision)
            return True
        
        # Check last N decisions
        last_decisions = self.decision_memory[-threshold:]
        
        # Count changes
        changes = 0
        for i in range(1, len(last_decisions)):
            if last_decisions[i] != last_decisions[i-1]:
                changes += 1
        
        # If changing too frequently, apply hysteresis
        if changes >= threshold:
            logger.warning(f"Consensus wavering detected: {last_decisions} -> {new_decision}")
            return False
        
        self.decision_memory.append(new_decision)
        
        # Keep only last 5 decisions
        if len(self.decision_memory) > 5:
            self.decision_memory = self.decision_memory[-5:]
        
        return True
    
    def calculate_consensus(self, votes: Dict) -> Dict:
        """
        Main consensus calculation with all features:
        1. Check Veto
        2. Calculate weighted consensus
        3. Prevent wavering
        4. Store in database
        """
        
        # Step 1: VETO CHECK
        veto_triggered, veto_reason = self.check_veto(votes)
        if veto_triggered:
            logger.warning(f"VETO TRIGGERED: {veto_reason}")
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'veto_triggered': True,
                'veto_reason': veto_reason,
                'consensus_score': 0
            }
        
        # Step 2: WEIGHTED CONSENSUS
        weighted_result = self.calculate_weighted_consensus(votes)
        
        # Step 3: PREVENT WAVERING
        is_stable = self.prevent_wavering(weighted_result['decision'])
        
        if not is_stable:
            # Use previous decision to avoid wavering
            previous_decision = self.decision_memory[-2] if len(self.decision_memory) >= 2 else 'HOLD'
            weighted_result['decision'] = previous_decision
            weighted_result['confidence'] = max(30, weighted_result['confidence'] - 20)
            weighted_result['wavering_prevented'] = True
        
        # Step 4: STORE IN DATABASE
        self._store_consensus_record(weighted_result, votes, veto_triggered)
        
        # Log consensus result
        logger.info(f"Consensus Result: {weighted_result['decision']} ({weighted_result['confidence']}%)")
        logger.info(f"Consensus Score: {weighted_result['consensus_score']}")
        
        return weighted_result
    
    def _store_consensus_record(self, result: Dict, votes: Dict, veto_triggered: bool):
        """Store consensus decision in database for audit"""
        if not self.db:
            return
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create consensus_log table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consensus_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decision VARCHAR(10),
                    confidence DECIMAL(5,2),
                    consensus_score DECIMAL(5,3),
                    veto_triggered BOOLEAN,
                    veto_reason TEXT,
                    votes_summary JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Store consensus record
            import json
            cursor.execute("""
                INSERT INTO consensus_log (decision, confidence, consensus_score, veto_triggered, veto_reason, votes_summary)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                result['decision'],
                result['confidence'],
                result.get('consensus_score', 0),
                veto_triggered,
                result.get('veto_reason'),
                json.dumps(votes)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not store consensus record: {e}")
    
    def get_consensus_history(self, limit: int = 20) -> List[Dict]:
        """Get historical consensus decisions from database"""
        if not self.db:
            return []
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT decision, confidence, consensus_score, veto_triggered, timestamp
                FROM consensus_log
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    'decision': row[0],
                    'confidence': row[1],
                    'consensus_score': row[2],
                    'veto_triggered': row[3],
                    'timestamp': row[4].isoformat() if row[4] else None
                })
            
            return history
            
        except Exception as e:
            logger.warning(f"Could not get consensus history: {e}")
            return []
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                         n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Simulate future price paths and predict cloud position probability.
        """
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
    
        for _ in range(n_sims):
            price = current_price
            path = [price]
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
                path.append(price)
        
            # Get Ichimoku cloud at end of simulation (simplified)
            final_price = path[-1]
            # Assume cloud top/bottom based on current price ± 2%
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
        
            if final_price > cloud_top:
                outcomes['above_cloud'] += 1
            elif final_price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
    
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
    
        # Determine vote based on most probable outcome
        if probs['above_cloud'] > 60:
           vote = 'BUY'
           conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
    
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    def get_current_price(symbol):
        """Get price with automatic fallback to cache"""
        result = price_cache.get_price(symbol, use_cache_fallback=True)
    
        if result and result.get('success'):
            return result['mid']
        else:
           # Return last cached price
           cached = price_cache.get_cached_price(symbol)
           if cached:
               return cached['mid']
        return None
     
        
