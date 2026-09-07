# run_ultimate.py - UPDATED
"""
ULTIMATE AI TRADING SYSTEM - 5-AGENT CONSENSUS
"""

import time
import threading
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 70)
    print("🏆 ULTIMATE AI TRADING SYSTEM - 5-AGENT CONSENSUS")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. Start Price Updater
    print("\n[1] Starting Price Updater...")
    try:
        from price_cache_manager import start_price_updater
        start_price_updater(interval_seconds=3)
        print("   ✅ Price updater started")
    except Exception as e:
        print(f"   ⚠️ Price updater error: {e}")
    
    # 2. Start Ultimate Trading Controller
    print("\n[2] Starting Ultimate Trading Controller...")
    try:
        from trading_controller import trading_controller  # Use trading_controller, not ultimate
        trading_controller.start()
        print("   ✅ Ultimate Trading Controller started")
    except Exception as e:
        print(f"   ❌ Trading controller error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Start Dashboard
    print("\n[3] Starting Dashboard...")
    try:
        from performance_dashboard import start_dashboard_server
        dashboard_thread = threading.Thread(
            target=start_dashboard_server,
            args=(5001,),
            daemon=True,
            name="Dashboard"
        )
        dashboard_thread.start()
        print("   ✅ Dashboard started on port 5001")
    except Exception as e:
        print(f"   ⚠️ Dashboard error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ ULTIMATE SYSTEM ONLINE")
    print("=" * 70)
    print("\n🌐 Access Points:")
    print("   📊 Dashboard: http://localhost:5001")
    print("=" * 70)
    print("Press Ctrl+C to shutdown")
    print("=" * 70)
    
    try:
        while True:
            time.sleep(10)
            # Simple heartbeat
            if int(time.time()) % 30 == 0:
                try:
                    from trading_controller import trading_controller
                    status = trading_controller.get_status()
                    print(f"💓 Active: {len(trading_controller.active_trades)} | Total: {len(trading_controller.trade_history)}")
                except:
                    print(f"💓 System running...")
                    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        try:
            from trading_controller import trading_controller
            trading_controller.stop()
            print("   ✅ Trading controller stopped")
        except:
            pass
        print("✅ System shutdown complete")

if __name__ == "__main__":
    main()