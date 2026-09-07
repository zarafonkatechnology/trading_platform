#!/usr/bin/env python3
"""
Test Agent_F Voting
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.agents.agent_f_candlestick import AgentFCandlestick

def test_agentf_vote():
    print("=" * 60)
    print("🤖 TESTING AGENT_F VOTING")
    print("=" * 60)
    
    # Create Agent_F
    agent_f = AgentFCandlestick()
    print(f"\n✅ Agent_F created: {agent_f.name}")
    print(f"   Type: {agent_f.agent_type}")
    print(f"   Specialization: {agent_f.specialization}")
    
    # Test 1: Bullish pattern (Hammer)
    print("\n📊 TEST 1: Bullish Pattern (Hammer)")
    print("-" * 40)
    
    candles = [
        {'open': 2350, 'high': 2360, 'low': 2340, 'close': 2355, 'volume': 1000},
        {'open': 2355, 'high': 2365, 'low': 2345, 'close': 2348, 'volume': 1000},
        {'open': 2348, 'high': 2352, 'low': 2330, 'close': 2345, 'volume': 1000}  # Hammer
    ]
    
    market_features = {'candles': candles}
    signal_data = {'asset_type': 'XAU/USD', 'current_price': 2345}
    
    action, confidence = agent_f.predict(signal_data, market_features)
    print(f"  Detected pattern: {agent_f.last_patterns}")
    print(f"  Agent_F vote: {action} (confidence: {confidence}%)")
    
    # Test 2: Bearish pattern (Shooting Star)
    print("\n📊 TEST 2: Bearish Pattern (Shooting Star)")
    print("-" * 40)
    
    candles2 = [
        {'open': 2350, 'high': 2360, 'low': 2340, 'close': 2355, 'volume': 1000},
        {'open': 2355, 'high': 2365, 'low': 2345, 'close': 2348, 'volume': 1000},
        {'open': 2350, 'high': 2380, 'low': 2348, 'close': 2352, 'volume': 1000}  # Shooting Star
    ]
    
    market_features2 = {'candles': candles2}
    action2, conf2 = agent_f.predict(signal_data, market_features2)
    print(f"  Detected pattern: {agent_f.last_patterns}")
    print(f"  Agent_F vote: {action2} (confidence: {conf2}%)")
    
    # Test 3: No pattern
    print("\n📊 TEST 3: No Clear Pattern")
    print("-" * 40)
    
    candles3 = [
        {'open': 2350, 'high': 2352, 'low': 2348, 'close': 2351, 'volume': 1000},
        {'open': 2351, 'high': 2353, 'low': 2349, 'close': 2350, 'volume': 1000},
        {'open': 2350, 'high': 2352, 'low': 2348, 'close': 2351, 'volume': 1000}
    ]
    
    market_features3 = {'candles': candles3}
    action3, conf3 = agent_f.predict(signal_data, market_features3)
    print(f"  Detected pattern: {agent_f.last_patterns}")
    print(f"  Agent_F vote: {action3} (confidence: {conf3}%)")
    
    print("\n" + "=" * 60)
    print("✅ Agent_F voting test complete!")
    print("=" * 60)

if __name__ == '__main__':
    test_agentf_vote()
