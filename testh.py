#!/usr/bin/env python
"""
Test the complete signal flow from trading_controller to database to frontend
"""

import time
import requests
import json
import threading
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

# ✅ USE YOUR CORRECT CREDENTIALS
EMAIL = "zarafonkatechnology@gmail.com"
PASSWORD = "1234Lama@"

def test_signal_flow():
    print("=" * 70)
    print("🧪 TESTING COMPLETE SIGNAL FLOW")
    print("=" * 70)
    
    # 1. Login to get token
    print(f"\n1️⃣ Logging in as {EMAIL}...")
    
    # ✅ FIX: Use form data correctly
    login_response = requests.post(
        f"{API_URL}/client/login",
        data={"email": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"   Status: {login_response.status_code}")
    print(f"   Response: {login_response.text[:200]}")
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    data = login_response.json()
    token = data.get('access_token')
    
    if not token:
        print(f"❌ No token in response: {data}")
        return
    
    print(f"✅ Logged in successfully")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Check current signals before
    print("\n2️⃣ Checking signals BEFORE trading controller runs...")
    before_response = requests.get(f"{API_URL}/signals", headers=headers)
    
    if before_response.status_code == 200:
        data = before_response.json()
        print(f"   ✅ Signals before: {data.get('count', 0)} signals")
        for s in data.get('signals', [])[:3]:
            print(f"      - {s.get('symbol')} {s.get('type')} ({s.get('confidence')}%) - {s.get('source')}")
    else:
        print(f"   ❌ Failed: {before_response.text}")
    
    # 3. Check database directly via API
    print("\n3️⃣ Checking database via master API...")
    db_response = requests.get(f"{API_URL}/master/trades", headers=headers)
    if db_response.status_code == 200:
        print("   ✅ Database is accessible")
    else:
        print(f"   ⚠️ Database check: {db_response.status_code}")
    
    # 4. Wait for trading controller to run
    print("\n4️⃣ Waiting for trading controller to generate signals...")
    print("   (Trading controller runs every 10-30 seconds)")
    
    # 5. Monitor for new signals
    print("\n5️⃣ Monitoring for new signals (30 seconds)...")
    new_signals = []
    initial_signal_ids = set()
    
    # Get initial signal IDs
    initial_response = requests.get(f"{API_URL}/signals", headers=headers)
    if initial_response.status_code == 200:
        data = initial_response.json()
        initial_signal_ids = {s.get('signal_id') or s.get('id') for s in data.get('signals', [])}
    
    for i in range(6):  # Check every 5 seconds for 30 seconds
        time.sleep(5)
        response = requests.get(f"{API_URL}/signals", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            current_count = data.get('count', 0)
            signals = data.get('signals', [])
            
            print(f"   [{i+1}/6] Checking signals... Found {current_count} signals")
            
            # Check for NEW signals (not in initial set)
            for signal in signals:
                signal_id = signal.get('signal_id') or signal.get('id')
                source = signal.get('source', 'Unknown')
                
                if signal_id not in initial_signal_ids:
                    print(f"      ✅ NEW SIGNAL: {signal.get('symbol')} {signal.get('type')} ({signal.get('confidence')}%) - {source}")
                    
                    # Check if signal is from AI/Controller
                    if source in ['Agent_RL', 'AI_Controller', 'Agent_X', 'Agent_R', 'Agent_Controller']:
                        print(f"         ✅ FROM TRADING CONTROLLER!")
                        new_signals.append(signal)
                    
                    initial_signal_ids.add(signal_id)
        else:
            print(f"   ❌ API error: {response.status_code}")
    
    # 6. Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"   Total signals from controller: {len(new_signals)}")
    
    if new_signals:
        print("\n   ✅ SIGNALS FROM TRADING CONTROLLER:")
        for s in new_signals[:5]:
            print(f"      - {s.get('symbol')} {s.get('type')} ({s.get('confidence')}%)")
            print(f"        Source: {s.get('source')}")
            print(f"        Reasoning: {s.get('reasoning', 'N/A')[:50]}...")
            print(f"        Time: {s.get('created_at')}")
            print()
    else:
        print("\n   ⚠️ No signals from trading controller detected.")
        print("   Make sure trading_controller.py is running!")
    
    # 7. Manual database check
    print("\n" + "=" * 70)
    print("📋 MANUAL DATABASE CHECK")
    print("=" * 70)
    print("Run this SQL in Supabase SQL Editor:")
    print("")
    print("SELECT id, symbol, signal_type, confidence, source, status, created_at")
    print("FROM signal_history")
    print("ORDER BY created_at DESC")
    print("LIMIT 10;")
    print("=" * 70)

if __name__ == "__main__":
    test_signal_flow()