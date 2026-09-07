"""
Agent D: Volatility Specialist - Bollinger Band Squeeze Detection
- Detects narrowing bands (squeeze) → signals breakout preparation
- Calculates band width percentage
- Alerts supervisor for BreakoutScalp strategy
- Enhanced with Velocity Filter + Adaptive Threshold
"""

import logging
import numpy as np
import random
from typing import Dict, List, Optional, Tuple
from collections import deque

# Try imports with fallbacks
try:
    from backend.agents.base_agent import BaseAgent
except ImportError:
    try:
        from agents.base_agent import BaseAgent
    except ImportError:
        # Fallback BaseAgent
        class BaseAgent:
            def __init__(self, name="BaseAgent", agent_type="General", specialization="General"):
                self.name = name
                self.agent_type = agent_type
                self.specialization = specialization
                self.xp_points = 0
                self.token_balance = 0
                self.trust_weight = 1.0
                self.total_votes = 0
                self.correct_votes = 0
                self.vote_accuracy = 0.0

logger = logging.getLogger(__name__)


class VelocityFilter:
    """Prevents premature breakout entries when momentum is still building."""
    
    def __init__(self, window: int = 5):
        self.window = window
        self.price_history = deque(maxlen=window + 1)
        self.velocity_history = deque(maxlen=window)
    
    def update(self, price: float) -> Dict:
        """Update filter with new price."""
        self.price_history.append(price)
        
        if len(self.price_history) < 3:
            return {
                'velocity': 0.0,
                'momentum': 'STABLE',
                'is_accelerating': False,
                'can_enter': False,
                'acceleration': 0.0
            }
        
        prices = list(self.price_history)
        velocities = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        current_velocity = velocities[-1]
        self.velocity_history.append(current_velocity)
        
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[-2]
        else:
            acceleration = 0.0
        
        if current_velocity > 0.1:
            momentum = 'RISING'
        elif current_velocity < -0.1:
            momentum = 'FALLING'
        else:
            momentum = 'STABLE'
        
        is_accelerating = False
        if len(velocities) >= 2:
            if current_velocity > 0 and acceleration > 0:
                is_accelerating = True
            if current_velocity < 0 and acceleration < 0:
                is_accelerating = True
        
        can_enter = abs(current_velocity) < 0.05 or is_accelerating
        
        return {
            'velocity': current_velocity,
            'momentum': momentum,
            'is_accelerating': is_accelerating,
            'can_enter': can_enter,
            'acceleration': acceleration
        }


class AgentDVolatility(BaseAgent):
    """
    Volatility Specialist - Bollinger Band Squeeze & Breakout Detection
    Enhanced with Velocity Filter + Adaptive Threshold.
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_D",
            agent_type="Volatility",
            specialization="Bollinger Band Squeeze & Breakout Detection"
        )
        
        # ===== STATE =====
        self.squeeze_detected = False
        self.squeeze_intensity = 0.0
        self.band_width_history = []
        self.breakout_ready = False
        self.breakout_direction = 'PENDING'
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_squeeze_threshold = 0.5
        self.current_squeeze_threshold = 0.5
        self.volatility_regime = 'NORMAL'
        
        # ===== PRICE CACHE =====
        self.last_price = 0.0
        self.last_bands = {}
        
        logger.info(f"   ✅ {self.name} (Volatility Specialist) initialized")
        logger.info(f"      📊 Base Squeeze Threshold: 0.5")
        logger.info(f"      📊 Velocity Filter: Active (breakout confirmation)")
        logger.info(f"      📊 Adaptive Threshold: Active")
    
    # ===== FIX: ADD THE MISSING METHOD =====
    def _get_adaptive_threshold(self, volatility: float) -> float:
        """
        Calculate adaptive squeeze threshold based on volatility regime.
        
        Higher volatility → higher threshold (need tighter squeeze)
        Lower volatility → lower threshold (easier to detect squeeze)
        """
        if volatility < 0.005:
            self.volatility_regime = 'LOW'
            return 0.4
        elif volatility < 0.015:
            self.volatility_regime = 'NORMAL'
            return 0.5
        elif volatility < 0.03:
            self.volatility_regime = 'HIGH'
            return 0.6
        else:
            self.volatility_regime = 'EXTREME'
            return 0.7
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None, None, None, None
        
        recent_prices = prices[-period:]
        sma = float(np.mean(recent_prices))
        std = float(np.std(recent_prices))
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        band_width = ((upper_band - lower_band) / sma) * 100
        
        return upper_band, lower_band, sma, band_width
    
    def detect_squeeze(self, band_width: float, historical_widths: List[float], 
                       squeeze_threshold: float = 0.5) -> Tuple[bool, float]:
        """Detect Bollinger Band Squeeze."""
        if len(historical_widths) < 20:
            return False, 0.0
        
        avg_width = float(np.mean(historical_widths[-20:]))
        if avg_width <= 0:
            return False, 0.0
        
        width_ratio = band_width / avg_width
        is_squeeze = width_ratio < squeeze_threshold
        
        if is_squeeze:
            squeeze_intensity = min(1.0, (1 - (width_ratio / squeeze_threshold)) * 1.5)
        else:
            squeeze_intensity = 0.0
        
        return is_squeeze, squeeze_intensity
    
    def predict(self, signal_data: Dict, market_features: Dict) -> Tuple[str, float]:
        """Analyze volatility and detect Bollinger Band squeezes."""
        try:
            asset = signal_data.get('asset_type', 'UNKNOWN')
            rsi = market_features.get('rsi_14', 50)
            candles = market_features.get('candles', [])
            prices = [c['close'] for c in candles] if candles else []
            
            if len(prices) < 20:
                return 'HOLD', 50
            
            current_price = prices[-1]
            self.last_price = current_price
            
            upper_band, lower_band, sma, band_width = self.calculate_bollinger_bands(prices)
            
            if upper_band is None:
                return 'HOLD', 50
            
            self.band_width_history.append(band_width)
            if len(self.band_width_history) > 50:
                self.band_width_history = self.band_width_history[-50:]
            
            volatility = np.std(prices[-20:]) / np.mean(prices[-20:]) if len(prices) >= 20 else 0.01
            
            self.current_squeeze_threshold = self._get_adaptive_threshold(volatility)
            
            is_squeeze, squeeze_intensity = self.detect_squeeze(
                band_width, 
                self.band_width_history,
                self.current_squeeze_threshold
            )
            
            self.squeeze_detected = is_squeeze
            self.squeeze_intensity = squeeze_intensity
            
            velocity_result = self.velocity_filter.update(current_price)
            
            market_features['bollinger_upper'] = upper_band
            market_features['bollinger_lower'] = lower_band
            market_features['bollinger_middle'] = sma
            market_features['band_width'] = band_width
            market_features['is_squeeze'] = is_squeeze
            market_features['squeeze_intensity'] = squeeze_intensity
            market_features['volatility_regime'] = self.volatility_regime
            market_features['adaptive_threshold'] = self.current_squeeze_threshold
            market_features['velocity'] = velocity_result
            
            action = 'HOLD'
            confidence = 50
            
            # ===== SQUEEZE DETECTED =====
            if is_squeeze:
                self.breakout_ready = True
                
                if current_price > sma:
                    self.breakout_direction = 'BUY'
                elif current_price < sma:
                    self.breakout_direction = 'SELL'
                else:
                    self.breakout_direction = 'PENDING'
                
                market_features['breakout_ready'] = True
                market_features['breakout_direction'] = self.breakout_direction
                
                confidence = 70 + (squeeze_intensity * 20)
                
                if velocity_result['is_accelerating']:
                    confidence = min(95, confidence + 10)
                    market_features['breakout_confirmed'] = True
                
                return 'WATCH', min(95, confidence)
            
            # ===== RANGING MARKET =====
            elif 45 <= rsi <= 55:
                action = 'HOLD'
                confidence = 50
            
            # ===== TRENDING MARKET =====
            elif rsi < 30 and current_price > lower_band:
                action = 'HOLD'
                confidence = 55
            elif rsi > 70 and current_price < upper_band:
                action = 'HOLD'
                confidence = 55
            elif rsi < 25 and current_price < lower_band:
                action = 'HOLD'
                confidence = 60
            elif rsi > 75 and current_price > upper_band:
                action = 'HOLD'
                confidence = 60
            
            # ===== BREAKOUT CONFIRMATION =====
            if not is_squeeze and self.breakout_ready:
                if current_price > upper_band * 1.005:
                    action = 'BUY'
                    confidence = 75
                    self.breakout_ready = False
                elif current_price < lower_band * 0.995:
                    action = 'SELL'
                    confidence = 75
                    self.breakout_ready = False
            
            return action, min(95, confidence)
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return 'HOLD', 50
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Full analysis method returning dict."""
        market_features = {}
        action, confidence = self.predict(signal_data, market_features)
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': action,
            'confidence': confidence,
            'reasoning': f"Volatility: {self.volatility_regime}, Squeeze: {self.squeeze_detected}",
            'squeeze_detected': self.squeeze_detected,
            'squeeze_intensity': self.squeeze_intensity,
            'band_width': self.band_width_history[-1] if self.band_width_history else 0,
            'volatility_regime': self.volatility_regime,
            'breakout_ready': self.breakout_ready,
            'breakout_direction': self.breakout_direction,
            'market_features': market_features,
            'timestamp': self._get_timestamp()
        }
    
    def get_breakout_signal(self) -> Optional[Dict]:
        """Called by supervisor to get breakout direction after squeeze."""
        if not self.squeeze_detected:
            return None
        
        return {
            'squeeze_detected': True,
            'intensity': self.squeeze_intensity,
            'direction': self.breakout_direction,
            'band_width': self.band_width_history[-1] if self.band_width_history else 0,
            'confidence': 70 + (self.squeeze_intensity * 20)
        }
    
    def get_squeeze_status(self) -> Dict:
        """Return current squeeze status for supervisor."""
        return {
            'is_squeezing': self.squeeze_detected,
            'band_width': self.band_width_history[-1] if self.band_width_history else 0,
            'intensity': self.squeeze_intensity,
            'volatility_regime': self.volatility_regime,
            'adaptive_threshold': self.current_squeeze_threshold,
            'breakout_ready': self.breakout_ready,
            'breakout_direction': self.breakout_direction
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for volatility breakout probability."""
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above_cloud'] += 1
            elif price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probs['above_cloud'] > 60:
            vote = 'BUY'
            conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_status(self) -> Dict:
        """Get agent status."""
        return {
            'name': self.name,
            'type': self.agent_type,
            'squeeze_detected': self.squeeze_detected,
            'squeeze_intensity': self.squeeze_intensity,
            'band_width': self.band_width_history[-1] if self.band_width_history else 0,
            'volatility_regime': self.volatility_regime,
            'adaptive_threshold': self.current_squeeze_threshold,
            'breakout_ready': self.breakout_ready,
            'breakout_direction': self.breakout_direction,
            'timestamp': self._get_timestamp()
        }