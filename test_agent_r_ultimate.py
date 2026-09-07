#!/usr/bin/env python3
"""
Test Agent_R Ultimate with Monte Carlo + Agent_J Integration
"""

import sys
sys.path.insert(0, '/home/mohammed/Downloads/trading_platform')

import numpy as np
import random
from datetime import datetime, timedelta
from backend.agents.agent_r_ultimate import AgentRUltimate

def generate_test_candles(n_candles: int = 100, start_price: float = 100.0):
    """Generate synthetic test candles with realistic patterns"""
    candles = []
    price = start_price
    support = 98.0
    resistance = 102.0
    
    for i in range(n_candles):
        # Create price movement with support/resistance bounces
        if price <= support:
            trend = 'up'
        elif price >= resistance:
            trend = 'down'
        else:
            trend = random.choice(['up', 'down', 'side'])
        
        if trend == 'up':
            change = random.uniform(0.001, 0.005)
        elif trend == 'down':
            change = random.uniform(-0.005, -0.001)
        else:
            change = random.uniform(-0.002, 0.002)
        
        open_price = price
        close_price = price * (1 + change)
        
        # Create candle body and wicks
        if close_price > open_price:
            high = close_price * (1 + random.uniform(0, 0.002))
            low = open_price * (1 - random.uniform(0, 0.002))
        else:
            high = open_price * (1 + random.uniform(0, 0.002))
            low = close_price * (1 - random.uniform(0, 0.002))
        
        volume = random.randint(5000, 30000)
        
        # Create reversal patterns at support/resistance
        if price <= support * 1.005 and trend == 'down':
            # Bullish reversal pattern
            close_price = price * (1 + random.uniform(0.005, 0.01))
            volume = random.randint(20000, 40000)  # Volume surge
            
        if price >= resistance * 0.995 and trend == 'up':
            # Bearish reversal pattern
            close_price = price * (1 - random.uniform(0.005, 0.01))
            volume = random.randint(20000, 40000)  # Volume surge
        
        candle = {
            'open': round(open_price, 4),
            'high': round(high, 4),
            'low': round(low, 4),
            'close': round(close_price, 4),
            'volume': volume,
            'timestamp': datetime.now() - timedelta(hours=n_candles - i)
        }
        
        candles.append(candle)
        price = close_price
    
    return candles, support, resistance


def test_agent_r():
    print("=" * 70)
    print("🧪 TESTING AGENT_R ULTIMATE")
    print("=" * 70)
    
    # Create agent
    agent = AgentRUltimate(name="Agent_R_Test")
    
    # Generate test data
    print("\n📊 Generating test market data...")
    candles, true_support, true_resistance = generate_test_candles(150, start_price=100.0)
    print(f"   True Support: {true_support}")
    print(f"   True Resistance: {true_resistance}")
    print(f"   Candles generated: {len(candles)}")
    
    # Update agent with candles
    print("\n🔄 Updating agent with market data...")
    agent.update_from_candles(candles)
    
    # Simulate Agent_J volume data
    print("\n🔊 Simulating Agent_J (Volume Master) data...")
    volume_data = {
        'current_volume': 25000,
        'avg_volume': 15000,
        'volume_ratio': 1.67,
        'volume_surge': True,
        'volume_trend': 'increasing'
    }
    agent.update_from_agent_j(volume_data)
    
    # Show detected zones
    print(f"\n📍 DETECTED ZONES:")
    print(f"   Supply Zones (Resistance): {len(agent.supply_zones)}")
    for zone in agent.supply_zones[:5]:
        print(f"      {zone.price:.4f} (strength: {zone.current_strength:.1f}%, touches: {zone.touches})")
    
    print(f"\n   Demand Zones (Support): {len(agent.demand_zones)}")
    for zone in agent.demand_zones[:5]:
        print(f"      {zone.price:.4f} (strength: {zone.current_strength:.1f}%, touches: {zone.touches})")
    
    # Test analysis at different price levels
    print("\n" + "=" * 70)
    print("📈 ANALYZING AT DIFFERENT PRICE LEVELS")
    print("=" * 70)
    
    test_prices = [
        ('Near Demand Zone', true_support + 0.2),
        ('Mid Range', (true_support + true_resistance) / 2),
        ('Near Supply Zone', true_resistance - 0.2),
    ]
    
    for description, price in test_prices:
        print(f"\n📍 {description} - Price: {price:.4f}")
        print("-" * 50)
        
        signal_data = {
            'price': price,
            'volume': 25000,
            'weekly_trend': 'up',
            'daily_trend': 'up',
            'volatility': 0.005
        }
        
        result = agent.analyze(signal_data)
        
        print(f"   🎯 Vote: {result['vote']}")
        print(f"   📊 Confidence: {result['confidence']}%")
        print(f"   💰 Position Size: {result['position_size'] * 100}%")
        print(f"   ✅ Is Genuine: {result['is_genuine']}")
        print(f"   📉 Manipulation Score: {result['manipulation_score']}")
        
        if result['level_info']:
            print(f"   📍 Active Level: {result['level_info']['price']:.4f} ({result['level_info']['type']})")
            print(f"   💪 Level Strength: {result['level_info']['strength']}%")
        
        if result['monte_carlo']:
            print(f"   🎲 Monte Carlo:")
            print(f"      Breakout Up: {result['monte_carlo']['breakout_up']}%")
            print(f"      Breakout Down: {result['monte_carlo']['breakout_down']}%")
            print(f"      Bounce: {result['monte_carlo']['bounce']}%")
        
        print(f"   💵 Hidden Funds Estimate: ${result['hidden_funds_estimate']:,.0f}")
        print(f"   💬 Reasoning: {result['reasoning'][:100]}...")
    
    # Test manipulation detection
    print("\n" + "=" * 70)
    print("🎭 MANIPULATION DETECTION TESTS")
    print("=" * 70)
    
    test_scenarios = [
        ("Genuine Breakout", 1.5, 1, 1.0, 80),
        ("Low Volume Suspicious", 0.3, 2, 0.5, 45),
        ("Manipulation", 0.4, 3, 0.0, 30),
    ]
    
    for name, v_ratio, hesitation, mtf, expected_conf in test_scenarios:
        print(f"\n📊 Scenario: {name}")
        print(f"   Volume Ratio: {v_ratio}, Hesitation: {hesitation}, MTF: {mtf}")
        
        m_score, signal, reasoning = agent.manipulation_detector.detect(
            volume_ratio=v_ratio,
            hesitation_bars=hesitation,
            mtf_alignment=mtf
        )
        
        print(f"   M Score: {m_score:.3f}")
        print(f"   Signal: {signal.value}")
        print(f"   Reasoning: {reasoning}")
    
    # Performance test
    print("\n" + "=" * 70)
    print("⚡ PERFORMANCE TEST")
    print("=" * 70)
    
    import time
    start = time.time()
    
    n_tests = 50
    for i in range(n_tests):
        price = 98 + random.random() * 5
        result = agent.analyze({'price': price, 'volume': 20000})
    
    elapsed = time.time() - start
    print(f"   {n_tests} analyses completed in {elapsed:.2f}s")
    print(f"   Average: {elapsed/n_tests*1000:.1f}ms per analysis")
    
    print("\n" + "=" * 70)
    print("✅ Agent_R Ultimate test complete!")
    print("=" * 70)
    
    return agent


if __name__ == '__main__':
    test_agent_r()
