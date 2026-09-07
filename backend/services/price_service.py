"""
Price Service - Using MT4 Real-Time Data (Replaces OANDA)
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List

from mt4_price_provider import get_mt4_prices

logger = logging.getLogger(__name__)

class UnifiedPriceService:
    """Price service using MT4 real-time data"""
    
    def __init__(self):
        self.mt4 = get_mt4_prices()
        self.prices = {}
        self.is_running = False
        self.update_thread = None
        
        # Asset mapping for price retrieval
        self.asset_map = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'WTI': 'CrudeOIL',
            'BRENT': 'BRENT_OIL',
            'SP500': 'S&P500',
            'NAS100': 'NAS100',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'USDJPY': 'USDJPY'
        }
        
        # Initialize prices
        self.prices = self._get_all_prices()
        
        logger.info("Price service initialized with MT4 fetcher")
        print("✅ Price Service ready (MT4 Real-Time)")
    
    def _get_all_prices(self) -> Dict:
        """Get all prices from MT4"""
        prices = {}
        
        for display_name, mt4_symbol in self.asset_map.items():
            price_data = self.mt4.get_price(mt4_symbol)
            if price_data.get('success'):
                mid = price_data.get('mid', 0)
                # Format based on asset type
                if display_name in ['GOLD', 'SILVER', 'WTI', 'BRENT', 'SP500', 'NAS100']:
                    prices[display_name] = round(mid, 2)
                else:
                    prices[display_name] = round(mid, 5)
            else:
                prices[display_name] = 0
        
        return prices
    
    def get_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        # Try direct match first
        if symbol in self.prices:
            return self.prices[symbol]
        
        # Try mapping
        mt4_symbol = self.asset_map.get(symbol)
        if mt4_symbol:
            price_data = self.mt4.get_price(mt4_symbol)
            if price_data.get('success'):
                return price_data.get('mid', 0)
        
        return 0
    
    def get_all_prices(self) -> Dict:
        """Get all prices"""
        return self._get_all_prices()
    
    def get_market_status(self) -> Dict:
        """Get market status"""
        is_connected = self.mt4.test_connection()
        return {
            'is_open': True,
            'source': 'MT4',
            'connected': is_connected
        }
    
    def get_account_info(self) -> Dict:
        """Get account info"""
        balance = self.mt4.get_account_balance()
        return {
            'balance': balance if balance > 0 else 100000,
            'currency': 'USD',
            'source': 'MT4'
        }


_price_service = None

def get_price_service():
    global _price_service
    if _price_service is None:
        _price_service = UnifiedPriceService()
    return _price_service


def generate_signals(self) -> List[Dict]:
    """Generate trading signals based on REAL current prices from MT4"""
    signals = []
    
    # Get current real prices from MT4
    gold_price = self.get_price('GOLD')
    silver_price = self.get_price('SILVER')
    wti_price = self.get_price('WTI')
    sp500_price = self.get_price('SP500')
    eur_price = self.get_price('EURUSD')
    brent_price = self.get_price('BRENT')
    
    # Gold Signal (XAU/USD)
    if gold_price and gold_price > 0:
        if gold_price < 2350:
            signals.append({
                'symbol': 'GOLD',
                'name': '🥇 Gold',
                'action': 'BUY',
                'price': gold_price,
                'confidence': 85,
                'signal_strength': 'STRONG_SIGNAL',
                'reasons': ['Gold near support level', 'Safe-haven demand increasing'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif gold_price > 2420:
            signals.append({
                'symbol': 'GOLD',
                'name': '🥇 Gold',
                'action': 'SELL',
                'price': gold_price,
                'confidence': 75,
                'signal_strength': 'SIGNAL',
                'reasons': ['Gold overbought', 'Profit taking expected'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        else:
            signals.append({
                'symbol': 'GOLD',
                'name': '🥇 Gold',
                'action': 'HOLD',
                'price': gold_price,
                'confidence': 60,
                'signal_strength': 'WEAK',
                'reasons': ['Gold ranging', 'Wait for breakout'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    # Silver Signal (XAG/USD)
    if silver_price and silver_price > 0:
        if silver_price < 27.50:
            signals.append({
                'symbol': 'SILVER',
                'name': '🥈 Silver',
                'action': 'BUY',
                'price': silver_price,
                'confidence': 80,
                'signal_strength': 'SIGNAL',
                'reasons': ['Silver undervalued', 'Industrial demand rising'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif silver_price > 29.50:
            signals.append({
                'symbol': 'SILVER',
                'name': '🥈 Silver',
                'action': 'SELL',
                'price': silver_price,
                'confidence': 70,
                'signal_strength': 'SIGNAL',
                'reasons': ['Silver overbought', 'Correction expected'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        else:
            signals.append({
                'symbol': 'SILVER',
                'name': '🥈 Silver',
                'action': 'BUY',
                'price': silver_price,
                'confidence': 65,
                'signal_strength': 'WEAK',
                'reasons': ['Silver in accumulation zone'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    # WTI Oil Signal
    if wti_price and wti_price > 0:
        if wti_price > 72:
            signals.append({
                'symbol': 'WTI',
                'name': '🛢️ WTI Oil',
                'action': 'SELL',
                'price': wti_price,
                'confidence': 78,
                'signal_strength': 'SIGNAL',
                'reasons': ['Oil overbought', 'Supply concerns easing'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif wti_price < 68:
            signals.append({
                'symbol': 'WTI',
                'name': '🛢️ WTI Oil',
                'action': 'BUY',
                'price': wti_price,
                'confidence': 75,
                'signal_strength': 'SIGNAL',
                'reasons': ['Oil near support', 'Geopolitical risks'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        else:
            signals.append({
                'symbol': 'WTI',
                'name': '🛢️ WTI Oil',
                'action': 'HOLD',
                'price': wti_price,
                'confidence': 55,
                'signal_strength': 'WEAK',
                'reasons': ['Oil ranging', 'Wait for catalyst'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    # S&P 500 Signal
    if sp500_price and sp500_price > 0:
        if sp500_price > 5100:
            signals.append({
                'symbol': 'SP500',
                'name': '📊 S&P 500',
                'action': 'HOLD',
                'price': sp500_price,
                'confidence': 65,
                'signal_strength': 'WEAK',
                'reasons': ['Index at all-time highs', 'Wait for pullback'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif sp500_price < 4900:
            signals.append({
                'symbol': 'SP500',
                'name': '📊 S&P 500',
                'action': 'BUY',
                'price': sp500_price,
                'confidence': 80,
                'signal_strength': 'SIGNAL',
                'reasons': ['Index at support', 'Bullish momentum'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        else:
            signals.append({
                'symbol': 'SP500',
                'name': '📊 S&P 500',
                'action': 'BUY',
                'price': sp500_price,
                'confidence': 70,
                'signal_strength': 'SIGNAL',
                'reasons': ['Uptrend intact', 'Earnings season strong'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    # Euro Signal
    if eur_price and eur_price > 0:
        if eur_price < 1.0650:
            signals.append({
                'symbol': 'EURUSD',
                'name': '💶 Euro',
                'action': 'BUY',
                'price': eur_price,
                'confidence': 72,
                'signal_strength': 'SIGNAL',
                'reasons': ['Euro oversold', 'Dollar weakness expected'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif eur_price > 1.0800:
            signals.append({
                'symbol': 'EURUSD',
                'name': '💶 Euro',
                'action': 'SELL',
                'price': eur_price,
                'confidence': 68,
                'signal_strength': 'SIGNAL',
                'reasons': ['Euro overbought', 'ECB dovish stance'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        else:
            signals.append({
                'symbol': 'EURUSD',
                'name': '💶 Euro',
                'action': 'HOLD',
                'price': eur_price,
                'confidence': 55,
                'signal_strength': 'WEAK',
                'reasons': ['Euro ranging', 'Wait for direction'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    # Brent Oil Signal
    if brent_price and brent_price > 0:
        if brent_price > 74:
            signals.append({
                'symbol': 'BRENT',
                'name': '🛢️ Brent Oil',
                'action': 'SELL',
                'price': brent_price,
                'confidence': 76,
                'signal_strength': 'SIGNAL',
                'reasons': ['Brent overbought', 'OPEC+ may increase supply'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
        elif brent_price < 70:
            signals.append({
                'symbol': 'BRENT',
                'name': '🛢️ Brent Oil',
                'action': 'BUY',
                'price': brent_price,
                'confidence': 74,
                'signal_strength': 'SIGNAL',
                'reasons': ['Brent near support', 'Supply concerns'],
                'timestamp': datetime.now().isoformat(),
                'source': 'MT4'
            })
    
    return signals
