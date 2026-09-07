# dashboard/unified_dashboard.py
"""
Updated Dashboard that connects to the UNIFIED controller
Displays signals from BOTH systems
"""

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from flask_socketio import SocketIO
import json
import os
import time
from datetime import datetime
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Import unified controller
from unified_trading_controller import UnifiedTradingController

# Initialize controller
controller = UnifiedTradingController({
    'forex_enabled': True,
    'indices_enabled': True,
    'metals_enabled': True,
    'energy_enabled': True,
    'dollar_enabled': True,
    'min_confidence': 60,
    'cycle_interval': 10,
    'use_hybrid': True
})

# Start controller in background
def start_controller():
    """Start the controller in a background thread"""
    controller.is_running = True
    while controller.is_running:
        try:
            result = controller.process_cycle()
            # Broadcast updates via WebSocket
            socketio.emit('market_update', result)
            time.sleep(controller.cycle_interval)
        except Exception as e:
            print(f"Controller error: {e}")
            time.sleep(5)

threading.Thread(target=start_controller, daemon=True).start()

# Routes
@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unified Trading Dashboard</title>
        <style>
            body { font-family: Arial; background: #0a0e27; color: #e0e0e0; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 20px; }
            .card { background: #16213e; padding: 15px; border-radius: 8px; border-left: 4px solid #ffd700; }
            .card .symbol { color: #ffd700; font-weight: bold; }
            .card .price { font-size: 24px; font-weight: bold; margin: 5px 0; }
            .card .change { font-size: 14px; }
            .card .change.up { color: #4caf50; }
            .card .change.down { color: #f44336; }
            .card .signal { font-size: 12px; margin-top: 5px; }
            .signal.buy { color: #4caf50; }
            .signal.sell { color: #f44336; }
            .status { padding: 8px 20px; border-radius: 20px; background: #4caf50; color: white; }
            .info { margin-top: 30px; padding: 20px; background: #16213e; border-radius: 8px; }
            .system-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; margin-left: 5px; }
            .system-tag.zscore { background: #2196F3; color: white; }
            .system-tag.engine { background: #FF9800; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Unified Trading Dashboard</h1>
                <span class="status" id="status">🟢 Online</span>
            </div>
            
            <div id="stats" style="margin: 20px 0; display: flex; gap: 20px;">
                <div>🔄 Cycle: <span id="cycle">0</span></div>
                <div>📊 Active: <span id="active">0</span></div>
                <div>💰 P&L: $<span id="pnl">0.00</span></div>
                <div>❄️ Cold Start: <span id="coldstart">Active</span></div>
            </div>
            
            <div id="signals"></div>
            
            <div class="info">
                <h3>📊 Systems</h3>
                <div id="systems">
                    <span style="background:#2196F3;padding:3px 10px;border-radius:4px;">Z-Score (Indices/Metals/Energy)</span>
                    <span style="background:#FF9800;padding:3px 10px;border-radius:4px;margin-left:10px;">Engine (Forex)</span>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <script>
            const socket = io();
            
            socket.on('market_update', function(data) {
                document.getElementById('cycle').textContent = data.cycle;
                
                // Update stats
                const active = Object.keys(window.activePositions || {}).length;
                document.getElementById('active').textContent = active;
                
                // Update signals
                const signalsDiv = document.getElementById('signals');
                let html = '<h2>📊 Signals</h2><div class="grid">';
                
                for (const [symbol, signal] of Object.entries(data.signals || {})) {
                    const action = signal.action || 'HOLD';
                    const confidence = signal.confidence || 0;
                    const price = signal.price || 0;
                    const source = signal.source || 'UNKNOWN';
                    const zScore = signal.z_score || 0;
                    
                    let systemTag = 'zscore';
                    if (source === 'ENGINE_SYSTEM' || source === 'ZSCORE_SYSTEM') {
                        systemTag = source === 'ENGINE_SYSTEM' ? 'engine' : 'zscore';
                    }
                    
                    const changeClass = action === 'BUY' ? 'up' : (action === 'SELL' ? 'down' : '');
                    const signalClass = action === 'BUY' ? 'buy' : (action === 'SELL' ? 'sell' : '');
                    
                    html += `
                        <div class="card">
                            <div class="symbol">
                                ${symbol}
                                <span class="system-tag ${systemTag}">${systemTag.toUpperCase()}</span>
                            </div>
                            <div class="price">${price.toFixed(5)}</div>
                            <div class="change ${changeClass}">
                                ${action} (${confidence.toFixed(1)}%)
                            </div>
                            <div class="signal ${signalClass}">
                                ${zScore ? `Z: ${zScore.toFixed(2)}` : ''}
                                ${signal.reasoning ? ` | ${signal.reasoning.substring(0, 30)}` : ''}
                            </div>
                        </div>
                    `;
                }
                
                html += '</div>';
                signalsDiv.innerHTML = html;
            });
        </script>
    </body>
    </html>
    """)

@app.route('/api/status')
def get_status():
    """Get full status"""
    return jsonify(controller.get_status())

@app.route('/api/signals')
def get_signals():
    """Get recent signals"""
    from core.signal_service import signal_service
    return jsonify(signal_service.get_recent_signals(50))

@app.route('/api/positions')
def get_positions():
    """Get active positions"""
    return jsonify(controller.risk_manager.active_positions)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 UNIFIED DASHBOARD")
    print("=" * 60)
    print("URL: http://localhost:5003")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=5003, debug=False, allow_unsafe_werkzeug=True)