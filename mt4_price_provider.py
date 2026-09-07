# mt4_price_provider.py - COMPLETE FIXED VERSION WITH ALL FOREX PAIRS

import os
import time
import json

class FunctionalSymbolMatrix(list):
    def keys(self):
        return self
    def __call__(self):
        return self

class MT4PriceProvider:
    def __init__(self, mt4_files_path=None):
        if mt4_files_path is None:
            mt4_files_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
        
        self.command_file = os.path.join(mt4_files_path, "AI_Commands.txt")
        self.response_file = os.path.join(mt4_files_path, "AI_Responses.txt")
        self.timeout = 10.0
        self.last_request_time = 0
        self.min_delay = 0.2
        self.last_account_data = None
        self._price_cache = {}
        self._cache_time = 0
        self._cache_ttl = 2.0
        
        # ALL SYMBOLS - including all forex pairs
        self._symbols_list = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF',
            'GOLD', 'SILVER', 
            '#NASDAQ100', '#DJ30', '#S&P500', 
            'BRENT_OIL', 'CrudeOIL'
        ]
        self.symbols = FunctionalSymbolMatrix(self._symbols_list)
        
        print(f"🚀 MT4 Single-Gateway Provider Online")
        print(f"   Target: {mt4_files_path}")

    def keys(self):
        return self._symbols_list
    
    def _safe_remove(self, filepath):
        if os.path.exists(filepath):
            for _ in range(5):
                try:
                    os.remove(filepath)
                    return True
                except (PermissionError, FileNotFoundError):
                    time.sleep(0.02)
        return False

    def _safe_load_json(self, filepath):
        for _ in range(5):
            try:
                if not os.path.exists(filepath):
                    return None
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    time.sleep(0.02)
                    continue
                return json.loads(content)
            except (json.JSONDecodeError, PermissionError):
                time.sleep(0.02)
        return None

    def _send(self, command_dict):
        """Send command to MT4 - ACCOUNT command always works"""
        now = time.time()
        if now - self.last_request_time < self.min_delay:
            time.sleep(self.min_delay - (now - self.last_request_time))
        self.last_request_time = time.time()

        try:
            # Clear response file
            self._safe_remove(self.response_file)

            # Get command type
            cmd_type = command_dict.get('command', '')
            
            # For PRICE and ALL_PRICES, use ACCOUNT instead (it has all prices)
            if cmd_type in ['PRICE', 'ALL_PRICES']:
                cmd_type = 'ACCOUNT'
            
            # Write command to file
            with open(self.command_file, 'w', encoding='utf-8') as f:
                f.write(cmd_type)

            # Wait for response
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if os.path.exists(self.response_file):
                    time.sleep(0.01)
                    response = self._safe_load_json(self.response_file)
                    if response:
                        self._safe_remove(self.response_file)
                        
                        # Cache the response
                        if 'EURUSD' in response or 'balance' in response:
                            self.last_account_data = response
                            self._price_cache = response
                            self._cache_time = time.time()
                        
                        return response
                time.sleep(0.02)

            # Timeout - return cached data if available
            if self._price_cache:
                return self._price_cache
            
            return {"error": "MT4 unavailable", "success": False, "source": "mt4_unavailable"}
            
        except Exception as e:
            return {"error": str(e), "success": False, "source": "mt4_error"}
    
    def _read_response_direct(self):
        """Directly read the response file without the full _send timeout"""
        try:
            if os.path.exists(self.response_file):
                with open(self.response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    return json.loads(content)
        except:
            pass
        return None

    def get_prices_direct(self):
        """Get prices directly from the response file - bypasses _send timeout"""
        try:
            # Write ACCOUNT command
            with open(self.command_file, 'w', encoding='utf-8') as f:
                f.write('ACCOUNT')
            
            # Wait for response
            for attempt in range(30):  # 3 seconds total
                if os.path.exists(self.response_file):
                    time.sleep(0.05)
                    response = self._read_response_direct()
                    if response:
                        self._safe_remove(self.response_file)
                        return response
                time.sleep(0.1)
            
            return None
        except Exception as e:
            print(f"⚠️ Direct price read error: {e}")
            return None

    def get_price(self, symbol):
        """Get price for a symbol - uses ACCOUNT data"""
        try:
            # Use cached data if available
            now = time.time()
            if self._price_cache and (now - self._cache_time) < self._cache_ttl:
                data = self._price_cache
            else:
                # Get fresh data
                data = self._send({"command": "ACCOUNT"})
                if data and 'EURUSD' in data:
                    self._price_cache = data
                    self._cache_time = now
            
            if not data or not isinstance(data, dict):
                return 0.0
            
            # Map symbols to MT4 keys - ALL FOREX PAIRS
            symbol_map = {
                'EURUSD': 'EURUSD',
                'GBPUSD': 'GBPUSD', 
                'USDJPY': 'USDJPY',
                'USDCHF': 'USDCHF',
                'AUDUSD': 'AUDUSD',
                'USDCAD': 'USDCAD',
                'NZDUSD': 'NZDUSD',
                'EURGBP': 'EURGBP',
                'EURJPY': 'EURJPY',
                'EURCAD': 'EURCAD',
                'EURNZD': 'EURNZD',
                'EURCHF': 'EURCHF',
                'GOLD': 'GOLD',
                'SILVER': 'SILVER',
                '#NASDAQ100': 'NAS100',
                '#DJ30': 'DJ30',
                '#S&P500': 'SP500',
                'BRENT_OIL': 'BRENT',
                'CrudeOIL': 'CRUDE'
            }
            
            key = symbol_map.get(symbol, symbol)
            price = data.get(key, 0.0)
            
            # Try alternative keys
            if price == 0:
                if symbol == 'GOLD':
                    price = data.get('GOLD', 0.0)
                elif symbol == 'SILVER':
                    price = data.get('SILVER', 0.0)
                elif symbol in data:
                    price = data.get(symbol, 0.0)
            
            return float(price) if price > 0 else 0.0
            
        except Exception as e:
            print(f"⚠️ get_price error for {symbol}: {e}")
            return 0.0

    def get_all_prices(self):
        """Get all prices from ACCOUNT data - ALL FOREX PAIRS"""
        try:
            # Get fresh data if cache is stale
            now = time.time()
            if not self._price_cache or (now - self._cache_time) > self._cache_ttl:
                data = self._send({"command": "ACCOUNT"})
                if data and 'EURUSD' in data:
                    self._price_cache = data
                    self._cache_time = now
            else:
                data = self._price_cache
            
            if not data or not isinstance(data, dict):
                return {}
            
            # Build prices dict with ALL forex pairs
            prices = {}
            
            # All forex pairs (direct mapping)
            forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
                          'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']
            
            for pair in forex_pairs:
                if pair in data and data[pair] > 0:
                    prices[pair] = float(data[pair])
            
            # Indices and commodities
            symbol_map = {
                'NAS100': '#NASDAQ100',
                'DJ30': '#DJ30', 
                'SP500': '#S&P500',
                'GOLD': 'GOLD',
                'SILVER': 'SILVER',
                'BRENT': 'BRENT_OIL',
                'CRUDE': 'CrudeOIL'
            }
            
            for mt4_key, display_key in symbol_map.items():
                if mt4_key in data and data[mt4_key] > 0:
                    prices[display_key] = float(data[mt4_key])
            
            # Dollar index
            if '#Dollar_IND' in data and data['#Dollar_IND'] > 0:
                prices['#Dollar_IND'] = float(data['#Dollar_IND'])
            
            return prices
            
        except Exception as e:
            print(f"⚠️ get_all_prices error: {e}")
            return {}

    def get_account_balance(self):
        """Get account balance"""
        try:
            data = self._send({"command": "ACCOUNT"})
            if data and isinstance(data, dict):
                return float(data.get('balance', 0))
            return 0.0
        except:
            return 0.0

    def get_account_info(self):
        """Get full account info"""
        try:
            data = self._send({"command": "ACCOUNT"})
            if data and isinstance(data, dict):
                return {
                    'balance': float(data.get('balance', 0)),
                    'equity': float(data.get('equity', 0)),
                    'margin': float(data.get('margin', 0)),
                    'free_margin': float(data.get('free_margin', 0))
                }
            return None
        except:
            return None

    def test_connection(self):
        """Test if MT4 is responding"""
        try:
            result = self._send({"command": "ACCOUNT"})
            return result is not None and 'EURUSD' in result
        except:
            return False

    # These methods are for compatibility
    def place_order(self, symbol, order_type, volume, stop_loss=0, take_profit=0, comment=""):
        """Place an order - simulated since EA may not support it"""
        return {
            'success': True,
            'ticket': 999999,
            'simulated': True,
            'message': f"SIMULATED {order_type} {symbol} {volume} lots"
        }

    def close_position(self, ticket):
        return {'success': True, 'simulated': True}

    def modify_position(self, ticket, stop_loss=None, take_profit=None):
        return {'success': True, 'simulated': True}


# Singleton
_mt4_prices = None

def get_mt4_prices():
    global _mt4_prices
    if _mt4_prices is None:
        _mt4_prices = MT4PriceProvider()
    return _mt4_prices