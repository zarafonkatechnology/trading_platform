"""
Market Signal Generator - Creates trading signals from MT4 market data
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from mt4_price_provider import get_mt4_prices

logger = logging.getLogger(__name__)

class MarketSignalGenerator:
    """Generates trading signals from real-time MT4 market data"""
    
    # Friendly names for display
    SYMBOL_NAMES = {
        'XAU/USD': '🥇 Gold',
        'XAG/USD': '🥈 Silver',
        'BCO/USD': '🛢️ Brent Oil',
        'WTICO/USD': '🛢️ WTI Oil',
        'S&P500/USD': '📊 S&P 500',
        'NAS100/USD': '📈 NASDAQ 100',
        'DE40/EUR': '🏦 DAX 40',
        'UK100/GBP': '🇬🇧 FTSE 100',
        'EURUSD': '💶 Euro',
        'GBPUSD': '💷 British Pound',
        'USDJPY': '💴 USDJPY',
        'AUDUSD': '🇦🇺 Australian Dollar',
        'USDCAD': '🇨🇦 USDCAD',
        'NZDUSD': '🇳🇿 NZ Dollar'
    }
    
    # Map display symbols to MT4 symbols
    SYMBOL_TO_MT4 = {
        'XAU/USD': 'GOLD',
        'XAG/USD': 'SILVER',
        'BCO/USD': 'BRENT_OIL',
        'WTICO/USD': 'CrudeOIL',
        'S&P500/USD': 'S&P500',
        'NAS100/USD': 'NAS100',
        'DE40/EUR': 'DE40',
        'UK100/GBP': 'UK100',
        'EURUSD': 'EURUSD',
        'GBPUSD': 'GBPUSD',
        'USDJPY': 'USDJPY',
        'AUDUSD': 'AUDUSD',
        'USDCAD': 'USDCAD',
        'NZDUSD': 'NZDUSD'
    }
    
    # List of symbols for scanning
    symbols = list(SYMBOL_NAMES.keys())
    
    def __init__(self):
        """Initialize with MT4"""
        self.mt4 = get_mt4_prices()
        self.is_connected = self.mt4.test_connection()
        logger.info("✅ Market Signal Generator initialized (Source: MT4)")
    
    def get_historical_candles(self, symbol: str, count: int = 100, granularity: str = 'H1') -> list:
        """Get historical candles from MT4 (simulated for compatibility)"""
        mt4_symbol = self.SYMBOL_TO_MT4.get(symbol, symbol.replace('/', '_'))
        price_data = self.mt4.get_price(mt4_symbol)
        
        if not price_data.get('success'):
            return []
        
        current_price = price_data.get('mid', 0)
        current_time = datetime.now()
        
        # Create synthetic candles for indicator calculation
        candles = []
        for i in range(count):
            candle_time = current_time - timedelta(hours=count - i)
            candles.append({
                'time': candle_time.isoformat(),
                'open': current_price,
                'high': current_price,
                'low': current_price,
                'close': current_price,
                'volume': 0
            })
        
        return candles
    
    def calculate_technical_indicators(self, candles: list) -> Dict:
        """Calculate technical indicators from candle data"""
        if len(candles) < 20:
            return {}
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        # Simple Moving Averages
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma_20
        
        # Price relative to SMA
        current_price = closes[-1]
        sma_ratio = (current_price - sma_20) / sma_20 if sma_20 > 0 else 0
        
        # Calculate returns
        returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else [0]
        volatility = np.std(returns[-20:]) * np.sqrt(252) if len(returns) >= 20 else 0
        
        # Momentum
        momentum_5 = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        momentum_10 = (closes[-1] - closes[-10]) / closes[-10] if len(closes) >= 10 else 0
        
        # RSI approximation
        rsi = self.calculate_rsi(closes, 14)
        
        # ATR (Average True Range) for volatility
        atr = self.calculate_atr(highs, lows, closes, 14)
        
        return {
            'current_price': current_price,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_ratio': sma_ratio,
            'volatility': volatility,
            'momentum_5': momentum_5,
            'momentum_10': momentum_10,
            'rsi': rsi,
            'atr': atr
        }
    
    def calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains[-period:]) if gains else 0
        avg_loss = np.mean(losses[-period:]) if losses else 1
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_atr(self, highs: list, lows: list, closes: list, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_values.append(tr)
        
        return np.mean(tr_values[-period:]) if tr_values else 0
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price from MT4"""
        mt4_symbol = self.SYMBOL_TO_MT4.get(symbol, symbol.replace('/', '_'))
        price_data = self.mt4.get_price(mt4_symbol)
        
        if price_data.get('success'):
            return price_data.get('mid', 0)
        return 0
    
    def generate_signal(self, symbol: str) -> Optional[Dict]:
        """Generate a trading signal for a symbol using MT4 data"""
        try:
            # Get historical candles (1 hour timeframe)
            candles = self.get_historical_candles(symbol, count=100, granularity='H1')
            
            if not candles or len(candles) < 20:
                return None
            
            # Calculate indicators
            indicators = self.calculate_technical_indicators(candles)
            
            if not indicators:
                return None
            
            # Determine signal based on multiple factors
            action = 'HOLD'
            confidence = 70
            reasons = []
            
            # Buy signals
            buy_signals = 0
            if indicators['sma_ratio'] > 0.01:
                buy_signals += 1
                reasons.append(f"SMA above 20-day ({indicators['sma_ratio']:.2%})")
            
            if indicators['momentum_5'] > 0.005:
                buy_signals += 1
                reasons.append(f"Positive 5-period momentum ({indicators['momentum_5']:.2%})")
            
            if indicators['rsi'] < 35:
                buy_signals += 1
                reasons.append(f"RSI oversold ({indicators['rsi']:.1f})")
            
            # Sell signals
            sell_signals = 0
            if indicators['sma_ratio'] < -0.01:
                sell_signals += 1
                reasons.append(f"SMA below 20-day ({abs(indicators['sma_ratio']):.2%})")
            
            if indicators['momentum_5'] < -0.005:
                sell_signals += 1
                reasons.append(f"Negative 5-period momentum ({abs(indicators['momentum_5']):.2%})")
            
            if indicators['rsi'] > 65:
                sell_signals += 1
                reasons.append(f"RSI overbought ({indicators['rsi']:.1f})")
            
            # Determine action
            if buy_signals >= 2:
                action = 'BUY'
                confidence = 70 + (buy_signals * 8)
            elif sell_signals >= 2:
                action = 'SELL'
                confidence = 70 + (sell_signals * 8)
            
            # Adjust confidence for volatility
            if indicators['volatility'] > 0.3:
                confidence -= 10
            
            confidence = max(50, min(95, confidence))
            
            if action != 'HOLD':
                return {
                    'symbol': symbol,
                    'name': self.SYMBOL_NAMES.get(symbol, symbol),
                    'action': action,
                    'price': indicators['current_price'],
                    'confidence': round(confidence, 1),
                    'signal_strength': 'STRONG_SIGNAL' if confidence >= 85 else 'SIGNAL',
                    'reasons': reasons[:3],
                    'indicators': {
                        'sma_ratio': round(indicators['sma_ratio'] * 100, 2),
                        'momentum': round(indicators['momentum_5'] * 100, 2),
                        'rsi': round(indicators['rsi'], 1),
                        'volatility': round(indicators['volatility'] * 100, 2)
                    },
                    'timestamp': datetime.now().isoformat(),
                    'source': 'MT4'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def scan_all_symbols(self) -> list:
        """Scan all symbols for trading opportunities using MT4 data"""
        if not self.mt4.test_connection():
            # # logger.warning("MT4 not connected, cannot scan signals")
            return []
        
        signals = []
        for symbol in self.symbols:
            signal = self.generate_signal(symbol)
            if signal:
                signals.append(signal)
                logger.info(f"Signal: {signal['action']} {signal['name']} @ ${signal['price']:.2f} ({signal['confidence']}%)")
        
        return signals
