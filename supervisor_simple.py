#!/usr/bin/env python3
"""
Simple Supervisor - Working Version
"""

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = 'trading_system.db'

class SimpleSupervisor:
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supervisor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                error_type TEXT,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def handle_timing_error(self, signal_id, agent_name, delay_ms):
        print(f"⚠️ Timing Error: {agent_name} delayed {delay_ms}ms")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO supervisor_log (signal_id, error_type, action, details)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, 'TIMING_ERROR', 'REDUCE_CONFIDENCE', f'Delay: {delay_ms}ms'))
        conn.commit()
        conn.close()
        
        return {'status': 'corrected', 'penalty': 0.7}
    
    def handle_consensus_failure(self, signal_id, votes):
        buy = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        
        decision = 'BUY' if buy > sell else 'SELL'
        print(f"⚠️ Consensus Failure: BUY={buy}, SELL={sell} → Override to {decision}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO supervisor_log (signal_id, error_type, action, details)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, 'CONSENSUS_FAILURE', 'SUPERVISOR_OVERRIDE', f'Final decision: {decision}'))
        conn.commit()
        conn.close()
        
        return {'status': 'corrected', 'decision': decision}
    
    def handle_volatility_error(self, signal_id, volatility):
        if volatility > 2.0:
            print(f"⚠️ High Volatility: {volatility}% → Reducing position size")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO supervisor_log (signal_id, error_type, action, details)
                VALUES (?, ?, ?, ?)
            ''', (signal_id, 'HIGH_VOLATILITY', 'REDUCE_POSITION', f'Volatility: {volatility}%'))
            conn.commit()
            conn.close()
            
            return {'status': 'risk_reduced', 'multiplier': 0.5}
        
        return {'status': 'normal'}

# Test
if __name__ == '__main__':
    print("=" * 50)
    print("TESTING SUPERVISOR")
    print("=" * 50)
    
    sup = SimpleSupervisor()
    
    # Test timing error
    sup.handle_timing_error(1, 'Agent_A', 6000)
    
    # Test consensus failure
    votes = {'Agent_A': {'vote': 'BUY'}, 'Agent_B': {'vote': 'SELL'}, 
             'Agent_C': {'vote': 'BUY'}, 'Agent_D': {'vote': 'SELL'}, 
             'Agent_E': {'vote': 'BUY'}}
    sup.handle_consensus_failure(2, votes)
    
    # Test volatility error
    sup.handle_volatility_error(3, 3.5)
    
    print("\n✅ Supervisor test complete")
