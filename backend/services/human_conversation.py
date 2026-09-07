"""
Complete Agent Chat System - Agents learn from DeepSeek and save knowledge
"""

import os
import json
import sqlite3
import requests
import threading
import time
import random
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = 'trading_platform.db'

class AgentChatSystem:
    """Complete chat system with DeepSeek integration"""
    
    def __init__(self):
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"
        self.deepseek_enabled = bool(self.deepseek_api_key)
        self.auto_talk_running = False
        self.conversation_history = []
        
        self._init_tables()
        self._start_auto_talk()
        
        if self.deepseek_enabled:
            print("✅ DeepSeek API connected - Agents can learn anything")
        else:
            print("⚠️ DeepSeek API not configured - Add DEEPSEEK_API_KEY to .env")
    
    def _init_tables(self):
        """Initialize database tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Learned knowledge table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_learned_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                question TEXT,
                answer TEXT,
                source TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Agent conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_conversations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_agent TEXT,
                to_agent TEXT,
                message TEXT,
                response TEXT,
                used_deepseek INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_all_agents(self) -> List[Dict]:
        """Get all agents from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, agent_type, specialization, xp_points FROM core_agents ORDER BY agent_name")
        rows = cursor.fetchall()
        conn.close()
        
        agents = []
        for row in rows:
            agents.append({
                'name': row[0],
                'type': row[1] or 'Trading Agent',
                'specialization': row[2] or 'General Trading',
                'xp': row[3] or 0
            })
        return agents
    
    def get_agent(self, agent_name: str) -> Optional[Dict]:
        """Get single agent info"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, agent_type, specialization, xp_points FROM core_agents WHERE agent_name = ?", (agent_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'name': row[0],
                'type': row[1] or 'Trading Agent',
                'specialization': row[2] or 'General Trading',
                'xp': row[3] or 0
            }
        return None
    
    def check_known_answer(self, agent_name: str, question: str) -> Optional[str]:
        """Check if agent already knows the answer"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT answer FROM agent_learned_knowledge 
            WHERE agent_name = ? AND question LIKE ?
            ORDER BY learned_at DESC LIMIT 1
        """, (agent_name, f'%{question}%'))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def ask_deepseek(self, agent: Dict, question: str) -> Optional[str]:
        """Ask DeepSeek API for an answer"""
        if not self.deepseek_enabled:
            return self._get_fallback_answer(agent, question)
        
        prompt = f"""You are {agent['name']}, a {agent['type']} specialist.

User asks: "{question}"

Answer as this agent would. Be helpful, practical, and concise. Focus on actionable trading advice.
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
                return self._get_fallback_answer(agent, question)
                
        except Exception as e:
            print(f"⚠️ DeepSeek API call failed: {e}")
            return self._get_fallback_answer(agent, question)
    
    def _get_fallback_answer(self, agent: Dict, question: str) -> str:
        """Fallback answers when DeepSeek is not available"""
        q_lower = question.lower()
        
        if 'rsi' in q_lower:
            return f"📊 RSI (Relative Strength Index) measures momentum from 0-100. Above 70 = overbought (sell signal), below 30 = oversold (buy signal). Look for divergence for stronger signals!"
        
        if 'macd' in q_lower:
            return f"📈 MACD shows trend direction. When MACD line crosses above signal line = bullish. Below = bearish. Histogram shows momentum strength."
        
        if 'bollinger' in q_lower:
            return f"📊 Bollinger Bands show volatility. Price touching upper band = overbought, lower band = oversold. Band squeezes often precede big moves!"
        
        if 'fibonacci' in q_lower:
            return f"📐 Key Fibonacci levels: 0.382, 0.5, 0.618, 0.786. The 0.618 (golden ratio) is most important for support/resistance."
        
        if 'stop loss' in q_lower:
            return f"🛑 Place stop loss 2x ATR below entry for longs. Never risk more than 2% of account on one trade!"
        
        return f"As a {agent['type']} specialist, I recommend studying price action and using multiple timeframes for confirmation. Would you like me to explain any specific concept?"
    
    def save_learned_knowledge(self, agent_name: str, question: str, answer: str):
        """Save learned knowledge to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_learned_knowledge (agent_name, question, answer, source)
            VALUES (?, ?, ?, ?)
        """, (agent_name, question, answer, 'deepseek'))
        
        # Award XP for learning
        cursor.execute("UPDATE core_agents SET xp_points = xp_points + 15 WHERE agent_name = ?", (agent_name,))
        
        conn.commit()
        conn.close()
        print(f"💾 Saved knowledge for {agent_name}: {question[:50]}... (+15 XP)")
    
    def chat_with_agent(self, agent_name: str, user_message: str) -> Dict:
        """Main chat function - checks knowledge, asks DeepSeek if needed"""
        
        agent = self.get_agent(agent_name)
        if not agent:
            return {'success': False, 'error': f'Agent {agent_name} not found'}
        
        # Check if agent already knows the answer
        known_answer = self.check_known_answer(agent_name, user_message)
        
        if known_answer:
            response = known_answer
            used_deepseek = 0
            xp_gained = 0
        else:
            # Ask DeepSeek for new knowledge
            response = self.ask_deepseek(agent, user_message)
            if response:
                self.save_learned_knowledge(agent_name, user_message, response)
                used_deepseek = 1
                xp_gained = 15
            else:
                response = "I'm having trouble connecting to my knowledge base. Please try again later."
                used_deepseek = 0
                xp_gained = 0
        
        # Save conversation
        conversation = {
            'agent': agent_name,
            'user_message': user_message,
            'agent_response': response,
            'used_deepseek': used_deepseek,
            'xp_gained': xp_gained,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.conversation_history.insert(0, conversation)
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_conversations_log (from_agent, to_agent, message, response, used_deepseek)
            VALUES (?, ?, ?, ?, ?)
        """, ('User', agent_name, user_message, response, used_deepseek))
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'response': response,
            'used_deepseek': used_deepseek,
            'xp_gained': xp_gained,
            'agent': agent
        }
    
    def agent_to_agent_talk(self, from_agent: str, to_agent: str, topic: str) -> Dict:
        """Two agents talk to each other"""
        
        from_agent_info = self.get_agent(from_agent)
        to_agent_info = self.get_agent(to_agent)
        
        if not from_agent_info or not to_agent_info:
            return {'success': False, 'error': 'Agent not found'}
        
        # First agent asks question
        question = f"As a {from_agent_info['type']} specialist, I'd like to ask about: {topic}. What's your perspective?"
        
        # Second agent answers
        answer = self.ask_deepseek(to_agent_info, question)
        
        if not answer:
            answer = f"As a {to_agent_info['type']} specialist, I believe this requires careful analysis of current market conditions."
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_conversations_log (from_agent, to_agent, message, response, used_deepseek)
            VALUES (?, ?, ?, ?, ?)
        """, (from_agent, to_agent, question, answer, 1))
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'question': question,
            'answer': answer
        }
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history[:limit]
    
    def get_learned_knowledge(self, agent_name: str = None) -> List[Dict]:
        """Get all learned knowledge"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if agent_name:
            cursor.execute("SELECT agent_name, question, answer, learned_at FROM agent_learned_knowledge WHERE agent_name = ? ORDER BY learned_at DESC", (agent_name,))
        else:
            cursor.execute("SELECT agent_name, question, answer, learned_at FROM agent_learned_knowledge ORDER BY learned_at DESC")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'agent': r[0], 'question': r[1], 'answer': r[2], 'learned_at': r[3]} for r in rows]
    
    def _start_auto_talk(self):
        """Start automatic agent conversations in background"""
        def auto_talk_loop():
            self.auto_talk_running = True
            while self.auto_talk_running:
                time.sleep(45)  # Every 45 seconds
                
                agents = self.get_all_agents()
                if len(agents) >= 2:
                    agent1, agent2 = random.sample(agents, 2)
                    topics = ['market trend', 'trading strategy', 'risk management', 'price action', 'technical indicators']
                    topic = random.choice(topics)
                    
                    result = self.agent_to_agent_talk(agent1['name'], agent2['name'], topic)
                    if result['success']:
                        print(f"💬 Auto talk: {agent1['name']} → {agent2['name']} about {topic}")
        
        thread = threading.Thread(target=auto_talk_loop, daemon=True)
        thread.start()
        print("🔄 Auto agent conversations started (every 45 seconds)")


# Singleton
_chat_system = None

def get_chat_system():
    global _chat_system
    if _chat_system is None:
        _chat_system = AgentChatSystem()
    return _chat_system
