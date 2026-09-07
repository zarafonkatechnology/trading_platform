import psycopg2
import psycopg2.extras
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List

class PriceCacheManager:
    def __init__(self):
        self.cache = {}
        self.cache_expiry = 2  # 2 seconds expiry
        
        # Cache stats for monitoring
        self.hits = 0
        self.misses = 0
    
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'trading_platform',
            'user': 'postgres',
            'password': 'lama'
        }
        
        # Define all symbols by category
        self.categories = {
            'forex': {
                'table': 'forex_prices',
                'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF',
                           'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY'],
                'decimals': {'default': 5, 'JPY': 3}
            },
            'metals': {
                'table': 'metals_prices',
                'symbols': ['GOLD', 'GAUUSD', 'GOLDEUR', 'SILVER', 'PLATINUM'],
                'decimals': 2,
                'prefix': '$'
            },
            'energy': {
                'table': 'energy_prices',
                'symbols': ['BRENT_OIL', 'CrudeOIL', 'NATURAL_GAS', 'GASOLINE', 'HEATING_OIL'],
                'decimals': 2,
                'prefix': '$'
            },
            'indices': {
                'table': 'indices_prices',
                'symbols': ['#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#NIKKEI225', 
                           '#DAX40', '#FTSE100', '#CAC40', '#HSI', '#CNA50', '#VIX', '#DOLLAR_IND'],
                'decimals': 2,
                'prefix': ''
            },
            'commodities': {
                'table': 'commodities_prices',
                'symbols': ['COCOA', 'COTTON#2', 'SUGAR#11', 'WHEAT', 'CORN'],
                'decimals': 2,
                'prefix': '$'
            }
        }
        
        # Display names mapping
        self.display_names = {
            'EURUSD': 'EUR/USD', 'GBPUSD': 'GBP/USD', 'USDJPY': 'USD/JPY',
            'USDCAD': 'USD/CAD', 'AUDUSD': 'AUD/USD', 'NZDUSD': 'NZD/USD', 'USDCHF': 'USD/CHF',
            'EURGBP': 'EUR/GBP', 'EURJPY': 'EUR/JPY', 'GBPJPY': 'GBP/JPY',
            'AUDJPY': 'AUD/JPY', 'CADJPY': 'CAD/JPY', 'CHFJPY': 'CHF/JPY',
            'GOLD': 'GOLD', 'SILVER': 'SILVER', 'PLATINUM': 'PLATINUM',
            'BRENT_OIL': 'BRENT OIL', 'CrudeOIL': 'CRUDE OIL',
            'NATURAL_GAS': 'NATURAL GAS', 'GASOLINE': 'GASOLINE', 'HEATING_OIL': 'HEATING OIL',
            '#NASDAQ100': 'NASDAQ100', '#DJ30': 'DJ30', '#S&P500': 'S&P500',
            '#RUSS2000': 'RUSS2000', '#NIKKEI225': 'NIKKEI225', '#DAX40': 'DAX40',
            '#FTSE100': 'FTSE100', '#CAC40': 'CAC40', '#HSI': 'HSI', '#CNA50': 'CNA50',
            'WHEAT': 'WHEAT', 'CORN': 'CORN', 'COCOA': 'COCOA', 'SUGAR': 'SUGAR', 'COTTON': 'COTTON',
        }
        
        # User-friendly name mapping (for agent queries)
        self.name_map = {
            'GOLD': 'GOLD', 'SILVER': 'SILVER', 'PLATINUM': 'PLATINUM',
            'BRENT OIL': 'BRENT_OIL', 'CRUDE OIL': 'CrudeOIL',
            'NASDAQ': '#NASDAQ100', 'NASDAQ100': '#NASDAQ100', 'NAS100': '#NASDAQ100',
            'DOW JONES': '#DJ30', 'DJ30': '#DJ30', 'DOW': '#DJ30',
            'S&P500': '#S&P500', 'SP500': '#S&P500', 'SPX': '#S&P500',
            'NATURAL GAS': 'NATURAL_GAS', 'GASOLINE': 'GASOLINE',
            'WHEAT': 'WHEAT', 'CORN': 'CORN', 'COCOA': 'COCOA',
        }
        
        self._last_update = 0
        self._update_interval = 5  # Increased from 3 to 5 seconds to reduce load
        self._mt4_offline_warning_shown = False
    
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def _update_price(self, table: str, symbol: str, bid: float, ask: float):
        """Generic price update function"""
        try:
            mid = (bid + ask) / 2
            spread = ask - bid
            display = self.display_names.get(symbol, symbol)
            
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Create table if not exists (for safety)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(50) UNIQUE,
                    display_name VARCHAR(100),
                    bid DECIMAL(20,8),
                    ask DECIMAL(20,8),
                    mid DECIMAL(20,8),
                    spread DECIMAL(20,8),
                    source VARCHAR(20),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute(f"""
                INSERT INTO {table} (symbol, display_name, bid, ask, mid, spread, source, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    mid = EXCLUDED.mid,
                    spread = EXCLUDED.spread,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at
            """, (symbol, display, bid, ask, mid, spread, 'MT4', datetime.now()))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            return False
    def _get_price(self, table: str, symbol: str) -> Optional[Dict]:
        """Get price from a specific table"""
        try:
                conn = self.get_connection()
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(f"""
                        SELECT symbol, display_name, bid, ask, mid, spread, updated_at
                        FROM {table} 
                        WHERE symbol = %s AND mid IS NOT NULL AND mid > 0
                        ORDER BY updated_at DESC
                        LIMIT 1
                """, (symbol,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                return dict(row) if row else None
        except Exception as e:
                print(f"Error getting price from {table}: {e}")
                return None
    def _get_simulated_price(self, symbol: str) -> Dict:
        """Generate simulated price when MT4 is unavailable"""
        import random
        
        # Base prices for major symbols
        base_prices = {
            'EURUSD': 1.0950, 'GBPUSD': 1.2850, 'USDJPY': 142.50,
            'USDCAD': 1.3650, 'AUDUSD': 0.6650, 'NZDUSD': 0.6150,
            'USDCHF': 0.8950, 'EURGBP': 0.8520, 'EURJPY': 156.00,
            'GBPJPY': 183.00, 'AUDJPY': 94.80, 'CADJPY': 104.30,
            'CHFJPY': 159.20, 'GOLD': 2385.50, 'SILVER': 28.50,
            'BRENT_OIL': 85.50, 'CrudeOIL': 80.25, 'NATURAL_GAS': 2.85,
            '#NASDAQ100': 18500, '#DJ30': 39800, '#S&P500': 5300
        }
        
        base = base_prices.get(symbol, 100.0)
        # Add small random movement (0.1%)
        movement = random.uniform(-0.001, 0.001)
        bid = base * (1 + movement)
        ask = bid * (1 + 0.0002)  # 0.02% spread
        
        return {
            'success': True,
            'bid': bid,
            'ask': ask,
            'mid': (bid + ask) / 2,
            'spread': ask - bid,
            'simulated': False,
            'source': 'SIMULATED'
        }
    
    def update_all_prices(self):
        """Update all prices from MT4 (with fallback to simulated)"""
        current_time = time.time()
        if current_time - self._last_update < self._update_interval:
            return 0
        
        self._last_update = current_time
        
        try:
            from mt4_price_provider import get_mt4_prices
            mt4 = get_mt4_prices()
            
            # Check connection
            is_connected = mt4.test_connection()
            
            if not is_connected:
                if not self._mt4_offline_warning_shown:
                    print("⚠️ MT4 not connected, using simulated prices")
                    self._mt4_offline_warning_shown = True
                # Use simulated prices
                return self._update_with_simulated_prices()
            
            # Reset warning flag when connected
            if self._mt4_offline_warning_shown:
                print("✅ MT4 reconnected")
                self._mt4_offline_warning_shown = False
            
            updated = 0
            for category, config in self.categories.items():
                for symbol in config['symbols']:
                    try:
                        result = mt4.get_price(symbol)
                        if result.get('success'):
                            bid = result.get('bid', 0)
                            ask = result.get('ask', 0)
                            if isinstance(bid, str):
                                bid = float(bid)
                            if isinstance(ask, str):
                                ask = float(ask)
                            if bid > 0 and ask > 0:
                                self._update_price(config['table'], symbol, bid, ask)
                                updated += 1
                        else:
                            # Use simulated price for this symbol
                            sim = self._get_simulated_price(symbol)
                            self._update_price(config['table'], symbol, sim['bid'], sim['ask'])
                            updated += 1
                    except Exception as e:
                        # Use simulated on error
                        sim = self._get_simulated_price(symbol)
                        self._update_price(config['table'], symbol, sim['bid'], sim['ask'])
                        updated += 1
            
            if updated > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {updated} prices")
            return updated
            
        except Exception as e:
            print(f"Update error: {e}")
            return self._update_with_simulated_prices()
    
    def _update_with_simulated_prices(self):
        """Update all prices using simulated data"""
        updated = 0
        for category, config in self.categories.items():
            for symbol in config['symbols']:
                sim = self._get_simulated_price(symbol)
                self._update_price(config['table'], symbol, sim['bid'], sim['ask'])
                updated += 1
        
        if updated > 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {updated} prices (SIMULATED)")
        return updated
    
    def update_cache_from_mt4(self):
        """Update all prices from MT4 and store in database"""
        return self.update_all_prices()
    
    def get_price(self, symbol: str):
        """Get price from cache with expiry"""
        if symbol in self.cache:
            entry = self.cache[symbol]
            # Check if cache is still valid
            if (datetime.now() - entry['timestamp']).total_seconds() < self.cache_expiry:
                self.hits += 1
                return entry['data']
        
        self.misses += 1
        return None
    
    def set_price(self, symbol: str, price_data: dict):
        """Store price in cache with timestamp"""
        self.cache[symbol] = {
            'data': price_data,
            'timestamp': datetime.now()
        }
    def get_price(self, query: str) -> Optional[Dict]:
        """Get price from appropriate table based on query"""
        query_upper = query.upper()
        
        # Check name mapping
        if query in self.name_map:
            query_upper = self.name_map[query]
        
        # Search in each category
        for category, config in self.categories.items():
            if query_upper in config['symbols']:
                return self._get_price(config['table'], query_upper)
            
            # Check without # for indices
            if category == 'indices' and query_upper.startswith('#'):
                if query_upper in config['symbols']:
                    return self._get_price(config['table'], query_upper)
        
        return None
    def get_cache_status(self):
        """Get cache performance metrics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cached_symbols': len(self.cache)
        }
    def format_price_response(self, query: str, agent_name: str = "Agent") -> str:
        """Format price response for agents"""
        price_data = self.get_price(query)
        
        if not price_data:
            return f"⚠️ {agent_name}: No price data for '{query}'"
        
        mid = float(price_data['mid'])
        display = price_data.get('display_name', query)
        symbol = price_data['symbol']
        source = price_data.get('source', 'CACHE')
        
        # Add source indicator for simulated data
        source_indicator = " (SIMULATED)" if source == 'SIMULATED' else ""
        
        # Format based on symbol type
        if 'JPY' in symbol:
            return f"✅ {agent_name}: {display} is currently {mid:.3f}{source_indicator}."
        elif symbol in ['EURUSD', 'GBPUSD', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF']:
            return f"✅ {agent_name}: {display} is currently {mid:.5f}{source_indicator}."
        else:
            return f"✅ {agent_name}: {display} is currently ${mid:.2f}{source_indicator}."
    
    def clear_all_prices(self):
        """Clear all prices from all tables"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for config in self.categories.values():
                cur.execute(f"DROP TABLE IF EXISTS {config['table']}")
            conn.commit()
            cur.close()
            conn.close()
            print("✅ All price tables dropped")
            return True
        except Exception as e:
            return False
    
    def get_status(self) -> Dict:
        """Get current status of price cache"""
        return {
            'mt4_connected': not self._mt4_offline_warning_shown,
            'using_simulated': self._mt4_offline_warning_shown,
            'last_update': datetime.fromtimestamp(self._last_update).isoformat() if self._last_update else None,
            'update_interval': self._update_interval
        }


# Global instance
price_cache = PriceCacheManager()


def start_price_updater(interval_seconds=3):
    """Start background price updater"""
    def update_loop():
        while True:
            try:
                price_cache.update_all_prices()
            except Exception as e:
                print(f"Update loop error: {e}")
            time.sleep(interval_seconds)
    
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    print(f"✅ Price updater started (every {interval_seconds} seconds)")
    print(f"   📡 Data source: {'SIMULATED until MT4 connects' if price_cache._mt4_offline_warning_shown else 'MT4'}")


def get_price_for_agent(agent_name: str, query: str) -> str:
    """Helper function for agents"""
    return price_cache.format_price_response(query, agent_name)


def get_any_price(symbol: str) -> Optional[Dict]:
    """Get any price"""
    return price_cache.get_price(symbol)


def force_reconnect_mt4():
    """Force a reconnection attempt to MT4"""
    try:
        from mt4_price_provider import get_mt4_prices
        mt4 = get_mt4_prices()
        # Force reconnection by shutting down and reinitializing
        mt4.shutdown()
        mt4._connect()
        price_cache._mt4_offline_warning_shown = not mt4.test_connection()
        return mt4.test_connection()
    except Exception as e:
        return False

# price_cache_manager.py - Add this metho
if __name__ == "__main__":
    print("Testing price cache...")
    print("=" * 50)
    
    # Check status
    status = price_cache.get_status()
    print(f"Status: {status}")
    
    # Update prices
    price_cache.update_all_prices()
    
    print("\n" + "=" * 50)
    print("CACHED PRICES:")
    print("=" * 50)
    
    test_queries = ['EURUSD', 'GOLD', 'NASDAQ100', 'BRENT OIL']
    for query in test_queries:
        response = price_cache.format_price_response(query, 'TestAgent')
        print(f"\n{query}: {response}")
    
    print("\n" + "=" * 50)
    print(f"✅ Price cache test complete")
    print(f"📡 Using {'SIMULATED' if price_cache._mt4_offline_warning_shown else 'MT4'} prices")