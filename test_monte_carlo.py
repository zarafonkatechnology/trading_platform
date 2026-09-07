#!/usr/bin/env python3
"""
Test Monte Carlo World Model
"""

import sys
sys.path.insert(0, '/home/mohammed/Downloads/trading_platform')

import numpy as np
from backend.utils.world_model import WorldModel, MonteCarloSimulator, MarketState

def generate_test_data(n_points: int = 200):
    """Generate synthetic price data for testing"""
    data = []
    price = 100.0
    
    for i in range(n_points):
        # Random walk with trend
        trend = 0.0001 if i < 100 else -0.0001
        price_change = np.random.normal(trend, 0.01)
        price = price * (1 + price_change)
        
        data.append({
            'price': price,
            'volume': np.random.randint(5000, 20000),
            'rsi': 50 + np.random.normal(0, 10),
            'trend': 'up' if trend > 0 else 'down'
        })
    
    return data

def test_world_model():
    print("=" * 60)
    print("TESTING WORLD MODEL + MONTE CARLO")
    print("=" * 60)
    
    # Generate test data
    print("\n📊 Generating test market data...")
    test_data = generate_test_data(500)
    
    # Train world model
    print("🧠 Training World Model...")
    world_model = WorldModel(lookback=100)
    world_model.learn_from_history(test_data)
    
    # Create current state
    current_state = MarketState(
        price=test_data[-1]['price'],
        volume=test_data[-1]['volume'],
        rsi=test_data[-1]['rsi'],
        trend=test_data[-1]['trend']
    )
    
    print(f"\n📍 Current State:")
    print(f"   Price: {current_state.price:.4f}")
    print(f"   Volume: {current_state.volume}")
    print(f"   RSI: {current_state.rsi:.1f}")
    print(f"   Trend: {current_state.trend}")
    
    # Run Monte Carlo simulation
    print("\n🎲 Running Monte Carlo Simulation...")
    simulator = MonteCarloSimulator(world_model, n_simulations=1000, horizon=20)
    
    # Evaluate actions
    for action in ['BUY', 'SELL', 'HOLD']:
        print(f"\n📈 Evaluating {action}:")
        
        # Generate futures once
        futures = simulator.simulate_futures(current_state)
        result = simulator.evaluate_action(action, current_state.price, futures)
        
        print(f"   Expected Return: {result['mean_return']*100:.2f}%")
        print(f"   Win Rate: {result['win_rate']:.1f}%")
        print(f"   Sharpe Ratio: {result['sharpe']:.2f}")
        print(f"   Risk Range: {result['percentile_25']*100:.1f}% to {result['percentile_75']*100:.1f}%")
    
    # Find best action
    print("\n🏆 BEST ACTION:")
    best = simulator.best_action(current_state, current_state.price)
    print(f"   Action: {best['best_action']}")
    print(f"   Confidence: {best['confidence']:.1f}%")
    print(f"   Expected Return: {best['expected_return']:.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    
    print("\n" + "=" * 60)
    print("✅ Monte Carlo World Model is ready!")
    print("=" * 60)

if __name__ == '__main__':
    test_world_model()
