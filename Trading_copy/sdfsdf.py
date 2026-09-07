# test_spread_fixed.py
"""
Test the fixed Spread API
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_spread_api():
    print("\n" + "="*60)
    print("📊 TESTING FIXED SPREAD API")
    print("="*60)
    
    # Test health
    print("\n1. Testing health...")
    try:
        response = requests.get(f"{BASE_URL}/spread/health")
        print(f"   ✅ Health: {response.json()}")
    except Exception as e:
        print(f"   ❌ Health error: {e}")
    
    # Test all spreads
    print("\n2. Testing all spreads...")
    try:
        response = requests.get(f"{BASE_URL}/spread/all")
        data = response.json()
        if data.get('success'):
            spreads = data.get('data', {})
            print(f"   ✅ Got {len(spreads)} symbols")
            for symbol, spread in list(spreads.items())[:5]:
                print(f"      {symbol}: {spread.get('client_spread_pips', 0):.1f} pips")
        else:
            print(f"   ❌ Failed: {data}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test specific symbol
    print("\n3. Testing EURUSD spread...")
    try:
        response = requests.get(f"{BASE_URL}/spread/client/EURUSD")
        data = response.json()
        if data.get('success'):
            spread = data.get('data', {})
            print(f"   ✅ EURUSD: {spread.get('client_spread_pips', 0):.1f} pips")
            print(f"      Broker: {spread.get('broker_spread_pips', 0):.1f} pips")
            print(f"      Markup: {spread.get('markup_pips', 0):.1f} pips")
        else:
            print(f"   ❌ Failed: {data}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_spread_api()