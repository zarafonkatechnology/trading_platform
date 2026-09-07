#!/usr/bin/env python3
"""
Test OANDA API using direct REST calls (no v20 library)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
ENVIRONMENT = os.getenv('OANDA_ENVIRONMENT', 'practice')

print("=" * 50)
print("TESTING OANDA API (REST DIRECT)")
print("=" * 50)

if not API_KEY or not ACCOUNT_ID:
    print("❌ API credentials not found!")
    exit(1)

# Set base URL
if ENVIRONMENT == 'practice':
    BASE_URL = 'https://api-fxpractice.oanda.com'
else:
    BASE_URL = 'https://api-fxtrade.oanda.com'

print(f"Base URL: {BASE_URL}")
print(f"Account ID: {ACCOUNT_ID}")

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Test 1: Get account summary
print("\n[TEST 1] Getting account info...")
response = requests.get(
    f"{BASE_URL}/v3/accounts/{ACCOUNT_ID}/summary",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    account = data.get('account', {})
    print(f"✅ Connected successfully!")
    print(f"   Account ID: {account.get('id')}")
    print(f"   Balance: ${float(account.get('balance', 0)):,.2f}")
    print(f"   NAV: ${float(account.get('nav', 0)):,.2f}")
    print(f"   Currency: {account.get('currency')}")
else:
    print(f"❌ Failed: {response.status_code}")
    print(f"   Response: {response.text}")
    exit(1)

# Test 2: Get prices
print("\n[TEST 2] Getting market prices...")
symbols = ['XAU/USD', 'EURUSD', 'S&P500/USD']
response = requests.get(
    f"{BASE_URL}/v3/accounts/{ACCOUNT_ID}/pricing",
    headers=headers,
    params={'instruments': ','.join(symbols)}
)

if response.status_code == 200:
    data = response.json()
    prices = data.get('prices', [])
    for price in prices:
        instrument = price.get('instrument')
        bids = price.get('bids', [])
        asks = price.get('asks', [])
        if bids and asks:
            bid = float(bids[0].get('price', 0))
            ask = float(asks[0].get('price', 0))
            mid = (bid + ask) / 2
            print(f"   {instrument}: Bid={bid:.4f}, Ask={ask:.4f}, Mid={mid:.4f}")
        else:
            print(f"   {instrument}: No price data")
else:
    print(f"❌ Failed to get prices: {response.status_code}")
    print(f"   Response: {response.text}")

# Test 3: Get account instruments
print("\n[TEST 3] Getting tradable instruments...")
response = requests.get(
    f"{BASE_URL}/v3/accounts/{ACCOUNT_ID}/instruments",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    instruments = data.get('instruments', [])
    print(f"✅ Found {len(instruments)} tradable instruments")
    print("   First 10 instruments:")
    for inst in instruments[:10]:
        print(f"     - {inst.get('name')} ({inst.get('type')})")
else:
    print(f"⚠️ Could not get instruments: {response.status_code}")

print("\n" + "=" * 50)
print("✅ OANDA REST API is working!")
print("=" * 50)
