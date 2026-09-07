import os
import time
import json
from datetime import datetime

class MT4Client:
    def __init__(self, mt4_files_path=None):
        if mt4_files_path is None:
            # Use forward slashes for Windows path
            mt4_files_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
        
        self.command_file = os.path.join(mt4_files_path, "AI_Commands.txt")
        self.response_file = os.path.join(mt4_files_path, "AI_Responses.txt")
        self.timeout = 10
        
        print(f"✅ MT4 Client initialized (PRICES ONLY MODE)")
        print(f"   Command: {self.command_file}")
        print(f"   Response: {self.response_file}")
    
    def _send(self, command):
        """Send command to MT4 and get response"""
        try:
            with open(self.command_file, 'w') as f:
                json.dump(command, f)
            
            start = time.time()
            while time.time() - start < self.timeout:
                if os.path.exists(self.response_file):
                    with open(self.response_file, 'r') as f:
                        response = json.load(f)
                    os.remove(self.response_file)
                    return response
                time.sleep(0.1)
            
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def ping(self):
        return self._send({"command": "PING"})
    
    def get_account(self):
        return self._send({"command": "ACCOUNT"})
    
    def get_price(self, symbol):
        """Get price for a single symbol"""
        return self._send({"command": "PRICE", "symbol": symbol})
    
    def get_all_prices(self):
        """Get prices for all trading symbols"""
        symbols = [
            # Forex
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
            # Metals
            "GOLD", "SILVER",
            # Oils
            "BRENT_OIL", "CrudeOIL",
            # Indices
            "#DJ30", "#S&P500", "#NASDAQ100"
        ]
        
        # Display names for better readability
        display_names = {
            "EURUSD": "EURUSD",
            "GBPUSD": "GBPUSD",
            "USDJPY": "USDJPY",
            "AUDUSD": "AUDUSD",
            "USDCAD": "USDCAD",
            "NZDUSD": "NZDUSD",
            "COLD": "GOLD",
            "SILVER": "SILVER",
            "BRENT_OIL": "BRENT OIL",
            "CrudeOIL": "CrudeOIL",
            "#DJ30": "DJ30",
            "#S&P500": "S&P500",
            "#NASDAQ100": "NASDAQ100"
        }
        
        prices = {}
        
        for symbol in symbols:
            result = self.get_price(symbol)
            display_name = display_names.get(symbol, symbol)
            
            if result.get('success'):
                prices[display_name] = {
                    'symbol': symbol,
                    'bid': result.get('bid', 0),
                    'ask': result.get('ask', 0),
                    'mid': (result.get('bid', 0) + result.get('ask', 0)) / 2,
                    'spread': result.get('spread', 0)
                }
            else:
                prices[display_name] = {
                    'symbol': symbol,
                    'error': result.get('error', 'No data'),
                    'bid': 0,
                    'ask': 0,
                    'mid': 0,
                    'spread': 0
                }
        
        return prices


# Test - PRICES ONLY (no trading)
if __name__ == "__main__":
    mt4 = MT4Client()
    
    print("\n" + "=" * 70)
    print("📊 MT4 PRICES ONLY - No Trading")
    print("=" * 70)
    
    # Test connection
    result = mt4.ping()
    print(f"\n📡 Connection: {result}")
    
    if result.get('status') == 'OK':
        # Get account info
        acc = mt4.get_account()
        print(f"\n💰 Account Balance: ${acc.get('balance', 'N/A')}")
        
        # Get all prices
        print("\n📊 LIVE PRICES:")
        print("-" * 70)
        print(f"{'Asset':<15} {'Bid':<12} {'Ask':<12} {'Spread':<8}")
        print("-" * 70)
        
        prices = mt4.get_all_prices()
        
        for name, data in prices.items():
            if data.get('error'):
                print(f"{name:<15} ❌ {data['error']}")
            else:
                # Format based on asset type
                if 'GOLD' in name or 'SILVER' in name:
                    print(f"{name:<15} ${data['bid']:<11.2f} ${data['ask']:<11.2f} {data['spread']:<8.1f}")
                elif 'OIL' in name:
                    print(f"{name:<15} ${data['bid']:<11.2f} ${data['ask']:<11.2f} {data['spread']:<8.1f}")
                elif 'DJ30' in name or 'S&P' in name or 'NASDAQ' in name:
                    print(f"{name:<15} {data['bid']:<11.2f} {data['ask']:<11.2f} {data['spread']:<8.1f}")
                else:
                    # Forex
                    print(f"{name:<15} {data['bid']:<11.5f} {data['ask']:<11.5f} {data['spread']:<8.1f}")
        
        print("\n" + "=" * 70)
        print("✅ Prices retrieved successfully (No trades executed)")
        print("=" * 70)
        
        # Also show raw data for debugging
        print("\n📋 Raw Data:")
        print("-" * 70)
        for name, data in prices.items():
            if not data.get('error'):
                print(f"{name}: Bid={data['bid']}, Ask={data['ask']}")
        
    else:
        print("❌ Cannot connect to MT4")
    
    print("\n" + "=" * 70)
