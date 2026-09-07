# src/core/price_cache.py
"""
In-memory price cache - No Redis required
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

class PriceCache:
    """Simple in-memory cache for prices - no external dependencies"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._prices: Dict[str, float] = {}
        self._metadata: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._subscribers = []
        self._lock = threading.Lock()
        
        logger.info("✅ PriceCache initialized (in-memory)")
    
    def update_prices(self, prices: Dict[str, float], source: str = "mt4"):
        """Update price cache"""
        with self._lock:
            self._prices = prices.copy()
            self._last_update = datetime.now()
            self._metadata['source'] = source
            self._metadata['last_update'] = self._last_update.isoformat()
            self._metadata['count'] = len(prices)
        
        # Notify subscribers
        self._notify_subscribers(prices)
    
    def get_prices(self) -> Dict[str, float]:
        """Get all cached prices"""
        with self._lock:
            return self._prices.copy()
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get price for a single symbol"""
        with self._lock:
            return self._prices.get(symbol)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get cache metadata"""
        with self._lock:
            return self._metadata.copy()
    
    def subscribe(self, callback):
        """Subscribe to price updates"""
        self._subscribers.append(callback)
    
    def _notify_subscribers(self, prices):
        """Notify all subscribers of price update"""
        for callback in self._subscribers:
            try:
                callback(prices)
            except Exception as e:
                logger.debug(f"Subscriber callback error: {e}")
    
    def clear(self):
        """Clear the cache"""
        with self._lock:
            self._prices.clear()
            self._metadata.clear()

# Singleton instance
price_cache = PriceCache()