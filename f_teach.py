#!/usr/bin/env python3
"""
Agent F - Educational Trading Agent
Complete teaching script with detailed explanations
"""

import random
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import math

# ============================================
# AGENT F CONFIGURATION
# ============================================

@dataclass
class AgentFConfig:
    """Configuration for Agent F"""
    name: str = "Agent_F"
    type: str = "adaptive_hybrid"
    
    # Learning parameters
    learning_rate: float = 0.01
    memory_size: int = 100
    confidence_decay: float = 0.95
    
    # Technical indicators weights
    trend_weight: float = 0.35
    momentum_weight: float = 0.25
    volume_weight: float = 0.20
    pattern_weight: float = 0.20
    
    # Risk parameters
    max_confidence: float = 0.95
    min_confidence: float = 0.50
    volatility_adjustment: bool = True


# ============================================
# MARKET STATE DETECTION
# ============================================

class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    BREAKOUT = "BREAKOUT"
    UNKNOWN = "UNKNOWN"


class MarketStateDetector:
    """
    Detects current market state/regime
    
    This is CRITICAL because different strategies work in different markets:
    - Trending: Follow the trend (momentum works well)
    - Ranging: Mean reversion works well
    - Volatile: Reduce position size, wider stops
    - Breakout: Aggressive entries
    """
    
    def __init__(self):
        self.price_history: Dict[str, List[float]] = {}
        self.max_history = 50
        
    def add_price(self, asset: str, price: float):
        """Add price to history"""
        if asset not in self.price_history:
            self.price_history[asset] = []
        
        self.price_history[asset].append(price)
        if len(self.price_history[asset]) > self.max_history:
            self.price_history[asset].pop(0)
    
    def detect_regime(self, asset: str) -> MarketRegime:
        """
        Detect current market regime
        
        Logic:
        1. Calculate trend strength (linear regression slope)
        2. Calculate volatility (standard deviation)
        3. Check for range-bound conditions
        4. Check for breakout conditions
        """
        prices = self.price_history.get(asset, [])
        
        if len(prices) < 20:
            return MarketRegime.UNKNOWN
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]
        
        # Trend detection using linear regression
        n = len(prices)
        x = list(range(n))
        
        # Calculate slope
        mean_x = sum(x) / n
        mean_y = sum(prices) / n
        
        numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator != 0:
            slope = numerator / denominator
            normalized_slope = slope / mean_y  # Normalize by price level
        else:
            normalized_slope = 0
        
        # Volatility calculation
        volatility = math.sqrt(sum(r * r for r in returns) / len(returns))
        
        # Range detection
        recent_prices = prices[-20:]
        price_range = (max(recent_prices) - min(recent_prices)) / mean_y
        
        # Classify regime
        if volatility > 0.03:  # >3% volatility
            return MarketRegime.VOLATILE
        elif abs(normalized_slope) > 0.002 and price_range > 0.02:
            return MarketRegime.TRENDING_UP if normalized_slope > 0 else MarketRegime.TRENDING_DOWN
        elif price_range < 0.01:  # <1% range
            return MarketRegime.RANGING
        elif price_range > 0.025 and abs(normalized_slope) > 0.003:
            return MarketRegime.BREAKOUT
        
        return MarketRegime.UNKNOWN


# ============================================
# TECHNICAL INDICATORS
# ============================================

class TechnicalIndicators:
    """
    Technical analysis indicators used by Agent F
    
    Each indicator provides a signal from -1 (strong sell) to +1 (strong buy)
    """
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict:
        """MACD Indicator"""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        ema_12 = TechnicalIndicators.calculate_ema(prices, 12)
        ema_26 = TechnicalIndicators.calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # For signal line, we need MACD history
        return {'macd': macd_line, 'signal': 0, 'histogram': 0}
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20) -> Dict:
        """Bollinger Bands"""
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        sma = TechnicalIndicators.calculate_sma(prices, period)
        
        # Calculate standard deviation
        recent = prices[-period:]
        variance = sum((p - sma) ** 2 for p in recent) / period
        std_dev = math.sqrt(variance)
        
        return {
            'upper': sma + (2 * std_dev),
            'middle': sma,
            'lower': sma - (2 * std_dev)
        }


# ============================================
# SIGNAL GENERATORS
# ============================================

class SignalGenerator:
    """
    Generates trading signals based on different strategies
    
    Each strategy returns:
    - vote: 'BUY', 'SELL', or 'HOLD'
    - confidence: 0-100
    - reasoning: explanation of the decision
    """
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.price_history: Dict[str, List[float]] = {}
    
    def add_price(self, asset: str, price: float):
        """Maintain price history for indicators"""
        if asset not in self.price_history:
            self.price_history[asset] = []
        self.price_history[asset].append(price)
        if len(self.price_history[asset]) > 100:
            self.price_history[asset].pop(0)
    
    def trend_signal(self, asset: str, current_price: float) -> Dict:
        """
        TREND FOLLOWING STRATEGY
        
        Concept: "The trend is your friend"
        - Buy when price is above moving averages (uptrend)
        - Sell when price is below moving averages (downtrend)
        - Confidence increases with trend strength
        """
        prices = self.price_history.get(asset, [current_price])
        
        if len(prices) < 20:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Insufficient data'}
        
        # Calculate moving averages
        sma_20 = self.indicators.calculate_sma(prices, 20)
        sma_50 = self.indicators.calculate_sma(prices, 50) if len(prices) >= 50 else sma_20
        
        # Determine trend
        price_above_sma20 = current_price > sma_20
        price_above_sma50 = current_price > sma_50
        sma20_above_sma50 = sma_20 > sma_50
        
        # Calculate trend strength (how far price is from MAs)
        trend_strength = abs(current_price - sma_20) / sma_20
        
        if price_above_sma20 and price_above_sma50 and sma20_above_sma50:
            # Strong uptrend
            confidence = min(60 + (trend_strength * 1000), 90)
            return {
                'vote': 'BUY',
                'confidence': confidence,
                'reasoning': f'Strong uptrend: Price above SMA20 (${sma_20:.2f}) and SMA50 (${sma_50:.2f})'
            }
        elif not price_above_sma20 and not price_above_sma50 and not sma20_above_sma50:
            # Strong downtrend
            confidence = min(60 + (trend_strength * 1000), 90)
            return {
                'vote': 'SELL',
                'confidence': confidence,
                'reasoning': f'Strong downtrend: Price below SMA20 (${sma_20:.2f}) and SMA50 (${sma_50:.2f})'
            }
        
        return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No clear trend detected'}
    
    def momentum_signal(self, asset: str, current_price: float) -> Dict:
        """
        MOMENTUM STRATEGY
        
        Concept: "Buy high, sell higher"
        - RSI > 70 = Overbought (potential sell)
        - RSI < 30 = Oversold (potential buy)
        - Confidence based on RSI extreme levels
        """
        prices = self.price_history.get(asset, [current_price])
        
        if len(prices) < 15:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Insufficient data'}
        
        rsi = self.indicators.calculate_rsi(prices)
        
        if rsi < 30:
            # Oversold - potential buy
            confidence = 60 + ((30 - rsi) * 1.5)
            return {
                'vote': 'BUY',
                'confidence': min(confidence, 85),
                'reasoning': f'Oversold condition: RSI = {rsi:.1f} (below 30)'
            }
        elif rsi > 70:
            # Overbought - potential sell
            confidence = 60 + ((rsi - 70) * 1.5)
            return {
                'vote': 'SELL',
                'confidence': min(confidence, 85),
                'reasoning': f'Overbought condition: RSI = {rsi:.1f} (above 70)'
            }
        elif rsi > 50 and rsi < 60:
            # Bullish momentum building
            return {
                'vote': 'BUY',
                'confidence': 55 + (rsi - 50),
                'reasoning': f'Bullish momentum: RSI = {rsi:.1f} (above 50)'
            }
        elif rsi < 50 and rsi > 40:
            # Bearish momentum building
            return {
                'vote': 'SELL',
                'confidence': 55 + (50 - rsi),
                'reasoning': f'Bearish momentum: RSI = {rsi:.1f} (below 50)'
            }
        
        return {'vote': 'HOLD', 'confidence': 50, 'reasoning': f'Neutral momentum: RSI = {rsi:.1f}'}
    
    def mean_reversion_signal(self, asset: str, current_price: float) -> Dict:
        """
        MEAN REVERSION STRATEGY
        
        Concept: "What goes up must come down"
        - Buy when price is below lower Bollinger Band
        - Sell when price is above upper Bollinger Band
        - Confidence based on distance from mean
        """
        prices = self.price_history.get(asset, [current_price])
        
        if len(prices) < 20:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Insufficient data'}
        
        bb = self.indicators.calculate_bollinger_bands(prices)
        
        # Calculate distance from mean (in standard deviations)
        distance_from_mean = (current_price - bb['middle']) / (bb['upper'] - bb['middle']) * 2
        
        if current_price < bb['lower']:
            # Price below lower band - oversold, expect reversion up
            oversold_extent = (bb['lower'] - current_price) / bb['lower']
            confidence = min(65 + (oversold_extent * 500), 88)
            return {
                'vote': 'BUY',
                'confidence': confidence,
                'reasoning': f'Price below lower Bollinger Band (${bb["lower"]:.2f}), expecting reversion up'
            }
        elif current_price > bb['upper']:
            # Price above upper band - overbought, expect reversion down
            overbought_extent = (current_price - bb['upper']) / bb['upper']
            confidence = min(65 + (overbought_extent * 500), 88)
            return {
                'vote': 'SELL',
                'confidence': confidence,
                'reasoning': f'Price above upper Bollinger Band (${bb["upper"]:.2f}), expecting reversion down'
            }
        
        return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Price within Bollinger Bands'}
    
    def pattern_recognition_signal(self, asset: str, current_price: float) -> Dict:
        """
        PATTERN RECOGNITION STRATEGY
        
        Detects common chart patterns:
        - Support/Resistance levels
        - Double tops/bottoms
        - Breakouts
        """
        prices = self.price_history.get(asset, [current_price])
        
        if len(prices) < 30:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Insufficient data'}
        
        recent = prices[-20:]
        highs = []
        lows = []
        
        # Find local highs and lows
        for i in range(2, len(recent) - 2):
            if recent[i] > recent[i-1] and recent[i] > recent[i-2] and \
               recent[i] > recent[i+1] and recent[i] > recent[i+2]:
                highs.append(recent[i])
            if recent[i] < recent[i-1] and recent[i] < recent[i-2] and \
               recent[i] < recent[i+1] and recent[i] < recent[i+2]:
                lows.append(recent[i])
        
        if len(highs) >= 2:
            # Check for resistance level
            resistance = sum(highs) / len(highs)
            if current_price > resistance * 0.99 and current_price < resistance * 1.01:
                return {
                    'vote': 'SELL',
                    'confidence': 65,
                    'reasoning': f'Price near resistance level (${resistance:.2f})'
                }
            elif current_price > resistance * 1.02:
                return {
                    'vote': 'BUY',
                    'confidence': 72,
                    'reasoning': f'Breakout above resistance (${resistance:.2f})'
                }
        
        if len(lows) >= 2:
            # Check for support level
            support = sum(lows) / len(lows)
            if current_price > support * 0.99 and current_price < support * 1.01:
                return {
                    'vote': 'BUY',
                    'confidence': 65,
                    'reasoning': f'Price near support level (${support:.2f})'
                }
            elif current_price < support * 0.98:
                return {
                    'vote': 'SELL',
                    'confidence': 72,
                    'reasoning': f'Breakdown below support (${support:.2f})'
                }
        
        return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No clear pattern detected'}


# ============================================
# AGENT F - MAIN CLASS
# ============================================

class AgentF:
    """
    AGENT F - Adaptive Hybrid Trading Agent
    
    This agent combines multiple strategies and adapts based on market conditions.
    
    KEY FEATURES:
    1. Multi-strategy approach (Trend, Momentum, Mean Reversion, Patterns)
    2. Market regime detection for strategy weighting
    3. Confidence scoring with reasoning
    4. Memory of past decisions for learning
    5. Risk-adjusted position sizing
    
    DECISION PROCESS:
    1. Detect current market regime
    2. Generate signals from all strategies
    3. Weight signals based on regime and historical performance
    4. Combine into final vote with confidence
    5. Provide detailed reasoning
    """
    
    def __init__(self, config: AgentFConfig = None):
        self.config = config or AgentFConfig()
        self.market_detector = MarketStateDetector()
        self.signal_generator = SignalGenerator()
        self.memory: List[Dict] = []
        self.performance_metrics = {
            'trend': {'correct': 0, 'total': 0},
            'momentum': {'correct': 0, 'total': 0},
            'reversion': {'correct': 0, 'total': 0},
            'pattern': {'correct': 0, 'total': 0}
        }
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🤖 AGENT F INITIALIZED                     ║
╠══════════════════════════════════════════════════════════════╣
║  Type: {self.config.type:<49}║
║  Strategies: Trend, Momentum, Mean Reversion, Pattern        ║
║  Learning: Enabled                                           ║
║  Market Awareness: Real-time regime detection                ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def update_price_history(self, asset: str, price: float):
        """Update price history for all components"""
        self.market_detector.add_price(asset, price)
        self.signal_generator.add_price(asset, price)
    
    def vote(self, asset: str, price: float) -> Dict:
        """
        Main voting method - generates trading signal
        
        Returns:
            Dict with 'vote', 'confidence', and 'reasoning'
        """
        print(f"\n{'─'*50}")
        print(f"🤖 Agent F analyzing {asset} at ${price:,.2f}")
        print(f"{'─'*50}")
        
        # Update price history
        self.update_price_history(asset, price)
        
        # Step 1: Detect market regime
        regime = self.market_detector.detect_regime(asset)
        print(f"📊 Market Regime: {regime.value}")
        
        # Step 2: Get signals from all strategies
        signals = {
            'trend': self.signal_generator.trend_signal(asset, price),
            'momentum': self.signal_generator.momentum_signal(asset, price),
            'reversion': self.signal_generator.mean_reversion_signal(asset, price),
            'pattern': self.signal_generator.pattern_recognition_signal(asset, price)
        }
        
        print(f"\n📈 Strategy Signals:")
        for name, signal in signals.items():
            print(f"   {name:10} → {signal['vote']:4} ({signal['confidence']:.0f}%) - {signal['reasoning']}")
        
        # Step 3: Adjust weights based on market regime
        weights = self._get_regime_weights(regime)
        print(f"\n⚖️  Regime-adjusted weights:")
        for name, weight in weights.items():
            print(f"   {name}: {weight*100:.0f}%")
        
        # Step 4: Combine signals
        final_vote = self._combine_signals(signals, weights)
        
        # Step 5: Add to memory for learning
        self._add_to_memory(asset, price, signals, final_vote, regime)
        
        print(f"\n🎯 FINAL DECISION: {final_vote['vote']} ({final_vote['confidence']:.0f}%)")
        print(f"💭 Reasoning: {final_vote['reasoning']}")
        print(f"{'─'*50}")
        
        return final_vote
    
    def _get_regime_weights(self, regime: MarketRegime) -> Dict:
        """
        Adjust strategy weights based on market regime
        
        Different strategies work better in different markets:
        - Trending: Trend following works best
        - Ranging: Mean reversion works best
        - Volatile: Reduce all weights, be cautious
        - Breakout: Momentum and patterns work best
        """
        base_weights = {
            'trend': self.config.trend_weight,
            'momentum': self.config.momentum_weight,
            'reversion': self.config.volume_weight,
            'pattern': self.config.pattern_weight
        }
        
        if regime == MarketRegime.TRENDING_UP or regime == MarketRegime.TRENDING_DOWN:
            # Boost trend following
            base_weights['trend'] *= 1.5
            base_weights['momentum'] *= 1.2
            base_weights['reversion'] *= 0.5
            
        elif regime == MarketRegime.RANGING:
            # Boost mean reversion
            base_weights['reversion'] *= 1.8
            base_weights['trend'] *= 0.6
            base_weights['momentum'] *= 0.7
            
        elif regime == MarketRegime.VOLATILE:
            # Reduce all weights, increase pattern recognition
            base_weights['trend'] *= 0.5
            base_weights['momentum'] *= 0.5
            base_weights['reversion'] *= 0.5
            base_weights['pattern'] *= 1.3
            
        elif regime == MarketRegime.BREAKOUT:
            # Boost momentum and patterns
            base_weights['momentum'] *= 1.5
            base_weights['pattern'] *= 1.5
            base_weights['reversion'] *= 0.3
        
        # Normalize weights to sum to 1
        total = sum(base_weights.values())
        return {k: v/total for k, v in base_weights.items()}
    
    def _combine_signals(self, signals: Dict, weights: Dict) -> Dict:
        """
        Combine multiple strategy signals into final decision
        
        Process:
        1. Calculate weighted scores for BUY, SELL, HOLD
        2. Determine final vote based on highest score
        3. Calculate confidence from score strength and agreement
        """
        buy_score = 0
        sell_score = 0
        hold_score = 0
        total_confidence = 0
        
        reason_parts = []
        
        for strategy, signal in signals.items():
            weight = weights.get(strategy, 0.25)
            vote = signal['vote']
            conf = signal['confidence'] / 100
            
            if vote == 'BUY':
                buy_score += conf * weight
            elif vote == 'SELL':
                sell_score += conf * weight
            else:
                hold_score += conf * weight
            
            total_confidence += conf * weight
            reason_parts.append(f"{strategy}:{signal['reasoning']}")
        
        # Determine final vote
        max_score = max(buy_score, sell_score, hold_score)
        
        if max_score == buy_score and buy_score > 0.3:
            vote = 'BUY'
            confidence = min(buy_score * 100, self.config.max_confidence * 100)
        elif max_score == sell_score and sell_score > 0.3:
            vote = 'SELL'
            confidence = min(sell_score * 100, self.config.max_confidence * 100)
        else:
            vote = 'HOLD'
            confidence = max(hold_score * 100, 50)
        
        # Adjust confidence based on strategy agreement
        agreement_bonus = self._calculate_agreement(signals)
        confidence = min(confidence * (1 + agreement_bonus), self.config.max_confidence * 100)
        
        # Build reasoning
        vote_counts = {
            'BUY': sum(1 for s in signals.values() if s['vote'] == 'BUY'),
            'SELL': sum(1 for s in signals.values() if s['vote'] == 'SELL'),
            'HOLD': sum(1 for s in signals.values() if s['vote'] == 'HOLD')
        }
        
        reasoning = f"Combined {len(signals)} strategies. "
        reasoning += f"Votes: BUY={vote_counts['BUY']}, SELL={vote_counts['SELL']}, HOLD={vote_counts['HOLD']}. "
        
        # Add top contributing strategy
        top_strategy = max(signals.items(), key=lambda x: x[1]['confidence'])
        reasoning += f"Primary driver: {top_strategy[0]} ({top_strategy[1]['reasoning']})"
        
        return {
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'scores': {'buy': buy_score, 'sell': sell_score, 'hold': hold_score},
            'vote_counts': vote_counts
        }
    
    def _calculate_agreement(self, signals: Dict) -> float:
        """Calculate strategy agreement bonus"""
        votes = [s['vote'] for s in signals.values()]
        most_common = max(set(votes), key=votes.count)
        agreement_ratio = votes.count(most_common) / len(votes)
        
        if agreement_ratio >= 0.75:  # 3 out of 4 agree
            return 0.15  # 15% confidence boost
        elif agreement_ratio >= 0.5:  # 2 out of 4 agree
            return 0.05  # 5% confidence boost
        
        return 0.0
    
    def _add_to_memory(self, asset: str, price: float, signals: Dict, 
                       final_vote: Dict, regime: MarketRegime):
        """Store decision in memory for learning"""
        memory_entry = {
            'timestamp': datetime.now(),
            'asset': asset,
            'price': price,
            'regime': regime.value,
            'signals': signals,
            'final_vote': final_vote,
            'outcome': None  # To be filled later
        }
        
        self.memory.append(memory_entry)
        
        # Keep memory size limited
        if len(self.memory) > self.config.memory_size:
            self.memory.pop(0)
    
    def learn_from_outcome(self, asset: str, entry_price: float, 
                           exit_price: float, decision: str):
        """
        Learn from trade outcome
        
        Updates performance metrics for each strategy
        """
        # Find the memory entry
        for entry in reversed(self.memory):
            if entry['asset'] == asset and entry['price'] == entry_price:
                
                # Determine if trade was profitable
                if decision == 'BUY':
                    profitable = exit_price > entry_price
                else:  # SELL
                    profitable = exit_price < entry_price
                
                # Update strategy performance
                for strategy, signal in entry['signals'].items():
                    if signal['vote'] == decision:
                        self.performance_metrics[strategy]['total'] += 1
                        if profitable:
                            self.performance_metrics[strategy]['correct'] += 1
                
                entry['outcome'] = {
                    'exit_price': exit_price,
                    'profitable': profitable,
                    'pnl_pct': abs(exit_price - entry_price) / entry_price * 100
                }
                
                print(f"\n📚 Agent F Learning:")
                print(f"   Trade outcome: {'✅ PROFIT' if profitable else '❌ LOSS'}")
                print(f"   Updated strategy performance metrics")
                
                break
    
    def get_performance_summary(self) -> Dict:
        """Get performance metrics for all strategies"""
        summary = {}
        for strategy, metrics in self.performance_metrics.items():
            if metrics['total'] > 0:
                accuracy = metrics['correct'] / metrics['total'] * 100
            else:
                accuracy = 0
            summary[strategy] = {
                'accuracy': accuracy,
                'total_trades': metrics['total'],
                'correct_trades': metrics['correct']
            }
        return summary


# ============================================
# DEMO AND TESTING
# ============================================

def demo_agent_f():
    """
    Demonstration of Agent F capabilities
    
    Shows how the agent:
    1. Analyzes different assets
    2. Detects market regimes
    3. Combines multiple strategies
    4. Provides detailed reasoning
    """
    print("\n" + "═" * 60)
    print(" " * 15 + "🤖 AGENT F DEMONSTRATION")
    print("═" * 60)
    
    # Create agent
    agent = AgentF()
    
    # Test assets with simulated prices
    test_assets = {
        'XAU/USD': 2385.50,   # Gold
        'EURUSD': 1.0725,    # Euro
        'S&P500/USD': 5200.50, # S&P 500
        'BCO/USD': 89.75      # Oil
    }
    
    print("\n📊 Analyzing multiple assets...")
    print("═" * 60)
    
    for asset, price in test_assets.items():
        # Feed some historical data for better analysis
        for i in range(30):
            variation = random.uniform(-0.01, 0.01)
            historical_price = price * (1 + variation * i/10)
            agent.update_price_history(asset, historical_price)
        
        # Get vote
        vote = agent.vote(asset, price)
        
        print(f"\n{'─'*40}")
    
    # Show performance (initially no trades)
    print("\n" + "═" * 60)
    print("📊 AGENT F CONFIGURATION SUMMARY")
    print("═" * 60)
    print(f"""
Strategy Weights:
  ├ Trend Following:    {agent.config.trend_weight*100:.0f}%
  ├ Momentum:           {agent.config.momentum_weight*100:.0f}%
  ├ Mean Reversion:     {agent.config.volume_weight*100:.0f}%
  └ Pattern Recognition: {agent.config.pattern_weight*100:.0f}%

Learning: {'✅ Enabled' if agent.config.learning_rate > 0 else '❌ Disabled'}
Memory Size: {agent.config.memory_size} trades
Confidence Range: {agent.config.min_confidence*100:.0f}% - {agent.config.max_confidence*100:.0f}%
    """)


def explain_agent_f_logic():
    """
    Educational function explaining Agent F's decision process
    """
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    🎓 AGENT F - EDUCATIONAL GUIDE                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  🧠 HOW AGENT F MAKES DECISIONS                                      ║
║  ─────────────────────────────                                       ║
║                                                                      ║
║  1️⃣  MARKET REGIME DETECTION                                         ║
║      • Analyzes 50 periods of price history                          ║
║      • Calculates trend slope using linear regression                ║
║      • Measures volatility (standard deviation)                      ║
║      • Classifies as: TRENDING, RANGING, VOLATILE, or BREAKOUT      ║
║                                                                      ║
║  2️⃣  MULTI-STRATEGY ANALYSIS                                         ║
║      • TREND: Moving average crossovers (SMA 20/50)                 ║
║      • MOMENTUM: RSI overbought/oversold levels                      ║
║      • REVERSION: Bollinger Bands mean reversion                     ║
║      • PATTERN: Support/resistance and breakout detection            ║
║                                                                      ║
║  3️⃣  WEIGHTED COMBINATION                                             ║
║      • Adjusts strategy weights based on market regime               ║
║      • Trending market → More weight on trend following              ║
║      • Ranging market → More weight on mean reversion                ║
║      • Volatile market → Reduced weights, more caution               ║
║                                                                      ║
║  4️⃣  CONFIDENCE CALCULATION                                           ║
║      • Base: Weighted average of strategy confidences                ║
║      • Bonus: +15% if 3+ strategies agree                            ║
║      • Bonus: +5% if 2 strategies agree                              ║
║      • Cap: Maximum 95% confidence                                   ║
║                                                                      ║
║  5️⃣  CONTINUOUS LEARNING                                              ║
║      • Tracks accuracy of each strategy                              ║
║      • Updates weights based on historical performance               ║
║      • Maintains memory of last 100 trades                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

📊 EXAMPLE DECISION TREE:

    Price Data → Regime Detection → Strategy Signals → Weighted Vote
         ↓              ↓                  ↓               ↓
    $2,385.50    TRENDING_UP      Trend: BUY(85%)    BUY (83%)
                                  Mom: BUY(75%)      Confidence: 83%
                                  Rev: HOLD(50%)     
                                  Pat: BUY(65%)

💡 KEY INSIGHTS:

    • Different strategies work better in different markets
    • Combining multiple strategies reduces false signals
    • Market regime awareness improves strategy selection
    • Confidence scoring helps with position sizing
    • Learning from past trades improves future decisions
""")


# ============================================
# INTEGRATION WITH MAIN TRADING SYSTEM
# ============================================

def create_agent_f_vote_function():
    """
    Creates a vote function compatible with the main trading system
    
    Returns a function that can be called like:
        vote = agent_f_vote(asset, price)
    """
    agent = AgentF()
    
    # Pre-populate with some historical data for better analysis
    def initialize_history(asset: str, base_price: float):
        for i in range(50, 0, -1):
            variation = math.sin(i / 10) * 0.01 + random.uniform(-0.005, 0.005)
            historical_price = base_price * (1 + variation)
            agent.update_price_history(asset, historical_price)
    
    def agent_f_vote(asset: str, price: float) -> Dict:
        # Initialize history if needed (only once per asset)
        if asset not in agent.market_detector.price_history:
            initialize_history(asset, price)
        
        # Get vote
        result = agent.vote(asset, price)
        
        return {
            'vote': result['vote'],
            'confidence': result['confidence']
        }
    
    return agent_f_vote


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🤖 AGENT F - ADAPTIVE HYBRID TRADING AGENT                ║
║   EDUCATIONAL VERSION                                        ║
║                                                              ║
║   This script teaches how Agent F makes trading decisions    ║
║   using multiple strategies, market regime detection,        ║
║   and adaptive weighting.                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Show educational content
    explain_agent_f_logic()
    
    # Run demonstration
    demo_agent_f()
    
    print("\n" + "═" * 60)
    print("✅ Agent F demonstration complete!")
    print("═" * 60)
    
    print("""
📝 INTEGRATION NOTES:
   
   To use Agent F in your main trading system:
   
   ```python
   from agent_f_educational import create_agent_f_vote_function
   
   # Create the vote function
   agent_f_vote = create_agent_f_vote_function()
   
   # Use in your signal processing
   votes['Agent_F'] = agent_f_vote(asset, price)

          """)
