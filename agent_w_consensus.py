# agent_w_consensus.py
"""
Agent_W - Consensus Agent
Aggregates all agents and generates final weighted consensus
"""

from typing import Dict, List
from datetime import datetime

class ConsensusAgent:
    """Consensus agent that aggregates all other agents"""
    
    def __init__(self):
        self.name = "Agent_W"
        self.agent_type = "Consensus Master"
        self.timeframe = "M15"
        print(f"   ✅ {self.name} initialized")
    
    def analyze(self, signal_data: Dict, agent_signals: List[Dict]) -> Dict:
        symbol = signal_data.get('symbol', 'EURUSD')
        
        if not agent_signals:
            return self._response(symbol, 'HOLD', 50, "No signals")
        
        # Count votes
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        total_weight = 0
        
        for signal in agent_signals:
            if signal:
                vote = signal.get('vote', 'HOLD')
                confidence = signal.get('confidence', 50)
                votes[vote] += confidence
                total_weight += confidence
        
        if total_weight > 0:
            final_action = max(votes, key=votes.get)
            final_confidence = (votes[final_action] / total_weight) * 100
        else:
            final_action = 'HOLD'
            final_confidence = 50
        
        reasoning = f"Consensus: {final_action} (BUY:{votes['BUY']:.0f} SELL:{votes['SELL']:.0f} HOLD:{votes['HOLD']:.0f})"
        
        return self._response(symbol, final_action, final_confidence, reasoning)
    
    def _response(self, symbol, action, confidence, reasoning):
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': action,
            'confidence': round(confidence, 1),
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }
    
    def _consensus_response(self, symbol, reason, action, confidence):
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': action,
            'confidence': confidence,
            'reasoning': reason
        }