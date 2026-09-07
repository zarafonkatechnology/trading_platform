# ============================================================
# microstructure_alpha.py - FIXED VERSION
# ============================================================

import numpy as np
from collections import deque  # ← ADD THIS
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MicrostructureAlpha:
    """
    Advanced microstructure signals for statistical arbitrage.
    """
    
    def __init__(self, window: int = 100):
        self.window = window
        self.order_book_imbalance = deque(maxlen=window)  # ← NOW WORKS
        self.order_flow_imbalance = deque(maxlen=window)  # ← NOW WORKS
        self.cancel_ratio = deque(maxlen=window)          # ← NOW WORKS
        self.volume_spike = deque(maxlen=window)          # ← NOW WORKS
        
    def calculate_order_book_imbalance(self, bid_volume: float, ask_volume: float) -> float:
        """OBI = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)"""
        if bid_volume + ask_volume == 0:
            return 0
        
        obi = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        self.order_book_imbalance.append(obi)
        return obi
    
    def calculate_order_flow_imbalance(self, buy_ticks: int, sell_ticks: int) -> float:
        """OFI = (Buy Ticks - Sell Ticks) / (Buy Ticks + Sell Ticks)"""
        if buy_ticks + sell_ticks == 0:
            return 0
        
        ofi = (buy_ticks - sell_ticks) / (buy_ticks + sell_ticks)
        self.order_flow_imbalance.append(ofi)
        return ofi
    
    def calculate_cancel_ratio(self, cancellations: int, orders: int) -> float:
        """Cancel Ratio = Cancellations / Total Orders"""
        if orders == 0:
            return 0
        
        cr = cancellations / orders
        self.cancel_ratio.append(cr)
        return cr
    
    def calculate_volume_spike(self, current_volume: float, history: List[float]) -> float:
        """Volume Spike = Current Volume / Average Volume"""
        if len(history) < 20:
            return 1.0
        
        avg_volume = np.mean(history[-20:])
        if avg_volume == 0:
            return 1.0
        
        spike = current_volume / avg_volume
        self.volume_spike.append(spike)
        return spike
    
    def get_combined_signal(self) -> Dict:
        """Combine all microstructure signals into a single confidence score."""
        avg_obi = np.mean(self.order_book_imbalance) if self.order_book_imbalance else 0
        avg_ofi = np.mean(self.order_flow_imbalance) if self.order_flow_imbalance else 0
        avg_cr = np.mean(self.cancel_ratio) if self.cancel_ratio else 0
        avg_spike = np.mean(self.volume_spike) if self.volume_spike else 0
        
        confidence = 0.5
        direction = 'NEUTRAL'
        
        if abs(avg_obi) > 0.2:
            confidence += (abs(avg_obi) - 0.2) * 0.5
            direction = 'BUY' if avg_obi > 0 else 'SELL'
        
        if abs(avg_ofi) > 0.15:
            confidence += (abs(avg_ofi) - 0.15) * 0.4
        
        if avg_cr > 0.3:
            confidence *= (1 - avg_cr)
        
        if avg_spike > 5:
            confidence *= 0.5
        
        confidence = max(0, min(1, confidence))
        
        return {
            'confidence': round(confidence * 100, 1),
            'direction': direction,
            'obi': round(avg_obi, 3),
            'ofi': round(avg_ofi, 3),
            'cancel_ratio': round(avg_cr, 3),
            'volume_spike': round(avg_spike, 2),
            'signal': direction if confidence > 0.6 else 'NEUTRAL'
        }
    
    def is_high_quality_signal(self) -> bool:
        """Determine if microstructure confirms the Z-score signal."""
        signal = self.get_combined_signal()
        return signal['confidence'] > 60 and signal['direction'] != 'NEUTRAL'