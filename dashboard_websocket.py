"""
WebSocket Dashboard - Real-Time Price Updates
"""

import json
import os
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# File path
DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"

# Cache
last_data = {}
last_update = 0
update_interval = 0.2  # 200ms for near real-time

def read_dashboard_file():
    """Read the dashboard JSON file"""
    try:
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
                
                # Extract prices
                prices = {}
                raw_prices = data.get('prices', {})
                
                for symbol, price_data in raw_prices.items():
                    if isinstance(price_data, dict):
                        price = price_data.get('price', 0)
                    else:
                        price = float(price_data) if price_data else 0
                    
                    if price > 0:
                        prices[symbol] = price
                
                # Map alternative names
                alt_map = {
                    'XAUUSD': 'GOLD',
                    'XAGUSD': 'SILVER',
                    'NAS100': '#NASDAQ100',
                    'US100': '#NASDAQ100',
                    'SP500': '#S&P500',
                    'US500': '#S&P500',
                    'DJ30': '#DJ30',
                    'US30': '#DJ30',
                    'BRENT': 'BRENT_OIL',
                    'CRUDE': 'CrudeOIL',
                    'USOIL': 'CrudeOIL'
                }
                
                for src, dst in alt_map.items():
                    if src in prices and prices[src] > 0:
                        if dst not in prices or prices[dst] == 0:
                            prices[dst] = prices[src]
                
                # Add forex pairs (these come from MT4 via the file)
                forex_pairs = [
                    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
                    'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 
                    'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
                ]
                
                # Ensure all forex pairs have data
                for pair in forex_pairs:
                    if pair not in prices or prices[pair] == 0:
                        # Try to get from MT4 directly through the dashboard
                        pass
                
                return {
                    'success': True,
                    'prices': prices,
                    'balance': data.get('balance', 0),
                    'equity': data.get('equity', 0),
                    'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                    'source': 'dashboard_file'
                }
    except Exception as e:
        logger.error(f"File read error: {e}")
    
    return {'success': False, 'prices': {}}

def broadcast_updates():
    """Background thread to broadcast updates via WebSocket"""
    global last_data, last_update
    
    while True:
        try:
            # Read the file
            data = read_dashboard_file()
            
            if data['success']:
                current_time = time.time()
                
                # Check if data has changed
                data_changed = False
                if data['prices'] != last_data.get('prices', {}):
                    data_changed = True
                
                if data_changed or (current_time - last_update) > 1.0:
                    last_data = data
                    last_update = current_time
                    
                    # Broadcast to all connected clients
                    socketio.emit('price_update', {
                        'prices': data['prices'],
                        'balance': data['balance'],
                        'equity': data['equity'],
                        'timestamp': data['timestamp']
                    })
                    
                    logger.debug(f"📡 Broadcast: {len(data['prices'])} prices at {data['timestamp']}")
            
            time.sleep(0.1)  # Check every 100ms for near real-time
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            time.sleep(1)

# Start broadcast thread
threading.Thread(target=broadcast_updates, daemon=True).start()

@app.route('/')
def index():
    """Dashboard HTML"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>📊 Real-Time Trading Dashboard</title>
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: #0a0e27;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 20px;
                border-bottom: 2px solid #ffd700;
            }
            .header h1 { color: #ffd700; }
            .status {
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: bold;
            }
            .status.online { background: #4caf50; color: white; }
            .status.connecting { background: #ff9800; color: white; }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .card {
                background: #16213e;
                border-radius: 10px;
                padding: 15px;
                border-left: 3px solid #ffd700;
                transition: all 0.2s;
            }
            .card.update {
                animation: flash 0.2s ease;
            }
            @keyframes flash {
                0% { background: #1a3a5a; }
                100% { background: #16213e; }
            }
            .card .symbol {
                font-weight: bold;
                color: #ffd700;
                font-size: 14px;
            }
            .card .price {
                font-size: 22px;
                font-weight: bold;
                margin: 8px 0;
            }
            .card .price.up { color: #4caf50; }
            .card .price.down { color: #f44336; }
            .card .signal {
                font-size: 12px;
                margin-top: 5px;
            }
            .card .signal.buy { color: #4caf50; }
            .card .signal.sell { color: #f44336; }
            .card .signal.hold { color: #888; }
            .card .source {
                font-size: 10px;
                color: #666;
                margin-top: 5px;
            }
            .stats {
                display: flex;
                gap: 30px;
                margin: 20px 0;
                padding: 15px;
                background: #16213e;
                border-radius: 10px;
            }
            .stats .stat { text-align: center; }
            .stats .stat .label { font-size: 11px; color: #888; }
            .stats .stat .value { font-size: 20px; font-weight: bold; color: #ffd700; }
            .update-time {
                color: #666;
                font-size: 12px;
                text-align: center;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #1a1a3a;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Real-Time Trading Dashboard</h1>
                <div>
                    <span id="wsStatus" class="status connecting">🔌 Connecting...</span>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="label">💰 Balance</div>
                    <div class="value" id="balance">$---</div>
                </div>
                <div class="stat">
                    <div class="label">📊 Equity</div>
                    <div class="value" id="equity">$---</div>
                </div>
                <div class="stat">
                    <div class="label">🕐 Last Update</div>
                    <div class="value" id="updateTime" style="font-size:14px;">--:--:--</div>
                </div>
                <div class="stat">
                    <div class="label">📡 Symbols</div>
                    <div class="value" id="symbolCount">0</div>
                </div>
            </div>
            
            <div id="pricesGrid" class="grid">
                <div style="text-align:center;padding:40px;color:#666;">Waiting for data...</div>
            </div>
            
            <div class="update-time">
                WebSocket Connected | Real-Time Updates
            </div>
        </div>
        
        <script>
            const socket = io();
            let previousPrices = {};
            
            socket.on('connect', function() {
                document.getElementById('wsStatus').className = 'status online';
                document.getElementById('wsStatus').textContent = '✅ Connected';
            });
            
            socket.on('disconnect', function() {
                document.getElementById('wsStatus').className = 'status connecting';
                document.getElementById('wsStatus').textContent = '🔌 Disconnected';
            });
            
            socket.on('price_update', function(data) {
                if (data.prices) {
                    updatePrices(data.prices);
                    
                    // Update account info
                    if (data.balance !== undefined) {
                        document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                    }
                    if (data.equity !== undefined) {
                        document.getElementById('equity').textContent = '$' + data.equity.toFixed(2);
                    }
                    if (data.timestamp) {
                        document.getElementById('updateTime').textContent = data.timestamp;
                    }
                    
                    const count = Object.keys(data.prices).length;
                    document.getElementById('symbolCount').textContent = count;
                }
            });
            
            function updatePrices(prices) {
                const grid = document.getElementById('pricesGrid');
                grid.innerHTML = '';
                
                // Sort symbols
                const sortedSymbols = Object.keys(prices).sort();
                
                for (const symbol of sortedSymbols) {
                    const price = prices[symbol];
                    if (price <= 0) continue;
                    
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.id = 'card-' + symbol;
                    
                    // Determine if price changed
                    let priceClass = '';
                    if (previousPrices[symbol] !== undefined) {
                        if (price > previousPrices[symbol]) {
                            priceClass = 'up';
                            card.classList.add('update');
                        } else if (price < previousPrices[symbol]) {
                            priceClass = 'down';
                            card.classList.add('update');
                        }
                    }
                    
                    // Format price
                    let displayPrice = price;
                    let decimals = 5;
                    if (symbol.includes('JPY') || symbol === '#DOLLAR_IND') {
                        decimals = 3;
                    } else if (symbol.includes('NASDAQ') || symbol.includes('S&P') || 
                              symbol.includes('DJ') || symbol.includes('DAX') ||
                              symbol === 'GOLD' || symbol === 'BRENT_OIL') {
                        decimals = 2;
                    }
                    
                    card.innerHTML = `
                        <div class="symbol">${symbol}</div>
                        <div class="price ${priceClass}">${displayPrice.toFixed(decimals)}</div>
                        <div class="signal hold">HOLD</div>
                        <div class="source">Real-Time</div>
                    `;
                    
                    grid.appendChild(card);
                    
                    // Update previous price
                    previousPrices[symbol] = price;
                }
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/prices')
def get_prices():
    """API endpoint for prices"""
    data = read_dashboard_file()
    return jsonify(data)

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        'status': 'running',
        'websocket': True,
        'file': DASHBOARD_FILE,
        'file_exists': os.path.exists(DASHBOARD_FILE)
    })

if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('🚀 REAL-TIME TRADING DASHBOARD')
    print('=' * 60)
    print('URL: http://localhost:5002')
    print('WebSocket: ws://localhost:5002/socket.io/')
    print('=' * 60 + '\n')
    
    socketio.run(app, host='0.0.0.0', port=5002, debug=False, allow_unsafe_werkzeug=True)