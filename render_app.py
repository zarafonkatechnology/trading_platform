#!/usr/bin/env python3
"""
UNIFIED TRADING SYSTEM - Render Deployment
Uses forex_dashboard.py code for REAL MT4 prices
"""

import os
import sys
import json
import logging
import threading
import time
import socket
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# CONFIGURATION - FROM forex_dashboard.py
# ============================================================

# For Render, the dashboard_data.json will be created by MT4
# The file should be in the same directory as the app
DASHBOARD_FILE = "dashboard_data.json"
SIGNALS_FILE = "signals.json"

# ============================================================
# SYMBOL CONFIGURATION - FROM forex_dashboard.py
# ============================================================

FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225']
METALS = ['GOLD', 'SILVER']
ENERGY = ['BRENT_OIL', 'CrudeOIL']
DOLLAR = ['#DOLLAR_IND']

ALL_SYMBOLS = FOREX_MAJORS + FOREX_CROSSES + INDICES + METALS + ENERGY + DOLLAR

# ============================================================
# GLOBAL STATE - FROM forex_dashboard.py
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
# CORE FUNCTIONS - FROM forex_dashboard.py
# ============================================================

def get_user_id():
    """Get user_id from cookies"""
    return request.cookies.get('user_id')

def get_card_balance(user_id=None):
    """Get balance from user_cards table"""
    try:
        # For Render, just return 0 if no Supabase
        return 0
    except Exception as e:
        logger.warning(f"⚠️ Error getting card balance: {e}")
        return 0

def get_current_price(symbol: str) -> float:
    """Get current price for a symbol - FROM forex_dashboard.py"""
    try:
        if current_data and 'prices' in current_data:
            price_data = current_data['prices'].get(symbol)
            if price_data:
                if isinstance(price_data, dict):
                    return float(price_data.get('price', 0))
                return float(price_data)
        
        # Try to read from file directly (MT4 data)
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
    """Get all current prices - FROM forex_dashboard.py"""
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
    """Get all data as dictionary - FROM forex_dashboard.py"""
    try:
        data = None
        source = "Fallback"
        
        # ===== READ FROM MT4 DASHBOARD FILE =====
        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    data = json.load(f)
                source = "MT4 Live Data"
                logger.info(f"✅ Read MT4 data from {DASHBOARD_FILE}")
            except Exception as e:
                logger.warning(f"⚠️ Error reading MT4 file: {e}")
        
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
        
        # ===== FALLBACK PRICES (if no MT4 data) =====
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
        
        # ===== BUILD PRICES FROM MT4 DATA =====
        if data and 'prices' in data:
            for symbol in ALL_SYMBOLS:
                price_data = None
                if symbol in data['prices']:
                    if isinstance(data['prices'][symbol], dict):
                        price_data = data['prices'][symbol]
                    else:
                        price_val = float(data['prices'][symbol])
                        price_data = {'bid': price_val, 'ask': price_val, 'price': price_val}
                else:
                    # Try alternative names (from forex_dashboard.py)
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
            # Update balance/equity from MT4 data
            response['balance'] = float(data.get('balance', response['balance']))
            response['equity'] = float(data.get('equity', response['equity']))
            response['source'] = "MT4 Live Data ✅"
        else:
            # No MT4 data - use fallback
            for symbol in ALL_SYMBOLS:
                fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                response['prices'][symbol] = {
                    'bid': fb['bid'],
                    'ask': fb['ask'],
                    'price': fb['price'],
                    'change': 0
                }
            response['balance'] = 10000.00
            response['equity'] = 10000.00
            response['source'] = "Fallback (No MT4 Data) ❌"
        
        # Add signals
        response['signals'] = fetch_signals_from_file()
        
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
# FILE WATCHER THREAD - FROM forex_dashboard.py
# ============================================================

def file_watcher():
    """Watch for file changes and broadcast updates - FROM forex_dashboard.py"""
    global last_file_mod_time
    
    logger.info("👁️ Starting file watcher for MT4 data...")
    
    while True:
        try:
            if os.path.exists(DASHBOARD_FILE):
                current_mtime = os.path.getmtime(DASHBOARD_FILE)
                if current_mtime > last_file_mod_time:
                    last_file_mod_time = current_mtime
                    logger.info("📁 MT4 data file changed, broadcasting update...")
                    
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
# WEBSOCKET EVENT HANDLERS - FROM forex_dashboard.py
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
    logger.info(f"🔌 Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_request_update():
    data = get_all_data_dict()
    emit('full_update', data)

# ============================================================
# HTML TEMPLATE - FROM forex_dashboard.py
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 Trading Platform - MT4 Live Prices</title>
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
        .container { max-width: 1200px; margin: 0 auto; }
        
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
        .status-ws { background: #2196F3; color: white; animation: pulse 1s infinite; }
        .status-mt4 { background: #ff9800; color: white; }
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
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
        }
        .account-item { text-align: center; }
        .account-label { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        .account-value { font-size: 22px; font-weight: bold; margin-top: 5px; }
        .account-value.gold { color: #ffd700; }
        .account-value.green { color: #4caf50; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #ffd700;
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-3px); }
        .card-forex { border-left-color: #4caf50; }
        .card-index { border-left-color: #00bcd4; }
        .card-metal { border-left-color: #ffd700; }
        .card-energy { border-left-color: #ff6b35; }
        .card-dollar { border-left-color: #9c27b0; }
        
        .card-symbol { font-size: 14px; font-weight: bold; color: #ffd700; }
        .card-price { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .card-bid-ask {
            font-size: 12px;
            color: #aaa;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #2a2a4a;
            padding-top: 8px;
        }
        .card-bid-ask .bid { color: #4caf50; }
        .card-bid-ask .ask { color: #ff6b35; }
        .card-spread { font-size: 11px; color: #888; margin-top: 4px; }
        .card-change { font-size: 13px; }
        .card-change.up { color: #4caf50; }
        .card-change.down { color: #f44336; }
        
        .signals-section {
            margin: 20px 0;
            padding: 15px;
            background: #16213e;
            border-radius: 10px;
            border-left: 4px solid #ff9800;
        }
        .signals-section h3 { color: #ff9800; margin-bottom: 10px; }
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
        
        .refresh-btn {
            background: #ffd700;
            color: #0a0e27;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            margin: 20px 0;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.8; }
        
        .endpoints {
            margin-top: 30px;
            padding: 20px;
            background: #16213e;
            border-radius: 10px;
        }
        .endpoints a { color: #ffd700; display: inline-block; margin: 5px 15px 5px 0; }
        
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
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Trading Platform <span>MT4 Live Prices</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="mt4Status" class="status status-offline">📡 MT4: Disconnected</span>
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
        <div class="account-item">
            <div class="account-label">📡 Data Source</div>
            <div class="account-value" style="font-size:16px;color:#ffd700;" id="dataSource">--</div>
        </div>
        <div class="account-item">
            <div class="account-label">📊 Symbols</div>
            <div class="account-value" style="font-size:18px;color:#00bcd4;" id="symbolCount">0</div>
        </div>
    </div>
    
    <div class="signals-section">
        <h3>🎯 Trading Signals</h3>
        <div id="signalsList">
            <div style="color: #666; text-align: center; padding: 10px;">No active signals</div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <div class="grid" id="pricesGrid">
        <div style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">Loading MT4 prices...</div>
    </div>
    
    <div class="endpoints">
        <h3 style="color:#ffd700;">🔗 API Endpoints</h3>
        <a href="/health">/health</a>
        <a href="/api/status">/api/status</a>
        <a href="/api/prices">/api/prices</a>
        <a href="/api/signals">/api/signals</a>
        <a href="/api/all_data">/api/all_data</a>
        <a href="/api/mt4_status">/api/mt4_status</a>
    </div>
    
    <div class="ip-info">
        🌐 Server: Render | Auto-refresh: <span id="countdown">5</span>s
    </div>
</div>

<script>
const socket = io();

socket.on('connect', function() {
    document.getElementById('wsStatus').className = 'status status-ws';
    document.getElementById('wsStatus').textContent = '🔌 Connected';
});

socket.on('disconnect', function() {
    document.getElementById('wsStatus').className = 'status status-offline';
    document.getElementById('wsStatus').textContent = '🔌 Disconnected';
});

socket.on('connected', function(data) {
    if (data) {
        document.getElementById('wsStatus').className = 'status status-ws';
        document.getElementById('wsStatus').textContent = '🔌 Connected';
    }
});

socket.on('full_update', function(data) {
    if (data && data.success) {
        updateDashboard(data);
    }
});

socket.on('price_update', function(data) {
    if (data && data.prices) {
        updatePricesOnly(data.prices);
    }
});

async function refreshData() {
    document.getElementById('refreshStatus').textContent = '⏳ Loading...';
    try {
        const response = await fetch('/api/all_data?_=' + Date.now());
        const data = await response.json();
        if (data.success) {
            updateDashboard(data);
            document.getElementById('refreshStatus').textContent = '✅ Updated ' + data.timestamp;
        } else {
            document.getElementById('refreshStatus').textContent = '❌ Error loading data';
        }
    } catch(e) {
        console.error('Error:', e);
        document.getElementById('refreshStatus').textContent = '❌ Connection error';
    }
}

function getCardType(symbol) {
    const forex = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 
                   'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
    const indices = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225'];
    const metals = ['GOLD', 'SILVER'];
    const energy = ['BRENT_OIL', 'CrudeOIL'];
    const dollar = ['#DOLLAR_IND'];
    
    if (forex.includes(symbol)) return 'forex';
    if (indices.includes(symbol)) return 'index';
    if (metals.includes(symbol)) return 'metal';
    if (energy.includes(symbol)) return 'energy';
    if (dollar.includes(symbol)) return 'dollar';
    return '';
}

function getDecimals(symbol) {
    if (['USDJPY', 'EURJPY'].includes(symbol)) return 3;
    if (['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', 'BRENT_OIL', 'CrudeOIL'].includes(symbol)) return 2;
    if (symbol === '#DOLLAR_IND') return 3;
    return 5;
}

function updatePricesOnly(prices) {
    const grid = document.getElementById('pricesGrid');
    if (!prices) return;
    
    let html = '';
    const symbols = Object.keys(prices);
    let count = 0;
    
    for (const symbol of symbols) {
        const priceData = prices[symbol];
        if (!priceData || !priceData.price) continue;
        count++;
        
        const cardType = getCardType(symbol);
        const price = priceData.price;
        const bid = priceData.bid || price;
        const ask = priceData.ask || price;
        const spread = Math.abs(ask - bid);
        const decimals = getDecimals(symbol);
        
        html += `
            <div class="card card-${cardType}">
                <div class="card-symbol">${symbol}</div>
                <div class="card-price">${price.toFixed(decimals)}</div>
                <div class="card-bid-ask">
                    <span class="bid">Bid: ${bid.toFixed(decimals)}</span>
                    <span class="ask">Ask: ${ask.toFixed(decimals)}</span>
                </div>
                <div class="card-spread">Spread: ${spread.toFixed(decimals)}</div>
            </div>
        `;
    }
    
    grid.innerHTML = html || '<div style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">No price data available</div>';
    document.getElementById('symbolCount').textContent = count;
}

function updateDashboard(data) {
    // Update MT4 status
    const mt4Status = document.getElementById('mt4Status');
    if (data.source && data.source.includes('MT4')) {
        mt4Status.className = 'status status-mt4';
        mt4Status.textContent = '📡 MT4: Connected ✅';
    } else {
        mt4Status.className = 'status status-offline';
        mt4Status.textContent = '📡 MT4: Disconnected ❌';
    }
    
    // Update account
    document.getElementById('balance').textContent = '$' + (data.balance || 10000).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 10000).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || '--';
    
    // Update signals
    const signalsList = document.getElementById('signalsList');
    if (data.signals && data.signals.length > 0) {
        let html = '';
        for (const signal of data.signals.slice(-5).reverse()) {
            const actionClass = signal.signal_type ? signal.signal_type.toLowerCase() : 'hold';
            const actionDisplay = signal.signal_type || 'HOLD';
            html += `
                <div class="signal-item">
                    <span class="symbol">${signal.symbol || 'Unknown'}</span>
                    <span class="action ${actionClass}">${actionDisplay}</span>
                    <span class="confidence">${signal.confidence || 0}%</span>
                    <span style="color:#888;font-size:11px;">${(signal.reasoning || '').substring(0, 40)}</span>
                </div>
            `;
        }
        signalsList.innerHTML = html;
    } else {
        signalsList.innerHTML = '<div style="color: #666; text-align: center; padding: 10px;">No active signals</div>';
    }
    
    // Update prices
    updatePricesOnly(data.prices);
}

let countdown = 5;
document.getElementById('countdown').textContent = countdown;
setInterval(() => {
    countdown--;
    document.getElementById('countdown').textContent = countdown;
    if (countdown <= 0) {
        countdown = 5;
        refreshData();
        socket.emit('request_update');
    }
}, 1000);

refreshData();
setTimeout(() => socket.emit('request_update'), 500);
</script>
</body>
</html>
"""

# ============================================================
# ROUTES - FROM forex_dashboard.py
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'mt4_data_exists': os.path.exists(DASHBOARD_FILE)
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'connected_clients': len(connected_clients),
        'mt4_data_exists': os.path.exists(DASHBOARD_FILE),
        'prices_count': len(get_all_current_prices())
    })

@app.route('/api/prices')
def api_prices():
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
    signals = fetch_signals_from_file()
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/all_data')
def api_all_data():
    return jsonify(get_all_data_dict())

@app.route('/api/mt4_status')
def mt4_status():
    """Check if MT4 data is available"""
    exists = os.path.exists(DASHBOARD_FILE)
    if exists:
        try:
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'connected': True,
                'prices_count': len(data.get('prices', {})),
                'file_exists': True,
                'balance': data.get('balance', 0),
                'timestamp': data.get('timestamp', datetime.now().isoformat())
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': True, 'connected': False, 'file_exists': False})

@app.route('/api/debug')
def debug():
    """Debug endpoint"""
    try:
        result = {
            'file_path': DASHBOARD_FILE,
            'file_exists': os.path.exists(DASHBOARD_FILE),
            'prices_count': len(get_all_current_prices()),
            'websocket_status': 'running',
            'connected_clients': len(connected_clients)
        }
        if result['file_exists']:
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
            result['has_prices'] = 'prices' in data
            result['balance'] = data.get('balance', 0)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('\n' + '=' * 60)
    print('🚀 TRADING PLATFORM - MT4 Live Prices')
    print('=' * 60)
    print(f'📂 Looking for: {DASHBOARD_FILE}')
    print(f'📡 MT4 Data: {"✅ EXISTS" if os.path.exists(DASHBOARD_FILE) else "❌ NOT FOUND"}')
    print(f'🌐 Server: http://0.0.0.0:{port}')
    print('=' * 60 + '\n')
    
    # Start file watcher
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    logger.info("✅ File watcher thread started")
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=port, debug=False)