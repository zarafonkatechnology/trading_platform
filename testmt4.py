# test_mt4_provider.py
"""
TEST 2: MT4 Price Provider Test
Tests the mt4_price_provider.py module
"""

import sys
import time

print("=" * 60)
print("TEST 2: MT4 PRICE PROVIDER TEST")
print("=" * 60)

try:
    from mt4_price_provider import get_mt4_prices
    print("✅ Successfully imported mt4_price_provider")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

print("\n1. Initializing MT4 Provider...")
mt4 = get_mt4_prices()
print(f"   Provider: {mt4}")

# Test connection
print("\n2. Testing Connection...")
connected = mt4.test_connection()
print(f"   Connected: {connected}")

if not connected:
    print("   ⚠️ Warning: test_connection() returned False")
    print("   This might be because PING command is not supported")
    print("   Proceeding with other tests...")

# Test account
print("\n3. Testing get_account_info()...")
try:
    info = mt4.get_account_info()
    if info:
        print(f"   ✅ Balance: ${info['balance']:.2f}")
        print(f"   ✅ Equity: ${info['equity']:.2f}")
        print(f"   ✅ Margin: ${info['margin']:.2f}")
        print(f"   ✅ Free Margin: ${info['free_margin']:.2f}")
    else:
        print("   ❌ No account info returned")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test ALL_PRICES
print("\n4. Testing get_all_prices()...")
try:
    prices = mt4.get_all_prices()
    if prices:
        print(f"   ✅ Got {len(prices)} prices")
        for symbol, price in list(prices.items())[:10]:
            print(f"      {symbol}: {price}")
    else:
        print("   ❌ No prices returned")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test individual price
print("\n5. Testing get_price('EURUSD')...")
try:
    result = mt4.get_price('EURUSD')
    if result and result.get('success'):
        print(f"   ✅ EURUSD: {result.get('bid')}")
    else:
        print(f"   ❌ Error: {result.get('error') if result else 'No response'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test individual price - NASDAQ
print("\n6. Testing get_price('#NASDAQ100')...")
try:
    result = mt4.get_price('#NASDAQ100')
    if result and result.get('success'):
        print(f"   ✅ #NASDAQ100: {result.get('bid')}")
    else:
        print(f"   ❌ Error: {result.get('error') if result else 'No response'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("TEST 2 COMPLETE")
print("=" * 60)