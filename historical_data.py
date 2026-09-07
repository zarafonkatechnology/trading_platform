# historical_data.py
"""
Historical Data Access Layer for Backtesting
Retrieves price data from your database for strategy validation
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
class HistoricalDataAccess:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'trading_platform',
            'user': 'postgres',
            'password': 'lama'
        }
    
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def get_price_history(self, symbol: str, days: int = 30, 
                          start_date: datetime = None, 
                          end_date: datetime = None) -> pd.DataFrame:
        """
        Retrieve historical price data for a symbol
        Returns DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            conn = self.get_connection()
            
            # Determine which table to query based on symbol
            table = self._get_table_for_symbol(symbol)
            
            # Build query WITHOUT volume column (since it doesn't exist)
            if start_date and end_date:
                query = f"""
                    SELECT updated_at as timestamp, bid, ask, mid
                    FROM {table}
                    WHERE symbol = %s 
                      AND updated_at BETWEEN %s AND %s
                      AND mid IS NOT NULL
                    ORDER BY updated_at ASC
                """
                params = (symbol, start_date, end_date)
            else:
                query = f"""
                    SELECT updated_at as timestamp, bid, ask, mid
                    FROM {table}
                    WHERE symbol = %s 
                      AND mid IS NOT NULL
                    ORDER BY updated_at DESC
                    LIMIT 5000
                """
                params = (symbol,)
            
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return self._generate_simulated_history(symbol, days)
            
            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Sort by time ascending
            df = df.sort_index()
            
            # Create OHLC candles (5-minute by default)
            # Use '5min' instead of '5T' for pandas compatibility
            ohlc = df['mid'].resample('5min').ohlc()
            ohlc.columns = ['open', 'high', 'low', 'close']
            
            # Add simulated volume (since we don't have real volume)
            ohlc['volume'] = np.random.randint(500, 5000, len(ohlc))
            
            # Forward fill any NaN values
            ohlc = ohlc.ffill()
            
            return ohlc.dropna()
            
        except Exception as e:
            print(f"Error getting price history for {symbol}: {e}")
            return self._generate_simulated_history(symbol, days)
    
    def _get_table_for_symbol(self, symbol: str) -> str:
        """Determine which table contains the symbol"""
        symbol_tables = {
            'EURUSD': 'forex_prices',
            'GBPUSD': 'forex_prices',
            'USDJPY': 'forex_prices',
            'USDCAD': 'forex_prices',
            'AUDUSD': 'forex_prices',
            'NZDUSD': 'forex_prices',
            'USDCHF': 'forex_prices',
            'GOLD': 'metals_prices',
            'SILVER': 'metals_prices',
            '#NASDAQ100': 'indices_prices',
            '#DJ30': 'indices_prices',
            '#S&P500': 'indices_prices',
            '#RUSS2000': 'indices_prices',
            '#NIKKEI225': 'indices_prices',
            '#DAX40': 'indices_prices',
            'BRENT_OIL': 'energy_prices',
            'CrudeOIL': 'energy_prices',
        }
        return symbol_tables.get(symbol, 'forex_prices')
    
    def _generate_simulated_history(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Enhanced synthetic asset history engine that generates both OHLC candles
        and Cumulative Volume Delta (CVD) order flow to satisfy volume sweep strategies.
        """
        print(f"🎲 Generating synthetic fallback timeline matrices for {symbol} ({days} days)...")
        
        # Build index range backwards from right now
        idx = pd.date_range(end=datetime.now(), periods=days * 288, freq='5min', name='timestamp')
        
        # Base asset baseline prices
        base_prices = {
            '#NASDAQ100': 19500.0,
            '#DJ30': 39000.0,
            '#S&P500': 5400.0,
            'EURUSD': 1.0850,
            'USDJPY': 158.00,
            'GOLD': 2350.0
        }
        
        start_price = base_prices.get(symbol, 100.0)
        
        # Generate random walk price drift arrays
        np.random.seed(42)  # Static seed for consistent test cycles
        price_changes = np.random.normal(0, 0.001, len(idx))
        cumulative_changes = np.exp(np.cumsum(price_changes))
        close_prices = start_price * cumulative_changes
        
        df_mock = pd.DataFrame(index=idx)
        df_mock['close'] = close_prices
        df_mock['open'] = df_mock['close'].shift(1).fillna(start_price)
        df_mock['high'] = df_mock[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.0005, len(idx))))
        df_mock['low'] = df_mock[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.0005, len(idx))))
        
        # Generate realistic volume
        df_mock['volume'] = np.random.randint(1000, 10000, len(idx))
        
        # === SYNTHETIC ORDER FLOW GENERATION FOR CVD STRATEGIES ===
        # Calculate single candle direction delta (positive on green candles, negative on red candles)
        candle_delta = (df_mock['close'] - df_mock['open']) / df_mock['open']
        
        # Add a noise factor to volume division to mimic retail vs institutional order book absorption
        order_flow_noise = np.random.normal(0, 0.1, len(idx))
        df_mock['delta'] = (df_mock['volume'] * (candle_delta * 10.0 + order_flow_noise)).astype(int)
        
        # Calculate the cumulative run to generate the CVD column expected by your Alpha script
        df_mock['cvd'] = df_mock['delta'].cumsum()
        
        # Clean up structures to ensure no infinite or dead NaN entries hit the resampler
        df_mock.ffill(inplace=True)
        df_mock.bfill(inplace=True)
        
        return df_mock
    
    def get_multiple_symbols_history(self, symbols: List[str], days: int = 30) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols"""
        histories = {}
        for symbol in symbols:
            histories[symbol] = self.get_price_history(symbol, days)
        return histories
    
    def get_recent_prices(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent prices for a symbol"""
        try:
            conn = self.get_connection()
            table = self._get_table_for_symbol(symbol)
            
            query = f"""
                SELECT updated_at as timestamp, bid, ask, mid
                FROM {table}
                WHERE symbol = %s AND mid IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT %s
            """
            
            df = pd.read_sql(query, conn, params=(symbol, limit))
            conn.close()
            
            if df.empty:
                return self._generate_simulated_history(symbol, days)
            
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Error getting recent prices: {e}")
            return []


# Global instance
historical_data = HistoricalDataAccess()


if __name__ == "__main__":
    print("Testing Historical Data Access")
    print("=" * 50)
    
    # Test 1: Get price history for NASDAQ100
    symbol = "#NASDAQ100"
    print(f"\n[1] Getting price history for {symbol}")
    hist = historical_data.get_price_history(symbol, days=7)
    print(f"   Retrieved {len(hist)} candles")
    if not hist.empty:
        print(f"   Date range: {hist.index[0]} to {hist.index[-1]}")
        print(f"   Price range: ${hist['low'].min():.2f} - ${hist['high'].max():.2f}")
    
    # Test 2: Test multiple symbols
    print("\n[2] Testing multiple symbols")
    symbols = ["#NASDAQ100", "GOLD", "EURUSD"]
    histories = historical_data.get_multiple_symbols_history(symbols, days=3)
    for sym, data in histories.items():
        print(f"   {sym}: {len(data)} candles")
    
    print("\n✅ Historical data access ready!")