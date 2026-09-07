#!/usr/bin/env python3
"""
UNIFIED TRADING SYSTEM - Render Deployment
Receives MT4 data via HTTP POST from Windows machine
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
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
# CONFIGURATION
# ============================================================

# On Render, the file will be saved in the app directory
DASHBOARD_FILE = "dashboard_data.json"
SIGNALS_FILE = "signals.json"

logger.info(f"📂 MT4 data file: {DASHBOARD_FILE}")

# ============================================================
# SYMBOL CONFIGURATION
# ============================================================

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

connected_clients = set()
last_file_mod_time = 0
mt4_data_available = False

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_data_dict():
    """Get all data as dictionary"""
    try:
        data = None
        source = "Fallback (No MT4 Data) ❌"
        mt4_connected = False
        
        # Check if we have MT4 data
        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    data = json.load(f)
                if data and data.get('prices'):
                    source = "MT4 Live Data ✅"
                    mt4_connected = True
                    logger.info(f"✅ MT4 data loaded from {DASHBOARD_FILE}")
            except Exception as e:
                logger.warning(f"⚠️ Error reading MT4 file: {e}")
        
        # Fallback prices (used only if no MT4 data)
        fallback = {
            'EURUSD': 1.14317, 'GBPUSD': 1.34154, 'USDJPY': 162.441,
            'USDCHF': 0.89510, 'AUDUSD': 0.67260, 'USDCAD': 1.36530,
            'NZDUSD': 0.61240, 'EURGBP': 0.85210, 'EURJPY': 185.635,
            'EURCAD': 1.56010, 'EURNZD': 1.86510, 'EURCHF': 0.95410,
            'GOLD': 3987.70, 'SILVER': 31.28,
            '#NASDAQ100': 21500.25, '#DJ30': 41500.25, '#S&P500': 5600.13,
            '#RUSS2000': 2200.13, '#CAC40': 7650.25, '#DAX40': 18800.25,
            '#FTSE100': 8350.25, '#NIKKEI225': 41200.25,
            'BRENT_OIL': 85.55, 'CrudeOIL': 80.80,
            '#DOLLAR_IND': 104.55
        }
        
        response = {
            'success': True,
            'balance': 10000.00,
            'equity': 10000.00,
            'prices': {},
            'stats': {},
            'leaderboard': [],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': source,
            'file_exists': os.path.exists(DASHBOARD_FILE),
            'mt4_connected': mt4_connected
        }
        
        # Build prices from MT4 data or fallback
        if data and data.get('prices'):
            # Use MT4 data
            for symbol in ALL_SYMBOLS:
                if symbol in data['prices']:
                    price_data = data['prices'][symbol]
                    if isinstance(price_data, dict):
                        response['prices'][symbol] = {
                            'bid': float(price_data.get('bid', 0)),
                            'ask': float(price_data.get('ask', 0)),
                            'price': float(price_data.get('price', 0)),
                            'change': float(price_data.get('change', 0))
                        }
                    else:
                        p = float(price_data)
                        response['prices'][symbol] = {
                            'bid': p,
                            'ask': p,
                            'price': p,
                            'change': 0
                        }
                else:
                    # Try alternative names
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
                    found = False
                    if symbol in alt_map:
                        for alt in alt_map[symbol]:
                            if alt in data['prices']:
                                price_data = data['prices'][alt]
                                if isinstance(price_data, dict):
                                    response['prices'][symbol] = {
                                        'bid': float(price_data.get('bid', 0)),
                                        'ask': float(price_data.get('ask', 0)),
                                        'price': float(price_data.get('price', 0)),
                                        'change': float(price_data.get('change', 0))
                                    }
                                else:
                                    p = float(price_data)
                                    response['prices'][symbol] = {
                                        'bid': p,
                                        'ask': p,
                                        'price': p,
                                        'change': 0
                                    }
                                found = True
                                break
                    
                    if not found:
                        p = fallback.get(symbol, 0)
                        response['prices'][symbol] = {
                            'bid': round(p * 0.9999, 5),
                            'ask': round(p * 1.0001, 5),
                            'price': round(p, 5),
                            'change': 0
                        }
            
            # Update balance from MT4 data
            if 'balance' in data:
                response['balance'] = float(data['balance'])
            if 'equity' in data:
                response['equity'] = float(data['equity'])
            if 'timestamp' in data:
                response['timestamp'] = data['timestamp']
        else:
            # Use fallback (no MT4 data)
            for symbol in ALL_SYMBOLS:
                p = fallback.get(symbol, 0)
                response['prices'][symbol] = {
                    'bid': round(p * 0.9999, 5),
                    'ask': round(p * 1.0001, 5),
                    'price': round(p, 5),
                    'change': 0
                }
        
        return response
        
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

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
        'mt4_connected': data.get('mt4_connected', False),
        'timestamp': datetime.now().isoformat()
    })

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
# HTML TEMPLATE
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 MT4 Trading Dashboard</title>
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
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 MT4 Trading Dashboard <span>Live Prices</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="mt4Status" class="status status-offline">📡 MT4: Disconnected ❌</span>
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
        <a href="/api/all_data">/api/all_data</a>
        <a href="/api/update_mt4_data">/api/update_mt4_data (POST)</a>
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
    if (data && data.mt4_connected) {
        document.getElementById('mt4Status').className = 'status status-mt4';
        document.getElementById('mt4Status').textContent = '📡 MT4: Connected ✅';
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
    
    // Update account
    document.getElementById('balance').textContent = '$' + (data.balance || 10000).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 10000).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || '--';
    
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
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'mt4_file_exists': os.path.exists(DASHBOARD_FILE)
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'connected_clients': len(connected_clients),
        'mt4_file_exists': os.path.exists(DASHBOARD_FILE)
    })

@app.route('/api/prices')
def api_prices():
    data = get_all_data_dict()
    return jsonify({
        'success': True,
        'prices': data['prices'],
        'timestamp': datetime.now().isoformat(),
        'count': len(data['prices'])
    })

@app.route('/api/all_data')
def api_all_data():
    return jsonify(get_all_data_dict())

@app.route('/api/update_mt4_data', methods=['POST'])
def update_mt4_data():
    """
    Receive MT4 data from Windows machine via HTTP POST
    This is the endpoint that your Windows script will call
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        if data.get('prices'):
            # Save to file
            with open(DASHBOARD_FILE, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"✅ MT4 data updated via POST: {len(data.get('prices', {}))} symbols")
            
            # Broadcast update to all connected clients
            full_data = get_all_data_dict()
            socketio.emit('full_update', full_data)
            
            # Also send price update
            socketio.emit('price_update', {
                'prices': data['prices'],
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            return jsonify({
                'success': True,
                'message': 'MT4 data updated successfully',
                'symbols': len(data.get('prices', {}))
            })
        else:
            return jsonify({'success': False, 'error': 'No prices in data'}), 400
            
    except Exception as e:
        logger.error(f"❌ Error updating MT4 data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('\n' + '=' * 60)
    print('📊 MT4 TRADING DASHBOARD')
    print('=' * 60)
    print(f'📂 Looking for: {DASHBOARD_FILE}')
    print(f'📡 MT4 Data: {"✅ EXISTS" if os.path.exists(DASHBOARD_FILE) else "❌ NOT FOUND"}')
    print(f'🌐 Server: http://0.0.0.0:{port}')
    print(f'📤 POST endpoint: /api/update_mt4_data')
    print('=' * 60 + '\n')
    
    # Start file watcher
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    logger.info("✅ File watcher thread started")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)