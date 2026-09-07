# test_mt4_connection.py
"""
Test MT4 connection and basic data retrieval
"""

import sys
import os
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mt4_connection():
    """
    Test MT4 connection
    """
    print("\n" + "="*60)
    print("🔍 TESTING MT4 CONNECTION")
    print("="*60)
    
    try:
        # Try to import MT4 bridge
        from src.mt4_gateway.mt4_bridge import MT4Bridge
        
        print("✅ MT4 Bridge imported")
        
        # Initialize bridge
        bridge = MT4Bridge()
        print("✅ MT4 Bridge initialized")
        
        # Test 1: Get symbols
        print("\n📊 Test 1: Getting symbols...")
        try:
            symbols = bridge.get_symbols()
            if symbols:
                print(f"✅ Found {len(symbols)} symbols")
                print(f"   First 10: {symbols[:10]}")
            else:
                print("❌ No symbols returned")
        except Exception as e:
            print(f"❌ Error getting symbols: {e}")
        
        # Test 2: Get price for EURUSD
        print("\n📊 Test 2: Getting price for EURUSD...")
        try:
            price = bridge.get_price('EURUSD')
            if price and price > 0:
                print(f"✅ Price: {price}")
            else:
                print(f"❌ Invalid price: {price}")
        except Exception as e:
            print(f"❌ Error getting price: {e}")
        
        # Test 3: Get bid/ask for EURUSD
        print("\n📊 Test 3: Getting bid/ask for EURUSD...")
        try:
            bid_ask = bridge.get_bid_ask('EURUSD')
            if bid_ask:
                print(f"✅ Bid/Ask: {bid_ask}")
            else:
                print("❌ No bid/ask data")
        except Exception as e:
            print(f"❌ Error getting bid/ask: {e}")
        
        # Test 4: Check connection status
        print("\n📊 Test 4: Connection status...")
        try:
            is_connected = bridge.is_connected()
            print(f"✅ Connected: {is_connected}")
        except Exception as e:
            print(f"❌ Error checking connection: {e}")
        
        # Test 5: Try alternative methods
        print("\n📊 Test 5: Trying alternative price sources...")
        try:
            # Try dashboard file
            import os
            appdata = os.environ.get('APPDATA', '')
            file_path = os.path.join(appdata, 'MetaQuotes', 'Terminal', 'Common', 'Files', 'dashboard_data.json')
            
            if os.path.exists(file_path):
                print(f"✅ Dashboard file found: {file_path}")
                import json
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if 'prices' in data:
                        print(f"   Prices in file: {list(data['prices'].keys())[:5]}")
                        if 'EURUSD' in data['prices']:
                            print(f"   EURUSD price: {data['prices']['EURUSD']}")
            else:
                print(f"❌ Dashboard file not found: {file_path}")
        except Exception as e:
            print(f"❌ Error reading dashboard file: {e}")
        
        print("\n" + "="*60)
        print("✅ Debug complete!")
        print("="*60)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n📁 Check if these files exist:")
        print("   - src/mt4_gateway/mt4_bridge.py")
        print("   - src/mt4_gateway/__init__.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_mt4_connection()