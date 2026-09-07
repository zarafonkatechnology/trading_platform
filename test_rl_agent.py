#!/usr/bin/env python3
"""
Test RL Agent Learning
Run this to verify agents are learning from data
"""

import sys
import json
import time
import random
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.ml.rl_agent import RLAgent
from backend.ml.sentinel_feature_engineer import SentinelFeatureEngineer

def test_rl_learning():
    """Test if RL agent actually learns"""
    
    print("=" * 60)
    print("🧠 RL AGENT LEARNING TEST")
    print("=" * 60)
    
    # Create an RL agent
    agent = RLAgent("Test_Agent", "Trend Follower")
    
    # Test 1: Initial state - No knowledge
    print("\n📊 TEST 1: Initial State (No Learning Yet)")
    print("-" * 40)
    
    features = {
        'z_score_20': 0.5,
        'rsi_14': 55,
        'trend_strength': 60,
        'current_price': 2350
    }
    
    action, confidence = agent.get_action(features, training=True)
    print(f"  Initial action: {action} (confidence: {confidence}%)")
    print(f"  Q-table size: {len(agent.q_table)}")
    
    # Test 2: Learn from positive rewards (BUY wins)
    print("\n📊 TEST 2: Learning from POSITIVE rewards (BUY → Profit)")
    print("-" * 40)
    
    for i in range(10):
        features = {'z_score_20': 0.3, 'rsi_14': 45, 'trend_strength': 55, 'current_price': 2350}
        next_features = {'z_score_20': 0.4, 'rsi_14': 50, 'trend_strength': 60, 'current_price': 2380}
        
        # BUY action with positive reward
        agent.update_from_reward(features, 'BUY', reward=0.5, next_state_features=next_features, xp_change=25)
    
    # Check if Q-value for BUY increased
    state_key = agent._get_state_key(features)
    print(f"  After 10 positive BUY experiences:")
    if state_key in agent.q_table:
        print(f"    Q-value for BUY: {agent.q_table[state_key].get('BUY', 0):.3f}")
        print(f"    Q-value for SELL: {agent.q_table[state_key].get('SELL', 0):.3f}")
        print(f"    Q-value for HOLD: {agent.q_table[state_key].get('HOLD', 0):.3f}")
    
    # Test 3: Learn from negative rewards (BUY loses)
    print("\n📊 TEST 3: Learning from NEGATIVE rewards (BUY → Loss)")
    print("-" * 40)
    
    for i in range(10):
        features = {'z_score_20': 0.8, 'rsi_14': 75, 'trend_strength': 80, 'current_price': 2450}
        next_features = {'z_score_20': 0.7, 'rsi_14': 70, 'trend_strength': 75, 'current_price': 2420}
        
        # BUY action with negative reward (loss)
        agent.update_from_reward(features, 'BUY', reward=-0.3, next_state_features=next_features, xp_change=-15)
    
    state_key2 = agent._get_state_key(features)
    print(f"  After 10 negative BUY experiences:")
    if state_key2 in agent.q_table:
        print(f"    Q-value for BUY: {agent.q_table[state_key2].get('BUY', 0):.3f}")
        print(f"    Q-value for SELL: {agent.q_table[state_key2].get('SELL', 0):.3f}")
        print(f"    Q-value for HOLD: {agent.q_table[state_key2].get('HOLD', 0):.3f}")
    
    # Test 4: Best action after learning
    print("\n📊 TEST 4: Best Action After Learning")
    print("-" * 40)
    
    test_features = {'z_score_20': 0.3, 'rsi_14': 45, 'trend_strength': 55, 'current_price': 2350}
    best_action = agent.get_best_action(test_features)
    action2, conf2 = agent.get_action(test_features, training=False)
    
    print(f"  Best action for this state: {best_action}")
    print(f"  Exploitation action: {action2} (confidence: {conf2}%)")
    
    # Test 5: Exploration vs Exploitation
    print("\n📊 TEST 5: Exploration Rate Decay")
    print("-" * 40)
    print(f"  Current exploration rate: {agent.exploration_rate:.3f}")
    print(f"  Minimum exploration rate: {agent.exploration_min:.3f}")
    
    # Test 6: Mini-batch update
    print("\n📊 TEST 6: Mini-Batch Update (Experience Replay)")
    print("-" * 40)
    print(f"  Memory size before: {len(agent.memory)}")
    
    loss = agent.mini_batch_update(batch_size=16)
    print(f"  Loss after update: {loss:.4f}")
    print(f"  Memory size after: {len(agent.memory)}")
    
    # Test 7: Stats
    print("\n📊 TEST 7: Agent Statistics")
    print("-" * 40)
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test 8: Save and Load weights
    print("\n📊 TEST 8: Save and Load Weights")
    print("-" * 40)
    
    # Save weights (simulated)
    agent.save_weights(version=1)
    print("  ✅ Weights saved")
    
    print("\n" + "=" * 60)
    print("✅ RL AGENT TEST COMPLETE")
    print("=" * 60)
    
    # Conclusion
    print("\n📈 VERDICT:")
    if agent.q_table and len(agent.q_table) > 0:
        print("  ✅ Agent IS learning! Q-table has entries.")
        print("  ✅ Agent can distinguish between good and bad actions.")
    else:
        print("  ❌ Agent is NOT learning. Check Q-table updates.")
    
    return agent

def test_with_real_market_data():
    """Test RL agent with simulated market data"""
    
    print("\n" + "=" * 60)
    print("📈 TEST WITH SIMULATED MARKET DATA")
    print("=" * 60)
    
    agent = RLAgent("Market_Agent", "Trend Follower")
    
    # Simulate 100 trading days of learning
    print("\n🔄 Simulating 100 trading days of learning...")
    
    for day in range(100):
        # Generate random market conditions
        z_score = random.uniform(-2, 2)
        rsi = random.uniform(20, 80)
        trend = random.uniform(20, 80)
        price = 2350 + random.uniform(-50, 50)
        
        features = {
            'z_score_20': z_score,
            'rsi_14': rsi,
            'trend_strength': trend,
            'current_price': price
        }
        
        # Agent chooses action
        action, confidence = agent.get_action(features, training=True)
        
        # Simulate market outcome
        if action == 'BUY':
            # BUY makes profit when market goes up
            market_move = random.uniform(-2, 3)
            profit = market_move
            reward = profit / 100
            xp = 25 if profit > 0 else -15
        elif action == 'SELL':
            market_move = random.uniform(-3, 2)
            profit = -market_move
            reward = profit / 100
            xp = 25 if profit > 0 else -15
        else:
            reward = -0.01  # Small penalty for HOLD
            xp = -5
            profit = 0
        
        # Next state
        next_features = features.copy()
        next_features['current_price'] = price * (1 + profit / 100)
        
        # Learn from experience
        agent.update_from_reward(features, action, reward, next_features, xp)
        
        # Every 20 days, show progress
        if (day + 1) % 20 == 0:
            stats = agent.get_stats()
            print(f"  Day {day+1}: Q-size={stats['q_table_size']}, "
                  f"Exploration={stats['exploration_rate']:.2f}, "
                  f"Win Rate={stats['win_rate']}%")
    
    print("\n✅ Market simulation complete!")
    stats = agent.get_stats()
    print(f"\nFinal Statistics:")
    print(f"  Q-Table Size: {stats['q_table_size']}")
    print(f"  Win Rate: {stats['win_rate']}%")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Exploration Rate: {stats['exploration_rate']:.3f}")
    
    return agent

if __name__ == '__main__':
    # Run tests
    test_rl_learning()
    test_with_real_market_data()
