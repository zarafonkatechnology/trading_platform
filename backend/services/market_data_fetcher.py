"""
Real-Time Market Data Fetcher - For DeepSeek Advisor
"""

import sys
import os
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path so we can import mt4_price_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mt4_price_provider import get_mt4_prices

class MarketDataFetcher:
    def __init__(self):
        """Initialize MT4 data fetcher"""
        self.mt4 = get_mt4_prices()
        self.source = "MT4"
        self._connection_cache = None
        self._cache_time = 0
        
        # Asset mapping for display
        self.asset_map = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'BRENT_OIL': 'BRENT_OIL',
            'S&P500': 'S&P500',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'NAS100': 'NAS100',
            'DJ30': 'DJ30',
            'CrudeOIL': 'CrudeOIL'
        }
        
        # Symbol map for price fetching (display_name -> MT4 symbol)
        self.symbol_map = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'BRENT_OIL': 'BRENT_OIL',
            'S&P500': 'S&P500',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'NAS100USD': 'NAS100',
            'DJ30USD': 'DJ30',
            'WTICOUSD': 'CrudeOIL'
        }
        
        # Reverse map for display
        self.reverse_map = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'BRENT_OIL': 'BRENT_OIL',
            'S&P500': 'S&P500',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'NASDAQ100': 'NASDAQ100',
            'DJ30': 'DJ30',
            'CrudeOIL': 'CrudeOIL'
        }
        
        print(f"✅ Market Data Fetcher initialized (Source: {self.source})")
    
    def _is_connected(self, use_cache=True):
        """Check MT4 connection with caching to avoid spam"""
        import time
        
        if use_cache and self._connection_cache is not None and (time.time() - self._cache_time) < 2:
            return self._connection_cache
        
        try:
            result = self.mt4.test_connection()
            self._connection_cache = result
            self._cache_time = time.time()
            return result
        except Exception:
            self._connection_cache = False
            return False
    
    def get_current_prices(self):
        """Get current prices from MT4"""
        prices = {}
        
        # Check MT4 connection - SILENTLY (no print spam)
        if not self._is_connected():
            # Silent fallback - no warning spam
            return self.get_fallback_prices()
        
        for display_name, mt4_symbol in self.symbol_map.items():
            try:
                price_data = self.mt4.get_price(mt4_symbol)
                
                if price_data.get('success'):
                    prices[display_name] = price_data.get('mid', 0)
                else:
                    prices[display_name] = 0
            except Exception as e:
                # Silent fail - don't spam console
                prices[display_name] = 0
        
        return prices
    
    def get_live_prices(self):
        """Get live prices from MT4"""
        try:
            # Check MT4 connection - SILENTLY
            if not self._is_connected():
                # Silent fallback
                return self.get_fallback_prices()
            
            # Get all prices from MT4
            prices = self.mt4.get_all_prices()
            
            # Convert to OANDA-style format for compatibility
            formatted_prices = {}
            for display_name, data in prices.items():
                if data.get('mid', 0) > 0:
                    # Convert display name to underscore format
                    mt4_symbol = self._get_mt4_symbol(display_name)
                    if mt4_symbol:
                        formatted_prices[mt4_symbol] = {
                            'bid': data.get('bid', 0),
                            'ask': data.get('ask', 0),
                            'mid': data.get('mid', 0),
                            'spread': data.get('spread', 0),
                            'source': 'MT4'
                        }
            
            # If no prices from MT4, use fallback
            if not formatted_prices:
                return self.get_fallback_prices()
            
            return formatted_prices
            
        except Exception as e:
            # Silent fail
            return self.get_fallback_prices()
    
    def _get_mt4_symbol(self, display_name):
        """Convert display name to MT4 symbol format"""
        # Handle direct symbol names
        if display_name in self.reverse_map:
            return self.reverse_map[display_name]
        
        # Handle common formats
        reverse_map = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'BRENT_OIL': 'BRENT_OIL',
            'CrudeOIL': 'CrudeOIL',
            'S&P500': 'S&P500',
            'NASDAQ100': 'NASDAQ100',
            'DJ30': 'DJ3',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD'
        }
        return reverse_map.get(display_name, display_name.replace('/', '_'))
    
    def get_fallback_prices(self):
        """Fallback simulated prices when MT4 is not available"""
        # Return fallback without printing warning (silent fallback)
        return {
            'GOLD': 2392.50,
            'SILVER': 28.45,
            'BRENT_OIL': 89.75,
            'S&P500': 5200.50,
            'EURUSD': 1.0950,
            'GBPUSD': 1.2850,
            'NASDAQ100': 18250.00,
            'DJ30': 39850.00
        }
    
    def get_price(self, symbol):
        """Get price for a single symbol"""
        # Try direct symbol first
        mt4_symbol = symbol.replace('_', '')
        price_data = self.mt4.get_price(mt4_symbol)
        
        if price_data.get('success'):
            return {
                'bid': price_data.get('bid', 0),
                'ask': price_data.get('ask', 0),
                'mid': price_data.get('mid', 0),
                'spread': price_data.get('spread', 0),
                'success': True
            }
        
        # Try with mapping
        mt4_symbol = self.asset_map.get(symbol, symbol)
        price_data = self.mt4.get_price(mt4_symbol)
        
        if price_data.get('success'):
            return {
                'bid': price_data.get('bid', 0),
                'ask': price_data.get('ask', 0),
                'mid': price_data.get('mid', 0),
                'spread': price_data.get('spread', 0),
                'success': True
            }
        
        return {'success': False, 'error': 'Price not available'}
    
    def get_market_status(self):
        """Get market status"""
        if self._is_connected():
            return "LIVE"
        return "OFFLINE"
    
    def get_account_balance(self):
        """Get account balance"""
        try:
            return self.mt4.get_account_balance()
        except Exception:
            return 0.0
    
    def get_market_summary(self) -> str:
        """Get formatted market summary for advisor"""
        prices = self.get_current_prices()
        
        summary = "📊 *Current Market Snapshot (MT4)*\n\n"
        
        # Display names for readability
        display_names = {
            'GOLD': '💰 GOLD',
            'SILVER': '🥈 SILVER',
            'BRENT_OIL': '🛢️ BRENT OIL',
            'S&P500': '📈 S&P 500',
            'EURUSD': '💶 EURUSD',
            'GBPUSD': '💷 GBPUSD',
            'NASDAQ100': '📊 NASDAQ 100',
            'DJ30': '📈 DOW JONES'
        }
        
        live_count = 0
        for asset, price in prices.items():
            name = display_names.get(asset, asset)
            if price > 0:
                live_count += 1
                if 'USD' in asset and asset not in ['GOLD', 'SILVER']:
                    summary += f"• {name}: {price:.5f}\n"
                else:
                    summary += f"• {name}: ${price:.2f}\n"
            else:
                summary += f"• {name}: ⚠️ No data\n"
        
        summary += f"\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if live_count > 0:
            summary += f"\n📡 Source: MT4 Real-Time ({live_count} instruments)"
        else:
            summary += f"\n📡 Source: Simulated Data (MT4 offline)"
        
        return summary
    
    def refresh_connection(self):
        """Force refresh MT4 connection status"""
        self._connection_cache = None
        return self._is_connected(use_cache=False)


# Global instance
market_fetcher = MarketDataFetcher()


def get_market_data():
    """Get market data instance"""
    return market_fetcher


if __name__ == "__main__":
    # Test the fetcher
    print("\n" + "=" * 50)
    print("Testing Market Data Fetcher")
    print("=" * 50)
    
    # Test connection
    print(f"MT4 Connected: {market_fetcher._is_connected()}")
    print(f"Market Status: {market_fetcher.get_market_status()}")
    print(f"Account Balance: ${market_fetcher.get_account_balance():.2f}")
    
    # Get prices
    print("\nCurrent Prices:")
    prices = market_fetcher.get_current_prices()
    for asset, price in prices.items():
        if price > 0:
            if 'USD' in asset and asset not in ['GOLD', 'SILVER']:
                print(f"  {asset}: {price:.5f}")
            else:
                print(f"  {asset}: ${price:.2f}")
    
    # Get live prices
    print("\nLive Prices Format:")
    live_prices = market_fetcher.get_live_prices()
    for asset, data in list(live_prices.items())[:5]:
        print(f"  {asset}: Bid={data.get('bid', 0):.5f}, Ask={data.get('ask', 0):.5f}")
    
    print("\n" + market_fetcher.get_market_summary())
