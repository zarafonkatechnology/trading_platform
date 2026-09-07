#!/usr/bin/env python3
"""
Test Telegram Bot with Scheduler - Send messages every minute
"""

import time
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    """Send message to Telegram"""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cycle():
    """Test cycle - runs every minute"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running test cycle...")
    
    # Get agent stats (if your app is running)
    try:
        import requests as req
        response = req.get('http://localhost:5000/api/agents', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                agents = data.get('agents', [])
                total_xp = sum(a.get('xp_points', 0) for a in agents)
                
                message = f"""
📊 *Trading System Update*
⏱️ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Agents: {len(agents)}
💰 Total XP: {total_xp}

_System is running normally_
"""
                send_telegram_message(message)
                print("✅ Telegram message sent")
                return
    except Exception as e:
        print(f"Could not connect to app: {e}")
    
    # Fallback message
    message = f"""
🔄 *Test Scheduler Message*
⏱️ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ Your Telegram bot is working!

_This is a test message from your trading system scheduler._
"""
    send_telegram_message(message)
    print("✅ Telegram message sent")

if __name__ == '__main__':
    print("=" * 60)
    print("📡 TELEGRAM SCHEDULER TEST")
    print("=" * 60)
    
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        print("   Please add: TELEGRAM_BOT_TOKEN=your_token")
        exit(1)
    
    if not CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not found in .env")
        print("   Please add: TELEGRAM_CHAT_ID=your_chat_id")
        exit(1)
    
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")
    print(f"✅ Chat ID: {CHAT_ID}")
    print("\n🚀 Starting test cycle - will send message every 60 seconds")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Send one immediately
        test_cycle()
        
        # Then every 60 seconds
        while True:
            time.sleep(60)
            test_cycle()
    except KeyboardInterrupt:
        print("\n\n🛑 Test stopped by user")
