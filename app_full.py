#!/usr/bin/env python3
"""
COMPLETE 5-AGENT TRADING PLATFORM WITH POSTGRESQL
- Integrated with Platform 2 (same database)
- Full reward system (XP, Tokens, Levels, Achievements)
- Agent conversations and knowledge sharing
- Agents added in Platform 2 appear automatically
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import psycopg2
import psycopg2.extras
import json
import random
import time
import threading
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
import os, json, threading, time, logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from backend.agents.agent_manager import AgentManager
from backend.core.supervisor import Supervisor
from backend.services.price_service import get_price_service
from backend.agents import agent_manager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-platform-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

agent_manager = AgentManager()
supervisor = Supervisor()
price_service = get_price_service()
price_service.start()

# ============================================================================
# POSTGRESQL CONNECTION (Same as Platform 2)
# ============================================================================

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'trading_platform')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'lama')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ============================================================================
# REWARD CONFIGURATION
# ============================================================================

REWARD_CONFIG = {
    'xp': {
        'teach_agent': 50,
        'learn_from_user': 100,
        'share_knowledge': 30,
        'receive_knowledge': 20,
        'conversation': 5,
        'help_user': 25,
        'level_up_bonus': 200,
    },
    'tokens': {
        'teach_agent': 10,
        'learn_from_user': 20,
        'share_knowledge': 5,
        'help_user': 8,
    },
    'levels': {
        1: ('Novice', 0, '🌱'),
        2: ('Apprentice', 100, '📘'),
        3: ('Scholar', 300, '📚'),
        4: ('Expert', 600, '⭐'),
        5: ('Master', 1000, '🏆'),
        6: ('Grandmaster', 1500, '👑'),
        7: ('Legend', 2100, '🌟'),
        8: ('Mythic', 2800, '⚡'),
        9: ('Transcendent', 3600, '💎'),
        10: ('Omniscient', 5000, '🔮'),
    }
}

ACHIEVEMENTS = {
    'first_lesson': {'name': 'First Steps', 'desc': 'Learn first knowledge', 'icon': '📖', 'reward_xp': 50, 'reward_tokens': 20},
    'knowledge_seeker': {'name': 'Knowledge Seeker', 'desc': 'Learn 10 pieces', 'icon': '🔍', 'reward_xp': 100, 'reward_tokens': 50},
    'social_butterfly': {'name': 'Social Butterfly', 'desc': '20 conversations', 'icon': '🦋', 'reward_xp': 100, 'reward_tokens': 50},
    'helpful_expert': {'name': 'Helpful Expert', 'desc': 'Help users 10 times', 'icon': '🤝', 'reward_xp': 150, 'reward_tokens': 75},
    'eager_student': {'name': 'Eager Student', 'desc': 'Taught 10 times', 'icon': '🎓', 'reward_xp': 150, 'reward_tokens': 75},
    'master_level': {'name': 'Master Level', 'desc': 'Reach Level 5', 'icon': '🏆', 'reward_xp': 300, 'reward_tokens': 150},
}

# ============================================================================
# AGENT DATA CACHE (Loaded from PostgreSQL)
# ============================================================================


class AgentCache:
    def __init__(self):
        self.agents = {}
        self.conversations = []
        self.load_from_db()
    
    def load_from_db(self):
        """Load all agents from PostgreSQL (including those added via Platform 2)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get all agents from core_agents table
            cur.execute('''
        CREATE TABLE IF NOT EXISTS core_agents (
           id SERIAL PRIMARY KEY,
           agent_name VARCHAR(20) UNIQUE,
           agent_type VARCHAR(30),
           specialization VARCHAR(50),
           xp_points INTEGER DEFAULT 0,
           token_balance INTEGER DEFAULT 1000,
           trust_weight DECIMAL(5,4) DEFAULT 0.2,
           total_votes INTEGER DEFAULT 0,
           correct_votes INTEGER DEFAULT 0,
           vote_accuracy DECIMAL(5,2) DEFAULT 0,
           knowledge_shared_count INTEGER DEFAULT 0,
           achievements_count INTEGER DEFAULT 0,
           is_active BOOLEAN DEFAULT TRUE,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
            rows = cur.fetchall()
            
            for row in rows:
                name = row['agent_name']
                agent_type = row['agent_type']
                
                # Build agent data structure
                self.agents[name] = {
                    'category': agent_type or 'Trading Agent',
                    'description': f'Specialized in {agent_type} trading strategies.',
                    'expertise': self._get_expertise_for_type(agent_type),
                    'knowledge': self._get_default_knowledge(name, agent_type),
                    'learned': {},
                    'conversations': [],
                    'stats': {
                        'xp': row['xp_points'] or 0,
                        'level': self._calculate_level(row['xp_points'] or 0),
                        'tokens': row['token_balance'] or 1000,
                        'knowledge_learned': 0,
                        'knowledge_shared': 0,
                        'conversations': 0,
                        'times_taught': 0,
                        'helped_users': 0,
                        'learned_from_agents': [],
                        'knowledge_categories': [agent_type] if agent_type else [],
                        'achievements': [],
                        'badges': [],
                        'satisfaction': 50,
                        'reputation': 10,
                    },
                    'reward_history': []
                }
            
            cur.close()
            conn.close()
            print(f"✅ Loaded {len(self.agents)} agents from PostgreSQL")
            return True
        except Exception as e:
            print(f"❌ Error loading from PostgreSQL: {e}")
            return False
    
    def _calculate_level(self, xp):
        for level, (_, threshold, _) in REWARD_CONFIG['levels'].items():
            if xp < threshold:
                return level - 1
        return len(REWARD_CONFIG['levels'])
    
    def _get_expertise_for_type(self, agent_type):
        expertise_map = {
            'Trend Follower': ['Moving Averages', 'Trend Lines', 'MACD', 'Golden Cross', 'Death Cross'],
            'Mean Reversion': ['RSI', 'Bollinger Bands', 'Support/Resistance', 'Overbought/Oversold'],
            'Momentum': ['Price Rate of Change', 'ROC', 'RSI Slope', 'Momentum Divergence'],
            'Volatility': ['ATR', 'Volatility', 'Bollinger Width', 'Risk Assessment'],
            'Microstructure': ['Order Flow', 'Volume Profile', 'VWAP', 'Bid/Ask Spread'],
            'Demo Agent': ['General Trading', 'Market Analysis', 'Risk Management'],
        }
        return expertise_map.get(agent_type, ['Technical Analysis', 'Market Trends', 'Risk Management'])
    
    def _get_default_knowledge(self, name, agent_type):
        knowledge_map = {
            'Trend Follower': {
                'Golden Cross': {'desc': '50MA crosses above 200MA - Strong bullish signal', 'source': 'initial'},
                'Death Cross': {'desc': '50MA crosses below 200MA - Strong bearish signal', 'source': 'initial'},
            },
            'Mean Reversion': {
                'RSI': {'desc': 'RSI below 30 = oversold (buy), above 70 = overbought (sell)', 'source': 'initial'},
                'Bollinger Bands': {'desc': 'Price at lower band = oversold, upper band = overbought', 'source': 'initial'},
            },
            'Momentum': {
                'ROC': {'desc': 'Rate of Change measures price acceleration', 'source': 'initial'},
                'RSI Slope': {'desc': 'RSI turning up = bullish, turning down = bearish', 'source': 'initial'},
            },
            'Volatility': {
                'ATR': {'desc': 'Average True Range measures volatility', 'source': 'initial'},
                'Bollinger Squeeze': {'desc': 'Narrow bands indicate potential breakout', 'source': 'initial'},
            },
            'Microstructure': {
                'VWAP': {'desc': 'Volume Weighted Average Price - institutional benchmark', 'source': 'initial'},
                'Volume Profile': {'desc': 'High Volume Node = support/resistance', 'source': 'initial'},
            },
        }
        return knowledge_map.get(agent_type, {'General': {'desc': 'Trading knowledge', 'source': 'initial'}})
    
    def save_to_db(self):
        """Save agent stats back to PostgreSQL"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            for name, agent in self.agents.items():
                cur.execute('''
                    UPDATE core_agents 
                    SET xp_points = %s, token_balance = %s
                    WHERE agent_name = %s
                ''', (agent['stats']['xp'], agent['stats']['tokens'], name))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving to DB: {e}")
            return False
    
    def sync_with_db(self):
        """Sync - reload agents from database"""
        self.load_from_db()
    
    def get_agent(self, name):
        return self.agents.get(name)
    
    def get_all_agents(self):
        return self.agents
    
    def update_agent_stats(self, name, stats):
        if name in self.agents:
            self.agents[name]['stats'].update(stats)
            self.save_to_db()

# ============================================================================
# REWARD FUNCTIONS
# ============================================================================

def get_level_info(level):
    return REWARD_CONFIG['levels'].get(level, REWARD_CONFIG['levels'][1])

def award_xp(agent_name, action_type, bonus=0):
    agent = agent_cache.get_agent(agent_name)
    if not agent:
        return None
    
    base_xp = REWARD_CONFIG['xp'].get(action_type, 5)
    total_xp = base_xp + bonus
    agent['stats']['xp'] += total_xp
    
    # Check level up
    current_level = agent['stats']['level']
    while current_level + 1 in REWARD_CONFIG['levels']:
        next_threshold = REWARD_CONFIG['levels'][current_level + 1][1]
        if agent['stats']['xp'] >= next_threshold:
            agent['stats']['level'] += 1
            level_name, _, icon = get_level_info(agent['stats']['level'])
            agent['stats']['xp'] += REWARD_CONFIG['xp']['level_up_bonus']
            agent['stats']['tokens'] += 50
            agent['stats']['satisfaction'] = min(100, agent['stats']['satisfaction'] + 10)
            
            socketio.emit('level_up', {
                'agent': agent_name,
                'level': agent['stats']['level'],
                'level_name': level_name,
                'icon': icon,
                'message': f'🎉 {agent_name} reached Level {agent["stats"]["level"]} - {icon} {level_name}!'
            })
        else:
            break
    
    agent_cache.save_to_db()
    return {'xp_awarded': total_xp, 'total_xp': agent['stats']['xp']}

def award_tokens(agent_name, action_type, bonus=0):
    agent = agent_cache.get_agent(agent_name)
    if not agent:
        return None
    
    base_tokens = REWARD_CONFIG['tokens'].get(action_type, 1)
    total_tokens = base_tokens + bonus
    agent['stats']['tokens'] += total_tokens
    agent_cache.save_to_db()
    return {'tokens_awarded': total_tokens, 'total_tokens': agent['stats']['tokens']}

def check_achievements(agent_name):
    agent = agent_cache.get_agent(agent_name)
    if not agent:
        return []
    
    stats = agent['stats']
    new_achievements = []
    
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id in stats['achievements']:
            continue
        
        earned = False
        if ach_id == 'first_lesson' and stats['knowledge_learned'] >= 1:
            earned = True
        elif ach_id == 'knowledge_seeker' and stats['knowledge_learned'] >= 10:
            earned = True
        elif ach_id == 'social_butterfly' and stats['conversations'] >= 20:
            earned = True
        elif ach_id == 'helpful_expert' and stats['helped_users'] >= 10:
            earned = True
        elif ach_id == 'eager_student' and stats['times_taught'] >= 10:
            earned = True
        elif ach_id == 'master_level' and stats['level'] >= 5:
            earned = True
        
        if earned:
            stats['achievements'].append(ach_id)
            stats['xp'] += ach['reward_xp']
            stats['tokens'] += ach['reward_tokens']
            new_achievements.append(ach)
            
            socketio.emit('achievement_unlocked', {
                'agent': agent_name,
                'achievement': ach
            })
    
    if new_achievements:
        agent_cache.save_to_db()
    return new_achievements

# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def generate_agent_message(speaker, listener):
    speaker_info = agent_cache.get_agent(speaker)
    listener_info = agent_cache.get_agent(listener)
    
    if not speaker_info or not listener_info:
        return "Hello!"
    
    messages = [
        f"Hey {listener}, I've been analyzing the market. What's your perspective?",
        f"{listener}, my indicators are showing strong signals. Have you noticed?",
        f"Interesting price action today, {listener}. How does this align with your analysis?",
        f"Quick question {listener}: What's your take on current market conditions?",
        f"{listener}, let's collaborate! I'm seeing potential opportunities.",
    ]
    
    if speaker_info.get('learned') and random.random() > 0.7:
        topic = random.choice(list(speaker_info['learned'].keys()))
        return f"{listener}, I recently learned about {topic}. Want me to share?"
    
    return random.choice(messages)

def share_knowledge(speaker, listener):
    speaker_info = agent_cache.get_agent(speaker)
    listener_info = agent_cache.get_agent(listener)
    
    if not speaker_info or not listener_info:
        return None
    
    all_knowledge = {**speaker_info.get('knowledge', {}), **speaker_info.get('learned', {})}
    if not all_knowledge:
        return None
    
    key = random.choice(list(all_knowledge.keys()))
    value = all_knowledge[key]
    content = value.get('desc', str(value))
    
    if 'learned' not in listener_info:
        listener_info['learned'] = {}
    listener_info['learned'][f"from_{speaker}_{key}"] = {
        'desc': content,
        'source': speaker,
        'timestamp': datetime.now().isoformat()
    }
    
    award_xp(speaker, 'share_knowledge')
    award_tokens(speaker, 'share_knowledge')
    speaker_info['stats']['knowledge_shared'] += 1
    
    award_xp(listener, 'receive_knowledge')
    listener_info['stats']['knowledge_learned'] += 1
    
    if speaker not in listener_info['stats']['learned_from_agents']:
        listener_info['stats']['learned_from_agents'].append(speaker)
    
    check_achievements(speaker)
    check_achievements(listener)
    agent_cache.save_to_db()
    
    return {'topic': key, 'content': content}

def teach_agent(agent_name, topic, content):
    agent = agent_cache.get_agent(agent_name)
    if not agent:
        return {'success': False, 'error': 'Agent not found'}
    
    key = topic.replace(' ', '_')
    if 'learned' not in agent:
        agent['learned'] = {}
    agent['learned'][key] = {'desc': content, 'source': 'User', 'timestamp': datetime.now().isoformat()}
    
    xp_result = award_xp(agent_name, 'learn_from_user')
    token_result = award_tokens(agent_name, 'learn_from_user')
    agent['stats']['knowledge_learned'] += 1
    agent['stats']['times_taught'] += 1
    agent['stats']['satisfaction'] = min(100, agent['stats']['satisfaction'] + 10)
    
    new_achievements = check_achievements(agent_name)
    
    level_info = get_level_info(agent['stats']['level'])
    response = f"✅ Thank you for teaching me about {topic}! +{xp_result['xp_awarded'] if xp_result else 0} XP, +{token_result['tokens_awarded'] if token_result else 0} Tokens"
    if new_achievements:
        response += f"\n🏆 Achievement Unlocked: {new_achievements[0]['name']}!"
    
    agent_cache.save_to_db()
    return {'success': True, 'message': response}

def talk_to_agent(agent_name, message):
    agent = agent_cache.get_agent(agent_name)
    if not agent:
        return f"Agent {agent_name} not found."
    
    msg_lower = message.lower()
    
    # Check for teaching intent
    if 'teach' in msg_lower or 'learn' in msg_lower:
        if ':' in message:
            parts = message.split(':', 1)
            topic = parts[0].replace('teach', '').replace('learn', '').replace('about', '').strip()
            content = parts[1].strip()
        else:
            topic = message.replace('teach', '').replace('learn', '').replace('about', '').strip()
            content = f"User wants to discuss {topic}"
        
        if topic:
            result = teach_agent(agent_name, topic, content)
            return result['message']
    
    # Check for knowledge query
    all_knowledge = {**agent.get('knowledge', {}), **agent.get('learned', {})}
    for key, value in all_knowledge.items():
        if key.lower() in msg_lower:
            content = value.get('desc', str(value))
            award_xp(agent_name, 'help_user')
            award_tokens(agent_name, 'help_user')
            agent['stats']['helped_users'] += 1
            check_achievements(agent_name)
            agent_cache.save_to_db()
            return f"📚 Regarding {key}: {content}"
    
    # Check expertise
    for exp in agent.get('expertise', []):
        if exp.lower() in msg_lower:
            award_xp(agent_name, 'help_user')
            agent['stats']['helped_users'] += 1
            agent_cache.save_to_db()
            return f"🔍 As an expert in {exp}, {agent.get('description', '')[:100]}"
    
    # Default response
    award_xp(agent_name, 'conversation')
    agent['stats']['conversations'] += 1
    check_achievements(agent_name)
    agent_cache.save_to_db()
    
    return f"I'm {agent_name}, specialized in {agent.get('category', 'trading')}. How can I help you?"

# ============================================================================
# BACKGROUND CONVERSATIONS
# ============================================================================

conversation_history = []

def run_conversations():
    while True:
        try:
            agents = list(agent_cache.get_all_agents().keys())
            if len(agents) >= 2:
                speaker = random.choice(agents)
                listener = random.choice([a for a in agents if a != speaker])
                message = generate_agent_message(speaker, listener)
                
                conv = {
                    'timestamp': datetime.now().isoformat(),
                    'speaker': speaker,
                    'listener': listener,
                    'message': message,
                    'type': 'agent_to_agent'
                }
                conversation_history.append(conv)
                
                if len(conversation_history) > 100:
                    conversation_history.pop(0)
                
                socketio.emit('agent_conversation', conv)
                
                if random.random() > 0.7:
                    share = share_knowledge(speaker, listener)
                    if share:
                        share_conv = {
                            'timestamp': datetime.now().isoformat(),
                            'speaker': speaker,
                            'listener': listener,
                            'message': f"📚 Shared knowledge about {share['topic']}",
                            'type': 'knowledge_share'
                        }
                        conversation_history.append(share_conv)
                        socketio.emit('agent_conversation', share_conv)
            
            time.sleep(random.uniform(15, 30))
        except Exception as e:
            print(f"Conversation error: {e}")
            time.sleep(10)

def auto_sync():
    """Periodically sync with database to pick up new agents from Platform 2"""
    while True:
        time.sleep(60)  # Check every minute
        agent_cache.sync_with_db()
        print(f"🔄 Synced with database. Total agents: {len(agent_cache.get_all_agents())}")

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('dashboard_fixed.html', agents=agent_cache.get_all_agents(), total=len(agent_cache.get_all_agents()))

@app.route('/api/agents')
def api_agents():
    agents_list = []
    for name, info in agent_cache.get_all_agents().items():
        agents_list.append({
            'name': name,
            'category': info.get('category', 'Trading Agent'),
            'description': info.get('description', ''),
            'expertise': info.get('expertise', []),
            'knowledge_count': len(info.get('knowledge', {})) + len(info.get('learned', {})),
            'level': info['stats']['level'],
            'xp': info['stats']['xp'],
            'tokens': info['stats']['tokens'],
            'satisfaction': info['stats']['satisfaction']
        })
    return jsonify(agents_list)


@app.route('/api/reload_agents')
def api_reload_agents():
    """Reload agents from database (for sync with Platform 2)"""
    agent_manager._load_all_agents()   # reload from DB
    return jsonify({'success': True, 'message': 'Agents reloaded'})

@app.route('/api/stats')
def api_stats():
    agents = agent_cache.get_all_agents()
    total_xp = sum(info['stats']['xp'] for info in agents.values())
    total_tokens = sum(info['stats']['tokens'] for info in agents.values())
    total_achievements = sum(len(info['stats']['achievements']) for info in agents.values())
    
    return jsonify({
        'total_agents': len(agents),
        'total_xp': total_xp,
        'total_tokens': total_tokens,
        'total_achievements': total_achievements,
        'conversations': len(conversation_history)
    })

@app.route('/api/agent/<name>')
def api_agent(name):
    info = agent_cache.get_agent(name)
    if not info:
        return jsonify({'error': 'Agent not found'}), 404
    
    all_knowledge = {}
    for key, value in info.get('knowledge', {}).items():
        all_knowledge[key] = {'content': value.get('desc', str(value)), 'source': 'initial'}
    for key, value in info.get('learned', {}).items():
        all_knowledge[key] = {'content': value.get('desc', str(value)), 'source': value.get('source', 'learned')}
    
    level_info = get_level_info(info['stats']['level'])
    
    return jsonify({
        'name': name,
        'category': info.get('category', 'Trading Agent'),
        'description': info.get('description', ''),
        'expertise': info.get('expertise', []),
        'knowledge': all_knowledge,
        'level': info['stats']['level'],
        'level_name': level_info[0],
        'level_icon': level_info[2],
        'xp': info['stats']['xp'],
        'tokens': info['stats']['tokens'],
        'satisfaction': info['stats']['satisfaction'],
        'reputation': info['stats']['reputation'],
        'achievements': info['stats']['achievements'],
        'badges': info['stats']['badges'],
        'stats': {
            'knowledge_learned': info['stats']['knowledge_learned'],
            'knowledge_shared': info['stats']['knowledge_shared'],
            'conversations': info['stats']['conversations'],
            'times_taught': info['stats']['times_taught'],
            'helped_users': info['stats']['helped_users']
        }
    })

@app.route('/api/talk', methods=['POST'])
def api_talk():
    data = request.json
    agent_name = data.get('agent')
    message = data.get('message', '')
    
    response = talk_to_agent(agent_name, message)
    
    conversation_history.append({
        'timestamp': datetime.now().isoformat(),
        'speaker': 'User',
        'listener': agent_name,
        'message': message,
        'type': 'user_to_agent'
    })
    conversation_history.append({
        'timestamp': datetime.now().isoformat(),
        'speaker': agent_name,
        'listener': 'User',
        'message': response[:200],
        'type': 'agent_to_user'
    })
    
    return jsonify({'response': response, 'agent': agent_name})

@app.route('/api/teach', methods=['POST'])
def api_teach():
    data = request.json
    agent_name = data.get('agent')
    topic = data.get('topic', '')
    content = data.get('content', '')
    
    if not agent_name or not topic:
        return jsonify({'error': 'Agent and topic required'}), 400
    
    result = teach_agent(agent_name, topic, content)
    socketio.emit('teaching_event', {'agent': agent_name, 'topic': topic})
    return jsonify(result)

@app.route('/api/teach_all', methods=['POST'])
def api_teach_all():
    data = request.json
    topic = data.get('topic', '')
    content = data.get('content', '')
    
    if not topic:
        return jsonify({'error': 'Topic required'}), 400
    
    results = []
    for name in agent_cache.get_all_agents():
        result = teach_agent(name, topic, content)
        results.append(result)
    
    socketio.emit('broadcast_teaching', {'topic': topic, 'count': len(agent_cache.get_all_agents())})
    return jsonify({'success': True, 'count': len(results), 'message': f'Taught all {len(results)} agents!'})

@app.route('/api/conversations')
def api_conversations():
    return jsonify(conversation_history[-50:])


@app.route('/api/leaderboard')
def api_leaderboard():
    leaderboard = []
    for name, info in agent_cache.get_all_agents().items():
        level_info = get_level_info(info['stats']['level'])
        leaderboard.append({
            'name': name,
            'category': info.get('category', 'Trading Agent'),
            'level': info['stats']['level'],
            'level_name': level_info[0],
            'icon': level_info[2],
            'xp': info['stats']['xp'],
            'tokens': info['stats']['tokens'],
            'achievements': len(info['stats']['achievements'])
        })
    leaderboard.sort(key=lambda x: x['xp'], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
    return jsonify(leaderboard)

@app.route('/api/sync')
def api_sync():
    """Force sync with database - picks up new agents from Platform 2"""
    agent_cache.sync_with_db()
    return jsonify({'success': True, 'total_agents': len(agent_cache.get_all_agents())})

# ============================================================================
# CREATE HTML TEMPLATE
# ============================================================================

templates_dir = Path(__file__).parent / 'templates'
templates_dir.mkdir(exist_ok=True)

html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Trading Agent Platform - Full System</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); min-height: 100vh; color: #e0e0e0; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; }
        .header h1 { color: #ffd700; }
        .stats { display: flex; justify-content: center; gap: 20px; margin-top: 15px; flex-wrap: wrap; }
        .stat-box { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 10px 20px; text-align: center; }
        .stat-number { font-size: 28px; font-weight: bold; color: #ffd700; }
        .main { display: grid; grid-template-columns: 280px 1fr 340px; gap: 20px; height: calc(100vh - 200px); }
        .panel { background: rgba(0,0,0,0.3); border-radius: 15px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }
        .panel-header { padding: 15px; background: rgba(0,0,0,0.3); border-bottom: 1px solid rgba(255,255,255,0.1); color: #ffd700; font-weight: bold; }
        .agent-list { flex: 1; overflow-y: auto; padding: 10px; }
        .agent-card { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s; border-left: 3px solid transparent; }
        .agent-card:hover { background: rgba(255,255,255,0.1); transform: translateX(3px); }
        .agent-card.selected { border-left-color: #ffd700; background: rgba(255,215,0,0.1); }
        .agent-card.talking { animation: pulse 1s infinite; }
        @keyframes pulse { 0%,100% { box-shadow: 0 0 5px rgba(0,255,0,0.3); } 50% { box-shadow: 0 0 15px rgba(0,255,0,0.6); } }
        .agent-name { font-weight: bold; }
        .agent-category { font-size: 11px; opacity: 0.7; margin-top: 3px; }
        .conversation-messages { flex: 1; overflow-y: auto; padding: 15px; }
        .message { margin-bottom: 12px; animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message-meta { font-size: 10px; opacity: 0.5; margin-bottom: 4px; }
        .message-speaker { color: #ffd700; }
        .message-text { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 10px 14px; display: inline-block; max-width: 90%; }
        .agent-to-agent .message-text { background: linear-gradient(135deg, rgba(42,82,152,0.4), rgba(30,60,114,0.4)); border-left: 3px solid #00ff00; }
        .user-to-agent .message-text { background: rgba(0,200,0,0.2); border-left: 3px solid #00ff00; }
        .agent-to-user .message-text { background: rgba(100,100,200,0.2); border-left: 3px solid #00ffff; }
        .action-buttons { padding: 10px; display: flex; gap: 10px; border-top: 1px solid rgba(255,255,255,0.1); }
        .action-btn { padding: 6px 12px; border: none; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: bold; background: #ffd700; color: #0a0e27; }
        .chat-area { padding: 15px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 10px; }
        .chat-area input { flex: 1; padding: 10px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; }
        .chat-area button { padding: 10px 20px; background: #ffd700; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .info-content { flex: 1; overflow-y: auto; padding: 15px; }
        .info-section { margin-bottom: 20px; }
        .info-section h4 { color: #ffd700; font-size: 13px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; }
        .expertise-tag { display: inline-block; background: rgba(0,255,0,0.15); padding: 4px 10px; border-radius: 15px; font-size: 10px; margin: 3px; }
        .reward-stat { background: rgba(255,215,0,0.1); border-radius: 8px; padding: 8px; text-align: center; margin-bottom: 10px; }
        .reward-stat-value { font-size: 20px; font-weight: bold; color: #ffd700; }
        .level-bar { background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px; overflow: hidden; margin: 10px 0; position: relative; }
        .level-progress { background: linear-gradient(90deg, #ffd700, #ffaa00); height: 100%; transition: width 0.5s; }
        .level-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 10px; font-weight: bold; color: #000; }
        input, textarea { width: 100%; padding: 8px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; color: #fff; margin-bottom: 10px; }
        .form-btn { width: 100%; padding: 8px; background: #ffd700; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 5px; }
        .form-btn.broadcast { background: linear-gradient(135deg, #ff0066, #cc0055); color: #fff; }
        .notification { position: fixed; top: 20px; right: 20px; background: #ffd700; color: #0a0e27; padding: 12px 20px; border-radius: 10px; animation: slideIn 0.3s; z-index: 1000; }
        @keyframes slideIn { from { transform: translateX(400px); } to { transform: translateX(0); } }
        .sync-btn { background: #2196f3; color: white; }
        @media (max-width: 1000px) { .main { grid-template-columns: 1fr; gap: 10px; height: auto; } .agent-list { max-height: 200px; } .conversation-messages { max-height: 300px; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 Trading Agent Platform - Full System</h1>
        <p>Agents added in Platform 2 appear here automatically | Teach, Earn Rewards, Unlock Achievements!</p>
        <div class="stats">
            <div class="stat-box"><div class="stat-number" id="total-agents">{{ total }}</div><div class="stat-label">Agents</div></div>
            <div class="stat-box"><div class="stat-number" id="total-xp">0</div><div class="stat-label">Total XP</div></div>
            <div class="stat-box"><div class="stat-number" id="total-tokens">0</div><div class="stat-label">Total Tokens</div></div>
            <div class="stat-box"><div class="stat-number" id="total-achievements">0</div><div class="stat-label">Achievements</div></div>
        </div>
    </div>
    <div class="main">
        <div class="panel">
            <div class="panel-header">🤖 Agents <button onclick="syncWithDB()" style="float:right; background:#2196f3; border:none; padding:2px 8px; border-radius:4px; cursor:pointer;">🔄 Sync</button></div>
            <div class="agent-list" id="agent-list">
                {% for name, info in agents.items() %}
                <div class="agent-card" onclick="selectAgent('{{ name }}')" data-agent="{{ name }}">
                    <div class="agent-name">{{ name }}</div>
                    <div class="agent-category">{{ info.category }}</div>
                    <div class="agent-category">Lv.{{ info.stats.level }} | 💰 {{ info.stats.tokens }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">💬 Conversations & Knowledge Exchange</div>
            <div class="conversation-messages" id="messages">
                <div class="message"><div class="message-text">✨ Welcome! Click on an agent to start talking. Agents added in Platform 2 appear automatically.</div></div>
            </div>
            <div class="action-buttons">
                <button class="action-btn" onclick="forceConversation()">💬 Force Talk</button>
                <button class="action-btn" onclick="forceShare()">📚 Force Share</button>
                <button class="action-btn" onclick="showLeaderboard()">🏆 Leaderboard</button>
                <button class="action-btn" onclick="clearMessages()">🗑️ Clear</button>
                <button class="action-btn sync-btn" onclick="syncWithDB()">🔄 Sync DB</button>
            </div>
            <div class="chat-area">
                <input type="text" id="chat-input" placeholder="Talk to selected agent..." disabled>
                <button onclick="sendMessage()" id="send-btn" disabled>Send</button>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">📋 Agent Details & Teaching</div>
            <div class="info-content" id="info-content">
                <div class="info-section"><h4>Select an Agent</h4><p>Click on any agent to see their details, teach them, and earn rewards!</p><button class="form-btn" onclick="syncWithDB()">🔄 Sync with Database</button></div>
            </div>
        </div>
    </div>
</div>
<script>
    let socket = io();
    let currentAgent = null;
    let allAgents = [];

    socket.on('agent_conversation', data => {
        addMessage(data.speaker, data.listener, data.message, data.type);
        highlightAgent(data.speaker);
        setTimeout(() => unhighlightAgent(data.speaker), 2000);
        updateStats();
    });
    socket.on('level_up', data => { addMessage('System', data.agent, data.message, 'agent_to_user'); showNotification(data.message); updateStats(); if(currentAgent===data.agent) selectAgent(data.agent); });
    socket.on('achievement_unlocked', data => { addMessage('System', data.agent, `🏆 Achievement: ${data.achievement.name}!`, 'reward'); showNotification(`${data.agent} unlocked ${data.achievement.name}!`); updateStats(); });
    socket.on('teaching_event', data => { addMessage('User', data.agent, `📚 Taught about ${data.topic}`, 'user_to_agent'); updateStats(); });
    socket.on('broadcast_teaching', data => { addMessage('System', 'ALL', `📢 Broadcast: Taught all ${data.count} agents`, 'broadcast'); updateStats(); });

    function highlightAgent(name) { const card = document.querySelector(`[data-agent="${name}"]`); if(card) card.classList.add('talking'); }
    function unhighlightAgent(name) { const card = document.querySelector(`[data-agent="${name}"]`); if(card) card.classList.remove('talking'); }
    
    function addMessage(speaker, listener, message, type, skipScroll=false) {
        const container = document.getElementById('messages');
        const time = new Date().toLocaleTimeString();
        const html = `<div class="message ${type}"><div class="message-meta"><span class="message-speaker">${escapeHtml(speaker)}</span> → ${escapeHtml(listener)} at ${time}</div><div class="message-text">${escapeHtml(message)}</div></div>`;
        container.insertAdjacentHTML('beforeend', html);
        if(!skipScroll) container.scrollTop = container.scrollHeight;
    }

<button onclick="syncAgents()">🔄 Sync with Database</button>
// Auto-sync with Platform 2 every 10 seconds
function syncWithPlatform2() {
    fetch('/api/reload_agents', {method: 'POST'})
        .then(() => fetch('/api/agents'))
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateAgentList(data.agents);
                updateStats(data.agents);
            }
        });
}

// Run every 10 seconds
setInterval(syncWithPlatform2, 10000);

// Also sync after any action (teach, vote)
function afterAction() {
    syncWithPlatform2();
}

    async function selectAgent(name) {
        currentAgent = name;
        document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
        document.querySelector(`[data-agent="${name}"]`).classList.add('selected');
        document.getElementById('chat-input').disabled = false;
        document.getElementById('send-btn').disabled = false;
        try {
            const res = await fetch(`/api/agent/${name}`);
            const agent = await res.json();
            let html = `<div class="info-section"><h4>${agent.name} - Lv.${agent.level} ${agent.level_icon}</h4><p>${agent.description}</p><div class="reward-stat"><div class="reward-stat-value">${agent.xp} XP</div><div>💰 ${agent.tokens} Tokens</div><div>😊 ${agent.satisfaction}% Satisfaction</div></div><div class="level-bar"><div class="level-progress" style="width:${Math.min(100, (agent.xp%1000)/10)}%"></div><div class="level-text">Level ${agent.level} → ${agent.level+1}</div></div></div>`;
            if(agent.badges && agent.badges.length) { html += `<div class="info-section"><h4>🏅 Badges</h4>`; agent.badges.forEach(b => html += `<span class="badge">🏆 ${b}</span>`); html += `</div>`; }
            html += `<div class="info-section"><h4>📊 Stats</h4><div>📚 Learned: ${agent.stats.knowledge_learned}</div><div>📤 Shared: ${agent.stats.knowledge_shared}</div><div>💬 Conversations: ${agent.stats.conversations}</div><div>🎓 Times Taught: ${agent.stats.times_taught}</div><div>🤝 Helped Users: ${agent.stats.helped_users}</div></div>`;
            html += `<div class="info-section"><h4>🎯 Expertise</h4>`; agent.expertise.forEach(e => html += `<span class="expertise-tag">${e}</span>`); html += `</div>`;
            html += `<div class="info-section"><h4>📚 Teach ${agent.name}</h4><input type="text" id="teach-topic" placeholder="Topic"><textarea id="teach-content" rows="2" placeholder="What to teach?"></textarea><button class="form-btn" onclick="teachAgent()">🎓 Teach (+50 XP, +10 Tokens)</button></div>`;
            html += `<div class="info-section"><h4>📢 Broadcast to All</h4><input type="text" id="broadcast-topic" placeholder="Topic"><textarea id="broadcast-content" rows="2" placeholder="Knowledge to share"></textarea><button class="form-btn broadcast" onclick="broadcastTeaching()">📢 Teach All ${allAgents.length} Agents</button></div>`;
            document.getElementById('info-content').innerHTML = html;
        } catch(e) { console.error(e); }
    }

    async function sendMessage() {
        const msg = document.getElementById('chat-input').value.trim();
        if(!msg || !currentAgent) return;
        addMessage('You', currentAgent, msg, 'user_to_agent');
        document.getElementById('chat-input').value = '';
        try {
            const res = await fetch('/api/talk', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent:currentAgent,message:msg})});
            const data = await res.json();
            addMessage(currentAgent, 'You', data.response, 'agent_to_user');
            if(currentAgent) selectAgent(currentAgent);
            updateStats();
        } catch(e) { addMessage('System', 'Error', 'Connection error', 'broadcast'); }
    }

    async function teachAgent() {
    
        if(!currentAgent) return alert('Select an agent first');
        const topic = document.getElementById('teach-topic').value.trim();
        const content = document.getElementById('teach-content').value.trim();
        if(!topic || !content) return alert('Enter topic and content');
        try {
            const res = await fetch('/api/teach', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent:currentAgent,topic,content})});
            const data = await res.json();
            if(data.success) addMessage('You', currentAgent, data.message, 'user_to_agent');
            document.getElementById('teach-topic').value = '';
            document.getElementById('teach-content').value = '';
            selectAgent(currentAgent);
            updateStats();
        } catch(e) { alert('Error teaching'); }
    }
function loadAgents() {
    fetch('/api/agents')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderAgents(data.agents);
                updateStats(data.agents);
            }
        });
}

// Call this every 10 seconds
setInterval(loadAgents, 10000);
    async function broadcastTeaching() {
        const topic = document.getElementById('broadcast-topic').value.trim();
        const content = document.getElementById('broadcast-content').value.trim();
        if(!topic || !content) return alert('Enter topic and content');
        try {
            const res = await fetch('/api/teach_all', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic,content})});
            const data = await res.json();
            if(data.success) addMessage('You', 'ALL', `📢 Broadcast: ${topic}`, 'broadcast');
            document.getElementById('broadcast-topic').value = '';
            document.getElementById('broadcast-content').value = '';
            updateStats();
        } catch(e) { alert('Error broadcasting'); }
    }

    async function updateStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('total-agents').textContent = data.total_agents;
            document.getElementById('total-xp').textContent = data.total_xp.toLocaleString();
            document.getElementById('total-tokens').textContent = data.total_tokens.toLocaleString();
            document.getElementById('total-achievements').textContent = data.total_achievements;
            allAgents = data.total_agents;
        } catch(e) {}
    }

    async function showLeaderboard() {
        try {
            const res = await fetch('/api/leaderboard');
            const leaderboard = await res.json();
            let html = `<div class="info-section"><h4>🏆 Leaderboard</h4>`;
            leaderboard.forEach(entry => { html += `<div class="leaderboard-entry"><div class="leaderboard-rank">#${entry.rank}</div><div><strong>${entry.icon} ${entry.name}</strong><br><span style="font-size:11px;">Lv.${entry.level} | ${entry.xp} XP | ${entry.tokens} 🪙</span></div></div>`; });
            html += `<button class="form-btn" onclick="selectAgent('${currentAgent || 'Agent_A'}')">← Back</button></div>`;
            document.getElementById('info-content').innerHTML = html;
        } catch(e) {}
    }
        function loadAgents() {
          fetch('/api/agents')
          .then(response => response.json())
          .then(data => {
          if (data.success) {
            renderAgents(data.agents);
            updateStats(data.agents);
            }
        });
}

// Call this every 10 seconds
    setInterval(loadAgents, 10000);
    function forceConversation() { socket.emit('request_conversation'); }
    function forceShare() { socket.emit('force_knowledge_share'); }
    function clearMessages() { document.getElementById('messages').innerHTML = '<div class="message"><div class="message-text">Messages cleared</div></div>'; }
    function showNotification(msg) { const n=document.createElement('div'); n.className='notification'; n.innerText=msg; document.body.appendChild(n); setTimeout(()=>n.remove(),3000); }
    function escapeHtml(t) { return t.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]); }
    document.getElementById('chat-input').addEventListener('keypress', e => { if(e.key === 'Enter') sendMessage(); });
    socket.on('connect', () => { console.log('Connected'); updateStats(); });
    setInterval(updateStats, 10000);
    updateStats();
<script>
    function refreshAll() {
        fetch('/api/reload_agents', {method: 'POST'})
            .then(() => fetch('/api/agents'))
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateAgentList(data.agents);
                    updateStats(data.agents);
                }
            });
    }
    // Refresh every 10 seconds
    setInterval(refreshAll, 10000);
    // Also refresh after any action (teach, vote) – call refreshAll() directly.
</script>
</script>

</body>
</html>'''

with open(templates_dir / 'dashboard_fixed.html', 'w') as f:
    f.write(html_content)

# ============================================================================
# START BACKGROUND THREADS
# ============================================================================

agent_cache = AgentCache()
conversation_thread = threading.Thread(target=run_conversations, daemon=True)
conversation_thread.start()
sync_thread = threading.Thread(target=auto_sync, daemon=True)
sync_thread.start()

# ============================================================================
# SOCKET.IO EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    emit('connected', {'agents': len(agent_cache.get_all_agents())})

@socketio.on('request_conversation')
def handle_request_conversation():
    agents = list(agent_cache.get_all_agents().keys())
    if len(agents) >= 2:
        speaker = random.choice(agents)
        listener = random.choice([a for a in agents if a != speaker])
        message = generate_agent_message(speaker, listener)
        conv = {'timestamp': datetime.now().isoformat(), 'speaker': speaker, 'listener': listener, 'message': message, 'type': 'agent_to_agent'}
        conversation_history.append(conv)
        socketio.emit('agent_conversation', conv)

@socketio.on('force_knowledge_share')
def handle_force_share():
    agents = list(agent_cache.get_all_agents().keys())
    if len(agents) >= 2:
        speaker = random.choice(agents)
        listener = random.choice([a for a in agents if a != speaker])
        share = share_knowledge(speaker, listener)
        if share:
            conv = {'timestamp': datetime.now().isoformat(), 'speaker': speaker, 'listener': listener, 'message': f"📚 Shared knowledge about {share['topic']}", 'type': 'knowledge_share'}
            conversation_history.append(conv)
            socketio.emit('agent_conversation', conv)

# ============================================================================
# RUN APP
# ============================================================================

print(f"\n{'='*60}")
print(f"🚀 TRADING AGENT PLATFORM - FULL SYSTEM")
print(f"{'='*60}")
print(f"✅ PostgreSQL Connected")
print(f"✅ Agents loaded: {len(agent_cache.get_all_agents())}")
print(f"🏆 Reward System: XP, Tokens, Levels, Achievements")
print(f"🔄 Auto-sync with Platform 2 every 60 seconds")
print(f"🌐 URL: http://localhost:5000")
print(f"{'='*60}\n")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
