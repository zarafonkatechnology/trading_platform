# standalone_test.py
"""
Standalone test that doesn't depend on imports
"""

import os
import json
from datetime import datetime

class StandaloneMT4Bridge:
    """Standalone MT4 bridge for testing"""
    
    def __init__(self):
        self.mt4_files_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
        self.dashboard_file = os.path.join(self.mt4_files_path, "dashboard_data.json")
    
    def read_dashboard_data(self):
        try:
            if os.path.exists(self.dashboard_file):
                with open(self.dashboard_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    def test_connection(self):
        data = self.read_dashboard_data()
        if data:
            print(f"✅ MT4 data loaded: {len(data.get('prices', {}))} symbols")
            print(f"   Balance: ${data.get('balance', 0)}")
            return True
        else:
            print("❌ No MT4 data available")
            return False

if __name__ == "__main__":
    print("🔍 Testing MT4 Bridge")
    print("=" * 50)
    
    bridge = StandaloneMT4Bridge()
    result = bridge.test_connection()
    
    print("=" * 50)
    print(f"✅ Test {'passed' if result else 'failed'}")