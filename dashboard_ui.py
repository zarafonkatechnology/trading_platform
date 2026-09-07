"""
UNIFIED DASHBOARD UI - Reads bid/ask from forex_dashboard.py
AND shows signals from advanced_trading_strategy.py
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import json
import os
import time
import requests
from datetime import datetime
from supabase import create_client, Client

from dotenv import load_dotenv
app = Flask(__name__)
# Load environment variables
load_dotenv()

# ============ SUPABASE CONFIGURATION ============
SUPABASE_URL = os.getenv('USER_AUTH_SUPABASE_URL', 'https://unyronpybahqltrbzxas.supabase.co')
SUPABASE_ANON_KEY = os.getenv('USER_AUTH_SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2NTQ3MjUsImV4cCI6MjEwMDIzMDcyNX0.DMIrAaIpvvWKxbuRTN3MF9UryqnXBD9R-u47B5cUEZM')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
# ============ SECOND SUPABASE CONFIGURATION (for skipped_signals) ============
SKIP_SUPABASE_URL = 'https://jcvisgkvwlzdohilimni.supabase.co'
SKIP_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3MTcxODMsImV4cCI6MjEwMDI5MzE4M30.STwnGvjXLNoeXeq3uY0q783FrGaCY8ZJtB2Yyt115fI'

# Initialize second Supabase client for skipped signals
skip_supabase: Client = create_client(SKIP_SUPABASE_URL, SKIP_SUPABASE_ANON_KEY)
CORS(app)
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
# ============ CONFIGURATION ============
DASHBOARD_URL = "http://localhost:5002"
DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
SIGNALS_FILE = "signals.json"  # Signals from advanced_trading_strategy.py

# Cache
cached_data = {}
last_fetch = 0
cache_ttl = 0.5  # 500ms

def fetch_from_dashboard():
    """Fetch data from forex_dashboard.py API"""
    global cached_data, last_fetch
    
    # Check cache
    current_time = time.time()
    if cached_data and (current_time - last_fetch) < cache_ttl:
        return cached_data
    
    try:
        response = requests.get(f"{DASHBOARD_URL}/api/all_data", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Parse prices with bid/ask
                prices = {}
                for symbol, price_data in data.get('prices', {}).items():
                    if isinstance(price_data, dict):
                        prices[symbol] = {
                            'price': price_data.get('price', 0),
                            'bid': price_data.get('bid', 0),
                            'ask': price_data.get('ask', 0),
                            'change': price_data.get('change', 0)
                        }
                    else:
                        price = float(price_data) if price_data else 0
                        prices[symbol] = {
                            'price': price,
                            'bid': price,
                            'ask': price,
                            'change': 0
                        }
                # Get card balance from Supabase
                card_balance = get_card_balance()
                cached_data = {
                    'success': True,
                    'prices': prices,
                    'balance': card_balance,
                    'mt4_balance': data.get('balance', 0),
                    'mt4_equity': data.get('equity', 0),
                    'equity': card_balance, 
                    'timestamp': data.get('timestamp', datetime.now().strftime('%H:%M:%S')),
                    'source': data.get('source', 'Dashboard'),
                    'signals': fetch_signals_from_file(),  # NEW: Add signals
                    'card_balance': card_balance,  # <-- ADD THIS LINE
                    'card_count': get_card_count()  # <-- ADD THIS LIN
                }
                last_fetch = current_time
                return cached_data
    except Exception as e:
        print(f"⚠️ Dashboard API error: {e}")
    
    # Fallback: read file directly
    try:
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
                
                prices = {}
                raw_prices = data.get('prices', {})
                for symbol, price_data in raw_prices.items():
                    if isinstance(price_data, dict):
                        prices[symbol] = {
                            'price': price_data.get('price', 0),
                            'bid': price_data.get('bid', 0),
                            'ask': price_data.get('ask', 0),
                            'change': price_data.get('change', 0)
                        }
                    else:
                        price = float(price_data) if price_data else 0
                        prices[symbol] = {
                            'price': price,
                            'bid': price,
                            'ask': price,
                            'change': 0
                        }
                card_balance = get_card_balance()
                cached_data = {
                    'success': True,
                    'prices': prices,
                    'balance': card_balance,
                    'equity': card_balance,
                    'mt4_equity': data.get('equity', 0),
                    'mt4_balance': data.get('balance', 0),
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'source': 'File (fallback)',
                    'signals': fetch_signals_from_file(),
                    'card_balance': card_balance,  # <-- ADD THIS LINE
                    'card_count': get_card_count()  # <-- ADD THIS LINE
                }
                last_fetch = current_time
                return cached_data
    except Exception as e:
        print(f"⚠️ File read error: {e}")
    
    return {'success': False, 'prices': {}, 'signals': []}
def get_user_card_balance():
    """Get total balance from user_cards"""
    try:
        user_id = request.headers.get('X-User-ID', 'default_user') if hasattr(request, 'headers') else 'default_user'
        
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
        print(f"⚠️ Error getting user cards balance: {e}")
        return 0

def get_user_card_count():
    """Get number of user cards"""
    try:
        user_id = request.headers.get('X-User-ID', 'default_user') if hasattr(request, 'headers') else 'default_user'
        
        response = supabase.table('user_cards')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        return len(response.data) if response.data else 0
    except Exception as e:
        print(f"⚠️ Error getting user card count: {e}")
        return 0
def get_card_balance(card_id=None, card_pin=None):
    """Get balance from user_cards table in Supabase for the logged-in user"""
    try:
        user_id = get_user_id()
        
        # If no user logged in, return 0
        if not user_id:
            return 0
        
        if card_id and card_pin:
            response = supabase.table('user_cards')\
                .select('balance, amount')\
                .eq('card_id', card_id)\
                .eq('card_pin', card_pin)\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .execute()
            
            if response.data and len(response.data) > 0:
                card = response.data[0]
                return card.get('balance') or card.get('amount') or 0
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
        print(f"⚠️ Supabase error: {e}")
        return 0
def get_card_count():
    """Get number of user cards for logged-in user"""
    try:
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
        print(f"⚠️ Error getting card count: {e}")
        return 0
def fetch_signals_from_file():
    """Fetch signals from advanced_trading_strategy.py signals file"""
    try:
        # Use absolute path
        signals_file = os.path.join(os.path.dirname(__file__), 'signals.json')
        
        if os.path.exists(signals_file):
            with open(signals_file, 'r') as f:
                signals = json.load(f)
                if isinstance(signals, list):
                    # Filter out HOLD signals
                    valid_signals = [s for s in signals if s.get('signal_type') != 'HOLD']
                    return valid_signals[-20:]  # Last 20
                return []
    except Exception as e:
        print(f"⚠️ Signals read error: {e}")
    return []

# ============ HTML TEMPLATE ============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 Unified Trading Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        /* Navigation Tabs */
.nav-tabs {
    display: flex;
    gap: 5px;
    margin-bottom: 25px;
    background: #0a0e27;
    border-radius: 12px;
    padding: 5px;
    border: 1px solid #1a2a4a;
}

.nav-tab {
    padding: 10px 25px;
    border: none;
    background: transparent;
    color: #888;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.3s;
}
.position-indicator {
    pointer-events: none;
    z-index: 10;
}

.position-indicator div {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    white-space: nowrap;
}
.nav-tab:hover {
    color: #e0e0e0;
    background: #16213e;
}

.nav-tab.active {
    background: #ffd700;
    color: #0a0e27;
}
/* Card Preview Styles */
.card-preview-container {
    background: linear-gradient(135deg, #1a2a5a 0%, #0f1a3a 100%);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid #2a3a6a;
}

.card-preview {
    background: linear-gradient(145deg, #2a3a6a, #1a2a5a);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #3a4a8a;
    position: relative;
    overflow: hidden;
}

.card-preview::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, rgba(255, 215, 0, 0.05) 0%, transparent 70%);
}

.card-preview-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 20px;
    position: relative;
    z-index: 1;
}

.card-preview-title {
    color: #ffd700;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.card-preview-badge {
    background: #ffd700;
    color: #0a0e27;
    font-size: 10px;
    padding: 2px 12px;
    border-radius: 10px;
    font-weight: bold;
    text-transform: uppercase;
}

.card-preview-number {
    margin-bottom: 20px;
    position: relative;
    z-index: 1;
}

.card-number-label {
    display: block;
    color: #888;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 5px;
}
/* Charts Page */
.charts-page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 10px;
}

.charts-page-header h2 {
    color: #ffd700;
    font-size: 22px;
}

.chart-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.chart-controls select {
    padding: 8px 15px;
    background: #0a0e27;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: white;
    font-size: 13px;
    cursor: pointer;
}

.chart-controls select:focus {
    outline: none;
    border-color: #ffd700;
}

.btn-refresh-chart {
    padding: 8px 20px;
    background: #ffd700;
    color: #0a0e27;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.3s;
}

.btn-refresh-chart:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.chart-container {
    background: #0a0e27;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid #1a2a4a;
    height: 400px;
    position: relative;
}

.chart-container canvas {
    width: 100% !important;
    height: 100% !important;
}

.chart-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 15px;
    background: #0a0e27;
    padding: 15px 20px;
    border-radius: 12px;
    border: 1px solid #1a2a4a;
}

.chart-stat-item {
    text-align: center;
}

.chart-stat-item .stat-label {
    display: block;
    font-size: 10px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.chart-stat-item .stat-value {
    display: block;
    font-size: 20px;
    font-weight: bold;
    color: #ffd700;
    margin-top: 3px;
}

.chart-stat-item .stat-value.up {
    color: #4caf50;
}

.chart-stat-item .stat-value.down {
    color: #f44336;
}
.card-number-value {
    display: block;
    color: #fff;
    font-size: 28px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
    letter-spacing: 2px;
    text-shadow: 0 0 20px rgba(255, 215, 0, 0.1);
}

.card-preview-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    position: relative;
    z-index: 1;
}

.preview-field {
    display: flex;
    flex-direction: column;
}

.preview-label {
    color: #888;
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 3px;
}

.preview-value {
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
}

/* Form Layout */
.form-row {
    display: flex;
    gap: 15px;
}

.form-group.half {
    flex: 1;
}

.digit-counter {
    background: #0a0e27;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid #2a3a6a;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
}

.digit-counter span:first-child {
    color: #ffd700;
}

.digit-counter span:last-child {
    color: #666;
}

/* Modal Actions */
.modal-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
    border-top: 1px solid #2a3a6a;
    padding-top: 20px;
}

.modal-actions .btn-cancel {
    flex: 1;
    padding: 10px;
    border: 1px solid #2a3a6a;
    background: transparent;
    color: #aaa;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
}

.modal-actions .btn-cancel:hover {
    background: #2a3a6a;
    color: #fff;
}

.modal-actions .btn-submit {
    flex: 2;
    padding: 10px;
    border: none;
    background: #ffd700;
    color: #0a0e27;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
}

.modal-actions .btn-submit:hover {
    background: #ffe44d;
    transform: scale(1.02);
}
.nav-tab.active:hover {
    background: #ffe44d;
}

/* Page sections */
.page-section {
    display: none;
}

.page-section.active {
    display: block;
}

/* Cards page */
.cards-page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 10px;
}

.cards-page-header h2 {
    color: #ffd700;
    font-size: 22px;
}

.btn-add-card {
    background: #ffd700;
    color: #0a0e27;
    border: none;
    padding: 10px 25px;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 14px;
}

.btn-add-card:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 15px;
}

.card-item {
    background: #16213e;
    border-radius: 12px;
    padding: 20px;
    border-left: 4px solid #ffd700;
    transition: all 0.3s;
}

.card-item:hover {
    transform: translateY(-3px);
    box-shadow: 0 5px 20px rgba(255, 215, 0, 0.1);
}

.card-item .card-id {
    color: #ffd700;
    font-size: 16px;
    font-weight: bold;
    display: block;
    margin-bottom: 5px;
}

.card-item .card-balance {
    font-size: 24px;
    font-weight: bold;
    color: #4caf50;
    margin: 10px 0;
}

.card-item .card-info {
    color: #888;
    font-size: 12px;
    line-height: 1.6;
}

.card-item .card-status {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    margin-top: 8px;
}

.card-item .card-status.active {
    background: #4caf50;
    color: white;
}

.card-item .card-status.inactive {
    background: #f44336;
    color: white;
}

.card-item .card-actions {
    margin-top: 12px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.card-item .card-actions button {
    padding: 6px 15px;
    border: 1px solid #2a3a6a;
    background: transparent;
    color: #aaa;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.3s;
}

.card-item .card-actions .btn-update:hover {
    border-color: #ffd700;
    color: #ffd700;
}

.card-item .card-actions .btn-delete:hover {
    border-color: #f44336;
    color: #f44336;
}

.no-cards-message {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 20px;
    color: #666;
    font-style: italic;
}

.no-cards-message .icon {
    font-size: 48px;
    margin-bottom: 15px;
    display: block;
}

.total-cards-summary {
    background: #0a0e27;
    padding: 15px 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
}

.total-cards-summary .item {
    text-align: center;
}

.total-cards-summary .item .label {
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
}

.total-cards-summary .item .value {
    font-size: 22px;
    font-weight: bold;
    color: #ffd700;
    margin-top: 3px;
}
        .status-online { background: #4caf50; color: white; animation: pulse 2s infinite; }
        .status-offline { background: #f44336; color: white; }
        .status-signal { background: #ff9800; color: white; animation: pulse 1s infinite; }
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
        
        .stats-bar {
            display: flex;
            gap: 30px;
            margin: 20px 0;
            padding: 15px;
            background: #16213e;
            border-radius: 10px;
            flex-wrap: wrap;
        }
        .stat-item { text-align: center; }
        .stat-item .label { font-size: 11px; color: #888; }
        .stat-item .value { font-size: 20px; font-weight: bold; color: #ffd700; }
        
        .signals-section {
            margin: 20px 0;
            padding: 15px;
            background: #16213e;
            border-radius: 10px;
            border-left: 4px solid #ff9800;
        }
        .signals-section h3 {
            color: #ff9800;
            margin-bottom: 10px;
            font-size: 16px;
        }
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
        .signal-item .filters { color: #888; font-size: 11px; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 18px 20px;
            border-left: 4px solid #ffd700;
            transition: all 0.3s;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 5px 20px rgba(255, 215, 0, 0.1); }
        .card.update { animation: flash 0.3s ease; }
        @keyframes flash { 0% { background: #1a3a5a; } 100% { background: #16213e; } }
        
        .card-symbol {
            font-size: 14px;
            font-weight: bold;
            color: #ffd700;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-price {
            font-size: 26px;
            font-weight: bold;
            margin: 8px 0;
        }
        .card-price.up { color: #4caf50; }
        .card-price.down { color: #f44336; }
        
        .card-change {
            font-size: 14px;
            font-weight: bold;
        }
        .card-change.up { color: #4caf50; }
        .card-change.down { color: #f44336; }
        
        .card-bidask {
            font-size: 11px;
            color: #888;
            margin-top: 5px;
            font-family: monospace;
        }
        .card-bidask .bid { color: #4caf50; }
        .card-bidask .ask { color: #f44336; }
        .card-bidask .label { color: #666; }
        
        .card-forex { border-left-color: #4caf50; }
        .card-index { border-left-color: #00bcd4; }
        .card-metal { border-left-color: #ffd700; }
        .card-energy { border-left-color: #ff6b35; }
        .card-dollar { border-left-color: #9c27b0; }
        
        .system-tag {
            font-size: 9px;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: bold;
        }
        .system-tag.zscore { background: #2196F3; color: white; }
        .system-tag.engine { background: #FF9800; color: white; }
        
        .signal-badge {
            font-size: 10px;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: bold;
            margin-left: 5px;
        }
        .signal-badge.buy { background: #4caf50; color: white; }
        .signal-badge.sell { background: #f44336; color: white; }
        .signal-badge.hold { background: #666; color: white; }
        
        .update-time {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #1a1a3a;
        }
        
        .refresh-btn {
            background: #ffd700;
            color: #0a0e27;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.8; }
        /* Sidebar Navigation */
.dashboard-wrapper {
    display: flex;
    gap: 20px;
    align-items: flex-start;
}

.sidebar {
    width: 280px;
    min-width: 280px;
    background: linear-gradient(135deg, #0f1a3a 0%, #1a2a5a 100%);
    border-radius: 15px;
    padding: 20px;
    position: sticky;
    top: 20px;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
}

.sidebar::-webkit-scrollbar {
    width: 4px;
}
.sidebar::-webkit-scrollbar-track {
    background: #0a0e27;
}
.sidebar::-webkit-scrollbar-thumb {
    background: #ffd700;
    border-radius: 4px;
}

.sidebar-title {
    color: #ffd700;
    font-size: 18px;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #2a3a6a;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.sidebar-title button {
    background: #ffd700;
    color: #0a0e27;
    border: none;
    padding: 5px 15px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: bold;
    font-size: 12px;
}

.sidebar-title button:hover {
    background: #ffe44d;
}

.card-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.card-list-item {
    background: #16213e;
    border-radius: 8px;
    padding: 12px 15px;
    margin-bottom: 10px;
    border-left: 3px solid #ffd700;
    transition: all 0.3s;
    cursor: pointer;
}

.card-list-item:hover {
    background: #1a2a5a;
    transform: translateX(5px);
}

.card-list-item .card-id {
    color: #ffd700;
    font-weight: bold;
    font-size: 13px;
    display: block;
}

.card-list-item .card-balance {
    color: #4caf50;
    font-size: 16px;
    font-weight: bold;
    margin-top: 5px;
}

.card-list-item .card-details {
    color: #888;
    font-size: 11px;
    margin-top: 3px;
    display: flex;
    justify-content: space-between;
}

.card-list-item .card-status {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    background: #4caf50;
    color: white;
}

.card-list-item .card-status.inactive {
    background: #f44336;
}

.card-list-item .card-actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;
}

.card-list-item .card-actions button {
    background: transparent;
    border: 1px solid #2a3a6a;
    color: #aaa;
    padding: 3px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    transition: all 0.3s;
}

.card-list-item .card-actions button:hover {
    background: #2a3a6a;
    color: white;
}

.card-list-item .card-actions .delete-btn:hover {
    border-color: #f44336;
    color: #f44336;
}

/* Modal for adding card */
.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1000;
    justify-content: center;
    align-items: center;
}

.modal.active {
    display: flex;
}

.modal-content {
    background: linear-gradient(135deg, #0f1a3a 0%, #1a2a5a 100%);
    padding: 30px;
    border-radius: 15px;
    max-width: 450px;
    width: 90%;
    border: 1px solid #2a3a6a;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-content h2 {
    color: #ffd700;
    margin-bottom: 20px;
    text-align: center;
}

.modal-content .form-group {
    margin-bottom: 15px;
}

.modal-content label {
    display: block;
    color: #aaa;
    font-size: 12px;
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.modal-content input, 
.modal-content select {
    width: 100%;
    padding: 10px;
    background: #0a0e27;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: white;
    font-size: 14px;
    transition: border-color 0.3s;
}

.modal-content input:focus,
.modal-content select:focus {
    outline: none;
    border-color: #ffd700;
}

.modal-content .modal-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}

.modal-content .modal-actions button {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
}

.modal-content .modal-actions .btn-submit {
    background: #ffd700;
    color: #0a0e27;
}

.nav-tab {
    padding: 10px 25px;
    border: none;
    background: transparent;
    color: #888;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.3s;
}

.nav-tab:hover {
    color: #e0e0e0;
    background: #16213e;
}

.nav-tab.active {
    background: #ffd700;
    color: #0a0e27;
}

.nav-tab.active:hover {
    background: #ffe44d;
}


.page-section.active {
    display: block;
}

.cards-page-header h2 {
    color: #ffd700;
    font-size: 22px;
}

.btn-add-card {
    background: #ffd700;
    color: #0a0e27;
    border: none;
    padding: 10px 25px;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 14px;
}

.btn-add-card:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.card-item:hover {
    transform: translateY(-3px);
    box-shadow: 0 5px 20px rgba(255, 215, 0, 0.1);
}

.card-item .card-id {
    color: #ffd700;
    font-size: 16px;
    font-weight: bold;
    display: block;
    margin-bottom: 5px;
}

.card-item .card-balance {
    font-size: 24px;
    font-weight: bold;
    color: #4caf50;
    margin: 10px 0;
}

.card-item .card-info {
    color: #888;
    font-size: 12px;
    line-height: 1.6;
}

.card-item .card-status {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    margin-top: 8px;
}

.card-item .card-status.active {
    background: #4caf50;
    color: white;
}

.card-item .card-status.inactive {
    background: #f44336;
    color: white;
}

.card-item .card-actions {
    margin-top: 12px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.card-item .card-actions button {
    padding: 6px 15px;
    border: 1px solid #2a3a6a;
    background: transparent;
    color: #aaa;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.3s;
}

.card-item .card-actions .btn-update:hover {
    border-color: #ffd700;
    color: #ffd700;
}

.card-item .card-actions .btn-delete:hover {
    border-color: #f44336;
    color: #f44336;
}

.no-cards-message .icon {
    font-size: 48px;
    margin-bottom: 15px;
    display: block;
}
.total-cards-summary .item {
    text-align: center;
}

.total-cards-summary .item .label {
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
}

.total-cards-summary .item .value {
    font-size: 22px;
    font-weight: bold;
    color: #ffd700;
    margin-top: 3px;
}
.modal-content .modal-actions .btn-submit:hover {
    background: #ffe44d;
}

.modal-content .modal-actions .btn-cancel {
    background: #2a3a6a;
    color: white;
}

.modal-content .modal-actions .btn-cancel:hover {
    background: #3a4a7a;
}

.no-cards {
    color: #666;
    text-align: center;
    padding: 30px 20px;
    font-style: italic;
}

/* Main content adjustment */
.main-content {
    flex: 1;
    min-width: 0;
}
/* Trade Buttons */
.trade-btn {
    padding: 12px 30px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 140px;
    justify-content: center;
    position: relative;
    overflow: hidden;
}

.trade-btn .btn-icon {
    font-size: 20px;
}

.trade-btn .btn-details {
    font-size: 11px;
    font-weight: normal;
    opacity: 0.8;
    margin-left: 5px;
}

.buy-btn {
    background: linear-gradient(135deg, #4caf50, #2e7d32);
    color: white;
    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.buy-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(76, 175, 80, 0.5);
}

.buy-btn:active {
    transform: translateY(0px);
}

.sell-btn {
    background: linear-gradient(135deg, #f44336, #c62828);
    color: white;
    box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
}

.sell-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(244, 67, 54, 0.5);
}

.sell-btn:active {
    transform: translateY(0px);
}

.trade-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
}

.trade-btn .pulse {
    animation: pulse-btn 1.5s ease-in-out infinite;
}

@keyframes pulse-btn {
    0% { opacity: 1; }
    50% { opacity: 0.7; }
    100% { opacity: 1; }
}

/* Trade confirmation modal */
.trade-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    z-index: 2000;
    justify-content: center;
    align-items: center;
}

.trade-modal.active {
    display: flex;
}

.trade-modal-content {
    background: linear-gradient(135deg, #0f1a3a 0%, #1a2a5a 100%);
    padding: 30px;
    border-radius: 15px;
    max-width: 450px;
    width: 90%;
    border: 1px solid #2a3a6a;
    text-align: center;
}

.trade-modal-content h2 {
    color: #ffd700;
    margin-bottom: 10px;
    font-size: 24px;
}

.trade-modal-content .trade-amount {
    font-size: 36px;
    font-weight: bold;
    color: #fff;
    margin: 15px 0;
}

.trade-modal-content .trade-details {
    color: #aaa;
    font-size: 14px;
    line-height: 1.8;
    margin: 15px 0;
}

.trade-modal-content .trade-details .label {
    color: #666;
}

.trade-modal-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}

.trade-modal-actions button {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
}

.trade-modal-actions .btn-confirm {
    background: #ffd700;
    color: #0a0e27;
}

.trade-modal-actions .btn-confirm:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.trade-modal-actions .btn-cancel-modal {
    background: #2a3a6a;
    color: white;
}

.trade-modal-actions .btn-cancel-modal:hover {
    background: #3a4a7a;
}

.trade-success {
    color: #4caf50;
    font-size: 48px;
    margin: 10px 0;
}

.trade-fail {
    color: #f44336;
    font-size: 48px;
    margin: 10px 0;
}
/* Signal Buttons */
.signal-btn {
    padding: 4px 12px;
    border: none;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    min-width: 60px;
}

.buy-btn-small {
    background: #4caf50;
    color: white;
}

.buy-btn-small:hover {
    background: #66bb6a;
    transform: scale(1.05);
}

.sell-btn-small {
    background: #f44336;
    color: white;
}

.sell-btn-small:hover {
    background: #ef5350;
    transform: scale(1.05);
}

.hold-btn-small {
    background: #666;
    color: #aaa;
    cursor: not-allowed;
    opacity: 0.6;
}

.skip-btn-small {
    background: #2a3a6a;
    color: #aaa;
    border: 1px solid #3a4a7a;
}

.skip-btn-small:hover {
    background: #3a4a7a;
    color: white;
    transform: scale(1.05);
}

/* Signal actions container */
.signal-actions {
    display: flex;
    gap: 5px;
    align-items: center;
}

/* Adjust signal item layout */
.signal-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 12px;
    margin: 5px 0;
    background: #1a2a4a;
    border-radius: 6px;
    font-size: 13px;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
    transition: all 0.3s;
}

.signal-item.skipped {
    opacity: 0.4;
    background: #0a0e27;
}

.signal-item.skipped .signal-btn {
    opacity: 0.3;
    cursor: not-allowed;
}

.signal-item .symbol { 
    color: #ffd700; 
    font-weight: bold; 
    min-width: 70px;
}

.signal-item .action { 
    font-weight: bold; 
    min-width: 50px;
}

.signal-item .action.buy { 
    color: #4caf50; 
}

.signal-item .action.sell { 
    color: #f44336; 
}

.signal-item .action.hold { 
    color: #888; 
}

.signal-item .confidence { 
    color: #888; 
    min-width: 45px;
}

.signal-item .filters { 
    color: #888; 
    font-size: 11px;
    flex: 1;
    min-width: 80px;
}

.signal-item .time { 
    color: #666; 
    font-size: 11px; 
    min-width: 60px;
}

.signal-btn[disabled] {
    cursor: not-allowed;
    opacity: 0.5;
}
@media (max-width: 1024px) {
    .dashboard-wrapper {
        flex-direction: column;
    }
    .sidebar {
        width: 100%;
        min-width: unset;
        position: relative;
        top: 0;
        max-height: none;
    }
}
        .source-tag {
            font-size: 10px;
            color: #666;
            margin-left: 10px;
        }
        
        .no-signals {
            color: #666;
            font-style: italic;
            padding: 10px;
            text-align: center;
        }
        
        @media (max-width: 600px) {
            .grid { grid-template-columns: 1fr; }
            .account-box { flex-direction: column; }
            .stats-bar { flex-direction: column; gap: 10px; }
            .signal-item { flex-wrap: wrap; gap: 5px; }
        }
/* Trade Modal - Enhanced */
.trade-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.85);
    z-index: 2000;
    justify-content: center;
    align-items: center;
    backdrop-filter: blur(5px);
}

.trade-modal.active {
    display: flex;
}

.trade-modal-content {
    background: linear-gradient(135deg, #0f1a3a 0%, #1a2a5a 100%);
    padding: 25px;
    border-radius: 15px;
    max-width: 480px;
    width: 92%;
    border: 1px solid #2a3a6a;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
    animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
    from {
        transform: translateY(-30px) scale(0.95);
        opacity: 0;
    }
    to {
        transform: translateY(0) scale(1);
        opacity: 1;
    }
}

.trade-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #2a3a6a;
}

.trade-modal-header h2 {
    color: #ffd700;
    font-size: 20px;
    margin: 0;
}

.trade-modal-close {
    background: none;
    border: none;
    color: #666;
    font-size: 22px;
    cursor: pointer;
    padding: 0 5px;
    transition: all 0.3s;
}

.trade-modal-close:hover {
    color: #fff;
    transform: rotate(90deg);
}

.trade-modal-body {
    margin-bottom: 20px;
}

.trade-details-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 20px;
}

.trade-detail-item {
    background: #0a0e27;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid #1a2a4a;
    text-align: center;
}

.trade-detail-item .trade-detail-label {
    display: block;
    font-size: 9px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.trade-detail-item .trade-detail-value {
    display: block;
    font-size: 16px;
    font-weight: bold;
    color: #ffd700;
    margin-top: 3px;
    font-family: 'Courier New', monospace;
}

.trade-detail-item .trade-detail-value.buy-color {
    color: #4caf50;
}

.trade-detail-item .trade-detail-value.sell-color {
    color: #f44336;
}

.trade-detail-item .trade-detail-value.spread-value {
    color: #00bcd4;
}

.trade-sl-tp {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-top: 10px;
}

.trade-input-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.trade-input-group label {
    font-size: 10px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.trade-input-group input {
    padding: 8px 12px;
    background: #0a0e27;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: white;
    font-size: 13px;
    font-family: 'Courier New', monospace;
    transition: all 0.3s;
    width: 100%;
}

.trade-input-group input:focus {
    outline: none;
    border-color: #ffd700;
}

.trade-input-group input::placeholder {
    color: #444;
    font-size: 11px;
}

.trade-modal-footer {
    display: flex;
    gap: 10px;
    padding-top: 15px;
    border-top: 1px solid #2a3a6a;
}

.trade-modal-footer button {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
}

.trade-modal-footer .btn-confirm {
    background: #ffd700;
    color: #0a0e27;
}

.trade-modal-footer .btn-confirm:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.trade-modal-footer .btn-cancel-modal {
    background: #2a3a6a;
    color: white;
}

.trade-modal-footer .btn-cancel-modal:hover {
    background: #3a4a7a;
}
.price-line-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #aaa;
    font-size: 12px;
    cursor: pointer;
    padding: 6px 12px;
    background: #0a0e27;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    transition: all 0.3s;
}

.price-line-toggle:hover {
    border-color: #ffd700;
}

.price-line-toggle input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: #ffd700;
    cursor: pointer;
}

.price-line-toggle span {
    user-select: none;
}
/* Trade result overlay */
.trade-result {
    text-align: center;
    padding: 20px 0;
}

.trade-result .result-icon {
    font-size: 48px;
    margin-bottom: 10px;
}

.trade-result .result-title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 5px;
}

.trade-result .result-title.success {
    color: #4caf50;
}

.trade-result .result-title.fail {
    color: #f44336;
}

.trade-result .result-details {
    color: #888;
    font-size: 13px;
    line-height: 1.6;
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

.account-item { 
    text-align: center; 
    padding: 5px;
}

.account-label { 
    font-size: 10px; 
    color: #aaa; 
    text-transform: uppercase; 
    letter-spacing: 1px; 
}

.account-value { 
    font-size: 22px; 
    font-weight: bold; 
    margin-top: 5px; 
}

.account-value.gold { color: #ffd700; }
.account-value.green { color: #4caf50; }
.account-value.red { color: #f44336; }
.account-value.cyan { color: #00bcd4; }
.account-value.orange { color: #ff9800; }
.account-value.purple { color: #9c27b0; }
/* Positions Section - Inside Charts Page */
.positions-section {
    margin: 20px 0 0 0;
    padding: 15px;
    background: #16213e;
    border-radius: 10px;
    border-left: 4px solid #00bcd4;
}

.positions-section h3 {
    color: #00bcd4;
    margin-bottom: 10px;
    font-size: 16px;
}

.position-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 15px;
    margin: 5px 0;
    background: #1a2a4a;
    border-radius: 6px;
    font-size: 13px;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
    border-left: 3px solid #ffd700;
}

.position-item .pos-symbol {
    color: #ffd700;
    font-weight: bold;
    min-width: 70px;
}

.position-item .pos-direction.buy {
    color: #4caf50;
    font-weight: bold;
}

.position-item .pos-direction.sell {
    color: #f44336;
    font-weight: bold;
}

.position-item .pos-profit {
    font-weight: bold;
    min-width: 80px;
}

.position-item .pos-profit.positive {
    color: #4caf50;
}

.position-item .pos-profit.negative {
    color: #f44336;
}

.position-item .pos-spread {
    color: #00bcd4;
    font-size: 11px;
}

.position-item .pos-close-btn {
    background: #f44336;
    color: white;
    border: none;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    font-weight: bold;
    transition: all 0.3s;
}

.position-item .pos-close-btn:hover {
    background: #d32f2f;
    transform: scale(1.05);
}

.no-positions {
    color: #666;
    font-style: italic;
    padding: 10px;
    text-align: center;
}
/* Trade execution animation */
.trade-flash {
    animation: tradeFlash 0.5s ease;
}

@keyframes tradeFlash {
    0% { background: rgba(255, 215, 0, 0.3); }
    100% { background: transparent; }
}
/* History Page Styles */
.history-page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 10px;
}

.history-page-header h2 {
    color: #ffd700;
    font-size: 22px;
}

.history-controls {
    display: flex;
    gap: 10px;
}

.btn-refresh-history {
    padding: 8px 20px;
    background: #ffd700;
    color: #0a0e27;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 13px;
}

.btn-refresh-history:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.btn-clear-filter {
    padding: 8px 20px;
    background: #2a3a6a;
    color: #aaa;
    border: 1px solid #3a4a7a;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 13px;
}

.btn-clear-filter:hover {
    background: #3a4a7a;
    color: white;
}

/* ============ HISTORY PAGE STYLES ============ */
.history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 15px;
}

.history-header h2 {
    color: #ffd700;
    font-size: 24px;
    margin: 0;
}

.history-actions {
    display: flex;
    gap: 10px;
}

.history-actions .btn-refresh,
.history-actions .btn-clear {
    padding: 8px 20px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 13px;
}

.history-actions .btn-refresh {
    background: #ffd700;
    color: #0a0e27;
}

.history-actions .btn-refresh:hover {
    background: #ffe44d;
    transform: scale(1.02);
}

.history-actions .btn-clear {
    background: #2a3a6a;
    color: #aaa;
    border: 1px solid #3a4a7a;
}

.history-actions .btn-clear:hover {
    background: #3a4a7a;
    color: white;
}

/* Filters */
.history-filters {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 15px;
    padding: 15px 20px;
    background: #16213e;
    border-radius: 12px;
    margin-bottom: 20px;
    align-items: end;
}

.filter-item {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.filter-item label {
    font-size: 10px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.filter-item select,
.filter-item input {
    padding: 8px 12px;
    background: #0a0e27;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: white;
    font-size: 13px;
    transition: all 0.3s;
    width: 100%;
}

.filter-item select:focus,
.filter-item input:focus {
    outline: none;
    border-color: #ffd700;
}

.filter-item .date-range {
    display: flex;
    align-items: center;
    gap: 8px;
}

.filter-item .date-range input {
    flex: 1;
    min-width: 0;
}

.filter-item .date-range span {
    color: #666;
    font-size: 12px;
}

/* Stats Cards */
.history-stats {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}

.stat-card {
    background: #0a0e27;
    border-radius: 10px;
    padding: 14px 16px;
    border: 1px solid #1a2a4a;
    text-align: center;
    transition: all 0.3s;
}

.stat-card:hover {
    border-color: #2a3a6a;
    transform: translateY(-2px);
}

.stat-card .stat-label {
    display: block;
    font-size: 10px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.stat-card .stat-value {
    display: block;
    font-size: 20px;
    font-weight: bold;
    color: #ffd700;
}

.stat-card .stat-value.positive {
    color: #4caf50;
}

.stat-card .stat-value.negative {
    color: #f44336;
}

/* Table */
.history-table-wrapper {
    background: #0a0e27;
    border-radius: 12px;
    border: 1px solid #1a2a4a;
    overflow-x: auto;
    padding: 0 0 5px 0;
}

.history-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    min-width: 950px;
}

.history-table thead {
    background: #16213e;
    border-bottom: 2px solid #2a3a6a;
}

.history-table thead th {
    padding: 12px 15px;
    text-align: left;
    color: #ffd700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    white-space: nowrap;
    position: sticky;
    top: 0;
    background: #16213e;
    z-index: 5;
}

.history-table tbody td {
    padding: 11px 15px;
    border-bottom: 1px solid #1a2a4a;
    color: #e0e0e0;
    font-size: 13px;
}

.history-table tbody tr:hover {
    background: #16213e;
}

.history-table .direction-buy {
    color: #4caf50;
    font-weight: bold;
}

.history-table .direction-sell {
    color: #f44336;
    font-weight: bold;
}

.history-table .status-open {
    color: #ffd700;
    font-weight: bold;
}

.history-table .status-closed {
    color: #888;
}

.history-table .status-tp {
    color: #4caf50;
    font-weight: bold;
}

.history-table .status-sl {
    color: #f44336;
    font-weight: bold;
}

.history-table .pnl-positive {
    color: #4caf50;
    font-weight: bold;
}

.history-table .pnl-negative {
    color: #f44336;
    font-weight: bold;
}

.history-table .no-data {
    text-align: center;
    color: #666;
    padding: 50px 20px;
    font-style: italic;
    font-size: 15px;
}

/* Pagination */
.history-pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    padding: 18px 0 5px 0;
}

.history-pagination .page-btn {
    padding: 7px 20px;
    background: #16213e;
    border: 1px solid #2a3a6a;
    border-radius: 6px;
    color: #aaa;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.3s;
}

.history-pagination .page-btn:hover:not(:disabled) {
    background: #2a3a6a;
    color: white;
    border-color: #3a4a7a;
}

.history-pagination .page-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.history-pagination #historyPageInfo {
    color: #888;
    font-size: 14px;
    min-width: 120px;
    text-align: center;
}

/* Responsive */
@media (max-width: 1024px) {
    .history-filters {
        grid-template-columns: 1fr 1fr;
    }
    
    .history-stats {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 600px) {
    .history-filters {
        grid-template-columns: 1fr;
    }
    
    .history-stats {
        grid-template-columns: 1fr 1fr;
    }
    
    .history-header {
        flex-direction: column;
        align-items: stretch;
    }
    
    .history-actions {
        justify-content: stretch;
    }
    
    .history-actions button {
        flex: 1;
    }
}
    </style>
</head>
<body>
<div class="container">

    <div class="header">
    <h1>📊 Unified Trading Dashboard <span>Real-Time Bid/Ask</span></h1>
    <div>
        <span id="status" class="status status-online">✅ Online</span>
        <span id="sourceTag" class="source-tag">Loading...</span>
         <button onclick="logout()" style="
            background: #dc3545; 
            color: white; 
            border: none; 
            padding: 8px 20px; 
            border-radius: 6px; 
            cursor: pointer; 
            font-weight: bold;
            transition: all 0.3s;
        " onmouseover="this.style.background='#c82333'" onmouseout="this.style.background='#dc3545'">
            🚪 Logout
        </button>
    </div>
</div>

<!-- Navigation Tabs -->
<div class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('dashboard')">📊 Dashboard</button>
    <button class="nav-tab" onclick="switchTab('cards')">💳 My Cards</button>
    <button class="nav-tab" onclick="switchTab('charts')">📈 Charts</button>
    <button class="nav-tab" onclick="switchTab('history')">📜 History</button>

</div>
<!-- Dashboard Page -->
<div id="dashboardPage" class="page-section active">
    <div class="account-box">
    <div class="account-item">
    <div class="account-label">💰 Balance</div>
    <div class="account-value gold" id="balance">$---</div>
    <div style="font-size:12px;color:#888;margin-top:5px;">
        <span id="cardCountDisplay">0</span> active cards
        <span id="balanceStatus" style="display:inline-block;margin-left:8px;font-size:11px;"></span>
    </div>
</div>
    <div class="account-item">
        <div class="account-label">📊 Equity</div>
        <div class="account-value gold" id="equity">$---</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Same as balance
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">📈 P&L</div>
        <div class="account-value" id="pnl" style="color:#888;">$---</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Profit / Loss
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">📊 Free Margin</div>
        <div class="account-value" id="freeMargin" style="color:#00bcd4;">$---</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Available
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">🔒 Margin</div>
        <div class="account-value" id="margin" style="color:#ff9800;">$---</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Used
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">📊 Margin Level</div>
        <div class="account-value" id="marginLevel" style="color:#9c27b0;">---%</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Equity / Margin
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">📅 Daily P&L</div>
        <div class="account-value" id="dailyPnl" style="color:#888;">$---</div>
        <div style="font-size:12px;color:#888;margin-top:5px;">
            Today's change
        </div>
    </div>
    <div class="account-item">
        <div class="account-label">🕐 Updated</div>
        <div class="account-value" style="font-size:18px;color:#aaa;" id="updated">--:--:--</div>
    </div>
</div>
<div class="stats-bar">
    <div class="stat-item">
        <div class="label">🔄 Symbols</div>
        <div class="value" id="symbolCount">0</div>
    </div>
    <div class="stat-item">
        <div class="label">📊 Spread</div>
        <div class="value" id="spreadInfo" style="font-size:14px;">--</div>
    </div>
    <div class="stat-item">
        <div class="label">📡 Source</div>
        <div class="value" id="dataSource" style="font-size:14px;">--</div>
    </div>
    <div class="stat-item">
        <div class="label">📈 Active Signals</div>
        <div class="value" id="signalCount" style="color:#ff9800;">0</div>
    </div>
    <div class="stat-item">
        <div class="label">💵 USD Direction</div>
        <div class="value" id="usdDirection" style="font-size:16px;color:#ffd700;">NEUTRAL</div>
    </div>
</div>

    <!-- SIGNALS SECTION -->
    <div class="signals-section" id="signalsSection">
        <h3>🎯 Trading Signals</h3>
        <div id="signalsList">
            <div class="no-signals">No active signals. Waiting for Z-Score thresholds...</div>
        </div>
        <div id="tradeButtons" style="display: none; margin-top: 15px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
    </div>
    </div>
    
    <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <div id="grid" class="grid">
        <div style="text-align:center;padding:40px;color:#666;">Loading prices...</div>
    </div>
    
            </div> <!-- End main-content -->
    </div> <!-- End dashboard-wrapper -->
    
    <div class="update-time">
        Auto-refresh every <span id="countdown">2</span>s | 
        <span id="symbolCount2">0</span> symbols
    </div>
</div>

</div>
<!-- Trade Confirmation Modal -->
<div class="trade-modal" id="tradeModal">
    <div class="trade-modal-content">
        <div class="trade-modal-header">
            <h2 id="tradeModalTitle">📊 Trade Execution</h2>
            <button class="trade-modal-close" onclick="closeTradeModal()">✕</button>
        </div>
        
        <div class="trade-modal-body">
            <!-- Trade Details Grid -->
            <div class="trade-details-grid">
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Symbol</span>
                    <span class="trade-detail-value" id="tradeSymbol">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Direction</span>
                    <span class="trade-detail-value" id="tradeDirection">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Entry Price</span>
                    <span class="trade-detail-value" id="tradePrice">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Spread</span>
                    <span class="trade-detail-value" id="tradeSpread">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Stop Loss (SL)</span>
                    <span class="trade-detail-value" id="tradeSL">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Take Profit (TP)</span>
                    <span class="trade-detail-value" id="tradeTP">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Lot Size</span>
                    <span class="trade-detail-value" id="tradeLotSize">0.01</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Confidence</span>
                    <span class="trade-detail-value" id="tradeConfidence">--</span>
                </div>
            </div>
            
        </div>
        
        <div class="trade-modal-footer">
            <button class="btn-cancel-modal" onclick="closeTradeModal()">Cancel</button>
            <button class="btn-confirm" onclick="confirmTrade()">Confirm Trade</button>
        </div>
    </div>
</div>
<!-- Cards Page -->
<div id="cardsPage" class="page-section">
    <div class="cards-page-header">
        <h2>💳 My Cards</h2>
        <button class="btn-add-card" onclick="showAddCardModal()">+ Add Card</button>
    </div>
    
    <div class="total-cards-summary">
        <div class="item">
            <div class="label">Total Cards</div>
            <div class="value" id="totalCardsCount">0</div>
        </div>
        <div class="item">
            <div class="label">Total Balance</div>
            <div class="value" id="totalCardsBalance">$0.00</div>
        </div>
    </div>
    
    <div class="cards-grid" id="cardsGrid">
        <div class="no-cards-message">
            <span class="icon">💳</span>
            No cards found. Click "+ Add Card" to add your first card.
        </div>
    </div>
</div>
<!-- Charts Page -->
<!-- Charts Page -->
<div id="chartsPage" class="page-section">
    <div class="charts-page-header">
        <h2>📈 Live Charts</h2>
        <div class="chart-controls">
            <select id="chartSymbol" onchange="switchChart()">
                <!-- Will be populated dynamically -->
            </select>
            <select id="chartTimeframe" onchange="switchChart()">
                <option value="60">1 Minute</option>
                <option value="300">5 Minutes</option>
                <option value="900">15 Minutes</option>
                <option value="3600">1 Hour</option>
            </select>
            <button onclick="refreshChart()" class="btn-refresh-chart">🔄 Refresh</button>
            <label class="price-line-toggle">
                <input type="checkbox" id="showPriceLine" checked onchange="togglePriceLine()">
                <span>Show Price Line</span>
            </label>
        </div>
    </div>
    
    <!-- ============ POSITIONS SECTION - MOVED ABOVE CHART ============ -->
    <div class="positions-section" id="positionsSection">
        <h3>📊 Open Positions</h3>
        <div id="positionsList">
            <div class="no-positions">No open positions. Execute a signal to start trading.</div>
        </div>
    </div>
    
    <!-- Chart comes AFTER positions -->
    <div class="chart-container">
        <canvas id="priceChart"></canvas>
    </div>
    
    <div class="chart-stats">
        <div class="chart-stat-item">
            <span class="stat-label">Current Price</span>
            <span class="stat-value" id="chartCurrentPrice">--</span>
        </div>
        <div class="chart-stat-item">
            <span class="stat-label">Change</span>
            <span class="stat-value" id="chartChange">--</span>
        </div>
        <div class="chart-stat-item">
            <span class="stat-label">High</span>
            <span class="stat-value" id="chartHigh">--</span>
        </div>
        <div class="chart-stat-item">
            <span class="stat-label">Low</span>
            <span class="stat-value" id="chartLow">--</span>
        </div>
        <div class="chart-stat-item">
            <span class="stat-label">Bid</span>
            <span class="stat-value" id="chartBid">--</span>
        </div>
        <div class="chart-stat-item">
            <span class="stat-label">Ask</span>
            <span class="stat-value" id="chartAsk">--</span>
        </div>
    </div>
</div>
<!-- History Page -->
<div id="historyPage" class="page-section">
    <div class="history-header">
        <h2>📜 Trade History</h2>
        <div class="history-actions">
            <button onclick="refreshHistory()" class="btn-refresh">🔄 Refresh</button>
            <button onclick="clearHistoryFilter()" class="btn-clear">✕ Clear Filter</button>
        </div>
    </div>
    
    <!-- Filters -->
    <div class="history-filters">
        <div class="filter-item">
            <label>📅 Date Range</label>
            <div class="date-range">
                <input type="date" id="historyDateFrom" onchange="applyHistoryFilter()">
                <span>to</span>
                <input type="date" id="historyDateTo" onchange="applyHistoryFilter()">
            </div>
        </div>
        <div class="filter-item">
            <label>📊 Direction</label>
            <select id="historyDirectionFilter" onchange="applyHistoryFilter()">
                <option value="all">All</option>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
            </select>
        </div>
        <div class="filter-item">
            <label>📌 Status</label>
            <select id="historyStatusFilter" onchange="applyHistoryFilter()">
                <option value="all">All Status</option>
                <option value="OPEN">Open</option>
                <option value="CLOSED">Closed</option>
                <option value="TP">Take Profit</option>
                <option value="SL">Stop Loss</option>
            </select>
        </div>
        <div class="filter-item">
            <label>🔍 Symbol</label>
            <select id="historySymbolFilter" onchange="applyHistoryFilter()">
                <option value="all">All Symbols</option>
            </select>
        </div>
    </div>
    
    <!-- Summary Stats -->
    <div class="history-stats">
        <div class="stat-card">
            <span class="stat-label">📊 Total Trades</span>
            <span class="stat-value" id="historyTotalTrades">0</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">🏆 Win Rate</span>
            <span class="stat-value" id="historyWinRate">0%</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">✅ Total Profit</span>
            <span class="stat-value positive" id="historyTotalProfit">$0.00</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">❌ Total Loss</span>
            <span class="stat-value negative" id="historyTotalLoss">$0.00</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">📈 Net P&L</span>
            <span class="stat-value" id="historyNetPnl">$0.00</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">💎 Best Trade</span>
            <span class="stat-value positive" id="historyBestTrade">$0.00</span>
        </div>
    </div>
    
    <!-- Table -->
    <div class="history-table-wrapper">
        <table class="history-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Entry</th>
                    <th>Close</th>
                    <th>SL</th>
                    <th>TP</th>
                    <th>Lot</th>
                    <th>P&L</th>
                    <th>Status</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody id="historyTableBody">
                <tr>
                    <td colspan="11" class="no-data">📭 No trade history found</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <!-- Pagination -->
    <div class="history-pagination">
        <button onclick="historyPrevPage()" class="page-btn" id="prevPageBtn">◀ Previous</button>
        <span id="historyPageInfo">Page 1 of 1</span>
        <button onclick="historyNextPage()" class="page-btn" id="nextPageBtn">Next ▶</button>
    </div>
</div>
<!-- Add Card Modal -->
<div class="modal" id="addCardModal">
    <div class="modal-content">
        <h2>💳 Add New Card</h2>
        
        <div class="card-preview-container">
            <div class="card-preview">
                <div class="card-preview-header">
                    <span class="card-preview-title">CARD PREVIEW</span>
                    <span class="card-preview-badge">CARD HOLDER</span>
                </div>
                
                <div class="card-preview-number">
                    <span class="card-number-label">CARD NUMBER</span>
                    <span class="card-number-value" id="previewCardNumber">1234 5678</span>
                </div>
                
                <div class="card-preview-details">
                    <div class="preview-field">
                        <span class="preview-label">CARD HOLDER NAME</span>
                        <span class="preview-value" id="previewCardHolder">JOHN DOE</span>
                    </div>
                    <div class="preview-field">
                        <span class="preview-label">PIN</span>
                        <span class="preview-value" id="previewPin">1234</span>
                    </div>
                </div>
            </div>
        </div>
        
    <form id="addCardForm" onsubmit="return false;">
    <div class="form-group">
        <label>CARD NUMBER</label>
        <input type="text" id="cardId" placeholder="12345678" maxlength="8" required>
    </div>
    
    <div class="form-group">
        <label>CARD HOLDER NAME</label>
        <input type="text" id="cardHolderName" placeholder="JOHN DOE" required>
    </div>
    
    <div class="form-group">
        <label>PIN</label>
        <input type="password" id="cardPin" placeholder="1234" maxlength="4" required>
    </div>
    
    <div class="modal-actions">
        <button type="button" class="btn-cancel" onclick="closeAddCardModal()">Cancel</button>
        <button type="button" class="btn-submit" onclick="saveCard()">Save Card</button>
    </div>
</form>
    </div>
</div>
<script>
let dailyPnlTracker = 0; // Track daily P&L across positions
let lastResetDate = new Date().toDateString(); // Track when we last reset
let previousPrices = {};
let countdown = 2;
let lastSignals = [];
// ============ SIGNAL TRADE EXECUTION ============
let currentTradeData = {
    symbol: '',
    direction: '',
    price: 0,
    bid: 0,
    ask: 0,
    spread: 0,
    sl: 0,
    tp: 0,
    lotSize: 0.01,
    confidence: 0
};
let tradeConfirmed = false;
let openPositions = [];
let positionIdCounter = 0;

// Define symbol categories
const FOREX = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 
               'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
const INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225'];
const METALS = ['GOLD', 'SILVER'];
const ENERGY = ['BRENT_OIL', 'CrudeOIL'];
const DOLLAR = ['#DOLLAR_IND'];

function getCardType(symbol) {
    const forexPairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 
                        'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF', 'EURTRY',
                        'GBPJPY', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD',
                        'AUDJPY', 'AUDCAD', 'AUDCHF', 'AUDNZD',
                        'CADJPY', 'CHFJPY', 'NZDJPY',
                        'USDTRY', 'USDMXN', 'USDZAR', 'USDSGD', 'USDHKD'];
    
    const indices = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', 
                     '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
                     '#ASX200', '#IBEX35', '#AEX25'];
    
    const metals = ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'];
    const energy = ['BRENT_OIL', 'CrudeOIL', 'NATURAL_GAS'];
    const dollar = ['#DOLLAR_IND'];
    
    if (forexPairs.includes(symbol)) return 'forex';
    if (indices.includes(symbol)) return 'index';
    if (metals.includes(symbol)) return 'metal';
    if (energy.includes(symbol)) return 'energy';
    if (dollar.includes(symbol)) return 'dollar';
    return '';
}

function getSystem(symbol) {
    if (FOREX.includes(symbol) || DOLLAR.includes(symbol)) return 'engine';
    return 'zscore';
}

function getDisplayName(symbol) {
    const names = {
        // Forex EUR pairs
        'EURUSD': 'EUR/USD',
        'EURGBP': 'EUR/GBP',
        'EURJPY': 'EUR/JPY',
        'EURCHF': 'EUR/CHF',
        'EURCAD': 'EUR/CAD',
        'EURNZD': 'EUR/NZD',
        'EURTRY': 'EUR/TRY',
        // Forex other pairs
        'GBPUSD': 'GBP/USD',
        'USDJPY': 'USD/JPY',
        'USDCHF': 'USD/CHF',
        'AUDUSD': 'AUD/USD',
        'USDCAD': 'USD/CAD',
        'NZDUSD': 'NZD/USD',
        'GBPJPY': 'GBP/JPY',
        'GBPAUD': 'GBP/AUD',
        'GBPCAD': 'GBP/CAD',
        'GBPCHF': 'GBP/CHF',
        'GBPNZD': 'GBP/NZD',
        'AUDJPY': 'AUD/JPY',
        'AUDCAD': 'AUD/CAD',
        'AUDCHF': 'AUD/CHF',
        'AUDNZD': 'AUD/NZD',
        'CADJPY': 'CAD/JPY',
        'CHFJPY': 'CHF/JPY',
        'NZDJPY': 'NZD/JPY',
        'USDTRY': 'USD/TRY',
        'USDMXN': 'USD/MXN',
        'USDZAR': 'USD/ZAR',
        'USDSGD': 'USD/SGD',
        'USDHKD': 'USD/HKD',
        // Indices
        '#NASDAQ100': 'NASDAQ',
        '#DJ30': 'Dow Jones',
        '#S&P500': 'S&P 500',
        '#RUSS2000': 'Russell 2000',
        '#CAC40': 'CAC 40',
        '#DAX40': 'DAX 40',
        '#FTSE100': 'FTSE 100',
        '#NIKKEI225': 'Nikkei 225',
        '#ASX200': 'ASX 200',
        '#IBEX35': 'IBEX 35',
        '#AEX25': 'AEX 25',
        // Metals
        'GOLD': 'Gold',
        'SILVER': 'Silver',
        'PLATINUM': 'Platinum',
        'PALLADIUM': 'Palladium',
        // Energy
        'BRENT_OIL': 'Brent Oil',
        'CrudeOIL': 'Crude Oil',
        'NATURAL_GAS': 'Natural Gas',
        // Dollar Index
        '#DOLLAR_IND': 'Dollar Index'
    };
    return names[symbol] || symbol;
}
function getDecimals(symbol) {
    // JPY pairs (3 decimals)
    if (symbol.includes('JPY') || symbol === '#DOLLAR_IND') return 3;
    
    // Indices (2 decimals)
    if (symbol.includes('NASDAQ') || symbol.includes('S&P') || 
        symbol.includes('DJ') || symbol.includes('DAX') ||
        symbol.includes('CAC') || symbol.includes('FTSE') ||
        symbol.includes('NIKKEI') || symbol.includes('RUSS') ||
        symbol === 'GOLD' || symbol === 'SILVER' || 
        symbol === 'BRENT_OIL' || symbol === 'CrudeOIL' ||
        symbol === 'PLATINUM' || symbol === 'PALLADIUM' ||
        symbol === 'NATURAL_GAS') return 2;
    
    // Metals with 5 decimals
    if (symbol === 'GOLD' || symbol === 'SILVER') return 2;
    
    // Default 5 decimals for forex
    return 5;
}
let showPriceLine = true; // Add this line near the top with your other variables

// Add the toggle function
function togglePriceLine() {
    const checkbox = document.getElementById('showPriceLine');
    if (checkbox) {
        showPriceLine = checkbox.checked;
        if (priceChart) {
            priceChart.data.datasets[1].hidden = !showPriceLine;
            priceChart.update();
        }
    }
}
// ============ SIMPLE CHART WITH CURRENT PRICE LINE ============
let priceChart = null;
let chartHistory = {};
let chartInitialized = false;
let lastKnownPrices = {};
let chartInterval = null;
let currentSymbol = 'EURUSD';
let currentTimeframe = 60; // seconds
let currentPriceLine = null;
// ============ LOGOUT FUNCTION ============
async function logout() {
    if (!confirm('Are you sure you want to logout?')) return;
    
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Clear all cookies
            document.cookie.split(";").forEach(function(c) {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
            
            // Show notification
            showNotification('👋 Logged Out', 'You have been successfully logged out.');
            
            // Redirect to login page
            setTimeout(() => {
                window.location.href = 'http://localhost:5005/login';
            }, 1000);
        } else {
            alert('❌ Error logging out: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Logout error:', error);
        alert('❌ Error logging out. Please try again.');
    }
}
function initChart() {
    const symbolSelect = document.getElementById('chartSymbol');
    symbolSelect.innerHTML = '';
    
    // Get ALL symbols from currentPrices
    let allSymbols = [];
    
    if (window.currentPrices && Object.keys(window.currentPrices).length > 0) {
        allSymbols = Object.keys(window.currentPrices).sort();
    } else if (previousPrices && Object.keys(previousPrices).length > 0) {
        allSymbols = Object.keys(previousPrices).sort();
    } else {
        // Fallback list of all symbols
        allSymbols = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF', 'EURTRY',
            'GBPJPY', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD',
            'AUDJPY', 'AUDCAD', 'AUDCHF', 'AUDNZD',
            'CADJPY', 'CHFJPY', 'NZDJPY',
            'USDTRY', 'USDMXN', 'USDZAR', 'USDSGD', 'USDHKD',
            '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000',
            '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
            '#ASX200', '#IBEX35', '#AEX25',
            'GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM',
            'BRENT_OIL', 'CrudeOIL', 'NATURAL_GAS',
            '#DOLLAR_IND'
        ];
    }
    
    // Add all symbols to dropdown
    const currentSelection = symbolSelect.value || allSymbols[0];
    allSymbols.forEach(sym => {
        const option = document.createElement('option');
        option.value = sym;
        option.textContent = sym;
        symbolSelect.appendChild(option);
    });
    
    // Set current symbol
    if (allSymbols.includes(currentSelection)) {
        currentSymbol = currentSelection;
        symbolSelect.value = currentSymbol;
    } else {
        currentSymbol = allSymbols[0] || 'EURUSD';
        symbolSelect.value = currentSymbol;
    }
    
    // Load or reuse history
    loadChartHistoryForSymbol(currentSymbol);
    createColoredChart();
    
    // Start chart updates if not already running
    if (!chartInterval) {
        startChartUpdates();
    }
    
    chartInitialized = true;
}
function loadChartHistoryForSymbol(symbol) {
    // Check if we already have history for this symbol
    if (chartHistory[symbol] && chartHistory[symbol].length > 0) {
        console.log(`📊 Using cached history for ${symbol} (${chartHistory[symbol].length} bars)`);
        return;
    }
    
    // Get current price from dashboard data
    const currentPrice = getCurrentPrice(symbol);
    
    // Store last known price
    lastKnownPrices[symbol] = currentPrice;
    
    // Generate initial history - ONLY ONCE per symbol
    chartHistory[symbol] = [];
    const basePrice = currentPrice > 0 ? currentPrice : 1.1000;
    
    // Generate 50 bars of historical data with realistic movement
    let price = basePrice * 0.995; // Start slightly below current
    const volatility = basePrice * 0.0005; // 0.05% volatility
    
    for (let i = 0; i < 50; i++) {
        const time = new Date(Date.now() - (50 - i) * currentTimeframe * 1000);
        // Random walk with mean reversion toward base price
        const drift = (basePrice - price) * 0.01;
        const random = (Math.random() - 0.5) * volatility * 3;
        const change = drift + random;
        price = price + change;
        
        // Ensure price stays reasonable
        if (price < basePrice * 0.97) price = basePrice * 0.97;
        if (price > basePrice * 1.03) price = basePrice * 1.03;
        
        const open = price;
        const close = price + (Math.random() - 0.5) * volatility;
        const high = Math.max(open, close) + Math.random() * volatility * 0.5;
        const low = Math.min(open, close) - Math.random() * volatility * 0.5;
        
        chartHistory[symbol].push({ 
            time, 
            open, 
            high, 
            low, 
            close: close 
        });
    }
    
    console.log(`📊 Generated initial history for ${symbol} (${chartHistory[symbol].length} bars)`);
}
function getCurrentPrice(symbol) {
    const prices = window.currentPrices || {};
    const priceData = prices[symbol];
    if (priceData && priceData.price) {
        return priceData.price;
    }
    const fallbackPrices = {
        'EURUSD': 1.1000, 'GBPUSD': 1.2700, 'USDJPY': 148.00,
        'USDCHF': 0.9000, 'AUDUSD': 0.6600, 'USDCAD': 1.3600,
        'NZDUSD': 0.6000, '#NASDAQ100': 18000, '#DJ30': 38000,
        '#S&P500': 4800, 'GOLD': 2300, 'SILVER': 28.00,
        'BRENT_OIL': 85.00, 'CrudeOIL': 80.00
    };
    return fallbackPrices[symbol] || 1.1000;
}
function createColoredChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    if (priceChart) {
        priceChart.destroy();
        priceChart = null;
    }
    
    // Check if checkbox exists
    const checkbox = document.getElementById('showPriceLine');
    if (checkbox) {
        showPriceLine = checkbox.checked;
    }
    
    if (!chartHistory[currentSymbol] || chartHistory[currentSymbol].length === 0) {
        loadChartHistoryForSymbol(currentSymbol);
    }
    
    const history = chartHistory[currentSymbol] || [];
    if (history.length === 0) {
        loadChartHistoryForSymbol(currentSymbol);
        return createColoredChart();
    }
    
    const labels = history.map(d => d.time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
    const prices = history.map(d => d.close);
    const currentPrice = getCurrentPrice(currentSymbol);
    
    const allPrices = history.flatMap(d => [d.high, d.low]);
    const minPrice = Math.min(...allPrices, currentPrice);
    const maxPrice = Math.max(...allPrices, currentPrice);
    const padding = (maxPrice - minPrice) * 0.05 || 0.001;
    
    // ============ BUILD DATASETS ============
    const datasets = [
        {
            label: currentSymbol,
            data: prices,
            borderColor: '#ffd700',
            backgroundColor: 'rgba(255, 215, 0, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 1,
            pointBackgroundColor: '#ffd700',
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#ffd700',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2,
            order: 2
        },
        {
            label: 'Current Price',
            data: Array(history.length).fill(currentPrice),
            type: 'line',
            borderColor: '#00bcd4',
            backgroundColor: 'rgba(0, 188, 212, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 1,
            borderDash: [5, 5],
            hidden: !showPriceLine
        }
    ];
    
    // ============ ADD SL/TP LINES IF POSITION EXISTS ============
    if (openPositions.length > 0) {
        // Find the position that matches the current symbol
        const matchingPositions = openPositions.filter(pos => pos.symbol === currentSymbol);
        
        if (matchingPositions.length > 0) {
            // Use the most recent matching position
            const pos = matchingPositions[matchingPositions.length - 1];
            
            // Validate SL and TP values
            if (pos.sl && pos.sl > 0 && !isNaN(pos.sl)) {
                // Add SL line (Red)
                datasets.push({
                    label: 'SL',
                    data: Array(history.length).fill(pos.sl),
                    type: 'line',
                    borderColor: '#f44336',
                    backgroundColor: 'rgba(244, 67, 54, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0,
                    order: 0,
                    borderDash: [8, 4],
                    pointHoverRadius: 0,
                    pointHoverBackgroundColor: '#f44336'
                });
            }
            
            if (pos.tp && pos.tp > 0 && !isNaN(pos.tp)) {
                // Add TP line (Green)
                datasets.push({
                    label: 'TP',
                    data: Array(history.length).fill(pos.tp),
                    type: 'line',
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0,
                    order: 0,
                    borderDash: [8, 4],
                    pointHoverRadius: 0,
                    pointHoverBackgroundColor: '#4caf50'
                });
            }
            
            if (pos.entryPrice && pos.entryPrice > 0 && !isNaN(pos.entryPrice)) {
                // Add Entry line (Yellow)
                datasets.push({
                    label: 'Entry',
                    data: Array(history.length).fill(pos.entryPrice),
                    type: 'line',
                    borderColor: '#ffd700',
                    backgroundColor: 'rgba(255, 215, 0, 0.05)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0,
                    order: 0,
                    borderDash: [4, 4],
                    pointHoverRadius: 0,
                    pointHoverBackgroundColor: '#ffd700'
                });
            }
        }
    }
    
    // ============ CREATE CHART ============
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#e0e0e0',
                        font: { size: 11 },
                        boxWidth: 12,
                        padding: 10,
                        // Custom label colors for SL/TP
                        generateLabels: function(chart) {
                            const labels = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                            return labels.map(label => {
                                // Set custom colors for SL/TP labels
                                if (label.text === 'SL') {
                                    label.fillStyle = '#f44336';
                                    label.strokeStyle = '#f44336';
                                } else if (label.text === 'TP') {
                                    label.fillStyle = '#4caf50';
                                    label.strokeStyle = '#4caf50';
                                } else if (label.text === 'Entry') {
                                    label.fillStyle = '#ffd700';
                                    label.strokeStyle = '#ffd700';
                                } else if (label.text === 'Current Price') {
                                    label.fillStyle = '#00bcd4';
                                    label.strokeStyle = '#00bcd4';
                                }
                                return label;
                            });
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 39, 0.95)',
                    borderColor: '#ffd700',
                    borderWidth: 1,
                    titleColor: '#ffd700',
                    bodyColor: '#e0e0e0',
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            
                            if (label === currentSymbol) {
                                return 'Price: ' + value.toFixed(5);
                            } else if (label === 'Current Price') {
                                return 'Current Price: ' + value.toFixed(5);
                            } else if (label === 'SL') {
                                return '🚫 Stop Loss: ' + value.toFixed(5);
                            } else if (label === 'TP') {
                                return '🎯 Take Profit: ' + value.toFixed(5);
                            } else if (label === 'Entry') {
                                return '📌 Entry: ' + value.toFixed(5);
                            }
                            return label + ': ' + value.toFixed(5);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#666',
                        font: { size: 9 },
                        maxTicksLimit: 15
                    }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#666',
                        font: { size: 10 },
                        callback: function(value) {
                            return value.toFixed(5);
                        }
                    },
                    min: minPrice - padding,
                    max: maxPrice + padding
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
    
    // ============ UPDATE POSITION INDICATOR ============
    if (openPositions.length > 0) {
        const matchingPositions = openPositions.filter(pos => pos.symbol === currentSymbol);
        if (matchingPositions.length > 0) {
            const pos = matchingPositions[matchingPositions.length - 1];
            updatePositionIndicator(
                pos.symbol,
                pos.entryPrice,
                pos.direction,
                pos.sl,
                pos.tp
            );
        }
    }
    
    updateChartStats();
}
// ============ BALANCE CHECK FUNCTION ============
function checkSufficientBalance(symbol, lotSize = 0.01) {
    const balanceElement = document.getElementById('balance');
    if (!balanceElement) return false;
    
    const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
    
    const leverage = 500;
    const contractSize = 100000;
    const priceData = window.currentPrices ? window.currentPrices[symbol] : null;
    let currentPrice = 1.1000;
    
    if (priceData && priceData.price) {
        currentPrice = priceData.price;
    }
    
    const requiredMargin = (lotSize * contractSize * currentPrice) / leverage;
    const minBalance = requiredMargin * 1.2;
    
    // Store for display
    checkSufficientBalance.calcMin = minBalance;
    
    return currentBalance >= minBalance;
}
function updateChartData() {
    const priceData = window.currentPrices ? window.currentPrices[currentSymbol] : null;
    if (!priceData || !priceData.price) return;
    checkSLTP();
    const currentPrice = priceData.price;
    const bid = priceData.bid || currentPrice;
    const ask = priceData.ask || currentPrice;
    
    // Update last known price
    lastKnownPrices[currentSymbol] = currentPrice;
    
    // Initialize history if it doesn't exist
    if (!chartHistory[currentSymbol] || chartHistory[currentSymbol].length === 0) {
        loadChartHistoryForSymbol(currentSymbol);
        return;
    }
    
    const now = new Date();
    const lastEntry = chartHistory[currentSymbol][chartHistory[currentSymbol].length - 1];
    const timeDiff = (now - lastEntry.time) / 1000; // in seconds
    
    // Only add new bar if enough time has passed
    if (timeDiff >= currentTimeframe) {
        // Create new bar
        chartHistory[currentSymbol].push({
            time: now,
            open: currentPrice,
            high: currentPrice,
            low: currentPrice,
            close: currentPrice
        });
        
        // Keep only last 100 bars
        if (chartHistory[currentSymbol].length > 100) {
            chartHistory[currentSymbol].shift();
        }
    } else {
        // Update the last bar's close, high, low
        lastEntry.close = currentPrice;
        lastEntry.high = Math.max(lastEntry.high, currentPrice);
        lastEntry.low = Math.min(lastEntry.low, currentPrice);
    }
    
    // Update chart if it exists
    if (priceChart) {
        const history = chartHistory[currentSymbol];
        const labels = history.map(d => d.time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
        const prices = history.map(d => d.close);
        
        priceChart.data.labels = labels;
        priceChart.data.datasets[0].data = prices;
        
        // Update current price line
        const showLine = document.getElementById('showPriceLine')?.checked ?? true;
        priceChart.data.datasets[1].data = Array(history.length).fill(currentPrice);
        priceChart.data.datasets[1].hidden = !showLine;
        
        priceChart.update('none');
    }
    
    updateChartStats();
}
// ============ HISTORY PAGE ============
let historyData = [];
let filteredHistory = [];
let historyCurrentPage = 1;
const HISTORY_PER_PAGE = 20;

async function loadHistory() {
    const historyBody = document.getElementById('historyTableBody');
    historyBody.innerHTML = '<tr><td colspan="11" class="no-data">⏳ Loading trade history...</td></tr>';
    
    try {
        const response = await fetch('/api/trade_history');
        const data = await response.json();
        
        if (data.success && data.trades) {
            historyData = data.trades;
            console.log(`📜 Loaded ${historyData.length} trades from database`);
            populateSymbolFilter(historyData);
            applyHistoryFilter();
        } else {
            historyBody.innerHTML = '<tr><td colspan="11" class="no-data">📭 No trade history found</td></tr>';
            document.getElementById('historyTotalTrades').textContent = '0';
            document.getElementById('historyPageInfo').textContent = 'Page 0 of 0';
        }
    } catch (e) {
        console.error('Error loading history:', e);
        historyBody.innerHTML = '<tr><td colspan="11" class="no-data">❌ Error loading trade history. Please try again.</td></tr>';
    }
}

function populateSymbolFilter(trades) {
    const symbolSelect = document.getElementById('historySymbolFilter');
    const symbols = new Set();
    trades.forEach(t => {
        if (t.symbol) symbols.add(t.symbol);
    });
    
    // Clear existing options except "All"
    while (symbolSelect.options.length > 1) {
        symbolSelect.remove(1);
    }
    
    Array.from(symbols).sort().forEach(symbol => {
        const option = document.createElement('option');
        option.value = symbol;
        option.textContent = symbol;
        symbolSelect.appendChild(option);
    });
}

function applyHistoryFilter() {
    const symbolFilter = document.getElementById('historySymbolFilter').value;
    const directionFilter = document.getElementById('historyDirectionFilter').value;
    const statusFilter = document.getElementById('historyStatusFilter').value;
    const dateFrom = document.getElementById('historyDateFrom').value;
    const dateTo = document.getElementById('historyDateTo').value;
    
    filteredHistory = historyData.filter(trade => {
        // Symbol filter
        if (symbolFilter !== 'all' && trade.symbol !== symbolFilter) return false;
        
        // Direction filter
        if (directionFilter !== 'all' && trade.direction !== directionFilter) return false;
        
        // Status filter
        if (statusFilter !== 'all') {
            const tradeStatus = trade.status || 'CLOSED';
            if (statusFilter === 'OPEN' && tradeStatus !== 'OPEN') return false;
            if (statusFilter === 'CLOSED' && tradeStatus !== 'CLOSED' && tradeStatus !== 'SL' && tradeStatus !== 'TP') return false;
            if (statusFilter === 'TP' && tradeStatus !== 'TP') return false;
            if (statusFilter === 'SL' && tradeStatus !== 'SL') return false;
        }
        
        // Date filter
        if (dateFrom) {
            const tradeDate = trade.open_time ? new Date(trade.open_time).toISOString().split('T')[0] : '';
            if (tradeDate < dateFrom) return false;
        }
        if (dateTo) {
            const tradeDate = trade.open_time ? new Date(trade.open_time).toISOString().split('T')[0] : '';
            if (tradeDate > dateTo) return false;
        }
        
        return true;
    });
    
    console.log(`📊 Filtered to ${filteredHistory.length} trades`);
    historyCurrentPage = 1;
    renderHistoryPage();
    updateHistorySummary();
}

function renderHistoryPage() {
    const historyBody = document.getElementById('historyTableBody');
    const totalPages = Math.ceil(filteredHistory.length / HISTORY_PER_PAGE) || 1;
    const start = (historyCurrentPage - 1) * HISTORY_PER_PAGE;
    const end = Math.min(start + HISTORY_PER_PAGE, filteredHistory.length);
    const pageData = filteredHistory.slice(start, end);
    
    if (pageData.length === 0) {
        historyBody.innerHTML = '<tr><td colspan="11" class="no-data">📭 No trades match your filters</td></tr>';
        document.getElementById('historyPageInfo').textContent = `Page 0 of 0`;
        document.getElementById('prevPageBtn').disabled = true;
        document.getElementById('nextPageBtn').disabled = true;
        return;
    }
    
    let html = '';
    pageData.forEach((trade, index) => {
        const rowNum = start + index + 1;
        const directionClass = trade.direction === 'BUY' ? 'direction-buy' : 'direction-sell';
        const pnl = parseFloat(trade.pnl || 0);
        const pnlClass = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const status = trade.status || 'CLOSED';
        
        let statusClass = 'status-closed';
        let statusDisplay = '✅ CLOSED';
        if (status === 'SL') {
            statusClass = 'status-sl';
            statusDisplay = '🔴 SL';
        } else if (status === 'TP') {
            statusClass = 'status-tp';
            statusDisplay = '🟢 TP';
        } else if (status === 'OPEN') {
            statusClass = 'status-open';
            statusDisplay = '🔓 OPEN';
        }
        
        const entryPrice = trade.entry_price ? parseFloat(trade.entry_price).toFixed(5) : '--';
        const closePrice = trade.close_price ? parseFloat(trade.close_price).toFixed(5) : '--';
        const sl = trade.sl ? parseFloat(trade.sl).toFixed(5) : '--';
        const tp = trade.tp ? parseFloat(trade.tp).toFixed(5) : '--';
        const lotSize = trade.lot_size || 0.01;
        const date = trade.open_time ? new Date(trade.open_time).toLocaleString() : 'N/A';
        
        html += `
            <tr>
                <td>${rowNum}</td>
                <td><strong style="color:#ffd700;">${trade.symbol || 'N/A'}</strong></td>
                <td class="${directionClass}">${trade.direction || 'N/A'}</td>
                <td>${entryPrice}</td>
                <td>${closePrice}</td>
                <td>${sl}</td>
                <td>${tp}</td>
                <td>${lotSize}</td>
                <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td class="${statusClass}">${statusDisplay}</td>
                <td style="font-size:11px;color:#888;">${date}</td>
            </tr>
        `;
    });
    
    historyBody.innerHTML = html;
    
    // Update pagination
    document.getElementById('historyPageInfo').textContent = `Page ${historyCurrentPage} of ${totalPages}`;
    document.getElementById('prevPageBtn').disabled = historyCurrentPage <= 1;
    document.getElementById('nextPageBtn').disabled = historyCurrentPage >= totalPages;
}

function updateHistorySummary() {
    const total = filteredHistory.length;
    let totalProfit = 0;
    let totalLoss = 0;
    let winningTrades = 0;
    let bestTrade = 0;
    
    filteredHistory.forEach(trade => {
        const pnl = parseFloat(trade.pnl || 0);
        if (pnl > 0) {
            totalProfit += pnl;
            winningTrades++;
            if (pnl > bestTrade) bestTrade = pnl;
        } else {
            totalLoss += Math.abs(pnl);
        }
    });
    
    const winRate = total > 0 ? (winningTrades / total) * 100 : 0;
    const netPnl = totalProfit - totalLoss;
    
    document.getElementById('historyTotalTrades').textContent = total;
    document.getElementById('historyWinRate').textContent = winRate.toFixed(1) + '%';
    document.getElementById('historyTotalProfit').textContent = '$' + totalProfit.toFixed(2);
    document.getElementById('historyTotalLoss').textContent = '$' + totalLoss.toFixed(2);
    
    const netElement = document.getElementById('historyNetPnl');
    netElement.textContent = (netPnl >= 0 ? '+' : '') + '$' + netPnl.toFixed(2);
    netElement.className = 'stat-value ' + (netPnl >= 0 ? 'positive' : 'negative');
    
    document.getElementById('historyBestTrade').textContent = '$' + bestTrade.toFixed(2);
}

function historyPrevPage() {
    if (historyCurrentPage > 1) {
        historyCurrentPage--;
        renderHistoryPage();
    }
}

function historyNextPage() {
    const totalPages = Math.ceil(filteredHistory.length / HISTORY_PER_PAGE);
    if (historyCurrentPage < totalPages) {
        historyCurrentPage++;
        renderHistoryPage();
    }
}

function refreshHistory() {
    loadHistory();
}

function clearHistoryFilter() {
    document.getElementById('historySymbolFilter').value = 'all';
    document.getElementById('historyDirectionFilter').value = 'all';
    document.getElementById('historyStatusFilter').value = 'all';
    document.getElementById('historyDateFrom').value = '';
    document.getElementById('historyDateTo').value = '';
    applyHistoryFilter();
}
function updateChartStats() {
    const priceData = window.currentPrices ? window.currentPrices[currentSymbol] : null;
    if (!priceData || !priceData.price) return;
    
    const currentPrice = priceData.price;
    const bid = priceData.bid || currentPrice;
    const ask = priceData.ask || currentPrice;
    const change = priceData.change || 0;
    
    document.getElementById('chartCurrentPrice').textContent = currentPrice.toFixed(5);
    document.getElementById('chartBid').textContent = bid.toFixed(5);
    document.getElementById('chartAsk').textContent = ask.toFixed(5);
    
    const changeElement = document.getElementById('chartChange');
    changeElement.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
    changeElement.className = 'stat-value ' + (change > 0 ? 'up' : (change < 0 ? 'down' : ''));
    
    const history = chartHistory[currentSymbol] || [];
    if (history.length > 0) {
        const highs = history.map(d => d.high);
        const lows = history.map(d => d.low);
        document.getElementById('chartHigh').textContent = Math.max(...highs).toFixed(5);
        document.getElementById('chartLow').textContent = Math.min(...lows).toFixed(5);
    }
}
function switchChart() {
    const symbolSelect = document.getElementById('chartSymbol');
    const timeframeSelect = document.getElementById('chartTimeframe');
    
    if (!symbolSelect || !timeframeSelect) return;
    
    const newSymbol = symbolSelect.value;
    const newTimeframe = parseInt(timeframeSelect.value);
    
    // Check if we need to reload history (only if symbol changed)
    const symbolChanged = newSymbol !== currentSymbol;
    
    currentSymbol = newSymbol;
    currentTimeframe = newTimeframe;
    
    // Only load history if symbol changed or no history exists
    if (symbolChanged || !chartHistory[currentSymbol] || chartHistory[currentSymbol].length === 0) {
        loadChartHistoryForSymbol(currentSymbol);
    }
    
    createColoredChart();
    
    // Re-add position indicators if positions exist
    if (openPositions.length > 0) {
        setTimeout(() => {
            const lastPos = openPositions[openPositions.length - 1];
            if (priceChart) {
                priceChart._positionData = {
                    symbol: lastPos.symbol,
                    entryPrice: lastPos.entryPrice,
                    direction: lastPos.direction,
                    sl: lastPos.sl,
                    tp: lastPos.tp
                };
                updatePositionIndicator(
                    lastPos.symbol,
                    lastPos.entryPrice,
                    lastPos.direction,
                    lastPos.sl,
                    lastPos.tp
                );
            }
        }, 300);
    }
}
function loadPersistedChartData() {
    try {
        const saved = localStorage.getItem('chartHistory');
        if (saved) {
            const parsed = JSON.parse(saved);
            // Restore history, converting string dates back to Date objects
            for (const [symbol, bars] of Object.entries(parsed)) {
                chartHistory[symbol] = bars.map(bar => ({
                    ...bar,
                    time: new Date(bar.time)
                }));
                console.log(`📊 Loaded ${bars.length} bars for ${symbol} from localStorage`);
            }
        }
    } catch (e) {
        console.log('No saved chart data found');
    }
}

function saveChartHistory() {
    try {
        // Only save last 100 bars per symbol to keep size manageable
        const toSave = {};
        for (const [symbol, bars] of Object.entries(chartHistory)) {
            if (bars && bars.length > 0) {
                toSave[symbol] = bars.slice(-100).map(bar => ({
                    ...bar,
                    time: bar.time.toISOString()
                }));
            }
        }
        localStorage.setItem('chartHistory', JSON.stringify(toSave));
    } catch (e) {
        // Ignore save errors
    }
}
function refreshChart() {
    // Don't regenerate random data - just update with current prices
    const priceData = window.currentPrices ? window.currentPrices[currentSymbol] : null;
    if (priceData && priceData.price) {
        // Force a price update
        updateChartData();
        // Refresh the chart display
        if (priceChart) {
            priceChart.update();
        }
    } else {
        // Only regenerate if no price data exists
        loadChartHistoryForSymbol(currentSymbol);
        createColoredChart();
    }
}

function startChartUpdates() {
    if (chartInterval) clearInterval(chartInterval);
    chartInterval = setInterval(() => {
        if (document.getElementById('chartsPage').classList.contains('active')) {
            updateChartData();
            // Save history every 10 seconds (only if we have data)
            if (Object.keys(chartHistory).length > 0) {
                saveChartHistory();
            }
        }
    }, 100); // Update every 100ms for smooth chart
}

// ============ FIXED: UPDATE PRICES WITH ALL SYMBOLS ============
const originalUpdatePrices = updatePrices;
updatePrices = function(prices) {
    window.currentPrices = prices;
    originalUpdatePrices(prices);
    
    if (document.getElementById('chartsPage').classList.contains('active')) {
        updateChartData();
    }
    
    const symbolSelect = document.getElementById('chartSymbol');
    if (symbolSelect) {
        const symbols = Object.keys(prices).sort();
        const currentOptions = Array.from(symbolSelect.options).map(opt => opt.value);
        
        // Check if we need to update the dropdown
        const needsUpdate = symbols.length > 0 && (
            currentOptions.length !== symbols.length ||
            !symbols.every(sym => currentOptions.includes(sym))
        );
        
        if (needsUpdate) {
            const currentSelection = symbolSelect.value;
            
            // Clear and repopulate with ALL symbols
            symbolSelect.innerHTML = '';
            symbols.forEach(sym => {
                const option = document.createElement('option');
                option.value = sym;
                option.textContent = sym;
                symbolSelect.appendChild(option);
            });
            
            // Restore selection if possible
            if (symbols.includes(currentSelection)) {
                symbolSelect.value = currentSelection;
            } else {
                currentSymbol = symbols[0];
                symbolSelect.value = currentSymbol;
            }
            
            loadChartHistoryForSymbol(currentSymbol);
            createColoredChart();
        }
    }
};
// ============ SKIP SIGNAL ============
let skippedSignals = new Set();
async function loadSkippedSignals() {
    try {
        // Remove X-User-ID header
        const response = await fetch('/api/get_skipped_signals');
        const data = await response.json();
        if (data.success && data.skipped) {
            skippedSignals = new Set(data.skipped.map(id => String(id)));
            console.log('Loaded skipped signals:', skippedSignals);
        }
    } catch (e) {
        console.error('Error loading skipped signals:', e);
    }
}
async function skipSignal(symbol, direction, signalId) {
    console.log('Skip signal called:', { symbol, direction, signalId });
    
    if (!confirm(`Skip ${direction} signal for ${symbol}?`)) return;
    
    try {
        const response = await fetch('/api/skip_signal', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                signal_id: String(signalId),
                symbol: symbol,
                direction: direction
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Add to local set - use consistent string format
            const signalIdStr = String(signalId);
            skippedSignals.add(signalIdStr);
            console.log('Skipped signals set:', skippedSignals);
            
            // Remove the signal element immediately
            const signalElement = document.getElementById(`signal-${signalIdStr}`);
            if (signalElement) {
                // Animate removal
                signalElement.style.transition = 'all 0.3s ease';
                signalElement.style.opacity = '0';
                signalElement.style.transform = 'translateX(-20px)';
                signalElement.style.maxHeight = '0';
                signalElement.style.padding = '0';
                signalElement.style.margin = '0';
                signalElement.style.overflow = 'hidden';
                
                setTimeout(() => {
                    if (signalElement.parentElement) {
                        signalElement.remove();
                    }
                    updateSignalCount();
                }, 400);
            }
            
            showNotification('Signal Skipped', `${direction} signal for ${symbol} has been skipped`);
        } else {
            alert('❌ Error skipping signal: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Error skipping signal:', e);
        alert('❌ Error skipping signal. Please try again.');
    }
}
async function resetSkippedSignals() {
    if (!confirm('Reset all skipped signals?')) return;
    
    try {
        const response = await fetch('/api/reset_skipped_signals', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            skippedSignals.clear();
            if (window.lastSignalsData) {
                updateSignals(window.lastSignalsData);
            } else {
                location.reload();
            }
            showNotification('Reset', 'All skipped signals have been reset');
        }
    } catch (e) {
        console.error('Error resetting skipped signals:', e);
        alert('Error resetting skipped signals');
    }
}
// Helper function to update signal count
function updateSignalCount() {
    const remainingSignals = document.querySelectorAll('.signal-item:not([style*="display: none"])');
    const signalCount = document.getElementById('signalCount');
    if (signalCount) {
        signalCount.textContent = remainingSignals.length;
    }
    
    const signalsList = document.getElementById('signalsList');
    if (signalsList && remainingSignals.length === 0) {
        // Only update if there's no "no signals" message already
        const noSignals = signalsList.querySelector('.no-signals');
        if (!noSignals) {
            signalsList.innerHTML = '<div class="no-signals">No active signals. All signals have been skipped.</div>';
        }
    }
}

// Simple notification system
function showNotification(title, message) {
    const existing = document.querySelector('.notification-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 24px;">✅</span>
            <div>
                <div style="font-weight: bold; color: #ffd700;">${title}</div>
                <div style="font-size: 13px; color: #aaa;">${message}</div>
            </div>
        </div>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: #666; font-size: 18px; cursor: pointer;">✕</button>
    `;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #0a0e27;
        border: 1px solid #ffd700;
        border-radius: 10px;
        padding: 15px 20px;
        color: #e0e0e0;
        z-index: 3000;
        display: flex;
        align-items: center;
        gap: 15px;
        min-width: 300px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}
// ============ SAVE CARD FUNCTION ============
async function saveCard() {
    console.log('🔵 Save Card button clicked!');
    
    const cardId = document.getElementById('cardId').value.trim();
    const pin = document.getElementById('cardPin').value.trim();
    const cardHolderName = document.getElementById('cardHolderName').value.trim().toUpperCase();
    
    // Validate fields
    if (!cardId || cardId.length < 8) {
        alert('⚠️ Please enter at least 8 digits for the card number.');
        return;
    }
    
    if (!pin || pin.length < 4) {
        alert('⚠️ Please enter a 4-digit PIN.');
        return;
    }
    
    if (!cardHolderName) {
        alert('⚠️ Please enter the card holder name.');
        return;
    }
    
    // Disable buttons while processing
    const saveBtn = document.querySelector('.btn-submit');
    const cancelBtn = document.querySelector('.btn-cancel');
    saveBtn.disabled = true;
    saveBtn.textContent = '⏳ Checking...';
    cancelBtn.disabled = true;
    
    try {
        // Check if card exists in database
        const checkResponse = await fetch('/api/check_card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: cardId,
                card_pin: pin,
                username: cardHolderName
            })
        });
        
        const checkResult = await checkResponse.json();
        console.log('Check result:', checkResult);
        
        if (checkResult.success && checkResult.exists) {
            // Card exists - add it to dashboard
            const card = checkResult.card;
            const balance = card.balance || card.amount || 0;
            
            const confirmMsg = `✅ Card found in database!\n\n` +
                `Status: ${card.is_active ? 'Active' : 'Inactive'}\n\n` +
                `Add this card to your dashboard?`;
            
            if (confirm(confirmMsg)) {
                // Add the card to user's dashboard
                const addResponse = await fetch('/api/add_card_to_user', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        card_id: cardId,
                        card_pin: pin,
                        username: cardHolderName
                    })
                });
                
                const addResult = await addResponse.json();
                
                if (addResult.success) {
                    alert('✅ Card added to your dashboard!');
                    closeAddCardModal();
                    loadCards();
                    refreshData();
                    document.getElementById('addCardForm').reset();
                    // Reset preview
                    document.getElementById('previewCardNumber').textContent = '1234 5678';
                    document.getElementById('previewCardHolder').textContent = 'JOHN DOE';
                    document.getElementById('previewPin').textContent = '1234';
                } else {
                    if (addResult.error && addResult.error.includes('already added')) {
                        alert('⚠️ This card is already in your dashboard!');
                    } else {
                        alert('❌ Error: ' + (addResult.error || 'Unknown error'));
                    }
                }
            }
        } else {
            // Card not found - show error, DO NOT ask to create
            alert(`❌ Invalid Card!\n\n` +
                `This card does not exist in our system. Please check the card details and try again.`);
        }
    } catch (e) {
        console.error('❌ Error:', e);
        alert('❌ Error processing request. Please try again.');
    } finally {
        // Re-enable buttons
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Card';
        cancelBtn.disabled = false;
    }
}
async function loadCards() {
    try {
        // Remove the X-User-ID header - use cookies instead
        const response = await fetch('/api/cards');
        const data = await response.json();
        
        if (data.success && data.cards) {
            renderCards(data.cards);
        }
    } catch (e) {
        console.error('Error loading cards:', e);
    }
}
function renderCards(cards) {
    const cardsGrid = document.getElementById('cardsGrid');
    const totalCardsCount = document.getElementById('totalCardsCount');
    const totalCardsBalance = document.getElementById('totalCardsBalance');
    
    if (!cards || cards.length === 0) {
        cardsGrid.innerHTML = `
            <div class="no-cards-message">
                <span class="icon">💳</span>
                No cards added yet.<br>
                Click the "Add New Card" button to get started.
            </div>
        `;
        totalCardsCount.textContent = '0';
        totalCardsBalance.textContent = '$0.00';
        return;
    }
    
    let html = '';
    let totalBalance = 0;
    
    for (const card of cards) {
        const balance = card.balance || card.amount || 0;
        totalBalance += balance;
        
        const statusClass = card.is_active ? 'active' : 'inactive';
        const statusText = card.is_active ? 'Active' : 'Inactive';
        const added = card.added_at ? new Date(card.added_at).toLocaleDateString() : 'N/A';
        const username = card.username || 'N/A';
        
        html += `
            <div class="card-item">
                <div class="card-balance">$${balance.toFixed(2)}</div>
                <div class="card-info">
                    <div>👤 ${username}</div>
                    <div>📅 Added: ${added}</div>
                </div>
                <span class="card-status ${statusClass}">${statusText}</span>
                <div class="card-actions">
                    <button class="btn-delete" onclick="deleteCard('${card.card_id}')">🗑️ Delete</button>
                </div>
            </div>
        `;
    }
    
    cardsGrid.innerHTML = html;
    totalCardsCount.textContent = cards.length;
    totalCardsBalance.textContent = '$' + totalBalance.toFixed(2);
}
function switchTab(tab, preventRefresh = false) {
    // Hide all pages
    document.querySelectorAll('.page-section').forEach(el => {
        el.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.nav-tab').forEach(el => {
        el.classList.remove('active');
    });
    
    // Show the selected page
    if (tab === 'dashboard') {
        document.getElementById('dashboardPage').classList.add('active');
        document.querySelector('.nav-tab:nth-child(1)').classList.add('active');
        refreshData();
        if (openPositions.length === 0) {
            clearPositionIndicator();
        }
    } else if (tab === 'cards') {
        document.getElementById('cardsPage').classList.add('active');
        document.querySelector('.nav-tab:nth-child(2)').classList.add('active');
        loadCards();
    } else if (tab === 'charts') {
        document.getElementById('chartsPage').classList.add('active');
        document.querySelector('.nav-tab:nth-child(3)').classList.add('active');
        
        // Only init chart if not prevented
        if (!preventRefresh) {
            initChart();
        }
        if (chartPriceUpdateInterval) {
            clearInterval(chartPriceUpdateInterval);
        }
        startChartPriceUpdates();
        setTimeout(updatePositionsList, 200);
        if (openPositions.length > 0) {
            setTimeout(() => {
                const lastPos = openPositions[openPositions.length - 1];
                addPositionMarkersToChart(
                    lastPos.symbol,
                    lastPos.entryPrice,
                    lastPos.direction,
                    lastPos.sl,
                    lastPos.tp
                );
            }, 500);
        }
    }else if (tab === 'history') {
        document.getElementById('historyPage').classList.add('active');
        const tabs = document.querySelectorAll('.nav-tab');
        if (tabs.length >= 4) {
            tabs[3].classList.add('active');
        }
        loadHistory();
    }
    else {
        // Stop chart price updates when not on chart page
        if (chartPriceUpdateInterval) {
            clearInterval(chartPriceUpdateInterval);
            chartPriceUpdateInterval = null;
        }
    }
}
function showAddCardModal() {
    document.getElementById('addCardModal').classList.add('active');
    document.getElementById('addCardForm').reset();
}

function closeAddCardModal() {
    document.getElementById('addCardModal').classList.remove('active');
}
document.getElementById('cardId').addEventListener('input', function() {
    const value = this.value.replace(/\\D/g, '');
    let formatted = value;
    if (value.length > 4) {
        formatted = value.substring(0, 4) + ' ' + value.substring(4, 8);
    }
    document.getElementById('previewCardNumber').textContent = formatted || '1234 5678';
});

document.getElementById('cardHolderName').addEventListener('input', function() {
    const value = this.value.toUpperCase() || 'JOHN DOE';
    document.getElementById('previewCardHolder').textContent = value;
});

document.getElementById('cardPin').addEventListener('input', function() {
    const value = this.value || '1234';
    document.getElementById('previewPin').textContent = value;
});
async function updateCardBalance(cardId, cardPin) {
    const newBalance = prompt(`Enter new balance for card ${cardId}:`, '0');
    if (newBalance === null) return;
    
    const amount = parseFloat(newBalance);
    if (isNaN(amount) || amount < 0) {
        alert('Please enter a valid amount');
        return;
    }
    
    try {
        const response = await fetch('/api/update_card_balance', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                card_id: cardId,
                card_pin: cardPin,
                balance: amount
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Balance updated successfully!');
            loadCards();
            refreshData();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Error updating balance:', e);
        alert('Error updating balance. Please try again.');
    }
}

async function deleteCard(cardId) {
    if (!confirm(`Are you sure you want to delete card ${cardId}?`)) return;
    
    try {
        const response = await fetch('/api/delete_card', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ card_id: cardId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Card deleted successfully!');
            loadCards();
            refreshData();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Error deleting card:', e);
        alert('Error deleting card. Please try again.');
    }
}
// Additional price update for chart - bypasses the 2-second refresh
let chartPriceUpdateInterval = null;

function startChartPriceUpdates() {
    if (chartPriceUpdateInterval) clearInterval(chartPriceUpdateInterval);
    
    // Update chart price every 500ms directly from API
    chartPriceUpdateInterval = setInterval(() => {
        if (!document.getElementById('chartsPage').classList.contains('active')) {
            return;
        }
        
        // Fetch only price data for the current symbol
        fetch('/api/prices?_=' + Date.now())
            .then(r => r.json())
            .then(data => {
                if (data.success && data.prices) {
                    // Update window.currentPrices with latest data
                    if (!window.currentPrices) window.currentPrices = {};
                    
                    // Merge the new prices
                    for (const [symbol, priceData] of Object.entries(data.prices)) {
                        if (symbol === currentSymbol) {
                            window.currentPrices[symbol] = priceData;
                            // Trigger chart update
                            updateChartData();
                        }
                    }
                }
            })
            .catch(() => { /* silent fail */ });
    }, 500); // Update every 500ms for faster chart response
}
document.addEventListener('DOMContentLoaded', function() {
    loadCards();
    loadPositions();
    loadPersistedChartData();
    // ============ FIX: Initialize daily P&L correctly ============
    const today = new Date().toDateString();
    const savedDate = localStorage.getItem('dailyPnlDate');
    let savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
    
    // Reset if it's a new day
    if (savedDate !== today) {
        savedPnl = 0;
        localStorage.setItem('dailyPnlSaved', '0');
        localStorage.setItem('dailyPnlDate', today);
    }
    
    dailyPnlTracker = savedPnl;
    console.log('📅 Daily P&L initialized to:', savedPnl);
    
    // Update display
    const dailyPnlElement = document.getElementById('dailyPnl');
    if (dailyPnlElement) {
        const formatted = (savedPnl >= 0 ? '+' : '') + '$' + savedPnl.toFixed(2);
        dailyPnlElement.textContent = formatted;
        dailyPnlElement.className = 'account-value ' + (savedPnl > 0 ? 'green' : (savedPnl < 0 ? 'red' : ''));
        dailyPnlElement.style.color = savedPnl > 0 ? '#4caf50' : (savedPnl < 0 ? '#f44336' : '#888');
    }
    initializeDailyPnl();
    window.currentPrices = {};
    chartHistory = {};
    
    setTimeout(() => {
        updatePositionsList();
        updatePositionPrices();
    }, 500);
    
    setTimeout(() => {
        if (document.getElementById('chartsPage')) {
            initChart();
        }
    }, 1000);
});
// ============ PERSIST POSITIONS ============
function savePositions() {
    try {
        localStorage.setItem('openPositions', JSON.stringify(openPositions));
        localStorage.setItem('positionIdCounter', positionIdCounter.toString());
    } catch (e) {
        console.error('Error saving positions:', e);
    }
}

function loadPositions() {
    try {
        const saved = localStorage.getItem('openPositions');
        if (saved) {
            openPositions = JSON.parse(saved);
            // Restore dates
            openPositions.forEach(pos => {
                pos.openTime = pos.openTime || new Date().toLocaleTimeString();
            });
        }
        const savedCounter = localStorage.getItem('positionIdCounter');
        if (savedCounter) {
            positionIdCounter = parseInt(savedCounter) || 0;
        }
    } catch (e) {
        console.error('Error loading positions:', e);
        openPositions = [];
        positionIdCounter = 0;
    }
}
async function refreshData() {
    document.getElementById('refreshStatus').textContent = '⏳ Loading...';
    
    try {
        await loadSkippedSignals();
        const response = await fetch('/api/prices?_=' + Date.now());
        const data = await response.json();
        
        if (data.success) {
            // Update account - Balance
            const cardBalance = data.balance || data.card_balance || 0;
            document.getElementById('balance').textContent = '$' + cardBalance.toFixed(2);
            document.getElementById('updated').textContent = data.timestamp || '--:--:--';
            document.getElementById('dataSource').textContent = data.source || 'Unknown';
            document.getElementById('sourceTag').textContent = '📡 ' + (data.source || 'Unknown');
            
            // ============ GET BALANCE FROM CARDS ============
            const cardsResponse = await fetch('/api/cards', {
            });
            const cardsData = await cardsResponse.json();
            
            let totalBalance = 0;
            
            if (cardsData.success && cardsData.cards) {
                for (const card of cardsData.cards) {
                    const balance = card.balance || card.amount || 0;
                    totalBalance += balance;
                }
            }
            
            // ============ GET POSITIONS FROM openPositions ============
            const positions = openPositions || [];
            
            // ============ CALCULATE TOTAL P&L FROM POSITIONS ============
            let totalPnl = 0;
            for (const pos of positions) {
                totalPnl += pos.pnl || 0;
            }
            
            // ============ CALCULATE EQUITY ============
            // Equity = Balance + Total P&L
            const totalEquity = totalBalance + totalPnl;
            
            // ============ CALCULATE USED MARGIN ============
            let usedMargin = 0;
            const hasPositions = positions && positions.length > 0;
            
            if (hasPositions) {
                // Calculate margin based on actual positions
                const leverage = 500;
                const contractSize = 100000;
                const priceData = data.prices || {};
                let currentPrice = 1.1000;
                if (priceData['EURUSD']) {
                    currentPrice = priceData['EURUSD'].price || 1.1000;
                }
                
                for (const pos of positions) {
                    const vol = Number(pos.lotSize || 0.01);
                    const price = Number(pos.entryPrice || currentPrice);
                    usedMargin += (vol * contractSize * price) / leverage;
                }
            } else {
                usedMargin = 0;
            }
            
            // ============ CALCULATE FREE MARGIN ============
            const freeMargin = totalEquity - usedMargin;
            
            // ============ CALCULATE MARGIN LEVEL ============
            let marginLevel = 0;
            marginLevel = usedMargin > 0 ? (totalEquity / usedMargin) * 100 : 0;
            
            // ============ UPDATE DOM ============
            // Update Equity display
            const equityElement = document.getElementById('equity');
            if (equityElement) {
                equityElement.textContent = '$' + totalEquity.toFixed(2);
                // Color equity based on P&L
                if (totalPnl > 0) {
                    equityElement.style.color = '#4caf50';
                } else if (totalPnl < 0) {
                    equityElement.style.color = '#f44336';
                } else {
                    equityElement.style.color = '#ffd700';
                }
            }
            
            // P&L
            const pnlElement = document.getElementById('pnl');
            if (pnlElement) {
                const formattedPnl = (totalPnl >= 0 ? '+' : '') + '$' + totalPnl.toFixed(2);
                pnlElement.textContent = formattedPnl;
                if (totalPnl > 0) {
                    pnlElement.className = 'account-value green';
                    pnlElement.style.color = '#4caf50';
                } else if (totalPnl < 0) {
                    pnlElement.className = 'account-value red';
                    pnlElement.style.color = '#f44336';
                } else {
                    pnlElement.className = 'account-value';
                    pnlElement.style.color = '#888';
                }
            }
            
            // Free Margin (Available = Equity - Used Margin)
            const freeMarginElement = document.getElementById('freeMargin');
            if (freeMarginElement) {
                freeMarginElement.textContent = '$' + freeMargin.toFixed(2);
                freeMarginElement.className = 'account-value cyan';
                freeMarginElement.style.color = '#00bcd4';
            }
            
            // Margin (Used)
            const marginElement = document.getElementById('margin');
            if (marginElement) {
                marginElement.textContent = '$' + usedMargin.toFixed(2);
                marginElement.className = 'account-value orange';
                marginElement.style.color = '#ff9800';
            }
            
            // Margin Level
            const marginLevelElement = document.getElementById('marginLevel');
            if (marginLevelElement) {
                if (usedMargin > 0) {
                    marginLevelElement.textContent = marginLevel.toFixed(2) + '%';
                    if (marginLevel >= 200) {
                        marginLevelElement.className = 'account-value green';
                        marginLevelElement.style.color = '#4caf50';
                    } else if (marginLevel >= 100) {
                        marginLevelElement.className = 'account-value orange';
                        marginLevelElement.style.color = '#ff9800';
                    } else {
                        marginLevelElement.className = 'account-value red';
                        marginLevelElement.style.color = '#f44336';
                    }
                } else {
                    marginLevelElement.textContent = '0.00%';
                    marginLevelElement.className = 'account-value purple';
                    marginLevelElement.style.color = '#9c27b0';
                }
            }

            // ============ DAILY P&L - READ ONLY ============
            const dailyPnlElement = document.getElementById('dailyPnl');
            if (dailyPnlElement) {
                let savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
                const savedDate = localStorage.getItem('dailyPnlDate');
                const today = new Date().toDateString();
                
                console.log('📅 Daily P&L - Reading from localStorage:', savedPnl, 'Date:', savedDate, 'Today:', today);
                
                if (savedDate !== today) {
                    console.log('📅 New day - resetting daily P&L');
                    savedPnl = 0;
                    localStorage.setItem('dailyPnlSaved', '0');
                    localStorage.setItem('dailyPnlDate', today);
                }
                
                dailyPnlTracker = savedPnl;
                
                const formatted = (savedPnl >= 0 ? '+' : '') + '$' + savedPnl.toFixed(2);
                dailyPnlElement.textContent = formatted;
                dailyPnlElement.className = 'account-value ' + (savedPnl > 0 ? 'green' : (savedPnl < 0 ? 'red' : ''));
                dailyPnlElement.style.color = savedPnl > 0 ? '#4caf50' : (savedPnl < 0 ? '#f44336' : '#888');
            }
            
            // Update card count display under balance
            if (data.card_count !== undefined) {
                document.getElementById('cardCountDisplay').textContent = data.card_count;
            }

            // Update prices with bid/ask
            updatePrices(data.prices);
            checkSLTP();  // <-- ADD THIS LINE

            // Update positions with latest prices
            updatePositionPrices();
            
            // Update signals
            if (data.signals) {
                updateSignals(data.signals);
            }
            
            // Update USD Direction
            if (data.dollar_status) {
                const usdDir = document.getElementById('usdDirection');
                const dir = data.dollar_status.usd_direction || 'NEUTRAL';
                const strength = data.dollar_status.usd_strength || 0;
                usdDir.textContent = `${dir} (${strength.toFixed(1)})`;
                if (dir === 'STRONG') {
                    usdDir.style.color = '#4caf50';
                } else if (dir === 'WEAK') {
                    usdDir.style.color = '#f44336';
                } else {
                    usdDir.style.color = '#ffd700';
                }
            }
            
            // ============ FIX 12: UPDATE CHART IMMEDIATELY ============
            // If chart page is active, update chart with latest data
            const chartsPage = document.getElementById('chartsPage');
            if (chartsPage && chartsPage.classList.contains('active')) {
                // Update chart data with the latest prices
                if (window.currentPrices && window.currentPrices[currentSymbol]) {
                    updateChartData();
                } else {
                    // If current symbol not in prices, refresh chart data
                    const symbolSelect = document.getElementById('chartSymbol');
                    if (symbolSelect) {
                        const allSymbols = Object.keys(data.prices || {});
                        if (allSymbols.length > 0) {
                            // Update dropdown with all symbols
                            const currentSelection = symbolSelect.value;
                            symbolSelect.innerHTML = '';
                            allSymbols.sort().forEach(sym => {
                                const option = document.createElement('option');
                                option.value = sym;
                                option.textContent = sym;
                                symbolSelect.appendChild(option);
                            });
                            if (allSymbols.includes(currentSelection)) {
                                symbolSelect.value = currentSelection;
                            } else {
                                symbolSelect.value = allSymbols[0];
                            }
                            currentSymbol = symbolSelect.value;
                            loadChartHistoryForSymbol(currentSymbol);
                            createColoredChart();
                        }
                    }
                }
                
                // Also update position indicators on chart if positions exist
                if (openPositions.length > 0 && priceChart) {
                    const lastPos = openPositions[openPositions.length - 1];
                    updatePositionIndicator(
                        lastPos.symbol,
                        lastPos.entryPrice,
                        lastPos.direction,
                        lastPos.sl,
                        lastPos.tp
                    );
                }
            }
            
            document.getElementById('refreshStatus').textContent = '✅ Updated ' + data.timestamp;
        } else {
            document.getElementById('refreshStatus').textContent = '❌ Error loading data';
        }
    } catch(e) {
        console.error('Error:', e);
        document.getElementById('refreshStatus').textContent = '❌ Connection error';
    }
}
// ============ FIXED: Initialize Daily P&L ============
function initializeDailyPnl() {
    try {
        const savedTracker = localStorage.getItem('dailyPnlSaved');
        const savedDate = localStorage.getItem('dailyPnlDate');
        const today = new Date().toDateString();
        
        console.log('📅 Initializing Daily P&L...');
        console.log('Saved tracker:', savedTracker);
        console.log('Saved date:', savedDate);
        console.log('Today:', today);
        
        if (savedTracker !== null && savedDate === today) {
            dailyPnlTracker = parseFloat(savedTracker);
            console.log('📅 Using saved daily P&L:', dailyPnlTracker);
        } else if (savedTracker !== null && savedDate !== today) {
            // New day - reset
            dailyPnlTracker = 0;
            lastResetDate = today;
            localStorage.setItem('dailyPnlSaved', '0');
            localStorage.setItem('dailyPnlDate', today);
            console.log('📅 New day - reset to 0');
        } else {
            // No saved data - initialize
            dailyPnlTracker = 0;
            lastResetDate = today;
            localStorage.setItem('dailyPnlSaved', '0');
            localStorage.setItem('dailyPnlDate', today);
            console.log('📅 No saved data - initialized to 0');
        }
        
        // Update the display immediately
        const dailyPnlElement = document.getElementById('dailyPnl');
        if (dailyPnlElement) {
            const formatted = (dailyPnlTracker >= 0 ? '+' : '') + '$' + dailyPnlTracker.toFixed(2);
            dailyPnlElement.textContent = formatted;
            if (dailyPnlTracker > 0) {
                dailyPnlElement.className = 'account-value green';
                dailyPnlElement.style.color = '#4caf50';
            } else if (dailyPnlTracker < 0) {
                dailyPnlElement.className = 'account-value red';
                dailyPnlElement.style.color = '#f44336';
            } else {
                dailyPnlElement.className = 'account-value';
                dailyPnlElement.style.color = '#888';
            }
        }
    } catch(e) {
        console.error('Error initializing daily P&L:', e);
    }
}
function updateSignals(signals) {
    window.lastSignalsData = signals;
    const signalsList = document.getElementById('signalsList');
    const signalCount = document.getElementById('signalCount');
    
    if (!signals || signals.length === 0) {
        signalsList.innerHTML = '<div class="no-signals">No active signals. Waiting for Z-Score thresholds...</div>';
        signalCount.textContent = '0';
        return;
    }
    
    // Show only recent valid signals (last 10)
    const recentSignals = signals.slice(-10).reverse();
    let validSignals = [];
    
    for (const signal of recentSignals) {
        if (signal.confidence >= 60) {
            // Create a consistent ID based on symbol + signal_type + created_at
            const signalId = signal.id || 
                signal.symbol + '_' + signal.signal_type + '_' + (signal.created_at || Date.now());
            
            // CRITICAL FIX: Convert to string for consistent comparison
            const signalIdStr = String(signalId);
            
            // Check if this signal has been skipped
            if (!skippedSignals.has(signalIdStr)) {
                // Add the signalId to the signal object for later use
                signal._signalId = signalIdStr;
                validSignals.push(signal);
            }
        }
    }
    
    signalCount.textContent = validSignals.length;
    
    if (validSignals.length === 0) {
        signalsList.innerHTML = '<div class="no-signals">No valid signals with confidence >= 60%</div>';
        return;
    }
    
    let html = '';
    for (const signal of validSignals) {
        const actionClass = signal.signal_type ? signal.signal_type.toLowerCase() : 'hold';
        const actionDisplay = signal.signal_type || 'HOLD';
        const confidence = signal.confidence || 0;
        const symbol = signal.symbol || 'Unknown';
        const time = signal.created_at ? new Date(signal.created_at).toLocaleTimeString() : '';
        const reasoning = signal.reasoning || '';
        const price = signal.price || '--';
        // Use the signalId from the signal object
        const signalId = signal._signalId || signal.id || signal.symbol + '_' + signal.signal_type + '_' + (signal.created_at || Date.now());
        
        // Determine button styling based on signal type
        let actionButtons = '';
        if (actionDisplay === 'BUY') {
            actionButtons = `
                <button class="signal-btn buy-btn-small" onclick="executeSignalTrade('${symbol}', 'BUY', ${confidence}, '${price}')">
                    📈 BUY
                </button>
                <button class="signal-btn skip-btn-small" onclick="skipSignal('${symbol}', 'BUY', '${signalId}')">
                    ⏭️ SKIP
                </button>
            `;
        } else if (actionDisplay === 'SELL') {
            actionButtons = `
                <button class="signal-btn sell-btn-small" onclick="executeSignalTrade('${symbol}', 'SELL', ${confidence}, '${price}')">
                    📉 SELL
                </button>
                <button class="signal-btn skip-btn-small" onclick="skipSignal('${symbol}', 'SELL', '${signalId}')">
                    ⏭️ SKIP
                </button>
            `;
        } else {
            actionButtons = `
                <button class="signal-btn hold-btn-small" disabled>
                    ⏸️ HOLD
                </button>
                <button class="signal-btn skip-btn-small" onclick="skipSignal('${symbol}', 'HOLD', '${signalId}')">
                    ⏭️ SKIP
                </button>
            `;
        }
        
        html += `
            <div class="signal-item" id="signal-${signalId}">
                <span class="symbol">${symbol}</span>
                <span class="action ${actionClass}">${actionDisplay}</span>
                <span class="confidence">${confidence}%</span>
                <span class="filters">${reasoning.substring(0, 50)}${reasoning.length > 50 ? '...' : ''}</span>
                <span class="time">${time}</span>
                <div class="signal-actions">
                    ${actionButtons}
                </div>
            </div>
        `;
    }
    
    signalsList.innerHTML = html;
}
function executeSignalTrade(symbol, direction, confidence, price) {
    // ============ CHECK BALANCE FIRST ============
    if (!checkSufficientBalance(symbol, 0.01)) {
        const balanceElement = document.getElementById('balance');
        const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
        
        showNotification('❌ Insufficient Balance', 
            `Balance: $${currentBalance.toFixed(2)} is not enough for this trade. Need minimum $${(checkSufficientBalance.calcMin || 0).toFixed(2)}`
        );
        
        // Flash the balance red to indicate error
        balanceElement.style.transition = 'color 0.3s';
        balanceElement.style.color = '#f44336';
        setTimeout(() => {
            balanceElement.style.color = '#ffd700';
        }, 2000);
        
        return;
    }
    
    // Get current price data
    const priceData = window.currentPrices ? window.currentPrices[symbol] : null;
    let currentPrice = 0;
    let bid = 0;
    let ask = 0;
    let spread = 0;
    
    if (priceData) {
        currentPrice = priceData.price || 0;
        bid = priceData.bid || currentPrice;
        ask = priceData.ask || currentPrice;
        spread = Math.abs(ask - bid);
    } else if (price && price !== '--' && !isNaN(parseFloat(price))) {
        currentPrice = parseFloat(price) || 0;
        const pipSize = symbol && symbol.includes('JPY') ? 0.01 : 0.0001;
        const spreadPips = 2.0;
        const spreadValue = spreadPips * pipSize;
        bid = currentPrice - spreadValue / 2;
        ask = currentPrice + spreadValue / 2;
        spread = spreadValue;
    } else {
        currentPrice = 0;
        bid = 0;
        ask = 0;
        spread = 0;
    }
    
    // Calculate SL and TP based on direction
    let sl = 0;
    let tp = 0;
    const pipSize = symbol && symbol.includes('JPY') ? 0.01 : 0.0001;
    const slPips = 20;
    const tpPips = 40;
    
    let entryPrice = 0;
    if (direction === 'BUY' && ask > 0) {
        entryPrice = ask;
        sl = entryPrice - (slPips * pipSize);
        tp = entryPrice + (tpPips * pipSize);
    } else if (direction === 'SELL' && bid > 0) {
        entryPrice = bid;
        sl = entryPrice + (slPips * pipSize);
        tp = entryPrice - (tpPips * pipSize);
    } else {
        entryPrice = currentPrice;
        if (direction === 'BUY') {
            sl = entryPrice - (slPips * pipSize);
            tp = entryPrice + (tpPips * pipSize);
        } else if (direction === 'SELL') {
            sl = entryPrice + (slPips * pipSize);
            tp = entryPrice - (tpPips * pipSize);
        }
    }
    
    // Store trade data
    currentTradeData = {
        symbol: symbol || 'Unknown',
        direction: direction || 'N/A',
        price: entryPrice,
        bid: bid,
        ask: ask,
        spread: spread,
        sl: sl,
        tp: tp,
        lotSize: 0.01,
        confidence: confidence || 0
    };
    
    // Show trade modal
    const modal = document.getElementById('tradeModal');
    const title = document.getElementById('tradeModalTitle');
    
    if (!modal) {
        alert('Trade modal not found!');
        return;
    }
    
    modal.classList.add('active');
    
    if (direction === 'BUY') {
        title.textContent = '📈 Buy Order - Confirm';
        title.style.color = '#4caf50';
    } else if (direction === 'SELL') {
        title.textContent = '📉 Sell Order - Confirm';
        title.style.color = '#f44336';
    } else {
        title.textContent = '📊 Trade Execution';
        title.style.color = '#ffd700';
    }
    
    // Fill in the details
    const tradeSymbol = document.getElementById('tradeSymbol');
    if (tradeSymbol) {
        tradeSymbol.textContent = symbol || '--';
        tradeSymbol.className = 'trade-detail-value';
    }
    
    const directionEl = document.getElementById('tradeDirection');
    if (directionEl) {
        directionEl.textContent = direction || '--';
        directionEl.className = 'trade-detail-value ' + (direction === 'BUY' ? 'buy-color' : (direction === 'SELL' ? 'sell-color' : ''));
    }
    
    const tradePrice = document.getElementById('tradePrice');
    if (tradePrice) {
        tradePrice.textContent = entryPrice > 0 ? entryPrice.toFixed(5) : '--';
        tradePrice.title = `Bid: ${bid.toFixed(5)} | Ask: ${ask.toFixed(5)} | Entry: ${entryPrice.toFixed(5)}`;
    }
    
    const tradeSpread = document.getElementById('tradeSpread');
    if (tradeSpread) {
        tradeSpread.textContent = spread > 0 ? (spread * 10000).toFixed(1) + ' pips' : '--';
        tradeSpread.className = 'trade-detail-value spread-value';
    }
    
    const tradeSL = document.getElementById('tradeSL');
    if (tradeSL) {
        tradeSL.textContent = sl > 0 ? sl.toFixed(5) : '--';
    }
    
    const tradeTP = document.getElementById('tradeTP');
    if (tradeTP) {
        tradeTP.textContent = tp > 0 ? tp.toFixed(5) : '--';
    }
    
    const tradeLotSize = document.getElementById('tradeLotSize');
    if (tradeLotSize) {
        tradeLotSize.textContent = '0.01';
    }
    
    const tradeConfidence = document.getElementById('tradeConfidence');
    if (tradeConfidence) {
        tradeConfidence.textContent = (confidence || 0) + '%';
    }
    
    tradeConfirmed = false;
}
function updatePositionPrices() {
    checkSLTP();
    if (openPositions.length === 0) {
        // No positions - show saved daily P&L from localStorage
        let savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
        const savedDate = localStorage.getItem('dailyPnlDate');
        const today = new Date().toDateString();
        
        // Reset if it's a new day
        if (savedDate !== today) {
            savedPnl = 0;
            localStorage.setItem('dailyPnlSaved', '0');
            localStorage.setItem('dailyPnlDate', today);
        }
        
        dailyPnlTracker = savedPnl;
        
        const dailyPnlElement = document.getElementById('dailyPnl');
        if (dailyPnlElement) {
            const formatted = (savedPnl >= 0 ? '+' : '') + '$' + savedPnl.toFixed(2);
            dailyPnlElement.textContent = formatted;
            dailyPnlElement.className = 'account-value ' + (savedPnl > 0 ? 'green' : (savedPnl < 0 ? 'red' : ''));
            dailyPnlElement.style.color = savedPnl > 0 ? '#4caf50' : (savedPnl < 0 ? '#f44336' : '#888');
        }
        
        const pnlElement = document.getElementById('pnl');
        if (pnlElement) {
            pnlElement.textContent = '+$0.00';
            pnlElement.className = 'account-value green';
            pnlElement.style.color = '#4caf50';
        }
        clearPositionIndicator();
        updatePositionsList();
        savePositions();
        return;
    }
    
    const priceData = window.currentPrices || {};
    let totalPnl = 0;
    let totalDailyPnl = 0;
    const today = new Date().toDateString();
    
    for (const pos of openPositions) {
        const symbolData = priceData[pos.symbol];
        if (symbolData) {
            const currentPrice = symbolData.price || 0;
            const currentBid = symbolData.bid || currentPrice;
            const currentAsk = symbolData.ask || currentPrice;
            
            pos.currentPrice = currentPrice;
            pos.currentBid = currentBid;
            pos.currentAsk = currentAsk;
            
            const pipSize = pos.symbol && pos.symbol.includes('JPY') ? 0.01 : 0.0001;
            
            // ============ FIX: Calculate P&L based on direction ============
            if (pos.direction === 'BUY') {
                // For BUY: We entered at ASK, profit when price goes up
                // Use bid price for closing a BUY position (you sell at bid)
                const closePrice = currentBid;
                const pipChange = (closePrice - pos.entryPrice) / pipSize;
                pos.pnl = pipChange * 0.10;
            } else {
                // For SELL: We entered at BID, profit when price goes down
                // Use ask price for closing a SELL position (you buy at ask)
                const closePrice = currentAsk;
                const pipChange = (pos.entryPrice - closePrice) / pipSize;
                pos.pnl = pipChange * 0.10;
            }
            
            // Calculate daily P&L correctly
            const posDate = new Date(pos.openTime).toDateString();
            if (posDate === today) {
                // Position opened today - daily P&L = total P&L
                pos.dailyPnl = pos.pnl;
            } else {
                // Position opened before today - calculate change from day start
                if (!pos.dayStartPrice) {
                    pos.dayStartPrice = pos.entryPrice;
                }
                // Use the same close price logic for daily P&L
                if (pos.direction === 'BUY') {
                    const closePrice = currentBid;
                    const dailyPipChange = (closePrice - pos.dayStartPrice) / pipSize;
                    pos.dailyPnl = dailyPipChange * 0.10;
                } else {
                    const closePrice = currentAsk;
                    const dailyPipChange = (pos.dayStartPrice - closePrice) / pipSize;
                    pos.dailyPnl = dailyPipChange * 0.10;
                }
            }
            
            totalPnl += pos.pnl;
            totalDailyPnl += pos.dailyPnl || 0;
        }
    }
    
    // Update tracker with closed positions + open positions daily P&L
    const savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
    const totalDaily = savedPnl + totalDailyPnl;
    dailyPnlTracker = totalDaily;
    
    // Update the daily P&L display
    const dailyPnlElement = document.getElementById('dailyPnl');
    if (dailyPnlElement) {
        const formatted = (totalDaily >= 0 ? '+' : '') + '$' + totalDaily.toFixed(2);
        dailyPnlElement.textContent = formatted;
        dailyPnlElement.className = 'account-value ' + (totalDaily > 0 ? 'green' : (totalDaily < 0 ? 'red' : ''));
        dailyPnlElement.style.color = totalDaily > 0 ? '#4caf50' : (totalDaily < 0 ? '#f44336' : '#888');
    }
    
    // Update P&L display
    const pnlElement = document.getElementById('pnl');
    if (pnlElement) {
        const formattedPnl = (totalPnl >= 0 ? '+' : '') + '$' + totalPnl.toFixed(2);
        pnlElement.textContent = formattedPnl;
        pnlElement.className = 'account-value ' + (totalPnl > 0 ? 'green' : (totalPnl < 0 ? 'red' : ''));
        pnlElement.style.color = totalPnl > 0 ? '#4caf50' : (totalPnl < 0 ? '#f44336' : '#888');
    }
    if (openPositions.length > 0) {
        // Get the most recent position (or update all)
        const lastPos = openPositions[openPositions.length - 1];
        updatePositionIndicator(
            lastPos.symbol,
            lastPos.entryPrice,
            lastPos.direction,
            lastPos.sl,
            lastPos.tp
        );
    }
    updatePositionsList();
    savePositions();
}

// ============ FIXED: Update Equity and Balance ============
function updateEquityBalance(totalPnl) {
    // Get current balance from the display
    const balanceElement = document.getElementById('balance');
    if (balanceElement) {
        // Parse the current balance (remove $ and commas)
        const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
        const newEquity = currentBalance + totalPnl;
        
        const equityElement = document.getElementById('equity');
        if (equityElement) {
            equityElement.textContent = '$' + newEquity.toFixed(2);
            if (totalPnl > 0) {
                equityElement.style.color = '#4caf50';
            } else if (totalPnl < 0) {
                equityElement.style.color = '#f44336';
            } else {
                equityElement.style.color = '#ffd700';
            }
        }
        
        // Update Free Margin (simplified)
        const freeMarginElement = document.getElementById('freeMargin');
        if (freeMarginElement) {
            freeMarginElement.textContent = '$' + newEquity.toFixed(2);
        }
        
        // Update Margin Level if there are positions
        const marginElement = document.getElementById('margin');
        const marginLevelElement = document.getElementById('marginLevel');
        if (marginElement && marginLevelElement) {
            const usedMargin = parseFloat(marginElement.textContent.replace(/[$,]/g, '')) || 0;
            if (usedMargin > 0) {
                const marginLevel = (newEquity / usedMargin) * 100;
                marginLevelElement.textContent = marginLevel.toFixed(2) + '%';
                if (marginLevel >= 200) {
                    marginLevelElement.className = 'account-value green';
                    marginLevelElement.style.color = '#4caf50';
                } else if (marginLevel >= 100) {
                    marginLevelElement.className = 'account-value orange';
                    marginLevelElement.style.color = '#ff9800';
                } else {
                    marginLevelElement.className = 'account-value red';
                    marginLevelElement.style.color = '#f44336';
                }
            }
        }
    }
}
function closePosition(positionId) {
    if (!confirm('Close this position?')) return;
    
    const index = openPositions.findIndex(p => p.id === positionId);
    if (index === -1) return;
    
    const position = openPositions[index];
    
    // Get the current price for the position
    const priceData = window.currentPrices || {};
    const symbolData = priceData[position.symbol];
    let currentPrice = position.currentPrice || position.entryPrice;
    let closePrice = 0;
    
    if (symbolData) {
        currentPrice = symbolData.price || 0;
        const currentBid = symbolData.bid || currentPrice;
        const currentAsk = symbolData.ask || currentPrice;
        
        // ============ FIX: Use correct close price based on direction ============
        if (position.direction === 'BUY') {
            // Closing a BUY position - you sell at BID
            closePrice = currentBid;
        } else {
            // Closing a SELL position - you buy at ASK
            closePrice = currentAsk;
        }
    } else {
        closePrice = position.currentPrice || position.entryPrice;
    }
    
    const pipSize = position.symbol && position.symbol.includes('JPY') ? 0.01 : 0.0001;
    let finalPnl = 0;
    
    // ============ FIX: Calculate final P&L based on direction ============
    if (position.direction === 'BUY') {
        const pipChange = (closePrice - position.entryPrice) / pipSize;
        finalPnl = pipChange * 0.10;
    } else {
        const pipChange = (position.entryPrice - closePrice) / pipSize;
        finalPnl = pipChange * 0.10;
    }
    
    // Calculate daily contribution
    const today = new Date().toDateString();
    const posDate = new Date(position.openTime).toDateString();
    
    let dailyContribution = 0;
    if (posDate === today) {
        dailyContribution = finalPnl;
    } else {
        if (!position.dayStartPrice) {
            position.dayStartPrice = position.entryPrice;
        }
        if (position.direction === 'BUY') {
            const dailyPipChange = (closePrice - position.dayStartPrice) / pipSize;
            dailyContribution = dailyPipChange * 0.10;
        } else {
            const dailyPipChange = (position.dayStartPrice - closePrice) / pipSize;
            dailyContribution = dailyPipChange * 0.10;
        }
    }
    
    console.log('📊 Closing position:', position.symbol);
    console.log('Entry price:', position.entryPrice);
    console.log('Close price:', closePrice);
    console.log('Direction:', position.direction);
    console.log('Final P&L:', finalPnl);
    console.log('Daily contribution:', dailyContribution);
    // ============ UPDATE TRADE IN DATABASE ============
    if (position.tradeId) {
        // Make sure finalPnl is a number
        const pnlValue = typeof finalPnl === 'number' ? finalPnl : parseFloat(finalPnl) || 0;
        updateTradeInDatabase(position.tradeId, closePrice, pnlValue, 'CLOSED');
    }
    // Add daily contribution to saved tracker
    let savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
    savedPnl += dailyContribution;
    
    localStorage.setItem('dailyPnlSaved', savedPnl.toString());
    localStorage.setItem('dailyPnlDate', new Date().toDateString());
    dailyPnlTracker = savedPnl;
    
    // Update display
    const dailyPnlElement = document.getElementById('dailyPnl');
    if (dailyPnlElement) {
        const formatted = (savedPnl >= 0 ? '+' : '') + '$' + savedPnl.toFixed(2);
        dailyPnlElement.textContent = formatted;
        dailyPnlElement.className = 'account-value ' + (savedPnl > 0 ? 'green' : (savedPnl < 0 ? 'red' : ''));
        dailyPnlElement.style.color = savedPnl > 0 ? '#4caf50' : (savedPnl < 0 ? '#f44336' : '#888');
    }
    
    // Remove position
    openPositions.splice(index, 1);
    clearPositionIndicator();
    updatePositionsList();
    
    // Update balance
    updateBalanceWithRealizedPnl(finalPnl).then(() => {
        savePositions();
        updatePositionPrices();
        setTimeout(() => {
            refreshData();
        }, 300);
    });
    
    showNotification('Position Closed', 
        `${position.direction} ${position.symbol} closed | P&L: ${finalPnl >= 0 ? '+' : ''}$${finalPnl.toFixed(2)}`
    );
}
// ============ CLEAR POSITION INDICATOR FROM CHART ============
function clearPositionIndicator() {
    const chartContainer = document.getElementById('priceChart');
    if (chartContainer) {
        const chartWrapper = chartContainer.parentElement;
        const oldIndicator = chartWrapper.querySelector('.position-indicator');
        if (oldIndicator) {
            oldIndicator.remove();
            console.log('🗑️ Position indicator removed from chart');
        }
    }
    
    // Also clear any stored position data on the chart
    if (priceChart) {
        priceChart._positionData = null;
    }
}
// Add this to your refreshData function after updating balance
function updateBalanceStatus() {
    const balanceElement = document.getElementById('balance');
    const statusElement = document.getElementById('balanceStatus');
    if (!balanceElement || !statusElement) return;
    
    const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
    const minRequired = 10; // Minimum $10 for 0.01 lot
    
    if (currentBalance < minRequired) {
        statusElement.innerHTML = '⚠️ Low Balance';
        statusElement.style.color = '#ff9800';
    } else if (currentBalance < minRequired * 2) {
        statusElement.innerHTML = '⚡ Limited';
        statusElement.style.color = '#ffc107';
    } else {
        statusElement.innerHTML = '✅ Sufficient';
        statusElement.style.color = '#4caf50';
    }
}
function updateTradeButtons() {
    const balanceElement = document.getElementById('balance');
    if (!balanceElement) return;
    
    const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
    const minRequired = 10; // Minimum $10
    
    const buyButtons = document.querySelectorAll('.buy-btn-small, .sell-btn-small');
    buyButtons.forEach(btn => {
        if (currentBalance < minRequired) {
            btn.disabled = true;
            btn.title = 'Insufficient balance';
            btn.style.opacity = '0.5';
        } else {
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    });
}
// ============ UPDATE BALANCE WITH REALIZED P&L ============
async function updateBalanceWithRealizedPnl(realizedPnl) {
    try {
        // Get current cards
        const response = await fetch('/api/cards', {
        });
        const data = await response.json();
        
        if (data.success && data.cards && data.cards.length > 0) {
            // Get the first active card and update its balance
            const card = data.cards[0];
            const currentBalance = card.balance || card.amount || 0;
            const newBalance = currentBalance + realizedPnl;
            
            console.log(`💰 Current balance: $${currentBalance.toFixed(2)}, P&L: ${realizedPnl >= 0 ? '+' : ''}$${realizedPnl.toFixed(2)}, New balance: $${newBalance.toFixed(2)}`);
            
            // Update the card balance in Supabase (user_cards)
            const updateResponse = await fetch('/api/update_card_balance', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    card_id: card.card_id,
                    card_pin: card.card_pin,
                    balance: newBalance
                })
            });
            
            const result = await updateResponse.json();
            if (result.success) {
                console.log(`✅ Balance updated successfully: $${newBalance.toFixed(2)}`);
                
                // ============ ALSO UPDATE THE MASTER TRADING_CARDS TABLE ============
                try {
                    const masterUpdateResponse = await fetch('/api/update_master_card_balance', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            card_id: card.card_id,
                            card_pin: card.card_pin,
                            balance: newBalance
                        })
                    });
                    const masterResult = await masterUpdateResponse.json();
                    if (masterResult.success) {
                        console.log(`✅ Master card balance also updated: $${newBalance.toFixed(2)}`);
                    } else {
                        console.warn('⚠️ Could not update master card balance:', masterResult.error);
                    }
                } catch (masterError) {
                    console.warn('⚠️ Error updating master card:', masterError);
                }
                
                // Update the balance display immediately
                document.getElementById('balance').textContent = '$' + newBalance.toFixed(2);
                return true;
            } else {
                console.error('❌ Failed to update balance:', result);
                return false;
            }
        }
        return false;
    } catch (e) {
        console.error('Error updating balance:', e);
        return false;
    }
}
// ============ UPDATE POSITIONS ON CHART ============
function updatePositionsOnChart() {
    if (openPositions.length > 0 && priceChart) {
        const lastPos = openPositions[openPositions.length - 1];
        updatePositionIndicator(
            lastPos.symbol,
            lastPos.entryPrice,
            lastPos.direction,
            lastPos.sl,
            lastPos.tp
        );
    } else {
        clearPositionIndicator();
    }
}
function confirmTrade() {
    // ============ SECOND BALANCE CHECK (prevent race condition) ============
    if (!checkSufficientBalance(currentTradeData.symbol, currentTradeData.lotSize || 0.01)) {
        const balanceElement = document.getElementById('balance');
        const currentBalance = parseFloat(balanceElement.textContent.replace(/[$,]/g, '')) || 0;
        
        showNotification('❌ Insufficient Balance', 
            `Balance: $${currentBalance.toFixed(2)} is not enough for this trade.`
        );
        
        closeTradeModal();
        return;
    }
    
    tradeConfirmed = true;
    const modal = document.getElementById('tradeModal');
    const body = document.querySelector('.trade-modal-body');
    const footer = document.querySelector('.trade-modal-footer');
    const header = document.querySelector('.trade-modal-header');
    
    const success = Math.random() > 0.1;
    
    const confirmBtn = footer.querySelector('.btn-confirm');
    const cancelBtn = footer.querySelector('.btn-cancel-modal');
    confirmBtn.disabled = true;
    confirmBtn.textContent = '⏳ Processing...';
    cancelBtn.disabled = true;
    
    setTimeout(() => {
        if (success) {
            const entryPrice = currentTradeData.price;
            
            const spreadPips = (currentTradeData.spread * 10000);
            const pipValue = 0.10;
            
            const initialPnl = -spreadPips * pipValue;
            const currentPrice = currentTradeData.bid + (currentTradeData.spread / 2);
            
            const position = {
                id: ++positionIdCounter,
                symbol: currentTradeData.symbol,
                direction: currentTradeData.direction,
                entryPrice: entryPrice,
                currentPrice: entryPrice,
                bid: currentTradeData.bid,
                ask: currentTradeData.ask,
                sl: currentTradeData.sl,
                tp: currentTradeData.tp,
                lotSize: currentTradeData.lotSize,
                spread: currentTradeData.spread,
                pnl: initialPnl,
                dailyPnl: initialPnl,
                dayStartPrice: entryPrice,
                confidence: currentTradeData.confidence,
                openTime: new Date().toLocaleTimeString()
            };
            saveTradeToDatabase(currentTradeData.symbol, currentTradeData.direction, entryPrice, 
                              currentTradeData.lotSize, currentTradeData.sl, currentTradeData.tp, 
                              currentTradeData.confidence, currentTradeData.spread);
            
            openPositions.push(position);
            
            updatePositionsList();
            
            switchToChartWithPosition(
                currentTradeData.symbol, 
                entryPrice, 
                currentTradeData.direction,
                currentTradeData.sl,
                currentTradeData.tp
            );
            
            const resultDiv = document.createElement('div');
            resultDiv.className = 'trade-result';
            const spreadDisplay = spreadPips.toFixed(1);
            resultDiv.innerHTML = `
                <div class="result-icon">✅</div>
                <div class="result-title success">Trade Executed!</div>
                <div class="result-details">
                    ${currentTradeData.direction} ${currentTradeData.lotSize} lots of ${currentTradeData.symbol}<br>
                    Entry: ${entryPrice.toFixed(5)}<br>
                    SL: ${currentTradeData.sl.toFixed(5)} | TP: ${currentTradeData.tp.toFixed(5)}<br>
                    Spread: ${spreadDisplay} pips<br>
                    <span style="color: #f44336;">Position starts at -$${Math.abs(initialPnl).toFixed(2)} (spread cost)</span>
                </div>
            `;
            body.innerHTML = '';
            body.appendChild(resultDiv);
            header.querySelector('h2').textContent = '✅ Order Placed - Viewing Chart';
            header.querySelector('h2').style.color = '#4caf50';
            footer.innerHTML = `
                <button class="btn-confirm" onclick="closeTradeModal()" style="flex:1;">Close</button>
            `;
            
            updatePositionPrices();
            
            showNotification('Trade Executed!', 
                `${currentTradeData.direction} ${currentTradeData.symbol} @ ${entryPrice.toFixed(5)} (Spread: ${spreadDisplay} pips)`
            );
            
        } else {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'trade-result';
            resultDiv.innerHTML = `
                <div class="result-icon">❌</div>
                <div class="result-title fail">Trade Failed</div>
                <div class="result-details">
                    Order could not be processed.<br>
                    Please try again.
                </div>
            `;
            body.innerHTML = '';
            body.appendChild(resultDiv);
            header.querySelector('h2').textContent = '❌ Order Failed';
            header.querySelector('h2').style.color = '#f44336';
            footer.innerHTML = `
                <button class="btn-confirm" onclick="closeTradeModal()" style="flex:1;">Close</button>
            `;
        }
        
        confirmBtn.disabled = false;
        cancelBtn.disabled = false;
        
    }, 1500);
}
// ============ SAVE TRADE TO DATABASE ============
async function saveTradeToDatabase(symbol, direction, entryPrice, lotSize, sl, tp, confidence, spread) {
    try {
        const response = await fetch('/api/save_trade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                direction: direction,
                entry_price: entryPrice,
                lot_size: lotSize || 0.01,
                sl: sl,
                tp: tp,
                confidence: confidence,
                spread: spread
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Trade saved to database:', result.trade);
            // Store the trade ID in the position for later updates
            if (openPositions.length > 0) {
                openPositions[openPositions.length - 1].tradeId = result.trade.id;
                savePositions();
            }
        } else {
            console.error('❌ Failed to save trade:', result.error);
        }
    } catch (e) {
        console.error('❌ Error saving trade:', e);
    }
}
// ============ UPDATE TRADE IN DATABASE WHEN CLOSED ============
async function updateTradeInDatabase(tradeId, closePrice, pnl, status) {
    try {
        // Make sure pnl is a number
        const pnlValue = typeof pnl === 'number' ? pnl : parseFloat(pnl) || 0;
        
        console.log(`📊 Updating trade ${tradeId}: pnl=${pnlValue}, status=${status}`);
        
        const response = await fetch('/api/update_trade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                trade_id: tradeId,
                close_price: closePrice,
                pnl: pnlValue,
                status: status || 'CLOSED'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Trade updated in database:', result.trade);
        } else {
            console.error('❌ Failed to update trade:', result.error);
        }
    } catch (e) {
        console.error('❌ Error updating trade:', e);
    }
}
function updatePositionsList() {
    const positionsList = document.getElementById('positionsList');
    if (!positionsList) return;
    
    if (openPositions.length === 0) {
        positionsList.innerHTML = '<div class="no-positions">No open positions. Execute a signal to start trading.</div>';
        clearPositionIndicator();
        return;
    }
    
    let html = '';
    let totalPnl = 0;
    
    for (const pos of openPositions) {
        const directionClass = pos.direction.toLowerCase();
        const pnlClass = pos.pnl >= 0 ? 'positive' : 'negative';
        const dailyPnlClass = (pos.dailyPnl || 0) >= 0 ? 'positive' : 'negative';
        totalPnl += pos.pnl;
        
        html += `
            <div class="position-item" id="pos-${pos.id}">
                <span class="pos-symbol">${pos.symbol}</span>
                <span class="pos-direction ${directionClass}">${pos.direction}</span>
                <span>Entry: ${pos.entryPrice.toFixed(5)}</span>
                <span>SL: ${pos.sl.toFixed(5)}</span>
                <span>TP: ${pos.tp.toFixed(5)}</span>
                <span class="pos-spread">Spread: ${(pos.spread * 10000).toFixed(1)} pips</span>
                <span class="pos-profit ${pnlClass}">P&L: ${pos.pnl >= 0 ? '+' : ''}$${pos.pnl.toFixed(2)}</span>
                <span class="pos-profit ${dailyPnlClass}" style="font-size: 11px;">Daily: ${(pos.dailyPnl || 0) >= 0 ? '+' : ''}$${(pos.dailyPnl || 0).toFixed(2)}</span>
                <span style="font-size: 11px; color: #666;">${pos.openTime}</span>
                <button class="pos-close-btn" onclick="closePosition(${pos.id})">✕ Close</button>
            </div>
        `;
    }
    
    const totalPnlClass = totalPnl >= 0 ? 'positive' : 'negative';
    html += `
        <div class="position-item" style="border-left-color: #ffd700; background: #1a2a4a;">
            <span style="color: #ffd700; font-weight: bold;">Total P&L:</span>
            <span class="pos-profit ${totalPnlClass}" style="font-size: 16px;">
                ${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}
            </span>
        </div>
    `;
    
    positionsList.innerHTML = html;
}
function updatePrices(prices) {
    const grid = document.getElementById('grid');
    grid.innerHTML = '';
    
    const symbols = Object.keys(prices).sort();
    let count = 0;
    let totalSpread = 0;
    let spreadCount = 0;
    
    for (const symbol of symbols) {
        const priceData = prices[symbol];
        if (!priceData || priceData.price <= 0) continue;
        
        count++;
        const card = document.createElement('div');
        const cardType = getCardType(symbol);
        const system = getSystem(symbol);
        
        card.className = `card card-${cardType}`;
        card.id = 'card-' + symbol;
        
        const price = priceData.price;
        const bid = priceData.bid || price;
        const ask = priceData.ask || price;
        const change = priceData.change || 0;
        
        // Calculate spread
        const spread = ask - bid;
        if (spread > 0 && spread < 1) {
            totalSpread += spread;
            spreadCount++;
        }
        
        // Check if price changed
        let priceClass = '';
        if (previousPrices[symbol] !== undefined) {
            const prevPrice = previousPrices[symbol];
            if (price > prevPrice) {
                priceClass = 'up';
                card.classList.add('update');
            } else if (price < prevPrice) {
                priceClass = 'down';
                card.classList.add('update');
            }
        }
        
        const decimals = getDecimals(symbol);
        const displayPrice = price.toFixed(decimals);
        const displayBid = bid.toFixed(decimals);
        const displayAsk = ask.toFixed(decimals);
        const displaySpread = spread.toFixed(decimals);
        
        // Change display
        const changeSymbol = change > 0 ? '▲' : (change < 0 ? '▼' : '');
        const changeClass = change > 0 ? 'up' : (change < 0 ? 'down' : '');
        const changeDisplay = Math.abs(change).toFixed(2);
        
        const displayName = getDisplayName(symbol);
        const systemLabel = system.toUpperCase();
        const systemColor = system === 'zscore' ? '#2196F3' : '#FF9800';
        
        const hasSpread = Math.abs(bid - ask) > 0.00001;
        
        card.innerHTML = `
            <div class="card-symbol">
                <span>${displayName}</span>
                <span class="system-tag ${system}" style="background:${systemColor};">${systemLabel}</span>
            </div>
            <div class="card-price ${priceClass}">${displayPrice}</div>
            <div class="card-change ${changeClass}">
                ${changeSymbol} ${changeDisplay}%
                ${hasSpread ? `<span style="color:#888;font-size:11px;margin-left:10px;">Spread: ${displaySpread}</span>` : ''}
            </div>
            <div class="card-bidask">
                <span class="label">Bid:</span> <span class="bid">${displayBid}</span> | 
                <span class="label">Ask:</span> <span class="ask">${displayAsk}</span>
            </div>
        `;
        
        grid.appendChild(card);
        previousPrices[symbol] = price;
    }
    
    document.getElementById('symbolCount').textContent = count;
    document.getElementById('symbolCount2').textContent = count;
    
    if (spreadCount > 0) {
        const avgSpread = (totalSpread / spreadCount);
        document.getElementById('spreadInfo').textContent = `${(avgSpread * 10000).toFixed(1)} pips`;
    }
}
// ============ FIXED: SWITCH TO CHART WITH POSITION ============
function switchToChartWithPosition(symbol, entryPrice, direction, sl, tp) {
    // Switch to charts tab WITH preventRefresh = true
    switchTab('charts', true); // preventRefresh = true
    
    // Set the symbol in the chart dropdown
    const symbolSelect = document.getElementById('chartSymbol');
    if (symbolSelect) {
        // Check if the symbol exists in the dropdown
        let symbolExists = false;
        for (let i = 0; i < symbolSelect.options.length; i++) {
            if (symbolSelect.options[i].value === symbol) {
                symbolExists = true;
                break;
            }
        }
        
        // If symbol exists, select it
        if (symbolExists) {
            symbolSelect.value = symbol;
            // Trigger chart switch
            if (typeof switchChart === 'function') {
                switchChart();
            }
        } else {
            // Add the symbol if it doesn't exist
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            symbolSelect.appendChild(option);
            symbolSelect.value = symbol;
            if (typeof switchChart === 'function') {
                switchChart();
            }
        }
    }
    
    // Add entry/exit markers to the chart after it loads
    setTimeout(() => {
        addPositionMarkersToChart(symbol, entryPrice, direction, sl, tp);
    }, 500);
}
// ============ CHECK SL/TP AUTOMATIC CLOSE ============
function checkSLTP() {
    if (openPositions.length === 0) return;
    
    const priceData = window.currentPrices || {};
    let positionsToClose = [];
    let closedPositions = [];
    
    for (let i = 0; i < openPositions.length; i++) {
        const pos = openPositions[i];
        const symbolData = priceData[pos.symbol];
        
        if (!symbolData || !symbolData.price) continue;
        
        const currentBid = symbolData.bid || symbolData.price;
        const currentAsk = symbolData.ask || symbolData.price;
        let shouldClose = false;
        let closeReason = '';
        let closePrice = 0;
        
        // Check SL and TP based on direction
        if (pos.direction === 'BUY') {
            // For BUY: SL is below entry, TP is above entry
            // Price hits SL when current bid <= SL
            if (currentBid <= pos.sl) {
                shouldClose = true;
                closeReason = 'SL';
                closePrice = pos.sl;
                console.log(`🔴 ${pos.symbol} BUY hit SL at ${pos.sl}`);
            }
            // Price hits TP when current ask >= TP
            else if (currentAsk >= pos.tp) {
                shouldClose = true;
                closeReason = 'TP';
                closePrice = pos.tp;
                console.log(`🟢 ${pos.symbol} BUY hit TP at ${pos.tp}`);
            }
        } else if (pos.direction === 'SELL') {
            // For SELL: SL is above entry, TP is below entry
            // Price hits SL when current ask >= SL
            if (currentAsk >= pos.sl) {
                shouldClose = true;
                closeReason = 'SL';
                closePrice = pos.sl;
                console.log(`🔴 ${pos.symbol} SELL hit SL at ${pos.sl}`);
            }
            // Price hits TP when current bid <= TP
            else if (currentBid <= pos.tp) {
                shouldClose = true;
                closeReason = 'TP';
                closePrice = pos.tp;
                console.log(`🟢 ${pos.symbol} SELL hit TP at ${pos.tp}`);
            }
        }
        
        if (shouldClose) {
            positionsToClose.push({
                index: i,
                position: pos,
                reason: closeReason,
                closePrice: closePrice
            });
        }
    }
    
    // Close positions in reverse order to avoid index issues
    for (let j = positionsToClose.length - 1; j >= 0; j--) {
        const { index, position, reason, closePrice } = positionsToClose[j];
        
        // Calculate final P&L
        const pipSize = position.symbol && position.symbol.includes('JPY') ? 0.01 : 0.0001;
        let finalPnl = 0;
        
        if (position.direction === 'BUY') {
            const pipChange = (closePrice - position.entryPrice) / pipSize;
            finalPnl = pipChange * 0.10;
        } else {
            const pipChange = (position.entryPrice - closePrice) / pipSize;
            finalPnl = pipChange * 0.10;
        }
        if (position.tradeId) {
            const pnlValue = typeof finalPnl === 'number' ? finalPnl : parseFloat(finalPnl) || 0;
            updateTradeInDatabase(position.tradeId, closePrice, pnlValue, reason);
        }
        // Calculate daily contribution
        const today = new Date().toDateString();
        const posDate = new Date(position.openTime).toDateString();
        
        let dailyContribution = 0;
        if (posDate === today) {
            dailyContribution = finalPnl;
        } else {
            if (!position.dayStartPrice) {
                position.dayStartPrice = position.entryPrice;
            }
            if (position.direction === 'BUY') {
                const dailyPipChange = (closePrice - position.dayStartPrice) / pipSize;
                dailyContribution = dailyPipChange * 0.10;
            } else {
                const dailyPipChange = (position.dayStartPrice - closePrice) / pipSize;
                dailyContribution = dailyPipChange * 0.10;
            }
        }
        
        // Update daily P&L
        let savedPnl = parseFloat(localStorage.getItem('dailyPnlSaved')) || 0;
        savedPnl += dailyContribution;
        localStorage.setItem('dailyPnlSaved', savedPnl.toString());
        localStorage.setItem('dailyPnlDate', new Date().toDateString());
        dailyPnlTracker = savedPnl;
        
        // Update balance with realized P&L
        updateBalanceWithRealizedPnl(finalPnl);
        
        // Store for notification
        closedPositions.push({
            symbol: position.symbol,
            direction: position.direction,
            reason: reason,
            pnl: finalPnl,
            entryPrice: position.entryPrice,
            closePrice: closePrice
        });
        
        // Remove position
        openPositions.splice(index, 1);
    }
    
    // Update UI if positions were closed
    if (closedPositions.length > 0) {
        // Update positions list
        updatePositionsList();
        updatePositionPrices();
        clearPositionIndicator();
        savePositions();
        
        // Show notification for each closed position
        for (const closed of closedPositions) {
            const emoji = closed.reason === 'TP' ? '🎯' : '🔴';
            const color = closed.reason === 'TP' ? '#4caf50' : '#f44336';
            const pnlText = closed.pnl >= 0 ? '+' : '';
            
            showNotification(
                `${emoji} ${closed.reason} Hit!`, 
                `${closed.direction} ${closed.symbol} closed at ${closed.closePrice.toFixed(5)} | P&L: ${pnlText}$${closed.pnl.toFixed(2)}`
            );
        }
        
        // Refresh data
        setTimeout(() => refreshData(), 300);
    }
}
// ============ ADD POSITION MARKERS ON CHART ============
function addPositionMarkersToChart(symbol, entryPrice, direction, sl, tp) {
    if (!priceChart) return;
    
    // Get the chart data
    const history = chartHistory[symbol] || [];
    if (history.length === 0) return;
    
    // Find the closest data point to the entry price
    let entryIndex = history.length - 1;
    let minDiff = Infinity;
    
    for (let i = 0; i < history.length; i++) {
        const diff = Math.abs(history[i].close - entryPrice);
        if (diff < minDiff) {
            minDiff = diff;
            entryIndex = i;
        }
    }
    
    // Store position data on the chart for reference
    priceChart._positionData = {
        symbol: symbol,
        entryPrice: entryPrice,
        direction: direction,
        sl: sl,
        tp: tp,
        entryIndex: history.length - 1
    };
    updatePositionIndicator(symbol, entryPrice, direction, sl, tp);
    // Add annotation using chart.js plugin or custom drawing
    // For simplicity, we'll log it and update the chart title
    const chartContainer = document.getElementById('priceChart');
    if (chartContainer) {
        // Add a tooltip or indicator on the chart
        const chartWrapper = chartContainer.parentElement;
        // Remove old position indicator if exists
        const oldIndicator = chartWrapper.querySelector('.position-indicator');
        if (oldIndicator) oldIndicator.remove();
        
        // Add position indicator
        const indicator = document.createElement('div');
        indicator.className = 'position-indicator';
        const directionColor = direction === 'BUY' ? '#4caf50' : '#f44336';
        indicator.innerHTML = `
            <div style="position: absolute; top: 10px; left: 50%; transform: translateX(-50%); 
                        background: rgba(10, 14, 39, 0.9); padding: 8px 16px; border-radius: 8px; 
                        border: 1px solid ${directionColor}; color: #fff; font-size: 12px; z-index: 100;">
                <span style="color: ${directionColor}; font-weight: bold;">${direction}</span> 
                ${symbol} @ ${entryPrice.toFixed(5)} 
                | SL: ${sl.toFixed(5)} | TP: ${tp.toFixed(5)}
            </div>
        `;
        indicator.style.position = 'relative';
        chartWrapper.style.position = 'relative';
        chartWrapper.appendChild(indicator);
    }
    
    // Force chart update to show the position
    if (priceChart) {
        priceChart.update();
    }
}
// ============ UPDATE POSITION INDICATOR WITH CURRENT PRICE ============
function updatePositionIndicator(symbol, entryPrice, direction, sl, tp) {
    const chartContainer = document.getElementById('priceChart');
    if (!chartContainer) return;
    
    const chartWrapper = chartContainer.parentElement;
    
    // Remove old indicator if exists
    const oldIndicator = chartWrapper.querySelector('.position-indicator');
    if (oldIndicator) oldIndicator.remove();
    
    // Get current price
    const priceData = window.currentPrices ? window.currentPrices[symbol] : null;
    let currentPrice = entryPrice;
    let currentBid = 0;
    let currentAsk = 0;
    let pnl = 0;
    let pnlColor = '#888';
    let pnlPrefix = '';
    
    if (priceData && priceData.price) {
        currentPrice = priceData.price;
        currentBid = priceData.bid || currentPrice;
        currentAsk = priceData.ask || currentPrice;
        
        // Calculate current P&L
        const pipSize = symbol && symbol.includes('JPY') ? 0.01 : 0.0001;
        let closePrice = 0;
        
        if (direction === 'BUY') {
            closePrice = currentBid;
            const pipChange = (closePrice - entryPrice) / pipSize;
            pnl = pipChange * 0.10;
        } else {
            closePrice = currentAsk;
            const pipChange = (entryPrice - closePrice) / pipSize;
            pnl = pipChange * 0.10;
        }
        
        pnlColor = pnl >= 0 ? '#4caf50' : '#f44336';
        pnlPrefix = pnl >= 0 ? '+' : '';
    }
    
    const directionColor = direction === 'BUY' ? '#4caf50' : '#f44336';
    const directionEmoji = direction === 'BUY' ? '📈' : '📉';
    
    // Create indicator with current price and P&L
    const indicator = document.createElement('div');
    indicator.className = 'position-indicator';
    indicator.innerHTML = `
        <div style="position: absolute; top: 10px; left: 50%; transform: translateX(-50%); 
                    background: rgba(10, 14, 39, 0.95); padding: 10px 20px; border-radius: 8px; 
                    border: 1px solid ${directionColor}; color: #fff; font-size: 12px; z-index: 100;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.6); min-width: 300px; text-align: center;">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 15px; flex-wrap: wrap;">
                <span>
                    <span style="color: ${directionColor}; font-weight: bold;">${directionEmoji} ${direction}</span>
                    <span style="color: #ffd700; font-weight: bold;">${symbol}</span>
                </span>
                <span style="color: #888; font-size: 11px;">
                    Entry: <span style="color: #ffd700;">${entryPrice.toFixed(5)}</span>
                </span>
                <span style="color: #888; font-size: 11px;">
                    Current: <span style="color: #00bcd4;">${currentPrice.toFixed(5)}</span>
                </span>
                <span style="color: #888; font-size: 11px;">
                    P&L: <span style="color: ${pnlColor}; font-weight: bold;">${pnlPrefix}$${pnl.toFixed(2)}</span>
                </span>
                <span style="color: #888; font-size: 10px;">
                    SL: <span style="color: #f44336;">${sl.toFixed(5)}</span>
                    TP: <span style="color: #4caf50;">${tp.toFixed(5)}</span>
                </span>
            </div>
        </div>
    `;
    indicator.style.position = 'relative';
    chartWrapper.style.position = 'relative';
    chartWrapper.appendChild(indicator);
}
function closeTradeModal() {
    const modal = document.getElementById('tradeModal');
    const body = document.querySelector('.trade-modal-body');
    const footer = document.querySelector('.trade-modal-footer');
    const header = document.querySelector('.trade-modal-header');
    
    // Reset modal to original state
    setTimeout(() => {
        body.innerHTML = `
            <div class="trade-details-grid">
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Symbol</span>
                    <span class="trade-detail-value" id="tradeSymbol">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Direction</span>
                    <span class="trade-detail-value" id="tradeDirection">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Entry Price</span>
                    <span class="trade-detail-value" id="tradePrice">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Spread</span>
                    <span class="trade-detail-value" id="tradeSpread">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Stop Loss (SL)</span>
                    <span class="trade-detail-value" id="tradeSL">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Take Profit (TP)</span>
                    <span class="trade-detail-value" id="tradeTP">--</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Lot Size</span>
                    <span class="trade-detail-value" id="tradeLotSize">0.01</span>
                </div>
                <div class="trade-detail-item">
                    <span class="trade-detail-label">Confidence</span>
                    <span class="trade-detail-value" id="tradeConfidence">--</span>
                </div>
            </div>
        `;
        footer.innerHTML = `
            <button class="btn-cancel-modal" onclick="closeTradeModal()">Cancel</button>
            <button class="btn-confirm" onclick="confirmTrade()">Confirm Trade</button>
        `;
        header.querySelector('h2').textContent = '📊 Trade Execution';
        header.querySelector('h2').style.color = '#ffd700';
        
        modal.classList.remove('active');
    }, 300);
}
function startCountdown() {
    countdown = 2;
    document.getElementById('countdown').textContent = countdown;
    
    const timer = setInterval(() => {
        countdown--;
        document.getElementById('countdown').textContent = countdown;
        if (countdown <= 0) {
            clearInterval(timer);
            refreshData();
            startCountdown();
        }
    }, 1000);
}

// Initial load
refreshData();
startCountdown();

// Refresh stats every 10 seconds
setInterval(() => {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            // Update any additional stats
        })
        .catch(e => console.error('Status error:', e));
}, 10000);
</script>
</body>
</html>
"""

def create_trade_history_table():
    """Create trade_history table if it doesn't exist"""
    try:
        # Check if table exists
        response = supabase.table('trade_history').select('id').limit(1).execute()
        print("✅ trade_history table already exists")
        return True
    except Exception as e:
        if 'PGRST205' in str(e) or 'does not exist' in str(e):
            print("📝 Creating trade_history table...")
            try:
                # Create table using raw SQL (if your Supabase client supports it)
                # You may need to use a different method if this doesn't work
                from supabase import create_client
                # Alternative: Use the REST API directly
                import requests
                
                url = f"{SUPABASE_URL}/rest/v1/rpc/create_trade_history_table"
                headers = {
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json"
                }
                
                # This requires you to create a function in Supabase first
                # Or use the SQL Editor method above
                print("❌ Please create the table manually in Supabase SQL Editor")
                print("SQL: CREATE TABLE trade_history (...)")
                return False
            except Exception as e2:
                print(f"❌ Error creating table: {e2}")
                return False
        else:
            print(f"❌ Error checking table: {e}")
            return False
# ============ ROUTES ============
@app.before_request
def set_user_context():
    """Set the current user_id for RLS policies"""
    try:
        user_id = get_user_id()
        if user_id:
            # Set the user_id in the session for RLS
            supabase.postgrest.headers['X-Client-Info'] = f'app.current_user_id={user_id}'
            skip_supabase.postgrest.headers['X-Client-Info'] = f'app.current_user_id={user_id}'
    except Exception as e:
        print(f"⚠️ Error setting user context: {e}")
@app.route('/')
def index():
    # Check if user is logged in
    user_id = get_user_id()
    if not user_id:
        # Redirect to login page if not logged in
        return redirect('http://localhost:5005/login')
    return render_template_string(HTML)
@app.route('/api/save_trade', methods=['POST'])
def save_trade():
    """Save executed trade to database - DIRECT INSERT (no stored procedure)"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        # Required fields
        symbol = data.get('symbol')
        direction = data.get('direction')
        entry_price = data.get('entry_price')
        lot_size = data.get('lot_size', 0.01)
        sl = data.get('sl')
        tp = data.get('tp')
        confidence = data.get('confidence')
        spread = data.get('spread')
        
        if not symbol or not direction or not entry_price:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        print(f"📊 Saving trade: {symbol} {direction} @ {entry_price} for user {user_id}")
        
        # ============ DIRECT INSERT (bypass stored procedure) ============
        response = skip_supabase.table('trade_history')\
            .insert({
                'user_id': user_id,
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'lot_size': lot_size,
                'sl': sl,
                'tp': tp,
                'confidence': confidence,
                'spread': spread,
                'open_time': datetime.now().isoformat(),
                'status': 'OPEN',
                'pnl': None,
                'close_price': None,
                'close_time': None
            })\
            .execute()
        
        if response.data:
            print(f"✅ Trade saved to database: {response.data[0]}")
            return jsonify({
                'success': True, 
                'trade': response.data[0],
                'message': f'{direction} trade saved for {symbol}'
            })
        else:
            print("❌ No data returned from insert")
            return jsonify({'success': False, 'error': 'Failed to save trade - no data returned'}), 500
            
    except Exception as e:
        print(f"⚠️ Error saving trade: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_trade', methods=['POST'])
def update_trade():
    """Update trade status - DIRECT UPDATE (no stored procedure)"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        trade_id = data.get('trade_id')
        close_price = data.get('close_price')
        pnl = data.get('pnl')
        status = data.get('status', 'CLOSED')
        
        if not trade_id:
            return jsonify({'success': False, 'error': 'Trade ID required'}), 400
        
        print(f"📊 Updating trade {trade_id}: pnl={pnl}, status={status}")
        
        # ============ DIRECT UPDATE ============
        response = skip_supabase.table('trade_history')\
            .update({
                'close_price': close_price,
                'pnl': pnl,
                'status': status,
                'close_time': datetime.now().isoformat()
            })\
            .eq('id', trade_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if response.data:
            print(f"✅ Trade updated in database: {response.data[0]}")
            return jsonify({
                'success': True,
                'trade': response.data[0],
                'message': f'Trade {trade_id} updated to {status}'
            })
        else:
            return jsonify({'success': False, 'error': 'Trade not found or unauthorized'}), 404
            
    except Exception as e:
        print(f"⚠️ Error updating trade: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/trade_history', methods=['GET'])
def get_trade_history():
    """Get trade history for the logged-in user"""
    try:
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        print(f"🔍 Fetching trade history for user_id: {user_id}")
        
        # First, check if there are ANY trades in the table
        all_trades = skip_supabase.table('trade_history')\
            .select('*')\
            .limit(5)\
            .execute()
        
        print(f"🔍 Total trades in table: {len(all_trades.data) if all_trades.data else 0}")
        if all_trades.data:
            print(f"🔍 Sample user_ids: {[t.get('user_id') for t in all_trades.data[:3]]}")
        
        # Now get trades for this user
        response = skip_supabase.table('trade_history')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('open_time', desc=True)\
            .execute()
        
        trade_count = len(response.data) if response.data else 0
        print(f"✅ Found {trade_count} trades for user {user_id}")
        
        if trade_count > 0:
            print(f"✅ First trade: {response.data[0]}")
        
        return jsonify({
            'success': True,
            'trades': response.data if response.data else [],
            'debug': {
                'user_id': user_id,
                'total_trades_found': trade_count,
                'all_trades_count': len(all_trades.data) if all_trades.data else 0
            }
        })
    except Exception as e:
        print(f"⚠️ Error getting trade history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/update_master_card_balance', methods=['POST'])
def update_master_card_balance():
    """Update master trading_cards balance"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        card_id = data.get('card_id')
        card_pin = data.get('card_pin')
        new_balance = data.get('balance')
        
        if not card_id or not card_pin or new_balance is None:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Update the master trading_cards table
        response = supabase.table('trading_cards')\
            .update({
                'balance': new_balance,
                'updated_at': datetime.now().isoformat()
            })\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'card': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Master card not found'}), 404
            
    except Exception as e:
        print(f"⚠️ Error updating master card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/open_trades', methods=['GET'])
def get_open_trades():
    """Get open trades for the logged-in user"""
    try:
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        # ============ USE SKIP SUPABASE FOR TRADE HISTORY ============
        response = skip_supabase.table('trade_history')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'OPEN')\
            .order('open_time', desc=True)\
            .execute()
        
        return jsonify({
            'success': True,
            'trades': response.data if response.data else []
        })
    except Exception as e:
        print(f"⚠️ Error getting open trades: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/prices')
def get_prices_api():
    data = fetch_from_dashboard()
    
    # Get user_id from cookies
    user_id = get_user_id()
    
    # Get total balance from user_cards for the logged-in user
    try:
        if user_id:
            # Get all user cards
            user_cards_response = supabase.table('user_cards')\
                .select('balance, amount')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .execute()
            
            total_balance = 0
            if user_cards_response.data:
                for card in user_cards_response.data:
                    balance = card.get('balance') or card.get('amount') or 0
                    total_balance += float(balance)
            
            # Update the balance in the response
            data['balance'] = total_balance
            data['equity'] = total_balance
            data['card_balance'] = total_balance
            data['card_count'] = len(user_cards_response.data) if user_cards_response.data else 0
        else:
            data['balance'] = 0
            data['equity'] = 0
            data['card_balance'] = 0
            data['card_count'] = 0
        
    except Exception as e:
        print(f"⚠️ Error getting user cards balance: {e}")
        data['balance'] = 0
        data['card_count'] = 0
    
    return jsonify(data)
# ============ CARD MANAGEMENT ROUTES ============
@app.route('/api/check_card', methods=['POST'])
def check_card():
    """Check if card exists in database"""
    try:
        data = request.json
        card_id = data.get('card_id')
        card_pin = data.get('card_pin')
        username = data.get('username')
        
        if not card_id or not card_pin:
            return jsonify({
                'success': False, 
                'error': 'Card ID and PIN are required'
            }), 400
        
        # Check if card exists with matching ID and PIN (any card in the system)
        response = supabase.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .execute()
        
        if response.data and len(response.data) > 0:
            card = response.data[0]
            
            # Check if username matches (if provided)
            if username:
                username_db = card.get('username', '')
                if username_db and username_db.upper() != username.upper():
                    return jsonify({
                        'success': False,
                        'exists': True,
                        'error': 'Username does not match',
                        'card': card
                    })
            
            return jsonify({
                'success': True,
                'exists': True,
                'card': card,
                'message': 'Card found in database'
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'message': 'Card not found in database'
            })
            
    except Exception as e:
        print(f"⚠️ Error checking card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/add_card_to_user', methods=['POST'])
def add_card_to_user():
    """Add an existing card to user's dashboard - only if active"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        card_id = data.get('card_id')
        card_pin = data.get('card_pin')
        username = data.get('username')
        
        if not card_id or not card_pin:
            return jsonify({'success': False, 'error': 'Card ID and PIN are required'}), 400
        
        # Check if card exists in trading_cards table
        card_response = supabase.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .execute()
        
        if not card_response.data or len(card_response.data) == 0:
            return jsonify({'success': False, 'error': 'Card not found in system'}), 404
        
        original_card = card_response.data[0]
        
        # ============ CHECK IF CARD IS ACTIVE ============
        if not original_card.get('is_active', False):
            return jsonify({
                'success': False, 
                'error': 'This card is inactive and cannot be added. Please contact support.'
            }), 400
        
        # Check if user already added this card
        existing = supabase.table('user_cards')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('card_id', card_id)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            return jsonify({'success': False, 'error': 'Card already added to your dashboard'}), 400
        
        # Add to user_cards (main database)
        response = supabase.table('user_cards')\
            .insert({
                'user_id': user_id,
                'card_id': card_id,
                'card_pin': card_pin,
                'username': username,
                'balance': original_card.get('balance', 0),
                'amount': original_card.get('amount', 0),
                'is_active': original_card.get('is_active', True),  # Use the same active status
                'added_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'card': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to add card'}), 500
        
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/cards', methods=['GET'])
def get_cards():
    """Get cards for the logged-in user"""
    try:
        user_id = get_user_id()
        
        # If no user logged in, return empty
        if not user_id:
            return jsonify({
                'success': True,
                'cards': []
            })
        
        response = supabase.table('user_cards')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('added_at', desc=True)\
            .execute()
        
        return jsonify({
            'success': True,
            'cards': response.data if response.data else []
        })
    except Exception as e:
        print(f"⚠️ Error getting cards: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/add_card', methods=['POST'])
def add_card():
    """Add existing card to user's account"""
    try:
        data = request.json
        
        # Check if card already exists
        check_response = supabase.table('trading_cards')\
            .select('*')\
            .eq('card_id', data['card_id'])\
            .execute()
        
        if check_response.data and len(check_response.data) > 0:
            return jsonify({'success': False, 'error': 'Card already exists'}), 400
        
        # Insert new card
        response = supabase.table('trading_cards')\
            .insert({
                'card_id': data['card_id'],
                'card_pin': data['card_pin'],
                'username': data.get('username'),
                'amount': data.get('amount', 0),
                'balance': data.get('balance', data.get('amount', 0)),
                'is_active': data.get('is_active', True)
            })\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'card': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to add card'}), 500
        
    except Exception as e:
        print(f"⚠️ Error adding card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/update_card_balance', methods=['POST'])
def update_card_balance():
    """Update card balance for user's card"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        card_id = data.get('card_id')
        card_pin = data.get('card_pin')
        new_balance = data.get('balance')
        
        if not card_id or not card_pin or new_balance is None:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Update only if it belongs to this user
        response = supabase.table('user_cards')\
            .update({
                'balance': new_balance,
                'updated_at': datetime.now().isoformat()
            })\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .eq('user_id', user_id)\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'card': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Card not found'}), 404
            
    except Exception as e:
        print(f"⚠️ Error updating card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/delete_card', methods=['POST'])
def delete_card():
    """Delete a card from user's dashboard"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        card_id = data.get('card_id')
        
        if not card_id:
            return jsonify({'success': False, 'error': 'Card ID required'}), 400
        
        # Delete only if it belongs to this user
        response = supabase.table('user_cards')\
            .delete()\
            .eq('card_id', card_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'card': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Card not found'}), 404
            
    except Exception as e:
        print(f"⚠️ Error deleting card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/card_balance')
def get_card_balance_api():
    """Get total card balance from user_cards"""
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Get all user cards
        response = supabase.table('user_cards')\
            .select('balance, amount')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        total_balance = 0
        card_count = 0
        
        if response.data:
            card_count = len(response.data)
            for card in response.data:
                balance = card.get('balance') or card.get('amount') or 0
                total_balance += float(balance)
        
        return jsonify({
            'success': True,
            'balance': total_balance,
            'card_count': card_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"⚠️ Error getting card balance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/signals')
def get_signals_api():
    """Get signals from advanced_trading_strategy.py"""
    signals = fetch_signals_from_file()
    return jsonify({'success': True, 'signals': signals})
@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle logout - clear cookies"""
    try:
        response = jsonify({'success': True, 'message': 'Logged out successfully'})
        
        # Clear all cookies by setting expiration to past
        response.set_cookie('user_id', '', expires=0, path='/')
        response.set_cookie('user_email', '', expires=0, path='/')
        response.set_cookie('user_name', '', expires=0, path='/')
        response.set_cookie('user_role', '', expires=0, path='/')
        response.set_cookie('trading_balance', '', expires=0, path='/')
        response.set_cookie('is_active', '', expires=0, path='/')
        response.set_cookie('logged_in', '', expires=0, path='/')
        
        return response
    except Exception as e:
        print(f"⚠️ Logout error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/status')
def get_status_api():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })
# ============ SKIP SIGNAL ROUTES (using second database) ============
@app.route('/api/skip_signal', methods=['POST'])
def skip_signal():
    """Mark a signal as skipped"""
    try:
        data = request.json
        user_id = get_user_id()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Please login first'}), 401
        
        signal_id = data.get('signal_id')
        symbol = data.get('symbol')
        direction = data.get('direction')
        
        if not signal_id:
            return jsonify({'success': False, 'error': 'Signal ID required'}), 400
        
        # Check if already skipped
        existing = skip_supabase.table('skipped_signals')\
            .select('id')\
            .eq('signal_id', signal_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            return jsonify({'success': True, 'message': 'Signal already skipped'})
        
        # Insert skipped signal
        response = skip_supabase.table('skipped_signals')\
            .insert({
                'signal_id': signal_id,
                'symbol': symbol or 'Unknown',
                'direction': direction or 'N/A',
                'user_id': user_id,
                'skipped_at': datetime.now().isoformat()
            })\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'skipped': response.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to skip signal'}), 500
            
    except Exception as e:
        print(f"⚠️ Error skipping signal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/get_skipped_signals', methods=['GET'])
def get_skipped_signals():
    """Get all skipped signals for a user"""
    try:
        if skip_supabase is None:
            return jsonify({'success': True, 'skipped': []})
            
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        response = skip_supabase.table('skipped_signals')\
            .select('signal_id')\
            .eq('user_id', user_id)\
            .execute()
        
        skipped = [item['signal_id'] for item in response.data] if response.data else []
        
        return jsonify({
            'success': True,
            'skipped': skipped
        })
    except Exception as e:
        print(f"⚠️ Error getting skipped signals: {e}")
        return jsonify({'success': True, 'skipped': []})  # Return empty on error
@app.route('/api/reset_skipped_signals', methods=['POST'])
def reset_skipped_signals():
    """Reset all skipped signals for a user"""
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        response = skip_supabase.table('skipped_signals')\
            .delete()\
            .eq('user_id', user_id)\
            .execute()
        
        return jsonify({'success': True, 'message': 'All skipped signals reset'})
    except Exception as e:
        print(f"⚠️ Error resetting skipped signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    data = fetch_from_dashboard()
    signals = fetch_signals_from_file()
    return jsonify({
        'status': 'healthy' if data.get('success') else 'unhealthy',
        'prices': len(data.get('prices', {})),
        'signals': len(signals),
        'timestamp': datetime.now().isoformat()
    })

# ============ MAIN ============

if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('📊 UNIFIED TRADING DASHBOARD (with Signals)')
    print('=' * 60)
    print('URL: http://localhost:5003')
    print(f'Connecting to forex_dashboard: {DASHBOARD_URL}')
    print('=' * 60 + '\n')
    
    app.run(host='0.0.0.0', port=5003, debug=False)