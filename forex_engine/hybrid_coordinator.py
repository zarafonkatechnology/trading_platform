# C:\trading_platform\forex_engine\hybrid_coordinator.py

import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class HybridCoordinator:
    """
    Hybrid Coordination System: Hierarchical + Bayesian Trust.
    
    Layer 1: Rule-based overrides (fast, predictable)
    Layer 2: Trust-weighted consensus (adaptive, self-learning)
    Layer 3: Direct execution (low-latency)
    """
    
    def __init__(self, use_hybrid: bool = True):
        self.USE_HYBRID = use_hybrid
        
        # ===== LAYER 1: OVERRIDE RULES =====
        self.override_rules = [
            {
                'name': 'SPREAD_EXTREME',
                'condition': lambda d: abs(d.get('x_z_score', 0)) > 2.5,
                'action': lambda d: 'BUY' if d.get('x_z_score', 0) < 0 else 'SELL',
                'confidence': lambda d: min(95, 75 + abs(d.get('x_z_score', 0)) * 8),
                'priority': 1
            },
            {
                'name': 'SENTIMENT_WHALE',
                'condition': lambda d: d.get('i_vote', 'HOLD') == d.get('g_vote', 'HOLD') != 'HOLD' and d.get('i_conf', 0) > 80,
                'action': lambda d: d.get('i_vote', 'HOLD'),
                'confidence': lambda d: (d.get('i_conf', 0) + d.get('g_conf', 0)) / 2,
                'priority': 2
            },
            {
                'name': 'SUPPLY_DEMAND',
                'condition': lambda d: d.get('r_vote', 'HOLD') != 'HOLD' and d.get('r_conf', 0) > 75,
                'action': lambda d: d.get('r_vote', 'HOLD'),
                'confidence': lambda d: d.get('r_conf', 0) * 0.9,
                'priority': 3
            },
            {
                'name': 'BROKER_SIGNAL',
                'condition': lambda d: d.get('broker_vote', 'HOLD') != 'HOLD' and d.get('broker_conf', 0) > 70,
                'action': lambda d: d.get('broker_vote', 'HOLD'),
                'confidence': lambda d: d.get('broker_conf', 0) * 0.85,
                'priority': 4
            },
        ]
        
        # ===== LAYER 2: BAYESIAN TRUST =====
        self.agent_trust = {
            'X': {'weight': 0.12, 'accuracy': 0.85, 'trades': 0, 'wins': 0},
            'U': {'weight': 0.08, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'D': {'weight': 0.10, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'C': {'weight': 0.10, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'E': {'weight': 0.08, 'accuracy': 0.50, 'trades': 0, 'wins': 0},
            'P': {'weight': 0.08, 'accuracy': 0.50, 'trades': 0, 'wins': 0},
            # Brokers as agents
            'EURUSD': {'weight': 0.12, 'accuracy': 0.75, 'trades': 0, 'wins': 0},
            'GBPUSD': {'weight': 0.10, 'accuracy': 0.70, 'trades': 0, 'wins': 0},
            'USDJPY': {'weight': 0.10, 'accuracy': 0.70, 'trades': 0, 'wins': 0},
            'USDCHF': {'weight': 0.08, 'accuracy': 0.65, 'trades': 0, 'wins': 0},
            'AUDUSD': {'weight': 0.08, 'accuracy': 0.65, 'trades': 0, 'wins': 0},
            'USDCAD': {'weight': 0.06, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'NZDUSD': {'weight': 0.06, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'EURGBP': {'weight': 0.06, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'EURJPY': {'weight': 0.06, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'EURCAD': {'weight': 0.06, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'EURNZD': {'weight': 0.06, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'EURCHF': {'weight': 0.06, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
        }
        
        # ===== LAYER 3: EXECUTION =====
        self.order_queue = []
        self.executed_orders = []
        self.decision_log = []
        
        # ===== STATE =====
        self.last_decision = {'action': 'HOLD', 'confidence': 0}
        self.active_override = None
        
        logger.info("✅ HybridCoordinator initialized")
        logger.info(f"   Mode: {'✅ HYBRID ACTIVE' if self.USE_HYBRID else '⏸️ VOTING MODE'}")
        logger.info("   Layer 1: Override Rules - 4 active")
        logger.info("   Layer 2: Bayesian Trust - 19 agents")
        logger.info("   Layer 3: Direct Execution - Ready")
    
    def update_trust(self, agent_name: str, was_correct: bool):
        """
        Update agent trust score based on trade result.
        agent_name: e.g., 'X', 'EURUSD', 'GBPUSD', etc.
        was_correct: True if trade was profitable, False otherwise.
        """
        if agent_name not in self.agent_trust:
            logger.warning(f"Agent {agent_name} not in trust registry")
            return

        trust = self.agent_trust[agent_name]
        trust['trades'] += 1
        if was_correct:
            trust['wins'] += 1

        # Calculate win rate
        if trust['trades'] > 0:
            win_rate = trust['wins'] / trust['trades']
            # Update accuracy using exponential moving average (EMA)
            alpha = 0.1  # Learning rate
            trust['accuracy'] = trust['accuracy'] * (1 - alpha) + win_rate * alpha
            # Clamp to prevent extreme values
            trust['accuracy'] = max(0.3, min(0.98, trust['accuracy']))
            # Update weight based on accuracy
            trust['weight'] = 0.05 + 0.25 * trust['accuracy']
            # Ensure minimum weight (0.03) and maximum (0.35)
            trust['weight'] = max(0.03, min(0.35, trust['weight']))

        logger.debug(f"Updated trust for {agent_name}: "
                     f"accuracy={trust['accuracy']:.2f}, weight={trust['weight']:.2f}")

    def get_weights(self) -> Dict:
        """Return current weights for all agents."""
        return {agent: info['weight'] for agent, info in self.agent_trust.items()}

    def save_weights(self, filepath: str = 'agent_weights.json'):
        """Save current weights to a JSON file."""
        weights = self.get_weights()
        try:
            with open(filepath, 'w') as f:
                json.dump(weights, f, indent=2)
            logger.info(f"Weights saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    def load_weights(self, filepath: str = 'agent_weights.json'):
        """Load weights from a JSON file."""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    weights = json.load(f)
                for agent, weight in weights.items():
                    if agent in self.agent_trust:
                        self.agent_trust[agent]['weight'] = weight
                logger.info(f"Weights loaded from {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to load weights: {e}")
        return False

    def reset_weights(self):
        """Reset all weights to their initial values based on accuracy."""
        for agent in self.agent_trust:
            trust = self.agent_trust[agent]
            trust['weight'] = 0.05 + 0.25 * trust['accuracy']
            trust['trades'] = 0
            trust['wins'] = 0
        logger.info("All agent weights reset to initial values.")

    
    def get_agent_accuracy(self, agent_name: str) -> float:
        return self.agent_trust.get(agent_name, {}).get('accuracy', 0.5)
    
    def decide(self, agent_data: Dict) -> Dict:
        """
        Main decision function.
        agent_data: dict with keys like 'X', 'U', 'D', 'EURUSD', etc.
                   each value is a dict with 'vote' and 'confidence'
        """
        if not self.USE_HYBRID:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Hybrid disabled', 'use_voting': True}
        
        data = self._flatten_agent_data(agent_data)
        
        # ===== LAYER 1: OVERRIDE RULES =====
        for rule in sorted(self.override_rules, key=lambda x: x['priority']):
            try:
                if rule['condition'](data):
                    action = rule['action'](data)
                    confidence = rule['confidence'](data)
                    self.active_override = rule['name']
                    
                    result = {
                        'action': action,
                        'confidence': min(95, confidence),
                        'reason': f"Override: {rule['name']}",
                        'layer': 'override',
                        'priority': rule['priority']
                    }
                    
                    self.decision_log.append(result)
                    return result
            except Exception as e:
                logger.warning(f"Rule error: {rule['name']} - {e}")
        
        # ===== LAYER 2: BAYESIAN CONSENSUS =====
        result = self._bayesian_consensus(agent_data)
        self.decision_log.append(result)
        self.last_decision = result
        
        return result
    
    def _flatten_agent_data(self, agent_data: Dict) -> Dict:
        """Flatten agent data for rule conditions."""
        flat = {}
        for agent, data in agent_data.items():
            # Check if data is dict with vote and confidence
            if isinstance(data, dict):
                vote = data.get('vote', 'HOLD')
                conf = data.get('confidence', 0)
                flat[f'{agent}_vote'] = vote
                flat[f'{agent}_conf'] = conf
                if 'z_score' in data:
                    flat[f'{agent}_z_score'] = data.get('z_score', 0)
        return flat
    
    def _bayesian_consensus(self, agent_data: Dict) -> Dict:
        """Trust-weighted consensus using Bayesian Model Averaging."""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for agent, data in agent_data.items():
            if agent in self.agent_trust:
                vote = data.get('vote', 'HOLD')
                confidence = data.get('confidence', 50)
                trust_weight = self.agent_trust[agent]['weight']
                accuracy = self.agent_trust[agent]['accuracy']
                
                weight = trust_weight * accuracy
                if vote in votes:
                    votes[vote] += weight * (confidence / 100)
        
        total = sum(votes.values())
        if total > 0:
            action = max(votes, key=votes.get)
            confidence = (votes[action] / total) * 100
            
            if confidence < 50:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Low confidence', 'layer': 'consensus'}
            
            return {
                'action': action,
                'confidence': min(95, confidence),
                'reason': f"Bayesian consensus (weights: {votes})",
                'layer': 'consensus',
                'votes': votes
            }
        
        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No consensus', 'layer': 'consensus'}
    
    def get_status(self) -> Dict:
        """Get system status."""
        return {
            'active_override': self.active_override,
            'last_decision': self.last_decision,
            'agent_trust': self.agent_trust.copy(),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
    