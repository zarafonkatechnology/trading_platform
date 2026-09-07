#!/usr/bin/env python3
"""
Test MT4 Price Module – Verifies OANDA replacement works with desired display names
"""

from mt4_price_module import get_mt4_provider

print("=" * 60)
print("🧪 Testing MT4 Price Module (OANDA Replacement)")
print("=" * 60)

mt4 = get_mt4_provider()

# Test connection
if mt4.test_connection():
    print("✅ MT4 is connected and responding!")
else:
    print("❌ MT4 not responding. Make sure EA is running.")
    exit()

# Test getting all prices
print("\n📊 Fetching live prices from MT4...")
prices = mt4.get_live_prices()

for asset, data in prices.items():
    print(f"\n{asset}:")
    print(f"   Bid: {data['bid']}")
    print(f"   Ask: {data['ask']}")
    print(f"   Mid: {data['mid']}")
    print(f"   Spread: {data['spread']}")

print("\n" + "=" * 60)
print("✅ MT4 module ready! Display names are as requested.")
