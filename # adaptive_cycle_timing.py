"""
Adaptive Cycle Timing Module
- Dynamically adjusts cycle duration based on volatility and regime
- Faster cycles in high volatility, slower in low volatility
- Prevents overtrading in quiet markets and missed opportunities in volatile ones
"""

import time
import math
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import threading


@dataclass
class CycleConfig:
    """Configuration for adaptive cycle timing."""
    # Base cycle times (in seconds)
    min_cycle_seconds: int = 60       # 1 minute minimum
    max_cycle_seconds: int = 900      # 15 minutes maximum
    default_cycle_seconds: int = 300  # 5 minutes default
    
    # Volatility thresholds (ATR percentage of price)
    very_high_volatility: float = 0.02   # 2% - very fast cycles
    high_volatility: float = 0.015       # 1.5% - fast cycles
    medium_volatility: float = 0.01      # 1% - normal cycles
    low_volatility: float = 0.005        # 0.5% - slow cycles
    
    # Regime multipliers
    regime_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'STRONG_TRENDING': 0.7,   # Faster cycles in strong trends
        'TRENDING': 0.8,
        'WEAK_TRENDING': 0.9,
        'MIXED': 1.0,
        'RANGING_WEAK': 1.2,
        'RANGING': 1.3,
        'CHOPPY': 1.5
    })
    
    # Performance adjustments
    max_drawdown_multiplier: float = 1.5      # Slower cycles after drawdown
    consecutive_losses_multiplier: float = 1.3  # Slower after losses


class AdaptiveCycleTimer:
    """
    Dynamically adjusts cycle timing based on:
    - Current market volatility
    - Market regime (trending/ranging)
    - Recent performance (drawdowns)
    - Time of day (optional)
    """
    
    def __init__(self, config: Optional[CycleConfig] = None):
        self.config = config or CycleConfig()
        self.volatility_history = deque(maxlen=20)
        self.cycle_history = deque(maxlen=50)
        self.last_cycle_time: Optional[datetime] = None
        self.consecutive_losses = 0
        self.current_drawdown = 0.0
        self.lock = threading.Lock()
    
    def calculate_volatility(self, candles: list, atr_period: int = 14) -> float:
        """
        Calculate current volatility as ATR percentage of price.
        
        Args:
            candles: List of candles with 'high', 'low', 'close'
            atr_period: Period for ATR calculation
        
        Returns:
            Volatility as percentage (e.g., 0.015 = 1.5%)
        """
        if len(candles) < atr_period + 1:
            return self.config.medium_volatility
        
        # Calculate True Range
        tr_list = []
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        
        # Calculate ATR
        atr = sum(tr_list[-atr_period:]) / atr_period
        
        # Calculate as percentage of current price
        current_price = candles[-1]['close']
        volatility = atr / current_price if current_price > 0 else self.config.medium_volatility
        
        # Update history
        self.volatility_history.append(volatility)
        
        return min(0.05, max(0.002, volatility))  # Clamp between 0.2% and 5%
    
    def get_volatility_tier(self, volatility: float) -> str:
        """Get volatility tier for cycle adjustment."""
        if volatility >= self.config.very_high_volatility:
            return 'VERY_HIGH'
        elif volatility >= self.config.high_volatility:
            return 'HIGH'
        elif volatility >= self.config.medium_volatility:
            return 'MEDIUM'
        elif volatility >= self.config.low_volatility:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def get_voltage_multiplier(self, volatility: float) -> float:
        """
        Get cycle time multiplier based on volatility.
        Higher volatility = faster cycles (lower multiplier)
        """
        tier = self.get_volatility_tier(volatility)
        
        multipliers = {
            'VERY_HIGH': 0.5,   # 50% faster (e.g., 5min -> 2.5min)
            'HIGH': 0.7,        # 30% faster
            'MEDIUM': 1.0,      # normal
            'LOW': 1.3,         # 30% slower
            'VERY_LOW': 1.6     # 60% slower
        }
        
        return multipliers.get(tier, 1.0)
    
    def get_regime_multiplier(self, regime: str) -> float:
        """Get cycle multiplier based on market regime."""
        return self.config.regime_multipliers.get(regime, 1.0)
    
    def get_performance_multiplier(self) -> float:
        """
        Get cycle multiplier based on recent performance.
        Slows down after losses or drawdowns.
        """
        multiplier = 1.0
        
        # Adjust for consecutive losses
        if self.consecutive_losses >= 3:
            multiplier *= self.config.consecutive_losses_multiplier
        elif self.consecutive_losses >= 5:
            multiplier *= (self.config.consecutive_losses_multiplier * 1.2)
        
        # Adjust for drawdown
        if self.current_drawdown > 0.05:  # 5% drawdown
            multiplier *= 1.3
        elif self.current_drawdown > 0.10:  # 10% drawdown
            multiplier *= 1.6
        
        return min(2.0, multiplier)  # Cap at 2x slower
    
    def calculate_cycle_seconds(self, 
                                volatility: float,
                                regime: str,
                                time_of_day: Optional[datetime] = None) -> int:
        """
        Calculate optimal cycle duration in seconds.
        
        Args:
            volatility: Current market volatility (ATR/price)
            regime: Market regime (e.g., 'TRENDING', 'RANGING')
            time_of_day: Current time (for session-based adjustments)
        
        Returns:
            Cycle duration in seconds (between min and max)
        """
        # Start with base cycle
        base_seconds = self.config.default_cycle_seconds
        
        # Apply volatility adjustment
        vol_mult = self.get_voltage_multiplier(volatility)
        
        # Apply regime adjustment
        regime_mult = self.get_regime_multiplier(regime)
        
        # Apply performance adjustment
        perf_mult = self.get_performance_multiplier()
        
        # Calculate raw cycle time
        raw_seconds = base_seconds * vol_mult * regime_mult * perf_mult
        
        # Apply time-of-day adjustments (optional)
        if time_of_day:
            hour = time_of_day.hour
            # Slower during low-liquidity hours
            if hour < 8 or hour > 20:  # Outside peak hours
                raw_seconds *= 1.2
            # Faster during major session overlaps
            if 13 <= hour <= 16:  # London-NY overlap
                raw_seconds *= 0.8
        
        # Clamp to min/max
        final_seconds = max(
            self.config.min_cycle_seconds,
            min(self.config.max_cycle_seconds, int(raw_seconds))
        )
        
        # Store for history
        with self.lock:
            self.cycle_history.append({
                'timestamp': datetime.now(),
                'volatility': volatility,
                'regime': regime,
                'cycle_seconds': final_seconds,
                'components': {
                    'base': base_seconds,
                    'vol_mult': vol_mult,
                    'regime_mult': regime_mult,
                    'perf_mult': perf_mult
                }
            })
        
        return final_seconds
    
    def record_trade_result(self, pnl_percent: float):
        """
        Record trade result for performance adjustment.
        
        Args:
            pnl_percent: Profit/loss percentage (e.g., -0.01 for -1%)
        """
        with self.lock:
            if pnl_percent < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            
            # Update drawdown (simplified)
            if pnl_percent < 0:
                self.current_drawdown += abs(pnl_percent)
            else:
                self.current_drawdown = max(0, self.current_drawdown - pnl_percent)
    
    def get_cycle_info(self, volatility: float, regime: str) -> Dict:
        """Get detailed cycle timing information."""
        cycle_seconds = self.calculate_cycle_seconds(volatility, regime)
        
        return {
            'cycle_seconds': cycle_seconds,
            'cycle_minutes': round(cycle_seconds / 60, 1),
            'volatility': round(volatility * 100, 2),
            'volatility_tier': self.get_volatility_tier(volatility),
            'regime': regime,
            'base_multiplier': self.get_voltage_multiplier(volatility),
            'regime_multiplier': self.get_regime_multiplier(regime),
            'performance_multiplier': self.get_performance_multiplier(),
            'consecutive_losses': self.consecutive_losses,
            'current_drawdown': round(self.current_drawdown * 100, 2),
            'next_cycle_at': (datetime.now() + timedelta(seconds=cycle_seconds)).strftime('%H:%M:%S')
        }
    
    def get_statistics(self) -> Dict:
        """Get cycle timing statistics."""
        with self.lock:
            if not self.cycle_history:
                return {'avg_cycle_seconds': self.config.default_cycle_seconds}
            
            recent_cycles = list(self.cycle_history)[-20:]
            avg_cycle = sum(c['cycle_seconds'] for c in recent_cycles) / len(recent_cycles)
            
            return {
                'avg_cycle_seconds': round(avg_cycle),
                'avg_cycle_minutes': round(avg_cycle / 60, 1),
                'min_cycle': min(c['cycle_seconds'] for c in recent_cycles),
                'max_cycle': max(c['cycle_seconds'] for c in recent_cycles),
                'total_cycles': len(self.cycle_history),
                'consecutive_losses': self.consecutive_losses,
                'current_drawdown': round(self.current_drawdown * 100, 2)
            }


class AdaptiveScheduler:
    """
    Scheduler that adapts its interval based on market conditions.
    Wrapper around schedule library with dynamic interval adjustment.
    """
    
    def __init__(self, cycle_timer: AdaptiveCycleTimer):
        self.cycle_timer = cycle_timer
        self.current_interval = cycle_timer.config.default_cycle_seconds
        self.last_run = None
        self.is_running = False
        self._thread = None
    
    def should_run(self, volatility: float, regime: str) -> Tuple[bool, int]:
        """
        Determine if enough time has passed since last cycle.
        
        Returns:
            (should_run, seconds_until_next)
        """
        new_interval = self.cycle_timer.calculate_cycle_seconds(volatility, regime)
        
        # Update current interval if changed
        if new_interval != self.current_interval:
            print(f"⏱️ Cycle timing adjusted: {self.current_interval}s → {new_interval}s")
            self.current_interval = new_interval
        
        if self.last_run is None:
            return True, 0
        
        elapsed = (datetime.now() - self.last_run).total_seconds()
        
        if elapsed >= self.current_interval:
            return True, 0
        else:
            return False, self.current_interval - elapsed
    
    def record_run(self):
        """Record that a cycle was executed."""
        self.last_run = datetime.now()
    
    def get_next_run_info(self, volatility: float, regime: str) -> Dict:
        """Get information about when the next cycle will run."""
        should_run, seconds_left = self.should_run(volatility, regime)
        
        return {
            'should_run_now': should_run,
            'seconds_until_next': round(seconds_left),
            'minutes_until_next': round(seconds_left / 60, 1),
            'current_interval_seconds': self.current_interval,
            'current_interval_minutes': round(self.current_interval / 60, 1),
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run_at': (datetime.now() + timedelta(seconds=seconds_left)).strftime('%H:%M:%S') if not should_run else 'NOW'
        }


# ============================================================
# Integration Helper
# ============================================================

def get_adaptive_cycle_info(volatility: float, regime: str) -> Dict:
    """Quick helper to get cycle timing info."""
    timer = AdaptiveCycleTimer()
    return timer.get_cycle_info(volatility, regime)


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ADAPTIVE CYCLE TIMING - TEST")
    print("=" * 60)
    
    timer = AdaptiveCycleTimer()
    scheduler = AdaptiveScheduler(timer)
    
    # Test scenarios
    test_scenarios = [
        ("High Volatility + Trending", 0.018, "STRONG_TRENDING"),
        ("Medium Volatility + Mixed", 0.012, "MIXED"),
        ("Low Volatility + Ranging", 0.004, "RANGING"),
        ("Very Low Volatility + Ranging", 0.002, "RANGING"),
    ]
    
    for name, vol, regime in test_scenarios:
        print(f"\n📊 {name}")
        print("-" * 40)
        
        info = timer.get_cycle_info(vol, regime)
        print(f"   Volatility: {info['volatility']}%")
        print(f"   Regime: {info['regime']}")
        print(f"   Cycle: {info['cycle_minutes']} minutes ({info['cycle_seconds']} seconds)")
        print(f"   Multipliers: Vol={info['base_multiplier']}, Regime={info['regime_multiplier']}, Perf={info['performance_multiplier']}")
        print(f"   Next cycle at: {info['next_cycle_at']}")
    
    # Simulate losses
    print("\n📉 AFTER CONSECUTIVE LOSSES")
    print("-" * 40)
    timer.record_trade_result(-0.01)  # -1%
    timer.record_trade_result(-0.01)  # -1%
    timer.record_trade_result(-0.01)  # -1%
    
    info = timer.get_cycle_info(0.012, "TRENDING")
    print(f"   Consecutive losses: {info['consecutive_losses']}")
    print(f"   Cycle: {info['cycle_minutes']} minutes")
    print(f"   Performance multiplier: {info['performance_multiplier']}")
    
    print("\n" + "=" * 60)
    print("✅ Adaptive Cycle Timing Ready")
    print("=" * 60)
