"""
Adaptive Position Sizing Module
- Kelly Criterion
- Fractional Kelly (conservative)
- Volatility-based adjustment
- Regime-based scaling
"""

import math
import json
import os
from typing import Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class PositionSizingConfig:
    """Configuration for position sizing."""
    kelly_fraction: float = 0.25          # Use 25% of full Kelly (conservative)
    max_position_pct: float = 0.25        # Maximum 25% of capital per trade
    min_position_pct: float = 0.01        # Minimum 1% of capital
    volatility_cap: float = 2.0           # Reduce size when vol > 2x average
    confidence_threshold: float = 0.60    # Minimum confidence to trade


class KellyCalculator:
    """
    Kelly Criterion for optimal position sizing.
    
    Full Kelly: f* = (p * b - q) / b
    where:
        p = probability of winning
        q = probability of losing (1 - p)
        b = odds received on the bet (profit / loss ratio)
    """
    
    @staticmethod
    def full_kelly(win_prob: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate full Kelly percentage.
        
        Args:
            win_prob: Historical win rate (0-1)
            avg_win: Average winning trade return (%)
            avg_loss: Average losing trade return (%)
        
        Returns:
            Optimal fraction of capital to risk
        """
        if avg_loss == 0:
            return 0.0
        
        # Odds (b) = average win / average loss
        b = avg_win / avg_loss if avg_loss > 0 else 0
        
        q = 1 - win_prob
        
        if b <= 0:
            return 0.0
        
        kelly = (win_prob * b - q) / b
        return max(0.0, min(0.5, kelly))  # Cap at 50%
    
    @staticmethod
    def fractional_kelly(win_prob: float, avg_win: float, avg_loss: float, 
                         fraction: float = 0.25) -> float:
        """
        Calculate Fractional Kelly (more conservative).
        
        Args:
            fraction: Fraction of full Kelly to use (0.1-0.5)
        """
        full = KellyCalculator.full_kelly(win_prob, avg_win, avg_loss)
        return full * fraction


class AdaptivePositionSizer:
    """
    Combines Kelly Criterion with:
    - Volatility adjustment
    - Regime-based scaling
    - Confidence multiplier
    - Daily loss limit
    """
    
    def __init__(self, config: PositionSizingConfig = None):
        self.config = config or PositionSizingConfig()
        self.daily_pnl = 0.0
        self.current_date = date.today()
        self.trades_today = 0
        self.history_file = "position_history.json"
        self._load_history()
    
    def _load_history(self):
        """Load historical daily PnL."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.daily_pnl = data.get('daily_pnl', 0.0)
                    self.trades_today = data.get('trades_today', 0)
            except:
                pass
    
    def _save_history(self):
        """Save daily PnL."""
        with open(self.history_file, 'w') as f:
            json.dump({
                'daily_pnl': self.daily_pnl,
                'trades_today': self.trades_today,
                'last_date': self.current_date.isoformat()
            }, f)
    
    def _reset_daily_if_needed(self):
        """Reset daily counters at midnight."""
        today = date.today()
        if today != self.current_date:
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.current_date = today
            self._save_history()
    
    def get_win_probability(self, agent_votes: Dict, historical_win_rates: Dict) -> float:
        """
        Calculate dynamic win probability from agent consensus.
        
        Args:
            agent_votes: Dictionary of agent votes with confidence
            historical_win_rates: Dictionary of agent_name -> win_rate
        """
        if not agent_votes:
            return 0.5
        
        # Weighted average of agent win rates
        total_weight = 0
        weighted_win = 0
        
        for agent_name, vote_data in agent_votes.items():
            weight = vote_data.get('confidence', 50) / 100
            win_rate = historical_win_rates.get(agent_name, 0.5)
            
            total_weight += weight
            weighted_win += win_rate * weight
        
        if total_weight == 0:
            return 0.5
        
        return weighted_win / total_weight
    
    def get_volatility_multiplier(self, current_atr: float, avg_atr: float) -> float:
        """
        Calculate volatility-based position multiplier.
        
        Returns:
            Multiplier between 0.25 and 1.5
        """
        if avg_atr <= 0:
            return 1.0
        
        vol_ratio = current_atr / avg_atr
        
        if vol_ratio > self.config.volatility_cap:
            return 0.25  # Very high volatility → tiny positions
        elif vol_ratio > 1.5:
            return 0.5
        elif vol_ratio > 1.2:
            return 0.75
        elif vol_ratio < 0.7:
            return 1.2  # Low volatility → slightly larger positions
        else:
            return 1.0
    
    def get_regime_multiplier(self, regime: str) -> float:
        """
        Get position multiplier based on market regime.
        
        Regimes:
            'TRENDING' → Full size
            'MIXED' → Reduced size
            'RANGING' → Half size
        """
        regime_map = {
            'TRENDING': 1.0,
            'TRENDING_WEAK': 0.8,
            'MIXED': 0.6,
            'RANGING_WEAK': 0.5,
            'RANGING': 0.4
        }
        return regime_map.get(regime, 0.6)
    
    def get_confidence_multiplier(self, confidence: float) -> float:
        """
        Scale position by confidence level.
        
        Confidence below threshold = no trade
        """
        if confidence < self.config.confidence_threshold:
            return 0.0
        
        # Linear scaling from threshold to 1.0
        if confidence >= 0.85:
            return 1.0
        else:
            return (confidence - self.config.confidence_threshold) / (0.85 - self.config.confidence_threshold)
    
    def calculate_position(self,
                          win_prob: float,
                          avg_win: float,
                          avg_loss: float,
                          confidence: float,
                          current_atr: float,
                          avg_atr: float,
                          regime: str,
                          force_trade: bool = False) -> Dict:
        """
        Calculate final position size.
        
        Returns:
            Dictionary with position size and all components
        """
        self._reset_daily_if_needed()
        
        # 1. Base Kelly size
        kelly_pct = KellyCalculator.fractional_kelly(
            win_prob, avg_win, avg_loss, self.config.kelly_fraction
        )
        
        # 2. Confidence multiplier (0 to 1)
        confidence_mult = self.get_confidence_multiplier(confidence)
        
        # 3. Volatility multiplier
        vol_mult = self.get_volatility_multiplier(current_atr, avg_atr)
        
        # 4. Regime multiplier
        regime_mult = self.get_regime_multiplier(regime)
        
        # 5. Daily loss penalty
        daily_penalty = 1.0
        if self.daily_pnl < -0.01:  # Down 1%
            daily_penalty = 0.5
        elif self.daily_pnl < -0.015:  # Down 1.5%
            daily_penalty = 0.25
        elif self.daily_pnl < -0.02:  # Down 2%
            daily_penalty = 0.0  # Stop trading
        
        # Final position size
        raw_size = kelly_pct * confidence_mult * vol_mult * regime_mult * daily_penalty
        
        # Apply min/max caps
        final_size = max(
            self.config.min_position_pct,
            min(self.config.max_position_pct, raw_size)
        )
        
        # Override for forced trades (e.g., very high confidence)
        if force_trade and final_size < self.config.min_position_pct:
            final_size = self.config.min_position_pct
        
        return {
            'position_size': round(final_size, 3),
            'position_percent': round(final_size * 100, 1),
            'components': {
                'kelly_base': round(kelly_pct * 100, 1),
                'confidence_mult': round(confidence_mult, 2),
                'volatility_mult': round(vol_mult, 2),
                'regime_mult': round(regime_mult, 2),
                'daily_penalty': round(daily_penalty, 2)
            },
            'kelly_pct': round(kelly_pct, 3),
            'confidence': round(confidence, 2),
            'win_probability': round(win_prob, 2)
        }
    
    def record_trade_result(self, pnl_pct: float):
        """Record trade result for daily loss tracking."""
        self.daily_pnl += pnl_pct
        self.trades_today += 1
        self._save_history()
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed."""
        self._reset_daily_if_needed()
        if self.daily_pnl < -0.02:  # -2% daily limit
            return False, f"Daily loss limit reached: {self.daily_pnl*100:.2f}%"
        return True, "OK"
    
    def get_status(self) -> Dict:
        """Get current risk status."""
        self._reset_daily_if_needed()
        return {
            'daily_pnl': round(self.daily_pnl * 100, 2),
            'trades_today': self.trades_today,
            'daily_limit': 2.0,
            'can_trade': self.daily_pnl >= -0.02,
            'max_position': round(self.config.max_position_pct * 100, 1)
        }


# ============================================================
# Example Usage and Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ADAPTIVE POSITION SIZING - TEST")
    print("=" * 60)
    
    sizer = AdaptivePositionSizer()
    
    # Test scenario 1: Strong trend, high confidence
    print("\n📊 Scenario 1: STRONG TREND, HIGH CONFIDENCE")
    result = sizer.calculate_position(
        win_prob=0.65,
        avg_win=0.02,
        avg_loss=0.01,
        confidence=0.92,
        current_atr=0.0015,
        avg_atr=0.0012,
        regime='TRENDING'
    )
    print(f"   Position Size: {result['position_percent']}%")
    print(f"   Components: {result['components']}")
    
    # Test scenario 2: Ranging market, low confidence
    print("\n📊 Scenario 2: RANGING MARKET, LOW CONFIDENCE")
    result = sizer.calculate_position(
        win_prob=0.52,
        avg_win=0.015,
        avg_loss=0.012,
        confidence=0.68,
        current_atr=0.0020,
        avg_atr=0.0010,
        regime='RANGING'
    )
    print(f"   Position Size: {result['position_percent']}%")
    print(f"   Components: {result['components']}")
    
    # Test scenario 3: After a loss (daily penalty)
    print("\n📊 Scenario 3: AFTER A LOSS (DAILY PENALTY)")
    sizer.record_trade_result(-0.015)
    result = sizer.calculate_position(
        win_prob=0.60,
        avg_win=0.02,
        avg_loss=0.01,
        confidence=0.85,
        current_atr=0.0015,
        avg_atr=0.0012,
        regime='TRENDING'
    )
    print(f"   Position Size: {result['position_percent']}%")
    print(f"   Components: {result['components']}")
    print(f"   Daily P&L: {sizer.get_status()['daily_pnl']}%")
