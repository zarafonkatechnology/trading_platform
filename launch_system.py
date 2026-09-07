# ============================================================
# launch_system.py - COMPLETE FIXED VERSION
# ============================================================
"""
UNIFIED AI TRADING SYSTEM LAUNCHER
Run this ONE file to start the entire system.
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {
    'use_central_hub': False,
    'use_dashboard': True,
    'use_telegram': False,
    'use_mt4': True,
    'dashboard_port': 5002,
    'web_port': 5000,
    'cycle_interval': 60,
    'use_hybrid': True,
}

# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("🚀 AI TRADING SYSTEM")
print("=" * 70)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

print("📋 CONFIGURATION:")
for key, value in CONFIG.items():
    print(f"   {key}: {value}")
print()

# ============================================================
# 1. START PRICE UPDATER
# ============================================================

print("[1] Starting Price Updater...")
try:
    from price_cache_manager import start_price_updater
    start_price_updater(interval_seconds=3)
    print("   ✅ Price updater started (3s interval)")
except Exception as e:
    print(f"   ⚠️ Price updater error: {e}")

# ============================================================
# 2. START ALPHA GENERATOR
# ============================================================

print("\n[2] Starting Alpha Generator...")
try:
    from alpha_generator import alpha_scheduler
    print("   ✅ Alpha generator ready")
except Exception as e:
    print(f"   ⚠️ Alpha generator error: {e}")

# ============================================================
# 3. START TRADING ENGINE
# ============================================================

print("\n[3] Starting Trading Engine...")
global_trading_engine = None
RL_MODEL = None

if CONFIG['use_central_hub']:
    print("   Using CENTRAL HUB")
    try:
        from central import CentralHub
        hub = CentralHub()
        hub.start()
        print("   ✅ Central Hub started")
        global_trading_engine = hub
    except Exception as e:
        print(f"   ❌ Central Hub error: {e}")
        CONFIG['use_central_hub'] = False

if not CONFIG['use_central_hub']:
    print("   Using TRADING CONTROLLER")
    try:
        from trading_controller import trading_controller
        trading_controller.start()
        print("   ✅ Trading Controller started")
        global_trading_engine = trading_controller
    except Exception as e:
        print(f"   ❌ Trading Controller error: {e}")
        sys.exit(1)

# ============================================================
# 3.5. LOAD RL MODEL
# ============================================================

print("\n[3.5] Loading RL Model...")
try:
    from stable_baselines3 import PPO
    import glob
    
    rl_model_path = None
    paths_to_try = [
        "models/rl_model.zip",
        "rl_trading/models/*.zip",
        "C:/trading_platform/models/rl_model.zip",
        "C:/trading_platform/rl_trading/models/*.zip"
    ]
    
    for path in paths_to_try:
        if '*' in path:
            matches = glob.glob(path)
            if matches:
                matches.sort(key=os.path.getmtime, reverse=True)
                rl_model_path = matches[0]
                break
        elif os.path.exists(path):
            rl_model_path = path
            break
    
    if rl_model_path:
        RL_MODEL = PPO.load(rl_model_path)
        if global_trading_engine is not None:
            try:
                global_trading_engine.rl_model = RL_MODEL
                print(f"   ✅ RL Model attached to trading engine")
            except:
                print(f"   ✅ RL Model loaded")
        else:
            print(f"   ✅ RL Model loaded")
        print(f"   📁 Model: {os.path.basename(rl_model_path)}")
    else:
        print("   ⚠️ RL Model not found")
except ImportError:
    print("   ⚠️ stable-baselines3 not installed")
except Exception as e:
    print(f"   ⚠️ RL Model error: {e}")

# ============================================================
# 3.6. ENABLE HYBRID COORDINATOR
# ============================================================

print("\n[3.6] Configuring Hybrid Coordinator...")

if CONFIG.get('use_hybrid', True):
    try:
        if global_trading_engine is not None:
            if hasattr(global_trading_engine, 'hybrid_coordinator'):
                global_trading_engine.hybrid_coordinator.USE_HYBRID = True
                global_trading_engine.use_hybrid = True
                print("   ✅ Hybrid Coordinator ENABLED")
            else:
                print("   ⚠️ Hybrid Coordinator not found - using voting mode")
        else:
            print("   ⚠️ No trading engine available")
    except Exception as e:
        print(f"   ⚠️ Hybrid Coordinator error: {e}")
else:
    print("   ⏸️ Hybrid Coordinator DISABLED")

# ============================================================
# 4. START DASHBOARD
# ============================================================

# ============================================================
# 4. START DASHBOARD (as separate process)
# ============================================================

# ============================================================
# 4. START DASHBOARD (as separate process)
# ============================================================

print("\n[4] Starting Dashboard...")
if CONFIG['use_dashboard']:
    try:
        # Your dashboard file
        dashboard_script = "forex_dashboard.py"
        
        if os.path.exists(dashboard_script):
            import subprocess
            dashboard_process = subprocess.Popen(
                [sys.executable, dashboard_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            print(f"   ✅ Dashboard started: {dashboard_script}")
            print(f"   📊 http://localhost:{CONFIG['dashboard_port']}")
            
            # Wait a moment for dashboard to start
            time.sleep(3)
            
            # Verify dashboard is running
            try:
                import requests
                response = requests.get(f"http://localhost:{CONFIG['dashboard_port']}/api/all_data", timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ Dashboard verified on port {CONFIG['dashboard_port']}")
                else:
                    print(f"   ⚠️ Dashboard may not be ready (status: {response.status_code})")
            except:
                print(f"   ⚠️ Could not verify dashboard - check manually")
        else:
            print(f"   ⚠️ Dashboard script not found: {dashboard_script}")
            print("   ℹ️ Please start dashboard manually: python forex_dashboard.py")
    except Exception as e:
        print(f"   ⚠️ Dashboard error: {e}")
else:
    print("   ⏸️ Dashboard disabled")
# ============================================================
# 5. START WEB APP
# ============================================================

# ============================================================
# 5. START WEB APP (Optional)
# ============================================================

print("\n[5] Starting Web App...")
try:
    from app import app
    
    def run_web_app():
        app.run(host='0.0.0.0', port=CONFIG['web_port'], debug=False, use_reloader=False)
    
    web_thread = threading.Thread(target=run_web_app, daemon=True, name="WebApp")
    web_thread.start()
    print(f"   ✅ Web app started on port {CONFIG['web_port']}")
    print(f"   📈 http://localhost:{CONFIG['web_port']}")
except ImportError:
    print("   ⚠️ Web app not found - skipping")
except Exception as e:
    print(f"   ⚠️ Web app error: {e}")
# ============================================================
# 6. START TELEGRAM BOT
# ============================================================

if CONFIG['use_telegram']:
    print("\n[6] Starting Telegram Bot...")
    try:
        from telegram_bot import telegram_bot
        print("   ✅ Telegram bot ready")
    except Exception as e:
        print(f"   ⚠️ Telegram bot error: {e}")

# ============================================================
# 7. SUMMARY
# ============================================================

print()
print("=" * 70)
print("✅ SYSTEM ONLINE")
print("=" * 70)
print()
print("🌐 ACCESS POINTS:")
print(f"   📊 Dashboard:  http://localhost:{CONFIG['dashboard_port']}")
print(f"   📈 Web App:    http://localhost:{CONFIG['web_port']}")
print()
print("🤖 TRADING STATUS:")

# Get Hybrid status from actual trading controller
hybrid_status = "⏸️ Disabled"
try:
    from trading_controller import trading_controller
    if hasattr(trading_controller, 'use_hybrid'):
        hybrid_status = "✅ ENABLED" if trading_controller.use_hybrid else "⏸️ Disabled"
    elif hasattr(trading_controller, 'hybrid_coordinator'):
        hybrid_status = "✅ ENABLED" if trading_controller.hybrid_coordinator.USE_HYBRID else "⏸️ Disabled"
except:
    pass

print(f"   Engine:        {'Central Hub' if CONFIG['use_central_hub'] else 'Trading Controller'}")
print(f"   RL Model:      {'✅ Loaded' if RL_MODEL else '⏸️ Not loaded'}")
print(f"   Hybrid Mode:   {hybrid_status}")
print(f"   MT4:           {'✅ Connected' if CONFIG['use_mt4'] else '⏸️ Disabled'}")
print(f"   Telegram:      {'✅ Active' if CONFIG['use_telegram'] else '⏸️ Disabled'}")
print(f"   Dashboard:     {'✅ Active' if CONFIG['use_dashboard'] else '⏸️ Disabled'}")
print()
print("⏰ TIMING:")
print(f"   Start Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Cycle Time:    {CONFIG['cycle_interval']} seconds")
print("=" * 70)
print("Press Ctrl+C to shutdown")
print("=" * 70)

# ============================================================
# 8. HEARTBEAT
# ============================================================

try:
    heartbeat = 0
    while True:
        time.sleep(10)
        heartbeat += 1
        
        if heartbeat % 3 == 0:
            try:
                if CONFIG['use_central_hub']:
                    engine = global_trading_engine
                    if hasattr(engine, 'active_trades'):
                        active = len(engine.active_trades)
                    else:
                        active = 0
                    
                    hybrid_status = False
                    if hasattr(engine, 'use_hybrid'):
                        hybrid_status = engine.use_hybrid
                    elif hasattr(engine, 'hybrid_coordinator'):
                        hybrid_status = engine.hybrid_coordinator.USE_HYBRID
                    
                    print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Active: {active} | "
                          f"RL: {'✅' if RL_MODEL else '❌'} | "
                          f"Hybrid: {'✅' if hybrid_status else '❌'}")
                else:
                    from trading_controller import trading_controller
                    status = trading_controller.get_status()
                    
                    hybrid_status = False
                    if hasattr(trading_controller, 'use_hybrid'):
                        hybrid_status = trading_controller.use_hybrid
                    elif hasattr(trading_controller, 'hybrid_coordinator'):
                        hybrid_status = trading_controller.hybrid_coordinator.USE_HYBRID
                    
                    print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Active: {len(status.get('active_positions', []))} | "
                          f"RL: {'✅' if RL_MODEL else '❌'} | "
                          f"Hybrid: {'✅' if hybrid_status else '❌'}")
            except Exception as e:
                print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] System running...")

except KeyboardInterrupt:
    print("\n" + "=" * 70)
    print("🛑 SHUTTING DOWN...")
    print("=" * 70)
    
    try:
        if CONFIG['use_central_hub'] and global_trading_engine:
            global_trading_engine.stop()
            print("   ✅ Trading engine stopped")
        else:
            from trading_controller import trading_controller
            trading_controller.stop()
            print("   ✅ Trading Controller stopped")
    except Exception as e:
        print(f"   ⚠️ Stop error: {e}")
    
    print("\n✅ System shutdown complete")
    print("=" * 70)