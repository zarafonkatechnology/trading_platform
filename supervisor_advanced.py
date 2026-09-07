#!/usr/bin/env python3
"""
Advanced Supervisor System - Batch Management, Error Correction, Market State Analysis
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'trading_system.db'

# ============================================
# ENUMS AND DATA CLASSES
# ============================================

class MarketState(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    DANGER = "danger"
    LOCKDOWN = "lockdown"

class ErrorType(Enum):
    TIMING_ERROR = "timing_error"
    CONSENSUS_FAILURE = "consensus_failure"
    HIGH_VOLATILITY = "high_volatility"
    LOW_CONFIDENCE = "low_confidence"
    AGENT_TIMEOUT = "agent_timeout"

# ============================================
# PART 1: BATCH MANAGEMENT & WINNER DETERMINATION
# ============================================

class BatchManager:
    """Manages trading batches and determines winners"""
    
    def __init__(self):
        self._init_batch_tables()
    
    def _init_batch_tables(self):
        """Initialize batch tracking tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Batches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_number INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_trades INTEGER,
                winning_agent TEXT,
                win_rate REAL,
                total_pnl REAL,
                market_state TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Batch performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_number INTEGER,
                agent_name TEXT,
                trades_count INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                total_pnl REAL,
                avg_confidence REAL,
                rank INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_new_batch(self, batch_number: int) -> int:
        """Start a new trading batch"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trading_batches (batch_number, start_time, market_state)
            VALUES (?, ?, ?)
        ''', (batch_number, datetime.now(), 'pending'))
        
        batch_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"📦 Batch #{batch_number} started")
        return batch_id
    
    def end_batch(self, batch_number: int, results: Dict):
        """End a batch and calculate winner"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update batch
        cursor.execute('''
            UPDATE trading_batches 
            SET end_time = ?, total_trades = ?, winning_agent = ?, 
                win_rate = ?, total_pnl = ?, market_state = ?
            WHERE batch_number = ?
        ''', (
            datetime.now(), results.get('total_trades', 0),
            results.get('winning_agent'), results.get('win_rate', 0),
            results.get('total_pnl', 0), results.get('market_state', 'unknown'),
            batch_number
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🏆 Batch #{batch_number} completed. Winner: {results.get('winning_agent')}")
        return results.get('winning_agent')
    
    def calculate_batch_winner(self, batch_number: int) -> Dict:
        """Calculate which agent won the batch"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all signals in this batch
        cursor.execute('''
            SELECT s.id, s.asset_type, s.current_price, gv.final_decision, gv.decision_confidence
            FROM signals s
            JOIN group_votes gv ON s.id = gv.signal_id
            WHERE s.created_at >= (SELECT start_time FROM trading_batches WHERE batch_number = ?)
            AND s.created_at <= (SELECT end_time FROM trading_batches WHERE batch_number = ?)
        ''', (batch_number, batch_number))
        
        signals = cursor.fetchall()
        
        # Get agent votes for these signals
        agent_performance = {}
        
        for signal in signals:
            signal_id = signal[0]
            actual_outcome = self._simulate_outcome(signal)  # In production, use actual PnL
            
            cursor.execute('''
                SELECT agent_name, vote FROM agent_votes WHERE signal_id = ?
            ''', (signal_id,))
            
            votes = cursor.fetchall()
            for agent_name, vote in votes:
                if agent_name not in agent_performance:
                    agent_performance[agent_name] = {'correct': 0, 'total': 0, 'pnl': 0}
                
                agent_performance[agent_name]['total'] += 1
                
                # Check if agent's vote matched the outcome
                if (vote == 'BUY' and actual_outcome > 0) or (vote == 'SELL' and actual_outcome < 0):
                    agent_performance[agent_name]['correct'] += 1
                    agent_performance[agent_name]['pnl'] += abs(actual_outcome)
        
        # Calculate win rates and determine winner
        winner = None
        best_win_rate = 0
        
        for agent, perf in agent_performance.items():
            win_rate = (perf['correct'] / perf['total'] * 100) if perf['total'] > 0 else 0
            perf['win_rate'] = win_rate
            
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                winner = agent
            
            # Store in batch_performance table
            cursor.execute('''
                INSERT INTO batch_performance (batch_number, agent_name, trades_count, 
                    wins, losses, win_rate, total_pnl, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (batch_number, agent, perf['total'], perf['correct'],
                  perf['total'] - perf['correct'], win_rate, perf['pnl'], 0))
        
        conn.commit()
        conn.close()
        
        return {
            'winner': winner,
            'win_rate': best_win_rate,
            'performance': agent_performance
        }
    
    def _simulate_outcome(self, signal) -> float:
        """Simulate trade outcome (in production, use real PnL)"""
        import random
        # Simulate price movement based on decision confidence
        confidence = signal[3] if len(signal) > 3 else 70
        direction = 1 if signal[2] == 'BUY' else -1
        movement = random.uniform(-2, 3) * (confidence / 100)
        return direction * movement

# ============================================
# PART 2: CORRECTION ENGINE - SQL-DRIVEN CHANGES
# ============================================

class CorrectionEngine:
    """Translates errors into SQL-driven changes"""
    
    def __init__(self):
        self._init_correction_tables()
    
    def _init_correction_tables(self):
        """Initialize error tracking tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT,
                signal_id INTEGER,
                agent_name TEXT,
                error_details TEXT,
                correction_sql TEXT,
                severity INTEGER,
                is_resolved INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_trust_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                trust_weight REAL,
                reason TEXT,
                market_state TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
def handle_timing_error(self, signal_id: int, agent_name: str, delay_ms: int) -> Dict:
    """Step 1: Handle timing error - signal arrived late"""
    
    correction_sql = f"""
        UPDATE agent_votes 
        SET confidence = confidence * 0.7,
            trust_weight = trust_weight * 0.9
        WHERE signal_id = {signal_id} AND agent_name = '{agent_name}';
    """
    
    self._execute_correction(correction_sql)
    
    # Log the error
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO error_log (error_type, signal_id, agent_name, error_details, correction_sql, severity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('TIMING_ERROR', signal_id, agent_name, f'Delay: {delay_ms}ms', correction_sql, 5))
    conn.commit()
    conn.close()
    
    return {
        'status': 'corrected',
        'action': 'confidence_reduced',
        'new_confidence_multiplier': 0.7,
        'message': f'Agent {agent_name} penalized for {delay_ms}ms delay'
    }

def handle_consensus_failure(self, signal_id: int, votes: Dict) -> Dict:
    """Step 3: Handle consensus failure - agents split vote"""
    
    # Find majority vote
    buy = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
    sell = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
    hold = sum(1 for v in votes.values() if v.get('vote') == 'HOLD')
    
    # Determine majority
    if buy > sell and buy > hold:
        majority = 'BUY'
    elif sell > buy and sell > hold:
        majority = 'SELL'
    else:
        majority = 'HOLD'
    
    minority_agents = [agent for agent, v in votes.items() if v.get('vote') != majority]
    
    # Build correction SQL
    correction_sql = f"""
        -- Supervisor override for consensus failure
        UPDATE group_votes 
        SET final_decision = '{majority}',
            decision_confidence = decision_confidence * 0.8,
            consensus_achieved = 0
        WHERE signal_id = {signal_id};
        
        -- Penalize minority agents
        UPDATE agent_votes 
        SET trust_weight = trust_weight * 0.85
        WHERE signal_id = {signal_id} AND agent_name IN ({','.join([f"'{a}'" for a in minority_agents])});
    """
    
    self._execute_correction(correction_sql)
    
    # Also log the error
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO error_log (error_type, signal_id, error_details, correction_sql, severity)
        VALUES (?, ?, ?, ?, ?)
    ''', ('CONSENSUS_FAILURE', signal_id, f'Agents split: BUY={buy}, SELL={sell}, HOLD={hold}', correction_sql, 7))
    conn.commit()
    conn.close()
    
    return {
        'status': 'corrected',
        'action': 'supervisor_override',
        'final_decision': majority,
        'penalized_agents': minority_agents,
        'message': f'Consensus failure resolved. Supervisor overrode to {majority}'
    }
# ============================================
# PART 3: MARKET STATE ANALYZER
# ============================================

class MarketStateAnalyzer:
    """Analyzes market state based on last 10 trades"""
    
    def __init__(self):
        self.last_10_trades = []
    
    def analyze_market_snapshot(self, trades: List[Dict]) -> Dict:
        """Analyze market state from last 10 trades"""
        
        if len(trades) < 5:
            return {'state': MarketState.RANGING, 'confidence': 50, 'reason': 'Insufficient data'}
        
        # Calculate metrics
        avg_volatility = sum(t.get('volatility', 0) for t in trades) / len(trades)
        avg_win_rate = sum(1 for t in trades if t.get('outcome') == 'WIN') / len(trades) * 100
        price_direction = self._calculate_direction(trades)
        
        # Determine market state
        if avg_volatility > 3.0:
            state = MarketState.HIGH_VOLATILITY
            confidence = min(90, avg_volatility * 20)
            reason = f"High volatility detected: {avg_volatility:.1f}%"
        elif avg_volatility < 0.5:
            state = MarketState.LOW_VOLATILITY
            confidence = 70
            reason = f"Low volatility: {avg_volatility:.1f}%"
        elif abs(price_direction) > 0.5:
            state = MarketState.TRENDING
            confidence = min(85, abs(price_direction) * 50)
            reason = f"Strong trend detected: {price_direction:.1f}%"
        else:
            state = MarketState.RANGING
            confidence = 60
            reason = "Market ranging, no clear direction"
        
        # Map agent performance to market state
        agent_performance = self._map_agent_performance(trades, state)
        
        return {
            'state': state.value,
            'confidence': round(confidence, 1),
            'reason': reason,
            'avg_volatility': round(avg_volatility, 2),
            'avg_win_rate': round(avg_win_rate, 1),
            'price_direction': round(price_direction, 2),
            'agent_performance': agent_performance,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_direction(self, trades: List[Dict]) -> float:
        """Calculate overall price direction"""
        if len(trades) < 2:
            return 0
        
        first_price = trades[0].get('price', 0)
        last_price = trades[-1].get('price', 0)
        
        if first_price == 0:
            return 0
        
        return ((last_price - first_price) / first_price) * 100
    
    def _map_agent_performance(self, trades: List[Dict], state: MarketState) -> Dict:
        """Map which agents perform best in each market state"""
        
        agent_correct = {}
        agent_total = {}
        
        for trade in trades:
            for agent, vote in trade.get('votes', {}).items():
                agent_total[agent] = agent_total.get(agent, 0) + 1
                if vote.get('was_correct', False):
                    agent_correct[agent] = agent_correct.get(agent, 0) + 1
        
        performance = {}
        for agent in agent_total:
            win_rate = (agent_correct.get(agent, 0) / agent_total[agent]) * 100 if agent_total[agent] > 0 else 0
            performance[agent] = {
                'win_rate': round(win_rate, 1),
                'trades': agent_total[agent],
                'trust_adjustment': self._get_trust_adjustment(win_rate, state)
            }
        
        return performance
    
    def _get_trust_adjustment(self, win_rate: float, state: MarketState) -> float:
        """Calculate trust adjustment based on performance in market state"""
        if win_rate > 70:
            return +0.05
        elif win_rate < 40:
            return -0.05
        return 0

# ============================================
# PART 4: DANGER ZONE & LOCKDOWN LOGIC
# ============================================

class DangerZoneManager:
    """Manages danger zone detection and lockdown protocols"""
    
    def __init__(self):
        self.lockdown_active = False
        self.lockdown_reason = None
        self.lockdown_start = None
        self._init_danger_tables()
    
    def _init_danger_tables(self):
        """Initialize danger zone tracking tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS danger_zone_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                trigger_reason TEXT,
                volatility REAL,
                consecutive_losses INTEGER,
                action_taken TEXT,
                affected_agents TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lockdown_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                reason TEXT,
                affected_agents TEXT,
                weight_changes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def define_danger_zone(self, market_state: Dict, consecutive_losses: int) -> Dict:
        """Code 1: Define Danger Zone based on market conditions"""
        
        danger_level = 'GREEN'
        action = 'NORMAL'
        reason = []
        
        # Check for extreme volatility
        if market_state.get('avg_volatility', 0) > 5:
            danger_level = 'RED'
            action = 'FULL_LOCKDOWN'
            reason.append(f"Extreme volatility: {market_state['avg_volatility']:.1f}%")
        
        # Check for consecutive losses
        if consecutive_losses >= 3:
            danger_level = 'YELLOW' if danger_level == 'GREEN' else 'RED'
            action = 'PARTIAL_LOCKDOWN' if danger_level == 'YELLOW' else 'FULL_LOCKDOWN'
            reason.append(f"{consecutive_losses} consecutive losses")
        
        # Check market state
        if market_state.get('state') == 'high_volatility':
            if danger_level == 'GREEN':
                danger_level = 'YELLOW'
                action = 'REDUCED_POSITIONS'
            reason.append("High volatility market")
        
        # Store danger event
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO danger_zone_events (level, trigger_reason, volatility, 
                consecutive_losses, action_taken)
            VALUES (?, ?, ?, ?, ?)
        ''', (danger_level, ', '.join(reason), market_state.get('avg_volatility', 0),
              consecutive_losses, action))
        conn.commit()
        conn.close()
        
        return {
            'level': danger_level,
            'action': action,
            'reasons': reason,
            'trust_weight_multiplier': 0 if danger_level == 'RED' else 0.5 if danger_level == 'YELLOW' else 1.0
        }
    
    def lockdown_logic(self, current_volatility: float, agent_weights: Dict) -> Dict:
        """Code 2: Lockdown role - if tolerance < volatility, reduce trust weight"""
        
        # Agent volatility tolerance settings
        agent_tolerance = {
            'Agent_A': 1.5,  # Trend follower - medium tolerance
            'Agent_B': 2.0,  # Mean reversion - higher tolerance
            'Agent_C': 1.0,  # Momentum - low tolerance
            'Agent_D': 3.0,  # Volatility - high tolerance
            'Agent_E': 1.5   # Microstructure - medium tolerance
        }
        
        changes = []
        
        for agent, current_weight in agent_weights.items():
            tolerance = agent_tolerance.get(agent, 1.5)
            
            # Lockdown logic: if tolerance < current_volatility
            if tolerance < current_volatility:
                new_weight = current_weight * (tolerance / current_volatility)
                new_weight = max(0.05, min(0.4, new_weight))
                
                changes.append({
                    'agent': agent,
                    'old_weight': current_weight,
                    'new_weight': new_weight,
                    'reason': f"Volatility {current_volatility}% exceeds tolerance {tolerance}%"
                })
                
                # Update in database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO agent_trust_weights (agent_name, trust_weight, reason, market_state)
                    VALUES (?, ?, ?, ?)
                ''', (agent, new_weight, f"Lockdown: volatility={current_volatility}%", "HIGH_VOLATILITY"))
                conn.commit()
                conn.close()
        
        if changes:
            logger.warning(f"🔒 LOCKDOWN ACTIVE: {len(changes)} agents affected")
            
            # Activate full lockdown if multiple agents affected
            if len(changes) >= 3:
                self.lockdown_active = True
                self.lockdown_start = datetime.now()
                self.lockdown_reason = f"Multiple agents exceeded volatility tolerance ({current_volatility}%)"
        
        return {
            'lockdown_active': self.lockdown_active,
            'changes': changes,
            'current_volatility': current_volatility
        }
    
    def release_lockdown(self) -> Dict:
        """Release lockdown when conditions normalize"""
        if not self.lockdown_active:
            return {'status': 'normal', 'message': 'No active lockdown'}
        
        lockdown_duration = (datetime.now() - self.lockdown_start).total_seconds() / 60
        
        # Record lockdown history
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lockdown_history (start_time, end_time, reason)
            VALUES (?, ?, ?)
        ''', (self.lockdown_start, datetime.now(), self.lockdown_reason))
        conn.commit()
        conn.close()
        
        self.lockdown_active = False
        self.lockdown_reason = None
        self.lockdown_start = None
        
        return {
            'status': 'released',
            'duration_minutes': round(lockdown_duration, 1),
            'message': f'Lockdown released after {lockdown_duration:.1f} minutes'
        }

# ============================================
# COMPLETE SUPERVISOR - ALL 4 STEPS INTEGRATED
# ============================================

class CompleteSupervisor:
    """Integrated supervisor with all features"""
    
    def __init__(self):
        self.batch_manager = BatchManager()
        self.correction_engine = CorrectionEngine()
        self.market_analyzer = MarketStateAnalyzer()
        self.danger_manager = DangerZoneManager()
        self.current_batch = 1
        self.trade_history = []
    
    def process_trade(self, trade_data: Dict) -> Dict:
        """Process a trade through all 4 supervisor steps"""
        
        logger.info(f"🔍 SUPERVISOR processing trade #{trade_data.get('signal_id')}")
        
        # Step 1: Check timing error
        timing_result = self._check_timing_error(trade_data)
        
        # Step 2: Process Telegram signal
        telegram_result = self._process_telegram_signal(trade_data)
        
        # Step 3: Check consensus failure
        consensus_result = self._check_consensus_failure(trade_data)
        
        # Step 4: Check volatility error
        volatility_result = self._check_volatility_error(trade_data)
        
        # Update trade history
        self.trade_history.append(trade_data)
        if len(self.trade_history) > 10:
            self.trade_history.pop(0)
        
        # Analyze market state from last 10 trades
        market_state = self.market_analyzer.analyze_market_snapshot(self.trade_history)
        
        # Check danger zone
        consecutive_losses = self._get_consecutive_losses()
        danger_zone = self.danger_manager.define_danger_zone(market_state, consecutive_losses)
        
        # Apply lockdown if needed
        if danger_zone['level'] in ['YELLOW', 'RED']:
            agent_weights = self._get_agent_weights()
            lockdown = self.danger_manager.lockdown_logic(
                market_state.get('avg_volatility', 0.5),
                agent_weights
            )
        else:
            lockdown = {'lockdown_active': False, 'changes': []}
        
        # Determine batch winner (every 10 trades)
        batch_result = None
        if len(self.trade_history) >= 10:
            batch_result = self.batch_manager.calculate_batch_winner(self.current_batch)
            self.current_batch += 1
        
        return {
            'signal_id': trade_data.get('signal_id'),
            'timing_check': timing_result,
            'telegram_processing': telegram_result,
            'consensus_check': consensus_result,
            'volatility_check': volatility_result,
            'market_state': market_state,
            'danger_zone': danger_zone,
            'lockdown': lockdown,
            'batch_winner': batch_result,
            'timestamp': datetime.now().isoformat()
        }

    def _check_timing_error(self, trade_data: Dict) -> Dict:
        """Step 1: Check for timing errors"""
        received_time = trade_data.get('received_at')
        signal_time = trade_data.get('signal_time')
        
        if received_time and signal_time:
            delay_ms = (received_time - signal_time).total_seconds() * 1000
            
            if delay_ms > 5000:  # More than 5 seconds delay
                return self.correction_engine.handle_timing_error(
                    trade_data.get('signal_id'),
                    trade_data.get('agent_name', 'Unknown'),
                    delay_ms
                )
        
        return {'status': 'normal', 'delay_ms': 0}
    
    def _process_telegram_signal(self, trade_data: Dict) -> Dict:
        """Step 2: Process Telegram signal"""
        source = trade_data.get('source', 'unknown')
        
        if source == 'telegram':
            return {
                'status': 'processed',
                'source': 'telegram',
                'confidence_boost': 5,
                'message': 'Signal from Telegram processed'
            }
        
        return {'status': 'normal', 'source': source}
    
    def _check_consensus_failure(self, trade_data: Dict) -> Dict:
        """Step 3: Check for consensus failure"""
        votes = trade_data.get('votes', {})
        
        if not votes:
            return {'status': 'normal', 'message': 'No votes to analyze'}
        
        buy = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        
        # If votes are too split (3-2 or 2-2-1)
        if abs(buy - sell) <= 1 and buy > 0 and sell > 0:
            return self.correction_engine.handle_consensus_failure(
                trade_data.get('signal_id'),
                votes
            )
        
        return {'status': 'consensus_achieved', 'buy': buy, 'sell': sell}
    
def handle_volatility_error(self, signal_id: int, volatility: float, threshold: float = 2.0) -> Dict:
    """Step 4: Handle high volatility error"""
    
    if volatility > threshold:
        new_size_multiplier = max(0.3, 1 - (volatility / 10))
        
        correction_sql = f"""
            -- Reduce position size due to high volatility
            UPDATE signals 
            SET position_size_multiplier = {new_size_multiplier},
                analysis_volatility = {volatility},
                status = 'RISK_REDUCED'
            WHERE id = {signal_id};
        """
        
        self._execute_correction(correction_sql)
        

        # Log the error
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO error_log (error_type, signal_id, error_details, correction_sql, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', ('HIGH_VOLATILITY', signal_id, f'Volatility: {volatility}%', correction_sql, 8))
        conn.commit()
        conn.close()
        
        return {
            'status': 'risk_reduced',
            'action': 'position_size_reduced',
            'new_size_multiplier': new_size_multiplier,
            'message': f'Position size reduced due to {volatility}% volatility'
        }
    
        return {'status': 'normal', 'message': 'Volatility within normal range'}
    def _get_consecutive_losses(self) -> int:
        """Count consecutive losses"""
        losses = 0
        for trade in reversed(self.trade_history):
            if trade.get('outcome') == 'LOSS':
                losses += 1
            else:
                break
        return losses
    
    def _get_agent_weights(self) -> Dict:
        """Get current agent trust weights"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT agent_name, trust_weight FROM agent_votes ORDER BY id DESC LIMIT 5')
        results = cursor.fetchall()
        conn.close()
        
        weights = {}
        for agent, weight in results:
            weights[agent] = weight if weight else 0.2
        
        # Default weights if none found
        for agent in ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E']:
            if agent not in weights:
                weights[agent] = 0.2
        
        return weights

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 ADVANCED SUPERVISOR SYSTEM")
    print("=" * 60)
    
    supervisor = CompleteSupervisor()
    
    # Test with sample trade data
    test_trade = {
        'signal_id': 1,
        'received_at': datetime.now(),
        'signal_time': datetime.now() - timedelta(milliseconds=100),
        'source': 'telegram',
        'volatility': 2.5,
        'votes': {
            'Agent_A': {'vote': 'BUY'},
            'Agent_B': {'vote': 'SELL'},
            'Agent_C': {'vote': 'BUY'},
            'Agent_D': {'vote': 'BUY'},
            'Agent_E': {'vote': 'SELL'}
        }
    }
    
    result = supervisor.process_trade(test_trade)
    
    print("\n📊 SUPERVISOR RESULT:")
    print(json.dumps(result, indent=2, default=str))
