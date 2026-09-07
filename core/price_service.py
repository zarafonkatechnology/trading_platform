"""Price Service - Single source of truth for ALL prices"""

import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PriceService:
    """Singleton service that provides unified price access."""
    
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
        
        # Cache
        self._prices = {}
        self._last_update = 0
        self._update_interval = 0.5
        
        # File path
        self.dashboard_file = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
        
        # Price history
        self._price_history = {}
        self._max_history = 100
        
        # Symbols
        self.forex_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
        ]
        
        self.indices = [
            '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', 
            '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
            '#AMAZON', '#APPLE', '#MICROSOFT', '#VISA', '#MASTERCARD', '#SPACEX'
        ]
        
        self.metals = ['GOLD', 'SILVER']
        self.energy = ['BRENT_OIL', 'CrudeOIL']
        self.dollar = ['#DOLLAR_IND']
        
        self.all_symbols = self.forex_pairs + self.indices + self.metals + self.energy + self.dollar
        
        # Alternative name mapping
        self.alt_map = {
            'XAUUSD': 'GOLD',
            'XAGUSD': 'SILVER',
            'NAS100': '#NASDAQ100',
            'US100': '#NASDAQ100',
            'SP500': '#S&P500',
            'US500': '#S&P500',
            'DJ30': '#DJ30',
            'US30': '#DJ30',
            'RUS2000': '#RUSS2000',
            'CAC40': '#CAC40',
            'DAX40': '#DAX40',
            'FTSE100': '#FTSE100',
            'NIKKEI225': '#NIKKEI225',
            'BRENT': 'BRENT_OIL',
            'CRUDE': 'CrudeOIL',
            'USOIL': 'CrudeOIL',
            'WTI': 'CrudeOIL',
            'DXY': '#DOLLAR_IND',
            'USDX': '#DOLLAR_IND'
        }
        
        # Fallback prices for testing
        self._fallback_prices = {
            'EURUSD': 1.14307, 'GBPUSD': 1.34144, 'USDJPY': 162.426,
            'USDCHF': 0.89500, 'AUDUSD': 0.67250, 'USDCAD': 1.36520,
            'NZDUSD': 0.61230, 'EURGBP': 0.85200, 'EURJPY': 185.620,
            'EURCAD': 1.56000, 'EURNZD': 1.86500, 'EURCHF': 0.95400,
            '#NASDAQ100': 30332.25, '#DJ30': 52654.00, '#S&P500': 7525.99,
            '#RUSS2000': 2200.00, '#CAC40': 7650.00, '#DAX40': 18800.00,
            '#FTSE100': 8350.00, '#NIKKEI225': 41200.00,
            'GOLD': 4029.97, 'SILVER': 59.18,
            'BRENT_OIL': 74.32, 'CrudeOIL': 70.97,
            '#DOLLAR_IND': 104.50
        }
        
        logger.info("PriceService initialized")
        logger.info(f"   Symbols: {len(self.all_symbols)} total")
        
        # Start background updater
        self._running = True
        self._updater_thread = threading.Thread(target=self._background_update, daemon=True)
        self._updater_thread.start()
    
    def _background_update(self):
        """Background thread to keep prices fresh"""
        while self._running:
            try:
                self.update_prices()
            except Exception:
                pass
            time.sleep(1)
    
    def update_prices(self):
        """Update all prices from sources"""
        now = time.time()
        if now - self._last_update < self._update_interval:
            return
        
        prices = {}
        
        # 1. Try dashboard file first
        file_prices = self._read_dashboard_file()
        if file_prices:
            prices.update(file_prices)
        
        # 2. If no prices, use fallback
        if not prices:
            prices = self._fallback_prices.copy()
        
        # 3. Apply alternative name mapping
        final_prices = {}
        for symbol, price in prices.items():
            if symbol in self.alt_map:
                mapped = self.alt_map[symbol]
                if mapped not in final_prices or price > 0:
                    final_prices[mapped] = price
            elif symbol in self.all_symbols:
                final_prices[symbol] = price
        
        # 4. Update price history
        for symbol, price in final_prices.items():
            if price > 0:
                if symbol not in self._price_history:
                    self._price_history[symbol] = []
                self._price_history[symbol].append(price)
                if len(self._price_history[symbol]) > self._max_history:
                    self._price_history[symbol] = self._price_history[symbol][-self._max_history:]
        
        # 5. Store prices
        self._prices = final_prices
        self._last_update = now
        self._prices['_timestamp'] = datetime.now().isoformat()
        self._prices['_source'] = 'PriceService'
    
    def _read_dashboard_file(self) -> Dict:
        """Read prices from dashboard JSON file"""
        try:
            if os.path.exists(self.dashboard_file):
                with open(self.dashboard_file, 'r') as f:
                    data = json.load(f)
                
                prices = {}
                raw_prices = data.get('prices', {})
                
                for symbol, price_data in raw_prices.items():
                    if isinstance(price_data, dict):
                        price = price_data.get('price', 0)
                    else:
                        price = float(price_data) if price_data else 0
                    
                    if price > 0:
                        prices[symbol] = price
                
                return prices
        except Exception:
            pass
        
        return {}
    
    def get_price(self, symbol: str) -> float:
        """Get price for a single symbol"""
        self.update_prices()
        return self._prices.get(symbol, 0)
    
    def get_all_prices(self) -> Dict:
        """Get all prices"""
        self.update_prices()
        return self._prices.copy()
    
    def get_price_with_change(self, symbol: str) -> Dict:
        """Get price with change percentage"""
        self.update_prices()
        
        price = self._prices.get(symbol, 0)
        change = 0.0
        
        if symbol in self._price_history and len(self._price_history[symbol]) >= 2:
            history = self._price_history[symbol]
            current = history[-1]
            previous = history[-2] if len(history) >= 2 else current
            if previous > 0:
                change = ((current - previous) / previous) * 100
        
        return {
            'price': price,
            'change': round(change, 2),
            'bid': price * 0.9999 if price > 0 else 0,
            'ask': price * 1.0001 if price > 0 else 0,
            'timestamp': self._prices.get('_timestamp', datetime.now().isoformat())
        }
    
    def get_forex_prices(self) -> Dict:
        """Get only forex prices"""
        all_prices = self.get_all_prices()
        return {symbol: price for symbol, price in all_prices.items() 
                if symbol in self.forex_pairs}
    
    def get_index_prices(self) -> Dict:
        """Get only index prices"""
        all_prices = self.get_all_prices()
        return {symbol: price for symbol, price in all_prices.items() 
                if symbol in self.indices}
    
    def get_price_history(self, symbol: str, periods: int = 60) -> List[float]:
        """Get price history for a symbol"""
        history = self._price_history.get(symbol, [])
        if periods > 0 and len(history) > periods:
            return history[-periods:]
        return history
    
    def stop(self):
        """Stop background updater"""
        self._running = False
        if self._updater_thread:
            self._updater_thread.join(timeout=2)

# Global instance
price_service = PriceService()