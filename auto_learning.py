"""
DeepSeek Auto-Learning System
Automatically teaches agents from their mistakes
"""

import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
import threading

class AutoLearningSystem:
    def __init__(self, deepseek_client, db_connection=None):
        self.deepseek = deepseek_client
        self.db = db_connection
        self.agent_mistakes = defaultdict(list)
        self.agent_lessons = defaultdict(list)
        self.learning_active = True
        self.learning_thread = None
        
    def record_mistake(self, agent_name, agent_type, signal_data, wrong_vote, correct_outcome, confidence):
        """Record an agent's mistake for later learning"""
        mistake = {
            'timestamp': datetime.now().isoformat(),
            'agent_name': agent_name,
            'agent_type': agent_type,
            'signal': signal_data,
            'wrong_vote': wrong_vote,
            'correct_outcome': correct_outcome,
            'confidence': confidence,
            'lesson_given': False
        }
        self.agent_mistakes[agent_name].append(mistake)
        
        # Keep only last 10 mistakes per agent
        if len(self.agent_mistakes[agent_name]) > 10:
            self.agent_mistakes[agent_name].pop(0)
        
        print(f"📝 Recorded mistake for {agent_name}: Voted {wrong_vote}, should have been {correct_outcome}")
        return mistake
    
    def generate_lesson_from_mistake(self, mistake):
        """Use DeepSeek to generate a lesson from a specific mistake"""
        prompt = f"""
You are a trading coach helping an AI agent learn from mistakes.

Agent: {mistake['agent_name']}
Agent Type: {mistake['agent_type']}
Market: {mistake['signal'].get('asset', 'Unknown')}
Price: {mistake['signal'].get('price', 'N/A')}

The agent VOTED: {mistake['wrong_vote']} with {mistake['confidence']:.0f}% confidence
The CORRECT move was: {mistake['correct_outcome']}

Create a SHORT, ACTIONABLE lesson (2-3 sentences) that will help this agent:
1. Understand what they missed
2. Learn a specific rule or indicator to watch for
3. Improve their future voting accuracy

Make it specific to the agent's type ({mistake['agent_type']}).
Keep it under 100 words.
"""
        
        try:
            response = self.deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are an expert trading coach teaching AI agents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=250
            )
            
            lesson = response.choices[0].message.content
            return lesson
        except Exception as e:
            print(f"Error generating lesson: {e}")
            return f"Lesson: When voting {mistake['wrong_vote']}, watch for confirmation signals first."
    
    def teach_agent_from_mistakes(self, agent_name):
        """Generate and apply lessons from all of an agent's mistakes"""
        if agent_name not in self.agent_mistakes:
            return None
        
        mistakes = [m for m in self.agent_mistakes[agent_name] if not m['lesson_given']]
        if not mistakes:
            return None
        
        lessons_given = []
        
        for mistake in mistakes[:3]:  # Max 3 lessons at once
            lesson = self.generate_lesson_from_mistake(mistake)
            mistake['lesson_given'] = True
            
            lessons_given.append({
                'lesson': lesson,
                'mistake_vote': mistake['wrong_vote'],
                'correct_outcome': mistake['correct_outcome']
            })
            
            print(f"🎓 Taught {agent_name}: {lesson[:100]}...")
        
        self.agent_lessons[agent_name].extend(lessons_given)
        
        return {
            'agent': agent_name,
            'lessons_count': len(lessons_given),
            'lessons': lessons_given,
            'xp_awarded': len(lessons_given) * 15  # 15 XP per lesson
        }
    
    def teach_all_agents(self):
        """Teach all agents that have mistakes"""
        results = {}
        for agent_name in list(self.agent_mistakes.keys()):
            result = self.teach_agent_from_mistakes(agent_name)
            if result:
                results[agent_name] = result
        return results
    
    def analyze_agent_performance(self, agent_name, vote_history):
        """DeepSeek analyzes an agent's overall performance"""
        prompt = f"""
Analyze this trading agent's performance and provide improvement recommendations:

Agent: {agent_name}
Vote History (last {len(vote_history)} votes):
{json.dumps(vote_history[-10:], indent=2)}

Provide:
1. Their main weakness (1 sentence)
2. One specific indicator they should use more
3. A motivational tip to improve
"""
        
        try:
            response = self.deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=200
            )
            return response.choices[0].message.content
        except:
            return "Keep practicing and learning from mistakes!"
    
    def start_auto_learning(self, interval_minutes=30):
        """Start background auto-learning thread"""
        def learning_loop():
            while self.learning_active:
                try:
                    print("🧠 DeepSeek Auto-Learning: Analyzing agent mistakes...")
                    results = self.teach_all_agents()
                    if results:
                        for agent, result in results.items():
                            print(f"   ✅ {agent}: {result['lessons_count']} lessons taught (+{result['xp_awarded']} XP)")
                    else:
                        print("   No new mistakes to learn from")
                except Exception as e:
                    print(f"Auto-learning error: {e}")
                
                time.sleep(interval_minutes * 60)
        
        self.learning_thread = threading.Thread(target=learning_loop, daemon=True)
        self.learning_thread.start()
        print(f"🤖 Auto-learning started (every {interval_minutes} minutes)")
    
    def stop_auto_learning(self):
        self.learning_active = False
        print("Auto-learning stopped")

# Global instance
auto_learning = None

def init_auto_learning(deepseek_client):
    global auto_learning
    auto_learning = AutoLearningSystem(deepseek_client)
    return auto_learning
