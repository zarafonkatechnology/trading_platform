# cleanup_positions.py
import sys
sys.path.insert(0, '..')

from trading_controller2 import ForexTradingController, FOREX_PAIRS

config = {
    'pairs': FOREX_PAIRS,
    'min_confidence': 50,
    'cycle_interval': 10,
}

controller = ForexTradingController(config)
controller.clear_stuck_positions()

print("\n✅ All positions cleared!")
print("Now run: python trading_controller2.py")