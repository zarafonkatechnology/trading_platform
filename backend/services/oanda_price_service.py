"""
OANDA Real-Time Price Service for Platform 1
"""

import os
import requests
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from mt4_price_provider import get_mt4_prices

load_dotenv()
logger = logging.getLogger(__name__)

class MT4PriceService:
    """Real-time price service using MetaTrader 4"""
    
    def __init__(self):
        self.mt4 = get_mt4_prices()
        self.connected = False
        self.last_prices = {}
        
        # Asset mapping for display
        self.asset_map = {
            'GOLD': {'name': '🥇 Gold', 'symbol': 'XAU/USD', 'type': 'metal'},
            'SILVER': {'name': '🥈 Silver', 'symbol': 'XAG/USD', 'type': 'metal'},
            'BRENT_OIL': {'name': '🛢️ Brent Oil', 'symbol': 'BCO/USD', 'type': 'commodity'},
            'CrudeOIL': {'name': '🛢️ WTI Oil', 'symbol': 'WTICO/USD', 'type': 'commodity'},
            'S&P500': {'name': '📊 S&P 500', 'symbol': 'S&P500/USD', 'type': 'index'},
            'NAS100': {'name': '📈 NASDAQ', 'symbol': 'NAS100/USD', 'type': 'index'},
            'DJ30': {'name': '🏛️ Dow Jones', 'symbol': 'DJ30/USD', 'type': 'index'},
            'EURUSD': {'name': '💶 Euro', 'symbol': 'EURUSD', 'type': 'forex'},
            'GBPUSD': {'name': '💷 Pound', 'symbol': 'GBPUSD', 'type': 'forex'},
            'USDJPY': {'name': '💴 USDJPY', 'symbol': 'USDJPY', 'type': 'forex'},
            'AUDUSD': {'name': '🇦🇺 Aussie', 'symbol': 'AUDUSD', 'type': 'forex'},
            'USDCAD': {'name': '🇨🇦 Loonie', 'symbol': 'USDCAD', 'type': 'forex'},
            'NZDUSD': {'name': '🇳🇿 Kiwi', 'symbol': 'NZDUSD', 'type': 'forex'}
        }
        
        self.test_connection()
        
    def test_connection(self):
        """Test MT4 connection"""
        try:
            self.connected = self.mt4.test_connection()
            if self.connected:
                print("✅ MT4 API Connected!")
                # Get account balance as additional verification
                balance = self.mt4.get_account_balance()
                print(f"💰 Account Balance: ${balance:.2f}")
            else:
                print("⚠️ MT4 connection failed - Check EA is running")
            return self.connected
        except Exception as e:
            print(f"⚠️ MT4 connection error: {e}")
            self.connected = False
            return False
    def get_live_prices(self):
        """Get live prices from MT4"""
        if not self.connected:
            return self._get_simulated_prices()
        
        try:
            prices = {}
            
            for mt4_symbol, info in self.asset_map.items():
                price_data = self.mt4.get_price(mt4_symbol)
                
                if price_data.get('success'):
                    mid = price_data.get('mid', 0)
                    bid = price_data.get('bid', 0)
                    ask = price_data.get('ask', 0)
                    
                    # Format price based on asset type
                    if info['type'] in ['metal', 'commodity', 'index']:
                        formatted_price = round(mid, 2)
                    else:
                        formatted_price = round(mid, 5)
                    
                    prices[info['name']] = formatted_price
                    self.last_prices[info['name']] = formatted_price
                else:
                    # Use last known price or fallback
                    prices[info['name']] = self.last_prices.get(info['name'], 0)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return self._get_simulated_prices()
    def get_raw_prices(self):
        """Get raw price data (bid, ask, spread) for each asset"""
        if not self.connected:
            return {}
        
        raw_prices = {}
        for mt4_symbol, info in self.asset_map.items():
            price_data = self.mt4.get_price(mt4_symbol)
            
            if price_data.get('success'):
                raw_prices[info['name']] = {
                    'bid': price_data.get('bid', 0),
                    'ask': price_data.get('ask', 0),
                    'mid': price_data.get('mid', 0),
                    'spread': price_data.get('spread', 0),
                    'symbol': info['symbol']
                }
        
        return raw_prices
    def get_price_by_symbol(self, symbol):
        """Get price for a specific symbol (e.g., 'XAU/USD')"""
        # Find matching asset
        for mt4_symbol, info in self.asset_map.items():
            if info['symbol'] == symbol:
                price_data = self.mt4.get_price(mt4_symbol)
                if price_data.get('success'):
                    return price_data.get('mid', 0)
        return 0
    def _get_simulated_prices(self):
        """Fallback simulated prices when MT4 is not available"""
        print("📊 Using simulated prices (MT4 not connected)")
        return {
            '🥇 Gold': 2392.50,
            '🥈 Silver': 28.45,
            '🛢️ Brent Oil': 89.75,
            '🛢️ WTI Oil': 85.30,
            '📊 S&P 500': 5200.50,
            '📈 NASDAQ': 18250.00,
            '🏛️ Dow Jones': 39850.00,
            '💶 Euro': 1.0950,
            '💷 Pound': 1.2850,
            '💴 USDJPY': 142.50,
            '🇦🇺 Aussie': 0.7185,
            '🇨🇦 Loonie': 1.3785,
            '🇳🇿 Kiwi': 0.5985
        }
    def get_market_status(self):
        """Get market status"""
        if self.connected:
            return {
                'is_open': True,
                'source': 'MT4 LIVE',
                'connected': True,
                'broker': 'MT4'
            }
        return {
            'is_open': True,
            'source': 'SIMULATED',
            'connected': False,
            'broker': 'None'
        }
    def get_account_info(self):
        """Get account information"""
        if self.connected:
            balance = self.mt4.get_account_balance()
            return {
                'balance': balance,
                'currency': 'USD',
                'broker': 'MT4',
                'connected': True
            }
        return {
            'balance': 10000,
            'currency': 'USD',
            'broker': 'SIMULATED',
            'connected': False
        }
    
    def refresh(self):
        """Refresh connection and prices"""
        self.test_connection()
        return self.get_live_prices()

    def get_account_summary(self):
        """Get account summary"""
        if not self.connected:
            return {'balance': 100000, 'currency': 'USD', 'is_demo': True}
        
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                account = data.get('account', {})
                return {
                    'balance': float(account.get('balance', 0)),
                    'currency': account.get('currency', 'USD'),
                    'is_demo': False
                }
        except:
            pass
        
        return {'balance': 100000, 'currency': 'USD', 'is_demo': True}
oanda_price_service = MT4PriceService()
