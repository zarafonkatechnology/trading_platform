# ============================================================
# stop_hunt_detector.py - Stop-Loss Hunting Detector
# ============================================================
# Detects market maker stop hunting patterns
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StopHuntDetector:
    """
    Detects stop-loss hunting patterns.
    
    Patterns:
    1. Long wick > 50% of candle (price spiked then reversed)
    2. Volume spike during the wick
    3. Close near the opposite side of the wick
    4. Price broke a key level then reversed
    """
    
    def __init__(self):
        self.history = []
        self.detected_hunts = []
        self.wick_threshold = 0.50  # 50% of candle is wick
        self.volume_multiplier = 2.5  # Volume spike threshold
        
        logger.info("✅ StopHuntDetector initialized")
    
    def analyze_candle(self, candle: Dict) -> Dict:
        """
        Analyze a single candle for stop hunting.
        
        candle = {
            'open': 100,
            'high': 105,
            'low': 97,
            'close': 101,
            'volume': 5000
        }
        """
        open_price = candle.get('open', 0)
        high_price = candle.get('high', 0)
        low_price = candle.get('low', 0)
        close_price = candle.get('close', 0)
        volume = candle.get('volume', 0)
        
        if high_price <= 0 or low_price <= 0:
            return {'is_hunt': False, 'reason': 'Invalid candle'}
        
        # Calculate body
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return {'is_hunt': False, 'reason': 'No range'}
        
        # Calculate wicks
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        
        # Wick ratios
        upper_ratio = upper_wick / total_range
        lower_ratio = lower_wick / total_range
        
        # Determine direction
        is_bullish = close_price > open_price
        
        # ===== HUNT DETECTION =====
        is_hunt = False
        hunt_type = None
        hunt_score = 0
        
        # Pattern 1: Long upper wick (sell side hunt)
        if upper_ratio > self.wick_threshold:
            is_hunt = True
            hunt_type = 'SELL_SIDE_HUNT'
            hunt_score = upper_ratio
            
            # Volume spike confirmation
            if volume > self._get_average_volume() * self.volume_multiplier:
                hunt_score += 0.2
        
        # Pattern 2: Long lower wick (buy side hunt)
        if lower_ratio > self.wick_threshold:
            is_hunt = True
            hunt_type = 'BUY_SIDE_HUNT'
            hunt_score = lower_ratio
            
            if volume > self._get_average_volume() * self.volume_multiplier:
                hunt_score += 0.2
        
        # Pattern 3: Key level break then reverse
        # (This needs to be checked with levels from market structure)
        
        result = {
            'is_hunt': is_hunt,
            'hunt_type': hunt_type,
            'hunt_score': min(1.0, hunt_score),
            'upper_wick_ratio': round(upper_ratio, 3),
            'lower_wick_ratio': round(lower_ratio, 3),
            'direction': 'BEARISH' if is_bullish else 'BULLISH',
            'reason': f'{hunt_type} detected' if is_hunt else 'No hunt detected'
        }
        
        if is_hunt:
            self.detected_hunts.append({
                'timestamp': datetime.now(),
                'candle': candle,
                'result': result
            })
            logger.debug(f"🔴 STOP HUNT DETECTED: {hunt_type} (Score: {hunt_score:.2f})")
        
        return result
    
    def _get_average_volume(self) -> float:
        """Calculate average volume from history."""
        if not self.history:
            return 1000
        volumes = [c.get('volume', 0) for c in self.history[-50:] if c.get('volume', 0) > 0]
        return np.mean(volumes) if volumes else 1000
    
    def get_recent_hunts(self, count: int = 5) -> List[Dict]:
        """Get recent stop hunts."""
        return self.detected_hunts[-count:] if self.detected_hunts else []
    
    def is_active_hunt(self, symbol: str = None) -> bool:
        """Check if a hunt is currently active."""
        if not self.detected_hunts:
            return False
        
        # Check if last hunt was within 5 minutes
        last_hunt = self.detected_hunts[-1]
        elapsed = (datetime.now() - last_hunt['timestamp']).seconds
        return elapsed < 300  # 5 minutes