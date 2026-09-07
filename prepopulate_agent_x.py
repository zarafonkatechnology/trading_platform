# prepopulate_agent_x.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agents.agent_x_spread import AgentXSpread
from price_bridge import price_bridge
import time

print("=" * 60)
print("🔄 Pre-populating Agent_X History")
print("=" * 60)

# Create Agent_X
agent = AgentXSpread()

# Get current prices
spx = price_bridge.get_price('#S&P500')
ndx = price_bridge.get_price('#NASDAQ100')

print(f"SPX: {spx}")
print(f"NDX: {ndx}")

if spx <= 0 or ndx <= 0:
    print("Using fallback prices")
    spx = 7525.99
    ndx = 30332.25

# Build history with slight variations
print("\nBuilding history...")
for i in range(35):
    # Add slight variation to build history
    spx_var = spx * (1 + (i - 17) * 0.0001)
    ndx_var = ndx * (1 + (i - 17) * 0.00012)
    
    signal_data = {
        'symbol': '#S&P500',
        'spx_price': spx_var,
        'ndx_price': ndx_var,
        'price': spx_var
    }
    
    result = agent.analyze(signal_data)
    
    if (i + 1) % 5 == 0:
        print(f"  Sample {i+1}/35: Z={result['z_score']:.2f}")
    
    time.sleep(0.01)

print(f"\n✅ Agent_X history built: {len(agent.spread_history)} samples")
print(f"   Z-Score: {agent.z_score:.3f}")
print(f"   Signal: {agent.signal}")

# Save to a file for the controller to load
import pickle
with open('agent_x_state.pkl', 'wb') as f:
    pickle.dump({
        'history': agent.spread_history,
        'mu': agent.mu,
        'sigma': agent.sigma,
        'z_score': agent.z_score,
        'samples': len(agent.spread_history)
    }, f)

print("   ✅ State saved to agent_x_state.pkl")
print("=" * 60)