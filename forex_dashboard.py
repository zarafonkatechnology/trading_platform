
import os
import json
import time
import socket
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============ FILE PATHS ============
COMMON_FILES = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
DASHBOARD_FILE = os.path.join(COMMON_FILES, "dashboard_data.json")
SIGNALS_FILE = os.path.join(COMMON_FILES, "dashboard_signals.json")
LEADERBOARD_FILE = os.path.join(COMMON_FILES, "leaderboard.json")

print("=" * 60)
print("📊 COMPLETE MARKET DASHBOARD WITH WEBSOCKET")
print(f"   Reading: {DASHBOARD_FILE}")
print("=" * 60)


# ============ HTML WITH WEBSOCKET ============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📊 Complete Market Dashboard</title>
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
        .header h1 { 
            color: #ffd700; 
            font-size: 28px;
        }
        .header h1 span {
            font-size: 14px;
            color: #888;
            font-weight: normal;
        }
        
        .status {
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }
        .status-online {
            background: #4caf50;
            color: white;
            animation: pulse 2s infinite;
        }
        .status-offline {
            background: #f44336;
            color: white;
        }
        .status-ws-connected {
            background: #2196F3;
            color: white;
            animation: pulse 1s infinite;
        }
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
        .account-item {
            text-align: center;
        }
        .account-label {
            font-size: 11px;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .account-value {
            font-size: 28px;
            font-weight: bold;
            margin-top: 5px;
        }
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
        .tab:hover {
            background: #1f3460;
            color: #fff;
        }
        .tab.active {
            background: #ffd700;
            color: #0a0e27;
        }
        .tab-content {
            display: none;
            animation: fadeIn 0.3s;
        }
        .tab-content.active {
            display: block;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .section-title {
            color: #ffd700;
            font-size: 20px;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #2a2a4a;
        }
        .section-title .emoji {
            margin-right: 10px;
        }
        .section-title .count {
            font-size: 12px;
            color: #888;
            font-weight: normal;
        }
        
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
        .card:hover {
            transform: translateY(-3px);
        }
        .card.pulse {
            animation: cardPulse 0.3s ease;
        }
        @keyframes cardPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); background: #1f3460; }
            100% { transform: scale(1); }
        }
        
        .card-symbol {
            font-size: 16px;
            font-weight: bold;
            color: #ffd700;
        }
        .card-price {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }
        .card-change {
            font-size: 14px;
        }
        .card-change.up { color: #4caf50; }
        .card-change.down { color: #f44336; }
        .card-spread {
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }
        .card-time {
            font-size: 11px;
            color: #888;
            margin-top: 8px;
        }
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
        
        .card-gold {
            border-left-color: #ffd700;
            background: linear-gradient(135deg, #1a2a1a 0%, #16213e 100%);
        }
        .card-silver {
            border-left-color: #c0c0c0;
            background: linear-gradient(135deg, #1a1a2a 0%, #16213e 100%);
        }
        .card-gold .card-price { color: #ffd700; }
        .card-silver .card-price { color: #c0c0c0; }
        .card-energy {
            border-left-color: #ff6b35;
            background: linear-gradient(135deg, #1a1a0a 0%, #16213e 100%);
        }
        .card-energy .card-price { color: #ff6b35; }
        .card-index {
            border-left-color: #00bcd4;
            background: linear-gradient(135deg, #0a1a2a 0%, #16213e 100%);
        }
        .card-index .card-price { color: #00bcd4; }
        .card-forex {
            border-left-color: #4caf50;
            background: linear-gradient(135deg, #0a1a0a 0%, #16213e 100%);
        }
        .card-forex .card-price { color: #4caf50; }
        .card-dollar {
            border-left-color: #9c27b0;
            background: linear-gradient(135deg, #1a0a2a 0%, #16213e 100%);
        }
        .card-dollar .card-price { color: #ce93d8; }
        
        /* Statistics Table */
        .stats-table {
            width: 100%;
            max-width: 600px;
            margin: 20px auto;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 12px;
            overflow: hidden;
        }
        .stats-table th {
            background: #0f3460;
            color: #ffd700;
            padding: 15px;
            text-align: left;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stats-table td {
            padding: 15px;
            border-bottom: 1px solid #2a2a4a;
        }
        .stats-table tr:last-child td {
            border-bottom: none;
        }
        .stats-table .label {
            color: #aaa;
            font-weight: bold;
        }
        .stats-table .value {
            color: #fff;
            font-size: 18px;
            font-weight: bold;
            text-align: right;
        }
        .stats-table .value.gold { color: #ffd700; }
        .stats-table .value.green { color: #4caf50; }
        .stats-table .value.red { color: #f44336; }
        
        /* Leaderboard */
        .leaderboard-table {
            width: 100%;
            max-width: 800px;
            margin: 20px auto;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 12px;
            overflow: hidden;
        }
        .leaderboard-table th {
            background: #0f3460;
            color: #ffd700;
            padding: 12px 15px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .leaderboard-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #2a2a4a;
        }
        .leaderboard-table tr:last-child td {
            border-bottom: none;
        }
        .leaderboard-table tr:hover {
            background: #1a2a4a;
        }
        .leaderboard-table .rank {
            font-weight: bold;
            color: #ffd700;
            text-align: center;
        }
        .leaderboard-table .rank-1 { color: #ffd700; }
        .leaderboard-table .rank-2 { color: #c0c0c0; }
        .leaderboard-table .rank-3 { color: #cd7f32; }
        .leaderboard-table .agent-name {
            font-weight: bold;
            color: #fff;
        }
        .leaderboard-table .win-rate {
            font-weight: bold;
        }
        .leaderboard-table .win-rate.high { color: #4caf50; }
        .leaderboard-table .win-rate.medium { color: #ff9800; }
        .leaderboard-table .win-rate.low { color: #f44336; }
        .leaderboard-table .xp {
            color: #ffd700;
            font-weight: bold;
        }
        .leaderboard-table .tokens {
            color: #00bcd4;
            font-weight: bold;
        }
        .leaderboard-table .confidence {
            color: #4caf50;
            font-weight: bold;
        }
        .leaderboard-table .votes {
            color: #aaa;
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
            margin-bottom: 20px;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.8; }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #ffd700;
            font-size: 18px;
        }
        
        .error {
            text-align: center;
            padding: 50px;
            color: #f44336;
            font-size: 18px;
        }
        
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
            .stats-table, .leaderboard-table { font-size: 12px; }
            .stats-table td, .leaderboard-table td { padding: 10px; }
        }
    </style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="header">
        <h1>📊 Complete Market Dashboard <span>Real-Time Prices</span></h1>
        <div>
            <span id="wsStatus" class="status status-offline">🔌 Connecting...</span>
            <span id="status" class="status status-online">✅ ONLINE</span>
        </div>
    </div>
    
    <!-- Account -->
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
    </div>
    
    <!-- Tabs -->
    <div class="tabs">
        <div class="tab active" onclick="switchTab('markets')">📊 Markets</div>
        <div class="tab" onclick="switchTab('statistics')">📈 Statistics</div>
        <div class="tab" onclick="switchTab('leaderboard')">🏆 Leaderboard</div>
    </div>
    
    <!-- Refresh -->
    <button class="refresh-btn" onclick="manualRefresh()">🔄 Refresh All Data</button>
    <span id="refreshStatus" style="color:#888;font-size:12px;margin-left:10px;"></span>
    
    <!-- TAB 1: MARKETS -->
    <div id="tab-markets" class="tab-content active">
        <!-- FOREX MAJORS -->
        <div class="section-title"><span class="emoji">💱</span> FOREX MAJORS <span class="count" id="forexMajorsCount"></span></div>
        <div id="forexMajorsGrid" class="grid">
            <div class="loading">Loading forex majors...</div>
        </div>
        
        <!-- FOREX MINORS & CROSSES -->
        <div class="section-title"><span class="emoji">💱</span> FOREX MINORS & CROSSES <span class="count" id="forexCrossesCount"></span></div>
        <div id="forexCrossesGrid" class="grid">
            <div class="loading">Loading forex crosses...</div>
        </div>
        
        <!-- INDICES -->
        <div class="section-title"><span class="emoji">📈</span> INDICES <span class="count" id="indicesCount"></span></div>
        <div id="indicesGrid" class="grid">
            <div class="loading">Loading indices...</div>
        </div>
        
        <!-- METALS -->
        <div class="section-title"><span class="emoji">🥇</span> METALS <span class="count" id="metalsCount"></span></div>
        <div id="metalsGrid" class="grid">
            <div class="loading">Loading metals...</div>
        </div>
        
        <!-- ENERGY -->
        <div class="section-title"><span class="emoji">🛢️</span> ENERGY <span class="count" id="energyCount"></span></div>
        <div id="energyGrid" class="grid">
            <div class="loading">Loading energy...</div>
        </div>
        
        <!-- DOLLAR INDEX -->
        <div class="section-title"><span class="emoji">💵</span> DOLLAR INDEX <span class="count" id="dollarCount"></span></div>
        <div id="dollarGrid" class="grid">
            <div class="loading">Loading dollar index...</div>
        </div>
    </div>
    
    <!-- TAB 2: STATISTICS -->
    <div id="tab-statistics" class="tab-content">
        <div style="text-align:center;">
            <h2 style="color:#ffd700;margin-bottom:20px;">📊 Trading Statistics</h2>
            <table class="stats-table" id="statsTable">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody id="statsBody">
                    <tr><td colspan="2" style="text-align:center;padding:30px;color:#888;">Loading statistics...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- TAB 3: LEADERBOARD -->
    <div id="tab-leaderboard" class="tab-content">
        <div style="text-align:center;">
            <h2 style="color:#ffd700;margin-bottom:20px;">🏆 Agent Leaderboard</h2>
            <table class="leaderboard-table" id="leaderboardTable">
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
                    <tr><td colspan="7" style="text-align:center;padding:30px;color:#888;">Loading leaderboard...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="ip-info">
        🌐 Server: localhost:5002 | Auto-refresh: <span id="countdown">5</span>s | 
        Data source: <span id="dataSource">File</span> | 
        WS: <span id="wsInfo">Disconnected</span>
    </div>
</div>

<script>
// Configuration
const FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'];
const FOREX_CROSSES = ['EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'];
const INDICES = ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', "#AMAZON", '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD'];
const METALS = ['GOLD', 'SILVER'];
const ENERGY = ['BRENT_OIL', 'CrudeOIL'];
const DOLLAR = ['#DOLLAR_IND'];

let refreshInterval = null;
let countdown = 5;
let currentData = null;

// ============ SOCKET.IO ============
const socket = io();

socket.on('connect', function() {
    document.getElementById('wsStatus').className = 'status status-ws-connected';
    document.getElementById('wsStatus').textContent = '🔌 Connected';
    document.getElementById('wsInfo').textContent = 'Connected';
    document.getElementById('wsInfo').style.color = '#4caf50';
});

socket.on('disconnect', function() {
    document.getElementById('wsStatus').className = 'status status-offline';
    document.getElementById('wsStatus').textContent = '🔌 Disconnected';
    document.getElementById('wsInfo').textContent = 'Disconnected';
    document.getElementById('wsInfo').style.color = '#f44336';
});

// Listen for price updates via WebSocket
socket.on('price_update', function(data) {
    if (data && data.prices) {
        // Update current data with new prices
        if (!currentData) {
            currentData = { prices: {} };
        }
        
        // Merge new prices
        for (const [symbol, priceData] of Object.entries(data.prices)) {
            if (!currentData.prices) currentData.prices = {};
            currentData.prices[symbol] = priceData;
        }
        
        // Update timestamp
        if (data.timestamp) {
            currentData.timestamp = data.timestamp;
        }
        
        // Only update the markets tab UI
        updateAllMarketCards(currentData);
    }
});

// Listen for full data updates via WebSocket
socket.on('full_update', function(data) {
    if (data && data.success) {
        currentData = data;
        updateFullDashboard(data);
    }
});

// ============ UI FUNCTIONS ============

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    const tabs = document.querySelectorAll('.tab');
    const tabMap = {'markets': 0, 'statistics': 1, 'leaderboard': 2};
    if (tabMap[tabName] !== undefined) {
        tabs[tabMap[tabName]].classList.add('active');
    }
    document.getElementById('tab-' + tabName).classList.add('active');
}

// Get price with alternative names - NOW RETURNS FULL OBJECT WITH BID/ASK
function getPriceData(data, symbol) {
    if (!data || !data.prices) return null;
    
    if (data.prices[symbol]) {
        return data.prices[symbol];
    }
    
    const altMap = {
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
        'CrudeOIL': ['CRUDE', 'USOIL'],
        'USDCHF': ['CHFUSD'],
        'EURCHF': ['EURCHF']
    };
    
    if (altMap[symbol]) {
        for (let alt of altMap[symbol]) {
            if (data.prices[alt]) {
                return data.prices[alt];
            }
        }
    }
    return null;
}

// Render market cards
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
            if (type === 'metal') {
                cardClass += symbol === 'GOLD' ? ' card-gold' : ' card-silver';
            } else if (type === 'energy') {
                cardClass += ' card-energy';
            } else if (type === 'index') {
                cardClass += ' card-index';
            } else if (type === 'forex') {
                cardClass += ' card-forex';
            } else if (type === 'dollar') {
                cardClass += ' card-dollar';
            }
            card.className = cardClass;
            card.id = 'card-' + symbol;
            
            const price = priceInfo.price;
            const bid = priceInfo.bid || price;
            const ask = priceInfo.ask || price;
            const spread = (ask - bid).toFixed(getDecimals(symbol));
            const change = priceInfo.change || 0;
            const changeClass = change >= 0 ? 'up' : 'down';
            const changeSymbol = change >= 0 ? '▲' : '▼';
            
            let decimals = getDecimals(symbol);
            let prefix = '';
            let displaySymbol = symbol;
            
            // Determine display format
            if (FOREX_MAJORS.includes(symbol) || FOREX_CROSSES.includes(symbol)) {
                if (symbol === 'USDJPY' || symbol === 'EURJPY') {
                    decimals = 3;
                } else {
                    decimals = 5;
                }
            } else if (METALS.includes(symbol)) {
                decimals = 2;
                prefix = '$';
            } else if (INDICES.includes(symbol)) {
                decimals = 2;
                if (symbol === '#NASDAQ100') displaySymbol = 'NASDAQ 100';
                else if (symbol === '#DJ30') displaySymbol = 'Dow Jones';
                else if (symbol === '#S&P500') displaySymbol = 'S&P 500';
                else if (symbol === '#RUSS2000') displaySymbol = 'Russell 2000';
                else if (symbol === '#CAC40') displaySymbol = 'CAC 40';
                else if (symbol === '#DAX40') displaySymbol = 'DAX 40';
                else if (symbol === '#FTSE100') displaySymbol = 'FTSE 100';
                else if (symbol === '#NIKKEI225') displaySymbol = 'Nikkei 225';
                else if (symbol === '#AMAZON') displaySymbol = 'Amazon';
                else if (symbol === '#APPLE') displaySymbol = 'Apple';
                else if (symbol === '#MICROSOFT') displaySymbol = 'Microsoft';
                else if (symbol === '#SPACEX') displaySymbol = 'SpaceX';
                else if (symbol === '#VISA') displaySymbol = 'Visa';
                else if (symbol === '#MASTERCARD') displaySymbol = 'Mastercard';
            } else if (ENERGY.includes(symbol)) {
                decimals = 2;
                prefix = '$';
                if (symbol === 'BRENT_OIL') displaySymbol = 'Brent Oil';
                else if (symbol === 'CrudeOIL') displaySymbol = 'Crude Oil';
            } else if (DOLLAR.includes(symbol)) {
                decimals = 3;
                displaySymbol = 'Dollar Index';
            }
            
            let priceDisplay = price.toFixed(decimals);
            let bidDisplay = bid.toFixed(decimals);
            let askDisplay = ask.toFixed(decimals);
            
            card.innerHTML = `
                <div class="card-symbol">${displaySymbol}</div>
                <div class="card-price">${prefix}${priceDisplay}</div>
                <div class="card-change ${changeClass}">${changeSymbol} ${Math.abs(change).toFixed(2)}%</div>
                <div class="card-bid-ask">
                    <span class="bid">Bid: ${prefix}${bidDisplay}</span>
                    <span class="ask">Ask: ${prefix}${askDisplay}</span>
                </div>
                <div class="card-spread">Spread: ${prefix}${spread}</div>
                <div class="card-time">Updated: ${data.timestamp || '--:--:--'}</div>
            `;
            grid.appendChild(card);
            
            // Animate price update
            setTimeout(() => {
                const cardEl = document.getElementById('card-' + symbol);
                if (cardEl) cardEl.classList.add('pulse');
                setTimeout(() => {
                    if (cardEl) cardEl.classList.remove('pulse');
                }, 300);
            }, 50);
        }
    });
    
    const countId = containerId.replace('Grid', 'Count');
    const countEl = document.getElementById(countId);
    if (countEl) {
        countEl.textContent = `(${found} ${found === 1 ? 'item' : 'items'})`;
    }
    
    if (found === 0) {
        grid.innerHTML = `<div class="error">⚠️ No ${type} data available</div>`;
    }
}

// Helper function to get decimals for a symbol
function getDecimals(symbol) {
    if (['USDJPY', 'EURJPY'].includes(symbol)) return 3;
    if (['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225', 'BRENT_OIL', 'CrudeOIL'].includes(symbol)) return 2;
    if (symbol === '#DOLLAR_IND') return 3;
    return 5;
}

// Update only market cards (for WebSocket price updates)
function updateAllMarketCards(data) {
    if (!data) return;
    renderCards('forexMajorsGrid', FOREX_MAJORS, 'forex', data);
    renderCards('forexCrossesGrid', FOREX_CROSSES, 'forex', data);
    renderCards('indicesGrid', INDICES, 'index', data);
    renderCards('metalsGrid', METALS, 'metal', data);
    renderCards('energyGrid', ENERGY, 'energy', data);
    renderCards('dollarGrid', DOLLAR, 'dollar', data);
}

// Render statistics
function renderStatistics(stats) {
    const tbody = document.getElementById('statsBody');
    if (!stats) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;padding:30px;color:#888;">No statistics available</td></tr>';
        return;
    }
    
    const rows = [
        ['Total Trades', stats.total_trades || 0, ''],
        ['Win Rate', (stats.win_rate || 0) + '%', stats.win_rate > 50 ? 'green' : stats.win_rate > 30 ? 'gold' : 'red'],
        ['Total P&L', '$' + (stats.total_pnl || 0).toFixed(2), (stats.total_pnl || 0) >= 0 ? 'green' : 'red'],
        ['Profit Factor', (stats.profit_factor || 0).toFixed(2), (stats.profit_factor || 0) > 1 ? 'green' : 'red'],
        ['Active Agents', stats.active_agents || 0, '']
    ];
    
    tbody.innerHTML = rows.map(row => `
        <tr>
            <td class="label">${row[0]}</td>
            <td class="value ${row[2]}">${row[1]}</td>
        </tr>
    `).join('');
}

// Render leaderboard
function renderLeaderboard(leaderboard) {
    const tbody = document.getElementById('leaderboardBody');
    if (!leaderboard || leaderboard.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#888;">No leaderboard data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = leaderboard.map((agent, index) => {
        const rank = index + 1;
        let rankClass = 'rank';
        if (rank === 1) rankClass += ' rank-1';
        else if (rank === 2) rankClass += ' rank-2';
        else if (rank === 3) rankClass += ' rank-3';
        
        let winRateClass = 'win-rate';
        if (agent.win_rate > 60) winRateClass += ' high';
        else if (agent.win_rate > 40) winRateClass += ' medium';
        else winRateClass += ' low';
        
        return `
            <tr>
                <td class="${rankClass}">#${rank}</td>
                <td class="agent-name">${agent.agent_name || 'Agent ' + rank}</td>
                <td class="votes">${agent.total_votes || 0}</td>
                <td class="${winRateClass}">${agent.win_rate || 0}%</td>
                <td class="xp">${agent.total_xp || 0}</td>
                <td class="tokens">${agent.total_tokens || 0}</td>
                <td class="confidence">${agent.avg_confidence || 0}%</td>
            </tr>
        `;
    }).join('');
}

// Update full dashboard
function updateFullDashboard(data) {
    if (!data || !data.success) return;
    
    // Update account
    document.getElementById('balance').textContent = '$' + (data.balance || 0).toFixed(2);
    document.getElementById('equity').textContent = '$' + (data.equity || 0).toFixed(2);
    document.getElementById('updated').textContent = data.timestamp || '--:--:--';
    document.getElementById('dataSource').textContent = data.source || 'File';
    
    // Update status
    const statusDiv = document.getElementById('status');
    statusDiv.className = 'status status-online';
    statusDiv.textContent = '✅ CONNECTED';
    
    // Update all sections
    updateAllMarketCards(data);
    renderStatistics(data.stats);
    renderLeaderboard(data.leaderboard);
}

// ============ MAIN REFRESH ============
async function manualRefresh() {
    document.getElementById('refreshStatus').textContent = '⏳ Loading...';
    try {
        const response = await fetch('/api/all_data?_=' + Date.now());
        const data = await response.json();
        
        if (data.success) {
            currentData = data;
            updateFullDashboard(data);
            document.getElementById('refreshStatus').textContent = '✅ Updated ' + data.timestamp;
            
            // Also update via WebSocket
            socket.emit('request_update');
        } else {
            document.getElementById('refreshStatus').textContent = '❌ Error: ' + (data.error || 'Unknown');
        }
    } catch(e) {
        console.error('Error:', e);
        document.getElementById('refreshStatus').textContent = '❌ Connection error';
    }
}

// ============ COUNTDOWN AUTO-REFRESH ============
function startCountdown() {
    countdown = 5;
    document.getElementById('countdown').textContent = countdown;
    
    const timer = setInterval(() => {
        countdown--;
        document.getElementById('countdown').textContent = countdown;
        if (countdown <= 0) {
            clearInterval(timer);
            manualRefresh();
            startCountdown();
        }
    }, 1000);
}

// ============ INITIALIZATION ============
manualRefresh();
startCountdown();

// Also request initial data via WebSocket
socket.on('connect', function() {
    socket.emit('request_update');
});
</script>
</body>
</html>
"""

# ============ WEBSOCKET EVENT HANDLERS ============

@socketio.on('connect')
def handle_connect():
    print(f"🔌 Client connected: {request.sid}")
    connected_clients.add(request.sid)
    
    # Send initial data
    data = get_all_data_dict()
    emit('full_update', data)
    emit('connected', {
        'status': 'connected', 
        'message': 'Welcome to the dashboard!',
        'timestamp': datetime.now().isoformat()
    })
    print(f"📤 Sent initial data to {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_clients:
        connected_clients.remove(request.sid)
    print(f"🔌 Client disconnected: {request.sid} (Total: {len(connected_clients)})")

@socketio.on('request_update')
def handle_request_update():
    """Send current data to client"""
    data = get_all_data_dict()
    emit('full_update', data)
    print(f"📤 Sent full update to {request.sid}")

def get_all_data_dict():
    """Get all data as dictionary (same as /api/all_data)"""
    try:
        data = None
        source = "Fallback"
        
        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    data = json.load(f)
                source = "File"
                print(f"✅ File read at {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"⚠️ Error reading file: {e}")
        
        response = {
            'success': True,
            'balance': 0,
            'equity': 0,
            'prices': {},
            'stats': {},
            'leaderboard': [],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': source,
            'file_exists': os.path.exists(DASHBOARD_FILE)
        }
        
        # ALL symbols
        all_symbols = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF',
            '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
            'GOLD', 'SILVER',
            'BRENT_OIL', 'CrudeOIL',
            '#DOLLAR_IND', 
            "#AMAZON", '#APPLE', '#MICROSOFT', '#SPACEX', '#VISA', '#MASTERCARD'
        ]
        
        # Fallback values with bid/ask spread
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
            '#DOLLAR_IND': {'bid': 104.50, 'ask': 104.60, 'price': 104.55},
            '#AMAZON': {'bid': 273.43, 'ask': 274.77, 'price': 274.10},
            # Add to fallback dictionary
            '#APPLE': {'bid': 309.32, 'ask': 310.88, 'price': 310.10},
            '#MICROSOFT': {'bid': 445.00, 'ask': 447.50, 'price': 446.25},
            '#SPACEX': {'bid': 185.00, 'ask': 186.50, 'price': 185.75},
            '#VISA': {'bid': 365.45, 'ask': 367.29, 'price': 366.37},
            '#MASTERCARD': {'bid': 485.00, 'ask': 487.50, 'price': 486.25}
        }
        
        if data:
            response['balance'] = float(data.get('balance', 0))
            response['equity'] = float(data.get('equity', 0))
            
            response['stats'] = {
                'total_trades': int(data.get('total_trades', 0)),
                'win_rate': float(data.get('win_rate', 0)),
                'total_pnl': float(data.get('total_pnl', 0)),
                'profit_factor': float(data.get('profit_factor', 0)),
                'active_agents': int(data.get('active_agents', 1))
            }
            
            # Try to get bid/ask from the data
            if 'prices' in data and data['prices']:
                for symbol in all_symbols:
                    price_data = None
                    
                    # Check if we have bid/ask in the data
                    if symbol in data['prices']:
                        if isinstance(data['prices'][symbol], dict):
                            price_data = data['prices'][symbol]
                        else:
                            price_val = float(data['prices'][symbol])
                            price_data = {'bid': price_val, 'ask': price_val, 'price': price_val}
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
                            'CrudeOIL': ['CRUDE', 'USOIL'],
                            '#AMAZON': ['AMAZON', 'AMZN'],
                            '#APPLE': ['APPLE', 'AAPL'],
                            '#MICROSOFT': ['MICROSOFT', 'MSFT'],
                            '#SPACEX': ['SPACEX'],
                            '#VISA': ['VISA', 'V'],
                            '#MASTERCARD': ['MASTERCARD', 'MA']
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
                        # Ensure we have bid and ask
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
                        # Use fallback
                        fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                        response['prices'][symbol] = {
                            'bid': fb['bid'],
                            'ask': fb['ask'],
                            'price': fb['price'],
                            'change': 0
                        }
            else:
                # No prices in data, use fallback
                for symbol in all_symbols:
                    fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                    response['prices'][symbol] = {
                        'bid': fb['bid'],
                        'ask': fb['ask'],
                        'price': fb['price'],
                        'change': 0
                    }
        else:
            # No data file, use fallback
            for symbol in all_symbols:
                fb = fallback.get(symbol, {'bid': 0, 'ask': 0, 'price': 0})
                response['prices'][symbol] = {
                    'bid': fb['bid'],
                    'ask': fb['ask'],
                    'price': fb['price'],
                    'change': 0
                }
            response['balance'] = 744.76
            response['equity'] = 744.76
            response['stats'] = {
                'total_trades': 365,
                'win_rate': 38.4,
                'total_pnl': 909.14,
                'profit_factor': 2.28,
                'active_agents': 1
            }
        
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, 'r') as f:
                    leaderboard = json.load(f)
                    if isinstance(leaderboard, list):
                        response['leaderboard'] = leaderboard
                    elif isinstance(leaderboard, dict) and 'leaderboard' in leaderboard:
                        response['leaderboard'] = leaderboard['leaderboard']
            except Exception as e:
                print(f"⚠️ Error reading leaderboard: {e}")
        
        if not response['leaderboard']:
            response['leaderboard'] = [
                {'agent_name': 'Alpha Trader', 'total_votes': 156, 'win_rate': 65, 'total_xp': 12500, 'total_tokens': 4500, 'avg_confidence': 82},
                {'agent_name': 'Beta AI', 'total_votes': 142, 'win_rate': 58, 'total_xp': 9800, 'total_tokens': 3200, 'avg_confidence': 76},
                {'agent_name': 'Gamma Strategy', 'total_votes': 128, 'win_rate': 52, 'total_xp': 8700, 'total_tokens': 2800, 'avg_confidence': 71}
            ]
        
        return response
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
# ============ GLOBALS ============
current_data = {
    'prices': {},
    'balance': 0,
    'equity': 0,
    'timestamp': datetime.now().isoformat(),
    'success': True
}
# ============ FILE WATCHER THREAD ============

last_file_mod_time = 0
connected_clients = set()  # ✅ ADD THIS LINE HERE

def file_watcher():
    """Watch for file changes and broadcast updates"""
    global last_file_mod_time
    
    print("👁️ Starting file watcher...")
    
    while True:
        try:
            if os.path.exists(DASHBOARD_FILE):
                current_mtime = os.path.getmtime(DASHBOARD_FILE)
                if current_mtime > last_file_mod_time:
                    last_file_mod_time = current_mtime
                    print(f"📁 File changed, broadcasting update...")
                    
                    # Get updated data
                    data = get_all_data_dict()
                    
                    # Broadcast to all connected clients
                    socketio.emit('full_update', data)
                    
                    # Also send just price updates for efficiency
                    if data.get('success') and data.get('prices'):
                        price_update = {
                            'prices': data['prices'],
                            'timestamp': data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
                        }
                        socketio.emit('price_update', price_update)
        except Exception as e:
            print(f"⚠️ File watcher error: {e}")
        
        time.sleep(1)  # Check every second
# full_market_dashboard.py - After globals, before @app.route

# ============ HELPER FUNCTIONS ============

def get_current_price(symbol: str) -> float:
    """
    ✅ NEW: Get current price for a symbol
    Returns 0 if symbol not found
    """
    try:
        # Try to get from current data
        if current_data and 'prices' in current_data:
            price_data = current_data['prices'].get(symbol)
            if price_data:
                if isinstance(price_data, dict):
                    return float(price_data.get('price', 0))
                return float(price_data)
        
        # Try to read from file directly
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
        print(f"⚠️ Error getting price for {symbol}: {e}")
        return 0


def get_all_current_prices() -> Dict:
    """
    ✅ NEW: Get all current prices
    """
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
        print(f"⚠️ Error getting all prices: {e}")
        return {}


# ============ FILE READING FUNCTIONS ============
# ============ API ROUTES ============

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/all_data')
def api_all_data():
    """Get all data: prices, stats, and leaderboard"""
    return jsonify(get_all_data_dict())
@app.route('/api/prices')
def api_prices():
    """Get only prices (lightweight endpoint)"""
    try:
        prices = get_all_current_prices()
        return jsonify({
            'success': True,
            'prices': prices,
            'timestamp': datetime.now().isoformat(),
            'count': len(prices)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/status')
def api_status():
    """Get server status"""
    return jsonify({
        'success': True,
        'status': 'online',
        'port': 5002,
        'file_exists': os.path.exists(DASHBOARD_FILE),
        'prices_count': len(get_all_current_prices()),
        'connected_clients': len(connected_clients),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/debug')
def debug():
    """Debug endpoint"""
    try:
        result = {
            'file_path': DASHBOARD_FILE,
            'file_exists': os.path.exists(DASHBOARD_FILE),
            'leaderboard_path': LEADERBOARD_FILE,
            'leaderboard_exists': os.path.exists(LEADERBOARD_FILE),
            'websocket_status': 'running'
        }
        
        if result['file_exists']:
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
            result['keys'] = list(data.keys())
            result['has_prices'] = 'prices' in data
            result['prices'] = data.get('prices', {})
            result['balance'] = data.get('balance', 0)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})
# forex_dashboard.py - Add this endpoint

@app.route('/api/history')
def get_history():
    """
    Get historical price data for a symbol
    Query params: symbol, count, timeframe
    """
    try:
        symbol = request.args.get('symbol', 'EURUSD')
        count = int(request.args.get('count', 100))
        timeframe = request.args.get('timeframe', 'M15')
        
        # Map timeframe to minutes
        timeframe_map = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440,
            'W1': 10080
        }
        minutes = timeframe_map.get(timeframe, 15)
        
        # Get historical data from MT4
        history = []
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                data = json.load(f)
                # Get price history from file
                if 'history' in data and symbol in data['history']:
                    history = data['history'][symbol][-count:]
        
        # If no history in file, try to generate from current price
        if not history:
            current_price = get_current_price(symbol)
            if current_price > 0:
                # Generate synthetic history
                import random
                price = current_price
                for i in range(count):
                    # Random walk with mean reversion
                    if i < count // 2:
                        price = price * (1 + (i - count//4) / count * 0.01)
                    else:
                        price = price * (1 - (i - count//4) / count * 0.005)
                    price = price * (1 + (random.random() - 0.5) * 0.002)
                    history.append(price)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'count': len(history),
            'history': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/history_all')
def get_history_all():
    """
    Get historical data for ALL symbols at once
    """
    try:
        count = int(request.args.get('count', 100))
        
        result = {}
        all_symbols = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF',
            '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
            'GOLD', 'SILVER',
            'BRENT_OIL', 'CrudeOIL',
            '#DOLLAR_IND'
        ]
        
        for symbol in all_symbols:
            current_price = get_current_price(symbol)
            if current_price > 0:
                # Generate synthetic history
                import random
                history = []
                price = current_price
                for i in range(count):
                    if i < count // 2:
                        price = price * (1 + (i - count//4) / count * 0.01)
                    else:
                        price = price * (1 - (i - count//4) / count * 0.005)
                    price = price * (1 + (random.random() - 0.5) * 0.002)
                    history.append(price)
                result[symbol] = history
        
        return jsonify({
            'success': True,
            'count': count,
            'history': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
@app.route('/api/websocket_status')
def websocket_status():
    """Check WebSocket status"""
    return jsonify({
        'connected_clients': len(socketio.server.manager.rooms.get('/', {}).get('', set())),
        'status': 'running'
    })

# ============ START ============
if __name__ == '__main__':
    HOST = '0.0.0.0'
    PORT = 5002
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "127.0.0.1"
    
    print("\n" + "=" * 60)
    print("📊 COMPLETE MARKET DASHBOARD WITH WEBSOCKET")
    print("   URL: http://localhost:" + str(PORT))
    print("   URL: http://127.0.0.1:" + str(PORT))
    print("   URL: http://" + local_ip + ":" + str(PORT))
    print("   File: " + DASHBOARD_FILE)
    print("   Debug: http://localhost:" + str(PORT) + "/api/debug")
    print("   WebSocket: ws://localhost:" + str(PORT) + "/socket.io/")
    print("=" * 60 + "\n")
    
    # Start file watcher thread
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    print("✅ File watcher thread started")
    
    # Run with SocketIO
    socketio.run(app, host=HOST, port=PORT, debug=False, allow_unsafe_werkzeug=True)