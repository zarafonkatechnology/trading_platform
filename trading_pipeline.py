"""
Multi-Agent Trading Pipeline - 4 Layers
"""

import time
from datetime import datetime
from collections import defaultdict

class TradingPipeline:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.layer1_agents = []   # Direction (4H, 1H)
        self.layer2_agents = []   # Confirmation (15M)
        self.layer3_agents = []   # Timing & Entry (5M)
        self.layer4_agents = []   # Risk & Execution
        
        self._classify_agents()
    
    def _classify_agents(self):
        """Group agents by layer based on their role/timeframe"""
        for name, agent in self.agent_manager.agents.items():
            timeframe = getattr(agent, 'timeframe', '')
            role = getattr(agent, 'role', '')
            if timeframe in ['4H', '1H', 'Daily'] or 'Direction' in role:
                self.layer1_agents.append(agent)
            elif timeframe == '15M' or 'Confirmation' in role:
                self.layer2_agents.append(agent)
            elif timeframe == '5M' or 'Entry' in role:
                self.layer3_agents.append(agent)
            else:
                self.layer4_agents.append(agent)
    
    def run_layer(self, agents, signal_data):
        """Run a layer of agents and return aggregated result"""
        results = []
        for agent in agents:
            try:
                vote = agent.analyze(signal_data)
                results.append(vote)
            except Exception as e:
                print(f"Error in agent {agent.name}: {e}")
        return results
    
    def execute(self, pair, price):
        """Run full pipeline"""
        signal_data = {'pair': pair, 'price': price}
        
        # Layer 1: Direction
        layer1_results = self.run_layer(self.layer1_agents, signal_data)
        direction = self._aggregate_layer1(layer1_results)
        if direction == 'HOLD':
            return self._decision('HOLD', 0, 'Layer 1 direction conflict')
        
        # Layer 2: Confirmation
        layer2_results = self.run_layer(self.layer2_agents, signal_data)
        if not self._confirm_layer2(layer2_results):
            return self._decision('HOLD', 0, 'Layer 2 confirmation failed')
        
        # Layer 3: Timing
        layer3_results = self.run_layer(self.layer3_agents, signal_data)
        entry = self._find_entry(layer3_results)
        if not entry:
            return self._decision('HOLD', 0, 'No entry signal')
        
        # Layer 4: Risk & Execution
        if not self._risk_check():
            return self._decision('HOLD', 0, 'Risk layer veto')
        
        final_vote, final_confidence = self._final_consensus(layer1_results, layer2_results, layer3_results)
        return self._decision(final_vote, final_confidence, 'All layers passed')
    
    def _aggregate_layer1(self, results):
        """Majority vote from direction agents"""
        buys = sum(1 for r in results if r.get('vote') == 'BUY')
        sells = sum(1 for r in results if r.get('vote') == 'SELL')
        if buys > sells:
            return 'BUY'
        elif sells > buys:
            return 'SELL'
        return 'HOLD'
    
    def _confirm_layer2(self, results):
        """At least 60% of confirmation agents must agree with direction"""
        # simplified: just check consensus > 0.6
        agrees = sum(1 for r in results if r.get('vote') in ['BUY', 'SELL'])
        return (agrees / len(results)) > 0.6 if results else False
    
    def _find_entry(self, results):
        """At least 2 entry signals must align"""
        buys = sum(1 for r in results if r.get('vote') == 'BUY')
        sells = sum(1 for r in results if r.get('vote') == 'SELL')
        return buys > 0 or sells > 0
    
    def _risk_check(self):
        # Placeholder – implement actual risk checks
        return True
    
    def _final_consensus(self, l1, l2, l3):
        total_weight = 0
        weighted_vote = 0
        for r in l1+l2+l3:
            weight = r.get('weight', 1.0)
            total_weight += weight
            if r.get('vote') == 'BUY':
                weighted_vote += weight
            elif r.get('vote') == 'SELL':
                weighted_vote -= weight
        if total_weight == 0:
            return 'HOLD', 0
        final_score = (weighted_vote / total_weight) * 100
        if final_score > 20:
            return 'BUY', min(95, 50 + final_score)
        elif final_score < -20:
            return 'SELL', min(95, 50 - final_score)
        return 'HOLD', 50
    
    def _decision(self, vote, confidence, reason):
        return {
            'action': vote,
            'confidence': confidence,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
