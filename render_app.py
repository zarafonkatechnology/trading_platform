#!/usr/bin/env python3
"""
📊 MT4 TRADING DASHBOARD - INSTANT UPDATES
Updates every 1 second - super fast!
"""

import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# FILE PATHS
# ============================================================

COMMON_FILES = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
DASHBOARD_FILE = os.path.join(COMMON_FILES, "dashboard_data.json")
LOCAL_FILE = "dashboard_data.json"

# ============================================================
# ALL 31 SYMBOLS
# ============================================================

FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', "#AMAZON", '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD']
METALS = ['GOLD', 'SILVER']
ENERGY = ['BRENT_OIL', 'CrudeOIL']
DOLLAR = ['#DOLLAR_IND']

ALL_SYMBOLS = FOREX_MAJORS + FOREX_CROSSES + INDICES + METALS + ENERGY + DOLLAR

# ============================================================
# GLOBALS
# ============================================================

current_data = {'prices': {}, 'balance': 0, 'equity': 0}
connected_clients = set()
last_file_mod_time = 0

# ============================================================
# FUNCTIONS
# ============================================================

def find_mt4_file():
    if os.path.exists(DASHBOARD_FILE):
        return DASHBOARD_FILE
    if os.path.exists(LOCAL_FILE):
        return LOCAL_FILE
    return None

def get_all_data_dict():
    """Get all data - INSTANT"""
    try:
        file_path = find_mt4_file()
        data = None
        source = "Fallback ❌"
        mt4_connected = False

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                source = "MT4 Live ✅"
                mt4_connected = True
            except:
                pass

        response = {
            'success': True,
            'balance': 10000,
            'equity': 10000,
            'prices': {},
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': source,
            'mt4_connected': mt4_connected
        }

        fallback = {
            'EURUSD': 1.14317, 'GBPUSD': 1.34154, 'USDJPY': 162.441,
            'USDCHF': 0.89510, 'AUDUSD': 0.67260, 'USDCAD': 1.36530,
            'NZDUSD': 0.61240, 'EURGBP': 0.85210, 'EURJPY': 185.635,
            'EURCAD': 1.56010, 'EURNZD': 1.86510, 'EURCHF': 0.95410,
            'GOLD': 3987.70, 'SILVER': 31.28,
            '#NASDAQ100': 21500.25, '#DJ30': 41500.25, '#S&P500': 5600.13,
            '#RUSS2000': 2200.13, '#CAC40': 7650.25, '#DAX40': 18800.25,
            '#FTSE100': 8350.25, '#NIKKEI225': 41200.25,
            "#AMAZON": 258.47, "#APPLE": 319.85, "#MICROSOFT": 499.68,
            "#SPACEX": 147.96, "#VISA": 374.36, "#MASTERCARD": 579.58,
            'BRENT_OIL': 85.55, 'CrudeOIL': 80.80,
            '#DOLLAR_IND': 104.55
        }

        if data and 'prices' in data:
            for symbol in ALL_SYMBOLS:
                if symbol in data['prices']:
                    p = data['prices'][symbol]
                    if isinstance(p, dict):
                        response['prices'][symbol] = {
                            'bid': float(p.get('bid', 0)),
                            'ask': float(p.get('ask', 0)),
                            'price': float(p.get('price', 0)),
                            'change': float(p.get('change', 0))
                        }
                    else:
                        p = float(p)
                        response['prices'][symbol] = {
                            'bid': p, 'ask': p, 'price': p, 'change': 0
                        }
                else:
                    alt_map = {
                        'GOLD': ['XAUUSD'], 'SILVER': ['XAGUSD'],
                        '#NASDAQ100': ['NAS100', 'US100'], '#DJ30': ['DJ30', 'US30'],
                        '#S&P500': ['SP500', 'US500'], '#RUSS2000': ['RUS2000', 'RUS2K', 'US2000'],
                        '#CAC40': ['CAC40', 'FR40'], '#DAX40': ['DAX40', 'GER40'],
                        '#FTSE100': ['FTSE100', 'UK100'], '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225'],
                        '#DOLLAR_IND': ['#DOLLAR_IND', 'DXY', 'USDX'],
                        'BRENT_OIL': ['BRENT', 'UKOIL'], 'CrudeOIL': ['CRUDE', 'USOIL']
                    }
                    found = False
                    if symbol in alt_map:
                        for alt in alt_map[symbol]:
                            if alt in data['prices']:
                                p = data['prices'][alt]
                                if isinstance(p, dict):
                                    response['prices'][symbol] = {
                                        'bid': float(p.get('bid', 0)),
                                        'ask': float(p.get('ask', 0)),
                                        'price': float(p.get('price', 0)),
                                        'change': float(p.get('change', 0))
                                    }
                                else:
                                    p = float(p)
                                    response['prices'][symbol] = {
                                        'bid': p, 'ask': p, 'price': p, 'change': 0
                                    }
                                found = True
                                break
                    if not found:
                        p = fallback.get(symbol, 0)
                        response['prices'][symbol] = {
                            'bid': p * 0.9999, 'ask': p * 1.0001, 'price': p, 'change': 0
                        }

            if 'balance' in data:
                response['balance'] = float(data['balance'])
            if 'equity' in data:
                response['equity'] = float(data['equity'])
            if 'timestamp' in data:
                response['timestamp'] = data['timestamp']
        else:
            for symbol in ALL_SYMBOLS:
                p = fallback.get(symbol, 0)
                response['prices'][symbol] = {
                    'bid': p * 0.9999, 'ask': p * 1.0001, 'price': p, 'change': 0
                }

        return response
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================================
# WEBSOCKET - INSTANT
# ============================================================

@socketio.on('connect')
def handle_connect():
    connected_clients.add(request.sid)
    data = get_all_data_dict()
    emit('full_update', data)
    emit('price_update', {'prices': data.get('prices', {}), 'timestamp': data.get('timestamp', '')})

@socketio.on('disconnect')
def handle_disconnect():
    connected_clients.discard(request.sid)

@socketio.on('request_update')
def handle_request_update():
    emit('full_update', get_all_data_dict())

# ============================================================
# FILE WATCHER - SUPER FAST (1 SECOND)
# ============================================================

def file_watcher():
    global last_file_mod_time
    while True:
        try:
            file_path = find_mt4_file()
            if file_path:
                current_mtime = os.path.getmtime(file_path)
                if current_mtime > last_file_mod_time:
                    last_file_mod_time = current_mtime
                    data = get_all_data_dict()
                    socketio.emit('full_update', data)
                    if data.get('prices'):
                        socketio.emit('price_update', {
                            'prices': data['prices'],
                            'timestamp': data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
                        })
        except:
            pass
        time.sleep(0.5)  # Check every 500ms - SUPER FAST!

# ============================================================
# HTML - INSTANT LOADING
# ============================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 MT4 Dashboard</title>
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
        .status-ws { background: #2196F3; color: white; animation: pulse 1s infinite; }
        .status-mt4 { background: #ff9800; color: white; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
        
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
        .tab-content { display: none; animation: fadeIn 0.1s; }
        .tab-content.active { display: block; }
        
        .section-title {
            color: #ffd700;
            font-size: 20px;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #2a2a4a;
        }
        .section-title .emoji { margin-right: 10px; }
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
        .card.pulse { animation: cardPulse 0.2s ease; }
        @keyframes cardPulse { 0% { transform: scale(1); } 50% { transform: scale(1.02); background: #1f3460; } 100% { transform: scale(1); } }
        
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
        <h1>📊 MT4 Dashboard <span>Live Prices</span></h1>
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
        <div class="account-item">
            <div class="account-label">📡 Data Source</div>
            <div class="account-value" style="font-size:16px;color:#ffd700;" id="dataSource">--</div>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="switchTab('markets')">📊 Markets</div>
        <div class="tab" onclick="switchTab('statistics')">📈 Statistics</div>
        <div class="tab" onclick="switchTab('leaderboard')">🏆 Leaderboard</div>
    </div>
    
    <button class="refresh-btn" onclick="manualRefresh()">🔄 Refresh</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <div id="tab-markets" class="tab-content active">
        <div class="section-title"><span class="emoji">💱</span> FOREX MAJORS <span class="count" id="forexMajorsCount"></span></div>
        <div id="forexMajorsGrid" class="grid"><div class="loading">Loading...</div></div>
        
        <div class="section-title"><span class="emoji">💱</span> FOREX CROSSES <span class="count" id="forexCrossesCount"></span></div>
        <div id="forexCrossesGrid" class="grid"><div class="loading">Loading...</div></div>
        
        <div class="section-title"><span class="emoji">📈</span> INDICES <span class="count" id="indicesCount"></span></div>
        <div id="indicesGrid" class="grid"><div class="loading">Loading...</div></div>
        
        <div class="section-title"><span class="emoji">🥇</span> METALS <span class="count" id="metalsCount"></span></div>
        <div id="metalsGrid" class="grid"><div class="loading">Loading...</div></div>
        
        <div class="section-title"><span class="emoji">🛢️</span> ENERGY <span class="count" id="energyCount"></span></div>
        <div id="energyGrid" class="grid"><div class="loading">Loading...</div></div>
        
        <div class="section-title"><span class="emoji">💵</span> DOLLAR INDEX <span class="count" id="dollarCount"></span></div>
        <div id="dollarGrid" class="grid"><div class="loading">Loading...</div></div>
    </div>
    
    <div id="tab-statistics" class="tab-content">
        <div style="text-align:center;">
            <h2 style="color:#ffd700;margin-bottom:20px;">📊 Trading Statistics</h2>
            <table class="stats-table" id="statsTable">
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="statsBody"><tr><td colspan="2" style="text-align:center;padding:30px;color:#888;">Loading...</td></tr></tbody>
            </table>
        </div>
    </div>
    
    <div id="tab-leaderboard" class="tab-content">
        <div style="text-align:center;">
            <h2 style="color:#ffd700;margin-bottom:20px;">🏆 Agent Leaderboard</h2>
            <table class="leaderboard-table" id="leaderboardTable">
                <thead><tr><th>Rank</th><th>Agent</th><th>Votes</th><th>Win Rate</th><th>XP</th><th>Tokens</th><th>Confidence</th></tr></thead>
                <tbody id="leaderboardBody"><tr><td colspan="7" style="text-align:center;padding:30px;color:#888;">Loading...</td></tr></tbody>
            </table>
        </div>
    </div>
    
    <div class="ip-info">
        🌐 Server: Render | Auto-refresh: <span id="countdown">5</span>s
    </div>
</div>

<script>
const FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'];
const FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
const INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', '#AMAZON', '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD'];
const METALS = ['GOLD', 'SILVER'];
const ENERGY = ['BRENT_OIL', 'CrudeOIL'];
const DOLLAR = ['#DOLLAR_IND'];

let countdown = 5;
let currentData = null;

const socket = io();

socket.on('connect', function() {
    document.getElementById('wsStatus').className = 'status status-ws';
    document.getElementById('wsStatus').textContent = '🔌 Connected';
    socket.emit('request_update');
});

socket.on('disconnect', function() {
    document.getElementById('wsStatus').className = 'status status-offline';
    document.getElementById('wsStatus').textContent = '🔌 Disconnected';
});

socket.on('full_update', function(data) {
    if (data && data.success) {
        currentData = data;
        updateFullDashboard(data);
    }
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

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    const tabMap = {'markets': 0, 'statistics': 1, 'leaderboard': 2};
    document.querySelectorAll('.tab')[tabMap[tabName]].classList.add('active');
    document.getElementById('tab-' + tabName).classList.add('active');
}

function getPriceData(data, symbol) {
    if (!data || !data.prices) return null;
    if (data.prices[symbol]) return data.prices[symbol];
    const altMap = {
        'GOLD': ['XAUUSD'], 'SILVER': ['XAGUSD'],
        '#NASDAQ100': ['NAS100', 'US100'], '#DJ30': ['DJ30', 'US30'],
        '#S&P500': ['SP500', 'US500'], '#RUSS2000': ['RUS2000', 'RUS2K', 'US2000'],
        '#CAC40': ['CAC40', 'FR40'], '#DAX40': ['DAX40', 'GER40'],
        '#FTSE100': ['FTSE100', 'UK100'], '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225'],
        '#DOLLAR_IND': ['#DOLLAR_IND', 'DXY', 'USDX'],
        'BRENT_OIL': ['BRENT', 'UKOIL'], 'CrudeOIL': ['CRUDE', 'USOIL']
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
            let decimals = 5;
            if (['USDJPY', 'EURJPY'].includes(symbol)) decimals = 3;
            else if (['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', 'BRENT_OIL', 'CrudeOIL'].includes(symbol)) decimals = 2;
            else if (symbol === '#DOLLAR_IND') decimals = 3;
            const spread = (ask - bid).toFixed(decimals);
            const change = priceInfo.change || 0;
            const changeClass = change >= 0 ? 'up' : 'down';
            const changeSymbol = change >= 0 ? '▲' : '▼';
            card.innerHTML = `
                <div class="card-symbol">${symbol}</div>
                <div class="card-price">${price.toFixed(decimals)}</div>
                <div class="card-change ${changeClass}">${changeSymbol} ${Math.abs(change).toFixed(2)}%</div>
                <div class="card-bid-ask">
                    <span class="bid">Bid: ${bid.toFixed(decimals)}</span>
                    <span class="ask">Ask: ${ask.toFixed(decimals)}</span>
                </div>
                <div class="card-spread">Spread: ${spread}</div>
                <div class="card-time">Updated: ${data.timestamp || '--:--:--'}</div>
            `;
            grid.appendChild(card);
        }
    });
    const countEl = document.getElementById(containerId.replace('Grid', 'Count'));
    if (countEl) countEl.textContent = `(${found} ${found === 1 ? 'item' : 'items'})`;
    if (found === 0) grid.innerHTML = '<div class="error">⚠️ No data available</div>';
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

function updateFullDashboard(data) {
    if (!data || !data.success) return;
    document.getElementById('balance').textContent = '$' + (data.balance || 0).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 0).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || 'File';
    updateAllMarketCards(data);
}

async function manualRefresh() {
    document.getElementById('refreshStatus').textContent = '⏳ Updating...';
    try {
        const response = await fetch('/api/all_data?_=' + Date.now());
        const data = await response.json();
        if (data.success) {
            currentData = data;
            updateFullDashboard(data);
            document.getElementById('refreshStatus').textContent = '✅ ' + data.timestamp;
            socket.emit('request_update');
        } else {
            document.getElementById('refreshStatus').textContent = '❌ Error';
        }
    } catch(e) {
        document.getElementById('refreshStatus').textContent = '❌ Connection error';
    }
}

function startCountdown() {
    countdown = 5;
    document.getElementById('countdown').textContent = countdown;
    setInterval(() => {
        countdown--;
        document.getElementById('countdown').textContent = countdown;
        if (countdown <= 0) {
            countdown = 5;
            manualRefresh();
        }
    }, 1000);
}

// INSTANT LOAD - No waiting!
manualRefresh();
startCountdown();
</script>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/all_data')
def api_all_data():
    return jsonify(get_all_data_dict())

@app.route('/api/prices')
def api_prices():
    data = get_all_data_dict()
    return jsonify({'success': True, 'prices': data['prices'], 'timestamp': datetime.now().isoformat()})

@app.route('/api/status')
def api_status():
    return jsonify({'status': 'running', 'timestamp': datetime.now().isoformat()})

@app.route('/api/update_mt4_data', methods=['POST'])
def update_mt4_data():
    try:
        data = request.json
        if data and data.get('prices'):
            with open('dashboard_data.json', 'w') as f:
                json.dump(data, f)
            socketio.emit('full_update', get_all_data_dict())
            return jsonify({'success': True, 'symbols': len(data.get('prices', {}))})
        return jsonify({'success': False, 'error': 'No prices'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("📊 MT4 DASHBOARD - INSTANT LOADING")
    print("=" * 60)
    print(f"📂 Symbols: {len(ALL_SYMBOLS)}")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print("=" * 60)
    
    threading.Thread(target=file_watcher, daemon=True).start()
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)