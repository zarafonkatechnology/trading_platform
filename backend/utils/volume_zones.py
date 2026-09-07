"""
Volume-Weighted Supply/Demand Zone Detection
Combines price action with volume confirmation
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VolumeNode:
    """Price level with accumulated volume"""
    price: float
    total_volume: float = 0
    buy_volume: float = 0
    sell_volume: float = 0
    tests: int = 0
    last_test: Optional[datetime] = None
    
    @property
    def net_delta(self) -> float:
        return self.buy_volume - self.sell_volume
    
    @property
    def dominance(self) -> str:
        """Which side dominates this level"""
        if self.net_delta > self.total_volume * 0.3:
            return 'BUY'
        elif self.net_delta < -self.total_volume * 0.3:
            return 'SELL'
        return 'NEUTRAL'
    
    @property
    def strength(self) -> float:
        """Calculate zone strength (0-100)"""
        # Volume score (max 40)
        volume_score = min(40, self.total_volume / 50000 * 20)
        
        # Test score (max 30)
        test_score = min(30, self.tests * 10)
        
        # Delta score (max 20)
        delta_ratio = abs(self.net_delta) / (self.total_volume + 1)
        delta_score = min(20, delta_ratio * 50)
        
        # Recency score (max 10)
        recency_score = 10
        if self.last_test:
            hours_ago = (datetime.now() - self.last_test).total_seconds() / 3600
            recency_score = max(0, 10 - hours_ago / 24)
        
        return min(100, volume_score + test_score + delta_score + recency_score)


class VolumeZoneDetector:
    """
    Detects support/resistance zones using volume profile
    """
    
    def __init__(self, bucket_size: float = 0.001):
        """
        Args:
            bucket_size: Price bucket size (0.001 = 10 pips for forex)
        """
        self.bucket_size = bucket_size
        self.volume_profile = defaultdict(lambda: VolumeNode(price=0))
        self.high_volume_nodes = []
        
    def update_from_candles(self, candles: List[Dict]):
        """
        Update volume profile from candle data
        
        Args:
            candles: List of candles with 'high', 'low', 'close', 'volume', 'buy_volume'
        """
        for candle in candles:
            self._add_candle_volume(candle)
        
        self._recalculate_nodes()
    
    def _add_candle_volume(self, candle: Dict):
        """Add volume from a single candle to price buckets"""
        high = candle['high']
        low = candle['low']
        volume = candle.get('volume', 0)
        buy_volume = candle.get('buy_volume', volume * 0.5)
        sell_volume = volume - buy_volume
        
        # Distribute volume across price range
        price_range = high - low
        if price_range <= 0:
            return
        
        num_buckets = max(1, int(price_range / self.bucket_size))
        bucket_volume = volume / num_buckets
        bucket_buy = buy_volume / num_buckets
        bucket_sell = sell_volume / num_buckets
        
        for i in range(num_buckets + 1):
            price = low + (i * price_range / num_buckets)
            bucket_key = self._get_bucket_key(price)
            
            if bucket_key not in self.volume_profile:
                self.volume_profile[bucket_key] = VolumeNode(price=price)
            
            node = self.volume_profile[bucket_key]
            node.total_volume += bucket_volume
            node.buy_volume += bucket_buy
            node.sell_volume += bucket_sell
    
    def _get_bucket_key(self, price: float) -> int:
        """Get bucket key for a price level"""
        return int(price / self.bucket_size)
    
    def _recalculate_nodes(self):
        """Recalculate high volume nodes"""
        self.high_volume_nodes = []
        
        for node in self.volume_profile.values():
            if node.total_volume > 0:
                node.price = node.price
                self.high_volume_nodes.append(node)
        
        # Sort by volume
        self.high_volume_nodes.sort(key=lambda x: x.total_volume, reverse=True)
    
    def get_supply_zones(self, current_price: float, top_n: int = 5) -> List[VolumeNode]:
        """Get supply zones (resistance) above current price"""
        above = [n for n in self.high_volume_nodes if n.price > current_price and n.dominance != 'BUY']
        above.sort(key=lambda x: x.price)
        return above[:top_n]
    
    def get_demand_zones(self, current_price: float, top_n: int = 5) -> List[VolumeNode]:
        """Get demand zones (support) below current price"""
        below = [n for n in self.high_volume_nodes if n.price < current_price and n.dominance != 'SELL']
        below.sort(key=lambda x: x.price, reverse=True)
        return below[:top_n]
    
    def get_nearest_zones(self, current_price: float) -> Tuple[Optional[VolumeNode], Optional[VolumeNode]]:
        """Get nearest supply and demand zones"""
        supply_zones = self.get_supply_zones(current_price, top_n=1)
        demand_zones = self.get_demand_zones(current_price, top_n=1)
        
        return (
            supply_zones[0] if supply_zones else None,
            demand_zones[0] if demand_zones else None
        )


class CandlePatternAnalyzer:
    """
    Analyzes Japanese candlestick patterns for reversal confirmation
    """
    
    @staticmethod
    def is_bullish_reversal(candle: Dict, previous_candle: Dict) -> Tuple[bool, float]:
        """
        Detect bullish reversal patterns
        
        Returns:
            (is_reversal, confidence)
        """
        confidence = 0
        reasons = []
        
        # Bullish engulfing
        if (candle['close'] > candle['open'] and 
            candle['open'] < previous_candle['close'] and
            candle['close'] > previous_candle['open']):
            confidence += 40
            reasons.append("bullish engulfing")
        
        # Hammer / Doji at support
        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        if lower_wick > body * 2:
            confidence += 30
            reasons.append("hammer/rejection")
        
        # Volume confirmation
        volume_ratio = candle.get('volume', 0) / (previous_candle.get('volume', 1) + 1)
        if volume_ratio > 1.5:
            confidence += 20
            reasons.append("volume surge")
        
        # Close above previous high
        if candle['close'] > previous_candle['high']:
            confidence += 10
            reasons.append("close above previous high")
        
        return confidence >= 50, f"{' | '.join(reasons)} ({confidence}%)"
    
    @staticmethod
    def is_bearish_reversal(candle: Dict, previous_candle: Dict) -> Tuple[bool, float]:
        """
        Detect bearish reversal patterns
        
        Returns:
            (is_reversal, confidence)
        """
        confidence = 0
        reasons = []
        
        # Bearish engulfing
        if (candle['close'] < candle['open'] and 
            candle['open'] > previous_candle['close'] and
            candle['close'] < previous_candle['open']):
            confidence += 40
            reasons.append("bearish engulfing")
        
        # Shooting star / rejection at resistance
        body = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        if upper_wick > body * 2:
            confidence += 30
            reasons.append("shooting star/rejection")
        
        # Volume confirmation
        volume_ratio = candle.get('volume', 0) / (previous_candle.get('volume', 1) + 1)
        if volume_ratio > 1.5:
            confidence += 20
            reasons.append("volume surge")
        
        # Close below previous low
        if candle['close'] < previous_candle['low']:
            confidence += 10
            reasons.append("close below previous low")
        
        return confidence >= 50, f"{' | '.join(reasons)} ({confidence}%)"


class VolumeConfirmedSRAgent:
    """
    Complete Supply/Demand agent using volume confirmation
    """
    
    def __init__(self, name: str = "Agent_R_Enhanced"):
        self.name = name
        self.agent_type = "Volume-Confirmed S/R"
        self.volume_detector = VolumeZoneDetector(bucket_size=0.001)
        self.candle_analyzer = CandlePatternAnalyzer()
        self.price_history = []
    
    def update_market_data(self, candles: List[Dict]):
        """Update agent with new market data"""
        self.price_history.extend(candles)
        # Keep last 500 candles
        if len(self.price_history) > 500:
            self.price_history = self.price_history[-500:]
        
        self.volume_detector.update_from_candles(candles)
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Analyze current price against volume-confirmed zones
        """
        current_price = signal_data.get('price', 0)
        
        # Get nearest volume zones
        nearest_supply, nearest_demand = self.volume_detector.get_nearest_zones(current_price)
        
        # Get recent candles for pattern analysis
        if len(self.price_history) < 2:
            return self._default_response(current_price)
        
        last_candle = self.price_history[-1]
        prev_candle = self.price_history[-2]
        
        # Check for reversal patterns
        is_bullish, bull_reason = self.candle_analyzer.is_bullish_reversal(last_candle, prev_candle)
        is_bearish, bear_reason = self.candle_analyzer.is_bearish_reversal(last_candle, prev_candle)
        
        # Determine action
        # BUY: Near demand zone + bullish reversal + volume confirmation
        if nearest_demand and current_price <= nearest_demand.price * 1.002:
            distance_pct = (current_price - nearest_demand.price) / nearest_demand.price * 100
            zone_strength = nearest_demand.strength
            
            if is_bullish and zone_strength > 50:
                vote = 'BUY'
                confidence = min(95, 50 + zone_strength * 0.3 + (1 - abs(distance_pct)) * 20)
                reasoning = f"Near demand zone ({nearest_demand.price:.5f}) with bullish reversal: {bull_reason}"
            else:
                vote = 'WATCH'
                confidence = zone_strength
                reasoning = f"Near demand zone but waiting for bullish confirmation"
        
        # SELL: Near supply zone + bearish reversal + volume confirmation
        elif nearest_supply and current_price >= nearest_supply.price * 0.998:
            distance_pct = (nearest_supply.price - current_price) / nearest_supply.price * 100
            zone_strength = nearest_supply.strength
            
            if is_bearish and zone_strength > 50:
                vote = 'SELL'
                confidence = min(95, 50 + zone_strength * 0.3 + (1 - abs(distance_pct)) * 20)
                reasoning = f"Near supply zone ({nearest_supply.price:.5f}) with bearish reversal: {bear_reason}"
            else:
                vote = 'WATCH'
                confidence = zone_strength
                reasoning = f"Near supply zone but waiting for bearish confirmation"
        
        else:
            vote = 'HOLD'
            confidence = 50
            reasoning = f"No significant volume zones nearby"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': round(confidence, 1),
            'reasoning': reasoning,
            'nearest_supply': nearest_supply.price if nearest_supply else None,
            'nearest_demand': nearest_demand.price if nearest_demand else None,
            'supply_strength': nearest_supply.strength if nearest_supply else 0,
            'demand_strength': nearest_demand.strength if nearest_demand else 0,
            'bullish_reversal': is_bullish,
            'bearish_reversal': is_bearish
        }
    
    def _default_response(self, current_price: float) -> Dict:
        """Default response when insufficient data"""
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': 'Insufficient volume data for zone detection',
            'nearest_supply': None,
            'nearest_demand': None
        }
