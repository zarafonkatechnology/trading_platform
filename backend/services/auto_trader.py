"""
Auto-Trading Engine - Executes trades based on advisor recommendations
"""

import threading
import time
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

class AutoTrader:
    """Automatically executes trades when advisor confidence is high"""
    
    def __init__(self, agent_manager, supervisor, advisor):
        self.agent_manager = agent_manager
        self.supervisor = supervisor
        self.advisor = advisor
        self.is_running = False
        self.trade_history = []
        self.min_confidence = 75  # Minimum confidence to auto-trade
        self.max_daily_trades = 10
        self.daily_trades = 0
        self.last_trade_date = None
    
    def start(self):
        """Start auto-trading thread"""
        self.is_running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        print("✅ Auto-Trader started - monitoring for high-confidence setups")
    
    def _monitor_loop(self):
        """Monitor market and execute trades"""
        while self.is_running:
            try:
                # Reset daily counter
                today = datetime.now().date()
                if self.last_trade_date != today:
                    self.daily_trades = 0
                    self.last_trade_date = today
                
                # Check if we can trade
                if self.daily_trades >= self.max_daily_trades:
                    time.sleep(60)
                    continue
                
                # Get current market data
                market_data = self._get_market_data()
                
                # Collect agent votes
                votes = self.agent_manager.collect_votes(market_data['signal'], market_data['features'])
                
                # Get advisor consensus
                advice = self.advisor.get_consensus_advice(votes, market_data['signal'], market_data['features'])
                
                # Parse decision from advice
                decision = self._parse_decision(advice)
                
                if decision and decision['confidence'] >= self.min_confidence:
                    self._execute_trade(decision, market_data)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Auto-trader error: {e}")
                time.sleep(60)
    
    def _get_market_data(self) -> Dict:
        """Get current market data"""
        from backend.services.market_data_fetcher import market_fetcher
        prices = market_fetcher.get_current_prices()
        
        return {
            'signal': {
                'asset_type': 'XAU/USD',
                'current_price': prices.get('XAU/USD', 2350),
                'confidence_percent': 80
            },
            'features': {
                'rsi_14': 55,
                'volatility': 0.8,
                'trend_strength': 60
            }
        }
    
    def _parse_decision(self, advice: str) -> Dict:
        """Parse advisor decision from text"""
        if 'FINAL DECISION: BUY' in advice:
            return {'action': 'BUY', 'confidence': 70}
        elif 'FINAL DECISION: SELL' in advice:
            return {'action': 'SELL', 'confidence': 70}
        else:
            return None
    
    def _execute_trade(self, decision: Dict, market_data: Dict):
        """Execute trade based on advisor recommendation"""
        self.daily_trades += 1
        
        trade_record = {
            'id': len(self.trade_history) + 1,
            'action': decision['action'],
            'price': market_data['signal']['current_price'],
            'confidence': decision['confidence'],
            'timestamp': datetime.now().isoformat(),
            'status': 'executed'
        }
        self.trade_history.append(trade_record)
        
        print(f"💹 AUTO-TRADE EXECUTED: {decision['action']} at ${trade_record['price']:.2f}")
        
        # Send notification via Telegram
        self._send_notification(trade_record)
    
    def _send_notification(self, trade: Dict):
        """Send trade notification to Telegram"""
        try:
            from telegram_bot import telegram_bot
            message = f"""
💹 *AUTO-TRADE EXECUTED*

🎯 Action: {trade['action']}
💰 Price: ${trade['price']:.2f}
📊 Confidence: {trade['confidence']}%
⏰ Time: {trade['timestamp']}

_Executed by Auto-Trader based on DeepSeek Advisor_
"""
            telegram_bot.send_message(message)
        except:
            pass
    
    def get_stats(self) -> Dict:
        """Get auto-trader statistics"""
        return {
            'total_trades': len(self.trade_history),
            'daily_trades': self.daily_trades,
            'max_daily': self.max_daily_trades,
            'is_active': self.is_running
        }

# Singleton
_auto_trader = None

def get_auto_trader(agent_manager, supervisor, advisor):
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AutoTrader(agent_manager, supervisor, advisor)
    return _auto_trader
