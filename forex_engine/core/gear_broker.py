# forex_engine/core/gear_broker.py - COMPLETE FIXED VERSION

import math
import logging
from collections import deque
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class GearBroker:
    """
    Each currency pair has its own broker that manages:
    - Z-score calculations (maintaining your existing method)
    - Gear synchronization with dollar engine
    - Entry/exit signals with persistence logic
    - Position management
    """
    
    def __init__(self, pair: str, config: Dict, parent_engine):
        self.pair = pair
        self.config = config
        self.parent_engine = parent_engine
        
        # Gear properties
        self.gear_ratio = config.get('gear_ratio', 1.0)
        self.gear_type = self._determine_gear_type(pair)
        self.gear_health = 100.0
        self.beta = config.get('beta', 1.0)  # ← FIX: Added beta
        
        # Spread history (your existing system)
        self.spread_history = deque(maxlen=config.get('max_history', 60))
        self.z_score_history = deque(maxlen=60)
        
        # EMA smoothing (from your agent_x)
        self.z_score_ema = 0.0
        self.alpha = config.get('alpha', 0.3)
        self.persistence = 0
        
        # Position state
        self.position = 0
        self.entry_price = 0.0
        self.entry_z_score = 0.0
        self.position_size = 0.0
        
        # Signals
        self.signal = 'HOLD'
        self.confidence = 0.0
        self.z_score = 0.0
        self.current_spread = 0.0
        self.mu = 0.0
        self.sigma = 0.0
        self.samples = 0
        
        # Performance
        self.trades = []
        self.pnl = 0.0
        self.win_rate = 0.0
        
        # Thresholds
        self.entry_threshold = config.get('entry_threshold', 2.0)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.emergency_threshold = config.get('emergency_threshold', 3.0)
        
        # Cooldown
        self.cooldown = 0
        self.cooldown_bars = config.get('cooldown_bars', 3)
        
        # Market data
        self.price1 = 0.0
        self.price2 = 0.0
        self.mid_price = 0.0
        
        # Last update tracking
        self.last_update_time = None
        self.update_count = 0
        
        logger.info(f"   ✅ Gear Broker: {pair} (Type: {self.gear_type}, Ratio: {self.gear_ratio})")
    
    def _determine_gear_type(self, pair: str) -> str:
        """
        Determine gear type based on pair relationship to USD.
        
        Returns:
            'DIRECT'  - USD/XXX (moves same as dollar)
            'INVERSE' - XXX/USD (moves opposite to dollar)
            'CROSS'   - Cross currency pairs
        """
        if pair.startswith('USD'):
            return 'DIRECT'
        elif pair.endswith('USD'):
            return 'INVERSE'
        else:
            return 'CROSS'
    
    def calculate_spread(self, price1: float, price2: float, beta: float = None) -> float:
        """Calculate spread between two assets."""
        if beta is None:
            beta = self.beta
        
        if price1 <= 0 or price2 <= 0:
            return 0.0
        return math.log(price1) - beta * math.log(price2)
    
    def update(self, price1: float, price2: float, beta: float = None) -> Dict:
        """
        Update broker state with new prices.
        This combines your existing Z-score logic with gear mechanics.
        """
        if beta is None:
            beta = self.beta
        
        self.price1 = price1
        self.price2 = price2
        self.mid_price = (price1 + price2) / 2
        self.last_update_time = datetime.now()
        self.update_count += 1
        
        # Calculate spread
        spread = self.calculate_spread(price1, price2, beta)
        if spread == 0:
            return {'status': 'NO_DATA', 'pair': self.pair}
        
        # Update spread history
        self.spread_history.append(spread)
        self.current_spread = spread
        
        # Calculate Z-score
        z_result = self._calculate_z_score(list(self.spread_history))
        raw_z = z_result['z_score']
        self.mu = z_result['mu']
        self.sigma = z_result['sigma']
        self.samples = z_result['samples']
        
        # Update Z-score history
        self.z_score_history.append(raw_z)
        self.z_score = raw_z
        
        # Update EMA
        if self.samples == 1:
            self.z_score_ema = raw_z
        else:
            self.z_score_ema = (self.alpha * raw_z) + ((1 - self.alpha) * self.z_score_ema)
        
        # Update persistence
        if abs(self.z_score_ema) >= self.entry_threshold:
            self.persistence += 1
        else:
            self.persistence = 0
        
        # Handle cooldown
        if self.cooldown > 0:
            self.cooldown -= 1
        
        # Get engine prediction
        engine_pred = self.parent_engine.get_gear_prediction(self.pair, self.gear_ratio)
        
        # Generate signal
        signal_result = self._generate_signal(raw_z, engine_pred)
        
        # Update position
        if signal_result['action'] in ['BUY', 'SELL']:
            self.position = 1 if signal_result['action'] == 'BUY' else -1
            self.entry_price = self.mid_price
            self.entry_z_score = raw_z
            self.position_size = self.config.get('position_size', 1.0)
            self.signal = signal_result['action']
            self.confidence = signal_result['confidence']
        elif signal_result['action'] in ['CLOSE', 'EMERGENCY_CLOSE']:
            # Record trade PnL
            if self.position != 0:
                trade_pnl = self._calculate_trade_pnl(self.mid_price)
                self.trades.append({
                    'pair': self.pair,
                    'entry_price': self.entry_price,
                    'exit_price': self.mid_price,
                    'pnl': trade_pnl,
                    'direction': 'BUY' if self.position == 1 else 'SELL',
                    'timestamp': datetime.now().isoformat()
                })
                self.pnl += trade_pnl
                self.win_rate = self._calculate_win_rate()
            
            self.position = 0
            self.cooldown = self.cooldown_bars
            self.signal = 'HOLD'
            self.confidence = 0
        
        return {
            'pair': self.pair,
            'action': signal_result['action'],
            'confidence': signal_result['confidence'],
            'reason': signal_result['reason'],
            'z_score': raw_z,
            'z_score_ema': self.z_score_ema,
            'persistence': self.persistence,
            'position': self.position,
            'spread': spread,
            'mu': self.mu,
            'sigma': self.sigma,
            'samples': self.samples,
            'engine_prediction': engine_pred,
            'gear_health': self.gear_health,
            'cooldown': self.cooldown,
            'entry_price': self.entry_price,
            'entry_z_score': self.entry_z_score,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_z_score(self, spread_history: List[float]) -> Dict:
        """Calculate Z-score."""
        if len(spread_history) < 10:
            return {'z_score': 0.0, 'mu': 0.0, 'sigma': 0.0, 'samples': len(spread_history)}
        
        mu = sum(spread_history) / len(spread_history)
        variance = sum((x - mu) ** 2 for x in spread_history) / len(spread_history)
        sigma = math.sqrt(variance) if variance > 0 else 0.0001
        
        if sigma > 0:
            z_score = (spread_history[-1] - mu) / sigma
        else:
            z_score = 0.0
        
        return {'z_score': z_score, 'mu': mu, 'sigma': sigma, 'samples': len(spread_history)}
    
    def _calculate_trade_pnl(self, exit_price: float) -> float:
        """Calculate PnL for a trade."""
        if self.position == 0 or self.entry_price == 0:
            return 0.0
        
        if self.position == 1:  # BUY
            return exit_price - self.entry_price
        else:  # SELL
            return self.entry_price - exit_price
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trades."""
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        return wins / len(self.trades)
    
    def _generate_signal(self, z_score: float, engine_pred: Dict) -> Dict:
        """
        Generate trading signal based on Z-score and engine prediction.
        """
        # Check engine health first
        if self.parent_engine.engine_health < 50:
            if self.position != 0:
                return {
                    'action': 'EMERGENCY_CLOSE',
                    'confidence': 85,
                    'reason': f'Engine health low ({self.parent_engine.engine_health:.1f}%)'
                }
            return {
                'action': 'HOLD',
                'confidence': 30,
                'reason': f'Engine health low ({self.parent_engine.engine_health:.1f}%)'
            }
        
        # Check cooldown
        if self.cooldown > 0:
            return {
                'action': 'HOLD',
                'confidence': 40,
                'reason': f'Cooldown ({self.cooldown} periods remaining)'
            }
        
        # Check gear health
        if self.gear_health < 60:
            if self.position != 0:
                return {
                    'action': 'CLOSE',
                    'confidence': 75,
                    'reason': f'Gear health low ({self.gear_health:.1f}%)'
                }
            return {
                'action': 'HOLD',
                'confidence': 35,
                'reason': f'Gear health low ({self.gear_health:.1f}%)'
            }
        
        # Adjust thresholds based on engine prediction
        entry_threshold = self.entry_threshold
        exit_threshold = self.exit_threshold
        
        # If engine predicts reversal, be more conservative
        reversal_prob = self.parent_engine.reversal_probability if hasattr(self.parent_engine, 'reversal_probability') else 0
        if reversal_prob > 60:
            entry_threshold *= 1.2  # Need stronger signal
            exit_threshold *= 0.8   # Exit earlier
        
        # Get engine direction
        engine_direction = engine_pred.get('predicted_direction', 'NEUTRAL')
        
        # Convert engine direction to match our signals
        engine_bullish = engine_direction in ['UP', 'FORWARD']
        engine_bearish = engine_direction in ['DOWN', 'BACKWARD']
        
        # Generate signal
        action = 'HOLD'
        confidence = 50
        reason = f'Normal (Z={z_score:.3f}, EMA={self.z_score_ema:.3f})'
        
        # Entry signals
        if self.position == 0:
            # Check persistence (your existing logic)
            if self.persistence >= 2:
                if self.z_score_ema > entry_threshold:
                    # Check if engine supports selling
                    if engine_bearish or engine_direction == 'NEUTRAL':
                        action = 'SELL'
                        confidence = min(90, 70 + (self.z_score_ema - entry_threshold) * 15)
                        reason = f'Overextended + Engine {engine_direction} (Z={z_score:.3f})'
                    else:
                        action = 'HOLD'
                        confidence = 50
                        reason = f'Overextended but Engine {engine_direction} (Z={z_score:.3f})'
                
                elif self.z_score_ema < -entry_threshold:
                    # Check if engine supports buying
                    if engine_bullish or engine_direction == 'NEUTRAL':
                        action = 'BUY'
                        confidence = min(90, 70 + (-self.z_score_ema - entry_threshold) * 15)
                        reason = f'Compressed + Engine {engine_direction} (Z={z_score:.3f})'
                    else:
                        action = 'HOLD'
                        confidence = 50
                        reason = f'Compressed but Engine {engine_direction} (Z={z_score:.3f})'
        
        # Exit signals
        elif self.position != 0:
            # Normal exit
            if abs(z_score) < exit_threshold:
                action = 'CLOSE'
                confidence = 70
                reason = f'Reverted to mean (Z={z_score:.3f})'
            
            # Emergency exit
            elif abs(z_score) > self.emergency_threshold:
                action = 'EMERGENCY_CLOSE'
                confidence = 90
                reason = f'Extreme divergence (Z={z_score:.3f})'
            
            # Engine reversal - exit
            elif reversal_prob > 70 and self.persistence < 2:
                action = 'CLOSE'
                confidence = 75
                reason = f'Engine reversal detected (Prob: {reversal_prob:.0f}%)'
        
        return {
            'action': action,
            'confidence': confidence,
            'reason': reason
        }
    
    def update_gear_health(self, expected_move: float, actual_move: float) -> float:
        """
        Update gear health based on deviation from expected movement.
        """
        if expected_move == 0:
            return self.gear_health
        
        deviation = (actual_move - expected_move) / expected_move if expected_move != 0 else 0
        deviation_pct = abs(deviation)
        
        if deviation_pct > 0.5:  # 50% deviation
            self.gear_health = max(0, self.gear_health - 20)
            logger.warning(f"⚠️ Gear {self.pair} slippage: {deviation_pct:.1%}")
        elif deviation_pct > 0.2:  # 20% deviation
            self.gear_health = max(0, self.gear_health - 10)
        else:
            self.gear_health = min(100, self.gear_health + 2)
        
        # Detect disconnection
        if self.gear_health < 40:
            logger.error(f"❌ Gear {self.pair} disconnected! Health: {self.gear_health:.1f}%")
        
        return self.gear_health
    
    def reset_position(self):
        """Reset position manually."""
        self.position = 0
        self.entry_price = 0.0
        self.entry_z_score = 0.0
        self.position_size = 0.0
        self.signal = 'HOLD'
        self.confidence = 0
        self.cooldown = self.cooldown_bars
        logger.info(f"🔄 {self.pair} position reset")
    
    def get_status(self) -> Dict:
        """Get current broker status."""
        return {
            'pair': self.pair,
            'gear_type': self.gear_type,
            'gear_ratio': self.gear_ratio,
            'gear_health': self.gear_health,
            'position': self.position,
            'position_size': self.position_size,
            'z_score': self.z_score,
            'z_score_ema': self.z_score_ema,
            'persistence': self.persistence,
            'mu': self.mu,
            'sigma': self.sigma,
            'samples': self.samples,
            'entry_price': self.entry_price,
            'entry_z_score': self.entry_z_score,
            'cooldown': self.cooldown,
            'current_spread': self.current_spread,
            'price1': self.price1,
            'price2': self.price2,
            'mid_price': self.mid_price,
            'pnl': self.pnl,
            'win_rate': self.win_rate,
            'trades': len(self.trades),
            'update_count': self.update_count,
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
        }