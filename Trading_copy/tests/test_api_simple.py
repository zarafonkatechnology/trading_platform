# test_api_simple.py
"""
Simple test for the API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Testing Trading Platform API")
    print("=" * 60)
    
    endpoints = [
        ("/", "Root"),
        ("/health", "Health"),
        ("/ping", "Ping"),
        ("/api/v1/trades/symbols", "Symbols"),
        ("/api/v1/trades/price/EURUSD", "Price"),
        ("/api/v1/trades/positions", "Positions"),
        ("/api/v1/trades/stats", "Stats"),
        ("/api/v1/dashboard/data", "Dashboard"),
        ("/api/v1/signals", "Signals")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=3)
            if response.status_code == 200:
                print(f"✅ {name:20} - Status: {response.status_code}")
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"   Keys: {keys[:5]}")
                except:
                    pass
            else:
                print(f"❌ {name:20} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {name:20} - Error: {str(e)[:50]}")
    
    print("=" * 60)
    print("✅ Test complete!")

if __name__ == "__main__":
    test_api()