#!/usr/bin/env python3
"""
SENTINEL AGENT - Simplified Working Version
"""

import sqlite3
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - 🔷 SENTINEL - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'trading_system.db'

class SimpleSentinel:
    """Simplified working Sentinel"""
    
    def __init__(self):
        self.veto_count = 0
        self.zero_error_count = 0
        self.start_time = datetime.now()
        self._init_tables()
        logger.info("🔷 SENTINEL ACTIVATED - Zero Error Enforcer")
    
    def _init_tables(self):
        """Initialize Sentinel tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentinel_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                agent TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loss_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                lesson TEXT,
                taught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Sentinel tables ready")
    
    def veto(self, decision: Dict, agent: str, context: Dict) -> Tuple[bool, str]:
        """Veto power - block bad decisions"""
        
        # Check 1: Position size too large
        if decision.get('position_size', 0) > 25000:
            self.veto_count += 1
            self._log("VETO", agent, "Position size exceeds limit")
            return False, f"❌ VETO: Position size {decision.get('position_size')} exceeds limit"
        
        # Check 2: Extreme confidence with no confirmation
        if decision.get('confidence', 0) > 95:
            self.veto_count += 1
            self._log("VETO", agent, "Extreme confidence without confirmation")
            return False, "❌ VETO: Extreme confidence without technical confirmation"
        
        # Check 3: Market too volatile
        if context.get('volatility', 0) > 5:
            self.veto_count += 1
            self._log("VETO", agent, f"High volatility: {context.get('volatility')}%")
            return False, f"❌ VETO: Market too volatile ({context.get('volatility')}%)"
        
        return True, "✅ PASSED: All checks cleared"
    
    def analyze_loss(self, agent: str, trade_data: Dict, outcome: str) -> str:
        """Analyze why we lost and teach the agent"""
        
        lesson = None
        
        if outcome == 'LOSS':
            price = trade_data.get('current_price', 0)
            decision = trade_data.get('decision', 'UNKNOWN')
            
            if decision == 'BUY' and trade_data.get('actual_move', 0) < 0:
                lesson = "Lesson: Check bearish indicators before BUY. Wait for confirmation."
            elif decision == 'SELL' and trade_data.get('actual_move', 0) > 0:
                lesson = "Lesson: Check bullish indicators before SELL. Wait for breakout."
            else:
                lesson = "Lesson: Review entry timing and risk management."
            
            # Store lesson
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO loss_lessons (agent_name, lesson)
                VALUES (?, ?)
            ''', (agent, lesson))
            conn.commit()
            conn.close()
            
            logger.info(f"📚 Taught {agent}: {lesson[:50]}...")
            self.zero_error_count += 1
        
        return lesson
    
    def get_status(self) -> Dict:
        """Get Sentinel status"""
        uptime = (datetime.now() - self.start_time).total_seconds() / 60
        return {
            'veto_count': self.veto_count,
            'zero_errors': self.zero_error_count,
            'uptime_minutes': round(uptime, 1),
            'status': 'ACTIVE',
            'legendary': self.veto_count > 0 and self.zero_error_count > 0
        }
    
    def _log(self, action: str, agent: str, reason: str):
        """Log to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sentinel_log (action, agent, reason)
            VALUES (?, ?, ?)
        ''', (action, agent, reason))
        conn.commit()
        conn.close()
    
    def _check_db_health(self) -> bool:
        """Check database health"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True
        except:
            return False

# Test
if __name__ == '__main__':
    print("=" * 50)
    print("TESTING SIMPLE SENTINEL")
    print("=" * 50)
    
    sentinel = SimpleSentinel()
    
    # Test 1: Veto bad trade
    bad_trade = {'decision': 'BUY', 'confidence': 98, 'position_size': 50000}
    allowed, msg = sentinel.veto(bad_trade, 'Agent_A', {'volatility': 0.5})
    print(f"Bad trade: {msg}")
    
    # Test 2: Allow good trade
    good_trade = {'decision': 'BUY', 'confidence': 75, 'position_size': 5000}
    allowed, msg = sentinel.veto(good_trade, 'Agent_A', {'volatility': 0.5})
    print(f"Good trade: {msg}")
    
    # Test 3: Analyze loss
    trade_data = {'current_price': 2350, 'decision': 'BUY', 'actual_move': -2.5}
    lesson = sentinel.analyze_loss('Agent_A', trade_data, 'LOSS')
    print(f"Loss analysis: {lesson}")
    
    # Test 4: Get status
    status = sentinel.get_status()
    print(f"\nSentinel Status: {status}")
    
    print("\n✅ Sentinel is ready!")
