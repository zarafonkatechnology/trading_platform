#!/usr/bin/env python3
"""
Test MT4 Price Fetcher
"""

from mt4_prices import mt4_prices

print("=" * 50)
print("🧪 Testing MT4 Price Fetcher")
print("=" * 50)

# Test connection
if mt4_prices.test_connection():
    print("✅ MT4 is connected!")
else:
    print("❌ MT4 not responding. Make sure EA is running.")
    exit()

# Get all prices
print("\n📊 Fetching live prices from MT4...")
prices = mt4_prices.get_live_prices()

for asset, data in prices.items():
    print(f"\n{asset}:")
    print(f"   Bid: {data['bid']}")
    print(f"   Ask: {data['ask']}")
    print(f"   Mid: {data['mid']}")
    print(f"   Spread: {data['spread']}")

print("\n" + "=" * 50)
print("✅ Test complete!")
