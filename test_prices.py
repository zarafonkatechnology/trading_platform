#!/usr/bin/env python3
"""
Test price service updates
"""

import time
import requests

BASE_URL = "http://localhost:5000"

print("Testing real-time price updates...")
print("Prices should change every 5 seconds")
print("-" * 50)

for i in range(10):
    try:
        response = requests.get(f"{BASE_URL}/api/market/prices")
        data = response.json()
        
        if data.get('success'):
            gold = data['prices'].get('XAU/USD', 0)
            silver = data['prices'].get('XAG/USD', 0)
            print(f"[{i+1}] Gold: ${gold:.2f} | Silver: ${silver:.2f}")
        else:
            print(f"[{i+1}] Error: {data}")
        
        time.sleep(3)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(3)

print("-" * 50)
print("If prices changed, real-time updates are working!")
