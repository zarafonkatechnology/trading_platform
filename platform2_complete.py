#!/usr/bin/env python3
"""
COMPLETE PLATFORM 2 - Instructor Dashboard
Full features: Agents, Telegram Signals, Supervisor Votes, Gatekeeper Audit, Collaboration
"""

import os

from flask import Flask, jsonify, render_template_string, request
import sqlite3
import json
import re
from datetime import datetime
import psycopg2
import requests
app = Flask(__name__)

DB_PATH = 'trading_system.db'

# ============================================
# COMPLETE HTML DASHBOARD
# ============================================

HTML_DASHBOARD = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Platform 2 | Instructor Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0e27; color: #e0e0e0; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1a1f3a, #0a0e27); padding: 20px; border-radius: 15px; margin-bottom: 20px; }
        .header h1 { color: #ffd700; }
        .tabs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
        .tab-btn { background: rgba(255,255,255,0.1); border: none; padding: 10px 20px; border-radius: 10px; color: white; cursor: pointer; }
        .tab-btn.active { background: #ffd700; color: #0a0e27; font-weight: bold; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: rgba(255,255,255,0.08); border-radius: 15px; padding: 15px; text-align: center; }
        .stat-value { font-size: 28px; font-weight: bold; color: #ffd700; }
        .data-table { width: 100%; background: rgba(0,0,0,0.3); border-radius: 15px; overflow-x: auto; }
        .data-table th, .data-table td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .data-table th { background: rgba(255,215,0,0.2); color: #ffd700; }
        .badge-success { background: #4caf50; padding: 2px 8px; border-radius: 20px; font-size: 11px; }
        .badge-danger { background: #f44336; padding: 2px 8px; border-radius: 20px; font-size: 11px; }
        .badge-warning { background: #ff9800; padding: 2px 8px; border-radius: 20px; font-size: 11px; }
        button { background: #ffd700; color: #0a0e27; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: bold; margin: 5px; }
        button:hover { opacity: 0.9; }
        .progress-bar { background: rgba(255,255,255,0.2); border-radius: 10px; height: 6px; overflow: hidden; }
        .progress-fill { background: #4caf50; height: 100%; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Platform 2: Instructor Dashboard</h1>
        <p>Complete transparency | All data accessible | Expandable database</p>
    </div>
    
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('agents')">🤖 Agents & Expandability</button>
        <button class="tab-btn" onclick="showTab('telegram')">📨 Telegram Signals</button>
        <button class="tab-btn" onclick="showTab('supervisor')">⚖️ Supervisor Votes</button>
        <button class="tab-btn" onclick="showTab('errors')">❌ Error Correction & ML</button>
        <button class="tab-btn" onclick="showTab('gatekeeper')">🚪 Gatekeeper Audit</button>
        <button class="tab-btn" onclick="showTab('collaboration')">🤝 Collaboration & Zero Errors</button>
    </div>
    
    <!-- Agents Tab -->
    <div id="tab-agents" class="tab-content active">
        <h3>🤖 Agents (Expandable - New agents auto-appear)</h3>
        <div class="stats-grid" id="agentStats"></div>
        <button onclick="addDemoAgent()" style="margin-bottom:15px; background:#4caf50; color:white;">➕ Add Demo Agent (Test Expandability)</button>
        <table class="data-table">
            <thead><tr><th>Agent</th><th>Type</th><th>XP</th><th>Tokens</th><th>Trust Weight</th><th>Accuracy</th><th>Votes</th><th>Status</th></tr></thead>
            <tbody id="agentsTable"></tbody>
        </table>
    </div>
    
    <!-- Telegram Tab -->
    <div id="tab-telegram" class="tab-content">
        <h3>📨 Telegram Signals</h3>
        <div class="stats-grid" id="telegramStats"></div>
        <table class="data-table">
            <thead><tr><th>Time</th><th>Asset</th><th>Price</th><th>Confidence</th><th>Strength</th></tr></thead>
            <tbody id="telegramTable"></tbody>
        </table>
    </div>
    
    <!-- Supervisor Tab -->
    <div id="tab-supervisor" class="tab-content">
        <h3>⚖️ Supervisor Vote Records</h3>
        <table class="data-table">
            <thead><tr><th>Time</th><th>Agent</th><th>Vote</th><th>Was Correct?</th><th>Error Type</th><th>XP Change</th></tr></thead>
            <tbody id="voteTable"></tbody>
        </table>
    </div>
    
    <!-- Error Tab -->
    <div id="tab-errors" class="tab-content">
        <h3>❌ Error Correction & ML Training</h3>
        <button onclick="startTrainingCycle()" style="margin-bottom:15px;">🔄 Start ML Training Cycle</button>
        <table class="data-table">
            <thead><tr><th>Agent</th><th>Error Category</th><th>Root Cause</th><th>Severity</th><th>Fixed?</th><th>Action</th></tr></thead>
            <tbody id="errorsTable"></tbody>
        </table>
        <h4>Training Cycles</h4>
        <table class="data-table">
            <thead><tr><th>Cycle</th><th>Started</th><th>Agents</th><th>Status</th></tr></thead>
            <tbody id="trainingTable"></tbody>
        </table>
    </div>
    
    <!-- Gatekeeper Tab -->
    <div id="tab-gatekeeper" class="tab-content">
        <h3>🚪 Gatekeeper Audit (Three Pillars)</h3>
        <table class="data-table">
            <thead><tr><th>Time</th><th>Agent</th><th>Identity</th><th>Logic</th><th>Resource</th><th>Gate Status</th></tr></thead>
            <tbody id="gatekeeperTable"></tbody>
        </table>
    </div>
    
    <!-- Collaboration Tab -->
    <div id="tab-collaboration" class="tab-content">
        <h3>🤝 Collaboration & Zero Error Metrics</h3>
        <table class="data-table">
            <thead><tr><th>Time</th><th>Consensus %</th><th>Teamwork Score</th><th>Zero Error</th></tr></thead>
            <tbody id="collabTable"></tbody>
        </table>
    </div>
</div>

<script>
    async function fetchJSON(url) {
        const res = await fetch(url);
        return res.json();
    }
    
    async function loadAgents() {
        const data = await fetchJSON('/api/agents');
        if (!data.success) return;
        const agents = data.agents;
        document.getElementById('agentsTable').innerHTML = agents.map(a => `
            <tr>
                <td>${a.agent_name}</td>
                <td>${a.agent_type || '-'}</td>
                <td>${a.xp_points || 0}</td>
                <td>${a.token_balance || 0}</td>
                <td>${((a.trust_weight || 0.2) * 100).toFixed(1)}%<div class="progress-bar"><div class="progress-fill" style="width:${(a.trust_weight || 0.2)*100}%"></div></div></td>
                <td><span class="${(a.vote_accuracy || 0) >= 70 ? 'badge-success' : 'badge-warning'}">${a.vote_accuracy || 0}%</span></td>
                <td>${a.total_votes || 0}</td>
                <td>${a.is_active ? '✅ Active' : '❌'}</td>
            </tr>
        `).join('');
        document.getElementById('agentStats').innerHTML = `
            <div class="stat-card"><div class="stat-value">${agents.length}</div><div class="stat-label">Total Agents</div></div>
            <div class="stat-card"><div class="stat-value">${agents.reduce((s,a)=>s+(a.xp_points||0),0)}</div><div class="stat-label">Total XP</div></div>
        `;
    }
    
    async function addDemoAgent() {
        const res = await fetch('/api/add_demo_agent', {method: 'POST'});
        const data = await res.json();
        if (data.success) {
            alert(`✅ ${data.message}`);
            loadAgents();
        } else {
            alert(`❌ Error: ${data.error}`);
        }
    }
    
    async function startTrainingCycle() {
        await fetch('/api/start_training', {method: 'POST'});
        alert('Training cycle started!');
        loadTrainingCycles();
    }
    
    async function loadTelegram() {
        const data = await fetchJSON('/api/telegram_signals');
        if (!data.success) return;
        const signals = data.signals || [];
        document.getElementById('telegramTable').innerHTML = signals.map(s => `
            <tr>
                <td>${new Date(s.received_at).toLocaleString()}</td>
                <td>${s.asset_type || '-'}</td>
                <td>$${s.current_price || 0}</td>
                <td>${s.confidence_percent || 0}%</td>
                <td><span class="${s.signal_strength === 'STRONG_SIGNAL' ? 'badge-success' : s.signal_strength === 'SIGNAL' ? 'badge-warning' : 'badge-danger'}">${s.signal_strength || 'WEAK'}</span></td>
            </tr>
        `).join('');
        document.getElementById('telegramStats').innerHTML = `<div class="stat-card"><div class="stat-value">${signals.length}</div><div class="stat-label">Total Signals</div></div>`;
    }
    
    async function loadVotes() {
        const data = await fetchJSON('/api/vote_records');
        if (!data.success) return;
        const votes = data.votes || [];
        document.getElementById('voteTable').innerHTML = votes.slice(0,50).map(v => `
            <tr>
                <td>${new Date(v.timestamp).toLocaleString()}</td>
                <td>${v.agent_name}</td>
                <td>${v.vote_cast}</td>
                <td>${v.was_correct ? '✅ Yes' : '❌ No'}</td>
                <td>${v.error_type || '-'}</td>
                <td>${v.xp_gained ? '+' + v.xp_gained : v.xp_lost ? '-' + v.xp_lost : 0}</td>
            </tr>
        `).join('');
    }
    
    async function loadErrors() {
        const data = await fetchJSON('/api/agent_errors');
        if (!data.success) return;
        const errors = data.errors || [];
        document.getElementById('errorsTable').innerHTML = errors.map(e => `
            <tr>
                <td>${e.agent_name}</td>
                <td>${e.error_category}</td>
                <td>${e.root_cause || e.error_description}</td>
                <td>${e.severity}/10</td>
                <td>${e.is_fixed ? '✅ Fixed' : '❌'}</td>
                <td>${!e.is_fixed ? `<button onclick="fixError(${e.id})">Fix</button>` : '-'}</td>
            </tr>
        `).join('');
    }
    
    async function loadTrainingCycles() {
        const data = await fetchJSON('/api/training_cycles');
        if (!data.success) return;
        const cycles = data.cycles || [];
        document.getElementById('trainingTable').innerHTML = cycles.map(c => `
            <tr>
                <td>#${c.cycle_number}</td>
                <td>${new Date(c.started_at).toLocaleString()}</td>
                <td>${c.agents_trained ? JSON.parse(c.agents_trained).length : 0}</td>
                <td><span class="${c.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}">${c.status || 'RUNNING'}</span></td>
            </tr>
        `).join('');
    }
    
    async function loadGatekeeper() {
        const data = await fetchJSON('/api/gatekeeper_audit');
        if (!data.success) return;
        const audits = data.audits || [];
        document.getElementById('gatekeeperTable').innerHTML = audits.slice(0,30).map(a => `
            <tr>
                <td>${new Date(a.timestamp).toLocaleString()}</td>
                <td>${a.agent_name}</td>
                <td>${a.pillar1_identity_passed ? '✅' : '❌'}</td>
                <td>${a.pillar2_logic_passed ? '✅' : '❌'}</td>
                <td>${a.pillar3_resource_passed ? '✅' : '❌'}</td>
                <td><span class="${a.gate_status === 'OPEN' ? 'badge-success' : 'badge-danger'}">${a.gate_status || 'BLOCKED'}</span></td>
            </tr>
        `).join('');
    }
    
    async function loadCollaboration() {
        const data = await fetchJSON('/api/collaboration_metrics');
        if (!data.success) return;
        const metrics = data.metrics || [];
        document.getElementById('collabTable').innerHTML = metrics.map(m => `
            <tr>
                <td>${new Date(m.timestamp).toLocaleString()}</td>
                <td>${m.consensus_percentage || 0}%</td>
                <td>${m.teamwork_score || 0}</td>
                <td>${m.zero_error_contribution ? '🏆 Yes' : '-'}</td>
            </tr>
        `).join('');
    }
    
    async function fixError(errorId) {
        await fetch('/api/correct_agent_error', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({error_id: errorId})
        });
        loadErrors();
    }
    
    function showTab(tabId) {
        document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
        document.getElementById(`tab-${tabId}`).classList.add('active');
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }
    
    // Load all data
    loadAgents();
    loadTelegram();
    loadVotes();
    loadErrors();
    loadTrainingCycles();
    loadGatekeeper();
    loadCollaboration();
    setInterval(() => {
        loadAgents();
        loadTelegram();
        loadVotes();
        loadErrors();
        loadGatekeeper();
        loadCollaboration();
    }, 30000);
</script>
</body>
</html>
'''

# ============================================
# DATABASE FUNCTIONS
# ============================================

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'trading_platform'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'lama'),
        cursor_factory=psycopg2.extras.RealDictCursor
    )
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Core agents table
    cursor.execute('''
CREATE TABLE IF NOT EXISTS core_agents (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) UNIQUE,
    agent_type VARCHAR(30),
    specialization VARCHAR(50),
    xp_points INTEGER DEFAULT 0,
    token_balance INTEGER DEFAULT 1000,
    trust_weight DECIMAL(5,4) DEFAULT 0.2,
    total_votes INTEGER DEFAULT 0,
    correct_votes INTEGER DEFAULT 0,
    vote_accuracy DECIMAL(5,2) DEFAULT 0,
    knowledge_shared_count INTEGER DEFAULT 0,
    achievements_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
    
    # Insert default agents if empty
    cursor.execute('SELECT COUNT(*) FROM core_agents')
    if cursor.fetchone()[0] == 0:
        default_agents = [
            ('Agent_A', 'Trend Follower', 'Moving Averages', 150, 1250, 0.25),
            ('Agent_B', 'Mean Reversion', 'RSI & Bollinger', 120, 1150, 0.22),
            ('Agent_C', 'Momentum', 'Price ROC', 90, 1080, 0.20),
            ('Agent_D', 'Volatility', 'ATR', 60, 1020, 0.18),
            ('Agent_E', 'Microstructure', 'Order Flow', 30, 1010, 0.15)
        ]
        for agent in default_agents:
            cursor.execute('''
                INSERT INTO core_agents (agent_name, agent_type, specialization, xp_points, token_balance, trust_weight)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', agent)
    
    # Telegram signals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT,
            current_price REAL,
            confidence_percent REAL,
            signal_strength TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Vote records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supervisor_vote_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            vote_cast TEXT,
            was_correct INTEGER,
            error_type TEXT,
            xp_gained INTEGER,
            xp_lost INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Agent errors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            error_category TEXT,
            error_description TEXT,
            root_cause TEXT,
            severity INTEGER,
            is_fixed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Training cycles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_training_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            agents_trained TEXT,
            status TEXT
        )
    ''')
    
    # Gatekeeper audit table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gatekeeper_full_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            pillar1_identity_passed INTEGER,
            pillar2_logic_passed INTEGER,
            pillar3_resource_passed INTEGER,
            gate_status TEXT,
            block_reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Collaboration metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS collaboration_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consensus_percentage REAL,
            teamwork_score REAL,
            zero_error_contribution INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/platform2')
def platform2():
    return HTML_DASHBOARD

@app.route('/api/agents')
def api_agents():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM core_agents ORDER BY agent_name')
    agents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'agents': agents})

@app.route('/api/add_demo_agent', methods=['POST'])
def api_add_demo_agent():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name FROM core_agents ORDER BY agent_name DESC LIMIT 1")
        last = cursor.fetchone()
        if last:
            last_name = last['agent_name']
            match = re.search(r'Agent_([A-Z])', last_name)
            if match:
                next_letter = chr(ord(match.group(1)) + 1)
                new_name = f"Agent_{next_letter}"
            else:
                new_name = "Agent_F"
        else:
            new_name = "Agent_A"
        
        cursor.execute('''
            INSERT INTO core_agents (agent_name, agent_type, specialization)
            VALUES (?, ?, ?)
        ''', (new_name, 'Demo Agent', 'Testing Expandability'))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Added {new_name}!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/telegram_signals')
def api_telegram_signals():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM telegram_signals ORDER BY received_at DESC LIMIT 100')
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'signals': signals})

@app.route('/api/vote_records')
def api_vote_records():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM supervisor_vote_records ORDER BY timestamp DESC LIMIT 100')
    votes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'votes': votes})

@app.route('/api/agent_errors')
def api_agent_errors():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agent_errors ORDER BY created_at DESC LIMIT 100')
    errors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'errors': errors})

@app.route('/api/training_cycles')
def api_training_cycles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ml_training_cycles ORDER BY cycle_number DESC')
    cycles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'cycles': cycles})

@app.route('/api/gatekeeper_audit')
def api_gatekeeper_audit():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM gatekeeper_full_audit ORDER BY timestamp DESC LIMIT 100')
    audits = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'audits': audits})

@app.route('/api/collaboration_metrics')
def api_collaboration_metrics():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM collaboration_metrics ORDER BY timestamp DESC LIMIT 50')
    metrics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'metrics': metrics})

@app.route('/api/correct_agent_error', methods=['POST'])
def api_correct_agent_error():
    data = request.get_json()
    error_id = data.get('error_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE agent_errors SET is_fixed = 1 WHERE id = ?', (error_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/start_training', methods=['POST'])
def api_start_training():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COALESCE(MAX(cycle_number), 0) + 1 FROM ml_training_cycles')
    new_cycle = cursor.fetchone()[0]
    cursor.execute('SELECT DISTINCT agent_name FROM agent_errors WHERE is_fixed = 0')
    agents = [row['agent_name'] for row in cursor.fetchall()]
    cursor.execute('''
        INSERT INTO ml_training_cycles (cycle_number, started_at, agents_trained, status)
        VALUES (?, ?, ?, ?)
    ''', (new_cycle, datetime.now().isoformat(), json.dumps(agents), 'RUNNING'))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'cycle_number': new_cycle})

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    init_db()
    print("\n" + "=" * 60)
    print("📊 PLATFORM 2: INSTRUCTOR DASHBOARD")
    print("=" * 60)
    print(f"✅ URL: http://localhost:5000/platform2")
    print(f"✅ Agents: Expandable - New agents auto-appear")
    print(f"✅ Telegram: Signal strength tracking")
    print(f"✅ Supervisor: Vote correctness tracking")
    print(f"✅ Gatekeeper: Three pillars audit")
    print(f"✅ Collaboration: Zero error metrics")
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
