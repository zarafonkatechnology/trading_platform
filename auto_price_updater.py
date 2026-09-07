# auto_price_updater.py
import time
import threading
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from mt4_price_provider import get_mt4_prices

class AutoPriceUpdater:
    def __init__(self, interval_seconds=5):
        self.interval = interval_seconds
        self.running = False
        self.mt4 = get_mt4_prices()
        
    def update_prices(self):
        """Fetch live prices from MT4 and update cache"""
        try:
            if self.mt4.test_connection():
                live_prices = self.mt4.get_all_prices()
                
                symbol_map = {
                    'GOLD': 'GOLD',
                    'SILVER': 'SILVER',
                    'BRENT OIL': 'BRENT_OIL',
                    'CrudeOIL': 'CrudeOIL',
                    'NASDAQ100': 'NAS100',
                    'S&P500': 'S&P500',
                    'DJ30': 'DJ30',
                    'EURUSD': 'EURUSD',
                    'GBPUSD': 'GBPUSD',
                    'USDJPY': 'USDJPY',
                    'AUDUSD': 'AUDUSD'
                }
                
                updated = 0
                for display_name, data in live_prices.items():
                    if data.get('mid', 0) > 0:
                        symbol = symbol_map.get(display_name, display_name.replace('/', ''))
                        price_cache.update_price(
                            symbol=symbol,
                            bid=data['bid'],
                            ask=data['ask'],
                            mid=data['mid'],
                            spread=data['spread'],
                            source='MT4_LIVE',
                            display_name=display_name
                        )
                        updated += 1
                
                if updated > 0:
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ Updated {updated} prices from MT4")
                return updated
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ MT4 not connected")
                return 0
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Update error: {e}")
            return 0
    
    def start(self):
        """Start the background updater"""
        self.running = True
        print(f"🚀 Auto price updater started (every {self.interval} seconds)")
        
        def loop():
            while self.running:
                self.update_prices()
                time.sleep(self.interval)
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
    
    def stop(self):
        self.running = False


# Start the updater
if __name__ == "__main__":
    updater = AutoPriceUpdater(interval_seconds=3)
    updater.start()
    
    print("\n📊 Monitoring price cache... Press Ctrl+C to stop\n")
    try:
        while True:
            time.sleep(10)
            # Show latest GOLD price every 10 seconds
            gold = price_cache.get_price('GOLD')
            if gold:
                print(f"💰 GOLD: ${gold.get('mid', '?')} (source: {gold.get('source', '?')})")
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping updater...")
        updater.stop()
