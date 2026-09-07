#!/usr/bin/env python3
"""
Direct test of price service
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.services.price_service import get_price_service

print("Testing Price Service...")
print("-" * 40)

# Get service
service = get_price_service()

# Get prices
prices = service.get_all_prices()

print("Current Prices:")
for symbol, price in prices.items():
    print(f"  {symbol}: ${price}")

print("-" * 40)
print("Prices should be non-zero values!")
