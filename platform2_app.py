#!/usr/bin/env python3
"""
Platform 2: Instructor Dashboard - SQLite Version
"""

import sqlite3
import re
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, template_folder='frontend/templates')
CORS(app)

DB_PATH = 'trading_system.db'

def get_db():
    """Get SQLite connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
    return conn

# ============================================
# DASHBOARD ROUTE
# ============================================

@app.route('/platform2')
def platform2_dashboard():
    return render_template('platform2_dashboard.html')

# ============================================
# AGENTS ENDPOINT
# ============================================

@app.route('/api/platform2/agents')
def api_agents():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM core_agents ORDER BY agent_name')
        rows = cursor.fetchall()
        agents = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'agents': agents})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# ADD DEMO AGENT (WORKING VERSION)
# ============================================

@app.route('/api/platform2/add_demo_agent', methods=['POST'])
def api_add_demo_agent():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Create table if not exists
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
                total_votes INTEGER DEFAULT 0,
                correct_votes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get the last agent to determine next letter
        cursor.execute("SELECT agent_name FROM core_agents ORDER BY agent_name DESC LIMIT 1")
        last = cursor.fetchone()
        
        if last:
            # last is a Row object, access by index
            last_name = last[0] if isinstance(last, tuple) else last['agent_name']
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
            INSERT INTO core_agents (agent_name, agent_type, specialization, xp_points, token_balance, trust_weight, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (new_name, 'Demo Agent', 'Testing Expandability', 0, 1000, 0.2, 1))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'agent_name': new_name, 'message': f'Added {new_name}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# TELEGRAM SIGNALS ENDPOINT
# ============================================

@app.route('/api/platform2/telegram_signals')
def api_telegram_signals():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Create table if not exists
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
        
        cursor.execute('SELECT * FROM telegram_signals ORDER BY received_at DESC LIMIT 100')
        rows = cursor.fetchall()
        signals = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'signals': signals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# VOTE RECORDS ENDPOINT
# ============================================

@app.route('/api/platform2/vote_records')
def api_vote_records():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        cursor.execute('SELECT * FROM supervisor_vote_records ORDER BY timestamp DESC LIMIT 100')
        rows = cursor.fetchall()
        votes = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'votes': votes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# AGENT ERRORS ENDPOINT
# ============================================

@app.route('/api/platform2/agent_errors')
def api_agent_errors():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        cursor.execute('SELECT * FROM agent_errors ORDER BY created_at DESC LIMIT 100')
        rows = cursor.fetchall()
        errors = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'errors': errors})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# TRAINING CYCLES ENDPOINT
# ============================================

@app.route('/api/platform2/training_cycles')
def api_training_cycles():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        cursor.execute('SELECT * FROM ml_training_cycles ORDER BY cycle_number DESC')
        rows = cursor.fetchall()
        cycles = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'cycles': cycles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# GATEKEEPER AUDIT ENDPOINT
# ============================================

@app.route('/api/platform2/gatekeeper_audit')
def api_gatekeeper_audit():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        cursor.execute('SELECT * FROM gatekeeper_full_audit ORDER BY timestamp DESC LIMIT 100')
        rows = cursor.fetchall()
        audits = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'audits': audits})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# COLLABORATION METRICS ENDPOINT
# ============================================

@app.route('/api/platform2/collaboration_metrics')
def api_collaboration_metrics():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consensus_percentage REAL,
                teamwork_score REAL,
                zero_error_contribution INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('SELECT * FROM collaboration_metrics ORDER BY timestamp DESC LIMIT 50')
        rows = cursor.fetchall()
        metrics = [dict(row) for row in rows]
        conn.close()
        return jsonify({'success': True, 'metrics': metrics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# CORRECT AGENT ERROR ENDPOINT
# ============================================

@app.route('/api/platform2/correct_agent_error', methods=['POST'])
def api_correct_agent_error():
    try:
        data = request.json
        error_id = data.get('error_id')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE agent_errors SET is_fixed = 1 WHERE id = ?', (error_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# START TRAINING ENDPOINT
# ============================================

@app.route('/api/platform2/start_training', methods=['POST'])
def api_start_training():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get next cycle number
        cursor.execute('SELECT COALESCE(MAX(cycle_number), 0) + 1 FROM ml_training_cycles')
        row = cursor.fetchone()
        new_cycle = row[0] if row else 1
        
        # Get agents with errors
        cursor.execute('SELECT DISTINCT agent_name FROM agent_errors WHERE is_fixed = 0')
        agent_rows = cursor.fetchall()
        agents = [row[0] for row in agent_rows]
        
        cursor.execute('''
            INSERT INTO ml_training_cycles (cycle_number, started_at, agents_trained, status)
            VALUES (?, ?, ?, ?)
        ''', (new_cycle, datetime.now().isoformat(), str(agents), 'RUNNING'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'cycle_number': new_cycle, 'agents': agents})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Create templates directory if needed
    import os
    os.makedirs('frontend/templates', exist_ok=True)
    
    print("\n" + "=" * 50)
    print("📊 Platform 2: Instructor Dashboard")
    print("=" * 50)
    print(f"URL: http://localhost:5000/platform2")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
