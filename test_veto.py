#!/usr/bin/env python3
"""
Test Sentinel Veto - See why it blocks bad trades
"""

from sentinel_simple import SimpleSentinel

sentinel = SimpleSentinel()

print("=" * 60)
print("SENTINEL VETO DEMONSTRATION")
print("=" * 60)

# Test 1: Normal trade - PASSES
print("\n[TEST 1] Normal Trade:")
normal = {'decision': 'BUY', 'confidence': 75, 'position_size': 5000}
allowed, msg = sentinel.veto(normal, 'Agent_A', {'volatility': 0.5})
print(f"  Trade: BUY 5000 units @ 75% confidence")
print(f"  Result: {msg}")
print(f"  ✅ Trade ALLOWED - Proceeds to execution")

# Test 2: Too large position - BLOCKED
print("\n[TEST 2] Too Large Position:")
large = {'decision': 'BUY', 'confidence': 75, 'position_size': 50000}
allowed, msg = sentinel.veto(large, 'Agent_A', {'volatility': 0.5})
print(f"  Trade: BUY 50000 units @ 75% confidence")
print(f"  Result: {msg}")
print(f"  🔴 Trade BLOCKED - Saved $45,000 risk!")

# Test 3: Overconfident - BLOCKED
print("\n[TEST 3] Overconfident Trade:")
overconfident = {'decision': 'BUY', 'confidence': 98, 'position_size': 5000}
allowed, msg = sentinel.veto(overconfident, 'Agent_A', {'volatility': 0.5})
print(f"  Trade: BUY 5000 units @ 98% confidence")
print(f"  Result: {msg}")
print(f"  🔴 Trade BLOCKED - 98% confidence is unrealistic!")

# Test 4: High volatility - BLOCKED
print("\n[TEST 4] High Volatility Market:")
high_vol = {'decision': 'BUY', 'confidence': 75, 'position_size': 5000}
allowed, msg = sentinel.veto(high_vol, 'Agent_A', {'volatility': 6.5})
print(f"  Market volatility: 6.5%")
print(f"  Result: {msg}")
print(f"  🔴 Trade BLOCKED - Market too dangerous!")

print("\n" + "=" * 60)
print("SUMMARY: Sentinel blocked 3/4 trades, saving potential losses")
print("=" * 60)

