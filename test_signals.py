#!/usr/bin/env python3
"""
Test signal generation
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.services.price_service import get_price_service

print("=" * 60)
print("TESTING SIGNAL GENERATION")
print("=" * 60)

# Get price service
service = get_price_service()

# Get all prices
print("\n[1] Current Prices:")
prices = service.get_all_prices()
for key, value in prices.items():
    print(f"  {key}: {value}")

# Generate signals
print("\n[2] Generated Signals:")
signals = service.generate_signals()

if signals:
    for signal in signals:
        print(f"  {signal['name']}: {signal['action']} @ ${signal['price']} ({signal['confidence']}%)")
else:
    print("  ❌ No signals generated!")

print("\n[3] Checking price service methods:")
print(f"  get_price('GOLD'): {service.get_price('GOLD')}")
print(f"  get_price('SILVER'): {service.get_price('SILVER')}")
print(f"  get_price('WTI'): {service.get_price('WTI')}")

print("\n" + "=" * 60)
