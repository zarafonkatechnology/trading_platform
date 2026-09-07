# test_controller_prices.py - Test trading_controller2 price fetching

import sys
import os
from pathlib import Path

# Add paths
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent
_trading_copy = _project_root / "Trading_copy"

for path in [
    str(_project_root),
    str(_trading_copy),
    str(_trading_copy / "core"),
]:
    if path not in sys.path:
        sys.path.insert(0, path)

print("\n" + "="*70)
print("🧪 TESTING TRADING_CONTROLLER2 PRICE FETCHING")
print("="*70)

# ============================================================
# 1. Import and create controller
# ============================================================
print("\n📊 STEP 1: Creating ForexTradingController...")

try:
    from trading_controller2 import ForexTradingController, FOREX_PAIRS
    print(f"   ✅ Imported ForexTradingController")
    print(f"   📊 FOREX_PAIRS: {len(FOREX_PAIRS)} pairs")
    
    # Create controller with minimal config
    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 50,
        'cycle_interval': 10,
        'rl_enabled': False,
    }
    
    controller = ForexTradingController(config)
    print("   ✅ Controller created")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 2. Test get_all_mt4_prices
# ============================================================
print("\n📊 STEP 2: Testing get_all_mt4_prices()...")

try:
    prices = controller.get_all_mt4_prices()
    
    print(f"\n   ✅ Got {len(prices)} prices:")
    for pair in FOREX_PAIRS:
        price = prices.get(pair, 0)
        if price > 0:
            print(f"      ✅ {pair}: {price:.5f}")
        else:
            print(f"      ❌ {pair}: NO PRICE")
            
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# 3. Test price_bridge directly
# ============================================================
print("\n📊 STEP 3: Testing price_bridge directly...")

try:
    from price_bridge import price_bridge
    
    bridge_prices = price_bridge.get_all_prices()
    
    print(f"\n   ✅ price_bridge returned {len(bridge_prices)} prices:")
    for pair in FOREX_PAIRS:
        price = bridge_prices.get(pair, 0)
        if price > 0:
            print(f"      ✅ {pair}: {price:.5f}")
        else:
            print(f"      ❌ {pair}: NO PRICE")
            
except Exception as e:
    print(f"   ❌ Error: {e}")

# ============================================================
# 4. Compare results
# ============================================================
print("\n" + "="*70)
print("📋 COMPARISON: Controller vs Price Bridge")
print("="*70)

print(f"\n{'Pair':<12} {'Controller':<15} {'Price Bridge':<15} {'Match':<10}")
print("-"*60)

all_match = True
for pair in FOREX_PAIRS:
    controller_price = prices.get(pair, 0) if 'prices' in locals() else 0
    bridge_price = bridge_prices.get(pair, 0) if 'bridge_prices' in locals() else 0
    
    controller_display = f"{controller_price:.5f}" if controller_price > 0 else "❌"
    bridge_display = f"{bridge_price:.5f}" if bridge_price > 0 else "❌"
    match = "✅" if (controller_price > 0 and bridge_price > 0 and abs(controller_price - bridge_price) < 0.0001) else "⚠️" if (controller_price > 0 and bridge_price > 0) else "❌"
    
    if match != "✅":
        all_match = False
    
    print(f"{pair:<12} {controller_display:<15} {bridge_display:<15} {match:<10}")

print("\n" + "="*70)

if all_match and len(prices) == len(FOREX_PAIRS):
    print("✅ SUCCESS: All 12 forex pairs have prices!")
else:
    print("⚠️ ISSUE: Some pairs are missing prices")

print("="*70 + "\n")