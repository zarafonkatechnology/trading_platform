# run_backtest_system.py
"""
Run full system with backtesting enabled
"""

from historical_data import historical_data
from backtest_engine import backtest_engine
from alpha_generator import alpha_scheduler, alpha_generator
from performance_dashboard import start_dashboard_server
from order_flow_analyzer import order_flow_analyzer
import threading
import time

def main():
    print("=" * 60)
    print("🚀 AI TRADING SYSTEM WITH BACKTESTING")
    print("=" * 60)
    
    # Start alpha generation with backtesting
    print("\n🧠 Starting Alpha Generator with Backtesting...")
    alpha_scheduler.start()
    
    # Start dashboard
    print("📊 Starting Performance Dashboard...")
    dashboard_thread = threading.Thread(target=start_dashboard_server, args=(5001,), daemon=True)
    dashboard_thread.start()
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM RUNNING")
    print("   Dashboard: http://localhost:5001")
    print("   Alphas will be generated and backtested every 24 hours")
    print("=" * 60)
    
    # Keep running
    try:
        while True:
            time.sleep(60)
            
            # Print periodic status
            validated_alphas = [a for a in alpha_generator.generated_alphas if a.get('backtest', {}).get('passed')]
            print(f"\n📊 Status: {len(validated_alphas)} validated alphas ready")
            
    except KeyboardInterrupt:
        print("\n🛑 System stopped")


if __name__ == "__main__":
    main()