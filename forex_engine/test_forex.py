#!/usr/bin/env python
"""
Quick test to verify signals endpoint is working
"""

import requests
import json

API_URL = "http://localhost:8000/api/v1"
EMAIL = "zarafonkatechnology@gmail.com"
PASSWORD = "1234Lama@"

def quick_test():
    print("=" * 60)
    print("🚀 QUICK SIGNALS TEST")
    print("=" * 60)
    
    # 1. Test ping (no auth)
    print("\n1️⃣ Testing ping endpoint...")
    try:
        ping = requests.get(f"{API_URL}/signals/ping", timeout=5)
        print(f"   Status: {ping.status_code}")
        if ping.status_code == 200:
            print(f"   Response: {ping.json()}")
        else:
            print(f"   Error: {ping.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # 2. Login
    print("\n2️⃣ Logging in...")
    login = requests.post(
        f"{API_URL}/client/login",
        data={"email": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if login.status_code != 200:
        print(f"   ❌ Login failed: {login.text}")
        return
    
    token = login.json().get('access_token')
    print(f"   ✅ Login successful")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get signals
    print("\n3️⃣ Getting signals...")
    response = requests.get(f"{API_URL}/signals", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data.get('count', 0)} signals")
        for s in data.get('signals', [])[:3]:
            print(f"      - {s.get('symbol')} {s.get('type')} ({s.get('confidence')}%) - {s.get('source')}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # 4. Get stats
    print("\n4️⃣ Getting stats...")
    stats = requests.get(f"{API_URL}/signals/stats", headers=headers)
    print(f"   Status: {stats.status_code}")
    
    if stats.status_code == 200:
        data = stats.json()
        print(f"   ✅ Stats: {data.get('stats', {})}")
    else:
        print(f"   ❌ Failed: {stats.text}")
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")

if __name__ == "__main__":
    quick_test()