# test_api.py
import requests
import json
from datetime import datetime

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Trading Platform API")
    print("=" * 60)
    
    endpoints = [
        ("/", "Root"),
        ("/health", "Health"),
        ("/ping", "Ping"),
        ("/api/v1/status", "API Status"),
        ("/api/v1/trades/symbols", "Symbols"),
        ("/api/v1/trades/price/EURUSD", "Price"),
        ("/api/v1/trades/positions", "Positions"),
        ("/api/v1/trades/stats", "Stats"),
        ("/api/v1/dashboard/data", "Dashboard Data"),
        ("/api/v1/dashboard/prices", "Dashboard Prices"),
        ("/api/v1/dashboard/account", "Dashboard Account"),
        ("/api/v1/signals", "Signals")
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=3)
            if response.status_code == 200:
                status = "✅ PASS"
                print(f"{status} {name:20} - Status: {response.status_code}")
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:5]}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                status = "❌ FAIL"
                print(f"{status} {name:20} - Status: {response.status_code}")
                print(f"   Error: {response.text[:100]}")
        except requests.exceptions.ConnectionError:
            print(f"❌ FAIL {name:20} - Connection Error (API not running)")
        except Exception as e:
            print(f"❌ FAIL {name:20} - Error: {str(e)[:50]}")
        
        print()
    
    print("=" * 60)
    print("✅ Test complete!")

if __name__ == "__main__":
    test_endpoints()