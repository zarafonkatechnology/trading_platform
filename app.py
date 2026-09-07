#!/usr/bin/env python
"""
Trading Agent Platform - Main Application
Graduation Project
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from backend.services.telegram_bot import TelegramBotHandler
from backend.services.telegram_bot_simple import SimpleTelegramBot

from backend.services.market_signal_generator import MarketSignalGenerator
import asyncio
from backend.services.price_service import get_price_service
# from backend.services.oanda_fetcher import get_oanda_fetcher
import sqlite3 
from backend.agents.agent_manager import AgentManager
DB_PATH = 'trading_system.db'

agent_manager = AgentManager()
def load_agents_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT agent_name, agent_type, specialization, xp_points, token_balance, trust_weight, total_votes, correct_votes, vote_accuracy FROM core_agents ORDER BY agent_name')
    rows = cursor.fetchall()
    conn.close()
    
    agents = []
    for row in rows:
        agents.append({
            'name': row[0],
            'type': row[1],
            'specialization': row[2],
            'xp': row[3],
            'tokens': row[4],
            'trust_weight': row[5],
            'total_votes': row[6],
            'correct_votes': row[7],
            'accuracy': row[8]
        })
    return agents


agent_manager.agents = load_agents_from_db()  # or similar
  # adjust to your database path
# Load environment variables
load_dotenv()

# Get absolute paths
PROJECT_ROOT = Path(__file__).parent.absolute()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'logs', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask imports
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Initialize Flask app with explicit paths
app = Flask(__name__,
           template_folder=os.path.join(PROJECT_ROOT, 'frontend/templates'),
           static_folder=os.path.join(PROJECT_ROOT, 'frontend/static'),
           static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JSON_SORT_KEYS'] = False
# Initialize storage for conversations and knowledge exchanges
app.conversations = []
app.knowledge_exchanges = []
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Import project modules
from backend.utils.database import db_manager, get_db
from backend.agents.agent_manager import AgentManager
from backend.core.supervisor import Supervisor
from backend.core.sentinel import SentinelAgent
from backend.core.gatekeeper import GatekeeperAgent

# Initialize components
agent_manager = AgentManager(db_manager)
price_service = get_price_service()
price_service.start()

mt4 = get_mt4_prices()

print("✅ MT4 Price Service Active")        
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_bot = None

if telegram_token and telegram_token != 'YOUR_BOT_TOKEN_HERE' and telegram_token != '':
    try:
        telegram_bot = SimpleTelegramBot(telegram_token, agent_manager, db_manager, app)
        telegram_bot.price_service = price_service  # Pass price service
        telegram_bot.start()
        logger.info("✅ Telegram bot started successfully!")
        print("✅ Telegram bot is running! Send a message to your bot on Telegram.")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        print(f"❌ Telegram bot initialization failed: {e}")
else:
    logger.warning("⚠️ Telegram bot token not configured. Bot disabled.")
    print("⚠️ Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN in .env")
supervisor = Supervisor()
sentinel = SentinelAgent()
gatekeeper = GatekeeperAgent()

# Store in app config
app.config['agent_manager'] = agent_manager
app.config['supervisor'] = supervisor
app.config['sentinel'] = sentinel
app.config['gatekeeper'] = gatekeeper

# Test database connection
if db_manager.test_connection():
    logger.info("Database connection successful")
    # Sync agents with database
    agent_manager.sync_with_database(db_manager)
else:
    logger.warning("Database connection failed - running in demo mode")

# ============================================
# ROUTES
# ============================================

# ============================================
# AGENT LEVELS & ACHIEVEMENTS CONFIGURATION
# ============================================

AGENT_LEVELS = {
    1: ('Novice', 0, '🔰'),
    2: ('Apprentice', 100, '📘'),
    3: ('Scholar', 300, '📚'),
    4: ('Expert', 600, '⭐'),
    5: ('Master', 1000, '🏆'),
    6: ('Grandmaster', 1500, '👑'),
    7: ('Legend', 2100, '🌟'),
    8: ('Mythic', 2800, '💫'),
    9: ('Transcendent', 3600, '✨'),
    10: ('Omniscient', 5000, '🔮'),
}

def get_agent_level(xp):
    """Get agent level based on XP"""
    for level, (name, required, icon) in AGENT_LEVELS.items():
        if xp < required:
            return level - 1, AGENT_LEVELS[level - 1][0], AGENT_LEVELS[level - 1][2]
    return 10, 'Omniscient', '🔮'

def check_level_up(agent_name, old_xp, new_xp):
    """Check if agent leveled up"""
    old_level = get_agent_level(old_xp)[0]
    new_level = get_agent_level(new_xp)[0]
    if new_level > old_level:
        level_name = get_agent_level(new_xp)[1]
        icon = get_agent_level(new_xp)[2]
        print(f"🎉 {agent_name} reached Level {new_level} - {icon} {level_name}!")
        return True
    return False

# ============================================
# MARKET DATA ROUTES (OANDA REAL-TIME)
# ============================================

@app.route('/api/market/prices')
def api_market_prices():
    """Get real-time market prices from MT4 """
    try:
        prices = price_service.get_all_prices()
        return jsonify({
            'success': True,
            'prices': prices,
            'source': 'MT4',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Price API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'prices': {}
        }), 500

@app.route('/api/market/status')
def api_market_status():
    """Get market status"""
    try:
        status = price_service.get_market_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market/account')
def api_market_account():
    """Get account information"""
    try:
        account = price_service.get_account_info()
        return jsonify({
            'success': True,
            'account': account
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market/signals')
def api_market_signals():
    """Get trading signals based on real prices"""
    try:
        signals = price_service.generate_signals()
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals),
            'source': 'MT4 Real-Time',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Signals API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market/candles/<instrument>')
def api_market_candles(instrument):
    """Get historical candles for an instrument"""
    try:
        count = request.args.get('count', 50, type=int)
        granularity = request.args.get('granularity', 'M5')
        candles = []  # Placeholder - implement if needed
        print("⚠️ Candle history not available in MT4 file bridge")
        return jsonify({
            'success': True,
            'instrument': instrument,
            'candles': candles,
            'count': len(candles)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market/order', methods=['POST'])
def api_market_order():
    """Place a trading order (simulated for demo)"""
    try:
        data = request.get_json()
        instrument = data.get('instrument')
        units = data.get('units')
        side = data.get('side')
        
        # Get current price
        current_price = price_service.get_price(instrument)
        
        return jsonify({
            'success': True,
            'order': {
                'id': f"ORDER_{int(time.time())}",
                'instrument': instrument,
                'units': units,
                'side': side,
                'price': current_price,
                'status': 'filled',
                'message': f"Demo order executed: {side} {units} {instrument} @ ${current_price}"
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/test_signal', methods=['POST'])
def api_test_signal():
    """Test endpoint to simulate a Telegram signal"""
    try:
        data = request.get_json()
        
        # Create test signal
        test_signal = {
            'asset': data.get('asset', 'BTCUSD'),
            'action': data.get('action', 'BUY'),
            'price': float(data.get('price', 50000)),
            'stoploss': data.get('stoploss'),
            'takeprofit': data.get('takeprofit'),
            'confidence': data.get('confidence', 85),
            'strength': data.get('strength', 'SIGNAL')
        }
        
        # Collect votes
        market_features = {
            'z_score_20': 0.5,
            'rsi_14': 55,
            'trend_strength': 60
        }
        
        votes = agent_manager.collect_votes(test_signal, market_features)
        
        # Calculate results
        buy_votes = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell_votes = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        total = len(votes)
        
        return jsonify({
            'success': True,
            'signal': test_signal,
            'votes': votes,
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'buy_percent': round(buy_votes / total * 100, 1),
            'sell_percent': round(sell_votes / total * 100, 1)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/')
def index():
    """Main dashboard - Platform 1 (Learning Platform)"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return f"<h1>Error loading dashboard</h1><p>{e}</p><p>Template path: {os.path.join(PROJECT_ROOT, 'frontend/templates')}</p>"

@app.route('/platform2')
def platform2():
    """Platform 2 (Trading Platform)"""
    try:
        return render_template('platform2_dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering platform2: {e}")
        return f"<h1>Error loading platform2</h1><p>{e}</p>"

@app.route('/security')
def security_dashboard():
    """Security Dashboard"""
    try:
        return render_template('security_dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering security dashboard: {e}")
        return f"<h1>Error loading security dashboard</h1><p>{e}</p>"

@app.route('/api/agents')
def api_agents():
    """Get all agents with their status"""
    agents = agent_manager.get_all_status()
    return jsonify({
        'success': True,
        'agents': agents,
        'total_agents': len(agents)
    })

@app.route('/api/agent/<agent_name>')
def api_agent(agent_name):
    """Get specific agent details"""
    agent = agent_manager.get_agent(agent_name)
    if agent:
        return jsonify({
            'success': True,
            'agent': agent.get_status()
        })
    return jsonify({'success': False, 'error': 'Agent not found'}), 404

@app.route('/api/votes', methods=['POST'])
def api_collect_votes():
    try:
        data = request.get_json()
        signal_data = data.get('signal', {})
        market_features = data.get('features', {})
        
        votes = agent_manager.collect_votes(signal_data, market_features)
        decision = supervisor.process_votes(votes)
        
        # Store in knowledge exchange
        vote_summary = f"BUY: {decision['vote_counts']['BUY']}, SELL: {decision['vote_counts']['SELL']}, HOLD: {decision['vote_counts']['HOLD']}"
        knowledge_entry = {
            'id': len(app.knowledge_exchanges) + 1,
            'from_agent': 'Voting System',
            'to_agent': 'ALL AGENTS',
            'topic': f'🗳️ Vote Result: {decision["decision"]}',
            'content': vote_summary,
            'xp_reward': 0,
            'token_reward': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        app.knowledge_exchanges.insert(0, knowledge_entry)
        
        return jsonify({'success': True, 'votes': votes, 'decision': decision})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_reward', methods=['POST'])
def api_update_reward():
    """Update agent rewards based on trade outcome"""
    data = request.json
    agent_name = data.get('agent_name')
    was_correct = data.get('was_correct', False)
    xp_gained = data.get('xp_gained', 0)
    xp_lost = data.get('xp_lost', 0)
    
    result = agent_manager.update_agent_rewards(agent_name, was_correct, xp_gained, xp_lost)
    
    # Sync with database
    agent_manager.sync_with_database(db_manager)
    
    return jsonify({
        'success': True,
        'agent_status': result
    })

@app.route('/api/status')
def api_status():
    """Overall system status"""
    agents = agent_manager.get_all_status()
    
    total_xp = sum(a['xp_points'] for a in agents)
    total_tokens = sum(a['token_balance'] for a in agents)
    avg_accuracy = sum(a['vote_accuracy'] for a in agents) / len(agents) if agents else 0
    
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'total_agents': len(agents),
        'total_xp': total_xp,
        'total_tokens': total_tokens,
        'avg_accuracy': round(avg_accuracy, 2),
        'agents': agents
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    db_healthy = db_manager.test_connection()
    
    return jsonify({
        'status': 'healthy' if db_healthy else 'degraded',
        'database': 'connected' if db_healthy else 'disconnected',
        'agents': len(agent_manager.get_all_agents()),
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# SOCKET.IO EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to trading platform'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_update_request():
    """Send latest agent data to client"""
    agents = agent_manager.get_all_status()
    emit('agent_update', {'agents': agents, 'timestamp': datetime.now().isoformat()})

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500



# ============================================
# MAIN ENTRY POINT
# ============================================

# ============================================
# CONVERSATION ROUTES
# ============================================

@app.route('/api/agent_conversation', methods=['POST'])
def api_agent_conversation():
    try:
        data = request.get_json()
        from_agent = data.get('from_agent')
        to_agent = data.get('to_agent')
        message = data.get('message')
        
        # Make sure app.conversations exists
        if not hasattr(app, 'conversations'):
            app.conversations = []
        
        conversation_entry = {
            'id': len(app.conversations) + 1,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        app.conversations.insert(0, conversation_entry)
        
        # Keep last 100
        if len(app.conversations) > 100:
            app.conversations = app.conversations[:100]
        
        # Also add to knowledge exchange
        if not hasattr(app, 'knowledge_exchanges'):
            app.knowledge_exchanges = []
        
        knowledge_entry = {
            'id': len(app.knowledge_exchanges) + 1,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'topic': '💬 Conversation',
            'content': message[:100],
            'xp_reward': 5,
            'token_reward': 2,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        app.knowledge_exchanges.insert(0, knowledge_entry)
        
        # Award XP to both agents
        from_agent_obj = agent_manager.get_agent(from_agent)
        to_agent_obj = agent_manager.get_agent(to_agent)
        if from_agent_obj:
            from_agent_obj.xp_points += 5
        if to_agent_obj:
            to_agent_obj.xp_points += 5
        
        return jsonify({'success': True, 'conversation': conversation_entry})
    except Exception as e:
        logger.error(f"Conversation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agent_conversations')
def api_agent_conversations():
    if not hasattr(app, 'conversations'):
        app.conversations = []
    return jsonify({
        'success': True,
        'conversations': app.conversations,
        'total': len(app.conversations)
    })

# ============================================
# TEACHING & KNOWLEDGE EXCHANGE ROUTES
# ============================================

# Initialize knowledge exchange storage
if not hasattr(app, 'knowledge_exchanges'):
    app.knowledge_exchanges = []

@app.route('/api/teach_agent', methods=['POST'])
def api_teach_agent():
    try:
        data = request.get_json()
        agent_name = data.get('agent_name')
        topic = data.get('topic')
        content = data.get('content')
        
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 404
        
        # Award XP and tokens
        agent.add_xp(50)
        agent.add_tokens(10)
        agent.knowledge_shared_count += 1
        
        # Force save to database
        agent._save_to_db()
        
        # Also sync all agents
        agent_manager.sync_with_database(db_manager)
        
        return jsonify({'success': True, 'message': f'Agent {agent_name} gained +50 XP, +10 Tokens!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
        # Store in knowledge exchange
        knowledge_entry = {
            'id': len(app.knowledge_exchanges) + 1,
            'from_agent': teacher,
            'to_agent': agent_name,
            'topic': topic,
            'content': content,
            'xp_reward': 50,
            'token_reward': 10,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_broadcast': False
        }
        app.knowledge_exchanges.insert(0, knowledge_entry)
        
        # Keep only last 100 entries
        if len(app.knowledge_exchanges) > 100:
            app.knowledge_exchanges = app.knowledge_exchanges[:100]
        
        # Try to update database if connected
        try:
            if db_manager and db_manager.test_connection():
                agent_manager.sync_with_database(db_manager)
        except Exception as db_error:
            logger.warning(f"Database sync failed: {db_error}")
        
        # Get updated agent status
        agent_status = {
            'name': agent.name,
            'xp_points': agent.xp_points,
            'token_balance': agent.token_balance,
            'trust_weight': getattr(agent, 'trust_weight', 0.2),
            'vote_accuracy': getattr(agent, 'vote_accuracy', 0)
        }
        
        # Emit socket event for real-time update
        socketio.emit('agent_update', {
            'agents': agent_manager.get_all_status(),
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'✅ Agent {agent_name} learned "{topic}" and gained +50 XP, +10 Tokens!',
            'agent': agent_status,
            'knowledge_entry': knowledge_entry
        })
        
    except Exception as e:
        logger.error(f"Teach agent error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/teach_all_agents', methods=['POST'])
def api_teach_all_agents():
    """Broadcast knowledge to ALL agents"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        topic = data.get('topic')
        content = data.get('content')
        teacher = data.get('teacher', 'User')
        
        # Validate input
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'}), 400
        if not content:
            return jsonify({'success': False, 'error': 'Content is required'}), 400
        
        agents = agent_manager.get_all_agents()
        if not agents:
            return jsonify({'success': False, 'error': 'No agents found'}), 404
        
        total_xp = 0
        total_tokens = 0
        updated_agents = []
        
        for agent in agents:
            # Award XP and tokens (slightly less for broadcast)
            agent.xp_points = getattr(agent, 'xp_points', 0) + 25
            agent.token_balance = getattr(agent, 'token_balance', 1000) + 5
            agent.knowledge_shared_count = getattr(agent, 'knowledge_shared_count', 0) + 1
            total_xp += 25
            total_tokens += 5
            updated_agents.append(agent.name)
        
        # Store broadcast in knowledge exchange
        broadcast_entry = {
            'id': len(app.knowledge_exchanges) + 1,
            'from_agent': teacher,
            'to_agent': 'ALL AGENTS',
            'topic': f'📢 [BROADCAST] {topic}',
            'content': content,
            'xp_reward': 25,
            'token_reward': 5,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_broadcast': True,
            'agents_affected': updated_agents
        }
        app.knowledge_exchanges.insert(0, broadcast_entry)
        
        # Keep only last 100 entries
        if len(app.knowledge_exchanges) > 100:
            app.knowledge_exchanges = app.knowledge_exchanges[:100]
        
        # Try to update database if connected
        try:
            if db_manager and db_manager.test_connection():
                agent_manager.sync_with_database(db_manager)
        except Exception as db_error:
            logger.warning(f"Database sync failed: {db_error}")
        
        # Emit socket event
        socketio.emit('broadcast_completed', {
            'topic': topic,
            'total_agents': len(agents),
            'total_xp_awarded': total_xp,
            'total_tokens_awarded': total_tokens,
            'agents': updated_agents,
            'timestamp': datetime.now().isoformat()
        })
        
        socketio.emit('agent_update', {
            'agents': agent_manager.get_all_status(),
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'📢 Broadcast to {len(agents)} agents! Total: +{total_xp} XP, +{total_tokens} Tokens',
            'total_xp': total_xp,
            'total_tokens': total_tokens,
            'agents_affected': updated_agents,
            'broadcast_entry': broadcast_entry
        })
        
    except Exception as e:
        logger.error(f"Teach all agents error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/request_knowledge', methods=['POST'])
def api_request_knowledge():
    """Agent requests knowledge from another agent"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        from_agent = data.get('from_agent')
        to_agent = data.get('to_agent')
        topic = data.get('topic')
        question = data.get('question')
        
        # Validate input
        if not from_agent:
            return jsonify({'success': False, 'error': 'From agent is required'}), 400
        if not to_agent:
            return jsonify({'success': False, 'error': 'To agent is required'}), 400
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'}), 400
        
        # Check if agents exist
        from_agent_obj = agent_manager.get_agent(from_agent)
        to_agent_obj = agent_manager.get_agent(to_agent)
        
        if not from_agent_obj:
            return jsonify({'success': False, 'error': f'Agent {from_agent} not found'}), 404
        if not to_agent_obj:
            return jsonify({'success': False, 'error': f'Agent {to_agent} not found'}), 404
        
        # Store request in knowledge exchange
        request_entry = {
            'id': len(app.knowledge_exchanges) + 1,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'topic': f'❓ [REQUEST] {topic}',
            'content': question,
            'xp_reward': 0,
            'token_reward': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_request': True,
            'status': 'pending'
        }
        app.knowledge_exchanges.insert(0, request_entry)
        
        # Keep only last 100 entries
        if len(app.knowledge_exchanges) > 100:
            app.knowledge_exchanges = app.knowledge_exchanges[:100]
        
        return jsonify({
            'success': True,
            'message': f'📨 Request sent from {from_agent} to {to_agent} about "{topic}"',
            'request_entry': request_entry
        })
        
    except Exception as e:
        logger.error(f"Request knowledge error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/knowledge_exchanges', methods=['GET'])
def api_knowledge_exchanges():
    """Get all knowledge exchanges"""
    try:
        exchanges = getattr(app, 'knowledge_exchanges', [])
        return jsonify({
            'success': True,
            'exchanges': exchanges,
            'total': len(exchanges)
        })
    except Exception as e:
        logger.error(f"Get knowledge exchanges error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agent_topics/<agent_name>', methods=['GET'])
def api_agent_topics(agent_name):
    """Get topics learned by an agent"""
    try:
        # Get agent
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            return jsonify({'success': False, 'error': f'Agent {agent_name} not found'}), 404
        
        # Filter knowledge exchanges for this agent
        exchanges = getattr(app, 'knowledge_exchanges', [])
        agent_topics = []
        
        for ex in exchanges:
            if ex.get('to_agent') == agent_name or (ex.get('is_broadcast') and agent_name in ex.get('agents_affected', [])):
                agent_topics.append({
                    'topic_name': ex.get('topic'),
                    'content': ex.get('content'),
                    'xp_gained': ex.get('xp_reward', 0),
                    'learned_at': ex.get('timestamp')
                })
        
        return jsonify({
            'success': True,
            'topics': agent_topics,
            'total': len(agent_topics)
        })
        
    except Exception as e:
        logger.error(f"Get agent topics error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save_all_data', methods=['POST'])
def api_save_all_data():
    """Save all platform data"""
    try:
        # Sync agents with database
        if db_manager and db_manager.test_connection():
            agent_manager.sync_with_database(db_manager)
        
        # Get current stats
        agents = agent_manager.get_all_status()
        total_xp = sum(a.get('xp_points', 0) for a in agents)
        total_tokens = sum(a.get('token_balance', 0) for a in agents)
        total_achievements = sum(a.get('achievements_count', 0) for a in agents)
        
        # Emit socket event
        socketio.emit('save_confirmation', {
            'timestamp': datetime.now().isoformat(),
            'total_xp': total_xp,
            'total_tokens': total_tokens,
            'total_achievements': total_achievements
        })
        
        return jsonify({
            'success': True,
            'message': '💾 Data saved successfully',
            'stats': {
                'total_xp': total_xp,
                'total_tokens': total_tokens,
                'total_achievements': total_achievements
            }
        })
        
    except Exception as e:
        logger.error(f"Save data error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agent_achievements/<agent_name>', methods=['GET'])
def api_agent_achievements(agent_name):
    """Get achievements for a specific agent"""
    try:
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            return jsonify({'success': False, 'error': f'Agent {agent_name} not found'}), 404
        
        xp = getattr(agent, 'xp_points', 0)
        achievements = []
        
        # Calculate achievements based on XP
        if xp >= 100:
            achievements.append({'name': 'Novice Trader', 'xp_required': 100, 'earned': True})
        if xp >= 500:
            achievements.append({'name': 'Apprentice', 'xp_required': 500, 'earned': True})
        if xp >= 1000:
            achievements.append({'name': 'Journeyman', 'xp_required': 1000, 'earned': True})
        if xp >= 5000:
            achievements.append({'name': 'Master', 'xp_required': 5000, 'earned': True})
        if xp >= 10000:
            achievements.append({'name': 'Legend', 'xp_required': 10000, 'earned': True})
        
        return jsonify({
            'success': True,
            'agent_name': agent_name,
            'xp': xp,
            'achievements': achievements,
            'total_achievements': len(achievements)
        })
        
    except Exception as e:
        logger.error(f"Get agent achievements error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
import threading
import time

def auto_save_loop():
    """Auto-save agent data every 30 seconds"""
    while True:
        time.sleep(1)
        try:
            agent_manager.sync_with_database(db_manager)
            logger.info("Auto-save completed")
        except Exception as e:
            logger.error(f"Auto-save error: {e}")

# Start auto-save thread
save_thread = threading.Thread(target=auto_save_loop, daemon=True)
save_thread.start()
logger.info("Auto-save thread started (every 30 seconds)")
if __name__ == '__main__':

    # Create necessary directories
    os.makedirs(os.path.join(PROJECT_ROOT, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'data', 'raw'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'data', 'processed'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'data', 'models'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'frontend', 'templates'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'frontend', 'static', 'css'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'frontend', 'static', 'js'), exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("TRADING AGENT PLATFORM STARTING")
    logger.info("=" * 50)
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Template Folder: {os.path.join(PROJECT_ROOT, 'frontend/templates')}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Host: {os.getenv('FLASK_HOST', '0.0.0.0')}")
    logger.info(f"Port: {os.getenv('FLASK_PORT', 5000)}")
    logger.info(f"Database: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    logger.info(f"Agents loaded: {len(agent_manager.get_all_agents())}")
    logger.info("=" * 50)
    
    # Check if template exists
    template_path = os.path.join(PROJECT_ROOT, 'frontend', 'templates', 'dashboard.html')
    if os.path.exists(template_path):
        logger.info(f"✓ Template found: {template_path}")
    else:
        logger.warning(f"✗ Template NOT found: {template_path}")
    
    # Run application
    socketio.run(
        app,
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )
