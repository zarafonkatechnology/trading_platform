"""
Agent Discussion Forum - Agents discuss trades before voting
"""

import threading
import time
import random
from datetime import datetime
from typing import Dict, List

class AgentForum:
    """Agents discuss and debate trades before voting"""
    
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.discussions = []
        self.is_running = False
    
    def start(self):
        """Start discussion forum"""
        self.is_running = True
        thread = threading.Thread(target=self._discussion_loop, daemon=True)
        thread.start()
        print("✅ Agent Forum started - Agents will discuss before voting")
    
    def _discussion_loop(self):
        """Run discussion cycles"""
        while self.is_running:
            try:
                self._run_discussion_cycle()
                time.sleep(120)  # Discuss every 2 minutes
            except Exception as e:
                print(f"Discussion error: {e}")
                time.sleep(60)
    
    def _run_discussion_cycle(self):
        """Run one discussion cycle"""
        agents = self.agent_manager.get_all_agents()
        if len(agents) < 2:
            return
        
        # Select topic
        topics = ['Gold Price Movement', 'Oil Market Outlook', 'Forex Trends', 'Volatility Analysis']
        topic = random.choice(topics)
        
        discussion = {
            'topic': topic,
            'started_at': datetime.now().isoformat(),
            'messages': [],
            'participants': []
        }
        
        # Each agent contributes
        for agent in agents[:5]:
            message = self._generate_agent_message(agent, topic)
            discussion['messages'].append({
                'agent': agent.name,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            discussion['participants'].append(agent.name)
            
            # Award small XP for participating
            agent.xp_points += 2
        
        self.discussions.insert(0, discussion)
        
        # Keep last 20 discussions
        if len(self.discussions) > 20:
            self.discussions = self.discussions[:20]
        
        # Store in knowledge exchange
        self._store_discussion(discussion)
    
    def _generate_agent_message(self, agent, topic: str) -> str:
        """Generate discussion message from agent"""
        templates = {
            'Agent_A': f"I see a strong trend developing in {topic}. My indicators suggest continuation.",
            'Agent_B': f"I'm watching for reversals in {topic}. RSI is at a key level.",
            'Agent_C': f"Momentum on {topic} is {'building' if random.random() > 0.5 else 'slowing'}.",
            'Agent_D': f"Volatility in {topic} is {'increasing' if random.random() > 0.5 else 'decreasing'}.",
            'Agent_F': f"I detect a potential reversal pattern in {topic}."
        }
        return templates.get(agent.name, f"I've analyzed {topic} and have some insights to share.")
    
    def _store_discussion(self, discussion: Dict):
        """Store discussion in knowledge exchange"""
        try:
            from app_code import app
            if hasattr(app, 'knowledge_exchanges'):
                for msg in discussion['messages']:
                    app.knowledge_exchanges.insert(0, {
                        'from_agent': msg['agent'],
                        'to_agent': 'ALL AGENTS',
                        'topic': f'💬 Forum: {discussion["topic"]}',
                        'content': msg['message'],
                        'xp_reward': 2,
                        'token_reward': 1,
                        'timestamp': msg['timestamp']
                    })
        except:
            pass
    
    def get_discussions(self, limit: int = 10) -> List[Dict]:
        """Get recent discussions"""
        return self.discussions[:limit]

# Singleton
_forum = None

def get_agent_forum(agent_manager):
    global _forum
    if _forum is None:
        _forum = AgentForum(agent_manager)
    return _forum
