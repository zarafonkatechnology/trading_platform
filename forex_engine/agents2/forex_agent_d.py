# agents2/forex_agent_d.py - Fixed Version

import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class AgentDVolatility:
    """
    Agent_D - Volatility & Bollinger Band Squeeze Specialist
    Detects narrowing bands → signals breakout preparation
    """
    
    def __init__(self, name="Forex_D", timeframe="M15"):  # ← FIXED: Default timeframe
        self.name = name
        self.timeframe = timeframe  # ← FIXED: Assign timeframe
        self.agent_type = "Volatility Specialist"
        
        # State
        self.squeeze_detected = False
        self.squeeze_intensity = 0.0
        self.band_width_history = deque(maxlen=50)
        self.breakout_ready = False
        self.breakout_direction = 'PENDING'
        
        # Price history
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        
        # Stats
        self.stats = {
            'squeezes_detected': 0,
            'breakouts_predicted': 0,
            'buy_signals': 0,
            'sell_signals': 0
        }
        
        logger.info(f"   ✅ {self.name} initialized")
        logger.info(f"      📊 Timeframe: {self.timeframe}")
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Main analysis method"""
        symbol = signal_data.get('symbol', 'EURUSD')
        current_price = signal_data.get('price', 0.0)
        rsi = signal_data.get('rsi', 50.0)
        
        if current_price <= 0:
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': 'No price data',
                'symbol': symbol,
                'agent': self.name,
                'timestamp': datetime.now().isoformat()
            }
        
        # Update price history
        self.price_history[symbol].append(current_price)
        prices = list(self.price_history[symbol])
        
        if len(prices) < 20:
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': f'Insufficient data ({len(prices)}/20)',
                'symbol': symbol,
                'agent': self.name,
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate Bollinger Bands
        upper_band, lower_band, sma, band_width = self._calculate_bollinger_bands(prices)
        
        if upper_band is None:
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': 'Cannot calculate bands',
                'symbol': symbol,
                'agent': self.name,
                'timestamp': datetime.now().isoformat()
            }
        
        # Track band width
        self.band_width_history.append(band_width)
        
        # Detect squeeze
        is_squeeze, squeeze_intensity = self._detect_squeeze(band_width)
        self.squeeze_detected = is_squeeze
        self.squeeze_intensity = squeeze_intensity
        
        # Generate signal
        if is_squeeze:
            self.breakout_ready = True
            breakout_direction = self._predict_breakout_direction(current_price, sma, upper_band, lower_band)
            self.stats['squeezes_detected'] += 1
            
            return {
                'agent': self.name,
                'symbol': symbol,
                'vote': 'WATCH',
                'confidence': 75 + (squeeze_intensity * 20),
                'reasoning': f"🔄 SQUEEZE DETECTED! Band width={band_width:.2f}% - {breakout_direction}",
                'squeeze_detected': True,
                'squeeze_intensity': squeeze_intensity,
                'band_width': band_width,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'middle_band': sma,
                'breakout_ready': True,
                'breakout_direction': breakout_direction,
                'current_price': current_price,
                'rsi': rsi,
                'timestamp': datetime.now().isoformat()
            }
        
        # Oversold/Overbought signals
        if rsi < 25 and current_price < lower_band:
            self.stats['buy_signals'] += 1
            return {
                'agent': self.name,
                'symbol': symbol,
                'vote': 'BUY',
                'confidence': 75,
                'reasoning': f"🟢 EXTREME OVERSOLD (RSI={rsi:.1f}) + Price below lower band",
                'squeeze_detected': False,
                'band_width': band_width,
                'current_price': current_price,
                'rsi': rsi,
                'timestamp': datetime.now().isoformat()
            }
        
        if rsi > 75 and current_price > upper_band:
            self.stats['sell_signals'] += 1
            return {
                'agent': self.name,
                'symbol': symbol,
                'vote': 'SELL',
                'confidence': 75,
                'reasoning': f"🔴 EXTREME OVERBOUGHT (RSI={rsi:.1f}) + Price above upper band",
                'squeeze_detected': False,
                'band_width': band_width,
                'current_price': current_price,
                'rsi': rsi,
                'timestamp': datetime.now().isoformat()
            }
        
        # Normal market
        return {
            'agent': self.name,
            'symbol': symbol,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': f"Normal volatility (Band width: {band_width:.2f}%, RSI: {rsi:.1f})",
            'squeeze_detected': False,
            'band_width': band_width,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'middle_band': sma,
            'breakout_ready': False,
            'current_price': current_price,
            'rsi': rsi,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None, None
        
        recent_prices = prices[-period:]
        sma = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        band_width = ((upper_band - lower_band) / sma) * 100
        
        return upper_band, lower_band, sma, band_width
    
    def _detect_squeeze(self, band_width: float, squeeze_threshold: float = 0.5) -> Tuple[bool, float]:
        """Detect Bollinger Band squeeze"""
        if len(self.band_width_history) < 20:
            return False, 0.0
        
        avg_width = np.mean(list(self.band_width_history)[-20:])
        width_ratio = band_width / avg_width if avg_width > 0 else 1.0
        
        is_squeeze = width_ratio < squeeze_threshold
        squeeze_intensity = min(1.0, (1 - (width_ratio / squeeze_threshold)) if is_squeeze else 0.0)
        
        return is_squeeze, squeeze_intensity
    
    def _predict_breakout_direction(self, price: float, sma: float, upper: float, lower: float) -> str:
        """Predict breakout direction"""
        if price > sma:
            return 'BULLISH' if price < upper else 'BULLISH_BREAKOUT'
        elif price < sma:
            return 'BEARISH' if price > lower else 'BEARISH_BREAKOUT'
        else:
            return 'NEUTRAL'