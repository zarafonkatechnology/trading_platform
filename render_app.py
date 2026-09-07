#!/usr/bin/env python3
"""
UNIFIED TRADING SYSTEM - Render Deployment
No numpy/pandas required - Python 3.14 compatible
"""

import os
import json
import logging
import time
from datetime import datetime
from flask import Flask, jsonify, render_template_string
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

SIGNALS_FILE = "signals.json"

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
# SUPABASE CLIENT (Optional)
# ============================================================

supabase = None
try:
    from supabase import create_client, Client
    
    SUPABASE_URL = os.getenv('USER_AUTH_SUPABASE_URL', 'https://unyronpybahqltrbzxas.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('USER_AUTH_SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2NTQ3MjUsImV4cCI6MjEwMDIzMDcyNX0.DMIrAaIpvvWKxbuRTN3MF9UryqnXBD9R-u47B5cUEZM')
    
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    logger.info("✅ Supabase client initialized")
except ImportError:
    logger.warning("⚠️ Supabase not available")
except Exception as e:
    logger.warning(f"⚠️ Supabase error: {e}")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

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

def get_fallback_prices():
    """Return fallback prices"""
    return {
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

def get_all_data_dict():
    """Get all data as dictionary"""
    fallback_prices = get_fallback_prices()
    
    prices = {}
    for symbol in ALL_SYMBOLS:
        price = fallback_prices.get(symbol, 0)
        prices[symbol] = {
            'bid': round(price * 0.9999, 5),
            'ask': round(price * 1.0001, 5),
            'price': round(price, 5),
            'change': 0
        }
    
    return {
        'success': True,
        'balance': 10000.00,
        'equity': 10000.00,
        'prices': prices,
        'signals': fetch_signals_from_file(),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'source': 'Render - Fallback',
        'file_exists': False
    }

# ============================================================
# WEBSOCKET
# ============================================================

connected_clients = set()

@socketio.on('connect')
def handle_connect():
    logger.info(f"🔌 Client connected: {request.sid}")
    connected_clients.add(request.sid)
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_clients:
        connected_clients.remove(request.sid)

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
    <title>📊 Trading Platform</title>
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
        <h1>📊 Trading Platform <span>Live Prices</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="status" class="status status-online">✅ ONLINE</span>
        </div>
    </div>
    
    <div class="account-box">
        <div class="account-item">
            <div class="account-label">💰 Balance</div>
            <div class="account-value gold" id="balance">$10,000.00</div>
        </div>
        <div class="account-item">
            <div class="account-label">📊 Equity</div>
            <div class="account-value green" id="equity">$10,000.00</div>
        </div>
        <div class="account-item">
            <div class="account-label">🕐 Updated</div>
            <div class="account-value" style="font-size:18px;color:#aaa;" id="updated">--:--:--</div>
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
        <div style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">Loading prices...</div>
    </div>
    
    <div class="endpoints">
        <h3 style="color:#ffd700;">🔗 API Endpoints</h3>
        <a href="/health">/health</a>
        <a href="/api/status">/api/status</a>
        <a href="/api/prices">/api/prices</a>
        <a href="/api/signals">/api/signals</a>
        <a href="/api/all_data">/api/all_data</a>
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

socket.on('full_update', function(data) {
    if (data && data.success) {
        updateDashboard(data);
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

function updateDashboard(data) {
    document.getElementById('balance').textContent = '$' + (data.balance || 10000).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 10000).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    
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
    
    const grid = document.getElementById('pricesGrid');
    if (data.prices) {
        let html = '';
        const symbols = Object.keys(data.prices);
        for (const symbol of symbols.slice(0, 30)) {
            const priceData = data.prices[symbol];
            if (!priceData || !priceData.price) continue;
            const bid = priceData.bid || priceData.price;
            const ask = priceData.ask || priceData.price;
            const price = priceData.price;
            html += `
                <div class="card">
                    <div class="card-symbol">${symbol}</div>
                    <div class="card-price">${price.toFixed(2)}</div>
                    <div class="card-bid-ask">
                        <span class="bid">Bid: ${bid.toFixed(2)}</span>
                        <span class="ask">Ask: ${ask.toFixed(2)}</span>
                    </div>
                </div>
            `;
        }
        grid.innerHTML = html || '<div style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">No price data available</div>';
    }
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
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'connected_clients': len(connected_clients)
    })

@app.route('/api/prices')
def api_prices():
    data = get_all_data_dict()
    return jsonify({
        'success': True,
        'prices': data['prices'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/signals')
def api_signals():
    signals = fetch_signals_from_file()
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/all_data')
def api_all_data():
    return jsonify(get_all_data_dict())

@app.route('/api/debug')
def debug():
    return jsonify({
        'status': 'ok',
        'signals_file_exists': os.path.exists(SIGNALS_FILE),
        'timestamp': datetime.now().isoformat()
    })

# ============================================================
# FILE WATCHER
# ============================================================

def file_watcher():
    last_mtime = 0
    while True:
        try:
            if os.path.exists(SIGNALS_FILE):
                current_mtime = os.path.getmtime(SIGNALS_FILE)
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    data = get_all_data_dict()
                    socketio.emit('full_update', data)
        except Exception as e:
            logger.debug(f"File watcher error: {e}")
        time.sleep(2)

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('\n' + '=' * 60)
    print('🚀 TRADING PLATFORM - Render Deployment')
    print('=' * 60)
    print(f'🌐 Server: http://0.0.0.0:{port}')
    print('=' * 60 + '\n')
    
    # Start file watcher
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)