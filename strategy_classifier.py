"""
Strategy Classification System
- Classifies trading signals into strategy types
- Validates signal alignment with market conditions
- Prevents contradictory signals (e.g., SELL on strong uptrend)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from datetime import datetime  # ADD THIS IMPORT


class StrategyType(Enum):
    """Types of trading strategies"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    CONTRARIAN = "contrarian"
    TREND_FOLLOWING = "trend_following"
    RANGE_BOUND = "range_bound"
    SCALP = "scalp"
    POSITION = "position"
    DARK_POOL_FOLLOWING = "dark_pool_following"
    UNDEFINED = "undefined"


class SignalStrength(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    CONTRADICTORY = "CONTRADICTORY"


@dataclass
class ClassificationResult:
    """Result of strategy classification"""
    strategy_type: StrategyType
    strength: SignalStrength
    confidence: float
    reasoning: str
    warnings: list
    suggested_action: str  # BUY, SELL, HOLD, AVOID


class StrategyClassifier:
    """
    Classifies trading signals based on market conditions.
    Ensures signals are consistent with the identified strategy.
    """
    
    def __init__(self):
        self.classification_history = []
    
    def classify(self, market_data: Dict, proposed_action: str) -> ClassificationResult:
        """
        Classify the trading signal into a strategy type.
        
        market_data should contain:
        - price_change_pct: 1-min price change %
        - volume_ratio: current volume / average volume
        - rsi: RSI value (0-100)
        - price_vs_ma: price relative to moving average (-1 to 1)
        - volatility: current volatility %
        - dark_pool_ratio: dark pool volume % (if available)
        - whale_detected: boolean (if available)
        """
        
        price_change = market_data.get('price_change_pct', 0)
        volume_ratio = market_data.get('volume_ratio', 1.0)
        rsi = market_data.get('rsi', 50)
        price_vs_ma = market_data.get('price_vs_ma', 0)
        volatility = market_data.get('volatility', 0.5)
        dark_pool_ratio = market_data.get('dark_pool_ratio', 20)
        whale_detected = market_data.get('whale_detected', False)
        
        warnings = []
        reasoning = []
        
        # Step 1: Determine strategy based on conditions
        strategy = StrategyType.UNDEFINED
        strength = SignalStrength.WEAK
        confidence = 50
        
        # Check for DARK POOL FOLLOWING (whale activity)
        if dark_pool_ratio > 40 or whale_detected:
            strategy = StrategyType.DARK_POOL_FOLLOWING
            confidence = min(90, 60 + dark_pool_ratio * 0.5)
            reasoning.append(f"Dark pool activity at {dark_pool_ratio:.0f}% - following whales")
            if whale_detected:
                reasoning.append("Whale footprint detected")
        
        # Check for MOMENTUM BURST
        elif abs(price_change) > 0.3 and volume_ratio > 1.5:
            strategy = StrategyType.MOMENTUM
            confidence = min(85, 60 + abs(price_change) * 50 + (volume_ratio - 1) * 10)
            reasoning.append(f"Price moved {abs(price_change):.2f}% with {volume_ratio:.1f}x volume")
            if price_change > 0 and proposed_action == 'BUY':
                reasoning.append("Momentum aligned with proposed action")
            elif price_change < 0 and proposed_action == 'SELL':
                reasoning.append("Momentum aligned with proposed action")
            else:
                warnings.append(f"⚠️ Action {proposed_action} contradicts momentum direction")
                confidence -= 20
        
        # Check for MEAN REVERSION
        elif (rsi > 70 or rsi < 30) and volume_ratio < 1.2:
            strategy = StrategyType.MEAN_REVERSION
            confidence = min(80, 60 + abs(rsi - 50))
            reasoning.append(f"RSI at {rsi:.1f} (extreme) - expecting reversal")
            if (rsi > 70 and proposed_action == 'SELL') or (rsi < 30 and proposed_action == 'BUY'):
                reasoning.append("Mean reversion aligned with proposed action")
            else:
                warnings.append(f"⚠️ Action {proposed_action} against mean reversion expectation")
        
        # Check for BREAKOUT
        elif abs(price_vs_ma) > 0.5 and volume_ratio > 1.3:
            strategy = StrategyType.BREAKOUT
            confidence = min(85, 60 + abs(price_vs_ma) * 30)
            reasoning.append(f"Price {abs(price_vs_ma)*100:.0f}% away from MA - breakout")
        
        # Check for CONTRARIAN (opposite to momentum)
        elif ((price_change > 0.2 and proposed_action == 'SELL') or
              (price_change < -0.2 and proposed_action == 'BUY')):
            strategy = StrategyType.CONTRARIAN
            confidence = min(70, 50 + abs(price_change) * 30)
            reasoning.append(f"Contrarian signal - selling into strength / buying into weakness")
            warnings.append("⚠️ CONTRARIAN TRADE - Higher risk, reduce position size")
        
        # Check for TREND FOLLOWING
        elif abs(price_vs_ma) > 0.2 and volume_ratio > 1.1:
            strategy = StrategyType.TREND_FOLLOWING
            confidence = 65
            reasoning.append(f"Trend following - price {'above' if price_vs_ma > 0 else 'below'} MA")
        
        # Default: RANGE BOUND
        else:
            strategy = StrategyType.RANGE_BOUND
            confidence = 50
            reasoning.append("Range bound market - wait for breakout")
        
        # Step 2: Determine signal strength
        if confidence >= 80 and len(warnings) == 0:
            strength = SignalStrength.STRONG
        elif confidence >= 60:
            strength = SignalStrength.MODERATE
        elif len(warnings) >= 2:
            strength = SignalStrength.CONTRADICTORY
        else:
            strength = SignalStrength.WEAK
        
        # Step 3: Determine suggested action based on strategy
        suggested_action = self._get_suggested_action(strategy, market_data, proposed_action)
        
        # Step 4: Final reasoning
        reasoning_text = " | ".join(reasoning)
        if warnings:
            reasoning_text += " | " + " | ".join(warnings)
        
        result = ClassificationResult(
            strategy_type=strategy,
            strength=strength,
            confidence=round(confidence, 1),
            reasoning=reasoning_text,
            warnings=warnings,
            suggested_action=suggested_action
        )
        
        # Store history
        self.classification_history.append({
            'timestamp': datetime.now().isoformat(),
            'market_data': market_data,
            'proposed_action': proposed_action,
            'result': result
        })
        
        return result
    
    def _get_suggested_action(self, strategy: StrategyType, 
                               market_data: Dict, 
                               proposed_action: str) -> str:
        """Get suggested action based on strategy type"""
        price_change = market_data.get('price_change_pct', 0)
        rsi = market_data.get('rsi', 50)
        
        if strategy == StrategyType.MOMENTUM:
            return 'BUY' if price_change > 0 else 'SELL'
        
        elif strategy == StrategyType.MEAN_REVERSION:
            return 'SELL' if rsi > 70 else 'BUY' if rsi < 30 else 'HOLD'
        
        elif strategy == StrategyType.DARK_POOL_FOLLOWING:
            # Follow whale direction
            return proposed_action
        
        elif strategy == StrategyType.CONTRARIAN:
            # Opposite of momentum
            return 'SELL' if price_change > 0 else 'BUY' if price_change < 0 else 'HOLD'
        
        else:
            return proposed_action
    
    def get_position_multiplier(self, classification: ClassificationResult) -> float:
        """Get position size multiplier based on strategy and strength"""
        multipliers = {
            (StrategyType.MOMENTUM, SignalStrength.STRONG): 1.0,
            (StrategyType.MOMENTUM, SignalStrength.MODERATE): 0.8,
            (StrategyType.MOMENTUM, SignalStrength.WEAK): 0.5,
            (StrategyType.MEAN_REVERSION, SignalStrength.STRONG): 0.8,
            (StrategyType.MEAN_REVERSION, SignalStrength.MODERATE): 0.6,
            (StrategyType.CONTRARIAN, SignalStrength.STRONG): 0.5,
            (StrategyType.CONTRARIAN, SignalStrength.MODERATE): 0.3,
            (StrategyType.DARK_POOL_FOLLOWING, SignalStrength.STRONG): 1.2,
            (StrategyType.BREAKOUT, SignalStrength.STRONG): 1.0,
        }
        
        return multipliers.get((classification.strategy_type, classification.strength), 0.5)
    
    def should_trade(self, classification: ClassificationResult) -> Tuple[bool, str]:
        """Determine if trade should be executed"""
        if classification.strength == SignalStrength.CONTRADICTORY:
            return False, "Signal contradictory - avoid trading"
        
        if classification.confidence < 50:
            return False, f"Confidence too low: {classification.confidence}%"
        
        if classification.strategy_type == StrategyType.RANGE_BOUND:
            return False, "Range bound market - wait for breakout"
        
        if classification.strategy_type == StrategyType.CONTRARIAN and classification.confidence < 65:
            return False, "Contrarian signal needs higher confidence"
        
        return True, "Trade approved"


# Strategy-specific risk adjustments
STRATEGY_RISK_ADJUSTMENTS = {
    StrategyType.MOMENTUM: {
        'stop_multiplier': 1.0,
        'tp_multiplier': 1.5,
        'max_hold_minutes': 8,
        'description': 'Fast-moving trade, tight stops'
    },
    StrategyType.MEAN_REVERSION: {
        'stop_multiplier': 1.2,
        'tp_multiplier': 1.0,
        'max_hold_minutes': 30,
        'description': 'Expecting reversal, wider stops'
    },
    StrategyType.BREAKOUT: {
        'stop_multiplier': 0.8,
        'tp_multiplier': 2.0,
        'max_hold_minutes': 60,
        'description': 'Let profits run'
    },
    StrategyType.CONTRARIAN: {
        'stop_multiplier': 1.5,
        'tp_multiplier': 1.0,
        'max_hold_minutes': 15,
        'description': 'High risk, tight take profit'
    },
    StrategyType.DARK_POOL_FOLLOWING: {
        'stop_multiplier': 1.0,
        'tp_multiplier': 1.8,
        'max_hold_minutes': 120,
        'description': 'Following whales, longer hold'
    },
    StrategyType.TREND_FOLLOWING: {
        'stop_multiplier': 1.2,
        'tp_multiplier': 2.0,
        'max_hold_minutes': 180,
        'description': 'Ride the trend'
    }
}


def get_strategy_config(strategy_type: StrategyType) -> Dict:
    """Get risk configuration for a strategy type"""
    return STRATEGY_RISK_ADJUSTMENTS.get(strategy_type, STRATEGY_RISK_ADJUSTMENTS[StrategyType.MOMENTUM])
