#!/usr/bin/env python3
"""
Test Decision-Time Scaling
Run this to see the improvement in reliability
"""

import sys
sys.path.insert(0, '/home/mohammed/Downloads/trading_platform')

from backend.agents.agent_manager import AgentManager
from backend.utils.decision_scaling import DecisionScaler
import time

def test_scaling():
    print("=" * 60)
    print("TESTING DECISION-TIME SCALING")
    print("=" * 60)
    
    # Initialize agent manager
    am = AgentManager()
    
    # Test with Agent_K (Ichimoku) as example
    agent = am.get_agent('Agent_K')
    if not agent:
        print("❌ Agent_K not found")
        return
    
    signal_data = {
        'pair': 'EURUSD',
        'price': 1.0950,
        'indicators': {
            'rsi': 55,
            'volume': 10000,
            'trend': 'up'
        }
    }
    
    print(f"\n📊 Testing Agent_K on EURUSD at {signal_data['price']}")
    print("-" * 40)
    
    # Test single prediction
    print("\n🔮 SINGLE PREDICTION (no scaling):")
    start = time.time()
    single_result = agent.analyze(signal_data)
    single_time = time.time() - start
    print(f"   Vote: {single_result['vote']}")
    print(f"   Confidence: {single_result['confidence']}%")
    print(f"   Time: {single_time:.3f}s")
    
    # Test scaled prediction
    print("\n🎯 SCALED PREDICTION (50 samples):")
    scaler = DecisionScaler(agent, n_samples=50)
    start = time.time()
    scaled_result = scaler.predict(signal_data)
    scaled_time = time.time() - start
    print(f"   Vote: {scaled_result['vote']}")
    print(f"   Confidence: {scaled_result['confidence']}%")
    print(f"   Consensus Ratio: {scaled_result['consensus_stats']['consensus_ratio']}%")
    print(f"   Time: {scaled_time:.3f}s")
    print(f"   Distribution: {scaled_result['consensus_stats']['votes_distribution']}")
    
    print("\n" + "=" * 60)
    print("✅ Decision-Time Scaling is ready!")
    print("=" * 60)

if __name__ == '__main__':
    test_scaling()
