# price_helper.py
"""
Centralized price fetching for all agents
All agents should use this to get prices
"""

import time
from datetime import datetime
from mt4_price_provider import get_mt4_prices
from price_cache_manager import price_cache

# Cache expiry in seconds
CACHE_EXPIRY = 2
API_URL = "http://127.0.0.1:5001/api/dashboard_data"
def get_all_prices() -> dict:
    """Get all prices from dashboard API"""
    try:
        response = requests.get(API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', {})
    except Exception as e:
        print(f"⚠️ API error: {e}")
    return {}
def get_all_prices_from_api() -> dict:
    """Get all prices from dashboard API"""
    try:
        response = requests.get(API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except Exception as e:
        print(f"⚠️ API error: {e}")
    return {}
def get_price_with_fallback(symbol: str, agent_name: str = "Unknown") -> float:
    """Get price from API with fallback"""
    
    all_prices = get_all_prices()
    
    if symbol in all_prices:
        return all_prices[symbol].get('price', 0.0)
    
    # Fallback to cache
    from price_cache_manager import price_cache
    cached = price_cache.get_price(symbol)
    if cached:
        print(f"⚠️ {agent_name}: Using cached price for {symbol}")
        return cached.get('price', 0.0)
    
    return 0.0
def get_price_with_details(symbol: str, agent_name: str = "Unknown") -> dict:
    """
    Get price with full details (bid, ask, mid, source)
    
    Returns:
        dict: {
            'price': float,
            'bid': float,
            'ask': float,
            'source': 'MT4' or 'CACHE',
            'age': float (seconds old)
        }
    """
    
    result = {
        'price': 0.0,
        'bid': 0.0,
        'ask': 0.0,
        'source': 'NONE',
        'age': 0.0
    }
    
    # 1. Try MT4 first
    try:
        mt4 = get_mt4_prices()
        mt4_result = mt4.get_price(symbol)
        
        if mt4_result and mt4_result.get('success'):
            bid = float(mt4_result.get('bid', 0))
            ask = float(mt4_result.get('ask', 0))
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                
                # Update cache
                price_cache.set_price(symbol, {
                    'price': mid,
                    'bid': bid,
                    'ask': ask,
                    'timestamp': datetime.now(),
                    'source': 'MT4'
                })
                
                result = {
                    'price': mid,
                    'bid': bid,
                    'ask': ask,
                    'source': 'MT4',
                    'age': 0.0
                }
                return result
    except Exception as e:
        print(f"⚠️ MT4 error for {symbol}: {e}")
    
    # 2. Fallback to cache
    cached = price_cache.get_price(symbol)
    if cached:
        age = (datetime.now() - cached.get('timestamp', datetime.now())).total_seconds()
        result = {
            'price': cached.get('price', 0.0),
            'bid': cached.get('bid', 0.0),
            'ask': cached.get('ask', 0.0),
            'source': 'CACHE',
            'age': age
        }
        print(f"⚠️ {agent_name}: Using cached price for {symbol} ({age:.1f}s old)")
        return result
    
    # 3. No price available
    print(f"❌ {agent_name}: No price available for {symbol}")
    return result


def get_multiple_prices(symbols: list, agent_name: str = "Unknown") -> dict:
    """
    Get prices for multiple symbols efficiently
    
    Args:
        symbols: List of symbol strings
        agent_name: Name of agent requesting
    
    Returns:
        dict: {symbol: price}
    """
    results = {}
    for symbol in symbols:
        results[symbol] = get_price_with_fallback(symbol, agent_name)
    return results


def is_price_valid(price: float) -> bool:
    """Check if price is valid for trading"""
    return price > 0.0


def is_price_stale(symbol: str, max_age: int = 5) -> bool:
    """Check if cached price is stale"""
    cached = price_cache.get_price(symbol)
    if cached:
        age = (datetime.now() - cached.get('timestamp', datetime.now())).total_seconds()
        return age > max_age
    return True