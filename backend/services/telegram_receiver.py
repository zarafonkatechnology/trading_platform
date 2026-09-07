"""
Telegram Bot Receiver - Receives real signals from Telegram
"""

import os
import requests
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class TelegramReceiver:
    """Receives real Telegram messages and stores them"""
    
    def __init__(self, db_manager):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.db = db_manager
        self.last_update_id = 0
        self.is_running = False
        
        if not self.token:
            print("⚠️ TELEGRAM_BOT_TOKEN not set. Bot disabled.")
    
    def start(self):
        """Start receiving messages"""
        if not self.token:
            return
        
        self.is_running = True
        thread = threading.Thread(target=self._poll_messages, daemon=True)
        thread.start()
        print("✅ Telegram receiver started - Listening for real signals")
    
    def _poll_messages(self):
        """Poll Telegram for new messages"""
        while self.is_running:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                params = {'offset': self.last_update_id + 1, 'timeout': 30}
                response = requests.get(url, params=params, timeout=35)
                data = response.json()
                
                if data.get('ok'):
                    for update in data.get('result', []):
                        self.last_update_id = update['update_id']
                        if 'message' in update:
                            self._process_message(update['message'])
                time.sleep(1)
            except Exception as e:
                print(f"Poll error: {e}")
                time.sleep(5)
    
    def _process_message(self, message):
        """Process incoming Telegram message"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        username = user.get('first_name', user.get('username', 'User'))
        
        print(f"\n📨 Received from @{username}: {text}")
        
        # Parse as trading signal
        signal = self._parse_signal(text)
        
        if signal:
            # Store in database
            self._store_signal(signal, text, chat_id, message['message_id'])
            
            # Send confirmation
            self._send_confirmation(chat_id, signal)
        else:
            self._send_help(chat_id)
    
    def _parse_signal(self, text: str) -> Optional[Dict]:
        """Parse trading signal from text"""
        import re
        
        text_upper = text.upper().strip()
        
        # Pattern: ASSET ACTION PRICE
        # Example: "GOLD BUY 2350" or "XAU/USD BUY 2350.50"
        pattern = r'^([A-Za-z0-9/]+)\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)'
        match = re.match(pattern, text_upper)
        
        if match:
            asset = match.group(1)
            action = match.group(2)
            price = float(match.group(3))
            
            # Map common asset names
            asset_map = {
                'GOLD': 'XAU/USD',
                'SILVER': 'XAG/USD',
                'OIL': 'BCO/USD',
                'WTI': 'WTICO/USD',
                'SP500': 'S&P500/USD',
                'NAS100': 'NAS100/USD',
                'EURUSD': 'EURUSD',
                'GBPUSD': 'GBPUSD',
                'USDJPY': 'USDJPY'
            }
            
            asset_display = asset_map.get(asset, asset)
            
            return {
                'asset_type': asset_display,
                'action': action,
                'price': price,
                'confidence': 75,
                'strength': 'SIGNAL',
                'raw': text
            }
        
        return None
    
    def _store_signal(self, signal: Dict, raw_message: str, chat_id: int, message_id: int):
        """Store signal in database"""
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO telegram_signals (asset_type, current_price, confidence_percent, 
                    signal_strength, data_source, raw_message, received_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                signal['asset_type'],
                signal['price'],
                signal['confidence'],
                signal['strength'],
                'TELEGRAM_LIVE',
                raw_message,
                datetime.now()
            ))
            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ Signal stored: {signal['asset_type']} {signal['action']} @ ${signal['price']}")
        except Exception as e:
            print(f"Error storing signal: {e}")
    
    def _send_confirmation(self, chat_id: int, signal: Dict):
        """Send confirmation message"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        message = f"""
✅ *Signal Received!*

📊 *{signal['asset_type']}*
🎯 *Action:* {signal['action']}
💰 *Price:* ${signal['price']:.2f}
📈 *Confidence:* {signal['confidence']}%

🔄 Sending to agents for voting...
"""
        
        try:
            requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=10)
        except Exception as e:
            print(f"Error sending confirmation: {e}")
    
    def _send_help(self, chat_id: int):
        """Send help message"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        message = """
🤖 *Trading Bot Commands*

Send a trading signal in this format:

`GOLD BUY 2350`
`SILVER SELL 28.50`
`EURUSD BUY 1.0890`

*Supported Assets:*
🥇 GOLD → XAU/USD
🥈 SILVER → XAG/USD
🛢️ OIL → BCO/USD
📊 SP500 → S&P500/USD
💶 EURUSD → EURUSD
"""
        
        try:
            requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=10)
        except Exception as e:
            print(f"Error sending help: {e}")
