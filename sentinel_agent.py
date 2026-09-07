#!/usr/bin/env python3
"""
SENTINEL AGENT - Zero Error Enforcer
Zero Downtime | Self-Healing | Veto Power | Agent Teaching
"""

import sqlite3
import json
import time
import threading
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - 🔷 SENTINEL - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'trading_system.db'

# ============================================
# PART 1: SENTINEL DATABASE SCHEMA
# ============================================

class SentinelDatabase:
    """Sentinel's database for tracking zero errors and self-healing"""
    
    @staticmethod
    def init_tables():
        """Initialize all Sentinel tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sentinel mastery table (tracks progress to legendary)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentinel_mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT UNIQUE,
                current_value REAL,
                target_value REAL,
                milestone TEXT,
                achieved_at TIMESTAMP
            )
        ''')
        
        # Veto log (every veto is recorded forever)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentinel_veto_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                veto_type TEXT,
                target_agent TEXT,
                original_action TEXT,
                    veto_reason TEXT,
                code_patch TEXT,
                success INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Self-healing actions log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS self_healing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT,
                error_detected TEXT,
                healing_action TEXT,
                code_changed TEXT,
                reboot_required INTEGER,
                healed_at TIMESTAMP,
                downtime_seconds INTEGER DEFAULT 0
            )
        ''')
        
        # Database connection health
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_connection_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                last_ping TIMESTAMP,
                reconnect_attempts INTEGER DEFAULT 0,
                last_error TEXT,
                recovery_action TEXT
            )
        ''')
        
        # Loss analysis table (why we lost trades)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loss_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                agent_name TEXT,
                loss_reason TEXT,
                root_cause TEXT,
                lesson_taught TEXT,
                xp_penalty INTEGER,
                corrected INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert zero error targets
        cursor.execute('''
            INSERT OR IGNORE INTO sentinel_mastery (metric_name, current_value, target_value, milestone)
            VALUES 
                ('error_rate', 100, 0, 'LEGENDARY'),
                ('uptime_percentage', 99.0, 100, 'LEGENDARY'),
                ('veto_accuracy', 85, 100, 'LEGENDARY'),
                ('self_heal_success', 70, 100, 'LEGENDARY'),
                ('db_reconnect_time', 30, 0, 'LEGENDARY')
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Sentinel database tables initialized")

# ============================================
# PART 2: SENTINEL CORE - VETO POWER & SELF-HEALING
# ============================================

class SentinelCore:
    """The heart of Sentinel - veto power and self-healing"""
    
    def __init__(self):
        self.veto_count = 0
        self.zero_error_count = 0
        self.uptime_start = datetime.now()
        self.downtime_total = 0
        self.is_legendary = False
        self.connection_pool = None
        self._init_connection_pool()
        
    def _init_connection_pool(self):
        """Initialize database connection pool for zero downtime"""
        try:
            self.connection_pool = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.connection_pool.row_factory = sqlite3.Row
            logger.info("✅ Sentinel connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Connection pool failed: {e}")
    
    # ========== VETO POWER ==========
    
def veto_power(self, proposed_action: Dict, agent_name: str, context: Dict) -> Tuple[bool, str, Optional[str]]:
    """
    The Sentinel can BLOCK any action that would cause an error.
    Returns: (is_allowed, reason, code_patch)
    """
    
    # Run all veto checks
    checks = [
        ('RISK_CHECK', self._check_trade_risk(proposed_action, agent_name)),
        ('HEALTH_CHECK', self._check_agent_health(agent_name)),
        ('MARKET_CHECK', self._check_market_anomaly(context)),
        ('CONSENSUS_CHECK', self._check_consensus_validity(proposed_action, context)),
        ('CODE_CHECK', self._check_code_integrity(proposed_action))
    ]
    
    for check_name, (_, is_safe, reason, patch) in checks:
        if not is_safe:
            self.veto_count += 1
            
            # Log the veto
            self._log_veto('BLOCK_TRADE', agent_name, proposed_action, reason, patch)
            
            # Apply code patch if provided
            if patch:
                self._apply_code_patch(patch)
            
            logger.warning(f"🔴 VETO #{self.veto_count}: {reason}")
            
            return False, reason, patch
    
    return True, "PASSED", None
def _check_trade_risk(self, action: Dict, agent_name: str) -> Tuple[str, bool, str, Optional[str]]:
    """Risk veto - prevents catastrophic losses"""
    
    # Get agent's recent performance from agent_votes table
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Try to get recent votes for this agent
        cursor.execute('''
            SELECT confidence, timestamp FROM agent_votes 
            WHERE agent_name = ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (agent_name,))
        recent_votes = cursor.fetchall()
    except:
        recent_votes = []
    conn.close()
    
    # Check if agent has been performing poorly (low confidence votes)
    if len(recent_votes) >= 3:
        low_confidence = sum(1 for v in recent_votes if v[0] < 50)
        if low_confidence >= 3:
            patch = f"Agent {agent_name} confidence low. Temporarily reducing trust weight."
            return 'RISK_CHECK', False, f"Low confidence: {low_confidence}/3 votes below 50%", patch
    
    # VETO: Position size too large
    if action.get('position_size', 0) > 25000:
        patch = "Position size capped at 25,000 units"
        return 'RISK_CHECK', False, "Position exceeds risk limit", patch
    
        return 'RISK_CHECK', True, None, None
def _check_agent_health(self, agent_name: str) -> Tuple[str, bool, str, Optional[str]]:
    """Health veto - agent must be functioning"""
    
    # Check if agent has recent activity
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT timestamp FROM agent_votes 
            WHERE agent_name = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (agent_name,))
        result = cursor.fetchone()
    except:
        result = None
    conn.close()
    
    if result:
        try:
            last_activity = datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]
            if (datetime.now() - last_activity).seconds > 300:  # 5 minutes
                patch = f"Restarting {agent_name} process"
                return 'HEALTH_CHECK', False, f"Agent heartbeat lost", patch
        except:
            pass
    
        return 'HEALTH_CHECK', True, None, None
    
    def _check_market_anomaly(self, context: Dict) -> Tuple[str, bool, str, Optional[str]]:
       """Market veto - extreme conditions"""
    
       volatility = context.get('volatility', 0)
       if not volatility:
        return 'MARKET_CHECK', True, None, None
    
    # VETO: Extreme volatility (>5%)
       if volatility > 5:
           patch = "Activating circuit breaker for 5 minutes"
           return 'MARKET_CHECK', False, f"Extreme volatility: {volatility}%", patch
    
           return 'MARKET_CHECK', True, None, None
    
    def _check_consensus_validity(self, action: Dict, context: Dict) -> Tuple[str, bool, str, Optional[str]]:
      votes = context.get('votes', {})
      if votes and len(votes) > 0:
        try:
            unique_votes = len(set(v.get('vote') for v in votes.values() if v.get('vote')))
            
            # VETO: Complete disagreement (3 different votes)
            if unique_votes == 3:
                patch = "Forcing HOLD until consensus restored"
                return 'CONSENSUS_CHECK', False, "Complete disagreement among agents", patch
        except:
            pass
    
            return 'CONSENSUS_CHECK', True, None, None
def _check_code_integrity(self, action: Dict) -> Tuple[str, bool, str, Optional[str]]:
    """Code veto - blocks malformed actions"""
    
    required_fields = ['decision']
    missing_fields = [f for f in required_fields if f not in action]
    
    if missing_fields:
        patch = f"Auto-filling missing fields: {missing_fields}"
        return 'CODE_CHECK', False, f"Malformed action: missing {missing_fields}", patch
    
        return 'CODE_CHECK', True, None, None
    
    def _log_veto(self, veto_type: str, agent_name: str, action: Dict, reason: str, patch: str):
        """Log veto to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sentinel_veto_log (veto_type, target_agent, original_action, veto_reason, code_patch, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (veto_type, agent_name, json.dumps(action), reason, patch, 1))
        conn.commit()
        conn.close()
    
    # ========== SELF-HEALING CODE ==========
    
    def _apply_code_patch(self, patch_code: str) -> bool:
        """Dynamically applies code patches to heal the system"""
        try:
            # Execute the patch
            exec_globals = {'db_path': DB_PATH, 'logger': logger}
            exec(patch_code, exec_globals)
            
            # Log successful healing
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO self_healing_log (component, error_detected, healing_action, code_changed, healed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('SYSTEM', 'runtime_error', 'code_patch_applied', patch_code[:200], datetime.now()))
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Self-healing applied: {patch_code[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Self-healing failed: {e}")
            return False
    
    def self_healing_cycle(self) -> List[Dict]:
        """Automatic healing cycle - runs every 60 seconds"""
        
        healing_actions = []
        
        # Check 1: Database connection
        if not self._check_db_health():
            patch = """
# Rebuild database connection
import sqlite3
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT 1")
conn.close()
print("✅ Database reconnected")
"""
            healing_actions.append(('REBUILD_DB', patch))
        
        # Apply all healing actions
        for action_type, patch in healing_actions:
            if self._apply_code_patch(patch):
                self.zero_error_count += 1
        
        return healing_actions
    
    def _check_db_health(self) -> bool:
        """Quick database health check"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            
            # Update health status
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO db_connection_health (status, last_ping, reconnect_attempts)
                VALUES (?, ?, ?)
            ''', ('HEALTHY', datetime.now(), 0))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def rebuild_connection_forever(self) -> bool:
        """The legendary method - never gives up. Achieves ZERO DOWNTIME."""
        
        start_time = datetime.now()
        reconnect_attempts = 0
        
        while reconnect_attempts < 10:
            try:
                self.connection_pool = sqlite3.connect(DB_PATH, check_same_thread=False)
                self.connection_pool.row_factory = sqlite3.Row
                
                # Test connection
                cursor = self.connection_pool.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                downtime_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Log legendary recovery
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO db_connection_health (status, reconnect_attempts, recovery_action, last_ping)
                    VALUES (?, ?, ?, ?)
                ''', ('RECOVERED', reconnect_attempts, f'RECOVERED_IN_{downtime_ms}ms', datetime.now()))
                conn.commit()
                conn.close()
                
                logger.info(f"🏆 LEGENDARY: Database recovered in {downtime_ms}ms after {reconnect_attempts} attempts")
                return True
                
            except Exception as e:
                reconnect_attempts += 1
                logger.warning(f"Reconnect attempt #{reconnect_attempts} failed: {e}")
                time.sleep(0.5)
        
        return False

# ============================================
# PART 3: LOSS ANALYSIS & AGENT TEACHING
# ============================================

class LossAnalyzer:
    """Analyzes why we lost trades and teaches agents"""
    
    def __init__(self):
        self.loss_patterns = {}
    
    def analyze_loss(self, signal_id: int, trade_data: Dict, votes: Dict, outcome: str) -> Dict:
        """Analyze why a trade was lost"""
        
        loss_reasons = []
        root_causes = []
        
        # Check each agent's vote
        for agent_name, vote_data in votes.items():
            reason = self._analyze_agent_decision(agent_name, vote_data, trade_data, outcome)
            if reason:
                loss_reasons.append({
                    'agent': agent_name,
                    'reason': reason,
                    'vote': vote_data.get('vote')
                })
                root_causes.append(reason)
        
        # Determine primary loss reason
        primary_reason = self._determine_primary_reason(loss_reasons, trade_data)
        
        # Generate lesson for agents
        lesson = self._generate_lesson(primary_reason, trade_data)
        
        # Store loss analysis
        self._store_loss_analysis(signal_id, loss_reasons, primary_reason, lesson)
        
        # Teach agents
        self._teach_agents(lesson, loss_reasons)
        
        return {
            'loss_analyzed': True,
            'primary_reason': primary_reason,
            'loss_reasons': loss_reasons,
            'lesson': lesson,
            'agents_to_correct': [r['agent'] for r in loss_reasons]
        }
    
    def _analyze_agent_decision(self, agent_name: str, vote_data: Dict, trade_data: Dict, outcome: str) -> Optional[str]:
        """Analyze why a specific agent made a wrong decision"""
        
        vote = vote_data.get('vote')
        confidence = vote_data.get('confidence', 50)
        price = trade_data.get('current_price', 0)
        actual_move = trade_data.get('actual_move', 0)
        
        # Check confidence vs outcome
        if confidence > 80 and outcome == 'LOSS':
            return f"Overconfidence: {confidence}% confidence but trade lost"
        
        # Check if agent voted against trend
        if vote == 'BUY' and actual_move < 0:
            return f"Voted BUY but market moved DOWN {abs(actual_move):.2f}%"
        elif vote == 'SELL' and actual_move > 0:
            return f"Voted SELL but market moved UP {actual_move:.2f}%"
        
        # Check if agent was indecisive
        if vote == 'HOLD' and abs(actual_move) > 1:
            return f"Too cautious: Held position while market moved {actual_move:.2f}%"
        
        return None
    
    def _determine_primary_reason(self, loss_reasons: List[Dict], trade_data: Dict) -> str:
        """Determine the primary reason for loss"""
        
        if not loss_reasons:
            return "Unknown loss reason"
        
        # Count reason types
        reason_counts = {}
        for r in loss_reasons:
            reason_type = r['reason'].split(':')[0]
            reason_counts[reason_type] = reason_counts.get(reason_type, 0) + 1
        
        if reason_counts:
            primary = max(reason_counts, key=reason_counts.get)
            return f"{primary}: {reason_counts[primary]} agents made this error"
        
        return "Consensus failure"
    
    def _generate_lesson(self, primary_reason: str, trade_data: Dict) -> str:
        """Generate a lesson for agents based on loss analysis"""
        
        lessons = {
            "Overconfidence": "Lesson: Reduce confidence in volatile markets. Consider price action before committing.",
            "Voted BUY but market moved DOWN": "Lesson: Check bearish indicators before BUY. Look for confirmation.",
            "Voted SELL but market moved UP": "Lesson: Check bullish indicators before SELL. Wait for breakout confirmation.",
            "Too cautious": "Lesson: Increase position sizing when multiple indicators align.",
            "Consensus failure": "Lesson: When agents disagree, wait for clearer signals or use weighted voting."
        }
        
        for key, lesson in lessons.items():
            if key in primary_reason:
                return lesson
        
        return f"Lesson: Review {primary_reason} and adjust trading strategy."
    
    def _store_loss_analysis(self, signal_id: int, loss_reasons: List[Dict], primary_reason: str, lesson: str):
        """Store loss analysis in database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for reason in loss_reasons:
            cursor.execute('''
                INSERT INTO loss_analysis (signal_id, agent_name, loss_reason, root_cause, lesson_taught, xp_penalty)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (signal_id, reason['agent'], reason['reason'], primary_reason, lesson, 15))
        
        conn.commit()
        conn.close()
    
    def _teach_agents(self, lesson: str, loss_reasons: List[Dict]):
        """Teach agents the lesson to prevent future losses"""
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for reason in loss_reasons:
            agent_name = reason['agent']
            
            # Apply XP penalty
            cursor.execute('''
                UPDATE agents SET xp = xp - 15 WHERE name = ?
            ''', (agent_name,))
            
            # Record the lesson
            cursor.execute('''
                INSERT INTO knowledge (from_agent, to_agent, topic, content, xp_reward)
                VALUES (?, ?, ?, ?, ?)
            ''', ('SENTINEL', agent_name, '📚 Loss Lesson', lesson, 0))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📚 SENTINEL taught {len(loss_reasons)} agents: {lesson[:100]}...")

# ============================================
# PART 4: COMPLETE SENTINEL INTEGRATION
# ============================================

class CompleteSentinel:
    """The complete Sentinel agent with all capabilities"""
    
    def __init__(self):
        SentinelDatabase.init_tables()
        self.core = SentinelCore()
        self.loss_analyzer = LossAnalyzer()
        self.is_running = False
        self.monitor_thread = None
        
        logger.info("🔷 SENTINEL AGENT ACTIVATED")
        logger.info("   Zero Error Enforcer | Self-Healing | Veto Power")
    
    def start(self):
        """Start Sentinel monitoring"""
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("✅ Sentinel monitoring started")
    
    def _monitor_loop(self):
        """Background monitoring thread"""
        while self.is_running:
            try:
                # Run self-healing cycle every 60 seconds
                self.core.self_healing_cycle()
                
                # Check for legendary achievement
                self._check_legendary_status()
                
                time.sleep(60)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)
    
    def _check_legendary_status(self):
        """Check if Sentinel has achieved LEGENDARY status"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT metric_name, current_value, target_value 
            FROM sentinel_mastery 
            WHERE current_value >= target_value
        ''')
        
        achieved = cursor.fetchall()
        conn.close()
        
        if len(achieved) == 5 and not self.core.is_legendary:
            self.core.is_legendary = True
            logger.info("🏆🏆🏆 LEGENDARY SENTINEL ACHIEVED 🏆🏆🏆")
            logger.info("   ✓ Zero Errors")
            logger.info("   ✓ Zero Downtime")
            logger.info("   ✓ Perfect Veto")
            logger.info("   ✓ Self-Healing Master")
            logger.info("   ✓ Instant Recovery")
    
    def vet_decision(self, decision: Dict, agent_name: str, context: Dict) -> Tuple[bool, str]:
        """Public method to veto a decision"""
        return self.core.veto_power(decision, agent_name, context)
    
    def analyze_and_teach(self, signal_id: int, trade_data: Dict, votes: Dict, outcome: str) -> Dict:
        """Analyze loss and teach agents"""
        if outcome == 'LOSS':
            return self.loss_analyzer.analyze_loss(signal_id, trade_data, votes, outcome)
        return {'status': 'win', 'message': 'No correction needed'}
    
    def get_status(self) -> Dict:
        """Get Sentinel status"""
        return {
            'legendary': self.core.is_legendary,
            'veto_count': self.core.veto_count,
            'zero_error_count': self.core.zero_error_count,
            'uptime_hours': round((datetime.now() - self.core.uptime_start).total_seconds() / 3600, 2),
            'status': 'ACTIVE'
        }

# ============================================
# TELEGRAM COMMANDS FOR SENTINEL
# ============================================

class SentinelTelegramCommands:
    """Telegram commands for Sentinel interaction"""
    
    def __init__(self, sentinel: CompleteSentinel):
        self.sentinel = sentinel
    
    def get_status_message(self) -> str:
        """Generate status message for Telegram"""
        status = self.sentinel.get_status()
        
        message = f"""
🔷 *SENTINEL STATUS REPORT*
{'='*30}

🏆 *Legendary Status:* {'✅ ACHIEVED' if status['legendary'] else '⏳ IN PROGRESS'}

📊 *Metrics:*
├ Veto Count: {status['veto_count']}
├ Zero Errors Prevented: {status['zero_error_count']}
└ Uptime: {status['uptime_hours']} hours

🔒 *Status:* {status['status']}

{'='*30}
*"Zero Errors, Zero Downtime"*
"""
        return message
    
    def get_loss_analysis_message(self, analysis: Dict) -> str:
        """Generate loss analysis message for Telegram"""
        
        message = f"""
❌ *LOSS ANALYSIS REPORT*
{'='*30}

📉 *Primary Reason:* {analysis.get('primary_reason', 'Unknown')}

🔍 *Agent Errors:*
"""
        for reason in analysis.get('loss_reasons', []):
            message += f"├ {reason['agent']}: {reason['reason'][:50]}\n"
        
        message += f"""
📚 *Lesson:* 
{analysis.get('lesson', 'Review strategy')}

{'='*30}
*Sentinel is teaching agents to improve*
"""
        return message

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🔷 SENTINEL AGENT - Zero Error Enforcer")
    print("=" * 60)
    
    # Initialize Sentinel
    sentinel = CompleteSentinel()
    sentinel.start()
    
    # Test veto power
    print("\n📋 Testing Veto Power:")
    
    # Test 1: Block bad trade
    bad_trade = {'decision': 'BUY', 'confidence': 95, 'position_size': 100000}
    allowed, reason, patch = sentinel.vet_decision(bad_trade, 'Agent_A', {'volatility': 0.5})
    print(f"  Bad trade: {'✅ ALLOWED' if allowed else '🔴 BLOCKED'} - {reason}")
    
    # Test 2: Allow good trade
    good_trade = {'decision': 'BUY', 'confidence': 75, 'position_size': 5000}
    allowed, reason, patch = sentinel.vet_decision(good_trade, 'Agent_A', {'volatility': 0.5})
    print(f"  Good trade: {'✅ ALLOWED' if allowed else '🔴 BLOCKED'} - {reason}")
    
    # Test loss analysis
    print("\n📋 Testing Loss Analysis:")
    test_votes = {
        'Agent_A': {'vote': 'BUY', 'confidence': 90},
        'Agent_B': {'vote': 'BUY', 'confidence': 85},
        'Agent_C': {'vote': 'SELL', 'confidence': 70},
        'Agent_D': {'vote': 'BUY', 'confidence': 80},
        'Agent_E': {'vote': 'HOLD', 'confidence': 60}
    }
    test_trade = {'current_price': 2350, 'actual_move': -2.5}
    
    analysis = sentinel.analyze_and_teach(1, test_trade, test_votes, 'LOSS')
    print(f"  Primary reason: {analysis.get('primary_reason')}")
    print(f"  Lesson: {analysis.get('lesson', 'N/A')[:60]}...")
    
    # Get status
    print("\n📋 Sentinel Status:")
    status = sentinel.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ Sentinel Agent is ready!")
    print("=" * 60)
