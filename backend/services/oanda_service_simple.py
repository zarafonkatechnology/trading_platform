"""
Simple OANDA Market Data Service using direct REST API
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

class SimpleOandaService:
    """Simple OANDA service using direct REST calls"""
    
    def __init__(self, api_key: str, account_id: str, environment: str = 'practice'):
        self.api_key = api_key
        self.account_id = account_id
        
        # Set base URL
        if environment == 'practice':
            self.base_url = 'https://api-fxpractice.oanda.com'
        else:
            self.base_url = 'https://api-fxtrade.oanda.com'
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        self.symbols = []
        self.is_connected = False
        self.latest_prices = {}
        self.price_callbacks = []
        
        logger.info(f"SimpleOandaService initialized for {environment}")
    
    def connect(self, symbols: List[str] = None):
        """Connect to OANDA"""
        
        self.symbols = symbols or [
            'XAU/USD', 'XAG/USD', 'BCO/USD', 'WTICO/USD',
            'S&P500/USD', 'NAS100/USD', 'EURUSD', 'GBPUSD', 'USDJPY'
        ]
        
        # Test connection
        try:
            response = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/summary",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                account = data.get('account', {})
                logger.info(f"Connected to OANDA account: {account.get('id')}")
                logger.info(f"Balance: ${float(account.get('balance', 0)):,.2f}")
                self.is_connected = True
                return True
            else:
                logger.error(f"Connection failed: {response.status_code}")
                self.is_connected = False
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.is_connected = False
            return False
    
    def get_all_prices(self) -> Dict:
        """Get current prices for all symbols"""
        if not self.is_connected:
            return {}
        
        try:
            response = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/pricing",
                headers=self.headers,
                params={'instruments': ','.join(self.symbols)}
            )
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                for price in data.get('prices', []):
                    instrument = price.get('instrument')
                    bids = price.get('bids', [])
                    asks = price.get('asks', [])
                    if bids and asks:
                        bid = float(bids[0].get('price', 0))
                        ask = float(asks[0].get('price', 0))
                        prices[instrument] = (bid + ask) / 2
                        self.latest_prices[instrument] = prices[instrument]
                return prices
            return {}
            
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return {}
    
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        try:
            response = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/summary",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                account = data.get('account', {})
                return {
                    'id': account.get('id'),
                    'balance': float(account.get('balance', 0)),
                    'nav': float(account.get('nav', 0)),
                    'currency': account.get('currency', 'USD')
                }
            return {'error': f"Status: {response.status_code}"}
            
        except Exception as e:
            return {'error': str(e)}
    
    def submit_order(self, symbol: str, units: int, side: str) -> Dict:
        """Submit a market order"""
        try:
            order_units = units if side.upper() == 'BUY' else -units
            
            data = {
                'order': {
                    'type': 'MARKET',
                    'instrument': symbol,
                    'units': str(order_units)
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v3/accounts/{self.account_id}/orders",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                order_fill = result.get('orderFillTransaction', {})
                return {
                    'success': True,
                    'order_id': order_fill.get('id'),
                    'price': order_fill.get('price'),
                    'units': order_fill.get('units')
                }
            else:
                return {'success': False, 'error': f"Status: {response.status_code}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def register_price_callback(self, callback):
        self.price_callbacks.append(callback)
    
    def stop(self):
        self.is_connected = False


def get_simple_oanda_service():
    """Get OANDA service singleton"""
    api_key = os.getenv('OANDA_API_KEY')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
    
    if api_key and account_id:
        return SimpleOandaService(api_key, account_id, environment)
    return None
