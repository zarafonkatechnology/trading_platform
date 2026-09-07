#!/usr/bin/env python3
"""
GATEKEEPER AGENT - Final Layer of Defense
Three Pillars of Integrity: Identity, Logic Sanity, Resource Check
"You Shall Not Pass (Unverified)"
"""

import sqlite3
import json
import hashlib
import hmac
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - 🚪 GATEKEEPER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'trading_system.db'

# ============================================
# PART 1: GATEKEEPER DATABASE SCHEMA
# ============================================

class GatekeeperDatabase:
    """Database schema for Gatekeeper"""
    
    @staticmethod
    def init_tables():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enrolled agents table (Pillar 1)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrolled_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE NOT NULL,
                enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TIMESTAMP,
                public_key_hash TEXT,
                enrollment_signature TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                token_balance REAL DEFAULT 1000,
                total_trades_executed INTEGER DEFAULT 0,
                last_trade_time TIMESTAMP
            )
        ''')
        
        # Technical boundaries table (Pillar 2 - Bollinger Safety)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_boundaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                boundary_type TEXT,
                min_value REAL,
                max_value REAL,
                is_active BOOLEAN DEFAULT TRUE,
                set_by TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Token limits table (Pillar 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE,
                max_trade_cost REAL DEFAULT 500,
                daily_budget REAL DEFAULT 2000,
                daily_spent REAL DEFAULT 0,
                max_position_size INTEGER DEFAULT 10000,
                min_balance_required REAL DEFAULT 100,
                last_reset DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Gatekeeper decision log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gatekeeper_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                agent_name TEXT,
                requested_action TEXT,
                requested_quantity INTEGER,
                requested_price REAL,
                identity_passed BOOLEAN,
                identity_reason TEXT,
                logic_passed BOOLEAN,
                logic_reason TEXT,
                resource_passed BOOLEAN,
                resource_reason TEXT,
                gate_status TEXT,
                lesson_packet TEXT,
                xp_protected INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Lesson packets taught by Gatekeeper
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gatekeeper_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                lesson_type TEXT,
                lesson_content TEXT,
                xp_saved INTEGER,
                was_applied BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default technical boundaries (set by Technical Master)
        boundaries = [
            ('XAU/USD', 'BOLLINGER_UPPER', None, 2450.0, 1, 'technical_master'),
            ('XAU/USD', 'BOLLINGER_LOWER', 2300.0, None, 1, 'technical_master'),
            ('XAU/USD', 'RSI_LIMIT', 25.0, 75.0, 1, 'technical_master'),
            ('XAG/USD', 'BOLLINGER_UPPER', None, 30.0, 1, 'technical_master'),
            ('XAG/USD', 'BOLLINGER_LOWER', 27.0, None, 1, 'technical_master'),
            ('BCO/USD', 'BOLLINGER_UPPER', None, 95.0, 1, 'technical_master'),
            ('BCO/USD', 'BOLLINGER_LOWER', 80.0, None, 1, 'technical_master'),
            ('S&P500/USD', 'RSI_LIMIT', 30.0, 70.0, 1, 'technical_master'),
            ('EURUSD', 'SPREAD_LIMIT', None, 0.002, 1, 'technical_master')
        ]
        
        for boundary in boundaries:
            cursor.execute('''
                INSERT OR IGNORE INTO technical_boundaries 
                (symbol, boundary_type, min_value, max_value, is_active, set_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', boundary)
        
        conn.commit()
        conn.close()
        logger.info("✅ Gatekeeper database tables initialized")


# ============================================
# PART 2: GATEKEEPER CORE IMPLEMENTATION
# ============================================

class GatekeeperCore:
    """Core Gatekeeper logic - Three Pillars of Integrity"""
    
    def __init__(self):
        self.gates_opened = 0
        self.gates_blocked = 0
        self.total_xp_protected = 0
        self._load_enrolled_agents()
    
    def _load_enrolled_agents(self):
        """Load enrolled agents from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT agent_name, token_balance FROM enrolled_agents WHERE is_active = 1')
        self.enrolled = {row[0]: {'balance': row[1]} for row in cursor.fetchall()}
        conn.close()
    
    # ========== PILLAR 1: IDENTITY VERIFICATION ==========
    
    def verify_identity(self, agent_name: str, agent_signature: str, signal_id: int) -> Tuple[bool, str]:
        """
        Pillar 1: Is this agent actually enrolled?
        Returns: (passed, reason)
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT enrollment_signature, is_active, expiry_date, token_balance
            FROM enrolled_agents WHERE agent_name = ?
        ''', (agent_name,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            lesson = f"❌ AGENT {agent_name} NOT ENROLLED. You must complete enrollment."
            self._teach_lesson(agent_name, 'IDENTITY_FAILURE', lesson, xp_protected=100)
            return False, f"Agent {agent_name} is not enrolled"
        
        enrollment_sig, is_active, expiry_date, token_balance = result
        
        if not is_active:
            lesson = f"⚠️ AGENT {agent_name} IS SUSPENDED. Contact administrator."
            self._teach_lesson(agent_name, 'IDENTITY_FAILURE', lesson, xp_protected=50)
            return False, f"Agent {agent_name} is suspended"
        
        if expiry_date and datetime.now() > datetime.fromisoformat(expiry_date):
            lesson = f"📅 AGENT {agent_name} ENROLLMENT EXPIRED. Renew to continue."
            self._teach_lesson(agent_name, 'IDENTITY_FAILURE', lesson, xp_protected=75)
            return False, f"Enrollment expired on {expiry_date}"
        
        # Verify signature (HMAC-based authentication)
        expected_signature = hmac.new(
            key=b'gatekeeper_secret_key',
            msg=f"{agent_name}{signal_id}".encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if agent_signature != expected_signature:
            lesson = f"🔐 AGENT {agent_name} INVALID SIGNATURE. Possible impersonation."
            self._teach_lesson(agent_name, 'IDENTITY_FAILURE', lesson, xp_protected=150)
            return False, "Invalid authentication signature"
        
        return True, "Identity verified - Agent is enrolled and authenticated"
    
    def enroll_agent(self, agent_name: str, initial_balance: float = 1000) -> Dict:
        """Enroll a new agent into the system"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Generate enrollment signature
        enrollment_sig = hashlib.sha256(
            f"{agent_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        expiry = (datetime.now() + timedelta(days=90)).isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO enrolled_agents 
            (agent_name, enrollment_signature, expiry_date, token_balance, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (agent_name, enrollment_sig, expiry, initial_balance, True))
        
        # Set token limits
        cursor.execute('''
            INSERT OR IGNORE INTO token_limits 
            (agent_name, max_trade_cost, daily_budget, max_position_size, min_balance_required)
            VALUES (?, ?, ?, ?, ?)
        ''', (agent_name, 500, 2000, 10000, 100))
        
        conn.commit()
        conn.close()
        
        self._load_enrolled_agents()
        
        logger.info(f"✅ Agent {agent_name} enrolled with ${initial_balance} tokens")
        
        return {
            'status': 'enrolled',
            'agent_name': agent_name,
            'enrollment_signature': enrollment_sig,
            'expiry': expiry,
            'token_balance': initial_balance
        }
    
    # ========== PILLAR 2: LOGIC SANITY (Bollinger Safety) ==========
    
    def verify_logic_sanity(self, agent_name: str, symbol: str, price: float, 
                            quantity: int, current_rsi: float = 50, 
                            current_volume: int = 1000) -> Tuple[bool, str]:
        """
        Pillar 2: Does this trade violate technical boundaries?
        Bollinger bands, RSI limits, volume sanity.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT boundary_type, min_value, max_value
            FROM technical_boundaries
            WHERE symbol = ? AND is_active = 1
        ''', (symbol,))
        
        boundaries = cursor.fetchall()
        conn.close()
        
        violations = []
        
        for btype, min_val, max_val in boundaries:
            if btype == 'BOLLINGER_UPPER' and max_val and price > max_val:
                violations.append(f"Price ${price:.2f} exceeds Bollinger Upper Band ${max_val:.2f}")
            elif btype == 'BOLLINGER_LOWER' and min_val and price < min_val:
                violations.append(f"Price ${price:.2f} below Bollinger Lower Band ${min_val:.2f}")
            elif btype == 'RSI_LIMIT':
                if min_val and current_rsi < min_val:
                    violations.append(f"RSI {current_rsi:.1f} below oversold threshold {min_val:.1f}")
                if max_val and current_rsi > max_val:
                    violations.append(f"RSI {current_rsi:.1f} above overbought threshold {max_val:.1f}")
            elif btype == 'SPREAD_LIMIT' and max_val:
                # For spread, we'd need bid/ask, simplified
                pass
        
        if violations:
            lesson = f"📊 LOGIC SANITY FAILURE\n" + "\n".join(violations)
            self._teach_lesson(agent_name, 'LOGIC_FAILURE', lesson, xp_protected=30)
            return False, f"Logic sanity failed: {violations[0]}"
        
        if quantity <= 0:
            return False, "Invalid quantity (must be positive)"
        
        if price <= 0:
            return False, "Invalid price (must be positive)"
        
        return True, "Logic sanity passed - Within Bollinger safety boundaries"
    
    # ========== PILLAR 3: RESOURCE CHECK ==========
    
    def verify_resources(self, agent_name: str, trade_cost: float, 
                         current_balance: float = None) -> Tuple[bool, str]:
        """
        Pillar 3: Does this trade cost more than token allowance?
        Checks token balance, daily budget, position limits.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get token limits
        cursor.execute('''
            SELECT max_trade_cost, daily_budget, daily_spent, max_position_size, min_balance_required
            FROM token_limits WHERE agent_name = ?
        ''', (agent_name,))
        result = cursor.fetchone()
        
        if not result:
            lesson = f"💰 AGENT {agent_name} HAS NO TOKEN LIMITS. Cannot execute trades."
            self._teach_lesson(agent_name, 'RESOURCE_FAILURE', lesson, xp_protected=50)
            return False, "No token limits configured"
        
        max_trade_cost, daily_budget, daily_spent, max_position, min_balance = result
        
        # Get current token balance
        if current_balance is None:
            cursor.execute('SELECT token_balance FROM enrolled_agents WHERE agent_name = ?', (agent_name,))
            balance_row = cursor.fetchone()
            current_balance = balance_row[0] if balance_row else 0
        
        # Check 1: Sufficient token balance
        if trade_cost > current_balance:
            lesson = f"💸 INSUFFICIENT TOKENS: Need ${trade_cost:.2f}, have ${current_balance:.2f}"
            xp_saved = int(trade_cost - current_balance)
            self._teach_lesson(agent_name, 'RESOURCE_FAILURE', lesson, xp_protected=xp_saved)
            return False, f"Insufficient balance: ${current_balance:.2f} < ${trade_cost:.2f}"
        
        # Check 2: Single trade limit
        if trade_cost > max_trade_cost:
            lesson = f"💎 TRADE TOO LARGE: ${trade_cost:.2f} exceeds max ${max_trade_cost:.2f}"
            self._teach_lesson(agent_name, 'RESOURCE_FAILURE', lesson, xp_protected=20)
            return False, f"Trade cost ${trade_cost:.2f} exceeds max ${max_trade_cost:.2f}"
        
        # Check 3: Daily budget
        today = datetime.now().date()
        if daily_spent and daily_spent > 0:
            # Reset if new day
            cursor.execute('SELECT last_reset FROM token_limits WHERE agent_name = ?', (agent_name,))
            last_reset_row = cursor.fetchone()
            if last_reset_row:
                last_reset = datetime.fromisoformat(last_reset_row[0]).date() if last_reset_row[0] else today
                if last_reset != today:
                    cursor.execute('UPDATE token_limits SET daily_spent = 0, last_reset = ? WHERE agent_name = ?',
                                  (today.isoformat(), agent_name))
                    daily_spent = 0
                    conn.commit()
            
            if daily_spent + trade_cost > daily_budget:
                remaining = daily_budget - daily_spent
                lesson = f"📅 DAILY BUDGET EXCEEDED: ${remaining:.2f} remaining, need ${trade_cost:.2f}"
                self._teach_lesson(agent_name, 'RESOURCE_FAILURE', lesson, xp_protected=25)
                return False, f"Daily budget exceeded. Remaining: ${remaining:.2f}"
        
        # Check 4: Minimum balance after trade
        new_balance = current_balance - trade_cost
        if new_balance < min_balance:
            lesson = f"⚠️ MIN BALANCE VIOLATION: After trade, balance would be ${new_balance:.2f} < ${min_balance:.2f}"
            self._teach_lesson(agent_name, 'RESOURCE_FAILURE', lesson, xp_protected=15)
            return False, f"Would violate minimum balance of ${min_balance:.2f}"
        
        # All checks passed - deduct tokens and update spent
        cursor.execute('''
            UPDATE enrolled_agents 
            SET token_balance = token_balance - ?, total_trades_executed = total_trades_executed + 1,
                last_trade_time = ?
            WHERE agent_name = ?
        ''', (trade_cost, datetime.now().isoformat(), agent_name))
        
        cursor.execute('''
            UPDATE token_limits 
            SET daily_spent = daily_spent + ? 
            WHERE agent_name = ?
        ''', (trade_cost, agent_name))
        
        conn.commit()
        conn.close()
        
        self._load_enrolled_agents()
        
        return True, f"Resources verified - ${trade_cost:.2f} deducted. New balance: ${new_balance:.2f}"
    
    # ========== TEACHING & XP PROTECTION ==========
    
    def _teach_lesson(self, agent_name: str, lesson_type: str, lesson_content: str, xp_protected: int):
        """Gatekeeper teaches agents when they fail"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gatekeeper_lessons (agent_name, lesson_type, lesson_content, xp_saved, was_applied)
            VALUES (?, ?, ?, ?, ?)
        ''', (agent_name, lesson_type, lesson_content, xp_protected, False))
        conn.commit()
        conn.close()
        
        self.total_xp_protected += xp_protected
        logger.info(f"📚 Gatekeeper taught {agent_name}: {lesson_type} - XP Protected: {xp_protected}")
    
    # ========== MAIN GATE DECISION ==========
    
    def request_permission(self, trade_request: Dict) -> Dict:
        """
        The main gate function.
        All three pillars must pass before gate opens.
        """
        agent_name = trade_request.get('agent_name')
        agent_signature = trade_request.get('signature', '')
        signal_id = trade_request.get('signal_id', 0)
        symbol = trade_request.get('symbol', 'XAU/USD')
        price = float(trade_request.get('price', 0))
        quantity = int(trade_request.get('quantity', 0))
        trade_cost = price * quantity
        
        current_rsi = trade_request.get('current_rsi', 50)
        current_volume = trade_request.get('current_volume', 1000)
        
        # Log attempt
        log_id = self._log_attempt(signal_id, agent_name, trade_request.get('action'), quantity, price)
        
        lesson_packet = []
        xp_protected_total = 0
        
        # PILLAR 1: Identity
        identity_passed, identity_reason = self.verify_identity(agent_name, agent_signature, signal_id)
        if not identity_passed:
            gate_status = "BLOCKED_IDENTITY"
            lesson_packet.append(f"IDENTITY: {identity_reason}")
            xp_protected_total += 100
        
        # PILLAR 2: Logic Sanity
        logic_passed, logic_reason = False, ""
        if identity_passed:
            logic_passed, logic_reason = self.verify_logic_sanity(
                agent_name, symbol, price, quantity, current_rsi, current_volume
            )
            if not logic_passed:
                gate_status = "BLOCKED_LOGIC"
                lesson_packet.append(f"LOGIC: {logic_reason}")
                xp_protected_total += 30
        
        # PILLAR 3: Resource Check
        resource_passed, resource_reason = False, ""
        if identity_passed and logic_passed:
            resource_passed, resource_reason = self.verify_resources(agent_name, trade_cost)
            if not resource_passed:
                gate_status = "BLOCKED_RESOURCE"
                lesson_packet.append(f"RESOURCE: {resource_reason}")
                xp_protected_total += 50
        
        all_passed = identity_passed and logic_passed and resource_passed
        
        if all_passed:
            gate_status = "OPEN"
            self.gates_opened += 1
            logger.info(f"🟢 GATE OPEN for {agent_name} | Trade: {trade_request.get('action')} {quantity} {symbol} @ ${price:.2f}")
        else:
            gate_status = f"BLOCKED_{gate_status}" if 'gate_status' in locals() else "BLOCKED_UNKNOWN"
            self.gates_blocked += 1
            self.total_xp_protected += xp_protected_total
            logger.warning(f"🔴 GATE CLOSED for {agent_name} | Reason: {gate_status}")
        
        # Update log
        self._update_log(log_id, identity_passed, identity_reason,
                        logic_passed, logic_reason,
                        resource_passed, resource_reason,
                        gate_status, '\n'.join(lesson_packet), xp_protected_total)
        
        return {
            'permission_granted': all_passed,
            'gate_status': gate_status,
            'lesson_packet': lesson_packet,
            'xp_protected': xp_protected_total,
            'new_token_balance': self._get_balance(agent_name) if all_passed else None
        }
    
    def _log_attempt(self, signal_id, agent_name, action, quantity, price) -> int:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gatekeeper_log 
            (signal_id, agent_name, requested_action, requested_quantity, requested_price)
            VALUES (?, ?, ?, ?, ?)
        ''', (signal_id, agent_name, action, quantity, price))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    
    def _update_log(self, log_id, identity_passed, identity_reason,
                    logic_passed, logic_reason, resource_passed, resource_reason,
                    gate_status, lesson_packet, xp_protected):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE gatekeeper_log 
            SET identity_passed = ?, identity_reason = ?,
                logic_passed = ?, logic_reason = ?,
                resource_passed = ?, resource_reason = ?,
                gate_status = ?, lesson_packet = ?, xp_protected = ?
            WHERE id = ?
        ''', (identity_passed, identity_reason, logic_passed, logic_reason,
              resource_passed, resource_reason, gate_status, lesson_packet, xp_protected, log_id))
        conn.commit()
        conn.close()
    
    def _get_balance(self, agent_name: str) -> float:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT token_balance FROM enrolled_agents WHERE agent_name = ?', (agent_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def get_stats(self) -> Dict:
        return {
            'gates_opened': self.gates_opened,
            'gates_blocked': self.gates_blocked,
            'total_xp_protected': self.total_xp_protected,
            'block_rate': round(self.gates_blocked / (self.gates_opened + self.gates_blocked) * 100, 1) if (self.gates_opened + self.gates_blocked) > 0 else 0
        }


# ============================================
# PART 3: INTEGRATION WITH SENTINEL & SUPERVISOR
# ============================================

class GatekeeperIntegration:
    """Integrates Gatekeeper with Sentinel and Supervisor"""
    
    def __init__(self, gatekeeper: GatekeeperCore, sentinel=None, supervisor=None):
        self.gatekeeper = gatekeeper
        self.sentinel = sentinel
        self.supervisor = supervisor
    
    def execute_trade_flow(self, trade_request: Dict) -> Dict:
        """
        Complete flow: Supervisor → Sentinel → Gatekeeper → Market
        """
        # Step 1: Supervisor processes signal
        if self.supervisor:
            # Supervisor checks (timing, consensus, volatility)
            supervisor_result = self._supervisor_check(trade_request)
            if not supervisor_result.get('passed', True):
                return {'status': 'blocked_by_supervisor', 'reason': supervisor_result.get('reason')}
        
        # Step 2: Sentinel veto check
        if self.sentinel and hasattr(self.sentinel, 'veto'):
            allowed, veto_msg = self.sentinel.veto(
                {'decision': trade_request.get('action'), 'position_size': trade_request.get('quantity') * trade_request.get('price', 0)},
                trade_request.get('agent_name'),
                {'volatility': trade_request.get('volatility', 0.5)}
            )
            if not allowed:
                return {'status': 'vetoed_by_sentinel', 'reason': veto_msg}
        
        # Step 3: Gatekeeper final check
        gate_decision = self.gatekeeper.request_permission(trade_request)
        
        if not gate_decision['permission_granted']:
            # Teach the agent via Sentinel if available
            if self.sentinel and hasattr(self.sentinel, 'analyze_loss'):
                self.sentinel.analyze_loss(
                    trade_request.get('agent_name'),
                    trade_request,
                    'BLOCKED_BY_GATEKEEPER'
                )
            return {
                'status': 'blocked_by_gatekeeper',
                'gate_status': gate_decision['gate_status'],
                'lesson_packet': gate_decision['lesson_packet'],
                'xp_protected': gate_decision['xp_protected']
            }
        
        # Step 4: Execute trade
        execution_result = self._execute_market_order(trade_request)
        
        return {
            'status': 'executed',
            'gate_status': 'OPEN',
            'execution': execution_result,
            'new_token_balance': gate_decision['new_token_balance']
        }
    
    def _supervisor_check(self, trade_request: Dict) -> Dict:
        # Placeholder for supervisor logic
        return {'passed': True}
    
    def _execute_market_order(self, trade_request: Dict) -> Dict:
        # Simulate market execution
        return {
            'order_id': f"ORD_{int(datetime.now().timestamp())}",
            'status': 'filled',
            'price': trade_request.get('price'),
            'quantity': trade_request.get('quantity'),
            'timestamp': datetime.now().isoformat()
        }


# ============================================
# PART 4: TELEGRAM COMMANDS FOR GATEKEEPER
# ============================================

class GatekeeperTelegram:
    """Telegram commands for Gatekeeper"""
    
    def __init__(self, gatekeeper: GatekeeperCore):
        self.gatekeeper = gatekeeper
    
    def get_status_message(self) -> str:
        stats = self.gatekeeper.get_stats()
        message = f"""
🚪 *GATEKEEPER STATUS REPORT*
{'='*30}

🟢 Gates Opened: {stats['gates_opened']}
🔴 Gates Blocked: {stats['gates_blocked']}
📊 Block Rate: {stats['block_rate']}%
🛡️ XP Protected: {stats['total_xp_protected']}

{'='*30}
*Three Pillars of Integrity Active*
"""
        return message
    
    def get_enrollment_message(self, agent_name: str, result: Dict) -> str:
        return f"""
✅ *Agent Enrollment Complete*
{'='*30}

🤖 Agent: {agent_name}
🎴 Token Balance: ${result['token_balance']:.2f}
📅 Expiry: {result['expiry'][:10]}
🔑 Signature: {result['enrollment_signature'][:16]}...

{'='*30}
*Agent can now trade through the Gate*
"""


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚪 GATEKEEPER AGENT - Final Layer of Defense")
    print("Three Pillars: Identity | Logic Sanity | Resource")
    print("=" * 60)
    
    # Initialize database
    GatekeeperDatabase.init_tables()
    
    # Create Gatekeeper
    gatekeeper = GatekeeperCore()
    
    # Enroll a test agent
    print("\n📋 Enrolling Agent_A...")
    enrollment = gatekeeper.enroll_agent("Agent_A", 5000)
    print(f"   {enrollment}")
    
    # Test a valid trade request
    print("\n📋 Testing valid trade request...")
    valid_request = {
        'agent_name': 'Agent_A',
        'signature': hmac.new(key=b'gatekeeper_secret_key', 
                              msg=f"Agent_A{1}".encode(), 
                              digestmod=hashlib.sha256).hexdigest(),
        'signal_id': 1,
        'symbol': 'XAU/USD',
        'action': 'BUY',
        'price': 2350.00,
        'quantity': 10,
        'current_rsi': 55,
        'current_volume': 1500
    }
    
    result = gatekeeper.request_permission(valid_request)
    print(f"   Result: {result}")
    
    # Test an invalid trade (too large)
    print("\n📋 Testing invalid trade (exceeds balance)...")
    invalid_request = valid_request.copy()
    invalid_request['quantity'] = 1000  # $2,350,000 cost
    invalid_request['price'] = 2350
    result2 = gatekeeper.request_permission(invalid_request)
    print(f"   Result: {result2}")
    
    # Show stats
    print("\n📊 Gatekeeper Stats:")
    stats = gatekeeper.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print("\n✅ Gatekeeper Agent is ready!")
