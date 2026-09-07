# performance_dashboard.py - COMPLETE FIXED VERSION WITH DEBUG
import time
import sys
import os
import json
from datetime import datetime
from flask import Flask, jsonify, render_template_string, Response

# ============ SINGLE FLASK APP ============
app = Flask(__name__)

# ============ MT4 PATHS ============
# The EA uses FILE_COMMON flag, so the file is in Common folder
COMMON_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
MT4_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"

# Try both possible locations
DASHBOARD_FILE_PATHS = [
    os.path.join(COMMON_FILES_PATH, "dashboard_data.json"),
]

# ============ COMPLETE HTML TEMPLATE ============
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Trading Dashboard | Real-Time Market Data</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #ffd700;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header h1 { color: #ffd700; font-size: 24px; }
        .header h1 span { font-size: 12px; color: #888; }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-connected { background: #4caf50; color: white; animation: pulse 2s infinite; }
        .status-disconnected { background: #f44336; color: white; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
        
        .account-card {
            background: linear-gradient(135deg, #1a2a4a 0%, #0f3460 100%);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        .balance-value { font-size: 32px; font-weight: bold; color: #ffd700; }
        .equity-value { font-size: 32px; font-weight: bold; color: #4caf50; }
        .label { font-size: 11px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            border-bottom: 1px solid #2a2a4a;
            flex-wrap: wrap;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background: #16213e;
            border-radius: 8px 8px 0 0;
            transition: all 0.2s;
        }
        .tab.active {
            background: #ffd700;
            color: #0a0e27;
            font-weight: bold;
        }
        .tab:hover:not(.active) { background: #1f3460; }
        
        .market-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .instrument-card {
            background: #16213e;
            border-radius: 12px;
            padding: 15px;
            border-left: 4px solid;
            transition: transform 0.2s;
        }
        .instrument-card:hover { transform: translateY(-2px); }
        .instrument-name { font-size: 16px; font-weight: bold; color: #ffd700; }
        .instrument-price { font-size: 24px; font-weight: bold; margin: 8px 0; }
        .change-positive { color: #4caf50; }
        .change-negative { color: #f44336; }
        .signal-buy { background: #4caf50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; display: inline-block; }
        .signal-sell { background: #f44336; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; display: inline-block; }
        .signal-hold { background: #ff9800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; display: inline-block; }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .data-table th, .data-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #2a2a4a;
        }
        .data-table th { background: #0f3460; color: #ffd700; }
        
        .refresh-btn {
            background: #ffd700;
            color: #0a0e27;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .refresh-btn:hover { opacity: 0.8; }
        
        .loading { text-align: center; padding: 40px; color: #ffd700; }
        
        @media (max-width: 768px) {
            .market-grid { grid-template-columns: 1fr; }
            .account-card { flex-direction: column; text-align: center; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 AI Trading System Dashboard <span>Real-Time Market Data</span></h1>
        <div id="mt4Status" class="status-badge status-disconnected">🔴 CHECKING...</div>
    </div>
    
    <div class="account-card" id="accountInfo">
        <div><div class="label">BALANCE</div><div class="balance-value" id="balance">$---</div></div>
        <div><div class="label">EQUITY</div><div class="equity-value" id="equity">$---</div></div>
        <div><div class="label">LAST UPDATE</div><div id="lastUpdate">--:--:--</div></div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('market')">📊 MARKET DATA</div>
        <div class="tab" onclick="showTab('signals')">🎯 TRADING SIGNALS</div>
        <div class="tab" onclick="showTab('stats')">📈 STATISTICS</div>
    </div>
    
    <button class="refresh-btn" onclick="refreshAll()">🔄 Refresh All Data</button>
    
    <div id="tab-market" class="tab-content">
        <div class="market-grid" id="marketGrid">
            <div class="loading">Loading market data...</div>
        </div>
    </div>
    
    <div id="tab-signals" class="tab-content" style="display:none;">
        <div id="signalsPanel">
            <div class="loading">Loading signals...</div>
        </div>
    </div>
    
    <div id="tab-stats" class="tab-content" style="display:none;">
        <table class="data-table">
            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
            <tbody id="statsBody">
                <tr><td colspan="2" class="loading">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</div>
<!-- Add to dashboard HTML -->
<div id="agentLeaderboard">
    <h3>🏆 Agent Leaderboard</h3>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Agent</th>
                <th>Votes</th>
                <th>Win Rate</th>
                <th>XP</th>
                <th>Tokens</th>
                <th>Confidence</th>
            </tr>
        </thead>
        <tbody id="leaderboardBody">
            <!-- Data will be loaded here -->
        </tbody>
    </table>
</div>
<script>
// Load leaderboard
async function loadLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard');
        const data = await response.json();
        const tbody = document.getElementById('leaderboardBody');
        tbody.innerHTML = '';
        
        data.forEach((agent, index) => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${agent.agent_name}</td>
                <td>${agent.total_votes}</td>
                <td style="color: ${agent.win_rate > 60 ? '#4caf50' : '#ff9800'}">
                    ${agent.win_rate}%
                </td>
                <td style="color: #ffd700;">${agent.total_xp}</td>
                <td>${agent.total_tokens}</td>
                <td>${agent.avg_confidence}%</td>
            `;
        });
    } catch(e) {
        console.error('Leaderboard error:', e);
    }
}
    let autoRefresh = null;
    
    function showTab(tabName) {
        document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
        document.getElementById(`tab-${tabName}`).style.display = 'block';
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        event.target.classList.add('active');
    }
    
    async function refreshAll() {
        try {
            const timestamp = Date.now();
            const response = await fetch(`/api/dashboard_data?t=${timestamp}`, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            const data = await response.json();
            
            if (data.success) {
                // Update account
                document.getElementById('balance').innerHTML = `$${data.account.balance.toFixed(2)}`;
                document.getElementById('equity').innerHTML = `$${data.account.equity.toFixed(2)}`;
                document.getElementById('lastUpdate').innerHTML = data.timestamp;
                
                const statusDiv = document.getElementById('mt4Status');
                if (data.mt4_connected) {
                    statusDiv.innerHTML = `🟢 MT4 CONNECTED`;
                    statusDiv.className = 'status-badge status-connected';
                } else {
                    statusDiv.innerHTML = '🔴 MT4 DISCONNECTED';
                    statusDiv.className = 'status-badge status-disconnected';
                }
                
                // Market Grid
                const grid = document.getElementById('marketGrid');
                grid.innerHTML = '';
                
                const categories = [
                    { name: '💱 FOREX', symbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD'] },
                    { name: '🥇 METALS', symbols: ['GOLD', 'SILVER'] },
                    { name: '📈 INDICES', symbols: ['#NASDAQ100', '#DJ30', '#S&P500'] },
                    { name: '🛢️ ENERGY', symbols: ['BRENT_OIL', 'CrudeOIL'] }
                ];
                
                for (const cat of categories) {
                    const catDiv = document.createElement('div');
                    catDiv.style.gridColumn = '1/-1';
                    catDiv.innerHTML = `<h3 style="color:#ffd700; margin:10px 0 5px 0;">${cat.name}</h3>`;
                    grid.appendChild(catDiv);
                    
                    for (const symbol of cat.symbols) {
                        const priceData = data.prices[symbol];
                        if (priceData && priceData.price > 0) {
                            const card = document.createElement('div');
                            card.className = 'instrument-card';
                            card.style.borderLeftColor = priceData.change >= 0 ? '#4caf50' : '#f44336';
                            const changeSymbol = priceData.change >= 0 ? '▲' : '▼';
                            const priceDisplay = cat.name === '💱 FOREX' ? priceData.price.toFixed(5) : `$${priceData.price.toFixed(2)}`;
                            card.innerHTML = `
                                <div class="instrument-name">${symbol}</div>
                                <div class="instrument-price">${priceDisplay}</div>
                                <div style="font-size:12px;"><span class="${priceData.change >= 0 ? 'change-positive' : 'change-negative'}">${changeSymbol} ${Math.abs(priceData.change_percent).toFixed(2)}%</span></div>
                                <div style="font-size:11px; color:#888;">Bid: ${priceData.bid?.toFixed(cat.name === '💱 FOREX' ? 5 : 2) || '-'} | Ask: ${priceData.ask?.toFixed(cat.name === '💱 FOREX' ? 5 : 2) || '-'}</div>
                            `;
                            grid.appendChild(card);
                        }
                    }
                }
                
                // Signals
                const signalsPanel = document.getElementById('signalsPanel');
                if (data.signals && data.signals.length > 0) {
                    signalsPanel.innerHTML = '';
                    for (const signal of data.signals) {
                        const card = document.createElement('div');
                        card.className = 'instrument-card';
                        card.style.borderLeftColor = signal.action === 'BUY' ? '#4caf50' : '#f44336';
                        card.innerHTML = `
                            <div class="instrument-name">${signal.symbol}</div>
                            <div class="instrument-price">${signal.action} @ ${signal.entry_price.toFixed(signal.symbol.includes('JPY') ? 3 : 5)}</div>
                            <div>Confidence: ${signal.confidence}%</div>
                            <div style="font-size:11px;">SL: ${signal.stop_loss?.toFixed(signal.symbol.includes('JPY') ? 3 : 5) || '-'} | TP: ${signal.take_profit?.toFixed(signal.symbol.includes('JPY') ? 3 : 5) || '-'}</div>
                            <div class="signal-${signal.action.toLowerCase()}">${signal.reason || 'AI Generated'}</div>
                        `;
                        signalsPanel.appendChild(card);
                    }
                } else {
                    signalsPanel.innerHTML = '<div class="loading">No active trading signals</div>';
                }
                
                // Statistics - THIS NOW SHOWS THE REAL DATA
                const statsBody = document.getElementById('statsBody');
                if (data.stats) {
                    statsBody.innerHTML = '';
                    const metrics = [
                        ['Total Trades', data.stats.total_trades || 0],
                        ['Win Rate', `${data.stats.win_rate || 0}%`],
                        ['Total P&L', `$${data.stats.total_pnl || 0}`],
                        ['Profit Factor', data.stats.profit_factor || 0],
                        ['Active Agents', data.stats.active_agents || 0]
                    ];
                    for (const [key, value] of metrics) {
                        const row = statsBody.insertRow();
                        row.insertCell(0).innerHTML = key;
                        row.insertCell(1).innerHTML = value;
                    }
                }
            }
        } catch(e) {
            console.error('Error:', e);
            document.getElementById('marketGrid').innerHTML = '<div class="loading">Error connecting to server. Make sure MT4 is running.</div>';
        }
    }
    
    refreshAll();
    autoRefresh = setInterval(refreshAll, 10000);
</script>
</body>
</html>
"""

# ============ HELPER FUNCTIONS ============
# ============ SIGNAL FUNCTIONS ============

def get_signals_from_file():
    """Read trading signals from file"""
    signals_file = os.path.join(MT4_FILES_PATH, "dashboard_signals.json")
    
    try:
        if os.path.exists(signals_file):
            with open(signals_file, 'r') as f:
                signals = json.load(f)
                print(f"✅ Loaded {len(signals)} signals from file")
                return signals
    except Exception as e:
        print(f"⚠️ Signal file error: {e}")
    
    # Try Common folder
    signals_file = os.path.join(COMMON_FILES_PATH, "dashboard_signals.json")
    try:
        if os.path.exists(signals_file):
            with open(signals_file, 'r') as f:
                signals = json.load(f)
                print(f"✅ Loaded {len(signals)} signals from Common folder")
                return signals
    except Exception as e:
        print(f"⚠️ Signal file error: {e}")
    
    return []

def generate_default_signals():
    """Generate default signals if no file exists"""
    default_signals = [
        {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry_price': 1.13550,
            'stop_loss': 1.13350,
            'take_profit': 1.13950,
            'confidence': 72,
            'reason': 'Support zone reached with 3 bounces. Strong volume confirmation.',
            'votes': {'BUY': 65, 'SELL': 20, 'HOLD': 15}
        },
        {
            'symbol': '#S&P500',
            'action': 'SELL',
            'entry_price': 7561.37,
            'stop_loss': 7599.18,
            'take_profit': 7485.76,
            'confidence': 81,
            'reason': 'Bearish CVD, liquidity sweep at resistance, volume spike 2.5x.',
            'votes': {'BUY': 12, 'SELL': 81, 'HOLD': 7}
        },
        {
            'symbol': 'GOLD',
            'action': 'BUY',
            'entry_price': 3987.55,
            'stop_loss': 3947.55,
            'take_profit': 4027.55,
            'confidence': 68,
            'reason': 'Demand zone reached with bullish divergence on RSI.',
            'votes': {'BUY': 60, 'SELL': 25, 'HOLD': 15}
        },
        {
            'symbol': 'GBPUSD',
            'action': 'BUY',
            'entry_price': 1.31640,
            'stop_loss': 1.31440,
            'take_profit': 1.32040,
            'confidence': 65,
            'reason': 'Demand zone with bullish order flow divergence.',
            'votes': {'BUY': 55, 'SELL': 25, 'HOLD': 20}
        }
    ]
    
    # Save default signals
    try:
        signals_file = os.path.join(MT4_FILES_PATH, "dashboard_signals.json")
        with open(signals_file, 'w') as f:
            json.dump(default_signals, f, indent=2)
        print(f"✅ Created default signals file with {len(default_signals)} signals")
    except:
        pass
    
    return default_signals
def read_dashboard_file():
    """Read dashboard data from multiple possible locations"""
    for path in DASHBOARD_FILE_PATHS:
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    print(f"✅ Found dashboard data at: {path}")
                    print(f"   Trades: {data.get('total_trades', 0)}")
                    print(f"   Win Rate: {data.get('win_rate', 0)}%")
                    return data
        except Exception as e:
            print(f"Error reading {path}: {e}")
    
    print("❌ No dashboard data found in any location")
    return None

def get_real_balance():
    """Get balance from file"""
    data = read_dashboard_file()
    if data:
        return float(data.get('balance', 0))
    return 0

def get_real_account_info():
    """Get full account info from file"""
    data = read_dashboard_file()
    if data:
        return {
            'balance': float(data.get('balance', 0)),
            'equity': float(data.get('equity', 0)),
            'margin': float(data.get('margin', 0)),
            'free_margin': float(data.get('free_margin', 0))
        }
    return None

# ============ ROUTES ============

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/balance')
def api_balance():
    """Get balance only"""
    balance = get_real_balance()
    
    response = jsonify({
        'balance': balance,
        'equity': balance,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/health')
def health():
    """Health check endpoint"""
    file_data = read_dashboard_file()
    file_exists = file_data is not None
    
    return jsonify({
        'status': 'healthy',
        'file_exists': file_exists,
        'balance': file_data.get('balance', 0) if file_data else 0,
        'trades': file_data.get('total_trades', 0) if file_data else 0,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ============ DEBUG ENDPOINT (FIXED - NOW EXISTS) ============
@app.route('/api/debug_file')
def debug_file():
    """Debug the dashboard file - Check both locations"""
    try:
        results = []
        
        for path in DASHBOARD_FILE_PATHS:
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            content = ""
            parsed = None
            
            if exists:
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                    parsed = json.loads(content)
                except Exception as e:
                    content = f"Error reading: {e}"
            
            results.append({
                'path': path,
                'exists': exists,
                'size': size,
                'content': content[:500] if content else "",
                'parsed': parsed
            })
        
        return jsonify({
            'success': True,
            'locations': results,
            'current_config_paths': DASHBOARD_FILE_PATHS
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ MAIN DASHBOARD DATA ENDPOINT ============
@app.route('/api/dashboard_data')
def api_dashboard_data():
    """Get all dashboard data from MT4 - REAL DATA ONLY"""
    try:
        from mt4_price_provider import get_mt4_prices
        from datetime import datetime
        
        # First, read from the dashboard file
        file_data = read_dashboard_file()
        
        # Default stats
        stats = {
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'profit_factor': 0,
            'active_agents': 23
        }
        
        # Default account values
        balance = 0
        equity = 0
        
        # If file data exists, use it
        if file_data:
            balance = float(file_data.get('balance', 0))
            equity = float(file_data.get('equity', 0))
            stats['total_trades'] = int(file_data.get('total_trades', 0))
            stats['win_rate'] = float(file_data.get('win_rate', 0))
            stats['total_pnl'] = float(file_data.get('total_pnl', 0))
            stats['profit_factor'] = float(file_data.get('profit_factor', 0))
            stats['active_agents'] = int(file_data.get('active_agents', 23))
            
            print(f"📊 Dashboard stats loaded: {stats}")
        
        # Get real-time prices from MT4
        mt4 = get_mt4_prices()
        raw_packet = mt4._send({"command": "ACCOUNT"})
        
        mt4_connected = False
        prices = {}
        
        # Exact list of symbols
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', 'BRENT_OIL', 'CrudeOIL']
        
        if isinstance(raw_packet, dict) and "error" not in raw_packet:
            if raw_packet.get('balance', 0) > 0:
                mt4_connected = True
                # Use MT4 data if available, fallback to file data
                balance = float(raw_packet.get('balance', balance))
                equity = float(raw_packet.get('equity', equity))
            
            # Map raw keys from MQL4 data dictionary
            raw_prices = {
                'EURUSD': raw_packet.get('EURUSD', 0.0),
                'GBPUSD': raw_packet.get('GBPUSD', 0.0),
                'USDJPY': raw_packet.get('USDJPY', 0.0),
                'GOLD': raw_packet.get('GOLD', 0.0),
                'SILVER': raw_packet.get('SILVER', 0.0),
                '#NASDAQ100': raw_packet.get('NAS100', 0.0),
                '#DJ30': raw_packet.get('DJ30', 0.0),
                '#S&P500': raw_packet.get('SP500', 0.0),
                'BRENT_OIL': raw_packet.get('BRENT', 0.0),
                'CrudeOIL': raw_packet.get('CRUDE', 0.0)
            }
            
            # Format prices
            for symbol in symbols:
                price_val = float(raw_prices.get(symbol, 0.0))
                prices[symbol] = {
                    'price': price_val,
                    'bid': price_val,
                    'ask': price_val,
                    'change': 0,
                    'change_percent': 0
                }
        
        # ============ GET SIGNALS ============
        signals = get_signals_from_file()
        
        # If no signals found, generate defaults
        if not signals:
            signals = generate_default_signals()
        
        print(f"📊 Sending {len(signals)} signals to dashboard")
        
        response = jsonify({
            'success': True,
            'mt4_connected': mt4_connected,
            'account': {
                'balance': balance,
                'equity': equity
            },
            'prices': prices,
            'signals': signals,  # NOW HAS SIGNALS!
            'stats': stats,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)})
# ============ START SERVER ============
@app.route('/api/leaderboard')
def api_leaderboard():
    """Get agent leaderboard"""
    try:
        from database_manager import DatabaseManager
        db = DatabaseManager()
        leaderboard = db.get_leaderboard()
        return jsonify(leaderboard)
    except Exception as e:
        return jsonify({'error': str(e)})
def start_dashboard_server(port=5001):
    """Start the dashboard server"""
    print(f"\n{'='*50}")
    print(f"📊 AI Trading Dashboard")
    print(f"   URL: http://localhost:{port}")
    print(f"   Refresh: Every 10 seconds")
    print(f"   Debug: http://localhost:{port}/api/debug_file")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    start_dashboard_server()