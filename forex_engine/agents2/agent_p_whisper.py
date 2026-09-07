# backend/agents/agent_p_whisper.py
"""
Agent_P - Whisper Analyst / Cross Pair Agent (FOREX ADAPTED)
Now serves as Cross Pair Agent for Forex with whisper detection
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
import logging
import numpy as np
import random
from datetime import datetime
import sys
import os

# ============================================
# HANDLE BASE AGENT IMPORT
# ============================================
try:
    # Try relative import first (when used as module)
    from .base_agent import BaseAgent
except ImportError:
    try:
        # Try absolute import (when in backend/agents folder)
        from backend.agents.base_agent import BaseAgent
    except ImportError:
        # Try direct import (when in same folder)
        try:
            from base_agent import BaseAgent
        except ImportError:
            # If base agent not found, create a minimal BaseAgent
            class BaseAgent:
                """Minimal BaseAgent for standalone testing"""
                def __init__(self, name="BaseAgent", agent_type="General", specialization="General"):
                    self.name = name
                    self.agent_type = agent_type
                    self.specialization = specialization
                    self.xp_points = 0
                    self.token_balance = 0
                    self.trust_weight = 1.0
                    self.total_votes = 0
                    self.correct_votes = 0
                    self.vote_accuracy = 0.0
                    self.knowledge_shared_count = 0
                    self.timeframe = None
                    self.role = None
                
                def get_status(self):
                    return {
                        'name': self.name,
                        'type': self.agent_type,
                        'specialization': self.specialization,
                        'xp_points': self.xp_points,
                        'token_balance': self.token_balance,
                        'trust_weight': self.trust_weight
                    }
                
                def update_from_reward(self, was_correct, xp_gained=0, xp_lost=0, asset=None, timeframe=None):
                    if was_correct:
                        self.xp_points += xp_gained or 10
                        self.correct_votes += 1
                    else:
                        self.xp_points = max(0, self.xp_points - (xp_lost or 5))
                    self.total_votes += 1
                    if self.total_votes > 0:
                        self.vote_accuracy = self.correct_votes / self.total_votes
                    return {'success': True}
            
            print("⚠️ BaseAgent not found - using minimal BaseAgent")

# Try importing price helpers
try:
    from price_cache_manager import get_price_for_agent, get_any_price
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    try:
        from backend.utils.price_cache_manager import get_price_for_agent, get_any_price
        from backend.utils.price_helper import get_price_with_fallback, get_price_with_details
    except ImportError:
        # Define dummy functions if imports fail
        def get_price_for_agent(agent_name, symbol):
            return None
        def get_any_price(symbol):
            return None
        def get_price_with_fallback(symbol, agent_name):
            return 0
        def get_price_with_details(symbol, agent_name):
            return {'mid': 0}
        print("⚠️ Price helpers not found - using dummy functions")

logger = logging.getLogger(__name__)

class WhisperAnalyst(BaseAgent):
    """
    Agent P - Whisper Analyst / Cross Pair Agent (FOREX)
    Detects hidden institutional activity across currency pairs through:
    1. Cross-pair correlation analysis
    2. Dark Pool volume analysis
    3. Unusual options flow (forex options)
    4. Order book spoofing detection
    5. Triangular arbitrage detection
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_P",
            agent_type="Cross Pair Agent",
            specialization="Detects whispers and cross-pair institutional activity"
        )
        
        # ============================================
        # CROSS PAIR CONFIGURATION
        # ============================================
        self.cross_pairs = [
            ('EURUSD', 'GBPUSD'),   # EUR/GBP correlation
            ('EURUSD', 'USDJPY'),   # EUR/JPY correlation
            ('GBPUSD', 'USDJPY'),   # GBP/JPY correlation
            ('AUDUSD', 'USDCAD'),   # Commodity correlation
            ('EURUSD', 'AUDUSD'),   # Risk correlation
            ('GBPUSD', 'AUDUSD'),   # Risk correlation
            ('EURJPY', 'GBPJPY'),   # Cross correlation
        ]
        
        # ============================================
        # STATE MANAGEMENT
        # ============================================
        self.pair_states = {}
        self.correlation_history = {}
        
        for pair1, pair2 in self.cross_pairs:
            key = f"{pair1}_{pair2}"
            self.correlation_history[key] = deque(maxlen=50)
            
            # Initialize pair states
            for pair in [pair1, pair2]:
                if pair not in self.pair_states:
                    self.pair_states[pair] = {
                        'price_history': deque(maxlen=100),
                        'spread_history': deque(maxlen=60),
                        'z_score': 0.0,
                        'position': 0,
                        'entry_price': 0.0,
                        'signal': 'HOLD',
                        'confidence': 50,
                        'cross_pair_bias': 0.0,  # -1 bearish, +1 bullish
                    }
        
        # ============================================
        # WHISPER DETECTION PARAMETERS
        # ============================================
        self.correlation_threshold = 0.7
        self.z_score_threshold = 2.0
        self.whisper_confidence_threshold = 60
        
        # Demo mode (compatible with original)
        self.demo_mode = True
        self.api_key = None  # Add your API key when ready
        
        # ============================================
        # RANDOM EVIDENCE GENERATION (Demo Mode)
        # ============================================
        self.evidence_sources = [
            'dark_pool', 'options', 'spoofing', 'cross_check',
            'triangular_arbitrage', 'correlation_break'
        ]
        
        print(f"   ✅ {self.name} (Cross Pair Agent) initialized")
        print(f"      Tracking {len(self.cross_pairs)} cross-pair relationships")
        print(f"      Monitoring {len(self.pair_states)} currency pairs")
    
    # ============================================
    # CORE ANALYSIS METHODS
    # ============================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Main analysis function - detects cross-pair whispers
        
        Args:
            signal_data: Dictionary with market data
        
        Returns:
            Vote (BUY/SELL/HOLD) based on detected activity
        """
        try:
            # Get current pair
            pair = signal_data.get('pair', 'EURUSD')
            current_price = signal_data.get('price', 0)
            
            # If no price, try to get from market data
            if current_price == 0:
                current_price = signal_data.get('current_price', 0)
            
            # Update pair state
            if pair in self.pair_states:
                self.pair_states[pair]['price_history'].append(current_price)
            
            # ============================================
            # 1. CROSS PAIR CORRELATION ANALYSIS
            # ============================================
            cross_evidence = self._analyze_cross_pairs(signal_data)
            
            # ============================================
            # 2. WHISPER DETECTION (Original Agent P Logic)
            # ============================================
            whisper_evidence = self._collect_whisper_evidence(pair, signal_data)
            
            # ============================================
            # 3. TRIANGULAR ARBITRAGE DETECTION
            # ============================================
            arbitrage_evidence = self._detect_triangular_arbitrage(signal_data)
            
            # ============================================
            # 4. CROSS PAIR BIAS CALCULATION
            # ============================================
            if pair in self.pair_states:
                bias = self._calculate_cross_pair_bias(pair, signal_data)
                self.pair_states[pair]['cross_pair_bias'] = bias
            
            # ============================================
            # 5. COMBINE ALL EVIDENCE
            # ============================================
            all_evidence = cross_evidence + whisper_evidence + arbitrage_evidence
            
            # ============================================
            # 6. MAKE DECISION
            # ============================================
            decision = self._make_decision(all_evidence, current_price, pair)
            
            # Store signal in state
            if pair in self.pair_states:
                self.pair_states[pair]['signal'] = decision['vote']
                self.pair_states[pair]['confidence'] = decision['confidence']
            
            return decision
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': f"Analysis error: {e}",
                'evidence': [],
                'timestamp': datetime.now().isoformat()
            }
    
    # ============================================
    # CROSS PAIR ANALYSIS
    # ============================================
    
    def _analyze_cross_pairs(self, market_data: Dict) -> List[Dict]:
        """
        Analyze cross-pair correlations and detect divergences
        """
        evidence = []
        
        for pair1, pair2 in self.cross_pairs:
            # Get prices
            price1 = market_data.get(pair1, 0)
            price2 = market_data.get(pair2, 0)
            
            if price1 <= 0 or price2 <= 0:
                continue
            
            # Update pair states
            if pair1 in self.pair_states:
                self.pair_states[pair1]['price_history'].append(price1)
            if pair2 in self.pair_states:
                self.pair_states[pair2]['price_history'].append(price2)
            
            # Calculate correlation
            key = f"{pair1}_{pair2}"
            corr = self._calculate_correlation(pair1, pair2)
            
            if corr is not None:
                self.correlation_history[key].append(corr)
                
                # Detect correlation break
                if len(self.correlation_history[key]) > 20:
                    avg_corr = np.mean(list(self.correlation_history[key])[-20:])
                    
                    if abs(corr - avg_corr) > 0.3:
                        # Correlation break detected
                        direction = self._determine_correlation_direction(pair1, pair2, price1, price2)
                        
                        evidence.append({
                            'type': 'correlation_break',
                            'strength': min(90, 60 + abs(corr - avg_corr) * 100),
                            'direction': direction,
                            'message': f"📊 CORRELATION BREAK: {pair1}/{pair2} correlation shifted from {avg_corr:.2f} to {corr:.2f}",
                            'pairs': [pair1, pair2]
                        })
        
        return evidence
    
    def _calculate_correlation(self, pair1: str, pair2: str) -> Optional[float]:
        """
        Calculate correlation between two pairs
        """
        if pair1 not in self.pair_states or pair2 not in self.pair_states:
            return None
        
        prices1 = list(self.pair_states[pair1]['price_history'])
        prices2 = list(self.pair_states[pair2]['price_history'])
        
        if len(prices1) < 20 or len(prices2) < 20:
            return None
        
        # Calculate returns
        returns1 = [prices1[i] / prices1[i-1] - 1 for i in range(1, len(prices1))]
        returns2 = [prices2[i] / prices2[i-1] - 1 for i in range(1, len(prices2))]
        
        # Align lengths
        min_len = min(len(returns1), len(returns2))
        returns1 = returns1[-min_len:]
        returns2 = returns2[-min_len:]
        
        if min_len < 20:
            return None
        
        # Calculate correlation
        corr = np.corrcoef(returns1, returns2)[0, 1]
        
        return corr
    
    def _determine_correlation_direction(self, pair1: str, pair2: str, price1: float, price2: float) -> str:
        """
        Determine direction of correlation break
        """
        # Simple logic - if one is rising and other falling, direction is clear
        if len(self.pair_states[pair1]['price_history']) > 5:
            p1_change = price1 / list(self.pair_states[pair1]['price_history'])[-5] - 1
            p2_change = price2 / list(self.pair_states[pair2]['price_history'])[-5] - 1
            
            if p1_change > 0.001 and p2_change < -0.001:
                return 'SELL'  # Divergence - sell the rising one
            elif p1_change < -0.001 and p2_change > 0.001:
                return 'BUY'   # Divergence - buy the rising one
        
        return 'HOLD'
    
    def _calculate_cross_pair_bias(self, pair: str, market_data: Dict) -> float:
        """
        Calculate cross-pair bias for a specific pair
        """
        bias = 0.0
        total_weight = 0
        
        for p1, p2 in self.cross_pairs:
            if pair == p1:
                other = p2
                weight = 0.5
            elif pair == p2:
                other = p1
                weight = 0.5
            else:
                continue
            
            # Get correlation
            key = f"{p1}_{p2}"
            if key in self.correlation_history and len(self.correlation_history[key]) > 0:
                current_corr = list(self.correlation_history[key])[-1]
                
                # Get price changes
                price_pair = market_data.get(pair, 0)
                price_other = market_data.get(other, 0)
                
                if price_pair > 0 and price_other > 0:
                    # Calculate relative strength
                    if pair == p1:
                        rel_strength = price_pair / price_other
                    else:
                        rel_strength = price_other / price_pair
                    
                    # Apply to bias
                    bias += rel_strength * current_corr * weight
                    total_weight += weight
        
        if total_weight > 0:
            return bias / total_weight
        return 0.0
    
    # ============================================
    # WHISPER DETECTION (Original Agent P Logic)
    # ============================================
    
    def _collect_whisper_evidence(self, ticker: str, signal_data: Dict) -> List[Dict]:
        """
        Collect whisper evidence from multiple sources
        """
        evidence = []
        
        # 1. Dark Pool Analysis
        dark_pool_data = self._analyze_dark_pools(ticker)
        if dark_pool_data['leak_detected']:
            evidence.append({
                'type': 'dark_pool',
                'strength': dark_pool_data['strength'],
                'direction': dark_pool_data['direction'],
                'message': dark_pool_data['message']
            })
        
        # 2. Unusual Options Flow (Forex Options)
        options_data = self._analyze_options_flow(ticker)
        if options_data['unusual_detected']:
            evidence.append({
                'type': 'options',
                'strength': options_data['urgency'],
                'direction': options_data['direction'],
                'message': options_data['message']
            })
        
        # 3. Order Book Spoofing
        spoofing_data = self._detect_spoofing(ticker)
        if spoofing_data['spoof_detected']:
            evidence.append({
                'type': 'spoofing',
                'strength': 85,
                'direction': spoofing_data['direction'],
                'message': spoofing_data['message']
            })
        
        # 4. Cross-agent interrogation
        cross_check = self._cross_examine_agents(ticker)
        if cross_check['confirmed']:
            evidence.append({
                'type': 'cross_check',
                'strength': cross_check['confidence'],
                'direction': cross_check['direction'],
                'message': cross_check['message']
            })
        
        return evidence
    
    def _analyze_dark_pools(self, ticker: str) -> Dict:
        """Detect dark pool activity (Forex dark pools)"""
        if self.demo_mode:
            has_activity = random.random() < 0.2
            
            if has_activity:
                is_accumulation = random.random() > 0.3
                strength = random.randint(60, 95)
                
                if is_accumulation:
                    return {
                        'leak_detected': True,
                        'strength': strength,
                        'direction': 'BUY',
                        'message': f"🐋 DARK POOL: {strength}% of {ticker} volume hidden. Large institutions accumulating silently."
                    }
                else:
                    return {
                        'leak_detected': True,
                        'strength': strength,
                        'direction': 'SELL',
                        'message': f"🐻 DARK POOL: Large hidden sell orders detected in {ticker}. Distribution underway."
                    }
            
            return {
                'leak_detected': False,
                'strength': 0,
                'direction': 'NEUTRAL',
                'message': "No unusual dark pool activity"
            }
        
        return {'leak_detected': False, 'strength': 0, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _analyze_options_flow(self, ticker: str) -> Dict:
        """Detect unusual options activity (Forex options)"""
        if self.demo_mode:
            has_unusual = random.random() < 0.15
            
            if has_unusual:
                is_bullish = random.random() > 0.4
                urgency = random.randint(70, 98)
                
                if is_bullish:
                    return {
                        'unusual_detected': True,
                        'urgency': urgency,
                        'direction': 'BUY',
                        'message': f"🔥 OPTION WHISPER: Massive OTM Call buying ({urgency}% urgency) on {ticker}. Someone knows something."
                    }
                else:
                    return {
                        'unusual_detected': True,
                        'urgency': urgency,
                        'direction': 'SELL',
                        'message': f"⚠️ OPTION WHISPER: Unusual OTM Put buying on {ticker}. Hedge funds protecting against downside."
                    }
            
            return {
                'unusual_detected': False,
                'urgency': 0,
                'direction': 'NEUTRAL',
                'message': "Options flow normal"
            }
        
        return {'unusual_detected': False, 'urgency': 0, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _detect_spoofing(self, ticker: str) -> Dict:
        """Detect order book spoofing"""
        if self.demo_mode:
            has_spoof = random.random() < 0.1
            
            if has_spoof:
                is_bullish_spoof = random.random() > 0.5
                direction = 'BUY' if is_bullish_spoof else 'SELL'
                message = f"🎭 SPOOFING DETECTED on {ticker}: Large orders vanishing instantly. Expect {direction} reversal."
                return {
                    'spoof_detected': True,
                    'direction': direction,
                    'message': message
                }
            
            return {
                'spoof_detected': False,
                'direction': 'NEUTRAL',
                'message': "Order book clean"
            }
        
        return {'spoof_detected': False, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _cross_examine_agents(self, ticker: str) -> Dict:
        """Ask other agents indirect questions"""
        whale_response = random.choice(['quiet', 'active', 'very_active'])
        volume_response = random.choice(['normal', 'increasing', 'decreasing'])
        
        if whale_response == 'very_active' and volume_response == 'increasing':
            return {
                'confirmed': True,
                'confidence': 85,
                'direction': 'BUY',
                'message': "🔍 CROSS-CHECK: Whale tracker confirms activity. Whisper validated!"
            }
        elif whale_response == 'active':
            return {
                'confirmed': True,
                'confidence': 65,
                'direction': 'BUY',
                'message': "📡 CROSS-CHECK: Other agents sense unusual activity."
            }
        
        return {
            'confirmed': False,
            'confidence': 0,
            'direction': 'NEUTRAL',
            'message': "No confirmation from other agents"
        }
    
    # ============================================
    # TRIANGULAR ARBITRAGE DETECTION
    # ============================================
    
    def _detect_triangular_arbitrage(self, market_data: Dict) -> List[Dict]:
        """
        Detect triangular arbitrage opportunities in forex
        """
        evidence = []
        
        # Common triangular relationships
        triangles = [
            ('EURUSD', 'USDJPY', 'EURJPY'),
            ('EURUSD', 'GBPUSD', 'EURGBP'),
            ('GBPUSD', 'USDJPY', 'GBPJPY'),
            ('AUDUSD', 'USDJPY', 'AUDJPY'),
            ('USDCHF', 'USDJPY', 'CHFJPY'),
        ]
        
        for pair1, pair2, pair3 in triangles:
            price1 = market_data.get(pair1, 0)
            price2 = market_data.get(pair2, 0)
            price3 = market_data.get(pair3, 0)
            
            if price1 <= 0 or price2 <= 0 or price3 <= 0:
                continue
            
            # Calculate implied cross rate
            # For EURUSD * USDJPY = EURJPY
            if pair1 == 'EURUSD' and pair2 == 'USDJPY' and pair3 == 'EURJPY':
                implied = price1 * price2
                actual = price3
                
                if actual > 0:
                    deviation = (actual - implied) / implied
                    
                    if abs(deviation) > 0.005:  # 0.5% deviation
                        direction = 'BUY' if deviation > 0 else 'SELL'
                        evidence.append({
                            'type': 'triangular_arbitrage',
                            'strength': min(90, 50 + abs(deviation) * 2000),
                            'direction': direction,
                            'message': f"🔄 TRIANGULAR ARBITRAGE: {pair1}*{pair2} vs {pair3} deviation of {deviation:.2%}",
                            'pairs': [pair1, pair2, pair3]
                        })
        
        return evidence
    
    # ============================================
    # DECISION MAKING
    # ============================================
    
    def _make_decision(self, evidence: List[Dict], current_price: float, pair: str) -> Dict:
        """
        Analyze all evidence and make final decision
        """
        if not evidence:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': "📻 SILENT: No cross-pair whispers or institutional footprints detected.",
                'evidence': [],
                'leak_score': 0,
                'cross_pair_bias': self.pair_states.get(pair, {}).get('cross_pair_bias', 0),
                'timestamp': datetime.now().isoformat()
            }
        
        total_strength = 0
        buy_signals = 0
        sell_signals = 0
        evidence_by_type = {}
        
        for e in evidence:
            total_strength += e['strength']
            if e['direction'] == 'BUY':
                buy_signals += 1
            elif e['direction'] == 'SELL':
                sell_signals += 1
            
            e_type = e.get('type', 'unknown')
            if e_type not in evidence_by_type:
                evidence_by_type[e_type] = []
            evidence_by_type[e_type].append(e)
        
        avg_strength = total_strength / len(evidence)
        leak_score = avg_strength
        
        # Cross-pair bias adjustment
        cross_bias = self.pair_states.get(pair, {}).get('cross_pair_bias', 0)
        
        # Adjust decision based on cross-pair bias
        if cross_bias > 0.2:
            buy_signals += 1  # Bias towards buying
        elif cross_bias < -0.2:
            sell_signals += 1  # Bias towards selling
        
        # Make final decision
        if buy_signals > sell_signals and leak_score > self.whisper_confidence_threshold:
            vote = 'BUY'
            confidence = min(95, leak_score + abs(cross_bias) * 10)
            reasoning = self._generate_whisper_report(evidence, 'BULLISH', cross_bias)
            
        elif sell_signals > buy_signals and leak_score > self.whisper_confidence_threshold:
            vote = 'SELL'
            confidence = min(95, leak_score + abs(cross_bias) * 10)
            reasoning = self._generate_whisper_report(evidence, 'BEARISH', cross_bias)
            
        elif leak_score > 60:
            vote = 'WATCH'
            confidence = leak_score
            reasoning = self._generate_whisper_report(evidence, 'MIXED', cross_bias)
            
        else:
            vote = 'HOLD'
            confidence = 40
            reasoning = "📻 Weak signals. Waiting for stronger cross-pair confirmation."
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': round(confidence, 1),
            'reasoning': reasoning,
            'evidence': evidence,
            'evidence_by_type': evidence_by_type,
            'leak_score': round(leak_score, 1),
            'cross_pair_bias': round(cross_bias, 3),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'pair': pair,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_whisper_report(self, evidence, sentiment, cross_bias) -> str:
        """
        Generate human-readable whisper report
        """
        report = f"🕵️ CROSS-PAIR WHISPER ANALYSIS: {sentiment}\n\n"
        
        # Group evidence by type
        evidence_groups = {}
        for e in evidence:
            e_type = e.get('type', 'unknown')
            if e_type not in evidence_groups:
                evidence_groups[e_type] = []
            evidence_groups[e_type].append(e)
        
        for e_type, items in evidence_groups.items():
            report += f"📌 {e_type.upper()}: ({len(items)} signals)\n"
            for item in items:
                report += f"   • {item['message']}\n"
            report += "\n"
        
        if cross_bias != 0:
            direction = "BULLISH" if cross_bias > 0 else "BEARISH"
            report += f"📊 CROSS-PAIR BIAS: {direction} ({cross_bias:.2f})\n"
        
        avg_strength = sum(e['strength'] for e in evidence) / len(evidence) if evidence else 0
        report += f"\n📊 Leak Confidence: {avg_strength:.0f}%"
        
        return report
    
    # ============================================
    # COMPATIBILITY METHODS
    # ============================================
    
    def predict(self, signal_data: Dict, market_features: Dict) -> Tuple[str, float]:
        """
        Original predict method - maintained for compatibility
        
        Returns:
            (action, confidence) tuple
        """
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def vote(self, signal_data: Dict, market_features: Dict) -> Dict:
        """
        Vote method for the agent voting system
        """
        result = self.analyze(signal_data)
        return {
            'agent': self.name,
            'pair': signal_data.get('pair', 'EURUSD'),
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'evidence': result.get('evidence', []),
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_signal(self, signal_data: Dict = None) -> Dict:
        """
        Analyze signal for the trading cycle
        """
        if signal_data is None:
            signal_data = {}
        
        result = self.analyze(signal_data)
        
        return {
            'agent': self.name,
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'pair': signal_data.get('pair', 'EURUSD'),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict:
        """
        Get status of all tracked pairs
        """
        status = {
            'name': self.name,
            'type': self.agent_type,
            'pairs': {},
            'cross_pairs': [],
            'active_whispers': 0
        }
        
        # Pair statuses
        for pair, state in self.pair_states.items():
            status['pairs'][pair] = {
                'signal': state['signal'],
                'confidence': state['confidence'],
                'position': state['position'],
                'z_score': state['z_score'],
                'cross_pair_bias': state['cross_pair_bias'],
                'entry_price': state['entry_price']
            }
        
        # Cross pair correlations
        for key, history in self.correlation_history.items():
            if len(history) > 0:
                status['cross_pairs'].append({
                    'pair': key,
                    'current_correlation': round(list(history)[-1], 3),
                    'length': len(history)
                })
        
        # Count active whispers
        for state in self.pair_states.values():
            if state['signal'] != 'HOLD':
                status['active_whispers'] += 1
        
        return status
    
    def get_pair_status(self, pair: str) -> Dict:
        """Get status for a specific pair"""
        if pair not in self.pair_states:
            return {'error': f'Pair {pair} not tracked'}
        
        state = self.pair_states[pair]
        return {
            'pair': pair,
            'signal': state['signal'],
            'confidence': state['confidence'],
            'position': state['position'],
            'z_score': state['z_score'],
            'cross_pair_bias': state['cross_pair_bias'],
            'entry_price': state['entry_price'],
            'price_history_length': len(state['price_history'])
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        for pair in self.pair_states:
            self.pair_states[pair]['position'] = 0
            self.pair_states[pair]['entry_price'] = 0.0
        
        print(f"🔄 {self.name} daily stats reset")
    
    # ============================================
    # MONTE CARLO FORECAST (Compatibility)
    # ============================================
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Monte Carlo forecast for price direction probability
        """
        outcomes = {'above': 0, 'inside': 0, 'below': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above'] += 1
            elif price < cloud_bottom:
                outcomes['below'] += 1
            else:
                outcomes['inside'] += 1
        
        probabilities = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probabilities['above'] > 60:
            vote = 'BUY'
            conf = probabilities['above']
        elif probabilities['below'] > 60:
            vote = 'SELL'
            conf = probabilities['below']
        else:
            vote = 'HOLD'
            conf = probabilities['inside']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probabilities}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get price with automatic fallback to cache"""
        try:
            result = get_any_price(symbol)
            if result and result.get('mid'):
                return result['mid']
        except:
            pass
        return None


# ============================================
# BACKWARD COMPATIBILITY
# ============================================

class AgentP(WhisperAnalyst):
    """
    Backward compatibility alias
    """
    def __init__(self):
        super().__init__()
        print("   ✅ Agent_P (Cross Pair) initialized (backward compatibility)")


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("TESTING AGENT_P - CROSS PAIR AGENT")
    print("="*60 + "\n")
    
    # Create agent
    agent = WhisperAnalyst()
    
    # Test data
    test_data = {
        'pair': 'EURUSD',
        'price': 1.1000,
        'current_price': 1.1000,
        'EURUSD': 1.1000,
        'GBPUSD': 1.3000,
        'USDJPY': 150.00,
        'EURJPY': 165.00,
        'AUDUSD': 0.7000,
        'USDCAD': 1.3500,
        'EURGBP': 0.8500,
    }
    
    print("\n📊 Testing analysis...")
    result = agent.analyze(test_data)
    
    print(f"\n📈 Analysis Result:")
    print(f"   Agent: {result.get('agent', 'Unknown')}")
    print(f"   Vote: {result.get('vote', 'HOLD')}")
    print(f"   Confidence: {result.get('confidence', 0)}%")
    print(f"   Leak Score: {result.get('leak_score', 0)}")
    print(f"   Cross Pair Bias: {result.get('cross_pair_bias', 0)}")
    print(f"   Buy Signals: {result.get('buy_signals', 0)}")
    print(f"   Sell Signals: {result.get('sell_signals', 0)}")
    print(f"\n   Reasoning: {result.get('reasoning', '')[:200]}...")
    
    print("\n✅ Test complete!")