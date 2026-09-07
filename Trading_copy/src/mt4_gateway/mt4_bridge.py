# src/mt4_gateway/mt4_bridge.py
"""
MT4 Bridge - Fixed version with bid/ask support
"""

import os
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from mt4_price_provider import get_mt4_prices
except ImportError:
    get_mt4_prices = None
    logger.warning("⚠️ mt4_price_provider not available. MT4Bridge will not connect to live MT4.")

class MT4Bridge:
    """
    MT4 Bridge that uses live MT4 price provider only.
    """
    
    def __init__(self):
        self.files_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
        self.dashboard_file = os.path.join(self.files_path, "dashboard_data.json")
        self.mt4 = None
        self._connected = False
        self._initialize_mt4()
        logger.info(f"MT4 Bridge initialized with live provider: {get_mt4_prices is not None}")

    def _initialize_mt4(self):
        """Initialize MT4 live provider connection."""
        if get_mt4_prices is None:
            self._connected = False
            return

        try:
            self.mt4 = get_mt4_prices()
            if self.mt4:
                account = self.mt4._send({"command": "ACCOUNT"})
                if isinstance(account, dict) and not account.get('error'):
                    self._connected = True
                    logger.info("✅ Connected to MT4 live provider")
                    return
                logger.warning(f"⚠️ MT4 live provider connected but ACCOUNT failed: {account}")
            else:
                logger.warning("⚠️ MT4 live provider returned None")
        except Exception as e:
            logger.warning(f"⚠️ MT4 live provider init failed: {e}")

        self._connected = False

    def _read_dashboard_file(self) -> dict:
        """Read the dashboard file (deprecated)."""
        logger.warning("⚠️ MT4Bridge is configured to use live provider only. File read is deprecated.")
        return {}
    
    def is_connected(self) -> bool:
        """Check if connected to MT4"""
        return self._connected
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get price for a symbol from MT4 live provider only."""
        if not self._connected or not self.mt4:
            return None

        try:
            # Prefer provider-specific method
            if hasattr(self.mt4, 'get_price'):
                price = self.mt4.get_price(symbol)
                return float(price) if price and float(price) > 0 else None

            # Fallback to PRICE command if supported
            result = self.mt4._send({"command": "PRICE", "symbol": symbol})
            if isinstance(result, dict):
                bid = result.get('bid') or result.get('price') or result.get('ask')
                if bid and float(bid) > 0:
                    return float(bid)
        except Exception as e:
            logger.warning(f"⚠️ MT4Bridge get_price failed for {symbol}: {e}")

        return None
    def get_all_prices(self) -> dict:
        """Get all real-time prices from MT4"""
        try:
               if self._connected:
                     prices = {}
                     symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 
                                     'USDCAD', 'NZDUSD', 'GOLD', 'SILVER', 
                                     '#NASDAQ100', '#DJ30', '#S&P500']
                     for symbol in symbols:
                          price = self.get_price(symbol)
                          if price and price > 0:
                                  prices[symbol] = price
                     return prices
               return {}
        except Exception as e:
               logger.error(f"Error getting all prices: {e}")
               return {}
    
    def get_bid_ask(self, symbol: str) -> Optional[dict]:
        """Get bid and ask for a symbol from MT4 live provider only."""
        if not self._connected or not self.mt4:
            return None

        try:
            # Use provider PRICE command if available
            result = self.mt4._send({"command": "PRICE", "symbol": symbol})
            if isinstance(result, dict):
                bid = result.get('bid')
                ask = result.get('ask')
                if bid and ask and float(bid) > 0 and float(ask) > 0:
                    return {
                        'bid': float(bid),
                        'ask': float(ask)
                    }

            price = self.get_price(symbol)
            if price and price > 0:
                pip = self._get_pip_value(symbol)
                return {
                    'bid': round(price - pip / 2, 5),
                    'ask': round(price + pip / 2, 5)
                }
        except Exception as e:
            logger.warning(f"⚠️ MT4Bridge get_bid_ask failed for {symbol}: {e}")

        return None
    
    def get_symbols(self) -> List[str]:
        """Get list of available symbols from the MT4 live provider."""
        if self._connected and self.mt4:
            try:
                if hasattr(self.mt4, 'symbols'):
                    return list(self.mt4.symbols)
                if hasattr(self.mt4, 'keys'):
                    return list(self.mt4.keys())
            except Exception as e:
                logger.warning(f"⚠️ MT4Bridge get_symbols failed: {e}")

        return ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
                'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF', 'GOLD', 'SILVER',
                '#NASDAQ100', '#DJ30', '#S&P500', '#BRENT_OIL', 'CrudeOIL']
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        pips = {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01,
            'USDCHF': 0.0001, 'AUDUSD': 0.0001, 'USDCAD': 0.0001,
            'NZDUSD': 0.0001, 'EURGBP': 0.0001, 'EURJPY': 0.01,
            'EURCAD': 0.0001, 'EURNZD': 0.0001, 'EURCHF': 0.0001,
            'GOLD': 0.1, 'SILVER': 0.01,
            '#NASDAQ100': 0.1, '#DJ30': 0.1, '#S&P500': 0.1,
            '#RUSS2000': 0.1, '#CAC40': 0.1, '#DAX40': 0.1,
            '#FTSE100': 0.1, '#NIKKEI225': 0.1,
            'BRENT_OIL': 0.01, 'CrudeOIL': 0.01
        }
        return pips.get(symbol, 0.0001)


# ============================================================
# TEST
# ============================================================

def main():
    print("\n" + "="*60)
    print("📊 TESTING MT4 BRIDGE (FIXED)")
    print("="*60)
    
    bridge = MT4Bridge()
    
    # Test connection
    print(f"\n🔌 Connected: {bridge.is_connected()}")
    
    # Test symbols
    symbols = bridge.get_symbols()
    print(f"\n📊 Available symbols: {len(symbols)}")
    if symbols:
        print(f"   First 10: {symbols[:10]}")
    
    # Test prices
    print("\n📊 Prices:")
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', '#NASDAQ100']:
        price = bridge.get_price(symbol)
        if price:
            print(f"   {symbol}: {price:.5f}")
        else:
            print(f"   {symbol}: NOT FOUND")
    
    # Test bid/ask (FIXED)
    print("\n📊 Bid/Ask (FIXED):")
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD']:
        bid_ask = bridge.get_bid_ask(symbol)
        if bid_ask:
            spread = (bid_ask['ask'] - bid_ask['bid']) / self._get_pip_value(symbol)
            print(f"   {symbol}: Bid={bid_ask['bid']:.5f}, Ask={bid_ask['ask']:.5f}, Spread={spread:.2f} pips")
        else:
            print(f"   {symbol}: NOT FOUND")
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)


if __name__ == "__main__":
    main()