# agents2/agent_manager.py

import logging
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import using relative or absolute paths
try:
    # Try relative imports first (if running as module)
    from .forex_agent_x import ForexAgentX
    from .forex_agent_u import ForexAgentU
    from .forex_agent_d import ForexAgentD
    from .pair_agents import (
        EURUSDAgent, GBPUSDAgent, USDJPYAgent, 
        AUDUSDAgent, USDCADAgent
    )
    from .cross_pair_agents import EURGBPAgent, EURJPYAgent
    from .base_pair_agent import BasePairAgent
except ImportError:
    # Fallback to absolute imports
    from forex_agent_x import ForexAgentX
    from forex_agent_u import ForexAgentU
    from forex_agent_d import ForexAgentD
    from pair_agents import (
        EURUSDAgent, GBPUSDAgent, USDJPYAgent, 
        AUDUSDAgent, USDCADAgent
    )
    from cross_pair_agents import EURGBPAgent, EURJPYAgent
    from base_pair_agent import BasePairAgent

logger = logging.getLogger(__name__)

class ForexAgentManager:
    """
    Unified Agent Manager that orchestrates ALL specialized agents:
    - X: Spread Reversion Specialist
    - U: Volatility & Position Sizing Specialist  
    - D: Trend Detection Specialist
    - Pair Agents: Specialized agents for each currency pair
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize agent groups
        self.specialist_agents = {}  # X, U, D
        self.pair_agents = {}        # EURUSD, GBPUSD, etc.
        
        # Agent results
        self.agent_results = {}
        self.consensus_signals = {}
        self.communication_log = []
        
        # Initialize all agents
        self._initialize_specialist_agents()
        self._initialize_pair_agents()
        
        # Agent weights for consensus
        self.agent_weights = self._initialize_agent_weights()
        
        # Performance tracking
        self.performance = {
            'specialists': {},
            'pairs': {},
            'overall': {'wins': 0, 'losses': 0, 'win_rate': 0.0}
        }
        
        logger.info("✅ Forex Agent Manager initialized")
        logger.info(f"   📊 {len(self.specialist_agents)} specialist agents")
        logger.info(f"   📊 {len(self.pair_agents)} pair agents")
        logger.info(f"   📊 Total: {len(self.specialist_agents) + len(self.pair_agents)} agents")
    
    def _initialize_specialist_agents(self):
        """Initialize the specialist agents (X, U, D)"""
        logger.info("Initializing specialist agents...")
        
        # Agent_X - Spread Reversion Specialist
        self.specialist_agents['X'] = ForexAgentX(
            name="Forex_X", 
            timeframe=self.config.get('timeframe', 'M15')
        )
        
        # Agent_U - Volatility & Position Sizing Specialist
        self.specialist_agents['U'] = ForexAgentU(
            name="Forex_U",
            timeframe=self.config.get('timeframe', 'M15')
        )
        
        # Agent_D - Trend Detection Specialist
        self.specialist_agents['D'] = ForexAgentD(
            name="Forex_D",
            timeframe=self.config.get('timeframe', 'M15')
        )
        
        logger.info(f"   ✅ {len(self.specialist_agents)} specialist agents initialized")
        logger.info(f"      Agents: {', '.join(self.specialist_agents.keys())}")
    
    def _initialize_pair_agents(self):
        """Initialize the specialized pair agents"""
        logger.info("Initializing pair agents...")
        
        try:
            # Major pairs
            self.pair_agents['EURUSD'] = EURUSDAgent()
            self.pair_agents['GBPUSD'] = GBPUSDAgent()
            self.pair_agents['USDJPY'] = USDJPYAgent()
            self.pair_agents['AUDUSD'] = AUDUSDAgent()
            self.pair_agents['USDCAD'] = USDCADAgent()
            
            # Cross pairs
            self.pair_agents['EURGBP'] = EURGBPAgent()
            self.pair_agents['EURJPY'] = EURJPYAgent()
        except NameError as e:
            logger.warning(f"Pair agents not available: {e}")
            logger.warning("Creating basic pair agents instead...")
            # Create basic agents if specialized ones aren't available
            for pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY']:
                self.pair_agents[pair] = BasePairAgent(pair, {'pair': pair})
        
        # Add any additional pairs from config
        extra_pairs = self.config.get('extra_pairs', {})
        for pair, config in extra_pairs.items():
            if pair not in self.pair_agents:
                # Create a basic pair agent for custom pairs
                self.pair_agents[pair] = BasePairAgent(pair, config)
        
        logger.info(f"   ✅ {len(self.pair_agents)} pair agents initialized")
        logger.info(f"      Pairs: {', '.join(self.pair_agents.keys())}")
    
    def _initialize_agent_weights(self) -> Dict:
        """
        Initialize weights for each agent in consensus calculation.
        Specialist agents have higher weights for their domain expertise.
        """
        weights = {
            # Specialist agents (higher weights for their expertise)
            'X': {'weight': 1.0, 'domain': 'Spread Reversion'},
            'U': {'weight': 0.8, 'domain': 'Volatility'},
            'D': {'weight': 0.8, 'domain': 'Trend'},
            
            # Pair agents (medium weights)
            'EURUSD': {'weight': 0.7, 'domain': 'Pair'},
            'GBPUSD': {'weight': 0.7, 'domain': 'Pair'},
            'USDJPY': {'weight': 0.7, 'domain': 'Pair'},
            'AUDUSD': {'weight': 0.6, 'domain': 'Pair'},
            'USDCAD': {'weight': 0.6, 'domain': 'Pair'},
            'EURGBP': {'weight': 0.5, 'domain': 'Cross'},
            'EURJPY': {'weight': 0.5, 'domain': 'Cross'},
        }
        
        # Add weights for any extra agents
        for agent_id in self.specialist_agents.keys():
            if agent_id not in weights and agent_id not in ['X', 'U', 'D']:
                weights[agent_id] = {'weight': 0.5, 'domain': 'Specialist'}
        
        return weights
    
    def process_market_data(self, market_data: Dict) -> Dict:
        """
        Process market data through ALL agents and generate consensus.
        """
        results = {}
        
        # 1. Process specialist agents (X, U, D, etc.)
        specialist_results = self._process_specialist_agents(market_data)
        results.update(specialist_results)
        
        # 2. Process pair agents (EURUSD, GBPUSD, etc.)
        pair_results = self._process_pair_agents(market_data)
        results.update(pair_results)
        
        # 3. Store results
        self.agent_results = results
        
        # 4. Generate consensus using weighted voting
        consensus = self._generate_weighted_consensus(results)
        self.consensus_signals = consensus
        
        # 5. Identify strongest signal
        strongest = self._identify_strongest_signal(results)
        
        # 6. Update communication
        self._update_communication(results, consensus)
        
        # 7. Check for agent disagreements
        disagreements = self._detect_disagreements(results)
        
        # 8. Log summary
        self._log_agent_summary(results, consensus)
        
        return {
            'agent_results': results,
            'consensus': consensus,
            'strongest_signal': strongest,
            'disagreements': disagreements,
            'specialist_results': specialist_results,
            'pair_results': pair_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _process_specialist_agents(self, market_data: Dict) -> Dict:
        """
        Process all specialist agents (X, U, D, etc.)
        """
        results = {}
        
        for agent_id, agent in self.specialist_agents.items():
            try:
                # Each specialist agent has its own analyze method
                result = agent.analyze(market_data)
                
                # Extract the key signal from each specialist
                if agent_id == 'X':
                    # Agent_X returns spread signals for each pair
                    # We need to extract the strongest signal
                    pair_signals = result.get('pair_signals', {})
                    if pair_signals:
                        # Find the strongest signal across all pairs
                        strongest_pair = max(
                            pair_signals.items(),
                            key=lambda x: x[1].get('confidence', 0) if x[1].get('action') != 'HOLD' else 0,
                            default=(None, {})
                        )
                        if strongest_pair[0] and strongest_pair[1].get('action') != 'HOLD':
                            results[f'X_{strongest_pair[0]}'] = {
                                'agent_id': 'X',
                                'pair': strongest_pair[0],
                                'action': strongest_pair[1]['action'],
                                'confidence': strongest_pair[1]['confidence'],
                                'reason': strongest_pair[1]['reason'],
                                'z_score': strongest_pair[1].get('z_score', 0),
                                'z_score_ema': strongest_pair[1].get('z_score_ema', 0),
                                'persistence': strongest_pair[1].get('persistence', 0),
                            }
                
                elif agent_id == 'U':
                    # Agent_U returns volatility signals
                    volatility_data = result.get('volatility', {})
                    if volatility_data:
                        for pair, data in volatility_data.items():
                            if data.get('regime') in ['HIGH', 'EXTREME']:
                                results[f'U_{pair}'] = {
                                    'agent_id': 'U',
                                    'pair': pair,
                                    'action': 'HOLD',  # Volatility doesn't give direction
                                    'confidence': 70 if data['regime'] == 'HIGH' else 85,
                                    'reason': f'High volatility detected: {data["regime"]}',
                                    'regime': data['regime'],
                                    'position_size': data.get('position_size', 0)
                                }
                
                elif agent_id == 'D':
                    # Agent_D returns trend signals
                    trend_data = result.get('signals', {})
                    if trend_data:
                        for pair, data in trend_data.items():
                            if data.get('trend_strength', 0) > 0.5:
                                action = 'BUY' if data['trend_direction'] == 'BULLISH' else 'SELL'
                                results[f'D_{pair}'] = {
                                    'agent_id': 'D',
                                    'pair': pair,
                                    'action': action,
                                    'confidence': min(85, 60 + abs(data['trend_strength']) * 20),
                                    'reason': f'Trend: {data["trend_direction"]} (Strength: {data["trend_strength"]:.2f})',
                                    'trend_strength': data['trend_strength'],
                                    'regime': data['regime'],
                                    'adx': data.get('adx', 0)
                                }
                
                else:
                    # Generic specialist agent
                    if result.get('signal') and result['signal'] != 'HOLD':
                        results[f'{agent_id}_general'] = {
                            'agent_id': agent_id,
                            'action': result['signal'],
                            'confidence': result.get('confidence', 50),
                            'reason': result.get('reasoning', ''),
                            'timestamp': result.get('timestamp', '')
                        }
                
                # Store full result for reference
                results[f'{agent_id}_full'] = result
                
            except Exception as e:
                logger.error(f"Error processing specialist agent {agent_id}: {e}")
                results[f'{agent_id}_error'] = {
                    'agent_id': agent_id,
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': f'Error: {e}'
                }
        
        return results
    
    def _process_pair_agents(self, market_data: Dict) -> Dict:
        """
        Process all pair agents (EURUSD, GBPUSD, etc.)
        """
        results = {}
        
        for pair, agent in self.pair_agents.items():
            try:
                result = agent.analyze(market_data)
                
                if result.get('action') and result['action'] != 'HOLD':
                    results[f'PAIR_{pair}'] = {
                        'agent_id': f'PAIR_{pair}',
                        'pair': pair,
                        'action': result['action'],
                        'confidence': result.get('confidence', 50),
                        'reason': result.get('reason', ''),
                        'z_score': result.get('z_score', 0),
                        'z_score_ema': result.get('z_score_ema', 0),
                        'persistence': result.get('persistence', 0),
                        'timestamp': result.get('timestamp', '')
                    }
                else:
                    results[f'PAIR_{pair}'] = {
                        'agent_id': f'PAIR_{pair}',
                        'pair': pair,
                        'action': 'HOLD',
                        'confidence': 50,
                        'reason': result.get('reason', 'Normal'),
                        'timestamp': result.get('timestamp', '')
                    }
                
                # Store full result
                results[f'PAIR_{pair}_full'] = result
                
            except Exception as e:
                logger.error(f"Error processing pair agent {pair}: {e}")
                results[f'PAIR_{pair}'] = {
                    'agent_id': f'PAIR_{pair}',
                    'pair': pair,
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': f'Error: {e}'
                }
        
        return results
    
    def _generate_weighted_consensus(self, results: Dict) -> Dict:
        """
        Generate consensus using weighted voting across all agents.
        """
        buy_weight = 0
        sell_weight = 0
        hold_weight = 0
        total_confidence = 0
        active_agents = 0
        
        # Track per-pair signals
        pair_signals = {}
        
        for key, result in results.items():
            # Skip full results
            if key.endswith('_full') or key.endswith('_error'):
                continue
            
            action = result.get('action', 'HOLD')
            confidence = result.get('confidence', 0)
            pair = result.get('pair', 'unknown')
            agent_id = result.get('agent_id', 'unknown')
            
            # Get weight for this agent
            if agent_id in self.agent_weights:
                weight = self.agent_weights[agent_id]['weight']
            elif agent_id in self.pair_agents:
                weight = self.agent_weights.get(agent_id, {'weight': 0.5})['weight']
            else:
                weight = 0.5
            
            # Weighted contribution
            weighted_confidence = confidence * weight
            
            if action == 'BUY':
                buy_weight += weighted_confidence
                active_agents += 1
                total_confidence += confidence
                
                # Track per-pair
                if pair not in pair_signals:
                    pair_signals[pair] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                pair_signals[pair]['BUY'] += 1
                
            elif action == 'SELL':
                sell_weight += weighted_confidence
                active_agents += 1
                total_confidence += confidence
                
                if pair not in pair_signals:
                    pair_signals[pair] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                pair_signals[pair]['SELL'] += 1
                
            else:
                hold_weight += 1
                if pair not in pair_signals:
                    pair_signals[pair] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                pair_signals[pair]['HOLD'] += 1
        
        # Determine consensus
        if active_agents == 0:
            return {
                'signal': 'HOLD',
                'confidence': 50,
                'reason': 'No active agents',
                'buy_weight': 0,
                'sell_weight': 0,
                'active_agents': 0,
                'pair_signals': pair_signals
            }
        
        avg_confidence = total_confidence / active_agents if active_agents > 0 else 0
        
        if buy_weight > sell_weight:
            signal = 'BUY'
            confidence = min(90, avg_confidence * (buy_weight / (buy_weight + sell_weight + 0.001)))
            reason = f'Consensus BUY (Weight: {buy_weight:.1f} vs {sell_weight:.1f})'
        elif sell_weight > buy_weight:
            signal = 'SELL'
            confidence = min(90, avg_confidence * (sell_weight / (buy_weight + sell_weight + 0.001)))
            reason = f'Consensus SELL (Weight: {sell_weight:.1f} vs {buy_weight:.1f})'
        else:
            signal = 'HOLD'
            confidence = 50
            reason = f'Consensus HOLD (BUY:{buy_weight:.1f} SELL:{sell_weight:.1f})'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reason': reason,
            'buy_weight': buy_weight,
            'sell_weight': sell_weight,
            'active_agents': active_agents,
            'avg_confidence': avg_confidence,
            'pair_signals': pair_signals
        }
    
    def _identify_strongest_signal(self, results: Dict) -> Dict:
        """
        Identify the strongest signal across all agents.
        """
        strongest = {
            'action': 'HOLD',
            'confidence': 0,
            'agent': None,
            'pair': None,
            'reason': ''
        }
        
        for key, result in results.items():
            if key.endswith('_full') or key.endswith('_error'):
                continue
            
            action = result.get('action', 'HOLD')
            confidence = result.get('confidence', 0)
            
            if action != 'HOLD' and confidence > strongest['confidence']:
                strongest = {
                    'action': action,
                    'confidence': confidence,
                    'agent': result.get('agent_id', 'unknown'),
                    'pair': result.get('pair', 'unknown'),
                    'reason': result.get('reason', ''),
                    'z_score': result.get('z_score', 0),
                    'z_score_ema': result.get('z_score_ema', 0)
                }
        
        return strongest
    
    def _detect_disagreements(self, results: Dict) -> Dict:
        """
        Detect significant disagreements between agents.
        """
        disagreements = {
            'buy_vs_sell': False,
            'specialist_vs_pair': False,
            'details': []
        }
        
        # Count signals by agent type
        specialist_buys = 0
        specialist_sells = 0
        pair_buys = 0
        pair_sells = 0
        
        for key, result in results.items():
            if key.endswith('_full') or key.endswith('_error'):
                continue
            
            action = result.get('action', 'HOLD')
            agent_id = result.get('agent_id', '')
            
            if action in ['BUY', 'SELL']:
                # Check if specialist or pair agent
                if agent_id in ['X', 'U', 'D'] or agent_id.startswith('X_') or agent_id.startswith('U_') or agent_id.startswith('D_'):
                    if action == 'BUY':
                        specialist_buys += 1
                    else:
                        specialist_sells += 1
                elif agent_id.startswith('PAIR_'):
                    if action == 'BUY':
                        pair_buys += 1
                    else:
                        pair_sells += 1
        
        # Check for specialist vs pair disagreement
        if specialist_buys > 0 and pair_sells > 0:
            disagreements['specialist_vs_pair'] = True
            disagreements['details'].append({
                'type': 'Specialist vs Pair',
                'message': f'Specialists BUY ({specialist_buys}) vs Pairs SELL ({pair_sells})'
            })
        elif specialist_sells > 0 and pair_buys > 0:
            disagreements['specialist_vs_pair'] = True
            disagreements['details'].append({
                'type': 'Specialist vs Pair',
                'message': f'Specialists SELL ({specialist_sells}) vs Pairs BUY ({pair_buys})'
            })
        
        # Check for buy vs sell imbalance
        total_buys = specialist_buys + pair_buys
        total_sells = specialist_sells + pair_sells
        
        if total_buys > 0 and total_sells > 0:
            disagreements['buy_vs_sell'] = True
            disagreements['details'].append({
                'type': 'Buy vs Sell',
                'message': f'BUY signals: {total_buys}, SELL signals: {total_sells}'
            })
        
        return disagreements
    
    def _update_communication(self, results: Dict, consensus: Dict):
        """
        Update communication log with agent messages.
        """
        # Log significant signals
        for key, result in results.items():
            if key.endswith('_full') or key.endswith('_error'):
                continue
            
            action = result.get('action', 'HOLD')
            confidence = result.get('confidence', 0)
            
            if action != 'HOLD' and confidence > 60:
                self.communication_log.append({
                    'from': result.get('agent_id', 'unknown'),
                    'pair': result.get('pair', 'unknown'),
                    'signal': action,
                    'confidence': confidence,
                    'reason': result.get('reason', ''),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Log consensus
        self.communication_log.append({
            'from': 'CONSENSUS',
            'signal': consensus['signal'],
            'confidence': consensus['confidence'],
            'reason': consensus['reason'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Limit log size
        if len(self.communication_log) > 1000:
            self.communication_log = self.communication_log[-500:]
    
    def _log_agent_summary(self, results: Dict, consensus: Dict):
        """
        Log a summary of all agent signals.
        """
        signals = []
        for key, result in results.items():
            if key.endswith('_full') or key.endswith('_error'):
                continue
            action = result.get('action', 'HOLD')
            if action != 'HOLD':
                signals.append(f"{result.get('agent_id', '')}:{action}({result.get('confidence', 0):.0f}%)")
        
        if signals:
            logger.info(f"📊 Agent Signals: {', '.join(signals)}")
            logger.info(f"📊 Consensus: {consensus['signal']} ({consensus['confidence']:.0f}%)")
            logger.info(f"📊 Buy Weight: {consensus.get('buy_weight', 0):.1f}, Sell Weight: {consensus.get('sell_weight', 0):.1f}")
    
    def get_agent_status(self) -> Dict:
        """
        Get status of all agents.
        """
        status = {
            'specialists': {},
            'pair_agents': {},
            'communication_log': self.communication_log[-20:],
            'performance': self.performance
        }
        
        # Specialist agents status
        for agent_id, agent in self.specialist_agents.items():
            status['specialists'][agent_id] = {
                'type': agent.__class__.__name__,
                'signal': getattr(agent, 'signal', 'HOLD'),
                'confidence': getattr(agent, 'confidence', 0),
            }
        
        # Pair agents status
        for pair, agent in self.pair_agents.items():
            status['pair_agents'][pair] = {
                'type': agent.__class__.__name__,
                'position': getattr(agent, 'position', 0),
                'z_score': getattr(agent, 'z_score', 0),
                'z_score_ema': getattr(agent, 'z_score_ema', 0),
                'persistence': getattr(agent, 'persistence', 0),
                'signal': getattr(agent, 'signal', 'HOLD'),
                'confidence': getattr(agent, 'confidence', 0),
                'trades': len(getattr(agent, 'trades', [])),
                'pnl': getattr(agent, 'pnl', 0),
                'win_rate': getattr(agent, 'win_rate', 0)
            }
        
        return status
    
    def get_trading_recommendation(self) -> Dict:
        """
        Get final trading recommendation with position sizing.
        """
        # Get consensus
        consensus = self.consensus_signals
        
        # Get volatility recommendation from Agent_U
        volatility_rec = None
        for key, result in self.agent_results.items():
            if 'U_' in key and 'regime' in result:
                volatility_rec = result
                break
        
        # Get strongest trend from Agent_D
        trend_rec = None
        for key, result in self.agent_results.items():
            if 'D_' in key and 'trend_strength' in result:
                if not trend_rec or result.get('trend_strength', 0) > trend_rec.get('trend_strength', 0):
                    trend_rec = result
        
        # Calculate position size based on volatility
        position_size = 1.0
        if volatility_rec:
            regime = volatility_rec.get('regime', 'NORMAL')
            if regime == 'EXTREME':
                position_size = 0.25
            elif regime == 'HIGH':
                position_size = 0.5
            elif regime == 'LOW':
                position_size = 1.5
        
        return {
            'signal': consensus.get('signal', 'HOLD'),
            'confidence': consensus.get('confidence', 50),
            'reason': consensus.get('reason', ''),
            'position_size': position_size,
            'volatility_regime': volatility_rec.get('regime', 'NORMAL') if volatility_rec else 'NORMAL',
            'trend_strength': trend_rec.get('trend_strength', 0) if trend_rec else 0,
            'best_pair': self._identify_best_pair(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _identify_best_pair(self) -> Dict:
        """
        Identify the best pair to trade based on all agents.
        """
        pair_scores = {}
        
        for key, result in self.agent_results.items():
            if key.endswith('_full') or key.endswith('_error'):
                continue
            
            pair = result.get('pair', 'unknown')
            action = result.get('action', 'HOLD')
            confidence = result.get('confidence', 0)
            
            if pair != 'unknown':
                if pair not in pair_scores:
                    pair_scores[pair] = {'score': 0, 'signals': 0, 'action': 'HOLD', 'buy_count': 0, 'sell_count': 0}
                
                if action != 'HOLD':
                    pair_scores[pair]['score'] += confidence
                    pair_scores[pair]['signals'] += 1
                    # Track majority action
                    if action == 'BUY':
                        pair_scores[pair]['buy_count'] = pair_scores[pair].get('buy_count', 0) + 1
                    elif action == 'SELL':
                        pair_scores[pair]['sell_count'] = pair_scores[pair].get('sell_count', 0) + 1
        
        # Find best pair
        best_pair = None
        best_score = 0
        
        for pair, data in pair_scores.items():
            if data['signals'] > 0:
                avg_score = data['score'] / data['signals']
                buy_count = data.get('buy_count', 0)
                sell_count = data.get('sell_count', 0)
                action = 'BUY' if buy_count > sell_count else 'SELL' if sell_count > buy_count else 'HOLD'
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_pair = {
                        'pair': pair,
                        'action': action,
                        'confidence': avg_score,
                        'signals': data['signals'],
                        'buy_count': buy_count,
                        'sell_count': sell_count
                    }
        
        return best_pair
    
    def update_agent_performance(self, trade_result: Dict):
        """
        Update performance metrics for all agents.
        """
        pair = trade_result.get('pair', 'unknown')
        pnl = trade_result.get('pnl', 0)
        was_win = pnl > 0
        
        # Update pair agent performance
        if pair in self.pair_agents:
            agent = self.pair_agents[pair]
            if hasattr(agent, 'trades'):
                agent.trades.append(trade_result)
                agent.pnl = getattr(agent, 'pnl', 0) + pnl
                
                wins = len([t for t in agent.trades if t.get('pnl', 0) > 0])
                losses = len(agent.trades) - wins
                agent.win_rate = wins / len(agent.trades) if agent.trades else 0
                
                # Update performance tracking
                self.performance['pairs'][pair] = {
                    'wins': wins,
                    'losses': losses,
                    'win_rate': agent.win_rate,
                    'pnl': agent.pnl,
                    'trades': len(agent.trades)
                }
        
        # Update overall performance
        if was_win:
            self.performance['overall']['wins'] += 1
        else:
            self.performance['overall']['losses'] += 1
        
        total = self.performance['overall']['wins'] + self.performance['overall']['losses']
        if total > 0:
            self.performance['overall']['win_rate'] = self.performance['overall']['wins'] / total
    
    def reset_daily_stats(self):
        """Reset daily statistics for all agents."""
        for agent in self.specialist_agents.values():
            if hasattr(agent, 'reset_daily_stats'):
                agent.reset_daily_stats()
        
        for agent in self.pair_agents.values():
            if hasattr(agent, 'reset_daily_stats'):
                agent.reset_daily_stats()
        
        logger.info("🔄 Daily stats reset for all agents")


# Test the agent manager
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create agent manager
    manager = ForexAgentManager()
    
    # Test with sample market data
    test_data = {
        'EURUSD': 1.1000,
        'GBPUSD': 1.3000,
        'USDJPY': 150.00,
        'AUDUSD': 0.7000,
        'USDCAD': 1.3500,
        'EURGBP': 0.8500,
        'EURJPY': 165.00,
        'GOLD': 2000.00,
        'OIL': 80.00,
        'engine_state': {
            'engine_speed': 0.2,
            'engine_direction': 'FORWARD',
            'engine_health': 85.0
        }
    }
    
    # Process market data
    result = manager.process_market_data(test_data)
    
    # Print results
    print("\n=== AGENT RESULTS ===")
    print(f"Consensus: {result['consensus']['signal']} ({result['consensus']['confidence']:.1f}%)")
    print(f"Strongest: {result['strongest_signal']['action']} from {result['strongest_signal']['agent']}")
    print(f"Disagreements: {result['disagreements']['details']}")
    
    print("\n=== RECOMMENDATION ===")
    recommendation = manager.get_trading_recommendation()
    print(f"Signal: {recommendation['signal']}")
    print(f"Confidence: {recommendation['confidence']:.1f}%")
    print(f"Position Size: {recommendation['position_size']}")
    print(f"Best Pair: {recommendation['best_pair']}")