# mt4_helper.py
"""
Centralized MT4 connection helper - use this everywhere
"""
from mt4_price_provider import get_mt4_prices

_mt4_instance = None
_connection_cache = None
_cache_time = 0

def get_mt4():
    """Get the singleton MT4 provider instance"""
    global _mt4_instance
    if _mt4_instance is None:
        _mt4_instance = get_mt4_prices()
    return _mt4_instance

def is_mt4_connected(use_cache=True):
    """Check MT4 connection with caching to avoid spam"""
    global _connection_cache, _cache_time
    import time
    
    if use_cache and _connection_cache is not None and (time.time() - _cache_time) < 2:
        return _connection_cache
    
    mt4 = get_mt4()
    result = mt4.test_connection()
    _connection_cache = result
    _cache_time = time.time()
    return result

def get_mt4_prices_safe():
    """Get MT4 prices with fallback to cache"""
    if is_mt4_connected():
        mt4 = get_mt4()
        return mt4.get_all_prices()
    return None

def get_mt4_price_safe(symbol):
    """Get single price with fallback"""
    if is_mt4_connected():
        mt4 = get_mt4()
        return mt4.get_price(symbol)
    return None
