"""
Hybrid Signal Processor - Multi-Asset, Multi-Timeframe
With ALL Agents: A, B, C, D, E, F, L, N, O, P, T, U, X
"""

import json
import logging
import time
import random
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class HybridSignalProcessor:
    """
    Processes signals with hybrid approach:
    - ALL 13 agents analyze all assets
    - Timeframe determines risk parameters
    - Weighted voting with agent-specific weights
    """
    
    def __init__(self, db_manager, agent_manager, supervisor, strategy_framework):
        self.db = db_manager
        self.agent_manager = agent_manager
        self.supervisor = supervisor
        self.strategy_framework = strategy_framework
        
        # Timeframe configuration
        self.timeframe_config = {
            5: {'name': 'SCALPING', 'min_confidence': 70, 'position_multiplier': 0.5, 'stop_pips': 10, 'risk_reward': 1.5},
            15: {'name': 'DAY_TRADE', 'min_confidence': 75, 'position_multiplier': 1.0, 'stop_pips': 20, 'risk_reward': 2.0},
            60: {'name': 'SWING', 'min_confidence': 80, 'position_multiplier': 1.5, 'stop_pips': 40, 'risk_reward': 3.0},
            1440: {'name': 'POSITION', 'min_confidence': 85, 'position_multiplier': 2.0, 'stop_pips': 80, 'risk_reward': 5.0}
        }
        
        # === ALL 13 AGENTS WITH WEIGHTS ===
        self.agent_weights = {
            # Strategy Specialists
            'Agent_A': 0.07,  # Strategy Alpha
            'Agent_B': 0.07,  # Strategy Beta
            'Agent_C': 0.07,  # Strategy Gamma
            
            # Technical Agents
            'Agent_D': 0.09,  # Volatility & Bollinger Band Squeeze
            'Agent_E': 0.07,  # Technical Analysis
            'Agent_F': 0.07,  # Candlestick Patterns
            
            # Fundamental Agents
            'Agent_L': 0.08,  # Fundamental Master
            'Agent_O': 0.07,  # Macro Analysis
            
            # Analysis Agents
            'Agent_N': 0.07,  # Flow Analysis
            'Agent_P': 0.07,  # Pattern Recognition
            'Agent_T': 0.07,  # Timing Specialist
            
            # Trading Specialists
            'Agent_U': 0.09,  # Liquidity & Stop Hunting
            'Agent_X': 0.11,  # Spread Reversion (Z-score)
        }
        
        # === AGENT TYPE CLASSIFICATION ===
        self.agent_types = {
            'strategy': ['Agent_A', 'Agent_B', 'Agent_C'],
            'technical': ['Agent_D', 'Agent_E', 'Agent_F', 'Agent_X', 'Agent_U'],
            'fundamental': ['Agent_L', 'Agent_O'],
            'analysis': ['Agent_N', 'Agent_P', 'Agent_T'],
        }
        
        # === AGENT INSTANCES ===
        self.agents = {}
        self._initialize_agents()
        
        # === STATISTICS ===
        self.stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'watch_signals': 0,
            'avg_confidence': 0,
            'by_agent': {}
        }
        
        logger.info("✅ HybridSignalProcessor initialized")
        logger.info(f"   Total Agents: {len(self.agent_weights)}")
        logger.info(f"   Agent Types: {len(self.agent_types)} categories")
        logger.info(f"   Timeframes: {list(self.timeframe_config.keys())}")
    
    def _initialize_agents(self):
        """Initialize ALL agent instances"""
        
        # === AGENT_D - Volatility & Bollinger Band Squeeze ===
        try:
            from agents.agent_d_volatility import AgentDVolatility
            self.agents['Agent_D'] = AgentDVolatility()
        except ImportError:
            self.agents['Agent_D'] = self._create_placeholder('Agent_D', 'Volatility & Squeeze')
        
        # === AGENT_U - Liquidity & Stop Hunting ===
        try:
            from agents.agent_u_liquidity import AgentULiquidity
            self.agents['Agent_U'] = AgentULiquidity()
        except ImportError:
            self.agents['Agent_U'] = self._create_placeholder('Agent_U', 'Liquidity & Stop Hunting')
        
        # === AGENT_X - Spread Reversion ===
        try:
            from agents.agent_x_spread import AgentXSpread
            self.agents['Agent_X'] = AgentXSpread()
        except ImportError:
            self.agents['Agent_X'] = self._create_placeholder('Agent_X', 'Spread Reversion')
        
        # === AGENT_L - Fundamental Master ===
        try:
            from agents.agent_l_fundamental import AgentLFundamental
            self.agents['Agent_L'] = AgentLFundamental()
        except ImportError:
            self.agents['Agent_L'] = self._create_placeholder('Agent_L', 'Fundamental Analysis')
        
        # === AGENT_F - Candlestick Patterns ===
        try:
            from agents.agent_f_candlestick import AgentFCandlestick
            self.agents['Agent_F'] = AgentFCandlestick()
        except ImportError:
            self.agents['Agent_F'] = self._create_placeholder('Agent_F', 'Candlestick Patterns')
        
        # === PLACEHOLDER AGENTS (A, B, C, E, N, O, P, T) ===
        # Replace these with your actual implementations
        self.agents['Agent_A'] = self._create_placeholder('Agent_A', 'Strategy Alpha')
        self.agents['Agent_B'] = self._create_placeholder('Agent_B', 'Strategy Beta')
        self.agents['Agent_C'] = self._create_placeholder('Agent_C', 'Strategy Gamma')
        self.agents['Agent_E'] = self._create_placeholder('Agent_E', 'Technical Analysis')
        self.agents['Agent_N'] = self._create_placeholder('Agent_N', 'Flow Analysis')
        self.agents['Agent_O'] = self._create_placeholder('Agent_O', 'Macro Analysis')
        self.agents['Agent_P'] = self._create_placeholder('Agent_P', 'Pattern Recognition')
        self.agents['Agent_T'] = self._create_placeholder('Agent_T', 'Timing Specialist')
        
        # Log initialization
        logger.info(f"   ✅ {len(self.agents)} agents initialized")
        for agent_type, agent_list in self.agent_types.items():
            active = [a for a in agent_list if a in self.agents]
            logger.info(f"   📊 {agent_type}: {len(active)} agents")
    
    def _create_placeholder(self, name: str, specialization: str):
        """Create a placeholder agent with proper interface"""
        class PlaceholderAgent:
            def __init__(self, n, spec):
                self.name = n
                self.agent_type = "Placeholder"
                self.specialization = spec
            
            def analyze(self, data):
                return {
                    'vote': 'HOLD', 
                    'confidence': 50, 
                    'reasoning': f'Placeholder - Implement {self.name} ({self.specialization})',
                    'agent': self.name,
                    'timestamp': datetime.now().isoformat()
                }
        return PlaceholderAgent(name, specialization)
    
    def _generate_candlestick_data(self, current_price, volatility):
        """Generate simulated candlestick data for agents that need it"""
        candles = []
        base_price = current_price if current_price > 0 else 1.1000
        
        for i in range(10):
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
    
    def process_signal(self, signal_data: Dict) -> Dict:
        """
        Process a trading signal through the hybrid pipeline with ALL agents
        """
        start_time = time.time()
        
        # Extract basic data
        asset = signal_data.get('asset_type', 'UNKNOWN')
        symbol = signal_data.get('symbol', 'EURUSD')
        timeframe = signal_data.get('timeframe_minutes', 15)
        current_price = signal_data.get('current_price', 0)
        
        print(f"\n{'='*80}")
        print(f"📊 PROCESSING HYBRID SIGNAL - ALL {len(self.agents)} AGENTS")
        print(f"{'='*80}")
        print(f"📡 Symbol: {symbol}")
        print(f"⏱️ Timeframe: {timeframe} minutes")
        print(f"💰 Price: {current_price:.5f}" if current_price > 0 else f"💰 Price: {current_price}")
        print(f"🤖 Agents: {len(self.agents)}")
        
        # Step 1: Get timeframe configuration
        tf_config = self.timeframe_config.get(timeframe, self.timeframe_config[15])
        
        # Step 2: Prepare market features with context
        volatility = signal_data.get('analysis_volatility', 0.5)
        rsi = signal_data.get('rsi', 50.0)
        
        # Generate candlestick data for agents that need it
        candles = self._generate_candlestick_data(current_price, volatility)
        
        market_features = {
            'timeframe': timeframe,
            'volatility': volatility,
            'asset': asset,
            'symbol': symbol,
            'strategy': tf_config['name'],
            'rsi': rsi,
            'candles': candles,
            'price': current_price,
            'high': signal_data.get('high', current_price * 1.001),
            'low': signal_data.get('low', current_price * 0.999),
            'volume': signal_data.get('volume', 1000),
            'bid': signal_data.get('bid', current_price * 0.9999),
            'ask': signal_data.get('ask', current_price * 1.0001),
        }
        
        # Step 3: Collect votes from ALL agents
        votes = {}
        agent_status = {}
        
        for agent_name, agent in self.agents.items():
            try:
                # Prepare data for agent
                agent_data = self._prepare_agent_data(signal_data, market_features, agent_name)
                
                # Get analysis
                result = agent.analyze(agent_data)
                
                # Parse result
                if isinstance(result, dict):
                    vote = result.get('vote', 'HOLD')
                    confidence = result.get('confidence', 50)
                    reasoning = result.get('reasoning', '')
                elif isinstance(result, tuple) and len(result) >= 2:
                    vote, confidence = result[0], result[1]
                    reasoning = result[2] if len(result) > 2 else ''
                else:
                    vote, confidence, reasoning = 'HOLD', 50, ''
                
                # Store vote
                votes[agent_name] = {
                    'vote': vote,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'weight': self.agent_weights.get(agent_name, 0.05)
                }
                
                agent_status[agent_name] = 'SUCCESS'
                
            except Exception as e:
                logger.error(f"Agent {agent_name} error: {e}")
                votes[agent_name] = {
                    'vote': 'HOLD',
                    'confidence': 50,
                    'reasoning': f'Error: {str(e)}',
                    'weight': self.agent_weights.get(agent_name, 0.05)
                }
                agent_status[agent_name] = f'ERROR: {str(e)}'
        
        # Step 4: Calculate weighted vote distribution
        weighted_votes = self._calculate_weighted_votes(votes)
        
        # Step 5: Analyze by agent type
        type_analysis = self._analyze_by_type(votes)
        
        # Step 6: Make decision based on weighted votes
        decision = self._make_decision(weighted_votes, tf_config, type_analysis)
        
        # Step 7: Calculate position size
        position_size = self._calculate_position_size(
            tf_config,
            decision['confidence'],
            volatility
        )
        
        # Step 8: Calculate stop loss and take profit
        stoploss = self._calculate_stoploss(current_price, tf_config, signal_data)
        takeprofit = self._calculate_takeprofit(current_price, stoploss, tf_config)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Step 9: Update statistics
        self._update_stats(decision, votes)
        
        # Step 10: Build result
        result = {
            'signal': signal_data,
            'symbol': symbol,
            'asset': asset,
            'timeframe': timeframe,
            'strategy': tf_config['name'],
            'votes': votes,
            'weighted_votes': weighted_votes,
            'type_analysis': type_analysis,
            'decision': decision,
            'risk_management': {
                'position_size': position_size,
                'stoploss': round(stoploss, 5),
                'takeprofit': round(takeprofit, 5),
                'risk_reward_ratio': round(abs(takeprofit - current_price) / abs(current_price - stoploss), 2) if stoploss != current_price else 0
            },
            'processing_time_ms': round(processing_time, 2),
            'agent_status': agent_status,
            'timestamp': datetime.now().isoformat()
        }
        
        # Step 11: Print summary
        self._print_summary(result)
        
        return result
    
    def _prepare_agent_data(self, signal_data: Dict, market_features: Dict, agent_name: str) -> Dict:
        """Prepare data specifically for each agent"""
        data = {
            'symbol': signal_data.get('symbol', 'EURUSD'),
            'price': signal_data.get('current_price', 0),
            'price1': signal_data.get('price1', 0),
            'price2': signal_data.get('price2', 0),
            'high': market_features.get('high', 0),
            'low': market_features.get('low', 0),
            'rsi': market_features.get('rsi', 50),
            'volume': market_features.get('volume', 0),
            'volatility': market_features.get('volatility', 0.5),
            'timeframe': market_features.get('timeframe', 15),
            'candles': market_features.get('candles', []),
            'asset_type': signal_data.get('asset_type', 'FOREX'),
            'bid': market_features.get('bid', 0),
            'ask': market_features.get('ask', 0),
        }
        
        # Agent-specific data
        if agent_name == 'Agent_X':
            # Spread reversion needs price1 and price2
            data['price1'] = signal_data.get('price1', signal_data.get('current_price', 0))
            data['price2'] = signal_data.get('price2', data['price1'] * 0.9)
            data['beta'] = signal_data.get('beta', 1.0)
        
        if agent_name == 'Agent_U':
            # Liquidity needs pip values
            data['pip_value'] = signal_data.get('pip_value', 0.0001)
        
        if agent_name == 'Agent_L':
            # Fundamental data
            data['interest_rate_diff'] = signal_data.get('interest_rate_diff', 0)
            data['economic_score'] = signal_data.get('economic_score', 50)
            data['central_bank_bias'] = signal_data.get('central_bank_bias', 'neutral')
            data['gdp_growth'] = signal_data.get('gdp_growth', 2.0)
            data['inflation'] = signal_data.get('inflation', 2.5)
        
        if agent_name == 'Agent_D':
            # Volatility data
            data['rsi'] = signal_data.get('rsi', 50)
            data['band_width'] = signal_data.get('band_width', 0)
        
        if agent_name == 'Agent_T':
            # Timing agent
            data['timeframe'] = signal_data.get('timeframe_minutes', 15)
            data['session'] = signal_data.get('trading_session', 'LONDON')
        
        return data
    
    def _calculate_weighted_votes(self, votes: Dict) -> Dict:
        """Calculate weighted votes"""
        weighted = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0, 'WATCH': 0.0}
        total_weight = 0
        confidence_weighted = 0
        total_confidence_weight = 0
        
        for agent, data in votes.items():
            vote = data.get('vote', 'HOLD')
            confidence = data.get('confidence', 50) / 100.0
            weight = data.get('weight', 0.05)
            
            weighted[vote] += weight
            total_weight += weight
            
            if vote in ['BUY', 'SELL']:
                confidence_weighted += confidence * weight
                total_confidence_weight += weight
        
        # Normalize
        if total_weight > 0:
            for key in weighted:
                weighted[key] = round(weighted[key] / total_weight * 100, 1)
        
        # Calculate average confidence
        avg_confidence = (confidence_weighted / total_confidence_weight * 100) if total_confidence_weight > 0 else 50
        
        # Determine consensus
        consensus = max(weighted.items(), key=lambda x: x[1])[0] if weighted else 'HOLD'
        
        return {
            'distribution': weighted,
            'total_weight': total_weight,
            'avg_confidence': round(avg_confidence, 1),
            'consensus': consensus
        }
    
    def _analyze_by_type(self, votes: Dict) -> Dict:
        """Analyze voting by agent type"""
        type_votes = {}
        
        for agent_type, agent_list in self.agent_types.items():
            type_votes[agent_type] = {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'WATCH': 0}
            type_confidence = 0
            type_count = 0
            
            for agent in agent_list:
                if agent in votes:
                    vote = votes[agent].get('vote', 'HOLD')
                    confidence = votes[agent].get('confidence', 50)
                    weight = votes[agent].get('weight', 0.05)
                    
                    type_votes[agent_type][vote] += weight
                    type_confidence += confidence * weight
                    type_count += weight
            
            # Normalize
            total = sum(type_votes[agent_type].values())
            if total > 0:
                for key in type_votes[agent_type]:
                    type_votes[agent_type][key] = round(type_votes[agent_type][key] / total * 100, 1)
            
            type_votes[agent_type]['avg_confidence'] = round(type_confidence / type_count, 1) if type_count > 0 else 50
            type_votes[agent_type]['consensus'] = max(type_votes[agent_type].items(), key=lambda x: x[1])[0] if total > 0 else 'HOLD'
        
        return type_votes
    
    def _make_decision(self, weighted_votes: Dict, tf_config: Dict, type_analysis: Dict) -> Dict:
        """Make decision based on weighted votes and type analysis"""
        distribution = weighted_votes['distribution']
        avg_confidence = weighted_votes['avg_confidence']
        
        buy_weight = distribution.get('BUY', 0)
        sell_weight = distribution.get('SELL', 0)
        hold_weight = distribution.get('HOLD', 0)
        watch_weight = distribution.get('WATCH', 0)
        
        # Check if WATCH has significant weight
        if watch_weight > 25 and watch_weight > hold_weight:
            return {
                'action': 'WATCH',
                'confidence': min(80, avg_confidence + 10),
                'reason': f"Agents watching for setup (WATCH: {watch_weight:.1f}%)"
            }
        
        # Check type consensus
        type_consensus = self._get_type_consensus(type_analysis)
        
        # Determine action with type analysis
        if buy_weight > sell_weight and buy_weight > hold_weight:
            action = 'BUY'
            confidence = min(90, avg_confidence + 5)
            
            # Boost confidence if technical and fundamental agree
            if type_consensus.get('technical') == 'BUY' and type_consensus.get('fundamental') == 'BUY':
                confidence = min(95, confidence + 10)
            
            reason = f"BUY consensus ({buy_weight:.1f}% vs {sell_weight:.1f}%)"
            
        elif sell_weight > buy_weight and sell_weight > hold_weight:
            action = 'SELL'
            confidence = min(90, avg_confidence + 5)
            
            # Boost confidence if technical and fundamental agree
            if type_consensus.get('technical') == 'SELL' and type_consensus.get('fundamental') == 'SELL':
                confidence = min(95, confidence + 10)
            
            reason = f"SELL consensus ({sell_weight:.1f}% vs {buy_weight:.1f}%)"
            
        elif buy_weight == sell_weight and buy_weight > 0:
            action = 'HOLD'
            confidence = max(50, avg_confidence - 10)
            reason = f"Tie between BUY ({buy_weight:.1f}%) and SELL ({sell_weight:.1f}%)"
            
        else:
            action = 'HOLD'
            confidence = max(50, avg_confidence - 5)
            reason = f"No clear consensus (BUY: {buy_weight:.1f}%, SELL: {sell_weight:.1f}%, HOLD: {hold_weight:.1f}%)"
        
        # Apply timeframe confidence threshold
        min_confidence = tf_config.get('min_confidence', 70)
        if confidence < min_confidence:
            action = 'HOLD'
            reason = f"Confidence {confidence:.1f}% below minimum {min_confidence}% for {tf_config['name']}"
        
        return {
            'action': action,
            'confidence': round(confidence, 1),
            'reason': reason,
            'buy_weight': buy_weight,
            'sell_weight': sell_weight,
            'hold_weight': hold_weight,
            'watch_weight': watch_weight,
            'type_consensus': type_consensus
        }
    
    def _get_type_consensus(self, type_analysis: Dict) -> Dict:
        """Get consensus by agent type"""
        consensus = {}
        for agent_type, data in type_analysis.items():
            if data.get('consensus') in ['BUY', 'SELL'] and data.get('avg_confidence', 0) > 60:
                consensus[agent_type] = data['consensus']
            else:
                consensus[agent_type] = 'NEUTRAL'
        return consensus
    
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
        
        if price <= 0:
            return 0
        
        # Use pip-based stops for forex
        pip_value = signal_data.get('pip_value', 0.0001)
        stop_pips = tf_config.get('stop_pips', 20)
        
        stoploss = price - (stop_pips * pip_value)
        
        return stoploss
    
    def _calculate_takeprofit(self, price: float, stoploss: float, tf_config: Dict) -> float:
        """Calculate take profit based on risk-reward ratio"""
        if price <= 0 or stoploss <= 0:
            return price * 1.01
        
        risk = abs(price - stoploss)
        reward_multiplier = tf_config.get('risk_reward', 2.0)
        
        return price + (risk * reward_multiplier)
    
    def _update_stats(self, decision: Dict, votes: Dict):
        """Update statistics"""
        self.stats['total_signals'] += 1
        
        action = decision.get('action', 'HOLD')
        if action == 'BUY':
            self.stats['buy_signals'] += 1
        elif action == 'SELL':
            self.stats['sell_signals'] += 1
        elif action == 'WATCH':
            self.stats['watch_signals'] += 1
        else:
            self.stats['hold_signals'] += 1
        
        # Update by agent
        for agent, data in votes.items():
            if agent not in self.stats['by_agent']:
                self.stats['by_agent'][agent] = {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'WATCH': 0}
            self.stats['by_agent'][agent][data.get('vote', 'HOLD')] += 1
    
    def _print_summary(self, result: Dict):
        """Print processing summary"""
        print(f"\n{'─'*80}")
        print(f"🗳️ WEIGHTED VOTING RESULTS:")
        weighted = result.get('weighted_votes', {})
        distribution = weighted.get('distribution', {})
        print(f"   BUY:  {distribution.get('BUY', 0):.1f}%  |  SELL: {distribution.get('SELL', 0):.1f}%")
        print(f"   HOLD: {distribution.get('HOLD', 0):.1f}%  |  WATCH: {distribution.get('WATCH', 0):.1f}%")
        print(f"   Avg Confidence: {weighted.get('avg_confidence', 50):.1f}%")
        print(f"   Consensus: {weighted.get('consensus', 'NONE')}")
        
        print(f"\n📊 AGENT TYPE ANALYSIS:")
        type_analysis = result.get('type_analysis', {})
        for agent_type, data in type_analysis.items():
            if data:
                consensus = data.get('consensus', 'NONE')
                conf = data.get('avg_confidence', 50)
                print(f"   {agent_type.upper()}: {consensus} ({conf:.0f}%)")
        
        print(f"\n📊 AGENT VOTES:")
        votes = result.get('votes', {})
        for agent, data in sorted(votes.items()):
            vote = data.get('vote', 'HOLD')
            confidence = data.get('confidence', 50)
            weight = data.get('weight', 0.05)
            
            if vote == 'BUY':
                icon = "🟢"
            elif vote == 'SELL':
                icon = "🔴"
            elif vote == 'WATCH':
                icon = "🟡"
            else:
                icon = "⚪"
            
            print(f"   {icon} {agent}: {vote} ({confidence:.0f}%) [w:{weight:.2f}]")
        
        decision = result.get('decision', {})
        print(f"\n✅ FINAL DECISION: {decision.get('action', 'HOLD')} ({decision.get('confidence', 50):.0f}%)")
        print(f"   {decision.get('reason', '')}")
        
        risk = result.get('risk_management', {})
        print(f"\n💰 RISK MANAGEMENT:")
        print(f"   Position Size: {risk.get('position_size', 0)} units")
        print(f"   Stop Loss: {risk.get('stoploss', 0):.5f}")
        print(f"   Take Profit: {risk.get('takeprofit', 0):.5f}")
        print(f"   Risk/Reward: 1:{risk.get('risk_reward_ratio', 0)}")
        
        print(f"\n⏱️ Processing Time: {result.get('processing_time_ms', 0)}ms")
        print(f"{'='*80}\n")
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self.stats
    
    def get_agent_weights(self) -> Dict:
        """Get current agent weights"""
        return self.agent_weights
    
    def update_agent_weight(self, agent_name: str, new_weight: float):
        """Update an agent's weight"""
        if agent_name in self.agent_weights:
            self.agent_weights[agent_name] = new_weight
            logger.info(f"Updated {agent_name} weight to {new_weight}")
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        status = {}
        for agent_name, agent in self.agents.items():
            status[agent_name] = {
                'type': self.agent_types.get(agent_name, 'unknown'),
                'weight': self.agent_weights.get(agent_name, 0),
                'specialization': getattr(agent, 'specialization', 'Unknown')
            }
        return status


# ============================================================
# TEST
# ============================================================

def main():
    """Test the hybrid signal processor"""
    print("=" * 80)
    print("TESTING HYBRID SIGNAL PROCESSOR - ALL 13 AGENTS")
    print("=" * 80)
    
    # Mock dependencies
    class MockDB:
        def save(self, data): pass
    
    class MockAgentManager:
        def collect_votes(self, data, features):
            return {}
    
    class MockSupervisor:
        pass
    
    class MockStrategyFramework:
        pass
    
    # Initialize processor
    processor = HybridSignalProcessor(
        db_manager=MockDB(),
        agent_manager=MockAgentManager(),
        supervisor=MockSupervisor(),
        strategy_framework=MockStrategyFramework()
    )
    
    # Test signal data
    test_data = {
        'symbol': 'EURUSD',
        'asset_type': 'FOREX',
        'timeframe_minutes': 15,
        'current_price': 1.1050,
        'price1': 1.1050,
        'price2': 1.3000,
        'rsi': 52.0,
        'analysis_volatility': 0.5,
        'volume': 5000,
        'high': 1.1070,
        'low': 1.1030,
        'pip_value': 0.0001,
        'sentiment': 10,
        'confidence_percent': 75,
        'interest_rate_diff': 0.25,
        'economic_score': 55,
        'central_bank_bias': 'neutral',
        'gdp_growth': 2.5,
        'inflation': 2.0,
        'trading_session': 'LONDON',
        'beta': 1.0
    }
    
    # Process
    result = processor.process_signal(test_data)
    
    print("\n✅ Test Complete")
    print(f"📊 Stats: {processor.get_stats()}")

if __name__ == "__main__":
    main()