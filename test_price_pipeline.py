# test_mt4_connection.py
from mt4_price_provider import get_mt4_prices

print("=" * 50)
print("Testing MT4 Connection")
print("=" * 50)

mt4 = get_mt4_prices()

# Test 1: Ping MT4
print("\n1. Testing MT4 connection...")
if mt4.test_connection():
    print("   ✅ MT4 is connected and responding!")
else:
    print("   ❌ MT4 is NOT responding")
    print("\n   Check:")
    print("   - Is MT4 running?")
    print("   - Is the EA attached to a chart?")
    print("   - Check MT4 Experts tab for errors")
    print("\n   Also verify file paths exist:")
    print(f"   Commands: {mt4.command_file}")
    print(f"   Responses: {mt4.response_file}")

# Test 2: Get account balance
print("\n2. Getting account balance...")
balance = mt4.get_account_balance()
if balance > 0:
    print(f"   ✅ Account Balance: ${balance}")
else:
    print("   ❌ Could not get balance")

# Test 3: Get a single price
print("\n3. Getting live price for GOLD...")
price = mt4.get_price("SILVER")
if price.get('success'):
    print(f"   ✅ Live price: Bid={price.get('bid')}, Ask={price.get('ask')}")
else:
    print(f"   ❌ Failed: {price.get('error')}")

print("\n" + "=" * 50)
