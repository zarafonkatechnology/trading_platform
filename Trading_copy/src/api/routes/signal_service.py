# src/services/signal_service.py
"""
Central Signal Service - Collects signals from AI agents and distributes to clients
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
import os

logger = logging.getLogger(__name__)

class SignalService:
    """Central service for collecting and distributing AI signals"""
    
    def __init__(self):
        self.signals = []
        self.client_subscriptions = defaultdict(list)  # client_id -> list of symbols
        self.signal_history = []
        self.is_running = False
        self.last_update = None
        
        # Initialize AI controllers
        self.indices_controller = None
        self.forex_controller = None
        self._initialize_controllers()
        
        # Start background signal collection
        self.start()
        
        logger.info("✅ Signal Service initialized")
    
    def _initialize_controllers(self):
        """Initialize AI controllers"""
        try:
            from trading_controller import AITradingController
            self.indices_controller = AITradingController()
            logger.info("✅ Indices AI controller loaded")
        except Exception as e:
            logger.warning(f"⚠️ Indices AI controller not available: {e}")
        
        try:
            from trading_controller2 import ForexTradingController
            config = {
                'pairs': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'],
                'min_confidence': 60,
                'rl_enabled': False,
            }
            self.forex_controller = ForexTradingController(config)
            logger.info("✅ Forex AI controller loaded")
        except Exception as e:
            logger.warning(f"⚠️ Forex AI controller not available: {e}")
    
    def start(self):
        """Start the signal collection service"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background thread for signal collection
        thread = threading.Thread(target=self._collect_signals_loop, daemon=True)
        thread.start()
        logger.info("✅ Signal collection started")
    
    def stop(self):
        """Stop the signal collection service"""
        self.is_running = False
        logger.info("⏹️ Signal collection stopped")
    
    def _collect_signals_loop(self):
        """Background loop to collect signals from AI agents"""
        while self.is_running:
            try:
                self._collect_signals()
                time.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"Error collecting signals: {e}")
                time.sleep(60)
    
    def _collect_signals(self):
        """Collect signals from all AI agents"""
        all_signals = []
        
        # Collect from indices AI
        indices_signals = self._get_indices_signals()
        if indices_signals:
            all_signals.extend(indices_signals)
        
        # Collect from forex AI
        forex_signals = self._get_forex_signals()
        if forex_signals:
            all_signals.extend(forex_signals)
        
        # Sort by confidence
        all_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Update signals
        self.signals = all_signals[:15]  # Keep top 15 signals
        self.last_update = datetime.now().isoformat()
        
        # Add to history
        for signal in self.signals:
            signal['collected_at'] = datetime.now().isoformat()
            self.signal_history.append(signal)
        
        # Keep history manageable
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
        
        logger.info(f"📊 Collected {len(self.signals)} signals")
        
        # Notify subscribed clients
        self._notify_subscribers()
    
    def _get_indices_signals(self) -> List[Dict]:
        """Get signals from indices AI agents"""
        signals = []
        
        if not self.indices_controller:
            return signals
        
        try:
            symbols = ['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225']
            prices = self.indices_controller.get_all_mt4_prices() if hasattr(self.indices_controller, 'get_all_mt4_prices') else {}
            
            for symbol in symbols:
                try:
                    analysis = self.indices_controller.analyze_market(symbol)
                    
                    if analysis and analysis.get('action') not in ['HOLD', None]:
                        confidence = analysis.get('confidence', 0)
                        if confidence >= 60:
                            signals.append({
                                'symbol': symbol,
                                'type': analysis.get('action', 'HOLD'),
                                'confidence': round(confidence, 1),
                                'reasoning': analysis.get('reasoning', 'Indices AI signal'),
                                'price': prices.get(symbol, 0),
                                'timestamp': datetime.now().isoformat(),
                                'source': 'Indices AI',
                                'agent': 'Indices Controller'
                            })
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error getting indices signals: {e}")
        
        return signals
    
    def _get_forex_signals(self) -> List[Dict]:
        """Get signals from forex AI agents"""
        signals = []
        
        if not self.forex_controller:
            return signals
        
        try:
            market_data = self.forex_controller.build_market_data() if hasattr(self.forex_controller, 'build_market_data') else {}
            
            for pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']:
                try:
                    # Try to get decision from broker manager
                    if hasattr(self.forex_controller, 'broker_manager'):
                        decisions = self.forex_controller.broker_manager.get_decision(market_data)
                        
                        if decisions and pair in decisions:
                            decision = decisions[pair]
                            signal = decision.get('signal', 'HOLD')
                            confidence = decision.get('confidence', 0)
                            
                            if signal != 'HOLD' and confidence >= 60:
                                signals.append({
                                    'symbol': pair,
                                    'type': signal,
                                    'confidence': round(confidence, 1),
                                    'reasoning': decision.get('reasoning', 'Forex AI signal'),
                                    'price': market_data.get(pair, 0),
                                    'timestamp': datetime.now().isoformat(),
                                    'source': 'Forex AI',
                                    'agent': 'Forex Controller'
                                })
                except Exception as e:
                    logger.debug(f"Error analyzing {pair}: {e}")
                    
        except Exception as e:
            logger.error(f"Error getting forex signals: {e}")
        
        return signals
    
    def _notify_subscribers(self):
        """Notify subscribed clients about new signals"""
        # This will be implemented with WebSocket
        pass
    
    def get_all_signals(self) -> List[Dict]:
        """Get all current signals"""
        return self.signals
    
    def get_signals_for_client(self, client_id: str) -> List[Dict]:
        """Get signals for a specific client based on their subscriptions"""
        subscribed_symbols = self.client_subscriptions.get(client_id, [])
        
        if not subscribed_symbols:
            # If no subscriptions, return all signals
            return self.signals
        
        # Filter signals for subscribed symbols
        return [s for s in self.signals if s.get('symbol') in subscribed_symbols]
    
    def subscribe_client(self, client_id: str, symbols: List[str]):
        """Subscribe a client to specific symbols"""
        self.client_subscriptions[client_id] = symbols
        logger.info(f"📋 Client {client_id} subscribed to {len(symbols)} symbols")
    
    def unsubscribe_client(self, client_id: str):
        """Unsubscribe a client from all signals"""
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            logger.info(f"📋 Client {client_id} unsubscribed")
    
    def get_signal_stats(self) -> Dict:
        """Get signal statistics"""
        return {
            'total_signals': len(self.signals),
            'last_update': self.last_update,
            'active_subscriptions': len(self.client_subscriptions),
            'history_count': len(self.signal_history),
            'signals_by_type': {
                'BUY': len([s for s in self.signals if s.get('type') == 'BUY']),
                'SELL': len([s for s in self.signals if s.get('type') == 'SELL']),
                'HOLD': len([s for s in self.signals if s.get('type') == 'HOLD'])
            },
            'top_signals': self.signals[:5]
        }

# Global signal service instance
signal_service = SignalService()