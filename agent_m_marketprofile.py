# agent_m_marketprofile.py
"""
Agent_M - Market Profile Master
Analyzes volume profile, POC, and value areas
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

class MarketProfileAgent:
    """Market Profile analysis - POC, Value Area, Volume Profile"""
    
    def __init__(self):
        self.name = "Agent_M"
        self.agent_type = "Market Profile Master"
        self.timeframe = "M15"
        self.value_area_percentage = 0.70  # 70% of volume
        print(f"   ✅ {self.name} initialized")
    
    def analyze(self, signal_data: Dict) -> Dict:
        symbol = signal_data.get('symbol', 'EURUSD')
        price = signal_data.get('price', 0)
        
        # Calculate simple value area
        value_area_high = price * 1.001
        value_area_low = price * 0.999
        
        if price > value_area_high:
            vote = 'SELL'
            confidence = 68
            reasoning = f"🔴 Price above Value Area High"
        elif price < value_area_low:
            vote = 'BUY'
            confidence = 68
            reasoning = f"🟢 Price below Value Area Low"
        else:
            vote = 'HOLD'
            confidence = 50
            reasoning = "⚪ Price inside Value Area"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_volume_profile(self, candles: List[Dict]) -> Dict:
        """Calculate volume profile from candles"""
        
        prices = [c['close'] for c in candles]
        volumes = [c.get('volume', 1000) for c in candles]
        
        if not prices:
            return {'poc': 0, 'value_area_high': 0, 'value_area_low': 0, 'profile': []}
        
        # Create price bins
        price_range = max(prices) - min(prices)
        if price_range == 0:
            price_range = 0.001
        
        num_bins = min(20, len(candles))
        bin_size = price_range / num_bins
        
        bins = {}
        min_price = min(prices)
        
        for i, price in enumerate(prices):
            bin_idx = int((price - min_price) / bin_size) if bin_size > 0 else 0
            volume = volumes[i] if i < len(volumes) else 1000
            if bin_idx not in bins:
                bins[bin_idx] = {'price': price, 'volume': 0, 'count': 0}
            bins[bin_idx]['volume'] += volume
            bins[bin_idx]['count'] += 1
        
        # Find POC (highest volume)
        poc_bin = max(bins.items(), key=lambda x: x[1]['volume'])
        poc = poc_bin[1]['price']
        
        # Calculate value area (70% of volume)
        total_volume = sum(b['volume'] for b in bins.values())
        target_volume = total_volume * self.value_area_percentage
        
        # Sort bins by volume for value area
        sorted_bins = sorted(bins.items(), key=lambda x: x[1]['volume'], reverse=True)
        accumulated_volume = 0
        value_area_bins = []
        
        for bin_id, bin_data in sorted_bins:
            value_area_bins.append(bin_data['price'])
            accumulated_volume += bin_data['volume']
            if accumulated_volume >= target_volume:
                break
        
        value_area_high = max(value_area_bins) if value_area_bins else poc
        value_area_low = min(value_area_bins) if value_area_bins else poc
        
        return {
            'poc': poc,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'profile': bins
        }
    
    def _hold_response(self, symbol, reason):
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': reason
        }