"""
Layer-Based Consensus Calculator
Only relevant agents vote, weighted by layer importance
"""

from config.voting_config import (
    LAYER_WEIGHTS, DIRECTION_VOTING_AGENTS, DIRECTION_WEIGHTS,
    CONFIRMATION_VOTING_AGENTS, CONFIRMATION_WEIGHTS,
    ENTRY_VOTING_AGENTS, ENTRY_WEIGHTS,
    RISK_VOTING_AGENTS, RISK_WEIGHTS,
    VETO_AGENTS, CONSENSUS_THRESHOLDS,
    get_agent_layer, get_agent_weight
)

class LayerConsensus:
    """Calculate consensus using layer-based voting"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset voting tallies"""
        self.layer_results = {
            'direction': {'buy': 0, 'sell': 0, 'hold': 0, 'total_weight': 0},
            'confirmation': {'buy': 0, 'sell': 0, 'hold': 0, 'total_weight': 0},
            'entry': {'buy': 0, 'sell': 0, 'hold': 0, 'total_weight': 0},
            'risk': {'buy': 0, 'sell': 0, 'hold': 0, 'total_weight': 0},
        }
        self.veto_active = False
        self.veto_reason = None
        self.all_votes = {}
    
    def add_vote(self, agent_name, vote, confidence):
        """Add a single agent's vote to the tally"""
        layer = get_agent_layer(agent_name)
        weight = get_agent_weight(agent_name)
        
        # Apply vote to layer tally
        if layer and layer in self.layer_results:
            if vote == 'BUY':
                self.layer_results[layer]['buy'] += weight * (confidence / 100)
            elif vote == 'SELL':
                self.layer_results[layer]['sell'] += weight * (confidence / 100)
            else:
                self.layer_results[layer]['hold'] += weight * (confidence / 100)
            
            self.layer_results[layer]['total_weight'] += weight
        
        # Check for veto
        if agent_name in VETO_AGENTS:
            if (vote == 'SELL' and confidence > 80) or (vote == 'BUY' and confidence > 80):
                self.veto_active = True
                self.veto_reason = f"{agent_name} vetoed: {VETO_AGENTS[agent_name]}"
        
        # Store for reporting
        self.all_votes[agent_name] = {'vote': vote, 'confidence': confidence, 'layer': layer}
    
    def calculate_layer_score(self, layer):
        """Calculate net score for a layer (-100 to +100)"""
        layer_data = self.layer_results[layer]
        total = layer_data['total_weight']
        
        if total == 0:
            return 0
        
        net = (layer_data['buy'] - layer_data['sell']) / total
        return net * 100
    
    def get_layer_direction(self, layer):
        """Get direction for a specific layer"""
        score = self.calculate_layer_score(layer)
        if score > 20:
            return 'BUY', score
        elif score < -20:
            return 'SELL', score
        return 'HOLD', score
    
    def calculate_final_consensus(self):
        """Calculate weighted final consensus"""
        if self.veto_active:
            return {
                'action': 'BLOCKED',
                'confidence': 0,
                'reason': self.veto_reason,
                'layer_scores': {}
            }
        
        final_score = 0
        layer_scores = {}
        
        for layer, weight in LAYER_WEIGHTS.items():
            score = self.calculate_layer_score(layer)
            layer_scores[layer] = score
            final_score += score * weight
        
        # Determine action based on score
        if final_score >= CONSENSUS_THRESHOLDS['strong_buy']:
            action = 'STRONG_BUY'
            confidence = min(100, 50 + final_score / 2)
        elif final_score >= CONSENSUS_THRESHOLDS['buy']:
            action = 'BUY'
            confidence = min(90, 45 + final_score / 2)
        elif final_score <= CONSENSUS_THRESHOLDS['strong_sell']:
            action = 'STRONG_SELL'
            confidence = min(100, 50 + abs(final_score) / 2)
        elif final_score <= CONSENSUS_THRESHOLDS['sell']:
            action = 'SELL'
            confidence = min(90, 45 + abs(final_score) / 2)
        else:
            action = 'HOLD'
            confidence = 50 + abs(final_score) / 2
        
        return {
            'action': action,
            'confidence': round(confidence, 1),
            'score': round(final_score, 1),
            'layer_scores': {k: round(v, 1) for k, v in layer_scores.items()},
            'veto': False
        }
    
    def get_summary(self):
        """Get human-readable summary"""
        summary = []
        summary.append("\n" + "=" * 50)
        summary.append("🗳️ LAYER-BASED VOTING SUMMARY")
        summary.append("=" * 50)
        
        for layer in ['direction', 'confirmation', 'entry', 'risk']:
            direction, score = self.get_layer_direction(layer)
            weight = LAYER_WEIGHTS[layer] * 100
            summary.append(f"\n{layer.upper()} ({weight:.0f}% weight): {direction} ({score:.1f})")
            
            # Show individual agent votes for this layer
            for agent, vote_data in self.all_votes.items():
                if vote_data['layer'] == layer:
                    summary.append(f"   {agent}: {vote_data['vote']} ({vote_data['confidence']:.0f}%)")
        
        final = self.calculate_final_consensus()
        summary.append("\n" + "=" * 50)
        summary.append(f"🎯 FINAL: {final['action']} ({final['confidence']}%)")
        if final.get('reason'):
            summary.append(f"📋 Reason: {final['reason']}")
        summary.append("=" * 50)
        
        return "\n".join(summary)
