"""
Hybrid Signal Processor - Multi-Asset, Multi-Timeframe
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class HybridSignalProcessor:
    """
    Processes signals with hybrid approach:
    - All agents analyze all assets
    - Timeframe determines risk parameters
    - Each agent uses specialized strategy
    """
    
    def __init__(self, db_manager, agent_manager, supervisor, strategy_framework):
        self.db = db_manager
        self.agent_manager = agent_manager
        self.supervisor = supervisor
        self.strategy_framework = strategy_framework
        
        # Timeframe configuration
        self.timeframe_config = {
            5: {'name': 'SCALPING', 'min_confidence': 70, 'position_multiplier': 0.5},
            15: {'name': 'DAY_TRADE', 'min_confidence': 75, 'position_multiplier': 1.0},
            60: {'name': 'SWING', 'min_confidence': 80, 'position_multiplier': 1.5},
            1440: {'name': 'POSITION', 'min_confidence': 85, 'position_multiplier': 2.0}
        }
    
def _generate_candlestick_data(self, current_price, volatility):
    """Generate simulated candlestick data for Agent_F"""
    import random
    
    candles = []
    base_price = current_price
    
    for i in range(10):
        # Simulate OHLC data
        open_price = base_price
        close_price = open_price * (1 + random.uniform(-volatility/100, volatility/100))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility/200))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility/200))
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': random.randint(1000, 10000)
        })
        
        base_price = close_price
    
        return candles
   # ============================================
    # NEW 4 AGENTS METHODS (I, J, K, L)
    # ============================================
    
    def _agent_i_sentiment(self, data):
        """Agent I - Sentiment Master"""
        sentiment_score = data.get('sentiment', 0)  # -100 to +100
        news_sentiment = data.get('news_sentiment', 'neutral')
        fear_greed = data.get('fear_greed_index', 50)
        
        if sentiment_score > 50 or fear_greed > 75:
            return 'SELL', 75, "Extreme greed detected - Market top risk"
        elif sentiment_score < -50 or fear_greed < 25:
            return 'BUY', 75, "Extreme fear detected - Market bottom opportunity"
        elif news_sentiment == 'positive':
            return 'BUY', 65, "Positive news sentiment"
        elif news_sentiment == 'negative':
            return 'SELL', 65, "Negative news sentiment"
        elif sentiment_score > 20:
            return 'BUY', 55, "Moderately positive sentiment"
        elif sentiment_score < -20:
            return 'SELL', 55, "Moderately negative sentiment"
        else:
            return 'HOLD', 50, "Neutral sentiment - No strong signal"
    
    def _agent_j_volume(self, data):
        """Agent J - Volume Master"""
        volume_ratio = data.get('volume_ratio', 1.0)  # Current volume / average volume
        volume_trend = data.get('volume_trend', 'flat')
        price_direction = data.get('trend', 'sideways')
        
        # Volume confirms price movement
        if volume_ratio > 1.5 and price_direction == 'up' and volume_trend == 'increasing':
            return 'BUY', 85, "High volume confirming uptrend"
        elif volume_ratio > 1.5 and price_direction == 'down' and volume_trend == 'increasing':
            return 'SELL', 85, "High volume confirming downtrend"
        
        # Volume divergence
        elif volume_ratio < 0.5 and price_direction == 'up':
            return 'SELL', 70, "Price up on low volume - Weak rally"
        elif volume_ratio < 0.5 and price_direction == 'down':
            return 'BUY', 70, "Price down on low volume - Exhaustion"
        
        # Volume spikes
        elif volume_ratio > 2.0:
            if price_direction == 'up':
                return 'BUY', 80, "Volume spike at support - Accumulation"
            else:
                return 'SELL', 80, "Volume spike at resistance - Distribution"
        
        else:
            return 'HOLD', 50, "Normal volume - No signal"
    
    def _agent_k_ichimoku(self, data):
        """Agent K - Ichimoku Expert"""
        price = data.get('price', 1.0950)
        tenkan = data.get('tenkan_sen', 1.0930)  # Conversion line
        kijun = data.get('kijun_sen', 1.0910)    # Base line
        cloud_top = data.get('cloud_top', 1.0940)
        cloud_bottom = data.get('cloud_bottom', 1.0900)
        lagging_span = data.get('lagging_span', 1.0950)
        
        # Price above cloud
        if price > cloud_top:
            if tenkan > kijun:
                return 'BUY', 85, "Bullish: Price above cloud with TK cross"
            else:
                return 'BUY', 70, "Bullish: Price above cloud"
        
        # Price below cloud
        elif price < cloud_bottom:
            if tenkan < kijun:
                return 'SELL', 85, "Bearish: Price below cloud with TK cross"
            else:
                return 'SELL', 70, "Bearish: Price below cloud"
        
        # Inside cloud
        elif cloud_bottom <= price <= cloud_top:
            return 'HOLD', 60, "Inside Ichimoku cloud - Wait for breakout"
        
        # TK cross signals
        elif tenkan > kijun and price > kijun:
            return 'BUY', 75, "Bullish TK cross"
        elif tenkan < kijun and price < kijun:
            return 'SELL', 75, "Bearish TK cross"
        
        else:
            return 'HOLD', 50, "No clear Ichimoku signal"
    
    def _agent_l_fundamental(self, data):
        """Agent L - Fundamental Master"""
        interest_rate_diff = data.get('interest_rate_diff', 0)  # Positive = higher rate for base currency
        economic_score = data.get('economic_score', 50)  # 0-100
        central_bank_bias = data.get('central_bank_bias', 'neutral')
        gdp_growth = data.get('gdp_growth', 2.0)
        inflation = data.get('inflation', 2.5)
        
        score = 50
        
        # Interest rate differential
        if interest_rate_diff > 1.0:
            score += 15
        elif interest_rate_diff < -1.0:
            score -= 15
        
        # Economic strength
        if economic_score > 60:
            score += 10
        elif economic_score < 40:
            score -= 10
        
        # Central bank bias
        if central_bank_bias == 'hawkish':
            score += 10
        elif central_bank_bias == 'dovish':
            score -= 10
        
        # GDP and inflation
        if gdp_growth > 2.5 and inflation < 3:
            score += 5
        
        if score > 65:
            return 'BUY', min(85, score), f"Strong fundamentals: Score {score}"
        elif score < 35:
            return 'SELL', min(85, 100 - score), f"Weak fundamentals: Score {score}"
        else:
            return 'HOLD', 55, f"Mixed fundamentals: Score {score}"
def process_signal(self, signal_data: Dict) -> Dict:
        """
        Process a trading signal through the hybrid pipeline
        """
        # Add candlestick data for Agent_F
        candles = self._generate_candlestick_data(
        signal_data.get('current_price', 0),
        signal_data.get('analysis_volatility', 0.5)
        )
        market_features['candles'] = candles
        start_time = time.time()
        
        asset = signal_data.get('asset_type', 'UNKNOWN')
        timeframe = signal_data.get('timeframe_minutes', 15)
        
        print(f"\n{'='*60}")
        print(f"📊 PROCESSING HYBRID SIGNAL")
        print(f"{'='*60}")
        print(f"📡 Asset: {asset}")
        print(f"⏱️ Timeframe: {timeframe} minutes")
        print(f"💰 Price: ${signal_data.get('current_price', 0):,.2f}")
        print(f"🎯 Confidence: {signal_data.get('confidence_percent', 75)}%")
        
        # Step 1: Get timeframe configuration
        tf_config = self.timeframe_config.get(timeframe, self.timeframe_config[15])
        
        # Step 2: Prepare market features with context
        market_features = {
            'timeframe': timeframe,
            'volatility': signal_data.get('analysis_volatility', 0.5),
            'asset': asset,
            'strategy': tf_config['name']
        }
        
        # Step 3: Collect votes from all agents
        votes = self.agent_manager.collect_votes(signal_data, market_features)
        
        # Step 4: Calculate vote distribution
        buy_votes = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell_votes = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        hold_votes = sum(1 for v in votes.values() if v.get('vote') == 'HOLD')
        total = len(votes)
        
        buy_percent = (buy_votes / total) * 100 if total > 0 else 0
        sell_percent = (sell_votes / total) * 100 if total > 0 else 0
        hold_percent = (hold_votes / total) * 100 if total > 0 else 0
        
        # Step 5: Calculate weighted decision
        if buy_votes > sell_votes and buy_votes > hold_votes:
            decision_action = 'BUY'
            decision_confidence = (buy_votes / total) * 100 if total > 0 else 0
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            decision_action = 'SELL'
            decision_confidence = (sell_votes / total) * 100 if total > 0 else 0
        else:
            decision_action = 'HOLD'
            decision_confidence = (hold_votes / total) * 100 if total > 0 else 50
        
        # Step 6: Apply timeframe-specific constraints
        if decision_confidence < tf_config['min_confidence']:
            decision_action = 'HOLD'
            decision_reason = f"Confidence {decision_confidence:.1f}% below minimum {tf_config['min_confidence']}% for {tf_config['name']}"
        else:
            decision_reason = "Normal processing"
        
        # Step 7: Calculate position size
        position_size = self._calculate_position_size(
            tf_config, 
            decision_confidence,
            signal_data.get('analysis_volatility', 0.5)
        )
        
        # Step 8: Calculate stop loss and take profit
        current_price = signal_data.get('current_price', 0)
        stoploss = self._calculate_stoploss(current_price, tf_config, signal_data)
        takeprofit = self._calculate_takeprofit(current_price, stoploss, tf_config)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Step 9: Build result
        result = {
            'signal': signal_data,
            'asset': asset,
            'timeframe': timeframe,
            'strategy': tf_config['name'],
            'votes': votes,
            'vote_distribution': {
                'buy': buy_votes, 'sell': sell_votes, 'hold': hold_votes,
                'buy_percent': round(buy_percent, 1),
                'sell_percent': round(sell_percent, 1),
                'hold_percent': round(hold_percent, 1)
            },
            'decision': {
                'action': decision_action,
                'confidence': round(decision_confidence, 1),
                'reason': decision_reason
            },
            'risk_management': {
                'position_size': position_size,
                'stoploss': round(stoploss, 2),
                'takeprofit': round(takeprofit, 2),
                'risk_reward_ratio': round(abs(takeprofit - current_price) / abs(current_price - stoploss), 2) if stoploss != current_price else 0
            },
            'processing_time_ms': round(processing_time, 2)
        }
        
        # Step 10: Print summary
        self._print_summary(result)
        
        return result
    
def _calculate_position_size(self, tf_config: Dict, confidence: float, volatility: float) -> int:
        """Calculate position size based on timeframe, confidence, and volatility"""
        base_sizes = {'SCALPING': 1000, 'DAY_TRADE': 5000, 'SWING': 10000, 'POSITION': 25000}
        base = base_sizes.get(tf_config['name'], 5000)
        
        confidence_factor = confidence / 100
        volatility_factor = max(0.5, min(1.5, 1.0 - (volatility / 100)))
        timeframe_factor = tf_config['position_multiplier']
        
        size = int(base * confidence_factor * volatility_factor * timeframe_factor)
        return max(100, min(25000, size))
    
def _calculate_stoploss(self, price: float, tf_config: Dict, signal_data: Dict) -> float:
        """Calculate stop loss based on timeframe and signal data"""
        if signal_data.get('stoploss'):
            return signal_data['stoploss']
        
        stop_percent = {
            'SCALPING': 0.005,   # 0.5%
            'DAY_TRADE': 0.01,   # 1%
            'SWING': 0.02,       # 2%
            'POSITION': 0.03     # 3%
        }.get(tf_config['name'], 0.01)
        
        return price * (1 - stop_percent)
    
def _calculate_takeprofit(self, price: float, stoploss: float, tf_config: Dict) -> float:
        """Calculate take profit based on risk-reward ratio"""
        risk = abs(price - stoploss)
        reward_multiplier = {
            'SCALPING': 1.5,
            'DAY_TRADE': 2.0,
            'SWING': 3.0,
            'POSITION': 5.0
        }.get(tf_config['name'], 2.0)
        
        return price + (risk * reward_multiplier)
    
def _print_summary(self, result: Dict):
        """Print processing summary"""
        print(f"\n{'─'*40}")
        print(f"🗳️ VOTING RESULTS:")
        print(f"   BUY:  {result['vote_distribution']['buy']} votes ({result['vote_distribution']['buy_percent']}%)")
        print(f"   SELL: {result['vote_distribution']['sell']} votes ({result['vote_distribution']['sell_percent']}%)")
        print(f"   HOLD: {result['vote_distribution']['hold']} votes ({result['vote_distribution']['hold_percent']}%)")
        
        print(f"\n📊 AGENT VOTES:")
        for agent, vote in result['votes'].items():
            icon = "🟢" if vote['vote'] == 'BUY' else "🔴" if vote['vote'] == 'SELL' else "⚪"
            print(f"   {icon} {agent}: {vote['vote']} ({vote['confidence']:.0f}%)")
        
        print(f"\n✅ FINAL DECISION: {result['decision']['action']} ({result['decision']['confidence']:.0f}%)")
        print(f"   {result['decision'].get('reason', '')}")
        
        print(f"\n💰 RISK MANAGEMENT:")
        print(f"   Position Size: {result['risk_management']['position_size']} units")
        print(f"   Stop Loss: ${result['risk_management']['stoploss']:.2f}")
        print(f"   Take Profit: ${result['risk_management']['takeprofit']:.2f}")
        print(f"   Risk/Reward: 1:{result['risk_management']['risk_reward_ratio']}")
        
        print(f"\n⏱️ Processing Time: {result['processing_time_ms']}ms")
        print(f"{'='*60}\n")
