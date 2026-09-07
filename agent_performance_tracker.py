"""
Real-Time Agent Performance Tracker
- Tracks win rates, confidence, XP, voting accuracy
- Updates in real-time during trading cycles
- Provides dashboard data via API
"""

import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    name: str
    agent_type: str
    total_votes: int = 0
    correct_votes: int = 0
    total_confidence: float = 0.0
    xp_points: int = 0
    token_balance: int = 0
    knowledge_shared_count: int = 0
    win_rate_history: deque = field(default_factory=lambda: deque(maxlen=20))
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=20))
    last_vote_time: Optional[datetime] = None
    last_vote: str = "HOLD"
    last_confidence: float = 0.0
    
    @property
    def win_rate(self) -> float:
        """Calculate current win rate."""
        if self.total_votes == 0:
            return 0.0
        return (self.correct_votes / self.total_votes) * 100
    
    @property
    def avg_confidence(self) -> float:
        """Calculate average confidence."""
        if self.total_votes == 0:
            return 0.0
        return self.total_confidence / self.total_votes
    
    @property
    def performance_score(self) -> float:
        """
        Calculate overall performance score (0-100).
        Combines win rate, confidence, and XP.
        """
        win_score = self.win_rate
        conf_score = self.avg_confidence
        xp_score = min(100, self.xp_points / 1000)
        
        # Weighted average
        return (win_score * 0.5) + (conf_score * 0.3) + (xp_score * 0.2)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'type': self.agent_type,
            'total_votes': self.total_votes,
            'correct_votes': self.correct_votes,
            'win_rate': round(self.win_rate, 1),
            'avg_confidence': round(self.avg_confidence, 1),
            'xp_points': self.xp_points,
            'token_balance': self.token_balance,
            'knowledge_shared': self.knowledge_shared_count,
            'performance_score': round(self.performance_score, 1),
            'last_vote': self.last_vote,
            'last_confidence': round(self.last_confidence, 1),
            'last_vote_time': self.last_vote_time.isoformat() if self.last_vote_time else None,
            'win_rate_history': list(self.win_rate_history),
            'confidence_history': list(self.confidence_history)
        }


class AgentPerformanceTracker:
    """
    Real-time tracker for all agents.
    Thread-safe, persists data to disk.
    """
    
    def __init__(self, save_interval: int = 60):
        """
        Args:
            save_interval: Save to disk every N seconds
        """
        self.agents: Dict[str, AgentMetrics] = {}
        self.lock = Lock()
        self.save_interval = save_interval
        self.last_save = time.time()
        self.data_file = "agent_performance.json"
        self._load_from_disk()
    
    def register_agent(self, name: str, agent_type: str):
        """Register a new agent."""
        with self.lock:
            if name not in self.agents:
                self.agents[name] = AgentMetrics(name=name, agent_type=agent_type)
                print(f"📊 Registered agent: {name}")
    
    def update_from_vote(self, agent_name: str, vote: str, confidence: float, 
                         was_correct: Optional[bool] = None, xp_gained: int = 0):
        """
        Update agent metrics after a vote.
        
        Args:
            agent_name: Name of the agent
            vote: BUY/SELL/HOLD
            confidence: Confidence level (0-100)
            was_correct: Whether the vote was correct (None if unknown yet)
            xp_gained: XP earned from this vote
        """
        with self.lock:
            if agent_name not in self.agents:
                return
            
            agent = self.agents[agent_name]
            agent.total_votes += 1
            agent.total_confidence += confidence
            agent.xp_points += xp_gained
            agent.last_vote = vote
            agent.last_confidence = confidence
            agent.last_vote_time = datetime.now()
            agent.confidence_history.append(confidence)
            
            if was_correct is not None:
                if was_correct:
                    agent.correct_votes += 1
                agent.win_rate_history.append(agent.win_rate)
            
            self._check_save()
    
    def update_from_database(self, agent_data: Dict):
        """
        Bulk update from database.
        
        Args:
            agent_data: Dictionary with agent_name -> metrics
        """
        with self.lock:
            for name, data in agent_data.items():
                if name not in self.agents:
                    self.agents[name] = AgentMetrics(
                        name=name,
                        agent_type=data.get('agent_type', 'Unknown')
                    )
                
                agent = self.agents[name]
                agent.xp_points = data.get('xp_points', 0)
                agent.token_balance = data.get('token_balance', 0)
                agent.knowledge_shared_count = data.get('knowledge_shared_count', 0)
                agent.total_votes = data.get('total_votes', 0)
                agent.correct_votes = data.get('correct_votes', 0)
            
            self._check_save()
    
    def record_trade_outcome(self, agent_name: str, was_correct: bool):
        """
        Record whether an agent's vote was correct after trade closes.
        """
        with self.lock:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                if was_correct:
                    agent.correct_votes += 1
                agent.win_rate_history.append(agent.win_rate)
                self._check_save()
    
    def get_agent_metrics(self, agent_name: str) -> Optional[Dict]:
        """Get metrics for a specific agent."""
        with self.lock:
            if agent_name in self.agents:
                return self.agents[agent_name].to_dict()
        return None
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """Get metrics for all agents."""
        with self.lock:
            return {name: agent.to_dict() for name, agent in self.agents.items()}
    
    def get_leaderboard(self, sort_by: str = 'performance_score', limit: int = 10) -> List[Dict]:
        """
        Get agent leaderboard sorted by specified metric.
        
        Args:
            sort_by: 'win_rate', 'performance_score', 'xp_points', 'avg_confidence'
            limit: Number of agents to return
        """
        with self.lock:
            agents_list = list(self.agents.values())
            
            sort_map = {
                'win_rate': lambda a: a.win_rate,
                'performance_score': lambda a: a.performance_score,
                'xp_points': lambda a: a.xp_points,
                'avg_confidence': lambda a: a.avg_confidence,
                'total_votes': lambda a: a.total_votes
            }
            
            key_func = sort_map.get(sort_by, lambda a: a.performance_score)
            sorted_agents = sorted(agents_list, key=key_func, reverse=True)
            
            return [agent.to_dict() for agent in sorted_agents[:limit]]
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics across all agents."""
        with self.lock:
            if not self.agents:
                return {}
            
            total_xp = sum(a.xp_points for a in self.agents.values())
            total_votes = sum(a.total_votes for a in self.agents.values())
            total_correct = sum(a.correct_votes for a in self.agents.values())
            avg_confidence = sum(a.avg_confidence for a in self.agents.values()) / len(self.agents)
            
            return {
                'total_agents': len(self.agents),
                'total_xp': total_xp,
                'total_votes': total_votes,
                'total_correct': total_correct,
                'overall_win_rate': round((total_correct / total_votes * 100) if total_votes > 0 else 0, 1),
                'avg_confidence': round(avg_confidence, 1),
                'best_agent': max(self.agents.values(), key=lambda a: a.performance_score).name,
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_save(self):
        """Auto-save to disk if interval elapsed."""
        if time.time() - self.last_save >= self.save_interval:
            self._save_to_disk()
    
    def _save_to_disk(self):
        """Save performance data to disk."""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'agents': self.get_all_metrics(),
                'summary': self.get_summary_stats()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.last_save = time.time()
        except Exception as e:
            print(f"⚠️ Failed to save performance data: {e}")
    
    def _load_from_disk(self):
        """Load performance data from disk."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    for name, agent_data in data.get('agents', {}).items():
                        self.agents[name] = AgentMetrics(
                            name=name,
                            agent_type=agent_data.get('type', 'Unknown'),
                            total_votes=agent_data.get('total_votes', 0),
                            correct_votes=agent_data.get('correct_votes', 0),
                            total_confidence=agent_data.get('avg_confidence', 0) * agent_data.get('total_votes', 0),
                            xp_points=agent_data.get('xp_points', 0),
                            token_balance=agent_data.get('token_balance', 0),
                            knowledge_shared_count=agent_data.get('knowledge_shared', 0)
                        )
            except Exception as e:
                print(f"⚠️ Failed to load performance data: {e}")


# ============================================================
# Flask API Endpoints for Dashboard
# ============================================================

def register_dashboard_endpoints(app, tracker: AgentPerformanceTracker):
    """
    Register Flask endpoints for the performance dashboard.
    Call this from your main app.
    """
    
    @app.route('/api/performance/agents', methods=['GET'])
    def get_agent_performance():
        """Get all agent performance metrics."""
        return jsonify({
            'success': True,
            'agents': tracker.get_all_metrics(),
            'summary': tracker.get_summary_stats()
        })
    
    @app.route('/api/performance/leaderboard', methods=['GET'])
    def get_leaderboard():
        """Get agent leaderboard."""
        sort_by = request.args.get('sort_by', 'performance_score')
        limit = int(request.args.get('limit', 10))
        return jsonify({
            'success': True,
            'leaderboard': tracker.get_leaderboard(sort_by=sort_by, limit=limit)
        })
    
    @app.route('/api/performance/agent/<agent_name>', methods=['GET'])
    def get_agent_metrics_route(agent_name):
        """Get metrics for specific agent."""
        metrics = tracker.get_agent_metrics(agent_name)
        if metrics:
            return jsonify({'success': True, 'agent': metrics})
        return jsonify({'success': False, 'error': 'Agent not found'}), 404
    
    @app.route('/api/performance/summary', methods=['GET'])
    def get_performance_summary():
        """Get summary statistics."""
        return jsonify({
            'success': True,
            'summary': tracker.get_summary_stats()
        })
    
    print("✅ Performance dashboard endpoints registered")


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("AGENT PERFORMANCE TRACKER - TEST")
    print("=" * 60)
    
    tracker = AgentPerformanceTracker(save_interval=30)
    
    # Register agents
    for i in range(5):
        tracker.register_agent(f"Agent_{chr(65+i)}", "Trading Agent")
    
    # Simulate votes
    import random
    for _ in range(50):
        for name in tracker.agents.keys():
            vote = random.choice(['BUY', 'SELL', 'HOLD'])
            confidence = random.uniform(50, 95)
            was_correct = random.random() > 0.4
            xp = random.randint(10, 50)
            
            tracker.update_from_vote(name, vote, confidence, was_correct, xp)
    
    # Print results
    print("\n📊 AGENT PERFORMANCE SUMMARY")
    print("-" * 40)
    summary = tracker.get_summary_stats()
    print(f"Total Agents: {summary['total_agents']}")
    print(f"Total XP: {summary['total_xp']}")
    print(f"Overall Win Rate: {summary['overall_win_rate']}%")
    print(f"Best Agent: {summary['best_agent']}")
    
    print("\n🏆 LEADERBOARD")
    print("-" * 40)
    for i, agent in enumerate(tracker.get_leaderboard(limit=5), 1):
        print(f"{i}. {agent['name']}: {agent['performance_score']}% "
              f"(Win: {agent['win_rate']}%, XP: {agent['xp_points']})")
    
    print("\n✅ Performance tracker ready")
