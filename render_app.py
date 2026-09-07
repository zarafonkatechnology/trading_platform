#!/usr/bin/env python3
"""
📊 MT4 TRADING DASHBOARD - INSTANT
No delays - instant updates via WebSocket
"""

import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# SYMBOLS
# ============================================================

FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', "#AMAZON", '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD']
METALS = ['GOLD', 'SILVER']
ENERGY = ['BRENT_OIL', 'CrudeOIL']
DOLLAR = ['#DOLLAR_IND']

ALL_SYMBOLS = FOREX_MAJORS + FOREX_CROSSES + INDICES + METALS + ENERGY + DOLLAR

# ============================================================
# FILE PATH
# ============================================================

DASHBOARD_FILE = "dashboard_data.json"

# ============================================================
# GLOBALS
# ============================================================

current_data = {'prices': {}, 'balance': 0, 'equity': 0, 'timestamp': ''}
connected_clients = set()

# ============================================================
# FUNCTIONS
# ============================================================

def get_all_data_dict():
    """Get all data - INSTANT"""
    try:
        data = None
        source = "Fallback ❌"
        mt4_connected = False

        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    data = json.load(f)
                source = "MT4 Live ✅"
                mt4_connected = True
            except:
                pass

        response = {
            'success': True,
            'balance': data.get('balance', 10000) if data else 10000,
            'equity': data.get('equity', 10000) if data else 10000,
            'prices': {},
            'timestamp': data.get('timestamp', datetime.now().strftime('%H:%M:%S')) if data else datetime.now().strftime('%H:%M:%S'),
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
                        response['prices'][symbol] = {'bid': p, 'ask': p, 'price': p, 'change': 0}
                else:
                    p = fallback.get(symbol, 0)
                    response['prices'][symbol] = {'bid': p * 0.9999, 'ask': p * 1.0001, 'price': p, 'change': 0}
        else:
            for symbol in ALL_SYMBOLS:
                p = fallback.get(symbol, 0)
                response['prices'][symbol] = {'bid': p * 0.9999, 'ask': p * 1.0001, 'price': p, 'change': 0}

        return response
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================================
# WEBSOCKET - INSTANT
# ============================================================

@socketio.on('connect')
def handle_connect():
    connected_clients.add(request.sid)
    print(f"🔌 Client connected: {request.sid}")
    emit('full_update', get_all_data_dict())

@socketio.on('disconnect')
def handle_disconnect():
    connected_clients.discard(request.sid)
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_request_update():
    emit('full_update', get_all_data_dict())

# ============================================================
# HTML TEMPLATE
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 MT4 Dashboard - Real-Time</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0e27; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #ffd700; padding-bottom: 15px; }
        .header h1 { color: #ffd700; font-size: 24px; }
        .status { padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; }
        .status-online { background: #4caf50; color: white; }
        .status-offline { background: #f44336; color: white; }
        .status-ws { background: #2196F3; color: white; }
        .status-mt4 { background: #ff9800; color: white; }
        .account-box { background: #1a2a4a; border-radius: 10px; padding: 15px; margin-bottom: 20px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px; }
        .account-item { text-align: center; }
        .account-label { font-size: 10px; color: #aaa; text-transform: uppercase; }
        .account-value { font-size: 22px; font-weight: bold; margin-top: 3px; }
        .account-value.gold { color: #ffd700; }
        .account-value.green { color: #4caf50; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 15px; }
        .card { background: #16213e; border-radius: 10px; padding: 15px; border-left: 3px solid #ffd700; }
        .card-symbol { font-size: 13px; font-weight: bold; color: #ffd700; }
        .card-price { font-size: 20px; font-weight: bold; margin: 5px 0; }
        .card-bid-ask { font-size: 10px; color: #aaa; display: flex; justify-content: space-between; border-top: 1px solid #2a2a4a; padding-top: 5px; }
        .card-bid-ask .bid { color: #4caf50; }
        .card-bid-ask .ask { color: #ff6b35; }
        .card-spread { font-size: 10px; color: #888; }
        .refresh-btn { background: #ffd700; color: #0a0e27; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 15px; }
        .refresh-btn:hover { opacity: 0.8; }
        .ip-info { color: #666; font-size: 11px; text-align: center; margin-top: 20px; border-top: 1px solid #1a1a3a; padding-top: 15px; }
        @media (max-width: 600px) { .account-box { flex-direction: column; } .grid { grid-template-columns: 1fr 1fr; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 MT4 Dashboard <span style="font-size:14px;color:#888;">Real-Time</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="mt4Status" class="status status-offline">📡 MT4: Waiting</span>
        </div>
    </div>
    
    <div class="account-box">
        <div class="account-item"><div class="account-label">💰 Balance</div><div class="account-value gold" id="balance">$---</div></div>
        <div class="account-item"><div class="account-label">📊 Equity</div><div class="account-value green" id="equity">$---</div></div>
        <div class="account-item"><div class="account-label">🕐 Updated</div><div class="account-value" style="font-size:16px;color:#aaa;" id="updated">--:--:--</div></div>
        <div class="account-item"><div class="account-label">📡 Data Source</div><div class="account-value" style="font-size:14px;color:#ffd700;" id="dataSource">--</div></div>
    </div>
    
    <button class="refresh-btn" onclick="manualRefresh()">🔄 Refresh</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <div class="grid" id="pricesGrid">
        <div style="text-align:center;padding:30px;color:#666;grid-column:1/-1;">Loading prices...</div>
    </div>
    
    <div class="ip-info">⚡ Real-Time WebSocket | Auto-update every 50ms</div>
</div>

<script>
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
        updateDashboard(data);
    }
});

socket.on('price_update', function(data) {
    if (data && data.prices) {
        updatePricesOnly(data.prices);
        if (data.timestamp) {
            document.getElementById('updated').textContent = data.timestamp;
        }
    }
});

function getCardType(symbol) {
    const forex = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
    const indices = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', '#AMAZON', '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD'];
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
    let count = 0;
    const symbols = Object.keys(prices);
    
    for (const symbol of symbols) {
        const priceData = prices[symbol];
        if (!priceData || !priceData.price) continue;
        count++;
        
        const cardType = getCardType(symbol);
        const price = priceData.price;
        const bid = priceData.bid || price;
        const ask = priceData.ask || price;
        const decimals = getDecimals(symbol);
        
        html += `
            <div class="card card-${cardType}">
                <div class="card-symbol">${symbol}</div>
                <div class="card-price">${price.toFixed(decimals)}</div>
                <div class="card-bid-ask">
                    <span class="bid">Bid: ${bid.toFixed(decimals)}</span>
                    <span class="ask">Ask: ${ask.toFixed(decimals)}</span>
                </div>
                <div class="card-spread">Spread: ${(ask - bid).toFixed(decimals)}</div>
            </div>
        `;
    }
    
    grid.innerHTML = html || '<div style="text-align:center;padding:30px;color:#666;grid-column:1/-1;">No price data available</div>';
}

function updateDashboard(data) {
    // Update MT4 status
    const mt4Status = document.getElementById('mt4Status');
    if (data.mt4_connected) {
        mt4Status.className = 'status status-mt4';
        mt4Status.textContent = '📡 MT4: Connected ✅';
    } else {
        mt4Status.className = 'status status-offline';
        mt4Status.textContent = '📡 MT4: Disconnected ❌';
    }
    
    document.getElementById('balance').textContent = '$' + (data.balance || 0).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 0).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || '--';
    
    updatePricesOnly(data.prices);
}

async function manualRefresh() {
    document.getElementById('refreshStatus').textContent = '⏳ Loading...';
    try {
        const response = await fetch('/api/all_data?_=' + Date.now());
        const data = await response.json();
        if (data.success) {
            updateDashboard(data);
            document.getElementById('refreshStatus').textContent = '✅ Updated ' + data.timestamp;
            socket.emit('request_update');
        }
    } catch(e) {
        document.getElementById('refreshStatus').textContent = '❌ Error';
    }
}

manualRefresh();
</script>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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
    """INSTANT update - receives data from Windows and broadcasts to WebSocket clients"""
    try:
        data = request.json
        if data and data.get('prices'):
            # Save to file (for fallback)
            with open(DASHBOARD_FILE, 'w') as f:
                json.dump(data, f)
            
            # Get updated data
            full_data = get_all_data_dict()
            
            # ⭐ BROADCAST TO ALL WEBSOCKET CLIENTS INSTANTLY
            socketio.emit('full_update', full_data)
            socketio.emit('price_update', {
                'prices': data['prices'],
                'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
            })
            
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
    print("📊 MT4 DASHBOARD - REAL-TIME WEBSOCKET")
    print("=" * 60)
    print(f"📂 Symbols: {len(ALL_SYMBOLS)}")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"⚡ WebSocket: ws://0.0.0.0:{port}/socket.io/")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)