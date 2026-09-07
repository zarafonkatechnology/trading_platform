"""
Dynamic Agent Weighting System
- Adjusts agent voting power based on recent performance
- Exponential decay weighting (recent trades matter more)
- Prevents over-reliance on underperforming agents
"""

import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class AgentPerformance:
    """Performance record for a single agent"""
    name: str
    total_votes: int = 0
    correct_votes: int = 0
    recent_results: deque = None
    weight: float = 1.0
    last_update: datetime = None
    
    def __post_init__(self):
        self.recent_results = deque(maxlen=50)  # Last 50 votes
    
    @property
    def win_rate(self) -> float:
        if self.total_votes == 0:
            return 0.5
        return self.correct_votes / self.total_votes
    
    @property
    def recent_win_rate(self) -> float:
        if not self.recent_results:
            return 0.5
        return sum(self.recent_results) / len(self.recent_results)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'total_votes': self.total_votes,
            'correct_votes': self.correct_votes,
            'win_rate': round(self.win_rate * 100, 1),
            'recent_win_rate': round(self.recent_win_rate * 100, 1),
            'weight': round(self.weight, 3),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


class DynamicWeightManager:
    """
    Manages dynamic voting weights for all agents.
    Weights decay with time and adjust based on recent accuracy.
    """
    
    def __init__(self, decay_factor: float = 0.95, 
                 min_weight: float = 0.3,
                 max_weight: float = 1.5,
                 recent_window: int = 20):
        """
        Args:
            decay_factor: How much recent performance matters (0.9-0.99)
            min_weight: Minimum allowed weight
            max_weight: Maximum allowed weight
            recent_window: Number of recent votes to consider
        """
        self.decay_factor = decay_factor
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.recent_window = recent_window
        
        self.agents: Dict[str, AgentPerformance] = {}
        self.history_file = "agent_weights_history.json"
        self._load_history()
    
    def register_agent(self, agent_name: str):
        """Register a new agent"""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentPerformance(name=agent_name)
            print(f"📊 Registered agent: {agent_name}")
    
    def record_vote(self, agent_name: str, was_correct: bool, confidence: float = None):
        """
        Record a vote outcome to update agent's weight.
        
        Args:
            agent_name: Name of the agent
            was_correct: Whether the vote was correct
            confidence: Optional confidence score (not used for weight)
        """
        if agent_name not in self.agents:
            self.register_agent(agent_name)
        
        agent = self.agents[agent_name]
        agent.total_votes += 1
        if was_correct:
            agent.correct_votes += 1
        agent.recent_results.append(1 if was_correct else 0)
        agent.last_update = datetime.now()
        
        # Update weight based on recent performance
        self._update_weight(agent)
        
        # Auto-save periodically
        if agent.total_votes % 10 == 0:
            self._save_history()
    
    def _update_weight(self, agent: AgentPerformance):
        """Calculate new weight based on recent performance"""
        if agent.total_votes < 5:
            # Not enough data, keep neutral weight
            agent.weight = 1.0
            return
        
        # Calculate exponential weighted average of recent results
        recent = list(agent.recent_results)[-self.recent_window:]
        if not recent:
            agent.weight = 1.0
            return
        
        # Exponential weights (more recent = higher weight)
        weights = [self.decay_factor ** (len(recent) - 1 - i) for i in range(len(recent))]
        weighted_avg = sum(w * r for w, r in zip(weights, recent)) / sum(weights)
        
        # Map accuracy (0-1) to weight (min_weight to max_weight)
        # Baseline 50% accuracy = 1.0 weight
        # 60% accuracy = 1.2 weight, 40% accuracy = 0.8 weight
        weight = 0.5 + weighted_avg  # Maps 0-1 to 0.5-1.5
        
        # Apply bounds
        agent.weight = max(self.min_weight, min(self.max_weight, weight))
    
    def get_weight(self, agent_name: str) -> float:
        """Get current weight for an agent"""
        if agent_name not in self.agents:
            return 1.0
        return self.agents[agent_name].weight
    
    def get_adjusted_vote(self, agent_name: str, vote: str, confidence: float) -> Tuple[str, float]:
        """
        Get weight-adjusted vote and confidence.
        
        Returns:
            (vote, adjusted_confidence)
        """
        weight = self.get_weight(agent_name)
        adjusted_confidence = min(95, confidence * weight)
        
        # Extreme weights can flip vote if confidence is very low
        if weight > 1.3 and confidence > 70:
            # Strong agent, keep vote
            return vote, adjusted_confidence
        elif weight < 0.7 and confidence < 60:
            # Weak agent, default to HOLD
            return 'HOLD', adjusted_confidence * 0.5
        
        return vote, adjusted_confidence
    
    def get_all_weights(self) -> Dict[str, float]:
        """Get all agent weights"""
        return {name: agent.weight for name, agent in self.agents.items()}
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for all agents"""
        return {
            name: agent.to_dict()
            for name, agent in self.agents.items()
        }
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get agent leaderboard by recent win rate"""
        agents_list = list(self.agents.values())
        agents_list.sort(key=lambda a: a.recent_win_rate, reverse=True)
        return [a.to_dict() for a in agents_list[:limit]]
    
    def _save_history(self):
        """Save weight history to disk"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'agents': {
                    name: {
                        'weight': agent.weight,
                        'total_votes': agent.total_votes,
                        'correct_votes': agent.correct_votes,
                        'recent_win_rate': agent.recent_win_rate
                    }
                    for name, agent in self.agents.items()
                }
            }
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save weight history: {e}")
    
    def _load_history(self):
        """Load weight history from disk"""
        if not os.path.exists(self.history_file):
            return
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                for name, agent_data in data.get('agents', {}).items():
                    if name in self.agents:
                        self.agents[name].weight = agent_data.get('weight', 1.0)
        except Exception as e:
            print(f"Failed to load weight history: {e}")
    
    def reset_agent(self, agent_name: str):
        """Reset agent's performance history"""
        if agent_name in self.agents:
            self.agents[agent_name] = AgentPerformance(name=agent_name)
            print(f"🔄 Reset performance for {agent_name}")


# ============================================================
# Integration with Existing Voting System
# ============================================================

class WeightedVotingSystem:
    """
    Integrates dynamic weights with your existing voting mechanism.
    """
    
    def __init__(self):
        self.weight_manager = DynamicWeightManager()
    
    def register_all_agents(self, agent_names: List[str]):
        """Register all agents at startup"""
        for name in agent_names:
            self.weight_manager.register_agent(name)
    
    def process_votes(self, agent_votes: Dict[str, Dict]) -> Dict:
        """
        Process votes with dynamic weights.
        
        Input: {agent_name: {'vote': 'BUY', 'confidence': 75}}
        Output: Adjusted votes with weights
        """
        adjusted_votes = {}
        weighted_buy = 0
        weighted_sell = 0
        weighted_hold = 0
        total_weight = 0
        
        for agent_name, vote_data in agent_votes.items():
            original_vote = vote_data.get('vote', 'HOLD')
            confidence = vote_data.get('confidence', 50)
            
            # Get adjusted vote with weight
            adjusted_vote, adjusted_confidence = self.weight_manager.get_adjusted_vote(
                agent_name, original_vote, confidence
            )
            
            adjusted_votes[agent_name] = {
                'original_vote': original_vote,
                'adjusted_vote': adjusted_vote,
                'original_confidence': confidence,
                'adjusted_confidence': adjusted_confidence,
                'weight': self.weight_manager.get_weight(agent_name)
            }
            
            weight = self.weight_manager.get_weight(agent_name)
            total_weight += weight
            
            if adjusted_vote == 'BUY':
                weighted_buy += weight
            elif adjusted_vote == 'SELL':
                weighted_sell += weight
            else:
                weighted_hold += weight
        
        # Calculate weighted consensus
        if total_weight > 0:
            buy_pct = (weighted_buy / total_weight) * 100
            sell_pct = (weighted_sell / total_weight) * 100
            hold_pct = (weighted_hold / total_weight) * 100
        else:
            buy_pct = sell_pct = hold_pct = 33.3
        
        # Determine final decision
        if buy_pct > sell_pct and buy_pct > hold_pct:
            final_vote = 'BUY'
            final_confidence = buy_pct
        elif sell_pct > buy_pct and sell_pct > hold_pct:
            final_vote = 'SELL'
            final_confidence = sell_pct
        else:
            final_vote = 'HOLD'
            final_confidence = max(hold_pct, max(buy_pct, sell_pct))
        
        return {
            'final_vote': final_vote,
            'final_confidence': round(final_confidence, 1),
            'weighted_distribution': {
                'BUY': round(buy_pct, 1),
                'SELL': round(sell_pct, 1),
                'HOLD': round(hold_pct, 1)
            },
            'individual_votes': adjusted_votes,
            'total_weight': round(total_weight, 2)
        }
    
    def record_outcome(self, agent_votes: Dict, actual_outcome: str, 
                       pnl: float = None, was_profitable: bool = None):
        """
        Record outcome for all agents after trade closes.
        
        Args:
            agent_votes: The original votes (before adjustment)
            actual_outcome: 'BUY', 'SELL', or 'HOLD' (what actually happened)
            pnl: Profit/loss amount (optional)
            was_profitable: Whether the trade was profitable (optional)
        """
        # Determine if each agent's vote was correct
        for agent_name, vote_data in agent_votes.items():
            original_vote = vote_data.get('vote', 'HOLD')
            was_correct = (original_vote == actual_outcome)
            
            # Optionally, consider profit for partial correctness
            if was_profitable is not None and pnl is not None:
                if pnl > 0 and original_vote == actual_outcome:
                    was_correct = True
                elif pnl < 0 and original_vote != actual_outcome:
                    was_correct = True
                else:
                    was_correct = False
            
            self.weight_manager.record_vote(agent_name, was_correct)


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("DYNAMIC AGENT WEIGHTING - TEST")
    print("=" * 60)
    
    # Initialize
    weighted_voting = WeightedVotingSystem()
    
    # Register agents
    agents = ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E']
    weighted_voting.register_all_agents(agents)
    
    # Simulate votes over time
    print("\n📊 Simulating votes and updating weights...")
    
    for episode in range(20):
        # Simulate votes
        votes = {}
        for agent in agents:
            # Random votes with agent-specific bias
            if agent == 'Agent_A':
                vote = 'BUY' if episode < 15 else 'HOLD'
                confidence = 70 + episode * 0.5
            elif agent == 'Agent_B':
                vote = 'SELL' if episode > 5 else 'BUY'
                confidence = 65 + episode * 0.3
            else:
                vote = ['BUY', 'SELL', 'HOLD'][episode % 3]
                confidence = 60 + (episode % 20)
            
            votes[agent] = {'vote': vote, 'confidence': confidence}
        
        # Process with weights
        result = weighted_voting.process_votes(votes)
        
        # Simulate outcome (let's say BUY was correct for first 15 episodes)
        actual_outcome = 'BUY' if episode < 15 else 'SELL'
        
        # Record outcome
        weighted_voting.record_outcome(votes, actual_outcome)
        
        if (episode + 1) % 5 == 0:
            print(f"\nEpisode {episode + 1}:")
            print(f"   Final Decision: {result['final_vote']} ({result['final_confidence']:.1f}%)")
            for agent, weight in weighted_voting.weight_manager.get_all_weights().items():
                print(f"      {agent}: weight={weight:.2f}")
    
    # Show final weights
    print("\n" + "=" * 60)
    print("FINAL AGENT WEIGHTS")
    print("=" * 60)
    
    summary = weighted_voting.weight_manager.get_performance_summary()
    for agent, info in summary.items():
        print(f"\n{agent}:")
        print(f"   Weight: {info['weight']:.2f}")
        print(f"   Win Rate: {info['win_rate']:.1f}%")
        print(f"   Recent WR: {info['recent_win_rate']:.1f}%")
        print(f"   Votes: {info['total_votes']}")
    
    print("\n✅ Dynamic weight system ready")
