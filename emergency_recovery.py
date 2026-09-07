# emergency_recovery.py
import os
import sys
import json
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advanced_trading_strategy import ZScoreEngineWithThresholds

def emergency_recovery():
    """Emergency recovery for Z-Score engine"""
    
    print("=" * 60)
    print("🚨 EMERGENCY RECOVERY")
    print("=" * 60)
    
    # 1. Load M15 data from MT4
    mt4_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
    history_file = os.path.join(mt4_path, "m15_history.json")
    
    if not os.path.exists(history_file):
        print("❌ M15 history file not found!")
        return False
    
    with open(history_file, 'r') as f:
        m15_data = json.load(f)
    
    print(f"✅ Loaded {len(m15_data)} symbols from M15 file")
    
    # 2. Create new engine
    engine = ZScoreEngineWithThresholds(lookback=50, entry_threshold=2.0)
    
    # 3. Load data
    loaded = 0
    for symbol, history in m15_data.items():
        if len(history) >= 20:
            for price in history:
                engine.update_price(symbol, price)
            loaded += 1
    
    print(f"✅ Loaded {loaded} symbols into new engine")
    
    # 4. Test with current prices
    import requests
    try:
        response = requests.get('http://localhost:5002/api/all_data', timeout=3)
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', {})
            
            print("\n📊 Testing Z-Score with current prices:")
            print("-" * 50)
            print(f"{'Symbol':<15} {'Z-Score':<10} {'Status':<10}")
            print("-" * 50)
            
            for symbol in ['EURUSD', 'GOLD', '#S&P500']:
                if symbol in prices:
                    price_data = prices[symbol]
                    if isinstance(price_data, dict):
                        price = price_data.get('price', 0)
                    else:
                        price = float(price_data) if price_data else 0
                    
                    if price > 0:
                        result = engine.peek_zscore(symbol, price)
                        z_score = result.get('z_score', 0)
                        samples = result.get('samples', 0)
                        
                        status = '✅ OK' if abs(z_score) > 0.01 else '⚠️ STILL 0'
                        print(f"{symbol:<15} {z_score:+.2f}     {status:<10}")
            
            print("-" * 50)
            
            # Return the engine
            return engine
    except Exception as e:
        print(f"⚠️ Error testing: {e}")
    
    return None

if __name__ == "__main__":
    engine = emergency_recovery()
    if engine:
        print("\n✅ Recovery complete! Use this engine in your controller.")
        print("   Replace self.zscore_engine with this new engine.")