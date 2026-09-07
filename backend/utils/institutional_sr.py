"""
Institutional Supply/Demand with Hidden Fund Estimation
Implements professional formulas for true support/resistance
"""

import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

@dataclass
class InstitutionalLevel:
    """Represents a supply/demand level with institutional calculations"""
    price: float
    level_type: str  # 'SUPPLY' or 'DEMAND'
    original_strength: float  # S_original (0-100)
    created_at: datetime
    touches: int = 0
    total_volume_at_level: float = 0
    reversal_pattern_score: float = 0  # R
    pattern_multiplier: float = 1.0    # P
    
    @property
    def age_hours(self) -> float:
        """Age of level in hours"""
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    @property
    def current_strength(self) -> float:
        """S_current = S_original × (0.15 + 0.85 × e^(-t/180))"""
        decay = 0.15 + 0.85 * math.exp(-self.age_hours / 180)
        return self.original_strength * decay
    
    @property
    def touch_multiplier(self) -> float:
        """min(1, T_touches/10)"""
        return min(1.0, self.touches / 10)
    
    def hidden_funds(self, volume: float, reversal_strength: float) -> float:
        """H = V × R × P - Estimates hidden institutional orders"""
        return volume * reversal_strength * self.pattern_multiplier
    
    def manipulation_score(self, volume_ratio: float, hesitation_bars: int, 
                          mtf_alignment: float) -> float:
        """
        M = 0.4×(V/V_avg) + 0.3×(1 - T_hes/3) + 0.3×C_mtf
        M ≥ 0.6 = Genuine move (not manipulation)
        """
        term1 = 0.4 * min(2.0, volume_ratio)  # Volume term (capped at 2x)
        term2 = 0.3 * max(0, 1 - hesitation_bars / 3)  # Hesitation term
        term3 = 0.3 * mtf_alignment  # Multi-timeframe alignment
        
        return term1 + term2 + term3
    
    def confidence(self, volume_ratio: float, hesitation_bars: int, 
                   mtf_alignment: float) -> float:
        """
        Confidence = S_current × min(1, T_touches/10) × M
        """
        s_current = self.current_strength / 100  # Normalize to 0-1
        touch_factor = self.touch_multiplier
        m_score = self.manipulation_score(volume_ratio, hesitation_bars, mtf_alignment)
        
        confidence = s_current * touch_factor * m_score
        
        # Decision thresholds
        if confidence >= 0.7:
            decision = "TRADE"
            position_size = 1.0
        elif confidence >= 0.4:
            decision = "REDUCE"
            position_size = 0.5
        else:
            decision = "NO_TRADE"
            position_size = 0
        
        return {
            'confidence': round(confidence * 100, 1),
            'decision': decision,
            'position_size': position_size,
            'components': {
                's_current': round(s_current * 100, 1),
                'touch_factor': round(touch_factor * 100, 1),
                'm_score': round(m_score * 100, 1),
                'manipulation_risk': m_score < 0.6
            }
        }


class InstitutionalSRAgent:
    """
    Agent_R enhanced with institutional formulas
    Detects true support/resistance using hidden fund estimation
    """
    
    def __init__(self, name: str = "Agent_R_Pro"):
        self.name = name
        self.agent_type = "Institutional S/R"
        self.levels = []  # List of InstitutionalLevel
        self.reversal_patterns = {
            'bullish_engulfing': 1.5,
            'hammer': 1.3,
            'morning_star': 2.0,
            'piercing': 1.4,
            'bullish_divergence': 1.6
        }
        self.bearish_patterns = {
            'bearish_engulfing': 1.5,
            'shooting_star': 1.3,
            'evening_star': 2.0,
            'dark_cloud': 1.4,
            'bearish_divergence': 1.6
        }
    
    def add_level(self, price: float, level_type: str, 
                  reversal_pattern: str, volume: float,
                  original_strength: float = 80.0):
        """Add a new institutional level"""
        
        # Get pattern multiplier
        if level_type == 'DEMAND':
            pattern_multiplier = self.reversal_patterns.get(reversal_pattern, 1.0)
        else:
            pattern_multiplier = self.bearish_patterns.get(reversal_pattern, 1.0)
        
        # Estimate reversal strength (R) from candle size
        # R = (candle_body / average_range) × 0.5 + 0.5
        reversal_strength = 0.7  # Default, calculate from actual candle
        
        level = InstitutionalLevel(
            price=price,
            level_type=level_type,
            original_strength=original_strength,
            created_at=datetime.now(),
            total_volume_at_level=volume,
            reversal_pattern_score=reversal_strength,
            pattern_multiplier=pattern_multiplier
        )
        
        self.levels.append(level)
        self._sort_levels()
        
        # Decay old levels
        self._decay_old_levels()
        
        return level
    
    def _sort_levels(self):
        """Sort levels by price"""
        self.levels.sort(key=lambda x: x.price)
    
    def _decay_old_levels(self, max_age_hours: int = 720):  # 30 days
        """Remove levels older than max_age_hours"""
        self.levels = [l for l in self.levels if l.age_hours < max_age_hours]
    
    def get_nearest_levels(self, current_price: float) -> Tuple[Optional[InstitutionalLevel], 
                                                                 Optional[InstitutionalLevel]]:
        """Get nearest supply (above) and demand (below) levels"""
        supply = None
        demand = None
        
        for level in self.levels:
            if level.level_type == 'SUPPLY' and level.price > current_price:
                if supply is None or level.price < supply.price:
                    supply = level
            elif level.level_type == 'DEMAND' and level.price < current_price:
                if demand is None or level.price > demand.price:
                    demand = level
        
        return supply, demand
    
    def detect_level_from_candle(self, candle: Dict, prev_candle: Dict,
                                  volume_profile: Dict) -> Optional[InstitutionalLevel]:
        """
        Detect institutional level from candle pattern
        """
        # Calculate reversal strength
        body = abs(candle['close'] - candle['open'])
        avg_range = volume_profile.get('avg_range', body)
        reversal_strength = min(1.0, (body / avg_range) * 0.5 + 0.5)
        
        # Check for bullish reversal at support
        if candle['close'] > candle['open']:  # Bullish candle
            # Check for pattern
            pattern = self._identify_bullish_pattern(candle, prev_candle)
            if pattern:
                return self.add_level(
                    price=candle['low'],
                    level_type='DEMAND',
                    reversal_pattern=pattern,
                    volume=candle.get('volume', 0),
                    original_strength=reversal_strength * 100
                )
        
        # Check for bearish reversal at resistance
        elif candle['close'] < candle['open']:  # Bearish candle
            pattern = self._identify_bearish_pattern(candle, prev_candle)
            if pattern:
                return self.add_level(
                    price=candle['high'],
                    level_type='SUPPLY',
                    reversal_pattern=pattern,
                    volume=candle.get('volume', 0),
                    original_strength=reversal_strength * 100
                )
        
        return None
    
    def _identify_bullish_pattern(self, candle: Dict, prev_candle: Dict) -> Optional[str]:
        """Identify bullish reversal pattern"""
        body = candle['close'] - candle['open']
        prev_body = prev_candle['close'] - prev_candle['open']
        
        # Bullish engulfing
        if (body > 0 and prev_body < 0 and 
            candle['close'] > prev_candle['open'] and 
            candle['open'] < prev_candle['close']):
            return 'bullish_engulfing'
        
        # Hammer
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        if lower_wick > body * 2:
            return 'hammer'
        
        return None
    
    def _identify_bearish_pattern(self, candle: Dict, prev_candle: Dict) -> Optional[str]:
        """Identify bearish reversal pattern"""
        body = candle['close'] - candle['open']
        prev_body = prev_candle['close'] - prev_candle['open']
        
        # Bearish engulfing
        if (body < 0 and prev_body > 0 and 
            candle['close'] < prev_candle['open'] and 
            candle['open'] > prev_candle['close']):
            return 'bearish_engulfing'
        
        # Shooting star
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        if upper_wick > abs(body) * 2:
            return 'shooting_star'
        
        return None
    
    def analyze(self, signal_data: Dict, volume_profile: Dict, 
                mtf_alignment: float = 0.7) -> Dict:
        """
        Complete analysis using institutional formulas
        
        Args:
            signal_data: Current market data (price, volume)
            volume_profile: Volume data (avg_volume, volume_ratio)
            mtf_alignment: Multi-timeframe alignment (0-1)
        """
        current_price = signal_data.get('price', 0)
        current_volume = signal_data.get('volume', 0)
        
        # Get nearest levels
        nearest_supply, nearest_demand = self.get_nearest_levels(current_price)
        
        # Determine which level is relevant
        relevant_level = None
        distance = float('inf')
        
        if nearest_supply:
            supply_dist = (nearest_supply.price - current_price) / current_price
            if supply_dist < distance:
                distance = supply_dist
                relevant_level = nearest_supply
        
        if nearest_demand:
            demand_dist = (current_price - nearest_demand.price) / current_price
            if demand_dist < distance:
                distance = demand_dist
                relevant_level = nearest_demand
        
        if not relevant_level or distance > 0.01:  # More than 1% away
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': 'No significant institutional levels nearby',
                'nearest_level': None
            }
        
        # Calculate confidence using the formula
        volume_ratio = volume_profile.get('volume_ratio', 1.0)
        hesitation_bars = volume_profile.get('hesitation_bars', 0)
        
        confidence_result = relevant_level.confidence(
            volume_ratio=volume_ratio,
            hesitation_bars=hesitation_bars,
            mtf_alignment=mtf_alignment
        )
        
        # Hidden funds estimation
        hidden_funds = relevant_level.hidden_funds(
            volume=current_volume,
            reversal_strength=relevant_level.reversal_pattern_score
        )
        
        # Determine vote
        if confidence_result['decision'] == 'TRADE':
            vote = 'BUY' if relevant_level.level_type == 'DEMAND' else 'SELL'
        elif confidence_result['decision'] == 'REDUCE':
            vote = 'BUY' if relevant_level.level_type == 'DEMAND' else 'SELL'
        else:
            vote = 'HOLD'
        
        # Generate reasoning
        reasoning = (
            f"Institutional {relevant_level.level_type} at {relevant_level.price:.5f} | "
            f"Strength: {relevant_level.current_strength:.1f}% | "
            f"Touches: {relevant_level.touches} | "
            f"Confidence: {confidence_result['confidence']:.1f}% | "
            f"Decision: {confidence_result['decision']} | "
            f"Est. Hidden Funds: ${hidden_funds:,.0f}"
        )
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': confidence_result['confidence'],
            'reasoning': reasoning,
            'nearest_level': {
                'price': relevant_level.price,
                'type': relevant_level.level_type,
                'strength': round(relevant_level.current_strength, 1),
                'touches': relevant_level.touches,
                'age_hours': round(relevant_level.age_hours, 1)
            },
            'confidence_components': confidence_result['components'],
            'hidden_funds_estimate': hidden_funds,
            'position_size': confidence_result['position_size']
        }
    
    def record_touch(self, price: float, volume: float):
        """Record a touch of a level (price reached but didn't break)"""
        for level in self.levels:
            if abs(level.price - price) / price < 0.002:  # Within 0.2%
                level.touches += 1
                level.total_volume_at_level += volume
                break
