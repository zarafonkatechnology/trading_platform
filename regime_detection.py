"""
Market Regime Detection Module
- Identifies trending vs ranging markets
- Uses ADX, ATR ratio, and efficiency ratio
- Provides regime confidence score
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """Market regime types."""
    STRONG_TRENDING = "STRONG_TRENDING"      # ADX > 40
    TRENDING = "TRENDING"                    # ADX 25-40
    WEAK_TRENDING = "WEAK_TRENDING"          # ADX 20-25
    MIXED = "MIXED"                          # ADX 18-22, conflicting signals
    RANGING_WEAK = "RANGING_WEAK"            # ADX 15-18
    RANGING = "RANGING"                      # ADX < 15
    CHOPPY = "CHOPPY"                        # ADX < 20 + high volatility


@dataclass
class RegimeInfo:
    """Container for regime detection results."""
    regime: MarketRegime
    adx: float
    efficiency_ratio: float
    volatility_ratio: float
    trend_strength: float          # 0-100
    confidence: float              # 0-100
    direction: str                 # 'UP', 'DOWN', or 'SIDEWAYS'
    description: str


class RegimeDetector:
    """
    Market regime detection using multiple indicators:
    - ADX (Average Directional Index) for trend strength
    - Efficiency Ratio for price efficiency
    - ATR ratio for volatility expansion/contraction
    - Price relative to moving averages
    """
    
    def __init__(self, adx_period: int = 14, ma_period: int = 50):
        """
        Args:
            adx_period: Period for ADX calculation (default 14)
            ma_period: Period for moving averages (default 50)
        """
        self.adx_period = adx_period
        self.ma_period = ma_period
        self.history = []  # Store recent regime changes
    
    def calculate_adx(self, high: List[float], low: List[float], 
                      close: List[float]) -> float:
        """
        Calculate Average Directional Index (ADX).
        
        ADX > 25 = Trending
        ADX < 20 = Ranging
        """
        if len(close) < self.adx_period + 1:
            return 20.0
        
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(close)):
            # True Range
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
            
            # Directional Movement
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        # Smooth with Wilder's smoothing (similar to EMA)
        atr = self._wilders_smoothing(tr_list, self.adx_period)
        smooth_plus_dm = self._wilders_smoothing(plus_dm_list, self.adx_period)
        smooth_minus_dm = self._wilders_smoothing(minus_dm_list, self.adx_period)
        
        if atr == 0:
            return 20.0
        
        plus_di = 100 * smooth_plus_dm / atr
        minus_di = 100 * smooth_minus_dm / atr
        
        # Directional Index
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        
        # ADX is smoothed DX
        adx = self._wilders_smoothing([dx] * self.adx_period, self.adx_period)
        
        return min(100, max(0, adx))
    
    def _wilders_smoothing(self, values: List[float], period: int) -> float:
        """Wilder's smoothing (used in ADX calculation)."""
        if len(values) < period:
            return np.mean(values) if values else 0
        
        # First average
        smoothing = np.mean(values[:period])
        
        # Subsequent values
        for i in range(period, len(values)):
            smoothing = (smoothing * (period - 1) + values[i]) / period
        
        return smoothing
    
    def calculate_efficiency_ratio(self, prices: List[float], period: int = 10) -> float:
        """
        Calculate Efficiency Ratio (Kaufman's Efficiency Ratio).
        
        ER = (net change) / (sum of absolute changes)
        ER = 1 = perfectly trending
        ER = 0 = perfectly ranging
        """
        if len(prices) < period + 1:
            return 0.5
        
        net_change = abs(prices[-1] - prices[-period])
        gross_change = sum(abs(prices[i] - prices[i-1]) for i in range(-period, 0))
        
        if gross_change == 0:
            return 0.5
        
        return net_change / gross_change
    
    def calculate_volatility_ratio(self, atr: float, prev_atr: float) -> float:
        """Calculate volatility expansion/contraction ratio."""
        if prev_atr == 0:
            return 1.0
        return atr / prev_atr
    
    def get_trend_direction(self, prices: List[float]) -> str:
        """Determine trend direction based on moving averages."""
        if len(prices) < self.ma_period + 10:
            return 'SIDEWAYS'
        
        # Simple MA
        ma_short = np.mean(prices[-20:])
        ma_long = np.mean(prices[-self.ma_period:])
        
        # Price vs MA
        current_price = prices[-1]
        price_above_ma = current_price > ma_long
        
        # Slope of MA
        ma_slope = (ma_short - ma_long) / ma_long
        
        if ma_slope > 0.002 and price_above_ma:
            return 'UP'
        elif ma_slope < -0.002 and not price_above_ma:
            return 'DOWN'
        else:
            return 'SIDEWAYS'
    
    def detect_regime(self, candles: List[Dict]) -> RegimeInfo:
        """
        Detect current market regime from candle data.
        
        Args:
            candles: List of candles with 'high', 'low', 'close'
        
        Returns:
            RegimeInfo with regime type and confidence
        """
        if len(candles) < 60:
            return RegimeInfo(
                regime=MarketRegime.MIXED,
                adx=20.0,
                efficiency_ratio=0.5,
                volatility_ratio=1.0,
                trend_strength=50,
                confidence=30,
                direction='SIDEWAYS',
                description="Insufficient data"
            )
        
        # Extract price series
        high = [c['high'] for c in candles]
        low = [c['low'] for c in candles]
        close = [c['close'] for c in candles]
        
        # Calculate indicators
        adx = self.calculate_adx(high, low, close)
        er = self.calculate_efficiency_ratio(close, period=20)
        
        # Calculate ATR for volatility
        tr_list = []
        for i in range(1, len(close)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr_list.append(max(hl, hc, lc))
        
        atr = np.mean(tr_list[-14:]) if len(tr_list) >= 14 else 0.001
        prev_atr = np.mean(tr_list[-28:-14]) if len(tr_list) >= 28 else atr
        vol_ratio = self.calculate_volatility_ratio(atr, prev_atr)
        
        # Determine direction
        direction = self.get_trend_direction(close)
        
        # Determine regime
        if adx > 40:
            regime = MarketRegime.STRONG_TRENDING
            trend_strength = min(100, adx)
            confidence = min(95, 60 + (adx - 40) * 1.5)
        elif adx > 25:
            regime = MarketRegime.TRENDING
            trend_strength = min(90, 50 + (adx - 25) * 1.5)
            confidence = min(85, 55 + (adx - 25))
        elif adx > 20:
            regime = MarketRegime.WEAK_TRENDING
            trend_strength = 45 + (adx - 20) * 5
            confidence = 50 + (adx - 20) * 3
        elif adx > 15:
            regime = MarketRegime.RANGING_WEAK
            trend_strength = 35 - (20 - adx) * 3
            confidence = 45 - (20 - adx) * 3
        elif vol_ratio > 1.2:
            regime = MarketRegime.CHOPPY
            trend_strength = 20
            confidence = 40
        else:
            regime = MarketRegime.RANGING
            trend_strength = 20
            confidence = 50
        
        # Adjust confidence based on efficiency ratio
        if regime in [MarketRegime.TRENDING, MarketRegime.STRONG_TRENDING]:
            confidence = min(95, confidence * (0.5 + er))
        elif regime in [MarketRegime.RANGING, MarketRegime.RANGING_WEAK]:
            confidence = min(90, confidence * (1.5 - er))
        
        # Adjust for volatility expansion/contraction
        if vol_ratio > 1.5:
            confidence = min(95, confidence * 1.1)
        elif vol_ratio < 0.7:
            confidence = min(95, confidence * 0.9)
        
        # Description
        descriptions = {
            MarketRegime.STRONG_TRENDING: f"Strong {direction} trend with high momentum",
            MarketRegime.TRENDING: f"Clear {direction} trend, favorable for trend-following",
            MarketRegime.WEAK_TRENDING: f"Weak {direction} trend, use caution",
            MarketRegime.MIXED: "Mixed signals, reduce position size",
            MarketRegime.RANGING_WEAK: "Weak ranging, wait for breakout",
            MarketRegime.RANGING: "Ranging market, favor mean reversion",
            MarketRegime.CHOPPY: "Choppy market with high volatility, stay cautious"
        }
        
        description = descriptions.get(regime, "Unknown regime")
        
        # Store in history
        self.history.append({
            'timestamp': datetime.now(),
            'regime': regime.value,
            'adx': round(adx, 1),
            'confidence': round(confidence, 1)
        })
        
        # Keep last 100 history entries
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return RegimeInfo(
            regime=regime,
            adx=round(adx, 1),
            efficiency_ratio=round(er, 3),
            volatility_ratio=round(vol_ratio, 2),
            trend_strength=round(trend_strength, 1),
            confidence=round(confidence, 1),
            direction=direction,
            description=description
        )
    
    def get_regime_multiplier(self, regime: MarketRegime) -> float:
        """
        Get position size multiplier based on regime.
        
        Returns:
            Multiplier between 0.25 and 1.0
        """
        multipliers = {
            MarketRegime.STRONG_TRENDING: 1.0,
            MarketRegime.TRENDING: 0.9,
            MarketRegime.WEAK_TRENDING: 0.7,
            MarketRegime.MIXED: 0.5,
            MarketRegime.RANGING_WEAK: 0.4,
            MarketRegime.RANGING: 0.3,
            MarketRegime.CHOPPY: 0.25
        }
        return multipliers.get(regime, 0.5)
    
    def get_strategy_recommendation(self, regime: MarketRegime) -> Dict:
        """
        Get trading strategy recommendation based on regime.
        """
        recommendations = {
            MarketRegime.STRONG_TRENDING: {
                'primary_agents': ['Agent_A', 'Agent_K', 'Agent_C'],
                'avoid_agents': ['Agent_B'],
                'position_multiplier': 1.0,
                'stop_loss_multiplier': 1.2,
                'take_profit_multiplier': 1.5,
                'comment': 'Favor trend-following, let profits run'
            },
            MarketRegime.TRENDING: {
                'primary_agents': ['Agent_A', 'Agent_K'],
                'avoid_agents': ['Agent_B'],
                'position_multiplier': 0.9,
                'stop_loss_multiplier': 1.1,
                'take_profit_multiplier': 1.3,
                'comment': 'Trend-following preferred'
            },
            MarketRegime.RANGING: {
                'primary_agents': ['Agent_B', 'Agent_R'],
                'avoid_agents': ['Agent_A', 'Agent_K'],
                'position_multiplier': 0.5,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 0.8,
                'comment': 'Mean reversion, take quick profits'
            },
            MarketRegime.CHOPPY: {
                'primary_agents': [],
                'avoid_agents': ['ALL'],
                'position_multiplier': 0.25,
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 1.0,
                'comment': 'High volatility, reduce or avoid trading'
            },
            MarketRegime.MIXED: {
                'primary_agents': ['Agent_W'],
                'avoid_agents': [],
                'position_multiplier': 0.6,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'comment': 'Mixed signals, use consensus agent'
            }
        }
        
        return recommendations.get(regime, recommendations[MarketRegime.MIXED])


# ============================================================
# Helper Functions for Integration
# ============================================================

def fetch_candles_for_regime(asset: str, count: int = 100, granularity: str = "H1") -> List[Dict]:
    """
    Fetch candles for regime detection.
    Replace with your actual data source.
    """
    # This should integrate with your OANDA bridge
    # For now, returns simulated data
    import random
    candles = []
    price = 100.0
    for i in range(count):
        change = random.gauss(0, 0.005)
        price = price * (1 + change)
        candles.append({
            'high': price * (1 + abs(random.gauss(0, 0.002))),
            'low': price * (1 - abs(random.gauss(0, 0.002))),
            'close': price
        })
    return candles


def get_regime_for_asset(asset: str) -> RegimeInfo:
    """
    Get regime info for an asset.
    """
    detector = RegimeDetector()
    candles = fetch_candles_for_regime(asset)
    return detector.detect_regime(candles)


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    from datetime import datetime
    import random
    
    print("=" * 60)
    print("MARKET REGIME DETECTION - TEST")
    print("=" * 60)
    
    detector = RegimeDetector()
    
    # Generate synthetic data for different regimes
    regimes_to_test = [
        ("Strong Trending (ADX > 40)", "trending"),
        ("Ranging (ADX < 20)", "ranging"),
        ("Volatile/Choppy", "choppy")
    ]
    
    for name, regime_type in regimes_to_test:
        print(f"\n📊 {name}")
        print("-" * 40)
        
        # Generate synthetic candles
        candles = []
        price = 100.0
        
        for i in range(100):
            if regime_type == "trending":
                # Trending: consistent upward movement
                change = 0.002 + random.gauss(0, 0.003)
            elif regime_type == "ranging":
                # Ranging: mean-reverting
                if i < 50:
                    change = random.gauss(0, 0.002)
                else:
                    change = random.gauss(0, 0.002)
            else:
                # Choppy: high volatility
                change = random.gauss(0, 0.01)
            
            price = price * (1 + change)
            candles.append({
                'high': price * (1 + abs(random.gauss(0, 0.002))),
                'low': price * (1 - abs(random.gauss(0, 0.002))),
                'close': price
            })
        
        result = detector.detect_regime(candles)
        
        print(f"   Regime: {result.regime.value}")
        print(f"   ADX: {result.adx}")
        print(f"   Efficiency Ratio: {result.efficiency_ratio}")
        print(f"   Trend Strength: {result.trend_strength}%")
        print(f"   Confidence: {result.confidence}%")
        print(f"   Direction: {result.direction}")
        print(f"   Description: {result.description}")
        
        rec = detector.get_strategy_recommendation(result.regime)
        print(f"   Strategy: {rec['comment']}")
        print(f"   Position Multiplier: {rec['position_multiplier']}")
    
    print("\n" + "=" * 60)
    print("✅ Regime Detection Ready")
    print("=" * 60)
