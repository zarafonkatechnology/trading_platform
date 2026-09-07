#!/usr/bin/env python3
"""
Test MT4 Real-Time Connection 
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt4_price_provider import get_mt4_prices

print("=" * 60)
print("TESTING MT4 REAL-TIME CONNECTION")
print("=" * 60)

# Initialize MT4 provider
print("\n📡 Connecting to MetaTrader 4...")
mt4 = get_mt4_prices()

# Test connection
print("\n[1] Testing MT4 connection...")
if mt4.test_connection():
    print("✅ MT4 is ONLINE and responding")
else:
    print("❌ ERROR: MT4 not connected!")
    print("\nPlease check:")
    print("  1. MetaTrader 4 is running")
    print("  2. EA is attached to chart (smiley face)")
    print("  3. AI_Commands.txt / AI_Responses.txt are being created")
    exit(1)

# Test 2: Get account info
print("\n[2] Getting account info...")
balance = mt4.get_account_balance()
if balance > 0:
    print(f"✅ Connected! Balance: ${balance:,.2f}")
else:
    print(f"⚠️ Balance: ${balance:,.2f} (might be demo account)")

# Test 3: Get LIVE prices for Gold, Oil, S&P 500, etc.
print("\n[3] Getting LIVE prices from MT4...")

# Symbols to test (MT4 format)
test_symbols = [
    ('GOLD', 'GOLD', 'Gold'),
    ('SILVER', 'SILVER', 'Silver'),
    ('BRENT_OIL', 'BRENT_OIL', 'Brent Oil'),
    ('CrudeOIL', 'CrudeOIL', 'CrudeOIL'),
    ('S&P500', 'S&P500', 'S&P 500'),
    ('NASDAQ100', 'NASDAQ100', 'NASDAQ 100'),
    ('DJ30', 'DJ30', 'Dow Jones'),
    ('EURUSD', 'EURUSD', 'Euro'),
    ('GBPUSD', 'GBPUSD', 'British Pound'),
]

print("\n📊 LIVE MARKET PRICES FROM MT4:")
print("-" * 60)

for display_name, mt4_symbol, description in test_symbols:
    price_data = mt4.get_price(mt4_symbol)
    
    if price_data.get('success'):
        bid = price_data.get('bid', 0)
        ask = price_data.get('ask', 0)
        mid = (bid + ask) / 2
        
        # Format based on instrument type
        if 'USD' in display_name and display_name not in ['XAU/USD', 'XAG/USD']:
            # Forex pairs
            print(f"  {display_name:12}: Bid={bid:.5f}, Ask={ask:.5f}, Mid={mid:.5f}")
        else:
            # Commodities and indices
            print(f"  {display_name:12}: Bid=${bid:.2f}, Ask=${ask:.2f}, Mid=${mid:.2f}")
    else:
        print(f"  {display_name:12}: ❌ No data (symbol: {mt4_symbol})")

print("\n" + "=" * 60)
print("If you see prices above, MT4 is working correctly!")
print("=" * 60)
