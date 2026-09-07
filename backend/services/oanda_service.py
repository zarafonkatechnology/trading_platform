"""
MT4 Market Data Service - Real-time Forex, Commodities, and Indices
Replaces OANDA with MetaTrader 4 data
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

from mt4_price_provider import get_mt4_prices

logger = logging.getLogger(__name__)

class MT4MarketData:
    """Handles real-time market data from MetaTrader 4"""
    
    def __init__(self):
        """Initialize MT4 market data service"""
        self.mt4 = get_mt4_prices()
        
        # Data storage
        self.latest_prices = {}
        self.latest_quotes = {}
        self.cached_candles = {}
        self.price_history = {}  # For candle simulation
        
        # Subscribed symbols (MT4 format)
        self.symbols = []
        
        # Display symbols mapping
        self.display_symbols = []
        
        # Callbacks
        self.price_callbacks = []
        
        # Connection status with caching
        self._connection_cache = None
        self._cache_time = 0
        self._last_error_log = 0
        self._error_log_interval = 60  # Log errors at most once per minute
        
        logger.info("MT4MarketData initialized")
    
    def _is_connected(self, use_cache=True):
        """Check MT4 connection with caching to avoid spam"""
        import time
        
        if use_cache and self._connection_cache is not None and (time.time() - self._cache_time) < 2:
            return self._connection_cache
        
        try:
            result = self.mt4.test_connection()
            self._connection_cache = result
            self._cache_time = time.time()
            self.is_connected = result
            return result
        except Exception:
            self._connection_cache = False
            self.is_connected = False
            return False
    
    def _log_error_once(self, message):
        """Log error message only once per interval to avoid spam"""
        import time
        current_time = time.time()
        if current_time - self._last_error_log > self._error_log_interval:
            logger.error(message)
            self._last_error_log = current_time
    
    def connect(self, symbols: List[str] = None):
        """Connect and initialize market data"""
        
        # Default symbols for trading (MT4 format)
        self.display_symbols = symbols or [
            'XAU/USD',    # Gold
            'XAG/USD',    # Silver
            'BCO/USD',    # Brent CrudeOIL
            'WTICO/USD',  # WTI CrudeOIL
            'S&P500/USD', # S&P 500
            'NAS100/USD', # NASDAQ 100
            'DJ30/USD',   # Dow Jones
            'EURUSD',    # Euro
            'GBPUSD',    # British Pound
            'USDJPY',    # US Dollar/Japanese Yen
            'AUDUSD',    # Australian Dollar
            'USDCAD',    # US Dollar/Canadian Dollar
            'NZDUSD'     # New Zealand Dollar
        ]
        
        # Convert to MT4 symbols
        self.symbols = [s.replace('/', '') for s in self.display_symbols]
        
        # Test connection - SILENTLY
        if self._is_connected():
            # Get account info (silently)
            balance = self.mt4.get_account_balance()
            logger.info(f"✅ MT4 connected - Balance: ${balance:.2f}")
            
            # Get initial prices
            self.refresh_all_prices()
            
            return True
        else:
            # Silent fail - don't log error here
            return False
    
    def refresh_all_prices(self):
        """Refresh all current prices from MT4"""
        # Silent check - no warning logs
        if not self._is_connected():
            return
        
        try:
            for display_symbol, mt4_symbol in zip(self.display_symbols, self.symbols):
                price_data = self.mt4.get_price(mt4_symbol)
                
                if price_data.get('success'):
                    bid = price_data.get('bid', 0)
                    ask = price_data.get('ask', 0)
                    mid = price_data.get('mid', 0)
                    
                    self.latest_prices[display_symbol] = {
                        'bid': bid,
                        'ask': ask,
                        'mid': mid,
                        'spread': price_data.get('spread', 0),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Update price history for candles
                    if display_symbol not in self.price_history:
                        self.price_history[display_symbol] = []
                    
                    self.price_history[display_symbol].append({
                        'time': datetime.now(),
                        'price': mid
                    })
                    
                    # Keep last 500 prices
                    if len(self.price_history[display_symbol]) > 500:
                        self.price_history[display_symbol] = self.price_history[display_symbol][-500:]
                    
                    # Notify callbacks
                    if mid > 0:
                        for callback in self.price_callbacks:
                            try:
                                callback(display_symbol, mid)
                            except Exception as e:
                                logger.error(f"Price callback error: {e}")
            
        except Exception as e:
            # Silent fail - only log debug
            logger.debug(f"Refresh prices error: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the current price for a symbol"""
        # Try cache first
        if symbol in self.latest_prices:
            return self.latest_prices[symbol].get('mid')
        
        # Try to fetch directly - silently
        if self._is_connected():
            mt4_symbol = symbol.replace('/', '')
            price_data = self.mt4.get_price(mt4_symbol)
            
            if price_data.get('success'):
                return price_data.get('mid', 0)
        return None
    
    def get_all_prices(self) -> Dict:
        """Get all current prices"""
        self.refresh_all_prices()
        
        prices = {}
        for symbol in self.display_symbols:
            if symbol in self.latest_prices:
                mid = self.latest_prices[symbol].get('mid')
                if mid and mid > 0:
                    prices[symbol] = mid
        
        return prices
    
    def get_historical_candles(self, symbol: str, count: int = 100, granularity: str = 'H1') -> List[Dict]:
        """Get historical candles for a symbol using price cache
        
        Granularity options:
        - M1 (1 minute), M5, M15, M30
        - H1 (1 hour), H4
        - D (1 day)
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < count:
            # Not enough history, return empty
            return []
        
        # Convert granularity to minutes
        granularity_minutes = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'D': 1440
        }.get(granularity, 60)
        
        # Group prices into candles
        candles = []
        history = self.price_history[symbol].copy()
        
        # Sort by time
        history.sort(key=lambda x: x['time'])
        
        # Create candles
        current_candle = None
        candle_start = None
        
        for entry in history:
            if candle_start is None:
                candle_start = entry['time']
                current_candle = {
                    'timestamp': candle_start.isoformat(),
                    'open': entry['price'],
                    'high': entry['price'],
                    'low': entry['price'],
                    'close': entry['price'],
                    'volume': 0
                }
            else:
                # Check if we need a new candle
                time_diff = (entry['time'] - candle_start).total_seconds() / 60
                
                if time_diff >= granularity_minutes:
                    # Close current candle and start new one
                    candles.append(current_candle)
                    candle_start = entry['time']
                    current_candle = {
                        'timestamp': candle_start.isoformat(),
                        'open': entry['price'],
                        'high': entry['price'],
                        'low': entry['price'],
                        'close': entry['price'],
                        'volume': 0
                    }
                else:
                    # Update current candle
                    current_candle['high'] = max(current_candle['high'], entry['price'])
                    current_candle['low'] = min(current_candle['low'], entry['price'])
                    current_candle['close'] = entry['price']
        
        # Add last candle
        if current_candle:
            candles.append(current_candle)
        
        # Return last 'count' candles
        return candles[-count:]
    
    def get_market_status(self) -> Dict:
        """Get current market status"""
        if self._is_connected():
            return {
                'is_open': True,
                'message': 'MT4 connected - Real-time data available',
                'source': 'MT4',
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Silent return - no warning
            return {
                'is_open': False,
                'message': 'MT4 offline - using fallback',
                'source': 'MT4',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_account_summary(self) -> Dict:
        """Get account information from MT4"""
        try:
            if self._is_connected():
                balance = self.mt4.get_account_balance()
                return {
                    'id': 'MT4 Account',
                    'balance': balance,
                    'nav': balance,
                    'margin_used': 0,
                    'margin_available': balance,
                    'currency': 'USD',
                    'status': 'connected',
                    'source': 'MT4'
                }
            else:
                # Silent return - no error log
                return {
                    'error': 'MT4 offline',
                    'status': 'disconnected',
                    'source': 'MT4'
                }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def get_open_positions(self) -> List[Dict]:
        """Get current open positions from MT4"""
        try:
            if not self._is_connected():
                return []
            
            # Query MT4 for positions
            result = self.mt4._send({"command": "POSITIONS"})
            
            if result and result.get('positions'):
                return result.get('positions', [])
            return []
            
        except Exception as e:
            logger.debug(f"Error getting positions: {e}")
            return []
    
    def submit_order(self, symbol: str, units: int, side: str, order_type: str = 'market') -> Dict:
        """Submit a trading order to MT4
        
        Args:
            symbol: Instrument name (e.g., 'XAU/USD')
            units: Positive for buy, negative for sell
            side: 'BUY' or 'SELL' (determines units sign)
            order_type: 'market' (only market orders supported)
        """
        try:
            if not self._is_connected():
                return {'success': False, 'error': 'MT4 offline'}
            
            # Convert to MT4 symbol format
            mt4_symbol = symbol.replace('/', '')
            
            # Set units sign based on side
            if side.upper() == 'BUY':
                order_units = abs(units)
                result = self.mt4.place_order(mt4_symbol, "BUY", order_units / 1000)
            else:
                order_units = -abs(units)
                result = self.mt4.place_order(mt4_symbol, "SELL", abs(units) / 1000)
            
            if result.get('success'):
                logger.info(f"Order filled: {side} {units} {symbol} @ {result.get('price')}")
                return {
                    'success': True,
                    'order_id': result.get('ticket'),
                    'symbol': symbol,
                    'units': order_units,
                    'price': result.get('price'),
                    'status': 'filled',
                    'source': 'MT4'
                }
            else:
                return {'success': False, 'error': result.get('error', 'Order failed')}
                
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            return {'success': False, 'error': str(e)}
    
    def register_price_callback(self, callback: Callable):
        """Register a callback for price updates"""
        self.price_callbacks.append(callback)
    
    def start_price_stream(self, interval_seconds: int = 2):
        """Start continuous price streaming"""
        def stream_loop():
            while True:
                try:
                    if self._is_connected():
                        self.refresh_all_prices()
                    time.sleep(interval_seconds)
                except Exception as e:
                    logger.debug(f"Price stream error: {e}")
                    time.sleep(interval_seconds)
        
        thread = threading.Thread(target=stream_loop, daemon=True)
        thread.start()
        logger.info(f"Price stream started (interval: {interval_seconds}s)")
    
    def stop(self):
        """Stop the service"""
        self.is_connected = False
        logger.info("MT4 service stopped")


# Singleton instance
_mt4_service = None

def get_mt4_service():
    """Get or create MT4 service singleton"""
    global _mt4_service
    if _mt4_service is None:
        _mt4_service = MT4MarketData()
    return _mt4_service


# For backward compatibility (if code expects OANDA service)
def get_oanda_service():
    """Compatibility wrapper - returns MT4 service"""
    return get_mt4_service()
