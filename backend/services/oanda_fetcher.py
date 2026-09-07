"""
OANDA Data Fetcher - Complete Working Version
"""

import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from colorama import Fore, Style

# Try to import OANDA
try:
    from oandapyV20 import API
    from oandapyV20.endpoints import accounts, pricing, instruments
    OANDA_AVAILABLE = True
except ImportError:
    OANDA_AVAILABLE = False
    print(f"{Fore.RED}⚠️  OANDA API not installed. Run: pip install oandapyV20{Style.RESET_ALL}")

# Load environment
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "101-001-38845725-001")
    OANDA_API_KEY = os.getenv("OANDA_API_KEY", "91d4d0dd73948488599e66d914c4791d-b9d39a915be08b24f485c44297e629a1")
    OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")
    
    INSTRUMENTS = {
        'WTI': 'CrudeOIL',
        'GOLD': 'GOLD',
        'SILVER': 'SILVER',
        'BRENT': 'BRENT_OIL',
        'SP500': 'S&P500',
        'EURUSD': 'EURUSD',
        'GBPUSD': 'GBPUSD'
    }
    
    CANDLE_COUNT = 50
    TIMEFRAME = 'M5'
    UPDATE_INTERVAL = 30

# ============================================================================
# OANDA DATA FETCHER
# ============================================================================

class OANDADataFetcher:
    def __init__(self, account_id: str = None, api_key: str = None, environment: str = None):
        self.account_id = account_id or Config.OANDA_ACCOUNT_ID
        self.api_key = api_key or Config.OANDA_API_KEY
        self.environment = environment or Config.OANDA_ENVIRONMENT
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        try:
            if not OANDA_AVAILABLE:
                raise ImportError("oandapyV20 not installed")
            self.client = API(access_token=self.api_key, environment=self.environment)
            r = accounts.AccountDetails(self.account_id)
            response = self.client.request(r)
            self.connected = True
            print(f"{Fore.GREEN}✅ OANDA {self.environment.upper()} Connected{Style.RESET_ALL}")
            print(f"   Balance: ${float(response['account']['balance']):,.2f}")
        except Exception as e:
            self.connected = False
            print(f"{Fore.YELLOW}⚠️  Simulated Mode: {e}{Style.RESET_ALL}")
    
    def get_live_prices(self, instruments: List[str]) -> Dict[str, Dict]:
        if not self.connected:
            return self._get_simulated_prices(instruments)
        
        try:
            r = pricing.PricingInfo(
                accountID=self.account_id,
                params={"instruments": ",".join(instruments)}
            )
            response = self.client.request(r)
            
            prices = {}
            for price_data in response.get('prices', []):
                instrument = price_data['instrument']
                bid = float(price_data['bids'][0]['price']) if price_data.get('bids') else 0
                ask = float(price_data['asks'][0]['price']) if price_data.get('asks') else 0
                prices[instrument] = {
                    'bid': bid,
                    'ask': ask,
                    'mid': (bid + ask) / 2,
                    'spread': ask - bid,
                    'timestamp': price_data.get('time', datetime.now().isoformat())
                }
            return prices
        except Exception as e:
            print(f"{Fore.RED}Error fetching prices: {e}{Style.RESET_ALL}")
            return self._get_simulated_prices(instruments)
    
    def get_candles(self, instrument: str, count: int = None, granularity: str = None) -> List[Dict]:
        count = count or Config.CANDLE_COUNT
        granularity = granularity or Config.TIMEFRAME
        
        if not self.connected:
            return self._get_simulated_candles(instrument, count)
        
        try:
            r = instruments.InstrumentsCandles(
                instrument=instrument,
                params={"count": count, "granularity": granularity, "price": "M"}
            )
            response = self.client.request(r)
            
            candles = []
            for candle in response.get('candles', []):
                if candle.get('complete'):
                    candles.append({
                        'time': candle['time'],
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': int(candle['volume'])
                    })
            return candles
        except Exception as e:
            print(f"{Fore.RED}Error fetching candles: {e}{Style.RESET_ALL}")
            return self._get_simulated_candles(instrument, count)
    
    def get_current_price(self, instrument: str) -> Optional[float]:
        """Get current price for a single instrument"""
        prices = self.get_live_prices([instrument])
        if instrument in prices:
            return prices[instrument]['mid']
        return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all instrument prices as simple dict"""
        instruments = list(Config.INSTRUMENTS.values())
        prices_data = self.get_live_prices(instruments)
        
        result = {}
        for inst, data in prices_data.items():
            # Convert back to display name
            for name, code in Config.INSTRUMENTS.items():
                if code == inst:
                    result[name] = data['mid']
                    break
            else:
                result[inst] = data['mid']
        
        return result
    
    def _get_simulated_prices(self, instruments: List[str]) -> Dict[str, Dict]:
        base_prices = {
            'CrudeOIL': 70.0,
            'GOLD': 4380.0,
            'SILVER': 68.5,
            'BRENT_OIL': 72.0,
            'S&P500': 5200.0,
            'EURUSD': 1.0725,
            'GBPUSD': 1.2530,
        }
        
        prices = {}
        for inst in instruments:
            base = base_prices.get(inst, 100.0)
            noise = random.uniform(-0.001, 0.001)
            price = base * (1 + noise)
            spread = base * 0.0001
            
            prices[inst] = {
                'bid': price - spread/2,
                'ask': price + spread/2,
                'mid': price,
                'spread': spread,
                'timestamp': datetime.now().isoformat(),
                'simulated': True
            }
        return prices
    
    def _get_simulated_candles(self, instrument: str, count: int) -> List[Dict]:
        base_prices = {
            'CrudeOIL': 70.0,
            'GOLD': 4380.0,
            'SILVER': 68.5,
        }
        
        base = base_prices.get(instrument, 100.0)
        candles = []
        
        for i in range(count):
            noise = random.uniform(-0.002, 0.002)
            close = base * (1 + noise)
            candles.append({
                'time': (datetime.now() - timedelta(minutes=count-i)).isoformat(),
                'open': close * random.uniform(0.999, 1.001),
                'high': close * random.uniform(1.000, 1.002),
                'low': close * random.uniform(0.998, 1.000),
                'close': close,
                'volume': random.randint(1000, 10000),
                'simulated': True
            })
        return candles


# Singleton instance
_oanda_fetcher = None

def get_oanda_fetcher():
    global _oanda_fetcher
    if _oanda_fetcher is None:
        _oanda_fetcher = OANDADataFetcher()
    return _oanda_fetcher
