# test_mt4_diagnose.py - Full MT4 Diagnostic Test
"""
Run this script to diagnose MT4 connection issues step by step.
"""

import os
import sys
import json
import time
from pathlib import Path

print("\n" + "="*70)
print("🔍 MT4 DIAGNOSTIC TEST")
print("="*70)

# ============================================================
# STEP 1: Check File Paths
# ============================================================
print("\n📁 STEP 1: Checking File Paths...")

mt4_paths = [
    "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/",
    "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/",
]

found_path = None
for path in mt4_paths:
    if os.path.exists(path):
        print(f"   ✅ Found: {path}")
        found_path = path
        break
    else:
        print(f"   ❌ Not found: {path}")

if not found_path:
    print("\n   ❌ No MT4 Files directory found!")
    print("   💡 Make sure MetaTrader 4 is installed and the terminal is running")
    sys.exit(1)

# ============================================================
# STEP 2: Check Files
# ============================================================
print("\n📄 STEP 2: Checking Command/Response Files...")

command_file = os.path.join(found_path, "AI_Commands.txt")
response_file = os.path.join(found_path, "AI_Responses.txt")

print(f"   Command file: {command_file}")
print(f"   Response file: {response_file}")

# Clean up old files
for filepath in [command_file, response_file]:
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"   🗑️ Removed: {os.path.basename(filepath)}")
        except:
            print(f"   ⚠️ Could not remove: {os.path.basename(filepath)}")

# ============================================================
# STEP 3: Import MT4 Provider
# ============================================================
print("\n📦 STEP 3: Importing MT4 Price Provider...")

try:
    from mt4_price_provider import get_mt4_prices, MT4PriceProvider
    print("   ✅ Import successful")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print("   💡 Check if mt4_price_provider.py is in your path")
    sys.exit(1)

# ============================================================
# STEP 4: Create Provider Instance
# ============================================================
print("\n🔧 STEP 4: Creating MT4 Provider Instance...")

try:
    # Create with specific path
    provider = MT4PriceProvider(found_path)
    print("   ✅ Provider created successfully")
    print(f"   📁 Using: {found_path}")
except Exception as e:
    print(f"   ❌ Provider creation failed: {e}")
    sys.exit(1)

# ============================================================
# STEP 5: Test ACCOUNT Command
# ============================================================
print("\n💳 STEP 5: Testing ACCOUNT Command...")

try:
    # Write ACCOUNT command
    account_file = os.path.join(found_path, "AI_Commands.txt")
    with open(account_file, 'w', encoding='utf-8') as f:
        f.write('ACCOUNT')
    print(f"   ✅ Wrote 'ACCOUNT' to {account_file}")
    
    # Wait for response
    response_file = os.path.join(found_path, "AI_Responses.txt")
    print("   ⏳ Waiting for MT4 response...")
    
    response = None
    for attempt in range(20):  # 2 seconds total
        if os.path.exists(response_file):
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    response = json.loads(content)
                    print(f"   ✅ Got response on attempt {attempt+1}")
                    break
            except:
                pass
        time.sleep(0.1)
    
    if response:
        print(f"\n   📊 ACCOUNT Response:")
        print(f"      Type: {type(response)}")
        print(f"      Keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        if isinstance(response, dict):
            for key, value in response.items():
                print(f"      {key}: {value}")
    else:
        print("   ❌ No response received from MT4")
        
except Exception as e:
    print(f"   ❌ ACCOUNT test failed: {e}")

# ============================================================
# STEP 6: Test PRICE Command
# ============================================================
print("\n💰 STEP 6: Testing PRICE Command...")

try:
    # Write PRICE command
    price_file = os.path.join(found_path, "AI_Commands.txt")
    with open(price_file, 'w', encoding='utf-8') as f:
        json.dump({"command": "PRICE", "symbol": "EURUSD"}, f)
    print(f"   ✅ Wrote PRICE command to {price_file}")
    
    # Wait for response
    response_file = os.path.join(found_path, "AI_Responses.txt")
    print("   ⏳ Waiting for MT4 response...")
    
    response = None
    for attempt in range(20):
        if os.path.exists(response_file):
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    response = json.loads(content)
                    print(f"   ✅ Got response on attempt {attempt+1}")
                    break
            except:
                pass
        time.sleep(0.1)
    
    if response:
        print(f"\n   📊 PRICE Response:")
        print(f"      Type: {type(response)}")
        print(f"      Keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        if isinstance(response, dict):
            for key, value in response.items():
                print(f"      {key}: {value}")
            
            # Check for bid/ask
            if 'bid' in response or 'ask' in response:
                print(f"   ✅ Price data available: Bid={response.get('bid')}, Ask={response.get('ask')}")
            else:
                print(f"   ⚠️ No price data in response")
    else:
        print("   ❌ No response received from MT4")
        
except Exception as e:
    print(f"   ❌ PRICE test failed: {e}")

# ============================================================
# STEP 7: Test ALL_PRICES Command
# ============================================================
print("\n📊 STEP 7: Testing ALL_PRICES Command...")

try:
    # Write ALL_PRICES command
    prices_file = os.path.join(found_path, "AI_Commands.txt")
    with open(prices_file, 'w', encoding='utf-8') as f:
        f.write('ALL_PRICES')
    print(f"   ✅ Wrote 'ALL_PRICES' to {prices_file}")
    
    # Wait for response
    response_file = os.path.join(found_path, "AI_Responses.txt")
    print("   ⏳ Waiting for MT4 response...")
    
    response = None
    for attempt in range(20):
        if os.path.exists(response_file):
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    response = json.loads(content)
                    print(f"   ✅ Got response on attempt {attempt+1}")
                    break
            except:
                pass
        time.sleep(0.1)
    
    if response:
        print(f"\n   📊 ALL_PRICES Response:")
        print(f"      Type: {type(response)}")
        print(f"      Keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        if isinstance(response, dict):
            for key, value in list(response.items())[:10]:  # Show first 10
                print(f"      {key}: {value}")
            if len(response) > 10:
                print(f"      ... and {len(response)-10} more")
    else:
        print("   ❌ No response received from MT4")
        
except Exception as e:
    print(f"   ❌ ALL_PRICES test failed: {e}")

# ============================================================
# STEP 8: Test Using Provider's _send Method
# ============================================================
print("\n🔄 STEP 8: Testing provider._send() method...")

try:
    # Test ACCOUNT
    print("\n   Testing ACCOUNT via _send...")
    result = provider._send({"command": "ACCOUNT"})
    print(f"   Result: {result}")
    
    # Test PRICE
    print("\n   Testing PRICE via _send...")
    result = provider._send({"command": "PRICE", "symbol": "EURUSD"})
    print(f"   Result: {result}")
    
except Exception as e:
    print(f"   ❌ _send test failed: {e}")

# ============================================================
# STEP 9: Test get_mt4_prices Singleton
# ============================================================
print("\n🔧 STEP 9: Testing get_mt4_prices() singleton...")

try:
    mt4 = get_mt4_prices()
    print(f"   ✅ Got MT4 instance: {type(mt4)}")
    
    # Test price
    price = mt4.get_price("EURUSD")
    print(f"   EURUSD Price: {price}")
    print(f"   Price type: {type(price)}")
    
    # Test get_all_prices
    prices = mt4.get_all_prices()
    print(f"   All prices: {len(prices)} symbols")
    if prices:
        for symbol, p in list(prices.items())[:5]:
            print(f"      {symbol}: {p}")
    
except Exception as e:
    print(f"   ❌ Singleton test failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# STEP 10: Test Trading Controller Import
# ============================================================
print("\n🏗️ STEP 10: Testing Trading Controller Import...")

try:
    from trading_controller2 import ForexTradingController, FOREX_PAIRS
    print(f"   ✅ Controller imported successfully")
    print(f"   📊 FOREX_PAIRS: {len(FOREX_PAIRS)} pairs")
    print(f"      {FOREX_PAIRS[:5]}...")
except Exception as e:
    print(f"   ❌ Controller import failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*70)
print("📋 DIAGNOSTIC SUMMARY")
print("="*70)

# Check what we found
issues = []
successes = []

if found_path:
    successes.append(f"✅ MT4 Files directory found: {found_path}")
else:
    issues.append("❌ MT4 Files directory NOT found")

if os.path.exists(command_file) or os.path.exists(response_file):
    successes.append("✅ Command/Response files exist")
else:
    issues.append("⚠️ Command/Response files not found (will be created)")

# Try to get provider
try:
    mt4 = get_mt4_prices()
    price = mt4.get_price("EURUSD")
    if price and float(price) > 0:
        successes.append(f"✅ Price retrieval working: EURUSD = {price}")
    else:
        issues.append("⚠️ Price retrieval returned 0")
except:
    issues.append("❌ Could not get MT4 provider")

# Print results
print("\n✅ SUCCESSES:")
for s in successes:
    print(f"   {s}")

print("\n⚠️ ISSUES:")
for i in issues:
    print(f"   {i}")

print("\n" + "="*70)

if issues:
    print("\n💡 RECOMMENDATIONS:")
    print("   1. Make sure MetaTrader 4 is OPEN and RUNNING")
    print("   2. Make sure the EA is attached to a chart")
    print("   3. Make sure 'Allow Automated Trading' is ENABLED")
    print("   4. Check the Experts tab in MT4 for error messages")
    print("   5. The system will work in SIMULATION mode without MT4")
else:
    print("\n🎉 All tests passed! MT4 is working correctly.")

print("="*70 + "\n")