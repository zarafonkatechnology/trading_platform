# test_connection.py
"""
Test all connections
"""

import asyncio
import requests
import json

def test_dashboard():
    print("📊 Testing Dashboard Connection...")
    try:
        response = requests.get("http://localhost:5002/health", timeout=3)
        if response.status_code == 200:
            print("✅ Dashboard is running")
            return True
    except:
        print("❌ Dashboard not running")
        return False

def test_api():
    print("📡 Testing API Connection...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            print("✅ API is running")
            return True
    except:
        print("❌ API not running")
        return False

def test_mt4_file():
    print("📁 Testing MT4 File Connection...")
    import os
    file_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
    if os.path.exists(file_path):
        print("✅ MT4 file found")
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                print(f"📊 Data loaded: {len(data.get('prices', {}))} symbols")
            return True
        except:
            print("⚠️ File exists but can't read")
    else:
        print("❌ MT4 file not found")
    return False

def main():
    print("=" * 50)
    print("🔍 Testing Trading Platform Connections")
    print("=" * 50)
    
    dashboard_ok = test_dashboard()
    api_ok = test_api()
    mt4_ok = test_mt4_file()
    
    print("\n" + "=" * 50)
    print("📊 Connection Status:")
    print(f"  Dashboard: {'✅' if dashboard_ok else '❌'}")
    print(f"  API:       {'✅' if api_ok else '❌'}")
    print(f"  MT4:       {'✅' if mt4_ok else '❌'}")
    print("=" * 50)

if __name__ == "__main__":
    main()