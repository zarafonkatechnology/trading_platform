#!/usr/bin/env python3
"""
Remote MT4 Client – Runs on Linux PC
Sends commands to Windows bridge via HTTP
"""

import requests
import json
import time

# Windows PC running the bridge
WINDOWS_PC_IP = "192.168.1.39"  # Change to your Windows IP
BRIDGE_PORT = 5000  # Port for HTTP bridge

class MT4RemoteClient:
    def __init__(self, host=WINDOWS_PC_IP, port=BRIDGE_PORT):
        self.base_url = f"http://{host}:{port}"
    
    def ping(self):
        try:
            resp = requests.get(f"{self.base_url}/ping", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def buy(self, symbol, volume, stop_loss=0, take_profit=0):
        data = {
            "command": "BUY",
            "symbol": symbol,
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
        resp = requests.post(f"{self.base_url}/trade", json=data)
        return resp.json()
    
    def sell(self, symbol, volume, stop_loss=0, take_profit=0):
        data = {
            "command": "SELL",
            "symbol": symbol,
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
        resp = requests.post(f"{self.base_url}/trade", json=data)
        return resp.json()
    
    def get_account(self):
        resp = requests.get(f"{self.base_url}/account")
        return resp.json()
    
    def get_price(self, symbol):
        resp = requests.get(f"{self.base_url}/price/{symbol}")
        return resp.json()


# Test
if __name__ == "__main__":
    client = MT4RemoteClient()
    
    print("Testing connection...")
    if client.ping():
        print("✅ Connected to Windows bridge!")
        
        account = client.get_account()
        print(f"Account balance: ${account.get('balance', 'N/A')}")
        
        price = client.get_price("EURUSD")
        print(f"EURUSD: {price.get('bid')}")
    else:
        print("❌ Cannot connect to Windows bridge")
