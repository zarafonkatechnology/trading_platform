# test_dashboard.py
"""
TEST 3: Performance Dashboard Test
Tests the dashboard API without running the full server
"""

import sys
import json
import time

print("=" * 60)
print("TEST 3: PERFORMANCE DASHBOARD TEST")
print("=" * 60)

try:
    from performance_dashboard import app, api_dashboard_data
    print("✅ Successfully imported performance_dashboard")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Test 1: Check if app exists
print("\n1. Checking Flask app...")
if app:
    print(f"   ✅ Flask app exists")
    print(f"   App name: {app.name}")
else:
    print("   ❌ App is None")

# Test 2: Test API endpoint directly
print("\n2. Testing api_dashboard_data() directly...")
try:
    # Call the API function directly
    with app.app_context():
        response = api_dashboard_data()
        
        # Check if response is valid
        if hasattr(response, 'json'):
            data = response.json
            print(f"   ✅ Response received")
            print(f"   Connected: {data.get('mt4_connected')}")
            print(f"   Balance: ${data.get('account', {}).get('balance', 0):.2f}")
            print(f"   Prices count: {len(data.get('prices', {}))}")
            
            if data.get('prices'):
                print("   First few prices:")
                for symbol, price in list(data['prices'].items())[:3]:
                    print(f"      {symbol}: {price.get('price')}")
        else:
            print(f"   ❌ Invalid response: {response}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check if Flask app can run
print("\n3. Checking Flask app configuration...")
try:
    # Check if app has routes
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    print(f"   Routes found: {len(routes)}")
    for route in routes[:5]:
        print(f"      {route}")
except Exception as e:
    print(f"   ❌ Error checking routes: {e}")

# Test 4: Check if port 5001 is available
print("\n4. Checking if port 5001 is available...")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5001))
    sock.close()
    if result == 0:
        print("   ⚠️ Port 5001 is already in use")
        print("   Another instance of dashboard may be running")
    else:
        print("   ✅ Port 5001 is available")
except Exception as e:
    print(f"   ❌ Error checking port: {e}")

print("\n" + "=" * 60)
print("TEST 3 COMPLETE")
print("=" * 60)