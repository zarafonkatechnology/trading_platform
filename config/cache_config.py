CACHE_CONFIG = {
    'default_ttl': 120,           # 2 minutes default
    'price_ttl': 10,              # 10 seconds for current price
    'candles': {
        'M1': 30,                 # 30 seconds
        'M5': 60,                 # 1 minute
        'M15': 120,               # 2 minutes
        'M30': 180,               # 3 minutes
        'H1': 300,                # 5 minutes
        'H4': 900,                # 15 minutes
        'D': 3600,                # 1 hour
    },
    'max_cache_items': 100,       # Maximum items in cache
}
