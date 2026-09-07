# update_live_prices.py - FIXED VERSION
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from mt4_price_provider import get_mt4_prices
import time

print("=" * 60)
print("🔄 UPDATING PRICES FROM MT4 TO CACHE")
print("=" * 60)

mt4 = get_mt4_prices()

# Check MT4 connection first
print("\n1. Checking MT4 connection...")
if mt4.test_connection():
    print("   ✅ MT4 is connected")
else:
    print("   ❌ MT4 NOT connected - check EA is running")
    print("\n   Please:")
    print("   1. Start MT4")
    print("   2. Attach AI_Price_Server EA to a chart")
    print("   3. Enable AutoTrading")
    exit()

# Get all prices from MT4
print("\n2. Fetching live prices from MT4...")
live_prices = mt4.get_all_prices()

print("\n3. Updating price cache with live data...")

# Define symbol mapping
symbol_map = {
    'GOLD': 'GOLD',
    'SILVER': 'SILVER', 
    'BRENT_OIL': 'BRENT_OIL',
    'CrudeOIL': 'CrudeOIL',
    'NASDAQ100': 'NASDAQ100',
    'S&P500': 'S&P500',
    'DJ30': 'DJ30',
    'EURUSD': 'EURUSD',
    'GBPUSD': 'GBPUSD',
    'USDJPY': 'USDJPY',
    'AUDUSD': 'AUDUSD'
}

updated = 0
for display_name, data in live_prices.items():
    # Check if data has valid values (not None and > 0)
    mid = data.get('mid')
    if mid is not None and mid > 0:
        bid = data.get('bid', 0)
        ask = data.get('ask', 0)
        spread = data.get('spread', ask - bid if bid and ask else 0)
        
        # Find matching symbol in our cache
        symbol = symbol_map.get(display_name, display_name.replace('/', ''))
        
        price_cache.update_price(
            symbol=symbol,
            bid=bid if bid else mid - (spread/2),
            ask=ask if ask else mid + (spread/2),
            mid=mid,
            spread=spread,
            source='MT4_LIVE',
            display_name=display_name
        )
        updated += 1
        print(f"   ✅ {display_name:12} = {mid:.5f}")
    else:
        print(f"   ⚠️ {display_name:12} = No data (skipped)")

print(f"\n📊 Updated {updated} symbols from MT4")

# Verify cache was updated
print("\n4. Verifying cache has live prices:")
gold = price_cache.get_price('GOLD')
if gold and gold.get('mid'):
    print(f"   ✅ GOLD live price: ${gold.get('mid')} from {gold.get('source')}")
else:
    print("   ❌ GOLD not in cache yet")

# Also check other symbols
test_symbols = ['SILVER', 'EURUSD', 'NASDAQ100']
for sym in test_symbols:
    price = price_cache.get_price(sym)
    if price and price.get('mid'):
        print(f"   ✅ {sym}: {price.get('mid')}")

print("\n" + "=" * 60)
print("✅ Done! Your agents now have live MT4 prices!")
print("=" * 60)
