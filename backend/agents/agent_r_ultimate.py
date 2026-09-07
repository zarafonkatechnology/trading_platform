"""
Agent_R Ultimate - Institutional Supply/Demand
Integrates: Volume Profile + Monte Carlo + Agent_J Volume Confirmation
Enhanced with Velocity Filter + Adaptive Threshold
"""

import logging
import math
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import requests
logger = logging.getLogger(__name__)


# ============================================================
# FIX: Add missing imports and fallbacks
# ============================================================

try:
    import requests
except ImportError:
    requests = None
    logger.warning("⚠️ requests module not available")

try:
    from price_cache_manager import get_price_for_agent, get_any_price
except ImportError:
    def get_price_for_agent(agent_name, symbol):
        return None
    def get_any_price(symbol):
        return None

try:
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    def get_price_with_fallback(symbol, agent_name):
        # Fallback: try to get from price cache
        try:
            from price_cache_manager import price_cache
            return price_cache.get_latest(symbol, 0)
        except:
            return 0
    def get_price_with_details(symbol):
        return {'mid': 0}


# ============================================================
# PART 1: DATA STRUCTURES
# ============================================================

class TradeSignal(Enum):
    GENUINE = "✅ GENUINE - Trade"
    MANIPULATION = "⚠️ MANIPULATION - Skip"
    UNCERTAIN = "❓ UNCERTAIN - Reduce Size"


@dataclass
class InstitutionalLevel:
    """Represents a supply/demand level with institutional calculations"""
    price: float
    level_type: str  # 'SUPPLY' or 'DEMAND'
    original_strength: float
    created_at: datetime
    touches: int = 0
    total_volume_at_level: float = 0
    reversal_pattern_score: float = 0.7
    pattern_multiplier: float = 1.0
    
    @property
    def age_hours(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    @property
    def current_strength(self) -> float:
        """S_current = S_original × (0.15 + 0.85 × e^(-t/180))"""
        decay = 0.15 + 0.85 * math.exp(-self.age_hours / 180)
        return self.original_strength * decay
    
    @property
    def touch_multiplier(self) -> float:
        return min(1.0, self.touches / 10)
    
    def hidden_funds(self, volume: float, reversal_strength: float) -> float:
        """H = V × R × P"""
        return volume * reversal_strength * self.pattern_multiplier


# ============================================================
# PART 2: VELOCITY FILTER (NEW)
# ============================================================

class VelocityFilter:
    """
    Prevents premature entries when momentum is still building.
    Ensures breakout confirmation before acting.
    """
    
    def __init__(self, window: int = 5):
        self.window = window
        self.price_history = []
        self.velocity_history = []
    
    def update(self, price: float) -> Dict:
        """Update filter with new price."""
        self.price_history.append(price)
        if len(self.price_history) > self.window + 1:
            self.price_history.pop(0)
        
        if len(self.price_history) < 3:
            return {
                'velocity': 0.0,
                'momentum': 'STABLE',
                'is_accelerating': False,
                'can_enter': False
            }
        
        velocities = [self.price_history[i] - self.price_history[i-1] 
                      for i in range(1, len(self.price_history))]
        current_velocity = velocities[-1]
        self.velocity_history.append(current_velocity)
        
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[-2]
            is_accelerating = (current_velocity > 0 and acceleration > 0) or \
                              (current_velocity < 0 and acceleration < 0)
        else:
            acceleration = 0.0
            is_accelerating = False
        
        if current_velocity > 0.1:
            momentum = 'RISING'
        elif current_velocity < -0.1:
            momentum = 'FALLING'
        else:
            momentum = 'STABLE'
        
        can_enter = abs(current_velocity) < 0.05 or is_accelerating
        
        return {
            'velocity': current_velocity,
            'momentum': momentum,
            'is_accelerating': is_accelerating,
            'can_enter': can_enter
        }


# ============================================================
# PART 3: MONTE CARLO SIMULATOR FOR ZONE BREAKOUT
# ============================================================

class MonteCarloZoneSimulator:
    """
    Monte Carlo simulation for zone breakout probability
    Runs 1000+ simulations to predict breakout direction
    """
    
    def __init__(self, n_simulations: int = 1000, horizon: int = 20):
        self.n_simulations = n_simulations
        self.horizon = horizon
        self.cache = {}
    
    def simulate_breakout_probability(self, current_price: float, 
                                       supply_price: Optional[float],
                                       demand_price: Optional[float],
                                       volatility: float = 0.005) -> Dict:
        """
        Simulate future price paths to determine breakout probability
        """
        results = {
            'breakout_up': 0,
            'breakout_down': 0,
            'bounce': 0,
            'price_paths': []
        }
        
        for _ in range(self.n_simulations):
            price = current_price
            path = [price]
            broke_up = False
            broke_down = False
            
            for step in range(self.horizon):
                shock = random.gauss(0, volatility)
                price = price * (1 + shock)
                path.append(price)
                
                if supply_price and price > supply_price:
                    broke_up = True
                if demand_price and price < demand_price:
                    broke_down = True
            
            if broke_up and not broke_down:
                results['breakout_up'] += 1
            elif broke_down and not broke_up:
                results['breakout_down'] += 1
            else:
                results['bounce'] += 1
            
            if len(results['price_paths']) < 50:
                results['price_paths'].append(path)
        
        results['probabilities'] = {
            'breakout_up': round(results['breakout_up'] / self.n_simulations * 100, 1),
            'breakout_down': round(results['breakout_down'] / self.n_simulations * 100, 1),
            'bounce': round(results['bounce'] / self.n_simulations * 100, 1)
        }
        
        results['expected_move'] = self._calculate_expected_move(results['price_paths'])
        
        return results
    
    def _calculate_expected_move(self, paths: List[List[float]]) -> float:
        """Calculate expected price move from simulations"""
        if not paths:
            return 0
        final_prices = [path[-1] for path in paths if len(path) > 1]
        if not final_prices:
            return 0
        avg_final = sum(final_prices) / len(final_prices)
        start = paths[0][0] if paths else 1
        return (avg_final - start) / start * 100


# ============================================================
# PART 4: MANIPULATION DETECTOR (FIXED)
# ============================================================

class ManipulationDetector:
    """M = 0.4×(V/V_avg) + 0.3×(1 - T/3) + 0.3×C_mtf"""
    
    W_VOLUME = 0.4
    W_HESITATION = 0.3
    W_ALIGNMENT = 0.3
    DEFAULT_THRESHOLD = 0.65  # ← FIX: Increased from 0.6 to 0.65
    
    def detect(self, volume_ratio: float, hesitation_bars: int, 
               mtf_alignment: float, threshold: float = None) -> Tuple[float, TradeSignal, str]:
        """Detect manipulation with adaptive threshold."""
        
        # Clamp inputs
        volume_ratio = min(2.0, max(0.1, volume_ratio))
        hesitation_bars = min(3, max(0, hesitation_bars))
        mtf_alignment = 1.0 if mtf_alignment >= 0.5 else 0.0
        
        # Calculate components
        volume_score = min(1.0, volume_ratio / 1.0)
        hesitation_score = 1 - (hesitation_bars / 3)
        alignment_score = mtf_alignment
        
        # Calculate M-score
        m_score = (self.W_VOLUME * volume_score + 
                   self.W_HESITATION * hesitation_score + 
                   self.W_ALIGNMENT * alignment_score)
        
        # Use adaptive threshold if provided
        genuine_threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD
        
        # Determine signal
        if m_score >= genuine_threshold:
            signal = TradeSignal.GENUINE
            reasoning = f"✅ GENUINE: M={m_score:.2f}≥{genuine_threshold:.2f}"
        elif m_score >= 0.45:  # ← FIX: Lower threshold for UNCERTAIN
            signal = TradeSignal.UNCERTAIN
            reasoning = f"❓ UNCERTAIN: M={m_score:.2f} - Reduce size"
        else:
            signal = TradeSignal.MANIPULATION
            reasoning = f"⚠️ MANIPULATION: M={m_score:.2f}<0.45 - Skip"
        
        return m_score, signal, reasoning


# ============================================================
# PART 5: COMPLETE AGENT_R ULTIMATE
# ============================================================

class AgentRUltimate:
    """
    Ultimate Institutional Supply/Demand Agent
    Integrates: Volume Profile + Monte Carlo + Agent_J Volume Confirmation
    Enhanced with Velocity Filter + Adaptive Threshold
    """
    
    def __init__(self, name: str = "Agent_R"):
        self.name = name
        self.agent_type = "Institutional S/R"
        
        # Components
        self.monte_carlo = MonteCarloZoneSimulator(n_simulations=1000)
        self.manipulation_detector = ManipulationDetector()
        
        # ===== FIX: ADD VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # Volume tracking (for Agent_J integration)
        self.volume_history = []
        self.avg_volume = 10000
        self.volume_surge_detected = False
        
        # Zone storage
        self.supply_zones = []
        self.demand_zones = []
        
        # Price/candle history
        self.candle_history = []
        
        # Cache for price
        self._price_cache = {}
        
        print(f"✅ {self.name} initialized (Monte Carlo + Agent_J + Velocity Filter)")
    
    # ============================================================
    # FIX: Price Retrieval
    # ============================================================
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price with fallback."""
        # Check cache first
        if symbol in self._price_cache:
            cached_time, cached_price = self._price_cache[symbol]
            if (datetime.now() - cached_time).seconds < 10:
                return cached_price
        
        try:
            # Try price cache
            from price_cache_manager import price_cache
            price = price_cache.get_latest(symbol, 0)
            if price > 0:
                self._price_cache[symbol] = (datetime.now(), price)
                return price
        except:
            pass
        
        # Try get_price_with_fallback
        price = get_price_with_fallback(symbol, self.name)
        if price > 0:
            self._price_cache[symbol] = (datetime.now(), price)
            return price
        
        return 0.0
    
    def get_volume_ratio(self, current_volume: float = None) -> float:
        """Calculate V_level / V_avg"""
        vol = current_volume or (self.volume_history[-1] if self.volume_history else 10000)
        return vol / self.avg_volume if self.avg_volume > 0 else 1.0
    
    # ============================================================
    # ZONE MANAGEMENT
    # ============================================================
    
    def add_zone(self, price: float, zone_type: str, volume: float,
                 pattern_multiplier: float = 1.0, strength: float = 80.0):
        """Add a new supply/demand zone"""
        level = InstitutionalLevel(
            price=price,
            level_type=zone_type,
            original_strength=strength,
            created_at=datetime.now(),
            total_volume_at_level=volume,
            pattern_multiplier=pattern_multiplier
        )
        
        if zone_type == 'SUPPLY':
            self.supply_zones.append(level)
            self.supply_zones.sort(key=lambda x: x.price)
        else:
            self.demand_zones.append(level)
            self.demand_zones.sort(key=lambda x: x.price, reverse=True)
        
        return level
    
    def get_nearest_zones(self, current_price: float) -> Tuple[Optional[InstitutionalLevel], 
                                                                Optional[InstitutionalLevel]]:
        """Get nearest supply (above) and demand (below) zones"""
        nearest_supply = None
        nearest_demand = None
        
        for zone in self.supply_zones:
            if zone.price > current_price:
                nearest_supply = zone
                break
        
        for zone in self.demand_zones:
            if zone.price < current_price:
                nearest_demand = zone
                break
        
        return nearest_supply, nearest_demand
    
    def update_from_candles(self, candles: List[Dict]):
        """Update zones from candle data"""
        for candle in candles:
            self.candle_history.append(candle)
            
            # Detect swing highs for supply
            if len(self.candle_history) >= 5:
                self._detect_swing_zones()
        
        if len(self.candle_history) > 200:
            self.candle_history = self.candle_history[-200:]
        
        self._decay_zones()
    
    def _detect_swing_zones(self):
        """Detect supply/demand zones from swing points"""
        if len(self.candle_history) < 5:
            return
        
        current = self.candle_history[-3]
        left = self.candle_history[-4]
        right = self.candle_history[-2]
        
        if current['high'] > left['high'] and current['high'] > right['high']:
            self.add_zone(current['high'], 'SUPPLY', current.get('volume', 10000))
        
        if current['low'] < left['low'] and current['low'] < right['low']:
            self.add_zone(current['low'], 'DEMAND', current.get('volume', 10000))
    
    def _decay_zones(self):
        """Remove old, weak zones"""
        self.supply_zones = [z for z in self.supply_zones if z.current_strength > 10]
        self.demand_zones = [z for z in self.demand_zones if z.current_strength > 10]
    
    # ============================================================
    # FIX: ADAPTIVE THRESHOLD
    # ============================================================
    
    def _get_adaptive_manipulation_threshold(self, volatility: float) -> float:
        """
        Calculate adaptive threshold based on volatility.
        Higher volatility → higher threshold (need more confirmation)
        """
        if volatility < 0.005:
            return 0.55  # Low volatility - easier to detect
        elif volatility < 0.015:
            return 0.60  # Normal volatility - default
        elif volatility < 0.03:
            return 0.65  # High volatility - need more confirmation
        else:
            return 0.70  # Extreme volatility - need strong confirmation
    
    # ============================================================
    # MULTI-TIMEFRAME ALIGNMENT
    # ============================================================
    
    def get_mtf_alignment(self, signal_data: Dict) -> float:
        """Get multi-timeframe alignment (C_mtf)"""
        weekly = signal_data.get('weekly_trend', 'neutral')
        daily = signal_data.get('daily_trend', 'neutral')
        
        if weekly == 'neutral' or daily == 'neutral':
            return 0.5
        elif weekly == daily:
            return 1.0
        else:
            return 0.0
    
    # ============================================================
    # MAIN ANALYSIS (FIXED)
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Complete analysis using:
        1. Volume profile (with Agent_J)
        2. Monte Carlo simulations
        3. Manipulation detection
        4. Velocity Filter
        5. Adaptive Threshold
        """
        # ===== FIX: Get symbol =====
        symbol = signal_data.get('symbol', 'UNKNOWN')
        
        # ===== FIX: Get price with fallback =====
        price = signal_data.get('price', 0)
        if price <= 0:
            price = self.get_current_price(symbol)
        
        if price <= 0:
            return self._hold_response(f"No price available for {symbol}")
        
        current_price = price
        current_volume = signal_data.get('volume', 10000)
        
        # ===== VELOCITY FILTER CHECK =====
        velocity_result = self.velocity_filter.update(current_price)
        
        # Get nearest zones
        nearest_supply, nearest_demand = self.get_nearest_zones(current_price)
        
        # Determine active level
        active_level = None
        level_type = None
        direction = None
        
        if nearest_demand and current_price <= nearest_demand.price * 1.005:
            active_level = nearest_demand
            level_type = 'DEMAND'
            direction = 'BUY'
        elif nearest_supply and current_price >= nearest_supply.price * 0.995:
            active_level = nearest_supply
            level_type = 'SUPPLY'
            direction = 'SELL'
        
        if not active_level:
            return self._hold_response("No active S/R level nearby")
        
        # 1. Volume ratio from Agent_J
        volume_ratio = self.get_volume_ratio(current_volume)
        
        # 2. Hesitation bars
        hesitation_bars = self._calculate_hesitation_bars(active_level.price, direction)
        
        # 3. MTF alignment
        mtf_alignment = self.get_mtf_alignment(signal_data)
        
        # 4. ADAPTIVE THRESHOLD
        volatility = signal_data.get('volatility', 0.01)
        adaptive_threshold = self._get_adaptive_manipulation_threshold(volatility)
        
        # 5. Manipulation score (M) with adaptive threshold
        m_score, signal, reasoning = self.manipulation_detector.detect(
            volume_ratio=volume_ratio,
            hesitation_bars=hesitation_bars,
            mtf_alignment=mtf_alignment,
            threshold=adaptive_threshold
        )
        
        # 6. Monte Carlo breakout simulation
        mc_result = self.monte_carlo.simulate_breakout_probability(
            current_price=current_price,
            supply_price=nearest_supply.price if nearest_supply else None,
            demand_price=nearest_demand.price if nearest_demand else None,
            volatility=volatility
        )
        
        # 7. Combine with Monte Carlo
        if mc_result['probabilities']['breakout_up'] > 60:
            mc_vote = 'BUY'
            mc_confidence = mc_result['probabilities']['breakout_up']
        elif mc_result['probabilities']['breakout_down'] > 60:
            mc_vote = 'SELL'
            mc_confidence = mc_result['probabilities']['breakout_down']
        else:
            mc_vote = 'HOLD'
            mc_confidence = mc_result['probabilities']['bounce']
        
        # 8. Velocity Filter check
        if velocity_result['momentum'] == 'RISING' and direction == 'SELL':
            if velocity_result['is_accelerating']:
                return self._hold_response("Velocity rising - selling against momentum")
        elif velocity_result['momentum'] == 'FALLING' and direction == 'BUY':
            if velocity_result['is_accelerating']:
                return self._hold_response("Velocity falling - buying against momentum")
        
        # 9. Final decision
        if signal == TradeSignal.GENUINE:
            if direction == mc_vote or mc_vote == 'HOLD':
                final_vote = direction
                final_confidence = min(95, 70 + m_score * 30)
                position_size = 1.0
            else:
                final_vote = 'HOLD'
                final_confidence = 50
                position_size = 0
                reasoning = f"⚠️ Monte Carlo conflict: {direction} vs {mc_vote}"
        elif signal == TradeSignal.UNCERTAIN:
            final_vote = direction if mc_vote == direction else 'HOLD'
            final_confidence = 50
            position_size = 0.5
        else:
            final_vote = 'HOLD'
            final_confidence = 30
            position_size = 0
        
        # Hidden funds estimate
        hidden_funds = active_level.hidden_funds(
            volume=current_volume,
            reversal_strength=active_level.reversal_pattern_score
        )
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': final_vote,
            'confidence': round(final_confidence, 1),
            'reasoning': f"{reasoning} | MC: {mc_result['probabilities']['breakout_up']:.0f}% up, {mc_result['probabilities']['breakout_down']:.0f}% down",
            'position_size': position_size,
            'is_genuine': signal == TradeSignal.GENUINE,
            'manipulation_score': round(m_score, 3),
            'level_info': {
                'price': active_level.price,
                'type': level_type,
                'strength': round(active_level.current_strength, 1),
                'touches': active_level.touches
            },
            'monte_carlo': mc_result['probabilities'],
            'hidden_funds_estimate': round(hidden_funds, 0),
            'velocity': velocity_result,
            'adaptive_threshold': adaptive_threshold
        }
    
    def _calculate_hesitation_bars(self, level_price: float, direction: str) -> int:
        """Calculate bars until reversal after touch"""
        if len(self.candle_history) < 5:
            return 1
        
        bars = 0
        touched = False
        
        for candle in reversed(self.candle_history[-10:]):
            if direction == 'BUY':
                touched_candle = candle['low'] <= level_price
            else:
                touched_candle = candle['high'] >= level_price
            
            if touched_candle and not touched:
                touched = True
                bars = 0
            elif touched:
                bars += 1
                
                if direction == 'BUY':
                    reversed_candle = candle['close'] > candle['open'] and candle['close'] > level_price
                else:
                    reversed_candle = candle['close'] < candle['open'] and candle['close'] < level_price
                
                if reversed_candle:
                    return min(3, bars)
        
        return 3
    
    def _hold_response(self, reason: str) -> Dict:
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': reason,
            'position_size': 0,
            'is_genuine': False,
            'manipulation_score': 0,
            'level_info': None,
            'monte_carlo': None,
            'hidden_funds_estimate': 0,
            'velocity': None,
            'adaptive_threshold': None
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for price direction."""
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
    
    def update_from_agent_j(self, volume_data: Dict):
        """Receive volume data from Agent_J (Volume Master)"""
        self.volume_history.append(volume_data.get('current_volume', 10000))
        if len(self.volume_history) > 20:
            self.volume_history.pop(0)
        self.avg_volume = sum(self.volume_history) / len(self.volume_history)
        self.volume_surge_detected = volume_data.get('volume_surge', False)