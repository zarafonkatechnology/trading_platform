"""
OANDA Real-Time Price Service - WORKING VERSION
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.accounts as accounts

logger = logging.getLogger(__name__)

class OandaRealTime:
    """Working OANDA real-time price service"""
    
    def __init__(self):
        self.api_key = os.getenv('OANDA_API_KEY')
        self.account_id = os.getenv('OANDA_ACCOUNT_ID')
        
        if not self.api_key or not self.account_id:
            print("❌ OANDA credentials missing! Check .env file")
            self.client = None
            self.is_connected = False
            return
        
        # Initialize client
        self.client = oandapyV20.API(access_token=self.api_key)
        self.is_connected = True
        
        # Symbols to track (real OANDA instruments)
        self.symbols = [
            'GOLD',    # Gold
            'SILVER',    # Silver
            'BRENT_OIL',    # Brent Oil
            'CrudeOIL',  # WTI Oil
            'S&P500', # S&P 500
            'NASDAQ100', # NASDAQ
            'EURUSD',    # Euro
            'GBPUSD',    # British Pound
            'USD_JPY',    # USDJPY
            'BTC_USD'     # Bitcoin
        ]
        
        self.current_prices = {}
        self.last_update = None
        
        print(f"✅ OANDA client initialized")
    
    def get_live_prices(self) -> Dict:
        """Get live prices from OANDA"""
        if not self.client:
            return {}
        
        try:
            # Request pricing
            params = {
                "instruments": ",".join(self.symbols)
            }
            r = pricing.PricingInfo(accountID=self.account_id, params=params)
            response = self.client.request(r)
            
            prices = {}
            
            for price_data in response.get('prices', []):
                instrument = price_data.get('instrument')
                bids = price_data.get('bids', [])
                asks = price_data.get('asks', [])
                
                if bids and asks:
                    bid = float(bids[0].get('price', 0))
                    ask = float(asks[0].get('price', 0))
                    mid = (bid + ask) / 2
                    
                    # Convert instrument name back to display format
                    display_name = instrument.replace('_', '/')
                    prices[display_name] = mid
                    self.current_prices[display_name] = mid
            
            self.last_update = datetime.now()
            return prices
            
        except Exception as e:
            logger.error(f"Error getting live prices: {e}")
            return {}
    
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        if not self.client:
            return {}
        
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            response = self.client.request(r)
            
            account = response.get('account', {})
            return {
                'balance': float(account.get('balance', 0)),
                'nav': float(account.get('nav', 0)),
                'currency': account.get('currency', 'USD'),
                'margin_available': float(account.get('marginAvailable', 0))
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """Test if OANDA connection works"""
        if not self.client:
            return False
        
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            response = self.client.request(r)
            return response.get('account') is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Singleton instance
_oanda = None

def get_oanda():
    global _oanda
    if _oanda is None:
        _oanda = OandaRealTime()
    return _oanda

