
"""
Fallback Data Generator - When Real Data is Unavailable
Ensures system never breaks, always has data to trade
"""

import random
from datetime import datetime, timedelta

class FallbackDataGenerator:
    """Generates realistic mock data when real data is unavailable"""
    
    @staticmethod
    def generate_candles(instrument="EURUSD", count=100, granularity="H1"):
        """Generate realistic-looking candle data"""
        base_price = {
            'EURUSD': 1.0950,
            'GBPUSD': 1.2850,
            'USD_JPY': 142.50,
            'GOLD': 2385.00,
            'AUD_USD': 0.6650,
            'USD_CAD': 1.3650,
            'NZD_USD': 0.6050,
        }.get(instrument, 100.00)
        
        candles = []
        current_price = base_price
        now = datetime.now()
        
        minute_multiplier = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'D': 1440
        }.get(granularity, 60)
        
        for i in range(count):
            # Random walk
            change = random.uniform(-0.002, 0.002)
            if instrument == 'USD_JPY':
                change = random.uniform(-0.15, 0.15)
            elif instrument == 'GOLD':
                change = random.uniform(-3, 3)
            
            open_price = current_price
            close_price = current_price + change
            
            # Simulate high/low
            high_price = max(open_price, close_price) + abs(change) * random.uniform(0.2, 0.8)
            low_price = min(open_price, close_price) - abs(change) * random.uniform(0.2, 0.8)
            
            candle_time = now - timedelta(minutes=minute_multiplier * (count - i))
            
            candles.append({
                'time': candle_time.isoformat(),
                'open': round(open_price, 5),
                'high': round(high_price, 5),
                'low': round(low_price, 5),
                'close': round(close_price, 5),
                'volume': random.randint(1000, 10000)
            })
            
            current_price = close_price
        
        return candles
    
    @staticmethod
    def generate_indicators(instrument="EURUSD"):
        """Generate realistic technical indicators"""
        base_price = {
            'EURUSD': 1.0950,
            'GBPUSD': 1.2850,
            'USD_JPY': 142.50,
            'GOLD': 2385.00,
        }.get(instrument, 100.00)
        
        # Random but realistic indicator values
        random.seed(hash(instrument + datetime.now().strftime('%Y%m%d%H')))
        
        trend = random.choice(['up', 'down', 'sideways'])
        strength = random.uniform(0.3, 0.9)
        
        if trend == 'up':
            rsi = random.uniform(55, 75)
            macd = random.uniform(0.001, 0.005)
            adx = random.uniform(25, 45)
        elif trend == 'down':
            rsi = random.uniform(25, 45)
            macd = random.uniform(-0.005, -0.001)
            adx = random.uniform(25, 45)
        else:
            rsi = random.uniform(45, 55)
            macd = random.uniform(-0.001, 0.001)
            adx = random.uniform(15, 25)
        
        return {
            'current_price': base_price,
            'ma20': base_price * (1 + random.uniform(-0.005, 0.005)),
            'ma50': base_price * (1 + random.uniform(-0.01, 0.01)),
            'ma200': base_price * (1 + random.uniform(-0.03, 0.03)),
            'rsi14': rsi,
            'macd': macd,
            'macd_signal': macd * random.uniform(0.5, 1.5),
            'atr14': base_price * random.uniform(0.003, 0.01),
            'volume_ratio': random.uniform(0.6, 1.8),
            'trend_strength': adx,
            'volatility': random.uniform(0.005, 0.02),
            'is_fallback': True  # Mark as fallback data
        }
    
    @staticmethod
    def generate_price(instrument="EURUSD"):
        """Generate single price point"""
        base_price = {
            'EURUSD': 1.0950,
            'GBPUSD': 1.2850,
            'USD_JPY': 142.50,
            'GOLD': 2385.00,
        }.get(instrument, 100.00)
        
        # Add small random movement
        change_pct = random.uniform(-0.001, 0.001)
        price = base_price * (1 + change_pct)
        
        return {
            'success': True,
            'instrument': instrument,
            'bid': round(price - 0.0001, 5),
            'ask': round(price + 0.0001, 5),
            'mid': round(price, 5),
            'is_fallback': True,
            'timestamp': datetime.now().isoformat()
        }
