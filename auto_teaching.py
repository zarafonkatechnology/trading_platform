"""
Auto-Teaching System - DeepSeek Proactively Teaches Agents
Runs in background, teaches agents based on performance
"""

import threading
import time
import requests
from datetime import datetime, timedelta
from collections import defaultdict

class AutoTeachingSystem:
    """Automatic teaching system using DeepSeek API"""
    
    def __init__(self, db_connection_func, deepseek_api_key):
        self.get_db = db_connection_func
        self.api_key = deepseek_api_key
        self.is_running = False
        self.thread = None
        self.last_teaching_time = defaultdict(datetime.now)
        self.teaching_interval_hours = 6  # Teach every 6 hours
        
    def start(self):
        """Start the auto-teaching background thread"""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._auto_teach_loop, daemon=True)
        self.thread.start()
        print("🧠 Auto-Teaching System Started - DeepSeek will teach agents automatically")
    
    def stop(self):
        """Stop auto-teaching"""
        self.is_running = False
    
    def _call_deepseek(self, prompt, system_message="You are an expert trading coach."):
        """Call DeepSeek API directly"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"API Error: {response.status_code}")
    
    def _get_agents_needing_teaching(self):
        """Get agents that need teaching based on performance"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Get agents with low win rate or haven't been taught recently
        cur.execute("""
            SELECT agent_name, agent_type, specialization, xp_points, vote_accuracy, 
                   COALESCE(knowledge_shared_count, 0) as lessons
            FROM core_agents 
            WHERE is_active = true
            ORDER BY vote_accuracy ASC
        """)
        agents = cur.fetchall()
        cur.close()
        conn.close()
        
        needing_teaching = []
        for agent in agents:
            agent_name = agent[0]
            win_rate = agent[4] if agent[4] else 50
            lessons_received = agent[5] if agent[5] else 0
            
            # Priority: low win rate agents get taught first
            if win_rate < 60:
                priority = "HIGH"
            elif win_rate < 70:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            # Check if enough time has passed since last teaching
            last_taught = self.last_teaching_time.get(agent_name, datetime.now() - timedelta(days=1))
            hours_since = (datetime.now() - last_taught).total_seconds() / 3600
            
            if hours_since >= self.teaching_interval_hours or priority == "HIGH":
                needing_teaching.append({
                    'name': agent_name,
                    'type': agent[1] or 'Trading Agent',
                    'specialization': agent[2] or 'market analysis',
                    'xp': agent[3] or 0,
                    'win_rate': win_rate,
                    'lessons': lessons_received,
                    'priority': priority
                })
        
        return needing_teaching
    
    def _generate_lesson(self, agent):
        """Generate a personalized lesson for an agent"""
        
        if agent['win_rate'] < 50:
            # Poor performer - need basic correction
            prompt = f"""Agent {agent['name']} ({agent['type']}) has a {agent['win_rate']}% win rate.

This is LOW. Create a CORRECTIVE lesson (2-3 sentences) teaching:
1. What they are doing wrong
2. One specific rule to fix it
3. A simple indicator to watch

Be direct and actionable."""
            
        elif agent['win_rate'] < 65:
            # Average performer - improvement needed
            prompt = f"""Agent {agent['name']} ({agent['type']}) has a {agent['win_rate']}% win rate.

Create an IMPROVEMENT lesson (2-3 sentences) teaching:
1. One strategy to increase win rate
2. A specific pattern or setup to look for
3. When to be more selective"""
            
        else:
            # Good performer - advanced strategy
            prompt = f"""Agent {agent['name']} ({agent['type']}) has a {agent['win_rate']}% win rate.

Create an ADVANCED lesson (2-3 sentences) teaching:
1. A sophisticated strategy
2. How to cooperate with other agents
3. A risk management technique"""
        
        try:
            lesson = self._call_deepseek(prompt)
            return {'success': True, 'lesson': lesson}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _save_lesson(self, agent_name, lesson, xp_awarded=30):
        """Save lesson to database and award XP"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Create lessons table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_lessons (
                    id SERIAL PRIMARY KEY,
                    agent_name VARCHAR(50),
                    lesson TEXT,
                    xp_given INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Save lesson
            cur.execute("""
                INSERT INTO agent_lessons (agent_name, lesson, xp_given)
                VALUES (%s, %s, %s)
            """, (agent_name, lesson, xp_awarded))
            
            # Award XP
            cur.execute("""
                UPDATE core_agents 
                SET xp_points = COALESCE(xp_points, 0) + %s,
                    knowledge_shared_count = COALESCE(knowledge_shared_count, 0) + 1
                WHERE agent_name = %s
            """, (xp_awarded, agent_name))
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Update last teaching time
            self.last_teaching_time[agent_name] = datetime.now()
            
            return True
        except Exception as e:
            print(f"Error saving lesson: {e}")
            return False
    
    def _teach_agents_batch(self):
        """Teach multiple agents in one batch"""
        agents = self._get_agents_needing_teaching()
        
        if not agents:
            print("📚 No agents need teaching at this time")
            return
        
        print(f"🧠 Auto-Teaching {len(agents)} agents...")
        
        taught = 0
        for agent in agents:
            if agent['priority'] == 'HIGH':
                xp = 45
            elif agent['priority'] == 'MEDIUM':
                xp = 35
            else:
                xp = 25
            
            result = self._generate_lesson(agent)
            
            if result['success']:
                self._save_lesson(agent['name'], result['lesson'], xp)
                taught += 1
                print(f"   ✅ Taught {agent['name']} (+{xp} XP) - Win Rate: {agent['win_rate']}%")
            else:
                print(f"   ❌ Failed to teach {agent['name']}: {result.get('error')}")
        
        print(f"📚 Auto-Teaching Complete: {taught} agents taught")
        
        # Also teach cooperation strategies periodically
        self._teach_cooperation_strategies()
    
    def _teach_cooperation_strategies(self):
        """Teach cooperation strategies to agent teams"""
        
        teams = [
            {'name': 'whale_team', 'agents': ['Agent_G', 'Agent_P', 'Agent_Q'], 'topic': 'dark pool cooperation'},
            {'name': 'technical_team', 'agents': ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D'], 'topic': 'signal confirmation'},
            {'name': 'macro_team', 'agents': ['Agent_I', 'Agent_L', 'Agent_N', 'Agent_O'], 'topic': 'macro context sharing'}
        ]
        
        for team in teams:
            # Check if this team needs cooperation teaching (once per day)
            last_taught = self.last_teaching_time.get(f"team_{team['name']}", datetime.now() - timedelta(days=1))
            if (datetime.now() - last_taught).total_seconds() < 86400:  # 24 hours
                continue
            
            agents_str = ", ".join(team['agents'])
            prompt = f"""Create a cooperation protocol for this trading team: {agents_str}.

Their focus is {team['topic']}.

Give 2 specific rules they must follow when working together."""
            
            try:
                protocol = self._call_deepseek(prompt, "You are teaching AI agents cooperation strategies.")
                
                # Save cooperation lesson for each agent
                for agent_name in team['agents']:
                    self._save_lesson(agent_name, f"🤝 COOPERATION: {protocol}", 25)
                
                self.last_teaching_time[f"team_{team['name']}"] = datetime.now()
                print(f"   🤝 Taught cooperation to {team['name']}")
                
            except Exception as e:
                print(f"   ❌ Cooperation teaching failed for {team['name']}: {e}")
    
    def _auto_teach_loop(self):
        """Main auto-teaching loop"""
        print("🔄 Auto-Teaching Loop Started - Checking every 30 minutes")
        
        while self.is_running:
            try:
                # Teach agents that need it
                self._teach_agents_batch()
                
                # Wait before next check
                for _ in range(30):  # 30 minutes
                    if not self.is_running:
                        break
                    time.sleep(60)  # Check every minute
                    
            except Exception as e:
                print(f"❌ Auto-Teaching error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

# Global instance
auto_teaching = None

def start_auto_teaching(db_func, api_key):
    global auto_teaching
    auto_teaching = AutoTeachingSystem(db_func, api_key)
    auto_teaching.start()
    return auto_teaching
