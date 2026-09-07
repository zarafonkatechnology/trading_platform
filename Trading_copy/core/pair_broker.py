# core/pair_broker.py
"""
Specialized Broker for each currency pair.
Each pair has its own broker with pair-specific parameters.
"""

import logging
import numpy as np
from typing import Dict, Optional
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class PairBroker:
    """
    Specialized broker for a single currency pair.
    Each pair has unique parameters, thresholds, and logic.
    """
    
    def __init__(self, pair: str, config: Dict, engine):
        self.pair = pair
        self.config = config
        self.engine = engine
        
        # Pair-specific parameters
        self.beta = config.get('beta', 1.0)
        self.gear_ratio = config.get('gear_ratio', 1.0)
        self.gear_type = config.get('gear_type', 'INVERSE')  # DIRECT, INVERSE, CROSS
        self.entry_threshold = config.get('entry_threshold', 2.0)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        
        # History
        self.spread_history = deque(maxlen=60)
        self.price_history = deque(maxlen=100)
        
        # State
        self.z_score = 0.0
        self.z_score_ema = 0.0
        self.persistence = 0
        self.signal = 'HOLD'
        self.confidence = 0
        
        # Performance
        self.performance = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_confidence': 0.0,
            'total_pnl': 0.0
        }
        
        # ===== FIX: Use self.gear_type and self.gear_ratio =====
        logger.info(f"   ✅ PairBroker: {pair} (Type: {self.gear_type}, Ratio: {self.gear_ratio})")
    
    def analyze(self, market_data: Dict) -> Dict:
        """Analyze pair and generate initial signal."""
        price = market_data.get(self.pair, 0)
        if price <= 0:
            return {'signal': 'HOLD', 'confidence': 0, 'reason': 'No price'}
        
        self.price_history.append(price)
        spread = self._calculate_spread(price, market_data)
        if spread > 0:
            self.spread_history.append(spread)
        
        z_result = self._calculate_z_score()
        self.z_score = z_result['z_score']
        
        if len(self.spread_history) == 1:
            self.z_score_ema = self.z_score
        else:
            self.z_score_ema = (0.3 * self.z_score) + (0.7 * self.z_score_ema)
        
        if abs(self.z_score_ema) >= self.entry_threshold:
            self.persistence += 1
        else:
            self.persistence = 0
        
        signal_result = self._generate_signal()
        
        return {
            'pair': self.pair,
            'signal': signal_result['signal'],
            'confidence': signal_result['confidence'],
            'reason': signal_result['reason'],
            'z_score': self.z_score,
            'z_score_ema': self.z_score_ema,
            'persistence': self.persistence,
            'price': price,
            'spread': self.spread_history[-1] if self.spread_history else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_spread(self, price: float, market_data: Dict) -> float:
        """Calculate spread for this pair."""
        # For EUR/USD type (base/quote)
        if '/' in self.pair:
            base, quote = self.pair.split('/')
        else:
            # For pairs like EURUSD, split at 3 characters
            base = self.pair[:3]
            quote = self.pair[3:]
        
        quote_price = market_data.get(quote, 1.0)
        if quote_price > 0:
            return price / quote_price
        return 0
    
    def _calculate_z_score(self) -> Dict:
        """Calculate Z-score from spread history."""
        if len(self.spread_history) < 10:
            return {'z_score': 0.0, 'mu': 0.0, 'sigma': 0.0, 'samples': len(self.spread_history)}
        
        values = list(self.spread_history)
        mu = sum(values) / len(values)
        variance = sum((x - mu) ** 2 for x in values) / len(values)
        sigma = np.sqrt(variance) if variance > 0 else 0.0001
        
        if sigma > 0:
            z_score = (values[-1] - mu) / sigma
        else:
            z_score = 0.0
        
        return {'z_score': z_score, 'mu': mu, 'sigma': sigma, 'samples': len(values)}
    
    def _generate_signal(self) -> Dict:
        """Generate signal based on Z-score and engine alignment."""
        if self.persistence < 2:
            return {'signal': 'HOLD', 'confidence': 50, 'reason': 'No persistence'}
        
        try:
            engine_pred = self.engine.get_gear_prediction(self.pair, self.gear_ratio)
            engine_direction = engine_pred.get('predicted_direction', 'SIDEWAYS')
        except:
            engine_direction = 'SIDEWAYS'
        
        if self.gear_type == 'INVERSE':
            # Inverse pairs (EUR/USD): move opposite to USD
            if self.z_score_ema > self.entry_threshold:
                # Overextended → SELL
                if engine_direction in ['DOWN', 'SIDEWAYS']:
                    confidence = min(85, 70 + (self.z_score_ema - self.entry_threshold) * 15)
                    return {'signal': 'SELL', 'confidence': confidence, 'reason': f'Engine confirms SELL (Z={self.z_score_ema:.2f})'}
                else:
                    return {'signal': 'HOLD', 'confidence': 50, 'reason': 'Engine misaligned'}
            
            elif self.z_score_ema < -self.entry_threshold:
                # Compressed → BUY
                if engine_direction in ['UP', 'SIDEWAYS']:
                    confidence = min(85, 70 + (-self.z_score_ema - self.entry_threshold) * 15)
                    return {'signal': 'BUY', 'confidence': confidence, 'reason': f'Engine confirms BUY (Z={self.z_score_ema:.2f})'}
                else:
                    return {'signal': 'HOLD', 'confidence': 50, 'reason': 'Engine misaligned'}
        
        elif self.gear_type == 'DIRECT':
            # Direct pairs (USD/JPY): move same as USD
            if self.z_score_ema > self.entry_threshold and engine_direction in ['UP', 'SIDEWAYS']:
                confidence = min(85, 70 + (self.z_score_ema - self.entry_threshold) * 15)
                return {'signal': 'BUY', 'confidence': confidence, 'reason': f'Engine confirms BUY (Z={self.z_score_ema:.2f})'}
            elif self.z_score_ema < -self.entry_threshold and engine_direction in ['DOWN', 'SIDEWAYS']:
                confidence = min(85, 70 + (-self.z_score_ema - self.entry_threshold) * 15)
                return {'signal': 'SELL', 'confidence': confidence, 'reason': f'Engine confirms SELL (Z={self.z_score_ema:.2f})'}
        
        elif self.gear_type == 'CROSS':
            # Cross pairs (EUR/GBP): less dependent on USD
            if self.z_score_ema > self.entry_threshold * 0.8:
                confidence = min(80, 65 + (self.z_score_ema - self.entry_threshold * 0.8) * 15)
                return {'signal': 'SELL', 'confidence': confidence, 'reason': f'Cross overextended (Z={self.z_score_ema:.2f})'}
            elif self.z_score_ema < -self.entry_threshold * 0.8:
                confidence = min(80, 65 + (-self.z_score_ema - self.entry_threshold * 0.8) * 15)
                return {'signal': 'BUY', 'confidence': confidence, 'reason': f'Cross compressed (Z={self.z_score_ema:.2f})'}
        
        return {'signal': 'HOLD', 'confidence': 50, 'reason': 'No clear signal'}
    
    def update_performance(self, was_correct: bool, pnl: float):
        """Update broker performance."""
        self.performance['trades'] += 1
        if was_correct:
            self.performance['wins'] += 1
        else:
            self.performance['losses'] += 1
        
        self.performance['win_rate'] = self.performance['wins'] / self.performance['trades'] if self.performance['trades'] > 0 else 0
        self.performance['total_pnl'] += pnl
        self.performance['avg_confidence'] = (self.performance['avg_confidence'] * (self.performance['trades'] - 1) + self.confidence) / self.performance['trades'] if self.performance['trades'] > 0 else 0