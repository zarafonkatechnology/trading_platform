"""
Agent Monitor - Automatically watches prices and triggers agent voting
"""

import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentMonitor:
    """Monitors prices and triggers agent voting automatically"""
    
    def __init__(self, price_service, agent_manager, supervisor):
        self.price_service = price_service
        self.agent_manager = agent_manager
        self.supervisor = supervisor
        self.is_running = False
        self.monitor_thread = None
        self.last_prices = {}
        self.last_vote_time = {}
        
    def start(self):
        """Start monitoring prices"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Agent Monitor started")
        print("✅ Agent Monitor active - watching prices for trading opportunities")
    
    def _monitor_loop(self):
        """Monitor prices and trigger voting on significant moves"""
        while self.is_running:
            try:
                # Get current prices
                current_prices = self.price_service.get_all_prices()
                
                for symbol, price in current_prices.items():
                    if symbol in self.last_prices:
                        old_price = self.last_prices[symbol]
                        price_change = abs((price - old_price) / old_price * 100)
                        
                        # If price changed more than 0.3%, trigger voting
                        if price_change > 0.3:
                            self._trigger_voting(symbol, price, price_change)
                    
                    self.last_prices[symbol] = price
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(5)
    
    def _trigger_voting(self, symbol, price, change_percent):
        """Trigger agent voting on price movement"""
        # Avoid too frequent voting on same symbol
        now = time.time()
        if symbol in self.last_vote_time:
            if now - self.last_vote_time[symbol] < 60:  # Max once per minute
                return
        
        self.last_vote_time[symbol] = now
        
        # Create signal data
        signal_data = {
            'asset': symbol,
            'current_price': price,
            'change_percent': round(change_percent, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        # Prepare market features
        market_features = {
            'z_score_20': 0,
            'rsi_14': 50,
            'trend_strength': 50 + change_percent
        }
        
        # Collect votes from all agents
        votes = self.agent_manager.collect_votes(signal_data, market_features)
        
        # Process with supervisor
        decision = self.supervisor.process_votes(votes)
        
        # Log the decision
        logger.info(f"Voting triggered for {symbol}: {decision['decision']} with {decision['confidence']}% confidence")
        
        # Store in knowledge exchange
        if hasattr(self, 'app'):
            if not hasattr(self.app, 'knowledge_exchanges'):
                self.app.knowledge_exchanges = []
            
            vote_entry = {
                'id': len(self.app.knowledge_exchanges) + 1,
                'from_agent': 'Market Monitor',
                'to_agent': 'ALL AGENTS',
                'topic': f'🗳️ Price Alert: {symbol} moved {change_percent}%',
                'content': f"Price: ${price:.2f}\nDecision: {decision['decision']}\nConfidence: {decision['confidence']}%",
                'xp_reward': 0,
                'token_reward': 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_signal': True
            }
            self.app.knowledge_exchanges.insert(0, vote_entry)
        
        # Print to console
        print(f"\n📊 PRICE ALERT: {symbol} moved {change_percent}% to ${price:.2f}")
        print(f"🗳️ AGENT VOTING RESULTS:")
        for agent_name, vote_data in votes.items():
            print(f"   {agent_name}: {vote_data['vote']} ({vote_data['confidence']:.0f}%)")
        print(f"✅ FINAL DECISION: {decision['decision']}\n")


_monitor = None

def get_agent_monitor(price_service, agent_manager, supervisor):
    global _monitor
    if _monitor is None:
        _monitor = AgentMonitor(price_service, agent_manager, supervisor)
    return _monitor

