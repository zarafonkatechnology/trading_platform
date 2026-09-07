#!/usr/bin/env python3
"""
Test OANDA Live Prices
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Check credentials
api_key = os.getenv('OANDA_API_KEY')
account_id = os.getenv('OANDA_ACCOUNT_ID')

print("=" * 60)
print("OANDA LIVE PRICES TEST")
print("=" * 60)

if not api_key:
    print("❌ OANDA_API_KEY not found in .env")
    print("\nPlease add to .env file:")
    print("OANDA_API_KEY=your_api_key_here")
    print("OANDA_ACCOUNT_ID=your_account_id_here")
    sys.exit(1)

if not account_id:
    print("❌ OANDA_ACCOUNT_ID not found in .env")
    sys.exit(1)

print(f"✅ API Key: {api_key[:10]}...")
print(f"✅ Account ID: {account_id}")

# Import and test
sys.path.insert(0, '/home/mohammed/trading_platform')
from backend.services.oanda_realtime import get_oanda

print("\n[1] Connecting to OANDA...")
oanda = get_oanda()

if oanda.test_connection():
    print("✅ Connection successful!")
    
    print("\n[2] Getting LIVE prices...")
    print("-" * 60)
    
    prices = oanda.get_live_prices()
    
    # Display prices
    name_map = {
        'XAU/USD': '🥇 GOLD',
        'XAG/USD': '🥈 SILVER',
        'BCO/USD': '🛢️ BRENT OIL',
        'WTICO/USD': '🛢️ WTI OIL',
        'S&P500/USD': '📊 S&P 500',
        'NAS100/USD': '📈 NASDAQ',
        'EURUSD': '💶 EURO',
        'GBPUSD': '💷 BRITISH POUND',
        'USDJPY': '💴 USDJPY',
        'BTC/USD': '₿ BITCOIN'
    }
    
    print(f"\n{'Asset':<20} {'Price':<15} {'Status'}")
    print("-" * 60)
    
    for symbol, price in prices.items():
        name = name_map.get(symbol, symbol)
        if symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            print(f"{name:<20} {price:.4f} {'✅ LIVE'}")
        else:
            print(f"{name:<20} ${price:.2f} {'✅ LIVE'}")
    
    print("\n[3] Account Info:")
    account = oanda.get_account_summary()
    if account:
        print(f"   Balance: ${account.get('balance', 0):,.2f}")
        print(f"   Currency: {account.get('currency', 'USD')}")
    
    print("\n" + "=" * 60)
    print("✅ OANDA IS WORKING WITH REAL LIVE PRICES!")
    print("=" * 60)
    
else:
    print("\n❌ Connection failed!")
    print("Check your API key and Account ID")
