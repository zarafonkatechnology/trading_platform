# ============================================================
# volume_profile.py - Volume Profile Integration
# ============================================================
# Analyzes volume at different price levels
# ============================================================

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VolumeProfile:
    """
    Volume Profile analysis.
    
    Identifies:
    - High Volume Nodes (HVN) - Fair value areas
    - Low Volume Nodes (LVN) - Vacuum zones
    - Point of Control (POC) - Highest volume level
    - Value Area (70% of volume)
    """
    
    def __init__(self, bins: int = 20):
        self.bins = bins
        self.history = []
        self.hvn = None
        self.lvn = None
        self.poc = None
        
        logger.info("✅ VolumeProfile initialized")
    
    def analyze_profile(self, candles: List[Dict]) -> Dict:
        """
        Build volume profile from candles.
        """
        if len(candles) < 10:
            return {'status': 'INSUFFICIENT_DATA'}
        
        # Extract prices and volumes
        prices = []
        volumes = []
        
        for candle in candles:
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            volume = candle.get('volume', 0)
            
            if high > 0 and low > 0 and volume > 0:
                prices.append((high + low) / 2)
                volumes.append(volume)
        
        if len(prices) < 10:
            return {'status': 'INSUFFICIENT_DATA'}
        
        # Create volume profile
        min_price = min(prices)
        max_price = max(prices)
        
        if max_price == min_price:
            return {'status': 'NO_RANGE'}
        
        # Create bins
        bin_width = (max_price - min_price) / self.bins
        
        # Initialize bins
        bin_edges = np.linspace(min_price, max_price, self.bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_volumes = np.zeros(self.bins)
        bin_counts = np.zeros(self.bins)
        
        # Fill bins
        for i, price in enumerate(prices):
            if i < len(volumes):
                # Find bin
                bin_idx = min(int((price - min_price) / bin_width), self.bins - 1)
                bin_volumes[bin_idx] += volumes[i]
                bin_counts[bin_idx] += 1
        
        # Find POC (Point of Control)
        poc_idx = np.argmax(bin_volumes)
        poc = bin_centers[poc_idx]
        
        # Find Value Area (70% of volume)
        total_volume = np.sum(bin_volumes)
        target_volume = total_volume * 0.70
        cumulative_volume = 0
        value_area_low = None
        value_area_high = None
        
        # Start from POC and expand outward
        left_idx = poc_idx
        right_idx = poc_idx
        
        while cumulative_volume < target_volume:
            left_volume = bin_volumes[left_idx - 1] if left_idx > 0 else 0
            right_volume = bin_volumes[right_idx + 1] if right_idx < self.bins - 1 else 0
            
            if left_volume > right_volume and left_idx > 0:
                left_idx -= 1
                cumulative_volume += left_volume
            elif right_idx < self.bins - 1:
                right_idx += 1
                cumulative_volume += right_volume
            else:
                break
        
        value_area_low = bin_centers[left_idx]
        value_area_high = bin_centers[right_idx]
        
        # Find High Volume Nodes (HVN)
        # HVN = bins with volume > 80% of max volume
        hvn_threshold = np.max(bin_volumes) * 0.80
        hvn_indices = np.where(bin_volumes > hvn_threshold)[0]
        hvn_levels = [bin_centers[i] for i in hvn_indices]
        
        # Find Low Volume Nodes (LVN)
        # LVN = bins with volume < 20% of max volume
        lvn_threshold = np.max(bin_volumes) * 0.20
        lvn_indices = np.where(bin_volumes < lvn_threshold)[0]
        lvn_levels = [bin_centers[i] for i in lvn_indices]
        
        result = {
            'poc': poc,
            'value_area_low': value_area_low,
            'value_area_high': value_area_high,
            'hvn_levels': hvn_levels,
            'lvn_levels': lvn_levels,
            'bin_centers': bin_centers.tolist(),
            'bin_volumes': bin_volumes.tolist(),
            'total_volume': total_volume,
            'value_area_width': value_area_high - value_area_low,
            'hvn_count': len(hvn_levels),
            'lvn_count': len(lvn_levels)
        }
        
        # Store for future reference
        self.history.append(result)
        if len(self.history) > 10:
            self.history.pop(0)
        
        self.poc = poc
        self.hvn = hvn_levels
        self.lvn = lvn_levels
        
        return result
    
    def get_price_context(self, price: float) -> Dict:
        """
        Get volume context for a specific price.
        """
        if not self.history:
            return {'context': 'UNKNOWN', 'reason': 'No profile'}
        
        latest = self.history[-1]
        
        # Check if price is in HVN
        for hvn in latest.get('hvn_levels', []):
            if abs(price - hvn) < 0.001 * price:
                return {'context': 'HIGH_VOLUME_NODE', 'type': 'HVN'}
        
        # Check if price is in LVN
        for lvn in latest.get('lvn_levels', []):
            if abs(price - lvn) < 0.001 * price:
                return {'context': 'LOW_VOLUME_NODE', 'type': 'LVN'}
        
        # Check if price is in value area
        value_area_low = latest.get('value_area_low', 0)
        value_area_high = latest.get('value_area_high', 0)
        
        if value_area_low < price < value_area_high:
            return {'context': 'VALUE_AREA', 'type': 'VA'}
        
        return {'context': 'OUTSIDE_VALUE_AREA', 'type': 'OVA'}