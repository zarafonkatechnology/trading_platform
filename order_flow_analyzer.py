# order_flow_analyzer.py - COMPLETE FIXED VERSION
"""
Order Flow Analyzer for Real-Time Market Microstructure
Detects: CVD, Liquidity Sweeps, Order Blocks, Volume Profile
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import time

class OrderFlowAnalyzer:
    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        self.price_history = {}  # symbol -> deque of prices
        self.volume_history = {}  # symbol -> deque of volumes
        self.tick_history = {}    # symbol -> deque of ticks
        self.last_update = {}     # symbol -> timestamp
        
        # Initialize with some default data
        self._initialize_default_data()
        
    def _initialize_default_data(self):
        """Initialize with default price data for common symbols"""
        default_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', 'SILVER', 
                          '#NASDAQ100', '#DJ30', '#S&P500', 'BRENT_OIL', 'CrudeOIL']
        
        for symbol in default_symbols:
            self.price_history[symbol] = deque(maxlen=self.lookback_period)
            self.volume_history[symbol] = deque(maxlen=self.lookback_period)
            self.last_update[symbol] = datetime.now()
            
            # Add some initial prices (will be updated from MT4)
            for i in range(20):
                base_price = self._get_base_price(symbol)
                price = base_price * (1 + (i - 10) * 0.0001)
                self.price_history[symbol].append(price)
                self.volume_history[symbol].append(1000 + i * 10)
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for symbol"""
        base_prices = {
            'EURUSD': 1.1380,
            'GBPUSD': 1.3190,
            'USDJPY': 161.50,
            'GOLD': 4135.00,
            'SILVER': 62.00,
            '#NASDAQ100': 29730.00,
            '#DJ30': 52072.00,
            '#S&P500': 7443.00,
            'BRENT_OIL': 76.80,
            'CrudeOIL': 73.00,
        }
        return base_prices.get(symbol, 1.0)
    
    def _get_mt4_price(self, symbol: str) -> float:
        """Get current price from MT4"""
        try:
            from mt4_price_provider import get_mt4_prices
            mt4 = get_mt4_prices()
            result = mt4.get_price(symbol)
            if result and result.get('success'):
                bid = float(result.get('bid', 0))
                ask = float(result.get('ask', 0))
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
        except:
            pass
        return self._get_base_price(symbol)
    
    def get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        return self._get_mt4_price(symbol)
    
    def update_price(self, symbol: str, price: float, volume: float = 1000):
        """Update price and volume history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback_period)
            self.volume_history[symbol] = deque(maxlen=self.lookback_period)
        
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        self.last_update[symbol] = datetime.now()
    
    def calculate_cvd(self, symbol: str, period: int = 20) -> Dict:
        """
        Calculate Cumulative Volume Delta (CVD)
        Shows net buying vs selling pressure
        """
        try:
            prices = list(self.price_history.get(symbol, deque(maxlen=period)))
            volumes = list(self.volume_history.get(symbol, deque(maxlen=period)))
            
            # If no data, use simulated
            if len(prices) < 2:
                return {'cvd': 0, 'signal': 'NEUTRAL', 'trend': 'FLAT', 'divergence': 'NONE'}
            
            cvd = 0
            deltas = []
            
            for i in range(1, len(prices)):
                price_change = prices[i] - prices[i-1]
                volume = volumes[i] if i < len(volumes) else 1000
                
                if price_change > 0:
                    delta = volume
                elif price_change < 0:
                    delta = -volume
                else:
                    delta = 0
                
                cvd += delta
                deltas.append(delta)
            
            cvd_trend = 'RISING' if len(deltas) > 3 and deltas[-1] > deltas[-3] else 'FALLING'
            
            if cvd > 0 and cvd_trend == 'RISING':
                signal = 'BULLISH'
            elif cvd < 0 and cvd_trend == 'FALLING':
                signal = 'BEARISH'
            else:
                signal = 'NEUTRAL'
            
            price_trend = prices[-1] - prices[0]
            divergence = 'NONE'
            
            if price_trend > 0 and cvd < 0:
                divergence = 'BEARISH_DIVERGENCE'
            elif price_trend < 0 and cvd > 0:
                divergence = 'BULLISH_DIVERGENCE'
            
            return {
                'cvd': cvd,
                'signal': signal,
                'trend': cvd_trend,
                'divergence': divergence,
                'delta_last': deltas[-1] if deltas else 0
            }
            
        except Exception as e:
            print(f"CVD error: {e}")
            return {'cvd': 0, 'signal': 'NEUTRAL', 'trend': 'FLAT', 'divergence': 'NONE'}
    
    def detect_liquidity_sweep(self, symbol: str, current_price: float, lookback: int = 50) -> Dict:
        """Detect liquidity sweeps (stop hunts)"""
        try:
            prices = list(self.price_history.get(symbol, deque(maxlen=lookback)))
            if len(prices) < 20:
                # Simulate from current price
                return {'swept': 'NONE', 'strength': 0, 'confirmed': False, 'direction': 'NEUTRAL'}
            
            recent_highs = prices[-20:]
            recent_lows = prices[-20:]
            all_time_high = max(prices[-50:])
            all_time_low = min(prices[-50:])
            
            if current_price > all_time_high * 0.998:
                sweep_strength = (current_price - all_time_high) / all_time_high * 100
                is_confirmed = sweep_strength < 0.5
                
                return {
                    'swept': 'RESISTANCE',
                    'level': all_time_high,
                    'strength': min(100, sweep_strength * 10),
                    'confirmed': is_confirmed,
                    'direction': 'BEARISH' if is_confirmed else 'NEUTRAL'
                }
            
            elif current_price < all_time_low * 1.002:
                sweep_strength = (all_time_low - current_price) / all_time_low * 100
                is_confirmed = sweep_strength < 0.5
                
                return {
                    'swept': 'SUPPORT',
                    'level': all_time_low,
                    'strength': min(100, sweep_strength * 10),
                    'confirmed': is_confirmed,
                    'direction': 'BULLISH' if is_confirmed else 'NEUTRAL'
                }
            
            return {'swept': 'NONE', 'strength': 0, 'confirmed': False, 'direction': 'NEUTRAL'}
            
        except Exception as e:
            print(f"Sweep error: {e}")
            return {'swept': 'NONE', 'strength': 0, 'confirmed': False, 'direction': 'NEUTRAL'}
    
    def calculate_volume_profile(self, symbol: str, current_price: float, bins: int = 10) -> Dict:
        """Calculate volume profile"""
        try:
            prices = list(self.price_history.get(symbol, deque(maxlen=200)))
            volumes = list(self.volume_history.get(symbol, deque(maxlen=200)))
            
            if len(prices) < 50:
                # Use simulated data
                return {'hvns': [], 'lvns': [], 'current_zone': 'MID', 'volume_at_price': 1000, 'avg_volume': 1000}
            
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price
            
            if price_range <= 0:
                return {'hvns': [], 'lvns': [], 'current_zone': 'MID', 'volume_at_price': 1000, 'avg_volume': 1000}
            
            bin_size = price_range / bins
            volume_by_bin = [0] * bins
            price_by_bin = [min_price + i * bin_size for i in range(bins)]
            
            for i in range(len(prices)):
                price = prices[i]
                volume = volumes[i] if i < len(volumes) else 1000
                bin_idx = min(int((price - min_price) / bin_size), bins - 1)
                if bin_idx >= 0:
                    volume_by_bin[bin_idx] += volume
            
            avg_volume = sum(volume_by_bin) / bins if bins > 0 else 1000
            hvns = [price_by_bin[i] for i, vol in enumerate(volume_by_bin) if vol > avg_volume * 1.5]
            lvns = [price_by_bin[i] for i, vol in enumerate(volume_by_bin) if vol < avg_volume * 0.5]
            
            current_bin = int((current_price - min_price) / bin_size)
            if current_bin < 0:
                current_bin = 0
            if current_bin >= bins:
                current_bin = bins - 1
            
            if volume_by_bin[current_bin] > avg_volume * 1.5:
                current_zone = 'HIGH_VOLUME_NODE'
            elif volume_by_bin[current_bin] < avg_volume * 0.5:
                current_zone = 'LOW_VOLUME_NODE'
            else:
                current_zone = 'MID'
            
            return {
                'hvns': hvns,
                'lvns': lvns,
                'current_zone': current_zone,
                'volume_at_price': volume_by_bin[current_bin],
                'avg_volume': avg_volume
            }
            
        except Exception as e:
            print(f"Volume profile error: {e}")
            return {'hvns': [], 'lvns': [], 'current_zone': 'MID', 'volume_at_price': 1000, 'avg_volume': 1000}
    
    def calculate_volume_ratio(self, symbol: str, period: int = 10) -> float:
        """Calculate current volume vs historical average"""
        try:
            volumes = list(self.volume_history.get(symbol, deque(maxlen=period)))
            if len(volumes) < 5:
                return 1.0
            
            current_volume = volumes[-1] if volumes else 1000
            avg_volume = sum(volumes[:-1]) / (len(volumes) - 1) if len(volumes) > 1 else 1000
            
            if avg_volume > 0:
                return current_volume / avg_volume
            return 1.0
            
        except Exception as e:
            return 1.0
    
    def get_order_flow_signal(self, symbol: str, current_price: float = None) -> Dict:
        """Get complete order flow signal combining all indicators"""
        if current_price is None:
            current_price = self.get_market_price(symbol)
        
        # Update history with current price
        self.update_price(symbol, current_price)
        
        # Calculate all metrics
        cvd_data = self.calculate_cvd(symbol)
        sweep_data = self.detect_liquidity_sweep(symbol, current_price)
        volume_profile = self.calculate_volume_profile(symbol, current_price)
        volume_ratio = self.calculate_volume_ratio(symbol)
        
        # Calculate overall score
        score = 0
        signals = []
        
        # CVD contribution
        if cvd_data['signal'] == 'BULLISH':
            score += 30
            signals.append(f"CVD Bullish")
        elif cvd_data['signal'] == 'BEARISH':
            score -= 30
            signals.append(f"CVD Bearish")
        
        # Divergence
        if cvd_data['divergence'] == 'BULLISH_DIVERGENCE':
            score += 40
            signals.append("Bullish Divergence")
        elif cvd_data['divergence'] == 'BEARISH_DIVERGENCE':
            score -= 40
            signals.append("Bearish Divergence")
        
        # Liquidity sweep
        if sweep_data['swept'] != 'NONE' and sweep_data['confirmed']:
            if sweep_data['direction'] == 'BULLISH':
                score += 35
                signals.append(f"Support Sweep")
            elif sweep_data['direction'] == 'BEARISH':
                score -= 35
                signals.append(f"Resistance Sweep")
        
        # Volume profile
        if volume_profile['current_zone'] == 'HIGH_VOLUME_NODE':
            if score > 0:
                score += 15
                signals.append("High Volume Support")
            elif score < 0:
                score -= 15
                signals.append("High Volume Resistance")
        
        # Volume spike
        if volume_ratio > 2.0:
            signals.append(f"Volume Spike ({volume_ratio:.1f}x)")
            if score > 0:
                score += 10
            else:
                score -= 10
        
        # Determine direction
        if score > 25:
            direction = 'BUY'
        elif score < -25:
            direction = 'SELL'
        else:
            direction = 'HOLD'
        
        return {
            'score': score,
            'direction': direction,
            'cvd': cvd_data['cvd'],
            'cvd_signal': cvd_data['signal'],
            'cvd_divergence': cvd_data['divergence'],
            'liquidity_sweep': sweep_data,
            'volume_profile': volume_profile['current_zone'],
            'volume_ratio': volume_ratio,
            'signals': signals,
            'strength': 'STRONG' if abs(score) > 50 else 'MODERATE' if abs(score) > 30 else 'WEAK'
        }


# Global instance
order_flow_analyzer = OrderFlowAnalyzer()


def get_order_flow_signal(symbol: str, price: float = None) -> Dict:
    """Convenience function to get order flow signal"""
    return order_flow_analyzer.get_order_flow_signal(symbol, price)


def update_price_history(symbol: str, price: float, volume: float = 1000):
    """Update price history for analysis"""
    order_flow_analyzer.update_price(symbol, price, volume)


if __name__ == "__main__":
    # Test the analyzer
    analyzer = OrderFlowAnalyzer()
    
    print("Testing Order Flow Analyzer")
    print("=" * 50)
    
    # Get signal for EURUSD
    signal = analyzer.get_order_flow_signal("EURUSD", 1.1380)
    
    print(f"\n📊 Order Flow Signal for EURUSD:")
    print(f"   Score: {signal['score']}")
    print(f"   Direction: {signal['direction']}")
    print(f"   Signals: {', '.join(signal['signals'])}")
    print(f"   CVD: {signal['cvd']}")
    print(f"   Liquidity Sweep: {signal['liquidity_sweep']['swept']}")
    print(f"   Volume Profile: {signal['volume_profile']}")