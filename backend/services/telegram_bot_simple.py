"""
Simple Telegram Bot Handler - No asyncio conflicts
"""

import logging
import re
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    """Simple Telegram bot using requests (no asyncio conflicts)"""
    
    def __init__(self, token, agent_manager, db_manager, app):
        self.token = token
        self.agent_manager = agent_manager
        self.db_manager = db_manager
        self.app = app
        self.last_update_id = 0
        self.running = False
        
    def send_message(self, chat_id, text):
        """Send a message via Telegram API"""
        import requests
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def parse_signal(self, message_text):
        """Parse trading signal from message"""
        message_text = message_text.upper().strip()
        
        # Pattern: ASSET ACTION PRICE
        pattern = r'^(\w+)\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)$'
        match = re.match(pattern, message_text)
        
        if match:
            return {
                'asset': match.group(1),
                'action': match.group(2),
                'price': float(match.group(3)),
                'confidence': 75,
                'strength': 'SIGNAL'
            }
        return None
    
    def process_message(self, message):
        """Process incoming message"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        username = user.get('username', user.get('first_name', 'User'))
        
        logger.info(f"Message from {username}: {text}")
        
        # Skip commands
        if text.startswith('/'):
            if text == '/start':
                self.send_message(chat_id, "🤖 *Trading Bot Active*\n\nSend a signal like:\n`BTCUSD BUY 50000`")
            elif text == '/help':
                self.send_message(chat_id, "Send a trading signal: `BTCUSD BUY 50000`")
            elif text == '/status':
                self.send_status(chat_id)
            return
        
        # Parse signal
        signal = self.parse_signal(text)
        
        if not signal:
            self.send_message(chat_id, "❌ Invalid format. Use: `BTCUSD BUY 50000`")
            return
        
        # Store in knowledge exchange
        if not hasattr(self.app, 'knowledge_exchanges'):
            self.app.knowledge_exchanges = []
        
        signal_entry = {
            'id': len(self.app.knowledge_exchanges) + 1,
            'from_agent': f'📡 {username}',
            'to_agent': 'ALL AGENTS',
            'topic': f'🎯 Signal: {signal["asset"]} {signal["action"]}',
            'content': f"Price: ${signal['price']:,.2f}\nConfidence: {signal['confidence']}%",
            'xp_reward': 0,
            'token_reward': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_signal': True
        }
        self.app.knowledge_exchanges.insert(0, signal_entry)
        
        # Get agent votes
        market_features = {
            'z_score_20': 0.5,
            'rsi_14': 55,
            'trend_strength': 60
        }
        
        votes = self.agent_manager.collect_votes(signal, market_features)
        
        # Calculate results
        buy_votes = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell_votes = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        total = len(votes)
        
        buy_percent = round(buy_votes / total * 100, 1)
        sell_percent = round(sell_votes / total * 100, 1)
        
        final_decision = 'BUY' if buy_votes > sell_votes else 'SELL' if sell_votes > buy_votes else 'HOLD'
        
        # Build response
        response = f"📊 *Voting Results*\n\n"
        response += f"Signal: {signal['action']} {signal['asset']} @ ${signal['price']:,.2f}\n\n"
        response += f"BUY: {buy_votes}/{total} ({buy_percent}%)\n"
        response += f"SELL: {sell_votes}/{total} ({sell_percent}%)\n\n"
        
        for agent_name, vote_data in votes.items():
            icon = "🟢" if vote_data['vote'] == 'BUY' else "🔴" if vote_data['vote'] == 'SELL' else "⚪"
            response += f"{icon} {agent_name}: {vote_data['vote']} ({vote_data['confidence']:.0f}%)\n"
        
        response += f"\n*Final Decision:* {final_decision}"
        
        self.send_message(chat_id, response)
    
    def send_status(self, chat_id):
        """Send agent status"""
        agents = self.agent_manager.get_all_status()
        message = "📊 *Agent Status*\n\n"
        for agent in agents:
            message += f"🤖 {agent['name']}: {agent['vote_accuracy']}% accuracy\n"
        self.send_message(chat_id, message)
    
    def run(self):
        """Run the bot (polling)"""
        import requests
        
        self.running = True
        logger.info("Starting Telegram bot polling...")
        
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                params = {'offset': self.last_update_id + 1, 'timeout': 30}
                
                response = requests.get(url, params=params, timeout=35)
                data = response.json()
                
                if data.get('ok'):
                    for update in data.get('result', []):
                        self.last_update_id = update['update_id']
                        if 'message' in update:
                            self.process_message(update['message'])
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Bot polling error: {e}")
                time.sleep(5)
    

    def start(self):
        """Start bot in background thread"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("Telegram bot thread started")
        return thread
def trigger_agent_voting(self, chat_id, signal, raw_message):
    """Trigger agent voting on a signal"""
    
    # Prepare market features
    market_features = {
        'z_score_20': 0.5,
        'rsi_14': 55,
        'trend_strength': 60
    }
    
    # Get votes from agents
    votes = self.agent_manager.collect_votes(signal, market_features)
    
    # Calculate results
    buy_votes = sum(1 for v in votes.values() if v['vote'] == 'BUY')
    sell_votes = sum(1 for v in votes.values() if v['vote'] == 'SELL')
    total = len(votes)
    
    final_decision = 'BUY' if buy_votes > sell_votes else 'SELL' if sell_votes > buy_votes else 'HOLD'
    
    # Build response
    response = f"🗳️ *Voting Results*\n\n"
    response += f"Signal: {signal['action']} {signal['asset']} @ ${signal['price']:.2f}\n\n"
    response += f"BUY: {buy_votes}/{total}\n"
    response += f"SELL: {sell_votes}/{total}\n\n"
    
    for agent_name, vote_data in votes.items():
        icon = "🟢" if vote_data['vote'] == 'BUY' else "🔴" if vote_data['vote'] == 'SELL' else "⚪"
        response += f"{icon} {agent_name}: {vote_data['vote']} ({vote_data['confidence']:.0f}%)\n"
    
    response += f"\n✅ *Final Decision:* {final_decision}"
    
    self.send_message(chat_id, response)
    
    # Store in knowledge exchange
    if hasattr(self.app, 'knowledge_exchanges'):
        entry = {
            'id': len(self.app.knowledge_exchanges) + 1,
            'from_agent': f'📡 {signal["asset"]} Signal',
            'to_agent': 'ALL AGENTS',
            'topic': f'🎯 {signal["action"]} {signal["asset"]}',
            'content': f"Price: ${signal['price']:.2f}\nDecision: {final_decision}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_signal': True
        }
        self.app.knowledge_exchanges.insert(0, entry)

def send_prices(self, chat_id):
    """Send current prices"""
    if self.price_service:
        prices = self.price_service.get_all_prices()
        response = "📊 *Current Market Prices*\n\n"
        for name, price in list(prices.items())[:5]:
            response += f"• {name}: ${price:.2f}\n"
        self.send_message(chat_id, response)
