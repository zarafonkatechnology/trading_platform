# agent_d_bbands.py - Bollinger Bands & Volatility Agent

"""
Agent_D - Bollinger Bands & Volatility Specialist
Detects Bollinger Band squeezes and volatility patterns
"""

import numpy as np
from typing import Dict, List, Optional
from collections import deque


class AgentD_BBands:  # ← Different name to avoid conflict
    """Detects Bollinger Band squeezes and volatility patterns"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.name = "Agent_D (BBands)"
        self.agent_type = "Volatility Specialist"
        self.period = period
        self.std_dev = std_dev
        self.price_history = {}
        self.squeeze_detected = {}
        self.band_width_history = {}
        
        print(f"   ✅ {self.name} initialized")
        print(f"      Period: {period}, Std Dev: {std_dev}")
    
    def analyze(self, symbol: str, price: float) -> Dict:
        """Analyze volatility and Bollinger Bands"""
        # Store price history
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=100)
            self.band_width_history[symbol] = deque(maxlen=50)
        
        self.price_history[symbol].append(price)
        prices = list(self.price_history[symbol])
        
        if len(prices) < self.period:
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': f'Building history ({len(prices)}/{self.period})',
                'squeeze_detected': False,
                'band_width': 0,
                'upper_band': 0,
                'lower_band': 0,
                'middle_band': 0
            }
        
        # Calculate Bollinger Bands
        recent = prices[-self.period:]
        sma = np.mean(recent)
        std = np.std(recent)
        
        upper = sma + (std * self.std_dev)
        lower = sma - (std * self.std_dev)
        band_width = ((upper - lower) / sma) * 100
        
        # Track band width history
        self.band_width_history[symbol].append(band_width)
        
        # Detect squeeze
        is_squeeze = False
        squeeze_intensity = 0
        
        if len(self.band_width_history[symbol]) >= 20:
            avg_width = np.mean(list(self.band_width_history[symbol])[-20:])
            width_ratio = band_width / avg_width if avg_width > 0 else 1.0
            
            if width_ratio < 0.5:
                is_squeeze = True
                squeeze_intensity = min(1.0, (1 - width_ratio / 0.5))
        
        self.squeeze_detected[symbol] = is_squeeze
        
        # Generate signal
        if is_squeeze:
            if price > sma:
                direction = 'BUY'
                confidence = min(90, 75 + squeeze_intensity * 20)
                reasoning = f"SQUEEZE! Band width: {band_width:.2f}% - Bullish breakout expected"
                breakout = 'BULLISH'
            else:
                direction = 'SELL'
                confidence = min(90, 75 + squeeze_intensity * 20)
                reasoning = f"SQUEEZE! Band width: {band_width:.2f}% - Bearish breakout expected"
                breakout = 'BEARISH'
            
            return {
                'vote': direction,
                'confidence': confidence,
                'reasoning': reasoning,
                'squeeze_detected': True,
                'squeeze_intensity': round(squeeze_intensity, 2),
                'band_width': round(band_width, 2),
                'upper_band': round(upper, 5),
                'lower_band': round(lower, 5),
                'middle_band': round(sma, 5),
                'breakout_direction': breakout
            }
        
        # Oversold/Overbought
        if price < lower and price < sma * 0.995:
            return {
                'vote': 'BUY',
                'confidence': 70,
                'reasoning': f'Price below lower band ({price:.5f} < {lower:.5f}) - Oversold',
                'squeeze_detected': False,
                'band_width': round(band_width, 2),
                'upper_band': round(upper, 5),
                'lower_band': round(lower, 5),
                'middle_band': round(sma, 5)
            }
        
        if price > upper and price > sma * 1.005:
            return {
                'vote': 'SELL',
                'confidence': 70,
                'reasoning': f'Price above upper band ({price:.5f} > {upper:.5f}) - Overbought',
                'squeeze_detected': False,
                'band_width': round(band_width, 2),
                'upper_band': round(upper, 5),
                'lower_band': round(lower, 5),
                'middle_band': round(sma, 5)
            }
        
        return {
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': f'Normal volatility (Band width: {band_width:.2f}%)',
            'squeeze_detected': False,
            'band_width': round(band_width, 2),
            'upper_band': round(upper, 5),
            'lower_band': round(lower, 5),
            'middle_band': round(sma, 5)
        }
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'name': self.name,
            'type': self.agent_type,
            'period': self.period,
            'std_dev': self.std_dev,
            'symbols_tracked': len(self.price_history),
            'squeezes_detected': sum(1 for v in self.squeeze_detected.values() if v)
        }


# Test
if __name__ == "__main__":
    agent = AgentD_BBands()
    
    # Simulate price data
    price = 1.1000
    for i in range(50):
        import random
        price = price * (1 + (random.random() - 0.48) * 0.001)
        result = agent.analyze('EURUSD', price)
        
        if result.get('squeeze_detected', False):
            print(f"[{i}] {result['vote']} - {result['reasoning']}")