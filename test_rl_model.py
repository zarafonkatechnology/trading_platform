# ============================================================
# test_rl_model.py - TEST RL MODEL (FULLY FIXED)
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob
import numpy as np
from stable_baselines3 import PPO

print("=" * 60)
print("🧪 TESTING RL MODEL")
print("=" * 60)

# ===== FIND MODEL AUTOMATICALLY =====
possible_paths = [
    "models/rl_model.zip",
    "../models/rl_model.zip",
    "rl_trading/models/*.zip",
    "C:/trading_platform/models/rl_model.zip",
    "C:/trading_platform/rl_trading/models/*.zip"
]

model = None
model_path = None

for pattern in possible_paths:
    if '*' in pattern:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            model_path = matches[0]
            break
    elif os.path.exists(pattern):
        model_path = pattern
        break

if model_path:
    try:
        model = PPO.load(model_path)
        print(f"✅ Model loaded from: {model_path}")
        print(f"   File size: {os.path.getsize(model_path) / 1024:.1f} KB")
    except Exception as e:
        print(f"⚠️ Error loading model: {e}")

if model is None:
    print("\n❌ Could not find any model file!")
    print("\nPlease copy the model manually:")
    print("   mkdir models -Force")
    print("   copy rl_trading\\models\\*.zip models\\rl_model.zip")
    sys.exit(1)

# ===== TEST WITH SIMULATED Z-SCORES =====
print("\n📊 Testing with simulated Z-scores:")
print("-" * 40)

test_z_scores = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}

for z in test_z_scores:
    state = np.array([
        float(np.clip(z, -3.5, 3.5)),
        0.0,  # position
        0.0,  # entry_z
        0.0   # unrealized pnl
    ], dtype=np.float32)
    
    # Get action from model
    action, _ = model.predict(state, deterministic=True)
    
    # FIX: Handle different action formats
    if isinstance(action, np.ndarray):
        if action.size == 0:
            action_int = 1  # HOLD
        elif action.ndim == 0:
            # 0-dimensional array (scalar)
            action_int = int(action.item())
        elif action.ndim == 1:
            # 1-dimensional array
            action_int = int(action[0])
        else:
            action_int = 1
    else:
        action_int = int(action)
    
    signal = action_map.get(action_int, 'HOLD')
    confidence = min(95, 50 + abs(z) * 10)
    
    print(f"   Z={z:5.2f} → {signal} (confidence: {confidence:.0f}%)")

print("\n" + "=" * 60)
print("✅ Test Complete!")
print("=" * 60)

print(f"\n📁 Model location: {model_path}")