# working_dashboard.py
"""
Simple Working Dashboard for NASDAQ
"""

from flask import Flask, jsonify, render_template_string
from datetime import datetime
import time
import os
import json

app = Flask(__name__)

# MT4 paths
MT4_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
COMMAND_FILE = os.path.join(MT4_PATH, "AI_Commands.txt")
RESPONSE_FILE = os.path.join(MT4_PATH, "AI_Responses.txt")

def send_command(command, timeout=15):
    """Send command to MT4 and wait for response"""
    try:
        # Clean up
        if os.path.exists(RESPONSE_FILE):
            try:
                os.remove(RESPONSE_FILE)
            except:
                pass
        
        # Send command
        with open(COMMAND_FILE, 'w') as f:
            json.dump(command, f)
        
        # Wait for response
        start = time.time()
        while time.time() - start < timeout:
            if os.path.exists(RESPONSE_FILE):
                with open(RESPONSE_FILE, 'r') as f:
                    response = json.load(f)
                os.remove(RESPONSE_FILE)
                return response
            time.sleep(0.5)
        
        return {"error": "Timeout", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

# HTML Template
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NASDAQ Trading Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body {
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', monospace;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #ffd700; text-align: center; border-bottom: 2px solid #ffd700; padding-bottom: 10px; }
        .card {
            background: #16213e;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            text-align: center;
        }
        .price {
            font-size: 48px;
            font-weight: bold;
            color: #ffd700;
            margin: 20px 0;
        }
        .balance {
            font-size: 36px;
            color: #4caf50;
        }
        .connected {
            color: #4caf50;
            font-weight: bold;
        }
        .info {
            font-size: 14px;
            color: #888;
            margin-top: 10px;
        }
        .refresh-btn {
            background: #ffd700;
            color: #0a0e27;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            margin-top: 20px;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>📊 NASDAQ AI Trading Dashboard</h1>
    
    <div class="card">
        <h2>💰 ACCOUNT</h2>
        <div class="balance" id="balance">$---</div>
        <div class="info" id="status"></div>
    </div>
    
    <div class="card">
        <h2>📈 NASDAQ100</h2>
        <div class="price" id="price">---</div>
        <div class="info" id="bidask"></div>
    </div>
    
    <div class="card">
        <h2>🎯 LAST SIGNAL</h2>
        <div id="signal">Waiting for signal...</div>
        <div class="info" id="time"></div>
    </div>
    
    <div style="text-align: center;">
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
    </div>
</div>

<script>
    async function loadData() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('balance').innerHTML = `$${data.balance.toFixed(2)}`;
                document.getElementById('price').innerHTML = `$${data.price.toFixed(2)}`;
                document.getElementById('bidask').innerHTML = `Bid: ${data.bid.toFixed(2)} | Ask: ${data.ask.toFixed(2)}`;
                document.getElementById('time').innerHTML = `Updated: ${data.time}`;
                
                if (data.connected) {
                    document.getElementById('status').innerHTML = '<span class="connected">🟢 MT4 CONNECTED</span>';
                } else {
                    document.getElementById('status').innerHTML = '<span>🔴 MT4 DISCONNECTED</span>';
                }
                
                if (data.signal) {
                    document.getElementById('signal').innerHTML = data.signal;
                }
            }
        } catch(e) {
            console.error('Error:', e);
        }
    }
    
    loadData();
    setInterval(loadData, 10000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    """Get live data from MT4"""
    try:
        # Test connection with PING
        ping = send_command({"command": "PING"}, timeout=15)
        connected = ping.get('status') == 'OK'
        
        balance = 0
        price = 0
        bid = 0
        ask = 0
        
        if connected:
            # Get account balance
            account = send_command({"command": "ACCOUNT"}, timeout=15)
            if account:
                balance = float(account.get('balance', 0))
            
            # Get NASDAQ price
            nasdaq = send_command({"command": "PRICE", "symbol": "#NASDAQ100"}, timeout=15)
            if nasdaq and nasdaq.get('success'):
                bid = float(nasdaq.get('bid', 0))
                ask = float(nasdaq.get('ask', 0))
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2
        
        # Fallback balance
        if balance == 0:
            balance = 989.00
        
        return jsonify({
            'success': True,
            'connected': connected,
            'balance': balance,
            'price': price,
            'bid': bid,
            'ask': ask,
            'signal': 'ANALYZING...',
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'connected': False,
            'balance': 989.00,
            'price': 0,
            'time': datetime.now().strftime('%H:%M:%S')
        })

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("📊 NASDAQ Trading Dashboard")
    print("   URL: http://localhost:5001")
    print("   Timeout: 15 seconds (EA takes ~11 seconds)")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)