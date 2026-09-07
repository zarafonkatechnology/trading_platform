#!/usr/bin/env python3
"""
Test complete Telegram message with all fields
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from telegram_bot import TelegramBot

def test_complete_message():
    print("=" * 60)
    print("📱 TESTING COMPLETE TELEGRAM MESSAGE")
    print("=" * 60)
    
    bot = TelegramBot()
    
    if not bot.enabled:
        print("❌ Telegram bot not configured")
        return
    
    # Test data
    asset = "XAU/USD"
    market_data = {
        'price': 2385.50,
        'symbol': 'XAU/USD',
        'status': 'LIVE',
        'volatility': 0.85,
        'stoploss': 2337.79,
        'takeprofit': 2433.21,
        'support': 2361.65,
        'resistance': 2409.36,
        'timeframe': 15
    }
    
    agent_results = {
        'Agent_A': {'vote': 'BUY', 'confidence': 84},
        'Agent_B': {'vote': 'BUY', 'confidence': 65},
        'Agent_C': {'vote': 'HOLD', 'confidence': 89},
        'Agent_D': {'vote': 'BUY', 'confidence': 62},
        'Agent_E': {'vote': 'BUY', 'confidence': 78},
        'Agent_F': {'vote': 'BUY', 'confidence': 69}
    }
    
    ensemble = {
        'signal': 'BUY',
        'confidence': 0.83,
        'buy_pct': 83,
        'sell_pct': 0,
        'hold_pct': 17,
        'buy_count': 5,
        'sell_count': 0,
        'hold_count': 1
    }
    
    print("\n📤 Sending test message...")
    result = bot.send(asset, market_data, agent_results, ensemble)
    
    if result:
        print("\n✅ Test message sent! Check your Telegram.")
    else:
        print("\n❌ Failed to send message")

if __name__ == '__main__':
    test_complete_message()
