# force_agent_x_now.py
import sys
sys.path.insert(0, '.')

from trading_controller import trading_controller
from price_bridge import price_bridge
import math

print("=" * 60)
print("🧪 FORCING AGENT_X UPDATE NOW")
print("=" * 60)

# Get prices
spx = price_bridge.get_price('#S&P500')
ndx = price_bridge.get_price('#NASDAQ100')

print(f"📊 Prices: SPX={spx:.2f}, NDX={ndx:.2f}")

if trading_controller.agent_x:
    # Build signal data
    signal_data = {
        'symbol': '#S&P500',
        'spx_price': spx,
        'ndx_price': ndx,
        'price': spx
    }
    
    # Analyze
    result = trading_controller.agent_x.analyze(signal_data)
    
    print(f"\n📊 Agent_X Result:")
    print(f"   Samples: {result.get('samples', 0)}/30")
    print(f"   Z-Score: {result.get('z_score', 0):.2f}")
    print(f"   Spread: {result.get('spread', 0):.6f}")
    print(f"   Mu: {result.get('mu', 0):.6f}")
    print(f"   Sigma: {result.get('sigma', 0):.6f}")
    
    # Check internal state
    print(f"\n📊 Internal State:")
    print(f"   last_spx: {trading_controller.agent_x.last_spx:.2f}")
    print(f"   last_ndx: {trading_controller.agent_x.last_ndx:.2f}")
    print(f"   current_spread: {trading_controller.agent_x.current_spread:.6f}")
    print(f"   z_score: {trading_controller.agent_x.z_score:.2f}")
    print(f"   spread_history length: {len(trading_controller.agent_x.spread_history)}")
    
print("=" * 60)