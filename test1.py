# test1.py
from mt4_price_provider import get_mt4_prices
import time

print("Testing MT4 Connection")
print("=" * 40)

mt4 = get_mt4_prices()

# Test connection
connected = mt4.test_connection()
print(f"Connected: {connected}")

# Test balance
info = mt4.get_account_info()
if info:
    print(f"✅ Balance: ${info['balance']:.2f}")
else:
    print("❌ No balance")

# Test price
price = mt4.get_price('EURUSD')
if price and price.get('success'):
    print(f"✅ EURUSD: {price.get('bid')}")
else:
    print(f"❌ Error: {price.get('error') if price else 'No response'}")