# ============================================================
# test_live_now.py - Live Market Test
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from datetime import datetime
from trading_controller import trading_controller

print("=" * 60)
print(f"🧪 LIVE MARKET TEST - {datetime.now().strftime('%H:%M:%S')}")
print("=" * 60)

# Get current market data
symbols = ['#S&P500', '#NASDAQ100', '#DJ30', 'EURUSD', 'GOLD']

for symbol in symbols:
    try:
        price_data = trading_controller._get_price_data(symbol)
        if price_data:
            price = price_data.get('price', 0)
            if price > 0:
                print(f"   {symbol}: {price:.2f}")
            else:
                print(f"   {symbol}: No price")
        else:
            print(f"   {symbol}: No data")
    except Exception as e:
        print(f"   {symbol}: Error - {e}")

# Check Agent_X status
if trading_controller.agent_x is not None:
    print(f"\n📊 Agent_X Status:")
    print(f"   Z-Score: {trading_controller.agent_x.z_score:.2f}")
    print(f"   Samples: {len(trading_controller.agent_x.spread_history)}/30")
    print(f"   Signal: {trading_controller.agent_x.signal}")
    print(f"   Confidence: {trading_controller.agent_x.confidence}%")

# Check if RL model is loaded
if hasattr(trading_controller, 'rl_model') and trading_controller.rl_model is not None:
    print(f"\n🤖 RL Model: ✅ Loaded")
    z_score = trading_controller.agent_x.z_score if trading_controller.agent_x else 0
    
    import numpy as np
    state = np.array([
        float(np.clip(z_score, -3.5, 3.5)),
        0.0, 0.0, 0.0
    ], dtype=np.float32)
    
    action, _ = trading_controller.rl_model.predict(state, deterministic=True)
    action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    if isinstance(action, np.ndarray):
        action_int = int(action.item()) if action.ndim == 0 else int(action[0])
    else:
        action_int = int(action)
    
    print(f"   RL Signal: {action_map.get(action_int, 'HOLD')}")
    print(f"   Z-Score: {z_score:.2f}")
else:
    print(f"\n🤖 RL Model: ❌ Not loaded")

print("\n" + "=" * 60)
print("✅ Test Complete")
print("=" * 60)

# Check if calibration window is active
current_time = datetime.now()
is_calibration = (current_time.hour == 16 and 30 <= current_time.minute < 35)
print(f"\n🕐 Calibration Window: {'✅ ACTIVE' if is_calibration else '⏸️ INACTIVE'} ({current_time.strftime('%H:%M')})")