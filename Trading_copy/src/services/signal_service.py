# src/services/signal_service.py - Complete Fixed Version
"""
Central Signal Service - Collects signals from AI agents and saves to database
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from src.database.supabase_client import get_trading_service

logger = logging.getLogger(__name__)

class SignalService:
    """Central service for collecting and distributing AI signals"""
    
    def __init__(self):
        self.db = get_trading_service()
        self.client_subscriptions = defaultdict(list)
        self.is_running = False
        self.last_update = None
        self.indices_controller = None
        self.forex_controller = None
        
        # Try to initialize AI controllers
        self._initialize_controllers()
        
        # Start background collection
        self.start()
        
        logger.info("✅ Signal Service initialized")
    
    def _initialize_controllers(self):
        """Initialize AI controllers with error handling"""
        try:
            import trading_controller
            self.indices_controller = trading_controller.trading_controller
            logger.info("✅ Indices AI controller loaded")
        except Exception as e:
            logger.warning(f"⚠️ Indices AI controller not available: {e}")
        
        try:
            import forex_engine.trading_controller2 as trading_controller2
            config = {
                'pairs': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'],
                'min_confidence': 60,
                'rl_enabled': False,
            }
            self.forex_controller = trading_controller2.ForexTradingController(config)
            logger.info("✅ Forex AI controller loaded")
        except Exception as e:
            logger.warning(f"⚠️ Forex AI controller not available: {e}")
    
    def start(self):
        """Start background signal collection"""
        if self.is_running:
            return
        self.is_running = True
        thread = threading.Thread(target=self._collect_signals_loop, daemon=True)
        thread.start()
        logger.info("✅ Signal collection started")
    
    def stop(self):
        self.is_running = False
        logger.info("⏹️ Signal collection stopped")
    
    def _collect_signals_loop(self):
        """Background loop to collect signals"""
        while self.is_running:
            try:
                self._collect_signals()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error collecting signals: {e}")
                time.sleep(60)
    
    def _collect_signals(self):
        """Collect signals from AI agents and save to database"""
        all_signals = []
        
        # ✅ Get signals from trading controller
        if self.indices_controller:
            try:
                symbols = ['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', 
                          '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
                          'BRENT_OIL', 'CrudeOIL']
                
                # Get prices
                prices = {}
                try:
                    prices = self.indices_controller.get_all_mt4_prices()
                except:
                    pass
                
                for symbol in symbols:
                    try:
                        # Get market analysis
                        analysis = self.indices_controller.analyze_market(symbol)
                        
                        if analysis and analysis.get('action') not in ['HOLD', None]:
                            action = analysis.get('action')
                            confidence = analysis.get('confidence', 0)
                            z_score = analysis.get('z_score', 0)
                            reasoning = analysis.get('reasoning', 'AI Signal')
                            
                            if confidence >= 60:
                                price = prices.get(symbol, 0)
                                
                                # ✅ SAVE TO DATABASE
                                signal_data = {
                                    'symbol': symbol,
                                    'signal_type': action,
                                    'confidence': int(confidence),
                                    'entry_price': price,
                                    'stop_loss': 0,
                                    'take_profit': 0,
                                    'reasoning': reasoning,
                                    'source': 'Agent_Controller',
                                    'z_score': z_score,
                                    'timeframe': 'M15',
                                    'status': 'PENDING'
                                }
                                
                                self._save_signal_to_db(signal_data)
                                
                                all_signals.append({
                                    'symbol': symbol,
                                    'type': action,
                                    'confidence': round(confidence, 1),
                                    'reasoning': reasoning,
                                    'price': price,
                                    'z_score': z_score,
                                    'timestamp': datetime.now().isoformat(),
                                    'source': 'AI Controller'
                                })
                    except Exception as e:
                        logger.debug(f"Error analyzing {symbol}: {e}")
                        
            except Exception as e:
                logger.error(f"Indices signal error: {e}")
        
        # Sort by confidence
        all_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        self.last_update = datetime.now().isoformat()
        
        logger.info(f"📊 Collected {len(all_signals)} signals from AI controllers")
        
        return all_signals
    
    # src/services/signal_service.py - Updated column names

    def _save_signal_to_db(self, signal_data: Dict) -> Optional[Dict]:
        """Save signal to database"""
        try:
               # The collector runs repeatedly. Do not create a new signal row
               # when the same recommendation is still active.
               cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
               duplicate = self.db.client.table('signal_history')\
                   .select('id')\
                   .eq('symbol', signal_data.get('symbol'))\
                   .eq('signal_type', signal_data.get('signal_type'))\
                   .eq('reasoning', signal_data.get('reasoning', ''))\
                   .eq('status', signal_data.get('status', 'PENDING'))\
                   .gte('created_at', cutoff)\
                   .limit(1)\
                   .execute()
               if duplicate.data:
                   logger.debug(
                      f"Skipping duplicate signal: {signal_data.get('symbol')} "
                      f"{signal_data.get('signal_type')}"
                   )
                   return duplicate.data[0]

               result = self.db.client.table('signal_history')\
                     .insert({
                          'symbol': signal_data.get('symbol'),
                          'signal_type': signal_data.get('signal_type'),
                          'confidence': signal_data.get('confidence', 0),
                          'entry_price': signal_data.get('entry_price', 0),
                          'stop_loss': signal_data.get('stop_loss', 0),
                          'take_profit': signal_data.get('take_profit', 0),
                          'reasoning': signal_data.get('reasoning', ''),
                          'source': signal_data.get('source', 'AI'),
                          'z_score': signal_data.get('z_score', 0),
                          'timeframe': signal_data.get('timeframe', 'M15'),
                          'status': signal_data.get('status', 'PENDING'),
                          'executed': False,
                          'created_at': datetime.now().isoformat()
                     })\
                     .execute()
               
               if result.data:
                     logger.info(f"✅ Signal saved to DB: {signal_data.get('symbol')} {signal_data.get('signal_type')}")
                     return result.data[0]
               return None
        except Exception as e:
               logger.error(f"❌ Error saving signal: {e}")
               return None
    def get_all_signals(self) -> List[Dict]:
        """Get all signals from database"""
        try:
            result = self.db.client.table('signal_history')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute()
            
            signals = result.data or []
            
            # Format for frontend
            formatted = []
            for s in signals:
                formatted.append({
                    'signal_id': s.get('id'),
                    'symbol': s.get('symbol'),
                    'type': s.get('signal_type'),
                    'confidence': s.get('confidence'),
                    'reasoning': s.get('reasoning'),
                    'price': s.get('entry_price'),
                    'timestamp': s.get('created_at'),
                    'source': s.get('source'),
                    'z_score': s.get('z_score'),
                    'status': s.get('status')
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting signals from DB: {e}")
            return []
    
    def get_signals_for_client(self, client_id: str) -> List[Dict]:
        """Get signals for a specific client"""
        return self.get_all_signals()
    
    def subscribe_client(self, client_id: str, symbols: List[str]):
        self.client_subscriptions[client_id] = symbols
        logger.info(f"📋 Client {client_id} subscribed to {len(symbols)} symbols")
    
    def unsubscribe_client(self, client_id: str):
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            logger.info(f"📋 Client {client_id} unsubscribed")
    
    def get_signal_stats(self) -> Dict:
        """Get signal statistics from database"""
        try:
            # Get counts
            result = self.db.client.table('signal_history')\
                .select('signal_type, status, count')\
                .execute()
            
            signals = result.data or []
            
            # Count by type
            buy_count = sum(1 for s in signals if s.get('signal_type') == 'BUY')
            sell_count = sum(1 for s in signals if s.get('signal_type') == 'SELL')
            hold_count = sum(1 for s in signals if s.get('signal_type') == 'HOLD')
            
            # Count by status
            pending = sum(1 for s in signals if s.get('status') == 'PENDING')
            executed = sum(1 for s in signals if s.get('status') == 'EXECUTED')
            
            return {
                'total_signals': len(signals),
                'last_update': self.last_update or datetime.now().isoformat(),
                'active_subscriptions': len(self.client_subscriptions),
                'history_count': len(signals),
                'signals_by_type': {
                    'BUY': buy_count,
                    'SELL': sell_count,
                    'HOLD': hold_count
                },
                'signals_by_status': {
                    'PENDING': pending,
                    'EXECUTED': executed
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_signals': 0,
                'last_update': datetime.now().isoformat(),
                'active_subscriptions': len(self.client_subscriptions),
                'history_count': 0,
                'signals_by_type': {'BUY': 0, 'SELL': 0, 'HOLD': 0},
                'signals_by_status': {'PENDING': 0, 'EXECUTED': 0}
            }


# Create global instance
signal_service = SignalService()