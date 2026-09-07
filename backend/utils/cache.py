"""
Simple Time-Based Cache for API Data
Prevents hitting rate limits by caching data
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict

class APICache:
    """Simple in-memory cache with TTL (Time To Live)"""
    
    def __init__(self, default_ttl_seconds=120):
        self.cache = {}
        self.default_ttl = default_ttl_seconds  # 2 minutes default
    
    def get(self, key):
        """Get cached data if not expired"""
        if key in self.cache:
            data, expiry = self.cache[key]
            if time.time() < expiry:
                return data
            else:
                # Remove expired
                del self.cache[key]
        return None
    
    def set(self, key, data, ttl_seconds=None):
        """Store data in cache with TTL"""
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
        expiry = time.time() + ttl_seconds
        self.cache[key] = (data, expiry)
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
    
    def stats(self):
        """Get cache statistics"""
        active = len([k for k, (_, exp) in self.cache.items() if time.time() < exp])
        expired = len([k for k, (_, exp) in self.cache.items() if time.time() >= exp])
        return {'active': active, 'expired': expired, 'total': len(self.cache)}


# Global cache instance (renamed to avoid OANDA reference)
api_cache = APICache(default_ttl_seconds=120)  # 2 minutes

# For backward compatibility (if other files still use 'oanda_cache')
oanda_cache = api_cache
