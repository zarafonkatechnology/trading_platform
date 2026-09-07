"""
Complete Agent Chat System - 23 agents talking, learning from DeepSeek
"""

import os
import json
import requests
import threading
import time
import random
from datetime import datetime
from typing import Dict, List, Optional
from flask import jsonify

DB_PATH = 'trading_platform.db'

class AgentChatSystem:
    """Complete chat system with 23 agents and DeepSeek learning"""
    
    def __init__(self, app=None):
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"
        self.deepseek_enabled = bool(self.deepseek_api_key)
        self.app = app
        self.auto_talk_running = False
        self.conversations = []
        
        self._init_database()
        self._start_auto_talk()
        
        if self.deepseek_enabled:
            print("✅ DeepSeek API connected - 23 agents can learn anything")
        else:
            print("⚠️ DeepSeek API not configured - Add DEEPSEEK_API_KEY to .env")
    
    def _init_database(self):
        """Initialize database tables"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_agent TEXT,
                to_agent TEXT,
                message TEXT,
                response TEXT,
                used_deepseek INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                question TEXT,
                answer TEXT,
                source TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_auto_learn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                topic TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized for 23 agents")
    
    def get_all_agents(self) -> List[Dict]:
        """Get all 23 agents"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, agent_type, specialization, xp_points FROM core_agents ORDER BY agent_name")
        rows = cursor.fetchall()
        conn.close()
        
        return [{'name': r[0], 'type': r[1], 'specialization': r[2], 'xp': r[3]} for r in rows]
    
    def get_agent(self, agent_name: str) -> Optional[Dict]:
        """Get single agent info"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, agent_type, specialization, xp_points FROM core_agents WHERE agent_name = ?", (agent_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'name': row[0], 'type': row[1], 'specialization': row[2], 'xp': row[3]}
        return None
    
    def check_known_answer(self, agent_name: str, question: str) -> Optional[str]:
        """Check if agent already knows the answer"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT answer FROM agent_knowledge 
            WHERE agent_name = ? AND question LIKE ?
            ORDER BY learned_at DESC LIMIT 1
        """, (agent_name, f'%{question}%'))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def ask_deepseek(self, agent: Dict, question: str) -> Optional[str]:
        """Ask DeepSeek for an answer"""
        if not self.deepseek_enabled:
            return None
        
        prompt = f"""You are {agent['name']}, a {agent['type']} trading specialist.

User asks: "{question}"

Answer as this agent would. Be helpful, practical, and concise. Focus on actionable trading advice.
Include specific examples or rules if applicable.
Keep response under 200 words.
"""
        
        headers = {
            'Authorization': f'Bearer {self.deepseek_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are a professional trading advisor helping users understand trading concepts.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        try:
            response = requests.post(self.deepseek_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                print(f"🤖 DeepSeek taught {agent['name']}: {question[:50]}...")
                return answer
            else:
                print(f"⚠️ DeepSeek API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️ DeepSeek API call failed: {e}")
            return None
    
    def save_knowledge(self, agent_name: str, question: str, answer: str, source: str = 'deepseek'):
        """Save learned knowledge to database"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_knowledge (agent_name, question, answer, source, learned_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, question, answer, source, datetime.now()))
        
        # Award XP for learning
        cursor.execute("UPDATE core_agents SET xp_points = xp_points + 15 WHERE agent_name = ?", (agent_name,))
        
        conn.commit()
        conn.close()
        print(f"💾 {agent_name} learned: {question[:50]}... (+15 XP)")
    
    def chat_with_agent(self, agent_name: str, user_message: str) -> Dict:
        """User chats with an agent - FORCES database for prices"""
        
        # CRITICAL: For Agent_F, intercept ALL price questions
        if agent_name == 'Agent_F':
            user_lower = user_message.lower()
            
            # Check if asking about ANY price
            price_keywords = ['price', 'gold', 'silver', 'nasdaq', 's&p', 'dow', 
                            'oil', 'brent', 'eurusd', 'gbpusd', 'usdjpy', 
                            'trading at', 'worth', 'how much']
            
            if any(keyword in user_lower for keyword in price_keywords):
                # USE DATABASE - NOT DEEPSEEK!
                try:
                    import psycopg2
                    conn = psycopg2.connect(
                        host="localhost",
                        port=5432,
                        database="trading_platform",
                        user="postgres",
                        password="lama"
                    )
                    cur = conn.cursor()
                    
                    # Get gold price from YOUR database
                    cur.execute("SELECT mid, updated_at FROM price_cache WHERE symbol = 'GOLD' ORDER BY updated_at DESC LIMIT 1")
                    row = cur.fetchone()
                    cur.close()
                    conn.close()
                    
                    if row and row[0] is not None:
                        price = float(row[0])
                        updated = row[1]
                        response = f"Gold is ${price:.2f} per ounce (from database, updated {updated})."
                    else:
                        response = "I don't have gold price data in the database. Please check if MT4 EA is connected."
                    
                    return {
                        'success': True,
                        'agent': agent_name,
                        'response': response,
                        'source': 'database',
                        'used_deepseek': False,
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    return {
                        'success': True,
                        'agent': agent_name,
                        'response': f"Database error: {e}",
                        'source': 'error',
                        'used_deepseek': False,
                        'timestamp': datetime.now().isoformat()
                    }
        
        # For non-price questions, use existing logic
        agent = self.get_agent(agent_name)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        # Check if agent already knows the answer
        known_answer = self.check_known_answer(agent_name, user_message)
        
        if known_answer:
            response = known_answer
            source = 'database'
            used_deepseek = False
        else:
            # Ask DeepSeek
            response = self.ask_deepseek(agent, user_message)
            if response:
                self.save_knowledge(agent_name, user_message, response, 'deepseek')
                source = 'deepseek'
                used_deepseek = True
            else:
                response = self.get_fallback_response(agent, user_message)
                source = 'fallback'
                used_deepseek = False
        
        # Save conversation
        self._save_conversation(agent_name, 'User', user_message, response, used_deepseek)
        
        return {
            'success': True,
            'agent': agent_name,
            'agent_type': agent['type'],
            'user_message': user_message,
            'response': response,
            'source': source,
            'used_deepseek': used_deepseek,
            'timestamp': datetime.now().isoformat()
        }
    
    def agent_to_agent_talk(self, from_agent: str, to_agent: str, topic: str = None) -> Dict:
        """One agent talks to another agent"""
        
        agent1 = self.get_agent(from_agent)
        agent2 = self.get_agent(to_agent)
        
        if not agent1 or not agent2:
            return {'success': False, 'error': 'Agent not found'}
        
        # Generate question based on agent types
        if not topic:
            topic = self._generate_question(agent1, agent2)
        
        # Check if agent2 knows the answer
        known_answer = self.check_known_answer(to_agent, topic)
        
        if known_answer:
            response = known_answer
            source = 'database'
        else:
            response = self.ask_deepseek(agent2, topic)
            if response:
                self.save_knowledge(to_agent, topic, response, 'deepseek')
                source = 'deepseek'
            else:
                response = f"As a {agent2['type']} specialist, I'd need to analyze more data to answer that properly."
                source = 'fallback'
        
        # Save conversation
        self._save_conversation(from_agent, to_agent, topic, response, source == 'deepseek')
        
        return {
            'success': True,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'question': topic,
            'response': response,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_question(self, agent1: Dict, agent2: Dict) -> str:
        """Generate a question for agent to ask another agent"""
        
        questions = [
            f"What's your opinion on the current gold market?",
            f"How do you analyze RSI divergence?",
            f"What's your strategy for breakout trading?",
            f"How do you manage risk in volatile markets?",
            f"What indicators do you trust the most?",
            f"Can you explain your approach to trend following?",
            f"What's your view on Fibonacci levels right now?",
            f"How do you identify whale movements?",
            f"What candlestick patterns do you look for?",
            f"How do you confirm a reversal signal?"
        ]
        
        return random.choice(questions)
    
    def get_fallback_response(self, agent: Dict, question: str) -> str:
        """Fallback response when DeepSeek is unavailable"""
        
        fallbacks = [
            f"As a {agent['type']} specialist, I recommend studying the charts and waiting for confirmation.",
            f"That's an interesting question. Based on my {agent['type']} analysis, I'd suggest looking at multiple timeframes.",
            f"I need more data to give you a precise answer. Can you provide more context about what you're trading?",
            f"Great question! For a {agent['type']} like me, I focus on price action and volume confirmation."
        ]
        
        return random.choice(fallbacks)
    
    def _save_conversation(self, from_agent: str, to_agent: str, message: str, response: str, used_deepseek: bool):
        """Save conversation to database"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_chats (from_agent, to_agent, message, response, used_deepseek, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (from_agent, to_agent, message, response, 1 if used_deepseek else 0, datetime.now()))
        
        conn.commit()
        conn.close()
        
        # Also store in memory for quick access
        self.conversations.insert(0, {
            'from': from_agent,
            'to': to_agent,
            'message': message,
            'response': response,
            'used_deepseek': used_deepseek,
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
        # Keep only last 100
        if len(self.conversations) > 100:
            self.conversations = self.conversations[:100]
    
    def get_conversations(self, limit: int = 50) -> List[Dict]:
        """Get recent conversations"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT from_agent, to_agent, message, response, used_deepseek, created_at
            FROM agent_chats ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                'from': row[0],
                'to': row[1],
                'message': row[2],
                'response': row[3],
                'used_deepseek': bool(row[4]),
                'time': row[5]
            })
        
        return conversations
    
    def _start_auto_talk(self):
        """Start automatic agent-to-agent conversations in background"""
        self.auto_talk_running = True
        
        def auto_talk_loop():
            while self.auto_talk_running:
                try:
                    time.sleep(45)  # Every 45 seconds
                    
                    # Get 23 agents
                    agents = self.get_all_agents()
                    if len(agents) >= 2:
                        # Pick two random agents
                        agent1, agent2 = random.sample(agents, 2)
                        
                        # They have a conversation
                        result = self.agent_to_agent_talk(agent1['name'], agent2['name'])
                        
                        if result['success']:
                            print(f"💬 Auto-talk: {agent1['name']} → {agent2['name']}: {result['question'][:50]}...")
                            
                            # Emit via WebSocket if app has socketio
                            if self.app and hasattr(self.app, 'socketio'):
                                self.app.socketio.emit('new_conversation', {
                                    'from': result['from_agent'],
                                    'to': result['to_agent'],
                                    'message': result['question'],
                                    'response': result['response'],
                                    'time': datetime.now().strftime('%H:%M:%S')
                                })
                
                except Exception as e:
                    print(f"Auto-talk error: {e}")
        
        thread = threading.Thread(target=auto_talk_loop, daemon=True)
        thread.start()
        print("🚀 Auto agent-to-agent talk started (every 45 seconds)")
    
    def stop_auto_talk(self):
        """Stop automatic conversations"""
        self.auto_talk_running = False


# Singleton instance
_chat_system = None

def get_chat_system(app=None):
    global _chat_system
    if _chat_system is None:
        _chat_system = AgentChatSystem(app)
    return _chat_system
