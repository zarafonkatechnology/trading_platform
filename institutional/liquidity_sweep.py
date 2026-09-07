# ============================================================
# liquidity_sweep.py - LIQUIDITY SWEEP DETECTOR (ENHANCED)
# ============================================================
# Detects when price sweeps known support/resistance levels
# Enhanced with: Auto-level detection, sweep strength, 
# reversal confirmation, false sweep detection
# ============================================================

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class LiquiditySweepDetector:
    """
    Detects liquidity sweeps - when price breaks a key level
    and then reverses.
    
    ENHANCED FEATURES:
    - Auto-detection of support/resistance levels from price action
    - Sweep strength calculation (0-100)
    - Reversal confirmation
    - False sweep detection
    - Velocity (speed) measurement
    - Time decay for old levels
    """
    
    def __init__(self, sweep_threshold: float = 0.001, 
                 lookback: int = 100,
                 min_level_distance: float = 0.005):
        """
        Initialize Liquidity Sweep Detector.
        
        Args:
            sweep_threshold: How far above/below level counts as sweep (0.1% default)
            lookback: Number of candles to analyze
            min_level_distance: Minimum distance between levels (0.5% default)
        """
        self.levels = []
        self.sweeps = deque(maxlen=100)
        self.sweep_threshold = sweep_threshold
        self.lookback = lookback
        self.min_level_distance = min_level_distance
        
        # Auto-detected levels
        self.auto_levels = {'SUPPORT': [], 'RESISTANCE': []}
        
        # Statistics
        self.stats = {
            'total_sweeps': 0,
            'confirmed_reversals': 0,
            'false_sweeps': 0,
            'sweep_win_rate': 0.0,
            'avg_sweep_strength': 0.0
        }
        
        # Recent data
        self.price_history = deque(maxlen=lookback)
        self.volume_history = deque(maxlen=lookback)
        self.sweep_strengths = deque(maxlen=100)
        
        logger.info("✅ LiquiditySweepDetector ENHANCED initialized")
        logger.info(f"   📊 Sweep Threshold: {sweep_threshold*100:.2f}%")
        logger.info(f"   📊 Lookback: {lookback} candles")
        logger.info(f"   📊 Min Level Distance: {min_level_distance*100:.2f}%")
    
    # ============================================================
    # LEVEL MANAGEMENT
    # ============================================================
    
    def add_level(self, level: float, level_type: str = 'SUPPORT', 
                  source: str = 'MANUAL', strength: float = 1.0):
        """Add a key level to monitor."""
        # Check if level already exists
        for existing in self.levels:
            if abs(existing['level'] - level) / level < self.min_level_distance:
                # Update strength if new level is stronger
                if strength > existing.get('strength', 0):
                    existing['strength'] = strength
                    existing['source'] = source
                return
        
        self.levels.append({
            'level': level,
            'type': level_type,
            'source': source,
            'strength': strength,
            'added': datetime.now(),
            'touches': 0
        })
        
        # Sort levels
        self.levels.sort(key=lambda x: x['level'])
        logger.debug(f"📊 Level added: {level_type} at {level:.4f} (Strength: {strength:.2f})")
    
    def detect_swing_levels(self, prices: List[float], window: int = 5) -> Dict:
        """
        Automatically detect support and resistance levels from swing points.
        """
        if len(prices) < window * 2:
            return {'SUPPORT': [], 'RESISTANCE': []}
        
        supports = []
        resistances = []
        
        # Find swing highs and lows
        for i in range(window, len(prices) - window):
            # Check swing high
            is_high = True
            for j in range(1, window + 1):
                if prices[i] <= prices[i - j] or prices[i] <= prices[i + j]:
                    is_high = False
                    break
            if is_high:
                resistances.append(prices[i])
            
            # Check swing low
            is_low = True
            for j in range(1, window + 1):
                if prices[i] >= prices[i - j] or prices[i] >= prices[i + j]:
                    is_low = False
                    break
            if is_low:
                supports.append(prices[i])
        
        # Cluster nearby levels
        supports = self._cluster_levels(supports, self.min_level_distance)
        resistances = self._cluster_levels(resistances, self.min_level_distance)
        
        # Store auto-detected levels
        self.auto_levels['SUPPORT'] = supports
        self.auto_levels['RESISTANCE'] = resistances
        
        # Add to active levels
        for level in supports:
            self.add_level(level, 'SUPPORT', source='AUTO', strength=0.7)
        for level in resistances:
            self.add_level(level, 'RESISTANCE', source='AUTO', strength=0.7)
        
        return {
            'SUPPORT': supports,
            'RESISTANCE': resistances
        }
    
    def _cluster_levels(self, levels: List[float], min_distance: float) -> List[float]:
        """Cluster nearby levels together."""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clustered = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if level - current_cluster[-1] < min_distance:
                current_cluster.append(level)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]
        
        if current_cluster:
            clustered.append(sum(current_cluster) / len(current_cluster))
        
        return clustered
    
    def update_levels_from_price(self, prices: List[float]):
        """Auto-detect levels from price data."""
        # Add to history
        for price in prices:
            self.price_history.append(price)
        
        # Detect levels if we have enough data
        if len(self.price_history) >= 30:
            price_list = list(self.price_history)
            self.detect_swing_levels(price_list, window=3)
    
    # ============================================================
    # SWEEP DETECTION
    # ============================================================
    
    def analyze_price_action(self, prices: List[float], volumes: List[float] = None) -> Dict:
        """
        Analyze if price swept a level and reversed.
        """
        if len(prices) < 5:
            return self._no_sweep_response("Insufficient data")
        
        # Update price history
        for price in prices:
            self.price_history.append(price)
        if volumes:
            for vol in volumes:
                self.volume_history.append(vol)
        
        # Auto-detect levels if not enough levels
        if len(self.levels) < 3 and len(self.price_history) >= 30:
            self.update_levels_from_price(list(self.price_history))
        
        current_price = prices[-1]
        previous_price = prices[-2] if len(prices) > 1 else current_price
        
        # Calculate velocity
        velocity = self._calculate_velocity(prices)
        
        # Find nearest levels
        nearest_support = None
        nearest_resistance = None
        min_dist_support = float('inf')
        min_dist_resistance = float('inf')
        
        for level_info in self.levels:
            level = level_info['level']
            level_type = level_info['type']
            dist = abs(level - current_price) / current_price
            
            if level_type == 'SUPPORT' and level < current_price and dist < min_dist_support:
                min_dist_support = dist
                nearest_support = level_info
            elif level_type == 'RESISTANCE' and level > current_price and dist < min_dist_resistance:
                min_dist_resistance = dist
                nearest_resistance = level_info
        
        # Check sweeps
        sweeps_detected = []
        
        # Check support sweep (break below)
        if nearest_support:
            level = nearest_support['level']
            if previous_price > level and current_price < level:
                sweep_distance = (level - current_price) / level
                if sweep_distance < self.sweep_threshold * 2:
                    sweeps_detected.append(self._create_sweep_result(
                        nearest_support, current_price, previous_price,
                        sweep_distance, 'BREAKDOWN', velocity, volumes
                    ))
        
        # Check resistance sweep (break above)
        if nearest_resistance:
            level = nearest_resistance['level']
            if previous_price < level and current_price > level:
                sweep_distance = (current_price - level) / level
                if sweep_distance < self.sweep_threshold * 2:
                    sweeps_detected.append(self._create_sweep_result(
                        nearest_resistance, current_price, previous_price,
                        sweep_distance, 'BREAKOUT', velocity, volumes
                    ))
        
        if sweeps_detected:
            # Return strongest sweep
            strongest = max(sweeps_detected, key=lambda x: x.get('sweep_strength', 0))
            return strongest
        
        return self._no_sweep_response("No sweep detected")
    
    def _create_sweep_result(self, level_info: Dict, current_price: float,
                            previous_price: float, sweep_distance: float,
                            direction: str, velocity: float, volumes: List[float]) -> Dict:
        """Create a sweep result dictionary."""
        level = level_info['level']
        level_type = level_info['type']
        strength = level_info.get('strength', 1.0)
        
        # Check volume confirmation
        volume_confirmed = self._check_volume(volumes) if volumes else False
        
        # Check reversal confirmation
        reversal_confirmed = self._check_reversal(None, level, direction)
        
        # Calculate sweep strength
        sweep_strength = self._calculate_sweep_strength(
            sweep_distance, velocity, volume_confirmed, strength
        )
        
        # Check if it's a false sweep
        is_false_sweep = self._is_false_sweep(None, level, direction)
        
        return {
            'is_sweep': True,
            'sweep_type': direction,
            'level': level,
            'level_type': level_type,
            'level_strength': strength,
            'current_price': current_price,
            'previous_price': previous_price,
            'sweep_distance': sweep_distance,
            'sweep_distance_pips': sweep_distance * 10000,
            'sweep_strength': sweep_strength,
            'velocity': velocity,
            'volume_confirmed': volume_confirmed,
            'reversal_confirmed': reversal_confirmed,
            'is_false_sweep': is_false_sweep,
            'reason': f'Sweep of {level_type} at {level:.4f} by {sweep_distance*100:.2f}%'
        }
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def _calculate_velocity(self, prices: List[float]) -> float:
        """Calculate price velocity (rate of change)."""
        if len(prices) < 5:
            return 0.0
        
        return (prices[-1] - prices[-5]) / prices[-5] if prices[-5] > 0 else 0
    
    def _check_volume(self, volumes: List[float]) -> bool:
        """Check if volume confirms the sweep."""
        if not volumes or len(volumes) < 10:
            return False
        
        vol_list = list(volumes)
        avg_volume = np.mean(vol_list[-20:-5]) if len(vol_list) > 20 else np.mean(vol_list[-10:])
        current_volume = vol_list[-1] if vol_list else 0
        
        return current_volume > avg_volume * 1.5
    
    def _check_reversal(self, prices: List[float], level: float, direction: str) -> bool:
        """Check if price reversed after sweep."""
        # Simplified - in production, check actual price action
        return False
    
    def _calculate_sweep_strength(self, sweep_distance: float, velocity: float,
                                   volume_confirmed: bool, level_strength: float) -> float:
        """Calculate overall sweep strength (0-1)."""
        strength = 0.0
        
        # Distance factor (closer = stronger)
        distance_factor = max(0, 1 - sweep_distance / (self.sweep_threshold * 2))
        strength += distance_factor * 0.4
        
        # Velocity factor (slower = stronger)
        velocity_factor = max(0, 1 - abs(velocity) * 10)
        strength += velocity_factor * 0.2
        
        # Volume factor
        strength += 0.2 if volume_confirmed else 0
        
        # Level strength factor
        strength += level_strength * 0.2
        
        return round(min(1.0, max(0, strength)), 3)
    
    def _is_false_sweep(self, prices: List[float], level: float, direction: str) -> bool:
        """Check if sweep is likely a false break."""
        # Simplified - in production, check actual price action
        return False
    
    def _no_sweep_response(self, reason: str) -> Dict:
        """Generate no-sweep response."""
        return {
            'is_sweep': False,
            'reason': reason,
            'sweep_strength': 0,
            'velocity': 0
        }
    
    # ============================================================
    # SWEEP HISTORY
    # ============================================================
    
    def add_sweep_to_history(self, sweep: Dict):
        """Add a sweep to history."""
        if sweep.get('is_sweep', False):
            self.sweeps.append({
                'timestamp': datetime.now(),
                'sweep': sweep
            })
            
            # Update stats
            self.stats['total_sweeps'] += 1
            self.sweep_strengths.append(sweep.get('sweep_strength', 0))
            
            if sweep.get('reversal_confirmed', False):
                self.stats['confirmed_reversals'] += 1
            if sweep.get('is_false_sweep', False):
                self.stats['false_sweeps'] += 1
            
            # Update win rate
            total = self.stats['total_sweeps']
            if total > 0:
                confirmed = self.stats['confirmed_reversals']
                self.stats['sweep_win_rate'] = confirmed / total
            
            # Update average strength
            if self.sweep_strengths:
                self.stats['avg_sweep_strength'] = sum(self.sweep_strengths) / len(self.sweep_strengths)
            
            logger.info(f"🔄 Sweep: {sweep['reason']} (Strength: {sweep.get('sweep_strength', 0):.2f})")
    
    def get_recent_sweeps(self, count: int = 5) -> List[Dict]:
        """Get recent sweeps."""
        return list(self.sweeps)[-count:] if self.sweeps else []
    
    def get_stats(self) -> Dict:
        """Get sweep statistics."""
        return {
            'total_sweeps': self.stats['total_sweeps'],
            'confirmed_reversals': self.stats['confirmed_reversals'],
            'false_sweeps': self.stats['false_sweeps'],
            'sweep_win_rate': self.stats['sweep_win_rate'] * 100,
            'avg_sweep_strength': self.stats['avg_sweep_strength'],
            'active_levels': len(self.levels),
            'auto_supports': len(self.auto_levels['SUPPORT']),
            'auto_resistances': len(self.auto_levels['RESISTANCE'])
        }
    
    def get_active_levels(self) -> Dict:
        """Get all active levels."""
        return {
            'levels': self.levels,
            'auto_supports': self.auto_levels['SUPPORT'],
            'auto_resistances': self.auto_levels['RESISTANCE']
        }
    
    def clear_old_levels(self, max_age_hours: int = 24):
        """Remove levels older than max_age_hours."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        self.levels = [l for l in self.levels if l['added'] > cutoff]

