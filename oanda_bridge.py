"""
OANDA Bridge for Multi-Agent Trading System
Handles real-time prices, orders, and account management
"""

import os
import json
import time
from datetime import datetime
import oandapyV20
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
from oandapyV20.exceptions import V20Error

class OandaBridge:
    def __init__(self, api_key=None, account_id=None, environment="practice"):
        """
        Initialize OANDA connection
        
        Args:
            api_key: Your OANDA API token
            account_id: Your OANDA account ID (format: xxx-xxx-xxxxxxx-xxx)
            environment: "practice" for demo, "live" for live trading
        """
        self.api_key = api_key or os.getenv('OANDA_API_KEY')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        
        # Set correct endpoint based on environment
        if environment == "live":
            self.environment = "live"
            self.endpoint = "https://api-fxtrade.oanda.com"
        else:
            self.environment = "practice"
            self.endpoint = "https://api-fxpractice.oanda.com"
        
        # Initialize API client
        self.client = oandapyV20.API(access_token=self.api_key, environment=self.environment)
        
        print(f"✅ OANDA Bridge initialized ({environment.upper()} mode)")
        print(f"   Account ID: {self.account_id}")
        print(f"   Endpoint: {self.endpoint}")
    
    def get_account_summary(self):
        """Get account details and balance"""
        try:
            r = accounts.AccountSummary(self.account_id)
            self.client.request(r)
            return {
                'success': True,
                'account_id': r.response['account']['id'],
                'balance': float(r.response['account']['balance']),
                'currency': r.response['account']['currency'],
                'open_trades': r.response['account']['openTradeCount'],
                'pending_orders': r.response['account']['pendingOrderCount']
            }
        except V20Error as e:
            return {'success': False, 'error': str(e)}
    
    def get_current_price(self, instrument="GOLD"):
        """
        Get real-time price for an instrument
        
        Instruments: GOLD (Gold), EURUSD, GBPUSD, USD_JPY, etc.
        """
        try:
            params = {
                "instruments": instrument
            }
            r = pricing.PricingInfo(accountID=self.account_id, params=params)
            self.client.request(r)
            
            prices = r.response.get('prices', [])
            if prices:
                price_data = prices[0]
                return {
                    'success': True,
                    'instrument': instrument,
                    'bid': float(price_data['bids'][0]['price']),
                    'ask': float(price_data['asks'][0]['price']),
                    'mid': (float(price_data['bids'][0]['price']) + float(price_data['asks'][0]['price'])) / 2,
                    'timestamp': price_data['time'],
                    'tradeable': price_data['tradeable']
                }
            return {'success': False, 'error': 'No price data returned'}
            
        except V20Error as e:
            return {'success': False, 'error': str(e)}
    def get_forex_pairs(self):
     """Get all available forex pairs only"""
     try:
          r = accounts.AccountInstruments(self.account_id)
          self.client.request(r)
        
          forex_pairs = []
          for instr in r.response.get('instruments', []):
            name = instr['name']
            # Filter for forex pairs (major, minor, exotic)
            if '_' in name and not any(x in name for x in ['XAU', 'XAG', 'BCO', 'SPX', 'NAS', 'GER']):
                forex_pairs.append({
                    'name': name,
                    'displayName': instr.get('displayName', name),
                    'pipLocation': instr.get('pipLocation'),
                    'marginRate': instr.get('marginRate'),
                    'minTradeSize': instr.get('minimumTradeSize', 1)
                })
        
            return {
            'success': True,
            'total': len(forex_pairs),
            'pairs': forex_pairs
        }
     except V20Error as e:
        return {'success': False, 'error': str(e)}
    def place_market_order(self, instrument, units, take_profit_percent=0.02, stop_loss_percent=0.01):
        """
        Place a market order
        
        Args:
            instrument: e.g., "GOLD", "EURUSD"
            units: Positive for BUY, Negative for SELL (e.g., 1000 to buy, -1000 to sell)
            take_profit_percent: TP as percentage (e.g., 0.02 = 2%)
            stop_loss_percent: SL as percentage (e.g., 0.01 = 1%)
        """
        try:
            # Get current price first
            price_info = self.get_current_price(instrument)
            if not price_info['success']:
                return price_info
            
            current_price = price_info['ask'] if units > 0 else price_info['bid']
            
            # Calculate TP and SL prices
            if units > 0:  # BUY order
                take_profit_price = round(current_price * (1 + take_profit_percent), 3)
                stop_loss_price = round(current_price * (1 - stop_loss_percent), 3)
            else:  # SELL order
                take_profit_price = round(current_price * (1 - take_profit_percent), 3)
                stop_loss_price = round(current_price * (1 + stop_loss_percent), 3)
            
            # Create market order
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "takeProfitOnFill": {
                        "price": str(take_profit_price)
                    },
                    "stopLossOnFill": {
                        "price": str(stop_loss_price)
                    }
                }
            }
            
            r = orders.OrderCreate(self.account_id, data=order_data)
            self.client.request(r)
            
            return {
                'success': True,
                'order_id': r.response['orderFillTransaction']['id'],
                'instrument': instrument,
                'units': units,
                'filled_price': float(r.response['orderFillTransaction']['price']),
                'take_profit': take_profit_price,
                'stop_loss': stop_loss_price,
                'trade_id': r.response['orderFillTransaction'].get('tradeOpened', {}).get('tradeID'),
                'timestamp': datetime.now().isoformat()
            }
            
        except V20Error as e:
            return {'success': False, 'error': str(e)}
    
    def close_trade(self, trade_id):
        """Close an open trade by ID"""
        try:
            r = trades.TradeClose(self.account_id, trade_id)
            self.client.request(r)
            return {
                'success': True,
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat()
            }
        except V20Error as e:
            return {'success': False, 'error': str(e)}
    
    def get_open_trades(self):
        """Get all open trades for the account"""
        try:
            r = trades.OpenTrades(self.account_id)
            self.client.request(r)
            return {
                'success': True,
                'trades': r.response.get('trades', []),
                'count': len(r.response.get('trades', []))
            }
        except V20Error as e:
            return {'success': False, 'error': str(e)}
    
    def get_price_history(self, instrument="GOLD", count=100, granularity="M1"):
        """
        Get historical price candles
        
        Granularity: M1, M5, M15, M30, H1, H4, D, W, M
        """
        try:
            params = {
                "count": count,
                "granularity": granularity,
                "price": "MBA"  # Mid, Bid, Ask
            }
            r = pricing.PricingCandles(instrument=instrument, params=params)
            self.client.request(r)
            
            candles = []
            for candle in r.response.get('candles', []):
                if candle['complete']:
                    candles.append({
                        'time': candle['time'],
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c'])
                    })
            
            return {
                'success': True,
                'instrument': instrument,
                'candles': candles,
                'count': len(candles)
            }
            
        except V20Error as e:
            return {'success': False, 'error': str(e)}

_oanda_instance = None

def get_oanda_bridge():
    global _oanda_instance
    if _oanda_instance is None:
        _oanda_instance = OandaBridge()
    return _oanda_instance
