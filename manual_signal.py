#!/usr/bin/env python
"""
Manually generate signals to test the flow
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

# ✅ USE YOUR CORRECT CREDENTIALS
EMAIL = "zarafonkatechnology@gmail.com"
PASSWORD = "1234Lama@"

def generate_manual_signal():
    print("📡 Generating manual test signal...")
    
    # Login with correct credentials
    login = requests.post(
        f"{API_URL}/client/login",
        data={"email": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"   Login status: {login.status_code}")
    
    if login.status_code != 200:
        print(f"❌ Login failed: {login.text}")
        return
    
    data = login.json()
    token = data.get('access_token')
    
    if not token:
        print(f"❌ No token in response: {data}")
        return
    
    print(f"✅ Logged in successfully")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Generate signal
    print("📤 Sending generate request...")
    response = requests.post(
        f"{API_URL}/signals/generate",
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Signal generated: {data.get('signal', {}).get('symbol')} {data.get('signal', {}).get('signal_type')}")
            print(f"   ID: {data.get('signal', {}).get('id')}")
        else:
            print(f"⚠️ Failed: {data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Failed: {response.text}")

if __name__ == "__main__":
    generate_manual_signal()