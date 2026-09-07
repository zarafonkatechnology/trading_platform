"""
Complete Signal Processing Pipeline
Telegram → Parse → Strategy → Agents → Supervisor → Sentinel → Gatekeeper → Database
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Complete signal processing pipeline"""
    
    def __init__(self, db_manager, agent_manager, supervisor, sentinel, gatekeeper, strategy_framework):
        self.db = db_manager
        self.agent_manager = agent_manager
        self.supervisor = supervisor
        self.sentinel = sentinel
        self.gatekeeper = gatekeeper
        self.strategy_framework = strategy_framework
        
        self.processing_times = {}
        self.signal_history = []
    
    def process_signal(self, signal_data: Dict) -> Dict:
        """
        Main processing pipeline for each signal.
        Returns complete processing result.
        """
        
        start_time = time.time()
        timeline = {}
        
        # ========== Step 1: Store raw signal ==========
        signal_id = self._store_signal(signal_data)
        timeline['storage_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # ========== Step 2: Get strategy for this timeframe ==========
        timeframe = signal_data.get('timeframe_minutes', 15)
        strategy = self.strategy_framework.get_strategy(timeframe)
        timeline['strategy_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # ========== Step 3: Prepare market features ==========
        market_features = self._prepare_market_features(signal_data)
        timeline['features_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # ========== Step 4: Get agent votes ==========
        vote_start = time.time()
        votes = self.agent_manager.collect_votes(signal_data, market_features)
        timeline['voting_ms'] = round((time.time() - vote_start) * 1000, 2)
        
        # ========== Step 5: Calculate group vote distribution ==========
        group_start = time.time()
        group_result = self._calculate_group_votes(signal_id, votes)
        timeline['group_calc_ms'] = round((time.time() - group_start) * 1000, 2)
        
        # ========== Step 6: Supervisor weighted decision ==========
        super_start = time.time()
        supervisor_decision = self.supervisor.process_votes(votes)
        supervisor_decision['strategy_used'] = strategy['name']
        timeline['supervisor_ms'] = round((time.time() - super_start) * 1000, 2)
        
        # ========== Step 7: Apply strategy constraints ==========
        if supervisor_decision['confidence'] < strategy['min_confidence']:
            supervisor_decision['decision'] = 'HOLD'
            supervisor_decision['reason'] = f"Confidence {supervisor_decision['confidence']}% below minimum {strategy['min_confidence']}%"
        
        # Check consensus requirement
        required = strategy['required_consensus']
        if supervisor_decision['decision'] == 'BUY' and group_result['buy_percent'] < required:
            supervisor_decision['decision'] = 'HOLD'
            supervisor_decision['reason'] = f"Consensus {group_result['buy_percent']}% below required {required}%"
        elif supervisor_decision['decision'] == 'SELL' and group_result['sell_percent'] < required:
            supervisor_decision['decision'] = 'HOLD'
            supervisor_decision['reason'] = f"Consensus {group_result['sell_percent']}% below required {required}%"
        
        # ========== Step 8: Calculate position size ==========
        position_size = self.strategy_framework.calculate_position_size(
            strategy,
            supervisor_decision['confidence'],
            signal_data.get('analysis_volatility', 0.5)
        )
        supervisor_decision['position_size'] = position_size
        
        # Calculate stop loss and take profit
        if signal_data.get('stoploss'):
            supervisor_decision['stoploss'] = signal_data['stoploss']
        else:
            supervisor_decision['stoploss'] = self.strategy_framework.calculate_stoploss(
                strategy, signal_data['current_price']
            )
        
        if signal_data.get('takeprofit'):
            supervisor_decision['takeprofit'] = signal_data['takeprofit']
        else:
            supervisor_decision['takeprofit'] = self.strategy_framework.calculate_takeprofit(
                strategy, signal_data['current_price'], supervisor_decision['stoploss']
            )
        
        # ========== Step 9: Sentinel veto check ==========
        sentinel_start = time.time()
        context = {
            'volatility': signal_data.get('analysis_volatility', 0),
            'votes': votes,
            'strategy': strategy['name']
        }
        
        veto_allowed, veto_reason, patch = self.sentinel.veto_power(
            supervisor_decision, 
            'SYSTEM', 
            context
        ) if hasattr(self.sentinel, 'veto_power') else (True, None, None)
        
        timeline['sentinel_ms'] = round((time.time() - sentinel_start) * 1000, 2)
        
        if not veto_allowed:
            supervisor_decision['decision'] = 'HOLD'
            supervisor_decision['veto_reason'] = veto_reason
            supervisor_decision['veto_applied'] = True
        
        # ========== Step 10: Gatekeeper final authentication ==========
        gate_start = time.time()
        trade_request = {
            'signal_id': signal_id,
            'agent_name': 'SYSTEM',
            'action': supervisor_decision['decision'],
            'price': signal_data['current_price'],
            'quantity': position_size,
            'symbol': signal_data.get('asset_type', 'UNKNOWN')
        }
        
        gate_result = self.gatekeeper.request_permission(trade_request) if hasattr(self.gatekeeper, 'request_permission') else {'permission_granted': True}
        timeline['gatekeeper_ms'] = round((time.time() - gate_start) * 1000, 2)
        
        if not gate_result.get('permission_granted', True):
            supervisor_decision['decision'] = 'HOLD'
            supervisor_decision['gate_blocked'] = True
            supervisor_decision['gate_reason'] = gate_result.get('reason', 'Gatekeeper blocked')
        
        # ========== Step 11: Store complete results ==========
        self._store_votes(signal_id, votes)
        self._store_group_result(signal_id, group_result, supervisor_decision)
        self._store_execution(signal_id, supervisor_decision, strategy, timeline)
        
        # ========== Step 12: Update signal status ==========
        self._update_signal_status(signal_id, supervisor_decision['decision'])
        
        timeline['total_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # ========== Step 13: Store complete audit record ==========
        self._store_audit_record(signal_id, signal_data, votes, group_result, 
                                  supervisor_decision, gate_result, timeline)
        
        # ========== Step 14: Add to knowledge exchange ==========
        self._add_to_knowledge_exchange(signal_data, group_result, supervisor_decision, strategy)
        
        result = {
            'signal_id': signal_id,
            'signal': signal_data,
            'strategy': strategy,
            'votes': votes,
            'group_result': group_result,
            'decision': supervisor_decision,
            'gate_result': gate_result,
            'timeline': timeline,
            'processing_time_ms': timeline['total_ms']
        }
        
        self.signal_history.append(result)
        
        # Print summary to console
        self._print_summary(signal_data, group_result, supervisor_decision, timeline)
        
        return result
    
    def _store_signal(self, signal_data: Dict) -> int:
        """Store signal in database"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signals (
                asset_type, current_price, confidence_percent, signal_strength,
                data_source, analysis_volatility, stoploss, takeprofit,
                support_level, resistance_level, timeframe_minutes,
                signal_timestamp, telegram_message_id, telegram_chat_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            signal_data.get('asset_type'),
            signal_data.get('current_price'),
            signal_data.get('confidence_percent', 75),
            signal_data.get('signal_strength', 'SIGNAL'),
            signal_data.get('data_source', 'TELEGRAM'),
            signal_data.get('analysis_volatility', 0.5),
            signal_data.get('stoploss'),
            signal_data.get('takeprofit'),
            signal_data.get('support_level'),
            signal_data.get('resistance_level'),
            signal_data.get('timeframe_minutes', 15),
            signal_data.get('signal_timestamp', datetime.now()),
            signal_data.get('telegram_message_id'),
            signal_data.get('telegram_chat_id'),
            'PROCESSING'
        ))
        
        signal_id = cursor.fetchone()[0]
        conn.commit()
        
        return signal_id
    
    def _prepare_market_features(self, signal_data: Dict) -> Dict:
        """Prepare market features for agent voting"""
        return {
            'volatility': signal_data.get('analysis_volatility', 0.5),
            'trend_strength': 50,
            'rsi': 50,
            'volume': 1000,
            'spread': 0.001
        }
    
    def _calculate_group_votes(self, signal_id: int, votes: Dict) -> Dict:
        """Calculate vote distribution percentages"""
        buy_count = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell_count = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        hold_count = sum(1 for v in votes.values() if v['vote'] == 'HOLD')
        total = len(votes)
        
        buy_percent = (buy_count / total) * 100 if total > 0 else 0
        sell_percent = (sell_count / total) * 100 if total > 0 else 0
        hold_percent = (hold_count / total) * 100 if total > 0 else 0
        
        # Identify key agents (highest confidence)
        key_agents = sorted(votes.keys(), 
                           key=lambda a: votes[a].get('confidence', 0), 
                           reverse=True)[:2]
        
        return {
            'buy_votes': buy_count,
            'sell_votes': sell_count,
            'hold_votes': hold_count,
            'buy_percent': round(buy_percent, 2),
            'sell_percent': round(sell_percent, 2),
            'hold_percent': round(hold_percent, 2),
            'key_agents': key_agents,
            'total_agents': total
        }
    
    def _store_votes(self, signal_id: int, votes: Dict):
        """Store individual agent votes"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        
        for agent_name, vote_data in votes.items():
            cursor.execute("""
                INSERT INTO agent_votes (signal_id, agent_name, vote, confidence, timestamp)
                VALUES (%s, %s, %s, %s, NOW())
            """, (signal_id, agent_name, vote_data['vote'], vote_data.get('confidence', 50)))
        
        conn.commit()
    
    def _store_group_result(self, signal_id: int, group_result: Dict, decision: Dict):
        """Store group voting results"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO group_votes (
                signal_id, buy_votes, sell_votes, hold_votes,
                buy_percent, sell_percent, hold_percent,
                final_decision, decision_confidence, key_agents
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            signal_id,
            group_result['buy_votes'],
            group_result['sell_votes'],
            group_result['hold_votes'],
            group_result['buy_percent'],
            group_result['sell_percent'],
            group_result['hold_percent'],
            decision['decision'],
            decision['confidence'],
            group_result['key_agents']
        ))
        
        conn.commit()
    
    def _store_execution(self, signal_id: int, decision: Dict, strategy: Dict, timeline: Dict):
        """Store execution decision"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO execution_decisions (
                signal_id, decision_timestamp, execution_latency_ms, strategy_used,
                entry_price, quantity, stoploss_placed, takeprofit_placed,
                final_buy_percent, final_sell_percent, final_hold_percent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            signal_id,
            datetime.now(),
            timeline.get('total_ms', 0),
            strategy['name'],
            decision.get('price', 0),
            decision.get('position_size', 0),
            decision.get('stoploss'),
            decision.get('takeprofit'),
            decision.get('buy_percent', 0),
            decision.get('sell_percent', 0),
            decision.get('hold_percent', 0)
        ))
        
        conn.commit()
    
    def _update_signal_status(self, signal_id: int, status: str):
        """Update signal status"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        cursor.execute("UPDATE signals SET status = %s WHERE id = %s", (status, signal_id))
        conn.commit()
    
    def _store_audit_record(self, signal_id: int, signal_data: Dict, votes: Dict,
                             group_result: Dict, decision: Dict, gate_result: Dict, timeline: Dict):
        """Store complete audit record"""
        conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else self.db
        cursor = conn.cursor()
        
        # Create audit_log table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                signal_id INTEGER,
                signal_data JSONB,
                votes JSONB,
                group_result JSONB,
                decision JSONB,
                gate_result JSONB,
                timeline JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO audit_log (signal_id, signal_data, votes, group_result, decision, gate_result, timeline)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            signal_id,
            json.dumps(signal_data),
            json.dumps(votes),
            json.dumps(group_result),
            json.dumps(decision),
            json.dumps(gate_result),
            json.dumps(timeline)
        ))
        
        conn.commit()
    
    def _add_to_knowledge_exchange(self, signal_data: Dict, group_result: Dict, decision: Dict, strategy: Dict):
        """Add signal result to knowledge exchange"""
        # This will be handled by the main app's knowledge_exchange list
        pass
    
    def _print_summary(self, signal_data: Dict, group_result: Dict, decision: Dict, timeline: Dict):
        """Print processing summary to console"""
        print(f"\n{'='*60}")
        print(f"📊 SIGNAL PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"📡 Asset: {signal_data.get('asset_type', 'Unknown')}")
        print(f"💰 Price: ${signal_data.get('current_price', 0):,.2f}")
        print(f"🎯 Confidence: {signal_data.get('confidence_percent', 75)}%")
        print(f"⏱️ Timeframe: {signal_data.get('timeframe_minutes', 15)} minutes")
        print(f"\n🗳️ VOTING RESULTS:")
        print(f"   BUY:  {group_result['buy_votes']} votes ({group_result['buy_percent']}%)")
        print(f"   SELL: {group_result['sell_votes']} votes ({group_result['sell_percent']}%)")
        print(f"   HOLD: {group_result['hold_votes']} votes ({group_result['hold_percent']}%)")
        print(f"\n✅ FINAL DECISION: {decision['decision']} ({decision['confidence']}%)")
        print(f"📈 Strategy: {decision.get('strategy_used', 'Unknown')}")
        print(f"💰 Position Size: {decision.get('position_size', 0)} units")
        print(f"🛑 Stop Loss: ${decision.get('stoploss', 0):,.2f}")
        print(f"🎯 Take Profit: ${decision.get('takeprofit', 0):,.2f}")
        print(f"⏱️ Processing Time: {timeline.get('total_ms', 0)}ms")
        print(f"{'='*60}\n")
