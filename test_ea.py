# test_ea_fixed.py
from mt4_price_provider import get_mt4_prices

print("Testing EA v3.7 - Command Parsing Fixed")
print("=" * 50)

mt4 = get_mt4_prices()

# Test PING
print("\n1. PING:")
result = mt4._send({"command": "PING"})
print(f"   {result}")

# Test ACCOUNT
print("\n2. ACCOUNT:")
result = mt4._send({"command": "ACCOUNT"})
print(f"   {result}")

# Test PRICE (EURUSD)
print("\n3. PRICE (EURUSD):")
result = mt4.get_price('EURUSD')
print(f"   {result}")

# Test PRICE (NASDAQ)
print("\n4. PRICE (#NASDAQ100):")
result = mt4.get_price('#NASDAQ100')
print(f"   {result}")