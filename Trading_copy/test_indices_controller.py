# test_complete_system.py
"""
Complete system test - Both controllers
"""

import sys
from pathlib import Path

# Add current directory
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("=" * 60)
print("🧪 COMPLETE SYSTEM TEST")
print("=" * 60)

# Test core_bridge
print("\n1️⃣ Testing core_bridge...")
try:
    from core_bridge import DollarEngine, GearBroker, GearAnomalyDetector, MonteCarloSimulator, OrderExecutionEngine
    print("   ✅ core_bridge loaded successfully!")
    
    # Test DollarEngine
    engine = DollarEngine()
    status = engine.get_status()
    print(f"   ✅ DollarEngine: {status.get('engine_direction', 'N/A')}")
except Exception as e:
    print(f"   ❌ core_bridge error: {e}")

# Test brokers_bridge
print("\n2️⃣ Testing brokers_bridge...")
try:
    from brokers_bridge import BROKER_MAP, BaseBroker, BrokerManager
    print("   ✅ brokers_bridge loaded")
    print(f"   BROKER_MAP: {len(BROKER_MAP)} brokers")
except Exception as e:
    print(f"   ❌ brokers_bridge error: {e}")

# Test Indices Controller
print("\n3️⃣ Testing Indices Controller...")
try:
    from trading_controller import AITradingController, SYMBOLS_TO_TRADE
    print(f"   ✅ Indices controller loaded")
    print(f"   Symbols: {len(SYMBOLS_TO_TRADE)}")
    
    controller = AITradingController()
    prices = controller.get_all_mt4_prices()
    found = sum(1 for s in SYMBOLS_TO_TRADE if prices.get(s, 0) > 0)
    print(f"   Prices: {found}/{len(SYMBOLS_TO_TRADE)}")
except Exception as e:
    print(f"   ❌ Indices controller error: {e}")

# Test Forex Controller
print("\n4️⃣ Testing Forex Controller...")
try:
    from trading_controller2 import ForexTradingController, FOREX_PAIRS
    print(f"   ✅ Forex controller loaded")
    print(f"   Pairs: {len(FOREX_PAIRS)}")
    
    config = {
        'pairs': FOREX_PAIRS[:3],  # Test with 3 pairs
        'min_confidence': 60,
        'cycle_interval': 10,
        'rl_enabled': False,
    }
    controller = ForexTradingController(config)
    prices = controller.get_all_mt4_prices()
    found = sum(1 for p in FOREX_PAIRS[:3] if prices.get(p, 0) > 0)
    print(f"   Prices: {found}/3")
    controller.stop()
except Exception as e:
    print(f"   ❌ Forex controller error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Complete System Test Done!")