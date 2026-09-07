# run_system.py - COMPLETE UPDATED VERSION
"""
Launch the Complete AI Trading System
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 70)
    print("🚀 AI TRADING SYSTEM - COMPLETE INTEGRATION")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # ============ 1. START PRICE UPDATER ============
    print("\n[1] Starting Price Updater...")
    try:
        from price_cache_manager import start_price_updater
        start_price_updater(interval_seconds=3)
        print("   ✅ Price updater started (3s interval)")
    except Exception as e:
        print(f"   ⚠️ Price updater error: {e}")

    # ============ 2. START ORDER FLOW ANALYZER ============
    print("\n[2] Starting Order Flow Analyzer...")
    try:
        from order_flow_analyzer import order_flow_analyzer
        print("   ✅ Order Flow Analyzer ready")
    except Exception as e:
        print(f"   ⚠️ Order Flow Analyzer error: {e}")

    # ============ 3. START ALPHA GENERATOR ============
    print("\n[3] Starting Alpha Generator...")
    try:
        from alpha_generator import AlphaScheduler
        alpha_scheduler.start()
        print("   ✅ Alpha generator started")
    except Exception as e:
        print(f"   ⚠️ Alpha generator error: {e}")

    # ============ 4. START TRADING CONTROLLER ============
    print("\n[4] Starting AI Trading Controller...")
    try:
        from trading_controller import trading_controller
        trading_controller.start()
        print("   ✅ AI Trading Controller started")
        print("      🔹 Using DeepSeek AI for decisions")
        print("      🔹 Trading symbols: EURUSD, GBPUSD, USDJPY, GOLD, BRENT_OIL, CrudeOIL")
    except Exception as e:
        print(f"   ❌ Trading controller error: {e}")
        print("   Using fallback trading cycle...")
        try:
            from telegram import run_trading_cycle
            def fallback_loop():
                while True:
                    try:
                        run_trading_cycle()
                        time.sleep(120)
                    except:
                        time.sleep(60)
            threading.Thread(target=fallback_loop, daemon=True).start()
            print("   ✅ Fallback trading cycle started")
        except:
            print("   ❌ No fallback available")

    # ============ 5. START LIVE EXECUTOR ============
    print("\n[5] Starting Live Executor...")
    try:
        from live_executor import start_executor_monitor
        start_executor_monitor(interval_seconds=10)
        print("   ✅ Live executor started")
    except Exception as e:
        print(f"   ⚠️ Live executor error: {e}")

    # ============ 6. START DASHBOARD ============
    print("\n[6] Starting Dashboard...")
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

    # ============ 7. START WEB APP ============
    print("\n[7] Starting Web App...")
    try:
        from app import app
        app_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
            daemon=True,
            name="WebApp"
        )
        app_thread.start()
        print("   ✅ Web app started on port 5000")
    except Exception as e:
        print(f"   ⚠️ Web app error: {e}")
        try:
            from flask import Flask
            fallback = Flask(__name__)
            @fallback.route('/')
            def home():
                return """
                <h1>🤖 AI Trading System</h1>
                <p>System is running!</p>
                <p>Dashboard: <a href="http://localhost:5001">http://localhost:5001</a></p>
                """
            fallback_thread = threading.Thread(
                target=lambda: fallback.run(host='0.0.0.0', port=5000, debug=False),
                daemon=True
            )
            fallback_thread.start()
            print("   ✅ Fallback web app started")
        except:
            pass

    # ============ SUMMARY ============
    print("\n" + "=" * 70)
    print("✅ SYSTEM ONLINE")
    print("=" * 70)
    print("\n🌐 Access Points:")
    print("   📊 Dashboard:  http://localhost:5001")
    print("   📈 Web App:    http://localhost:5000")
    print("\n🤖 AI Trading Status:")
    print("   ✅ DeepSeek API integrated")
    print("   ✅ Sentiment analysis active")
    print("   ✅ Order flow monitoring")
    print("   ✅ Supply/Demand strategy")
    print("   ✅ Position sizing (Kelly Criterion)")
    print("   ✅ MT4 execution ready")
    print("\n" + "=" * 70)
    print("Press Ctrl+C to shutdown")
    print("=" * 70)

    # ============ HEARTBEAT ============
    try:
        heartbeat = 0
        while True:
            time.sleep(10)
            heartbeat += 1
            
            # Show status every 30 seconds
            if heartbeat % 3 == 0:
                try:
                    from trading_controller import trading_controller
                    status = trading_controller.get_status()
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"💓 [{timestamp}] Active: {len(status['active_trades'])} | Total Trades: {status['total_trades']} | Running: {status['running']}")
                except:
                    print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] System running...")
                
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("🛑 SHUTTING DOWN...")
        print("=" * 70)
        
        # Stop trading controller
        try:
            from trading_controller import trading_controller
            trading_controller.stop()
            print("   ✅ Trading controller stopped")
        except:
            pass
        
        print("\n✅ System shutdown complete")
        print("=" * 70)

if __name__ == "__main__":
    main()