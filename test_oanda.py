#!/usr/bin/env python3
"""
Test OANDA Connection
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')

print("=" * 50)
print("TESTING OANDA CONNECTION")
print("=" * 50)

if not API_KEY:
    print("❌ OANDA_API_KEY not found in .env")
    exit(1)

if not ACCOUNT_ID:
    print("❌ OANDA_ACCOUNT_ID not found in .env")
    exit(1)

print(f"✅ API Key found: {API_KEY[:10]}...")
print(f"✅ Account ID: {ACCOUNT_ID}")

# Test connection
url = "https://api-fxpractice.oanda.com/v3/accounts"
headers = {'Authorization': f'Bearer {API_KEY}'}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("✅ OANDA Connection Successful!")
        data = response.json()
        print(f"   Account: {data['accounts'][0]['id']}")
    else:
        print(f"❌ Connection failed: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
