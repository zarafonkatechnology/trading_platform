#!/usr/bin/env python3
"""
Platform 2 - Minimal Working Version
"""

from flask import Flask, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)

DB_PATH = 'trading_system.db'

# Simple HTML dashboard
HTML_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>Platform 2 - Instructor Dashboard</title>
    <style>
        body { font-family: Arial; background: #0a0e27; color: #e0e0e0; padding: 20px; }
        h1 { color: #ffd700; }
        button { background: #ffd700; color: #0a0e27; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 10px 0; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background: #ffd700; color: #0a0e27; }
        .success { color: #4caf50; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <h1>📊 Platform 2: Instructor Dashboard</h1>
    <p>Complete transparency | Expandable database</p>
    
    <button onclick="addAgent()">➕ Add Demo Agent (Test Expandability)</button>
    <div id="message"></div>
    <div id="agents"></div>
    
    <script>
        function loadAgents() {
            fetch('/api/agents')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h3>🤖 Agents List</h3><table><tr><th>Agent</th><th>Type</th><th>XP</th><th>Tokens</th><th>Trust Weight</th></tr>';
                        data.agents.forEach(a => {
                            html += `<tr>
                                <td>${a.agent_name}</td>
                                <td>${a.agent_type || '-'}</td>
                                <td>${a.xp_points || 0}</td>
                                <td>${a.token_balance || 0}</td>
                                <td>${((a.trust_weight || 0.2) * 100).toFixed(1)}%</td>
                            </tr>`;
                        });
                        html += '</table>';
                        document.getElementById('agents').innerHTML = html;
                    }
                });
        }
        
        function addAgent() {
            fetch('/api/add_demo_agent', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('message').innerHTML = `<p class="success">✅ ${data.message}</p>`;
                        loadAgents();
                    } else {
                        document.getElementById('message').innerHTML = `<p class="error">❌ Error: ${data.error}</p>`;
                    }
                })
                .catch(err => {
                    document.getElementById('message').innerHTML = `<p class="error">❌ Error: ${err.message}</p>`;
                });
        }
        
        loadAgents();
    </script>
</body>
</html>
'''

# Create table if not exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS core_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT UNIQUE,
            agent_type TEXT,
            specialization TEXT,
            xp_points INTEGER DEFAULT 0,
            token_balance INTEGER DEFAULT 1000,
            trust_weight REAL DEFAULT 0.2,
            vote_accuracy REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Insert default agents if none exist
    cursor.execute('SELECT COUNT(*) FROM core_agents')
    count = cursor.fetchone()[0]
    if count == 0:
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
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Routes
@app.route('/platform2')
def platform2():
    return HTML_DASHBOARD

@app.route('/api/agents')
def api_agents():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM core_agents ORDER BY agent_name')
        rows = cursor.fetchall()
        agents = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'agents': agents})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_demo_agent', methods=['POST'])
def api_add_demo_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get last agent to determine next name
        cursor.execute("SELECT agent_name FROM core_agents ORDER BY agent_name DESC LIMIT 1")
        last = cursor.fetchone()
        
        if last:
            last_name = last[0]
            import re
            match = re.search(r'Agent_([A-Z])', last_name)
            if match:
                next_letter = chr(ord(match.group(1)) + 1)
                new_name = f"Agent_{next_letter}"
            else:
                new_name = "Agent_F"
        else:
            new_name = "Agent_A"
        
        # Insert new agent
        cursor.execute('''
            INSERT INTO core_agents (agent_name, agent_type, specialization, xp_points, token_balance, trust_weight)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (new_name, 'Demo Agent', 'Testing Expandability', 0, 1000, 0.2))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Added {new_name}! The new agent appears automatically.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    print("\n" + "=" * 50)
    print("📊 Platform 2: Instructor Dashboard")
    print("=" * 50)
    print(f"URL: http://localhost:5000/platform2")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
