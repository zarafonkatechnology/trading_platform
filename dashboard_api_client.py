# dashboard_api_client.py - COMPLETE FIXED VERSION

import os
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DashboardAPIClient:
    """HTTP client for forex_dashboard.py"""
    
    def __init__(self, url='http://localhost:5002', timeout=3, max_retries=2):
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.prices = {}
        self.balance = 0
        self.equity = 0
        self.timestamp = ''
        self.connected = False
        self.last_update = 0
        self.last_error = ''
        self._cache_ttl = 5
        self._last_fetch_time = 0
    
    def fetch_prices(self, force_refresh: bool = False) -> bool:
        """Fetch prices with retry logic and caching"""
        
        # Check cache freshness
        if not force_refresh and self._is_cache_fresh():
            logger.debug(f"Using cached data (last update: {self.last_update})")
            return self.connected
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Fetching prices from {self.url} (attempt {attempt + 1})")
                response = requests.get(
                    f'{self.url}/api/all_data',
                    timeout=self.timeout,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data.get('success', False):
                        self.last_error = f"API returned success=False: {data}"
                        logger.warning(self.last_error)
                        continue
                    
                    self.connected = True
                    self.last_error = ''
                    
                    # Extract prices
                    if 'prices' in data:
                        raw_prices = data['prices']
                        self.prices = {}
                        for symbol, price_data in raw_prices.items():
                            try:
                                if isinstance(price_data, dict):
                                    price = price_data.get('price', 0)
                                else:
                                    price = float(price_data) if price_data else 0
                                
                                if price > 0 and price < 1e9:
                                    self.prices[symbol] = price
                                else:
                                    logger.warning(f"Invalid price for {symbol}: {price}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error parsing {symbol}: {e}")
                    
                    self.balance = float(data.get('balance', self.balance))
                    self.equity = float(data.get('equity', self.equity))
                    self.timestamp = data.get('timestamp', datetime.now().isoformat())
                    self.last_update = time.time()
                    self._last_fetch_time = time.time()
                    
                    logger.info(f"✅ Fetched {len(self.prices)} prices. Balance: {self.balance:.2f}")
                    return True
                    
                elif response.status_code == 404:
                    self.last_error = f"API endpoint not found: {self.url}/api/all_data"
                    logger.error(self.last_error)
                    self.connected = False
                    return False
                    
                else:
                    self.last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    logger.warning(f"Attempt {attempt + 1} failed: {self.last_error}")
                    self.connected = False
                    
            except requests.exceptions.Timeout:
                self.last_error = f"Timeout after {self.timeout}s (attempt {attempt + 1})"
                logger.warning(self.last_error)
                
            except requests.exceptions.ConnectionError:
                self.last_error = f"Connection refused (attempt {attempt + 1})"
                logger.warning(self.last_error)
                
            except json.JSONDecodeError as e:
                self.last_error = f"Invalid JSON response: {e}"
                logger.warning(self.last_error)
                
            except Exception as e:
                self.last_error = f"Unexpected error: {e}"
                logger.error(self.last_error)
            
            # Wait before retry
            if attempt < self.max_retries:
                time.sleep(0.5 * (attempt + 1))
        
        self.connected = False
        return False
    
    def _is_cache_fresh(self) -> bool:
        """Check if cached data is still fresh"""
        if not self.connected or self._last_fetch_time == 0:
            return False
        return (time.time() - self._last_fetch_time) < self._cache_ttl
    
    def get_price(self, symbol: str, default: float = 0.0) -> float:
        """Get price with fallback"""
        if not self._is_cache_fresh():
            self.fetch_prices()
        
        return self.prices.get(symbol, default)
    
    def get_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """Get multiple prices at once"""
        if not self._is_cache_fresh():
            self.fetch_prices()
        
        result = {}
        for symbol in symbols:
            result[symbol] = self.prices.get(symbol, 0.0)
        return result
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all prices"""
        if not self._is_cache_fresh():
            self.fetch_prices()
        return self.prices.copy()
    
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        return {
            'balance': self.balance,
            'equity': self.equity,
            'timestamp': self.timestamp,
            'connected': self.connected,
            'last_update': datetime.fromtimestamp(self.last_update).strftime('%H:%M:%S') if self.last_update else 'Never',
            'prices_count': len(self.prices),
            'last_error': self.last_error
        }
    
    def is_connected(self) -> bool:
        """Check if connected to dashboard"""
        if self.connected and not self._is_cache_fresh():
            self.fetch_prices()
        return self.connected
    
    def get_status(self) -> Dict:
        """Get detailed status"""
        return {
            'url': self.url,
            'connected': self.connected,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'last_update': self.last_update,
            'last_error': self.last_error,
            'prices_count': len(self.prices),
            'balance': self.balance,
            'equity': self.equity,
            'cache_ttl': self._cache_ttl,
            'is_cache_fresh': self._is_cache_fresh()
        }
    
    def wait_for_connection(self, max_wait: float = 10.0) -> bool:
        """Wait for dashboard to become available"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.fetch_prices():
                return True
            time.sleep(1.0)
        return False
    
    def health_check(self) -> bool:
        """Quick health check"""
        try:
            response = requests.get(f'{self.url}/health', timeout=2)
            return response.status_code == 200
        except:
            return False