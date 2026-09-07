#!/usr/bin/env python3
"""
Test script for add_demo_agent endpoint
"""

import sqlite3
import re
import json
from flask import Flask, jsonify

app = Flask(__name__)

DB_PATH = 'trading_system.db'

@app.route('/test_add_agent', methods=['POST'])
def test_add_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists, create if not
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE,
                agent_type TEXT,
                specialization TEXT,
                xp_points INTEGER DEFAULT 0,
                token_balance INTEGER DEFAULT 1000,
                trust_weight REAL DEFAULT 0.2,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get last agent
        cursor.execute("SELECT agent_name FROM core_agents ORDER BY agent_name DESC LIMIT 1")
        last = cursor.fetchone()
        
        if last:
            last_name = last[0]
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
            INSERT INTO core_agents (agent_name, agent_type, specialization)
            VALUES (?, ?, ?)
        ''', (new_name, 'Demo Agent', 'Testing'))
        
        conn.commit()
        
        # Get all agents to verify
        cursor.execute('SELECT agent_name FROM core_agents')
        all_agents = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'agent_name': new_name,
            'all_agents': all_agents
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("Test server running on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
