"""
Manipulation Detection for Institutional S/R
Detects whether a level is genuine or manipulated
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from enum import Enum

class TradeSignal(Enum):
    GENUINE = "✅ GENUINE - Trade"
    MANIPULATION = "⚠️ MANIPULATION - Skip Trade"
    UNCERTAIN = "❓ UNCERTAIN - Reduce Size"

@dataclass
class ManipulationResult:
    """Result of manipulation detection"""
    score: float
    signal: TradeSignal
    volume_score: float
    hesitation_score: float
    alignment_score: float
    reasoning: str


class ManipulationDetector:
    """
    Detects whether a support/resistance level is genuine or manipulated
    Uses the formula: M = 0.4×(V/V_avg) + 0.3×(1 - T/3) + 0.3×C_mtf
    """
    
    # Weights from your specification
    W_VOLUME = 0.4      # Volume ratio weight
    W_HESITATION = 0.3  # Hesitation bars weight
    W_ALIGNMENT = 0.3   # Multi-timeframe alignment weight
    
    # Thresholds
    GENUINE_THRESHOLD = 0.6      # M >= 0.6 = genuine
    VOLUME_MIN_RATIO = 0.5       # V/V_avg must be >= 0.5
    MAX_HESITATION_BARS = 3      # T_hesitation must be < 3
    
    def __init__(self):
        self.detection_history = []
    
    def detect(self, volume_ratio: float, hesitation_bars: int, 
               mtf_alignment: float) -> ManipulationResult:
        """
        Detect if a level is genuine or manipulated
        
        Args:
            volume_ratio: V_level / V_avg (volume at level / average volume)
            hesitation_bars: Number of bars after touch before reversal (T_hesitation)
            mtf_alignment: Multi-timeframe alignment (0 or 1)
        
        Returns:
            ManipulationResult with score and signal
        """
        # Clamp inputs to valid ranges
        volume_ratio = min(2.0, max(0.1, volume_ratio))
        hesitation_bars = min(3, max(0, hesitation_bars))
        mtf_alignment = 1.0 if mtf_alignment >= 0.5 else 0.0
        
        # Calculate individual scores
        volume_score = min(1.0, volume_ratio / 1.0)  # Normalize to 0-1
        hesitation_score = 1 - (hesitation_bars / self.MAX_HESITATION_BARS)
        alignment_score = mtf_alignment
        
        # Apply formula
        m_score = (self.W_VOLUME * volume_score + 
                   self.W_HESITATION * hesitation_score + 
                   self.W_ALIGNMENT * alignment_score)
        
        # Determine signal
        if m_score >= self.GENUINE_THRESHOLD:
            signal = TradeSignal.GENUINE
            reasoning = self._genuine_reasoning(volume_score, hesitation_score, alignment_score)
        elif m_score >= 0.4:
            signal = TradeSignal.UNCERTAIN
            reasoning = self._uncertain_reasoning(volume_score, hesitation_score, alignment_score)
        else:
            signal = TradeSignal.MANIPULATION
            reasoning = self._manipulation_reasoning(volume_score, hesitation_score, alignment_score)
        
        result = ManipulationResult(
            score=round(m_score, 3),
            signal=signal,
            volume_score=round(volume_score, 3),
            hesitation_score=round(hesitation_score, 3),
            alignment_score=round(alignment_score, 3),
            reasoning=reasoning
        )
        
        self.detection_history.append(result)
        return result
    
    def _genuine_reasoning(self, volume_score: float, hesitation_score: float, 
                           alignment_score: float) -> str:
        reasons = []
        if volume_score >= 0.5:
            reasons.append(f"strong volume ({volume_score*100:.0f}%)")
        if hesitation_score >= 0.7:
            reasons.append(f"quick reversal ({hesitation_score*100:.0f}%)")
        if alignment_score >= 0.9:
            reasons.append("multi-timeframe alignment")
        
        return f"✅ GENUINE LEVEL: {', '.join(reasons)}. M = {self._calculate_m(volume_score, hesitation_score, alignment_score):.2f} ≥ 0.6"
    
    def _manipulation_reasoning(self, volume_score: float, hesitation_score: float, 
                                 alignment_score: float) -> str:
        reasons = []
        if volume_score < 0.4:
            reasons.append("low volume at level")
        if hesitation_score < 0.4:
            reasons.append("slow reversal (manipulation suspected)")
        if alignment_score < 0.5:
            reasons.append("timeframe conflict")
        
        return f"⚠️ MANIPULATION DETECTED: {', '.join(reasons)}. M = {self._calculate_m(volume_score, hesitation_score, alignment_score):.2f} < 0.6"
    
    def _uncertain_reasoning(self, volume_score: float, hesitation_score: float, 
                             alignment_score: float) -> str:
        return f"❓ UNCERTAIN: M = {self._calculate_m(volume_score, hesitation_score, alignment_score):.2f} - Reduce position size"
    
    def _calculate_m(self, v: float, h: float, a: float) -> float:
        return (self.W_VOLUME * v + self.W_HESITATION * h + self.W_ALIGNMENT * a)


class VolumeProfileAnalyzer:
    """
    Analyzes volume profile at price levels
    Calculates V_level / V_avg ratio
    """
    
    def __init__(self, lookback_bars: int = 20):
        self.lookback_bars = lookback_bars
        self.volume_history = []
    
    def add_volume(self, volume: float):
        """Add current volume to history"""
        self.volume_history.append(volume)
        if len(self.volume_history) > self.lookback_bars:
            self.volume_history.pop(0)
    
    @property
    def avg_volume(self) -> float:
        """Average volume over lookback period"""
        if not self.volume_history:
            return 10000  # Default
        return sum(self.volume_history) / len(self.volume_history)
    
    def volume_ratio(self, current_volume: float) -> float:
        """Calculate V_level / V_avg"""
        return current_volume / self.avg_volume if self.avg_volume > 0 else 1.0


class HesitationAnalyzer:
    """
    Analyzes hesitation bars (T_hesitation)
    Counts bars after touch before reversal
    """
    
    def __init__(self):
        self.touch_detected = False
        self.bars_since_touch = 0
        self.reversal_detected = False
    
    def update(self, candle: Dict, level_price: float, direction: str):
        """
        Update hesitation analysis
        
        Args:
            candle: Current candle data
            level_price: Price of the S/R level
            direction: 'BUY' for demand, 'SELL' for supply
        """
        # Check if price touched the level
        if direction == 'BUY':
            touched = candle['low'] <= level_price
        else:
            touched = candle['high'] >= level_price
        
        if touched and not self.touch_detected:
            self.touch_detected = True
            self.bars_since_touch = 0
        elif self.touch_detected and not self.reversal_detected:
            self.bars_since_touch += 1
            
            # Check for reversal
            if direction == 'BUY':
                reversed = candle['close'] > candle['open'] and candle['close'] > level_price
            else:
                reversed = candle['close'] < candle['open'] and candle['close'] < level_price
            
            if reversed:
                self.reversal_detected = True
    
    @property
    def hesitation_bars(self) -> int:
        """Number of bars until reversal (T_hesitation)"""
        if not self.reversal_detected:
            return 3  # Max if no reversal yet
        return min(3, self.bars_since_touch)


class MultiTimeframeAnalyzer:
    """
    Analyzes multi-timeframe alignment (C_mtf)
    Returns 1 if weekly + daily agree, 0 otherwise
    """
    
    def __init__(self):
        self.timeframes = ['1H', '4H', 'Daily', 'Weekly']
    
    def get_alignment(self, trends: Dict[str, str]) -> float:
        """
        Get multi-timeframe alignment score
        
        Args:
            trends: Dictionary of timeframe -> trend ('up', 'down', 'neutral')
        
        Returns:
            1.0 if weekly and daily agree, 0.5 if partial, 0.0 if conflict
        """
        weekly = trends.get('Weekly', 'neutral')
        daily = trends.get('Daily', 'neutral')
        
        if weekly == 'neutral' or daily == 'neutral':
            return 0.5
        elif weekly == daily:
            return 1.0
        else:
            return 0.0
