#!/usr/bin/env python
"""
Run trading controller and log signals
"""

import time
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 Starting Trading Controller...")
print("=" * 60)

try:
    from trading_controller import trading_controller
    
    # Print configuration
    print(f"📊 Symbols: {trading_controller.symbols}")
    print(f"📊 Cycle: {trading_controller.cycle_seconds} seconds")
    print(f"📊 Min Confidence: {trading_controller.config.get('min_confidence', 50)}")
    print("=" * 60)
    
    # Start the controller
    trading_controller.start()
    print("✅ Trading Controller Started!")
    print("📡 Signals will be saved to database every cycle")
    print("🔍 Press Ctrl+C to stop")
    
    # Keep running
    while True:
        time.sleep(10)
        status = trading_controller.get_status()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Active: {status['active_positions']} | Signals: {len(status.get('signals', []))}")
        
except KeyboardInterrupt:
    print("\n🛑 Stopping trading controller...")
    trading_controller.stop()
    print("✅ Stopped")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()