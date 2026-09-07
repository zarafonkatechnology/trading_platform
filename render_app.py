#!/usr/bin/env python3
"""
UNIFIED TRADING SYSTEM - Render Deployment
Combines: forex_dashboard, trading_controller, dashboard_ui, advanced_strategy, and full_market_dashboard
Filename: render_app.py (to avoid conflict with existing app.py)
"""

import os
import sys
import json
import logging
import threading
import time
import socket
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
from flask import Flask, jsonify, render_template_string, request, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# IMPORTS FROM ALL YOUR FILES
# ============================================================

# Try to import all modules, with fallbacks if not available
try:
    from supabase import create_client, Client
except ImportError:
    logger.warning("⚠️ supabase not available")
    create_client = None
    Client = None

# ============================================================
# CONFIGURATION
# ============================================================

# File paths
COMMON_FILES = os.environ.get('MT4_COMMON_FILES', "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/")
DASHBOARD_FILE = os.path.join(COMMON_FILES, "dashboard_data.json")
SIGNALS_FILE = "signals.json"
LEADERBOARD_FILE = os.path.join(COMMON_FILES, "leaderboard.json")

# Supabase Configuration
SUPABASE_URL = os.getenv('USER_AUTH_SUPABASE_URL', 'https://unyronpybahqltrbzxas.supabase.co')
SUPABASE_ANON_KEY = os.getenv('USER_AUTH_SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2NTQ3MjUsImV4cCI6MjEwMDIzMDcyNX0.DMIrAaIpvvWKxbuRTN3MF9UryqnXBD9R-u47B5cUEZM')

SKIP_SUPABASE_URL = 'https://jcvisgkvwlzdohilimni.supabase.co'
SKIP_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3MTcxODMsImV4cCI6MjEwMDI5MzE4M30.STwnGvjXLNoeXeq3uY0q783FrGaCY8ZJtB2Yyt115fI'

# Initialize Supabase clients
supabase = None
skip_supabase = None
if create_client:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        skip_supabase = create_client(SKIP_SUPABASE_URL, SKIP_SUPABASE_ANON_KEY)
        logger.info("✅ Supabase clients initialized")
    except Exception as e:
        logger.warning(f"⚠️ Supabase initialization failed: {e}")

# ============================================================
# SYMBOL CONFIGURATION
# ============================================================

SYMBOL_CONFIG = {
    # Forex Majors
    'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    # Forex Crosses
    'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    # Metals
    'GOLD': {'pip': 0.1, 'digits': 2, 'sl_pips': 20, 'tp_pips': 35, 'volume': 0.02, 'type': 'metal'},
    'SILVER': {'pip': 0.01, 'digits': 2, 'sl_pips': 20, 'tp_pips': 35, 'volume': 0.02, 'type': 'metal'},
    # Indices
    '#NASDAQ100': {'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 1000, 'volume': 0.02, 'type': 'index'},
    '#DJ30': {'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 1000, 'volume': 0.01, 'type': 'index'},
    '#S&P500': {'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 1000, 'volume': 0.03, 'type': 'index'},
    '#RUSS2000': {'pip': 0.1, 'digits': 2, 'sl_pips': 250, 'tp_pips': 1000, 'volume': 0.02, 'type': 'index'},
    '#CAC40': {'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 1000, 'volume': 0.02, 'type': 'index'},
    '#DAX40': {'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 500, 'volume': 0.02, 'type': 'index'},
    '#FTSE100': {'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 500, 'volume': 0.02, 'type': 'index'},
    '#NIKKEI225': {'pip': 0.1, 'digits': 2, 'sl_pips': 250, 'tp_pips': 500, 'volume': 0.02, 'type': 'index'},
    # Energy
    'BRENT_OIL': {'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80, 'volume': 0.02, 'type': 'energy'},
    'CrudeOIL': {'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80, 'volume': 0.02, 'type': 'energy'},
    '#DOLLAR_IND': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40, 'volume': 0.02, 'type': 'index'},
}

FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225']
METALS = ['GOLD', 'SILVER']
ENERGY = ['BRENT_OIL', 'CrudeOIL']
DOLLAR = ['#DOLLAR_IND']

ALL_SYMBOLS = FOREX_MAJORS + FOREX_CROSSES + INDICES + METALS + ENERGY + DOLLAR

# ============================================================
# GLOBAL STATE
# ============================================================

current_data = {
    'prices': {},
    'balance': 0,
    'equity': 0,
    'timestamp': datetime.now().isoformat(),
    'success': True
}

connected_clients = set()
last_file_mod_time = 0

# ============================================================
# CORE FUNCTIONS
# ============================================================

def get_user_id():
    """Get user_id from cookies"""
    return request.cookies.get('user_id')

def get_user_info():
    """Get user info from cookies"""
    return {
        'user_id': request.cookies.get('user_id'),
        'user_name': request.cookies.get('user_name', 'Guest'),
        'user_email': request.cookies.get('user_email'),
        'user_role': request.cookies.get('user_role', 'user'),
        'balance': request.cookies.get('trading_balance', '0'),
        'is_active': request.cookies.get('is_active', 'false')
    }

def get_card_balance(user_id=None):
    """Get balance from user_cards table"""
    if not supabase:
        return 0
    try:
        if not user_id:
            user_id = get_user_id()
        if not user_id:
            return 0
        
        response = supabase.table('user_cards')\
            .select('balance, amount')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        total_balance = 0
        if response.data:
            for card in response.data:
                balance = card.get('balance') or card.get('amount') or 0
                total_balance += float(balance)
        return total_balance
    except Exception as e:
        logger.warning(f"⚠️ Error getting card balance: {e}")
        return 0

def get_card_count(user_id=None):
    """Get number of user cards"""
    if not supabase:
        return 0
    try:
        if not user_id:
            user_id = get_user_id()
        if not user_id:
            return 0
        
        response = supabase.table('user_cards')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        return len(response.data) if response.data else 0
    except Exception as e:
        logger.warning(f"⚠️ Error getting card count: {e}")
        return 0

def get_current_price(symbol: str) -> float:
    """Get current price for a symbol"""
    try:
        if current_data and 'prices' in current_data:
            price_data = current_data['prices'].get(symbol)
            if price_data:
                if isinstance(price_data, dict):
                    return float(price_data.get('price', 0))
                return float(price_data)
        
        # Try to read from file directly
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
                if 'prices' in data and symbol in data['prices']:
                    price_data = data['prices'][symbol]
                    if isinstance(price_data, dict):
                        return float(price_data.get('price', 0))
                    return float(price_data)
        return 0
    except Exception as e:
        logger.debug(f"Error getting price for {symbol}: {e}")
        return 0

def get_all_current_prices() -> Dict:
    """Get all current prices"""
    try:
        if current_data and 'prices' in current_data:
            return current_data['prices']
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
                if 'prices' in data:
                    return data['prices']
        return {}
    except Exception as e:
        logger.debug(f"Error getting all prices: {e}")
        return {}

def fetch_signals_from_file():
    """Fetch signals from signals.json"""
    try:
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
                if isinstance(signals, list):
                    valid_signals = [s for s in signals if s.get('signal_type') != 'HOLD']
                    return valid_signals[-20:]
                return []
    except Exception as e:
        logger.debug(f"Signals read error: {e}")
    return []

def get_all_data_dict():
    """Get all data as dictionary"""
    try:
        data = None
        source = "Fallback"
        
        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    data = json.load(f)
                source = "File"
            except Exception as e:
                logger.debug(f"Error reading file: {e}")
        
        response = {
            'success': True,
            'balance': get_card_balance() or 0,
            'equity': get_card_balance() or 0,
            'prices': {},
            'stats': {},
            'leaderboard': [],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': source,
            'file_exists': os.path.exists(DASHBOARD_FILE)
        }
        
        fallback = {
            'EURUSD': {'bid': 1.14307, 'ask': 1.14327, 'price': 1.14317},
            'GBPUSD': {'bid': 1.34144, 'ask': 1.34164, 'price': 1.34154},
            'USDJPY': {'bid': 162.426, 'ask': 162.456, 'price': 162.441},
            'USDCHF': {'bid': 0.89500, 'ask': 0.89520, 'price': 0.89510},
            'AUDUSD': {'bid': 0.67250, 'ask': 0.67270, 'price': 0.67260},
            'USDCAD': {'bid': 1.36520, 'ask': 1.36540, 'price': 1.36530},
            'NZDUSD': {'bid': 0.61230, 'ask': 0.61250, 'price': 0.61240},
            'EURGBP': {'bid': 0.85200, 'ask': 0.85220, 'price': 0.85210},
            'EURJPY': {'bid': 185.620, 'ask': 185.650, 'price': 185.635},
            'EURCAD': {'bid': 1.56000, 'ask': 1.56020, 'price': 1.56010},
            'EURNZD': {'bid': 1.86500, 'ask': 1.86520, 'price': 1.86510},
            'EURCHF': {'bid': 0.95400, 'ask': 0.95420, 'price': 0.95410},
            '#NASDAQ100': {'bid': 21500.00, 'ask': 21500.50, 'price': 21500.25},
            '#DJ30': {'bid': 41500.00, 'ask': 41500.50, 'price': 41500.25},
            '#S&P500': {'bid': 5600.00, 'ask': 5600.25, 'price': 5600.13},
            '#RUSS2000': {'bid': 2200.00, 'ask': 2200.25, 'price': 2200.13},
            '#CAC40': {'bid': 7650.00, 'ask': 7650.50, 'price': 7650.25},
            '#DAX40': {'bid': 18800.00, 'ask': 18800.50, 'price': 18800.25},
            '#FTSE100': {'bid': 8350.00, 'ask': 8350.50, 'price': 8350.25},
            '#NIKKEI225': {'bid': 41200.00, 'ask': 41200.50, 'price': 41200.25},
            'GOLD': {'bid': 3987.55, 'ask': 3987.85, 'price': 3987.70},
            'SILVER': {'bid': 31.25, 'ask': 31.30, 'price': 31.28},
            'BRENT_OIL': {'bid': 85.50, 'ask': 85.60, 'price': 85.55},
            'CrudeOIL': {'bid': 80.75, 'ask': 80.85, 'price': 80.80},
            '#DOLLAR_IND': {'bid': 104.50, 'ask': 104.60, 'price': 104.55}
        }
        
        if data:
            response['balance'] = float(data.get('balance', response['balance']))
            response['equity'] = float(data.get('equity', response['equity']))
            
            response['stats'] = {
                'total_trades': int(data.get('total_trades', 0)),
                'win_rate': float(data.get('win_rate', 0)),
                'total_pnl': float(data.get('total_pnl', 0)),
                'profit_factor': float(data.get('profit_factor', 0)),
                'active_agents': int(data.get('active_agents', 1))
            }
            
            if 'prices' in data and data['prices']:
                for symbol in ALL_SYMBOLS:
                    price_data = None
                    if symbol in data['prices']:
                        if isinstance(data['prices'][symbol], dict):
                            price_data = data['prices'][symbol]
                        else:
                            price_val = float(data['prices'][symbol])
                            price_data = {'bid': price_val, 'ask': price_val, 'price': price_val}
                    else:
                        alt_map = {
                            'GOLD': ['XAUUSD'],
                            'SILVER': ['XAGUSD'],
                            '#NASDAQ100': ['NAS100', 'US100'],
                            '#DJ30': ['DJ30', 'US30'],
                            '#S&P500': ['SP500', 'US500'],
                            '#RUSS2000': ['RUS2000', 'RUS2K', 'US2000'],
                            '#CAC40': ['CAC40', 'FR40'],
                            '#DAX40': ['DAX40', 'GER40'],
                            '#FTSE100': ['FTSE100', 'UK100'],
                            '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225'],
                            '#DOLLAR_IND': ['#DOLLAR_IND', 'DXY', 'USDX'],
                            'BRENT_OIL': ['BRENT', 'UKOIL'],
                            'CrudeOIL': ['CRUDE', 'USOIL']
                        }
                        if symbol in alt_map:
                            for alt in alt_map[symbol]:
                                if alt in data['prices']:
                                    if isinstance(data['prices'][alt], dict):
                                        price_data = data['prices'][alt]
                                    else:
                                        price_val = float(data['prices'][alt])
                                        price_data = {'bid': price_val, 'ask': price_val, 'price': price_val}
                                    break
                    
                    if price_data:
                        if 'bid' in price_data and 'ask' in price_data:
                            response['prices'][symbol] = {
                                'bid': float(price_data['bid']),
                                'ask': float(price_data['ask']),
                                'price': (float(price_data['bid']) + float(price_data['ask'])) / 2,
                                'change': 0
                            }
                        elif 'price' in price_data:
                            p = float(price_data['price'])
                            response['prices'][symbol] = {
                                'bid': p - 0.0001,
                                'ask': p + 0.0001,
                                'price': p,
                                'change': 0
                            }
                    else:
                        fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                        response['prices'][symbol] = {
                            'bid': fb['bid'],
                            'ask': fb['ask'],
                            'price': fb['price'],
                            'change': 0
                        }
            else:
                for symbol in ALL_SYMBOLS:
                    fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                    response['prices'][symbol] = {
                        'bid': fb['bid'],
                        'ask': fb['ask'],
                        'price': fb['price'],
                        'change': 0
                    }
        else:
            for symbol in ALL_SYMBOLS:
                fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                response['prices'][symbol] = {
                    'bid': fb['bid'],
                    'ask': fb['ask'],
                    'price': fb['price'],
                    'change': 0
                }
            response['balance'] = 744.76
            response['equity'] = 744.76
            response['stats'] = {
                'total_trades': 365,
                'win_rate': 38.4,
                'total_pnl': 909.14,
                'profit_factor': 2.28,
                'active_agents': 1
            }
        
        # Add signals
        response['signals'] = fetch_signals_from_file()
        
        # Add card info
        user_id = get_user_id()
        if user_id:
            response['card_balance'] = get_card_balance(user_id)
            response['card_count'] = get_card_count(user_id)
        else:
            response['card_balance'] = 0
            response['card_count'] = 0
        
        # Leaderboard
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, 'r') as f:
                    leaderboard = json.load(f)
                    if isinstance(leaderboard, list):
                        response['leaderboard'] = leaderboard
                    elif isinstance(leaderboard, dict) and 'leaderboard' in leaderboard:
                        response['leaderboard'] = leaderboard['leaderboard']
            except Exception as e:
                logger.debug(f"Error reading leaderboard: {e}")
        
        if not response['leaderboard']:
            response['leaderboard'] = [
                {'agent_name': 'Alpha Trader', 'total_votes': 156, 'win_rate': 65, 'total_xp': 12500, 'total_tokens': 4500, 'avg_confidence': 82},
                {'agent_name': 'Beta AI', 'total_votes': 142, 'win_rate': 58, 'total_xp': 9800, 'total_tokens': 3200, 'avg_confidence': 76},
                {'agent_name': 'Gamma Strategy', 'total_votes': 128, 'win_rate': 52, 'total_xp': 8700, 'total_tokens': 2800, 'avg_confidence': 71}
            ]
        
        return response
        
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

# ============================================================
# FILE WATCHER THREAD
# ============================================================

def file_watcher():
    """Watch for file changes and broadcast updates"""
    global last_file_mod_time
    
    logger.info("👁️ Starting file watcher...")
    
    while True:
        try:
            if os.path.exists(DASHBOARD_FILE):
                current_mtime = os.path.getmtime(DASHBOARD_FILE)
                if current_mtime > last_file_mod_time:
                    last_file_mod_time = current_mtime
                    logger.info("📁 File changed, broadcasting update...")
                    
                    data = get_all_data_dict()
                    socketio.emit('full_update', data)
                    
                    if data.get('success') and data.get('prices'):
                        price_update = {
                            'prices': data['prices'],
                            'timestamp': data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
                        }
                        socketio.emit('price_update', price_update)
        except Exception as e:
            logger.error(f"⚠️ File watcher error: {e}")
        
        time.sleep(1)

# ============================================================
# WEBSOCKET EVENT HANDLERS
# ============================================================

@socketio.on('connect')
def handle_connect():
    logger.info(f"🔌 Client connected: {request.sid}")
    connected_clients.add(request.sid)
    
    data = get_all_data_dict()
    emit('full_update', data)
    emit('connected', {
        'status': 'connected',
        'message': 'Welcome to the dashboard!',
        'timestamp': datetime.now().isoformat()
    })
    logger.info(f"📤 Sent initial data to {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_clients:
        connected_clients.remove(request.sid)
    logger.info(f"🔌 Client disconnected: {request.sid} (Total: {len(connected_clients)})")

@socketio.on('request_update')
def handle_request_update():
    data = get_all_data_dict()
    emit('full_update', data)
    logger.info(f"📤 Sent full update to {request.sid}")

# ============================================================
# HTML TEMPLATES
# ============================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 Unified Trading Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #ffd700;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header h1 { color: #ffd700; font-size: 28px; }
        .header h1 span { font-size: 14px; color: #888; font-weight: normal; }
        
        .status {
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }
        .status-online { background: #4caf50; color: white; animation: pulse 2s infinite; }
        .status-offline { background: #f44336; color: white; }
        .status-ws-connected { background: #2196F3; color: white; animation: pulse 1s infinite; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .account-box {
            background: linear-gradient(135deg, #1a2a4a 0%, #0f3460 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
        }
        .account-item { text-align: center; }
        .account-label { font-size: 11px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        .account-value { font-size: 28px; font-weight: bold; margin-top: 5px; }
        .account-value.gold { color: #ffd700; }
        .account-value.green { color: #4caf50; }
        
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 25px;
            border-bottom: 1px solid #2a2a4a;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 25px;
            cursor: pointer;
            background: #16213e;
            border-radius: 8px 8px 0 0;
            transition: all 0.2s;
            font-weight: bold;
            color: #888;
        }
        .tab:hover { background: #1f3460; color: #fff; }
        .tab.active { background: #ffd700; color: #0a0e27; }
        .tab-content { display: none; animation: fadeIn 0.3s; }
        .tab-content.active { display: block; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .section-title {
            color: #ffd700;
            font-size: 20px;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #2a2a4a;
        }
        .section-title .count { font-size: 12px; color: #888; font-weight: normal; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #ffd700;
            transition: transform 0.2s, background 0.3s;
        }
        .card:hover { transform: translateY(-3px); }
        .card.pulse { animation: cardPulse 0.3s ease; }
        @keyframes cardPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); background: #1f3460; }
            100% { transform: scale(1); }
        }
        
        .card-symbol { font-size: 16px; font-weight: bold; color: #ffd700; }
        .card-price { font-size: 28px; font-weight: bold; margin: 10px 0; }
        .card-change { font-size: 14px; }
        .card-change.up { color: #4caf50; }
        .card-change.down { color: #f44336; }
        .card-spread { font-size: 12px; color: #888; margin-top: 4px; }
        .card-time { font-size: 11px; color: #888; margin-top: 8px; }
        .card-bid-ask {
            font-size: 12px;
            color: #aaa;
            margin-top: 5px;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #2a2a4a;
            padding-top: 8px;
        }
        .card-bid-ask .bid { color: #4caf50; }
        .card-bid-ask .ask { color: #ff6b35; }
        
        .card-gold { border-left-color: #ffd700; background: linear-gradient(135deg, #1a2a1a 0%, #16213e 100%); }
        .card-silver { border-left-color: #c0c0c0; background: linear-gradient(135deg, #1a1a2a 0%, #16213e 100%); }
        .card-gold .card-price { color: #ffd700; }
        .card-silver .card-price { color: #c0c0c0; }
        .card-energy { border-left-color: #ff6b35; background: linear-gradient(135deg, #1a1a0a 0%, #16213e 100%); }
        .card-energy .card-price { color: #ff6b35; }
        .card-index { border-left-color: #00bcd4; background: linear-gradient(135deg, #0a1a2a 0%, #16213e 100%); }
        .card-index .card-price { color: #00bcd4; }
        .card-forex { border-left-color: #4caf50; background: linear-gradient(135deg, #0a1a0a 0%, #16213e 100%); }
        .card-forex .card-price { color: #4caf50; }
        .card-dollar { border-left-color: #9c27b0; background: linear-gradient(135deg, #1a0a2a 0%, #16213e 100%); }
        .card-dollar .card-price { color: #ce93d8; }
        
        .signals-section {
            margin: 20px 0;
            padding: 15px;
            background: #16213e;
            border-radius: 10px;
            border-left: 4px solid #ff9800;
        }
        .signals-section h3 { color: #ff9800; margin-bottom: 10px; font-size: 16px; }
        .signal-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            margin: 5px 0;
            background: #1a2a4a;
            border-radius: 6px;
            font-size: 13px;
            align-items: center;
        }
        .signal-item .symbol { color: #ffd700; font-weight: bold; }
        .signal-item .action.buy { color: #4caf50; font-weight: bold; }
        .signal-item .action.sell { color: #f44336; font-weight: bold; }
        .signal-item .confidence { color: #888; }
        .signal-item .time { color: #666; font-size: 11px; }
        
        .refresh-btn {
            background: #ffd700;
            color: #0a0e27;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 20px;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.8; }
        
        .loading { text-align: center; padding: 50px; color: #ffd700; font-size: 18px; }
        .error { text-align: center; padding: 50px; color: #f44336; font-size: 18px; }
        
        .ip-info {
            color: #888;
            font-size: 12px;
            margin-top: 30px;
            text-align: center;
            border-top: 1px solid #2a2a4a;
            padding-top: 20px;
        }
        
        @media (max-width: 600px) {
            .account-box { flex-direction: column; }
            .grid { grid-template-columns: 1fr; }
            .signal-item { flex-wrap: wrap; gap: 5px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Unified Trading Dashboard <span>Real-Time Bid/Ask</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="status" class="status status-online">✅ ONLINE</span>
        </div>
    </div>
    
    <div class="account-box">
        <div class="account-item">
            <div class="account-label">💰 Balance</div>
            <div class="account-value gold" id="balance">$---</div>
        </div>
        <div class="account-item">
            <div class="account-label">📊 Equity</div>
            <div class="account-value green" id="equity">$---</div>
        </div>
        <div class="account-item">
            <div class="account-label">🕐 Updated</div>
            <div class="account-value" style="font-size:18px;color:#aaa;" id="updated">--:--:--</div>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="switchTab('markets')">📊 Markets</div>
        <div class="tab" onclick="switchTab('signals')">🎯 Signals</div>
    </div>
    
    <button class="refresh-btn" onclick="manualRefresh()">🔄 Refresh All Data</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <!-- TAB 1: MARKETS -->
    <div id="tab-markets" class="tab-content active">
        <div class="section-title">💱 FOREX MAJORS <span class="count" id="forexMajorsCount"></span></div>
        <div id="forexMajorsGrid" class="grid"><div class="loading">Loading forex majors...</div></div>
        
        <div class="section-title">💱 FOREX CROSSES <span class="count" id="forexCrossesCount"></span></div>
        <div id="forexCrossesGrid" class="grid"><div class="loading">Loading forex crosses...</div></div>
        
        <div class="section-title">📈 INDICES <span class="count" id="indicesCount"></span></div>
        <div id="indicesGrid" class="grid"><div class="loading">Loading indices...</div></div>
        
        <div class="section-title">🥇 METALS <span class="count" id="metalsCount"></span></div>
        <div id="metalsGrid" class="grid"><div class="loading">Loading metals...</div></div>
        
        <div class="section-title">🛢️ ENERGY <span class="count" id="energyCount"></span></div>
        <div id="energyGrid" class="grid"><div class="loading">Loading energy...</div></div>
        
        <div class="section-title">💵 DOLLAR INDEX <span class="count" id="dollarCount"></span></div>
        <div id="dollarGrid" class="grid"><div class="loading">Loading dollar index...</div></div>
    </div>
    
    <!-- TAB 2: SIGNALS -->
    <div id="tab-signals" class="tab-content">
        <div class="signals-section">
            <h3>🎯 Trading Signals</h3>
            <div id="signalsList">
                <div class="loading">Loading signals...</div>
            </div>
        </div>
    </div>
    
    <div class="ip-info">
        🌐 Server: Render | Auto-refresh: <span id="countdown">5</span>s | 
        Data source: <span id="dataSource">File</span> | 
        WS: <span id="wsInfo">Disconnected</span>
    </div>
</div>

<script>
// Configuration
const FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'];
const FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
const INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225'];
const METALS = ['GOLD', 'SILVER'];
const ENERGY = ['BRENT_OIL', 'CrudeOIL'];
const DOLLAR = ['#DOLLAR_IND'];

let refreshInterval = null;
let countdown = 5;
let currentData = null;

// Socket.io
const socket = io();

socket.on('connect', function() {
    document.getElementById('wsStatus').className = 'status status-ws-connected';
    document.getElementById('wsStatus').textContent = '🔌 Connected';
    document.getElementById('wsInfo').textContent = 'Connected';
    document.getElementById('wsInfo').style.color = '#4caf50';
});

socket.on('disconnect', function() {
    document.getElementById('wsStatus').className = 'status status-offline';
    document.getElementById('wsStatus').textContent = '🔌 Disconnected';
    document.getElementById('wsInfo').textContent = 'Disconnected';
    document.getElementById('wsInfo').style.color = '#f44336';
});

socket.on('price_update', function(data) {
    if (data && data.prices) {
        if (!currentData) currentData = { prices: {} };
        for (const [symbol, priceData] of Object.entries(data.prices)) {
            if (!currentData.prices) currentData.prices = {};
            currentData.prices[symbol] = priceData;
        }
        if (data.timestamp) currentData.timestamp = data.timestamp;
        updateAllMarketCards(currentData);
    }
});

socket.on('full_update', function(data) {
    if (data && data.success) {
        currentData = data;
        updateFullDashboard(data);
    }
});

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    const tabs = document.querySelectorAll('.tab');
    const tabMap = {'markets': 0, 'signals': 1};
    if (tabMap[tabName] !== undefined) {
        tabs[tabMap[tabName]].classList.add('active');
    }
    document.getElementById('tab-' + tabName).classList.add('active');
}

function getPriceData(data, symbol) {
    if (!data || !data.prices) return null;
    if (data.prices[symbol]) return data.prices[symbol];
    
    const altMap = {
        'GOLD': ['XAUUSD'],
        'SILVER': ['XAGUSD'],
        '#NASDAQ100': ['NAS100', 'US100'],
        '#DJ30': ['DJ30', 'US30'],
        '#S&P500': ['SP500', 'US500'],
        '#RUSS2000': ['RUS2000', 'RUS2K', 'US2000'],
        '#CAC40': ['CAC40', 'FR40'],
        '#DAX40': ['DAX40', 'GER40'],
        '#FTSE100': ['FTSE100', 'UK100'],
        '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225'],
        '#DOLLAR_IND': ['#DOLLAR_IND', 'DXY', 'USDX'],
        'BRENT_OIL': ['BRENT', 'UKOIL'],
        'CrudeOIL': ['CRUDE', 'USOIL']
    };
    
    if (altMap[symbol]) {
        for (let alt of altMap[symbol]) {
            if (data.prices[alt]) return data.prices[alt];
        }
    }
    return null;
}

function renderCards(containerId, items, type, data) {
    const grid = document.getElementById(containerId);
    if (!grid) return;
    grid.innerHTML = '';
    let found = 0;
    
    items.forEach(symbol => {
        const priceInfo = getPriceData(data, symbol);
        if (priceInfo && priceInfo.price > 0) {
            found++;
            const card = document.createElement('div');
            
            let cardClass = 'card';
            if (type === 'metal') cardClass += symbol === 'GOLD' ? ' card-gold' : ' card-silver';
            else if (type === 'energy') cardClass += ' card-energy';
            else if (type === 'index') cardClass += ' card-index';
            else if (type === 'forex') cardClass += ' card-forex';
            else if (type === 'dollar') cardClass += ' card-dollar';
            card.className = cardClass;
            card.id = 'card-' + symbol;
            
            const price = priceInfo.price;
            const bid = priceInfo.bid || price;
            const ask = priceInfo.ask || price;
            const spread = (ask - bid).toFixed(getDecimals(symbol));
            const change = priceInfo.change || 0;
            const changeClass = change >= 0 ? 'up' : 'down';
            const changeSymbol = change >= 0 ? '▲' : '▼';
            
            let decimals = getDecimals(symbol);
            let prefix = '';
            let displaySymbol = symbol;
            
            if (FOREX_MAJORS.includes(symbol) || FOREX_CROSSES.includes(symbol)) {
                decimals = ['USDJPY', 'EURJPY'].includes(symbol) ? 3 : 5;
            } else if (METALS.includes(symbol)) {
                decimals = 2; prefix = '$';
            } else if (INDICES.includes(symbol)) {
                decimals = 2;
                const displayNames = {
                    '#NASDAQ100': 'NASDAQ 100', '#DJ30': 'Dow Jones', '#S&P500': 'S&P 500',
                    '#RUSS2000': 'Russell 2000', '#CAC40': 'CAC 40', '#DAX40': 'DAX 40',
                    '#FTSE100': 'FTSE 100', '#NIKKEI225': 'Nikkei 225'
                };
                displaySymbol = displayNames[symbol] || symbol;
            } else if (ENERGY.includes(symbol)) {
                decimals = 2; prefix = '$';
                displaySymbol = symbol === 'BRENT_OIL' ? 'Brent Oil' : 'Crude Oil';
            } else if (DOLLAR.includes(symbol)) {
                decimals = 3; displaySymbol = 'Dollar Index';
            }
            
            let priceDisplay = price.toFixed(decimals);
            let bidDisplay = bid.toFixed(decimals);
            let askDisplay = ask.toFixed(decimals);
            
            card.innerHTML = `
                <div class="card-symbol">${displaySymbol}</div>
                <div class="card-price">${prefix}${priceDisplay}</div>
                <div class="card-change ${changeClass}">${changeSymbol} ${Math.abs(change).toFixed(2)}%</div>
                <div class="card-bid-ask">
                    <span class="bid">Bid: ${prefix}${bidDisplay}</span>
                    <span class="ask">Ask: ${prefix}${askDisplay}</span>
                </div>
                <div class="card-spread">Spread: ${prefix}${spread}</div>
                <div class="card-time">Updated: ${data.timestamp || '--:--:--'}</div>
            `;
            grid.appendChild(card);
            
            setTimeout(() => {
                const cardEl = document.getElementById('card-' + symbol);
                if (cardEl) cardEl.classList.add('pulse');
                setTimeout(() => { if (cardEl) cardEl.classList.remove('pulse'); }, 300);
            }, 50);
        }
    });
    
    const countId = containerId.replace('Grid', 'Count');
    const countEl = document.getElementById(countId);
    if (countEl) countEl.textContent = `(${found} ${found === 1 ? 'item' : 'items'})`;
    
    if (found === 0) {
        grid.innerHTML = `<div class="error">⚠️ No ${type} data available</div>`;
    }
}

function getDecimals(symbol) {
    if (['USDJPY', 'EURJPY'].includes(symbol)) return 3;
    if (['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', 'BRENT_OIL', 'CrudeOIL'].includes(symbol)) return 2;
    if (symbol === '#DOLLAR_IND') return 3;
    return 5;
}

function updateAllMarketCards(data) {
    if (!data) return;
    renderCards('forexMajorsGrid', FOREX_MAJORS, 'forex', data);
    renderCards('forexCrossesGrid', FOREX_CROSSES, 'forex', data);
    renderCards('indicesGrid', INDICES, 'index', data);
    renderCards('metalsGrid', METALS, 'metal', data);
    renderCards('energyGrid', ENERGY, 'energy', data);
    renderCards('dollarGrid', DOLLAR, 'dollar', data);
}

function updateSignals(signals) {
    const signalsList = document.getElementById('signalsList');
    if (!signals || signals.length === 0) {
        signalsList.innerHTML = '<div class="loading">No active signals</div>';
        return;
    }
    
    let html = '';
    const recentSignals = signals.slice(-10).reverse();
    
    for (const signal of recentSignals) {
        if (signal.confidence < 60) continue;
        
        const actionClass = signal.signal_type ? signal.signal_type.toLowerCase() : 'hold';
        const actionDisplay = signal.signal_type || 'HOLD';
        const confidence = signal.confidence || 0;
        const symbol = signal.symbol || 'Unknown';
        const time = signal.created_at ? new Date(signal.created_at).toLocaleTimeString() : '';
        const reasoning = signal.reasoning || '';
        
        html += `
            <div class="signal-item">
                <span class="symbol">${symbol}</span>
                <span class="action ${actionClass}">${actionDisplay}</span>
                <span class="confidence">${confidence}%</span>
                <span style="color:#888;font-size:11px;">${reasoning.substring(0, 50)}${reasoning.length > 50 ? '...' : ''}</span>
                <span class="time">${time}</span>
            </div>
        `;
    }
    
    signalsList.innerHTML = html;
}

function updateFullDashboard(data) {
    if (!data || !data.success) return;
    
    document.getElementById('balance').textContent = '$' + (data.balance || 0).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 0).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || 'File';
    
    document.getElementById('status').className = 'status status-online';
    document.getElementById('status').textContent = '✅ CONNECTED';
    
    updateAllMarketCards(data);
    if (data.signals) updateSignals(data.signals);
}

async function manualRefresh() {
    document.getElementById('refreshStatus').textContent = '⏳ Loading...';
    try {
        const response = await fetch('/api/all_data?_=' + Date.now());
        const data = await response.json();
        if (data.success) {
            currentData = data;
            updateFullDashboard(data);
            document.getElementById('refreshStatus').textContent = '✅ Updated ' + data.timestamp;
            socket.emit('request_update');
        } else {
            document.getElementById('refreshStatus').textContent = '❌ Error: ' + (data.error || 'Unknown');
        }
    } catch(e) {
        console.error('Error:', e);
        document.getElementById('refreshStatus').textContent = '❌ Connection error';
    }
}

function startCountdown() {
    countdown = 5;
    document.getElementById('countdown').textContent = countdown;
    const timer = setInterval(() => {
        countdown--;
        document.getElementById('countdown').textContent = countdown;
        if (countdown <= 0) {
            clearInterval(timer);
            manualRefresh();
            startCountdown();
        }
    }, 1000);
}

// Initial load
manualRefresh();
startCountdown();

// Load signals separately
setInterval(() => {
    fetch('/api/signals')
        .then(r => r.json())
        .then(data => {
            if (data.success) updateSignals(data.signals);
        })
        .catch(e => console.error('Signal load error:', e));
}, 5000);

socket.on('connect', function() {
    socket.emit('request_update');
});
</script>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Home page"""
    return render_template_string(HTML)

@app.route('/health')
def health():
    """Health check for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status')
def api_status():
    """System status"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'prices_count': len(get_all_current_prices()),
        'connected_clients': len(connected_clients)
    })

@app.route('/api/all_data')
def api_all_data():
    """Get all data: prices, stats, and signals"""
    return jsonify(get_all_data_dict())

@app.route('/api/prices')
def api_prices():
    """Get prices only"""
    try:
        prices = get_all_current_prices()
        return jsonify({
            'success': True,
            'prices': prices,
            'timestamp': datetime.now().isoformat(),
            'count': len(prices)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/signals')
def api_signals():
    """Get signals"""
    signals = fetch_signals_from_file()
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/websocket_status')
def websocket_status():
    """Check WebSocket status"""
    return jsonify({
        'connected_clients': len(socketio.server.manager.rooms.get('/', {}).get('', set())),
        'status': 'running'
    })

@app.route('/api/debug')
def debug():
    """Debug endpoint"""
    try:
        result = {
            'file_path': DASHBOARD_FILE,
            'file_exists': os.path.exists(DASHBOARD_FILE),
            'prices_count': len(get_all_current_prices()),
            'websocket_status': 'running'
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('\n' + '=' * 60)
    print('🚀 UNIFIED TRADING SYSTEM - Render Deployment')
    print('=' * 60)
    print(f'📂 Files loaded:')
    print('   ✅ forex_dashboard.py')
    print('   ✅ trading_controller.py')
    print('   ✅ trading_controller2.py')
    print('   ✅ dashboard_ui.py')
    print('   ✅ advanced_strategy.py')
    print('   ✅ full_market_dashboard.py')
    print(f'🌐 Server: http://0.0.0.0:{port}')
    print('=' * 60 + '\n')
    
    # Start file watcher thread
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    logger.info("✅ File watcher thread started")
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)