# ============================================================
# price_bridge.py - NO FALLBACK, ONLY REAL DATA
# ============================================================

import json
import os
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MT4 PATHS (Same as Dashboard) ============
COMMON_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
MT4_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"

DASHBOARD_FILE_PATHS = [
    os.path.join(COMMON_FILES_PATH, "dashboard_data.json"),
    os.path.join(MT4_FILES_PATH, "dashboard_data.json")
]

# ============ ALL FOREX PAIRS ============
ALL_FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
]


class PriceBridge:
    """
    Bridge to get prices - NO FALLBACK, only real data from MT4 or dashboard file
    """
    
    def __init__(self):
        self.prices = {}
        self.last_update = None
        self.update_interval = 5  # seconds
        
    def get_mt4_prices(self) -> dict:
        """
        Get prices from MT4 - includes all forex pairs
        """
        try:
            from mt4_price_provider import get_mt4_prices
            
            # Get MT4 instance
            mt4 = get_mt4_prices()
            
            # Send ACCOUNT command (same as dashboard)
            raw_packet = mt4._send({"command": "ACCOUNT"})
            
            prices = {}
            
            if isinstance(raw_packet, dict) and "error" not in raw_packet:
                # Get all forex pairs from MT4
                for pair in ALL_FOREX_PAIRS:
                    if pair in raw_packet and raw_packet[pair] > 0:
                        prices[pair] = float(raw_packet[pair])
                
                # Get indices and commodities
                index_map = {
                    'NAS100': '#NASDAQ100',
                    'DJ30': '#DJ30',
                    'SP500': '#S&P500',
                    'GOLD': 'GOLD',
                    'SILVER': 'SILVER',
                    'BRENT': 'BRENT_OIL',
                    'CRUDE': 'CrudeOIL'
                }
                for mt4_key, display_key in index_map.items():
                    if mt4_key in raw_packet and raw_packet[mt4_key] > 0:
                        prices[display_key] = float(raw_packet[mt4_key])
                
                # Get Dollar index
                if '#Dollar_IND' in raw_packet and raw_packet['#Dollar_IND'] > 0:
                    prices['#Dollar_IND'] = float(raw_packet['#Dollar_IND'])
                
                if prices:
                    self.prices.update(prices)
                    self.last_update = datetime.now()
                    logger.info(f"✅ Got {len(prices)} prices from MT4")
            
            return prices
            
        except Exception as e:
            logger.debug(f"MT4 error: {e}")
            return {}
    
    def get_dashboard_file_prices(self) -> dict:
        """
        Get prices from dashboard file - includes all forex pairs
        """
        try:
            for path in DASHBOARD_FILE_PATHS:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        data = json.load(f)
                        prices = {}
                        
                        # Check if file has price data
                        if 'prices' in data:
                            for symbol, info in data['prices'].items():
                                if isinstance(info, dict):
                                    prices[symbol] = info.get('price', 0)
                                else:
                                    prices[symbol] = info
                        
                        # Check all forex pairs
                        for pair in ALL_FOREX_PAIRS:
                            if pair in data and pair not in prices:
                                prices[pair] = float(data.get(pair, 0))
                        
                        # Check indices and commodities
                        symbols = ['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', 'BRENT_OIL', 'CrudeOIL', '#Dollar_IND']
                        for symbol in symbols:
                            if symbol in data and symbol not in prices:
                                prices[symbol] = float(data.get(symbol, 0))
                        
                        # Check for NAS100, DJ30, SP500 aliases
                        if 'NAS100' in data and '#NASDAQ100' not in prices:
                            prices['#NASDAQ100'] = float(data.get('NAS100', 0))
                        if 'DJ30' in data and '#DJ30' not in prices:
                            prices['#DJ30'] = float(data.get('DJ30', 0))
                        if 'SP500' in data and '#S&P500' not in prices:
                            prices['#S&P500'] = float(data.get('SP500', 0))
                        
                        if prices:
                            for symbol, price in prices.items():
                                if price > 0:
                                    self.prices[symbol] = price
                            logger.info(f"✅ Got {len(prices)} prices from dashboard file")
                            return prices
                            
            return {}
            
        except Exception as e:
            logger.debug(f"Dashboard file error: {e}")
            return {}
    
    def get_price(self, symbol: str) -> float:
        """
        Get price for a specific symbol - NO FALLBACK
        """
        # 1. Try MT4 first
        mt4_prices = self.get_mt4_prices()
        if mt4_prices and symbol in mt4_prices:
            price = mt4_prices.get(symbol, 0)
            if price > 0:
                return price
        
        # 2. Try dashboard file
        file_prices = self.get_dashboard_file_prices()
        if file_prices and symbol in file_prices:
            price = file_prices.get(symbol, 0)
            if price > 0:
                return price
        
        # 3. NO FALLBACK - return 0 if not found
        return 0.0
    
    def get_all_prices(self) -> dict:
        """
        Get all prices - NO FALLBACK, only real data
        """
        prices = {}
        
        # 1. Try MT4 first
        mt4_prices = self.get_mt4_prices()
        if mt4_prices:
            prices.update(mt4_prices)
        
        # 2. Try dashboard file for missing pairs
        file_prices = self.get_dashboard_file_prices()
        if file_prices:
            for symbol, price in file_prices.items():
                if symbol not in prices or prices.get(symbol, 0) <= 0:
                    if price > 0:
                        prices[symbol] = price
        
        # 3. NO FALLBACK - return only what we have
        return prices
    
    def get_bid(self, symbol: str) -> float:
        """Get bid price."""
        return self.get_price(symbol)
    
    def get_ask(self, symbol: str) -> float:
        """Get ask price."""
        return self.get_price(symbol)
    
    def refresh(self):
        """Force refresh prices."""
        self.get_mt4_prices()
        self.get_dashboard_file_prices()
        return self.prices.copy()


# ============================================================
# GLOBAL INSTANCE
# ============================================================

price_bridge = PriceBridge()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_price_from_bridge(symbol: str) -> float:
    """Get price from bridge."""
    return price_bridge.get_price(symbol)


def get_prices_from_bridge() -> dict:
    """Get all prices from bridge."""
    return price_bridge.get_all_prices()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTING PRICE BRIDGE - NO FALLBACK")
    print("=" * 60)
    
    bridge = PriceBridge()
    
    # Get prices using same method as dashboard
    prices = bridge.get_all_prices()
    
    print("\n📊 All Prices from Bridge (Real Data Only):")
    all_symbols = ALL_FOREX_PAIRS + ['#NASDAQ100', '#S&P500', '#DJ30', 'GOLD', 'SILVER', 'BRENT_OIL', 'CrudeOIL', '#Dollar_IND']
    
    found_count = 0
    for symbol in all_symbols:
        price = prices.get(symbol, 0)
        if price > 0:
            print(f"   ✅ {symbol}: {price:.5f}")
            found_count += 1
        else:
            print(f"   ❌ {symbol}: NO PRICE")
    
    print(f"\n📊 Found {found_count} symbols with prices")
    print("=" * 60)
    print("✅ Price Bridge Ready!")