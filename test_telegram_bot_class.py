#!/usr/bin/env python3
"""
Test your Telegram bot class
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import your bot class
# If it's in a separate file:
from telegram_bot import TelegramBot

# Or if it's defined in this file, copy the class here

def test_telegram_bot():
    print("=" * 60)
    print("📱 TESTING TELEGRAM BOT CLASS")
    print("=" * 60)
    
    # Initialize bot
    bot = TelegramBot()
    
    if not bot.enabled:
        print("\n❌ Telegram bot is DISABLED!")
        print("   Check your .env file:")
        print("   - TELEGRAM_BOT_TOKEN=your_token")
        print("   - TELEGRAM_CHAT_ID=your_chat_id")
        return
    
    print("\n✅ Telegram bot is ENABLED")
    print(f"   Token: {bot.token[:10]}...")
    print(f"   Chat ID: {bot.chat_id}")
    
    # Test sending a market snapshot
    print("\n📊 Sending test market snapshot...")
    
    test_prices = {
        'XAU/USD': {'price': 2385.50, 'symbol': 'XAU/USD', 'status': 'LIVE'},
        'XAG/USD': {'price': 28.45, 'symbol': 'XAG/USD', 'status': 'LIVE'},
        'BCO/USD': {'price': 89.75, 'symbol': 'BCO/USD', 'status': 'LIVE'},
        'EURUSD': {'price': 1.0725, 'symbol': 'EURUSD', 'status': 'LIVE'},
    }
    
    # Test send_summary
    bot.send_summary(test_prices)
    print("✅ Market snapshot sent (if configured)")
    
    # Test sending a trading signal
    print("\n📈 Sending test trading signal...")
    
    test_market_data = {
        'price': 2385.50,
        'symbol': 'XAU/USD',
        'status': 'LIVE'
    }
    
    test_agent_results = {
        'Agent_A': {'vote': 'BUY', 'confidence': 85},
        'Agent_B': {'vote': 'SELL', 'confidence': 45},
        'Agent_C': {'vote': 'BUY', 'confidence': 78},
        'Agent_D': {'vote': 'BUY', 'confidence': 72},
        'Agent_E': {'vote': 'HOLD', 'confidence': 60},
    }
    
    test_ensemble = {
        'signal': 'BUY',
        'confidence': 0.78,
        'buy_pct': 60,
        'sell_pct': 20,
        'hold_pct': 20
    }
    
    result = bot.send(
        asset='XAU/USD',
        market_data=test_market_data,
        agent_results=test_agent_results,
        ensemble=test_ensemble
    )
    
    if result:
        print("✅ Trading signal sent to Telegram!")
    else:
        print("⚠️ No signal sent (confidence may be below threshold)")
    
    print("\n" + "=" * 60)
    print("✅ Test complete! Check your Telegram bot.")
    print("=" * 60)

if __name__ == '__main__':
    test_telegram_bot()
