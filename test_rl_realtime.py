#!/usr/bin/env python3
"""
Test RL Agent with Real-Time Market Data
This connects to your running app and tests RL learning
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_rl_vote_integration():
    """Test if RL agents are updated when votes are cast"""
    
    print("=" * 60)
    print("🧠 RL AGENT REAL-TIME TEST")
    print("=" * 60)
    
    # Test signal
    test_signal = {
        "asset_type": "XAU/USD",
        "current_price": 2350.50,
        "confidence_percent": 85,
        "timeframe_minutes": 15
    }
    
    print(f"\n📡 Sending test signal: {test_signal['asset_type']} @ ${test_signal['current_price']}")
    
    # Send vote request
    response = requests.post(f"{BASE_URL}/api/vote", 
                            json={"signal": test_signal, "features": {}})
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Vote processed!")
        print(f"  Decision: {data['result']['decision']}")
        print(f"  Profit/Loss: {data.get('profit_loss', 'N/A')}")
        
        if data.get('profit_loss'):
            print(f"  RL Update: Completed")
        else:
            print(f"  RL Update: Not triggered")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Check RL agent status
    print("\n📊 Checking RL Agent Status...")
    try:
        response = requests.get(f"{BASE_URL}/api/rl_status")
        if response.status_code == 200:
            data = response.json()
            print(f"  RL Agents Active: {data.get('active', False)}")
            print(f"  Training Cycles: {data.get('cycle_number', 0)}")
        else:
            print("  Could not get RL status")
    except:
        print("  RL status endpoint not available")

if __name__ == '__main__':
    test_rl_vote_integration()
