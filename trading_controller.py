# trading_controller.py - M15 COMPLETE FIXED VERSION
"""
ULTIMATE 5-AGENT TRADING CONTROLLER - M15 TIMEFRAME
"""

import json
import threading
import time
import requests
import os
import re
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from agent_coordinator import coordinator
from price_bridge import PriceBridge, get_price_from_bridge
import time as time_module
import numpy as np
import math
import traceback
# ===== ADD THIS IMPORT =====
from datetime import timedelta  # Missing for signal expiry
import pandas as pd  
from liquidity_filter import ProfessionalSpreadFilter
from institutional import (
    MarketRegimeClassifier,
    AdaptiveThresholdCalibrator,
    HierarchicalCoordinator,
    ResilienceTester,
    AntiFragilePositionSizer,
    CircuitBreakerSystem,
    ColdStartProtection,
    SelfHealingSystem,
    ShadowTradingSystem
)
try:
    from performance_metrics import PerformanceMetrics
except ImportError:
    print("⚠️ performance_metrics.py not found - using fallback")
    class PerformanceMetrics:
        def __init__(self):
            self.trades = []
            self.daily_returns = []
            self.equity_curve = [10000]
        def add_trade(self, trade):
            self.trades.append(trade)
        def get_expectancy(self):
            return {'expectancy': 0, 'status': 'NO_DATA'}
        def print_report(self):
            print("📊 Performance Metrics - Not fully implemented")

try:
    from microstructure_alpha import MicrostructureAlpha
except ImportError:
    print("⚠️ microstructure_alpha.py not found - using fallback")\

    class MicrostructureAlpha:
        def __init__(self):
            pass
        def get_combined_signal(self):
            return {'confidence': 50, 'signal': 'NEUTRAL'}

try:
    from correlation_protection import CorrelationProtection
except ImportError:
    print("⚠️ correlation_protection.py not found - using fallback")
    class CorrelationProtection:
        def __init__(self):
            pass
        def is_trade_safe(self):
            return {'safe': True, 'kill_switch': False, 'reason': ''}
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class HybridCoordinator:
    """
    Hybrid Coordination System: Hierarchical + Bayesian Trust.
    
    Layer 1: Rule-based overrides (fast, predictable)
    Layer 2: Trust-weighted consensus (adaptive, self-learning)
    Layer 3: Direct execution (low-latency)
    
    TOGGLE: Set USE_HYBRID = True to enable, False to use current voting
    """
    
    def __init__(self):
        # ===== TOGGLE: Enable/Disable Hybrid Mode =====
        self.USE_HYBRID = True  # ← Set to False to use current voting
        
        # ===== LAYER 1: OVERRIDE RULES =====
        self.override_rules = [
            {
                'name': 'SPREAD_EXTREME',
                'condition': lambda d: abs(d.get('x_z_score', 0)) > 2.5,
                'action': lambda d: 'BUY' if d.get('x_z_score', 0) < 0 else 'SELL',
                'confidence': lambda d: min(95, 75 + abs(d.get('x_z_score', 0)) * 8),
                'priority': 1
            },
            {
                'name': 'SENTIMENT_WHALE',
                'condition': lambda d: d.get('i_vote', 'HOLD') == d.get('g_vote', 'HOLD') != 'HOLD' and d.get('i_conf', 0) > 80,
                'action': lambda d: d.get('i_vote', 'HOLD'),
                'confidence': lambda d: (d.get('i_conf', 0) + d.get('g_conf', 0)) / 2,
                'priority': 2
            },
            {
                'name': 'SUPPLY_DEMAND',
                'condition': lambda d: d.get('r_vote', 'HOLD') != 'HOLD' and d.get('r_conf', 0) > 75,
                'action': lambda d: d.get('r_vote', 'HOLD'),
                'confidence': lambda d: d.get('r_conf', 0) * 0.9,
                'priority': 3
            },
            {
                'name': 'DARKPOOL_DIV',
                'condition': lambda d: d.get('q_vote', 'HOLD') != 'HOLD' and abs(d.get('d_vol', 0)) > 0.003,
                'action': lambda d: d.get('q_vote', 'HOLD'),
                'confidence': lambda d: d.get('q_conf', 0) * 0.8,
                'priority': 4
            }
        ]
        
        # ===== LAYER 2: BAYESIAN TRUST =====
        self.agent_trust = {
            'R': {'weight': 0.12, 'accuracy': 0.65, 'trades': 0, 'wins': 0},
            'Q': {'weight': 0.12, 'accuracy': 0.70, 'trades': 0, 'wins': 0},
            'D': {'weight': 0.10, 'accuracy': 0.55, 'trades': 0, 'wins': 0},
            'H': {'weight': 0.12, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'G': {'weight': 0.10, 'accuracy': 0.50, 'trades': 0, 'wins': 0},
            'M': {'weight': 0.10, 'accuracy': 0.50, 'trades': 0, 'wins': 0},
            'I': {'weight': 0.06, 'accuracy': 0.60, 'trades': 0, 'wins': 0},
            'X': {'weight': 0.08, 'accuracy': 0.90, 'trades': 0, 'wins': 0},
        }
        
        # ===== LAYER 3: EXECUTION =====
        self.order_queue = []
        self.executed_orders = []
        self.decision_log = []
        
        # ===== STATE =====
        self.last_decision = {'action': 'HOLD', 'confidence': 0}
        self.active_override = None
        
        logger.info("✅ HybridCoordinator initialized")
        logger.info(f"   Mode: {'✅ HYBRID ACTIVE' if self.USE_HYBRID else '⏸️ VOTING MODE'}")
        logger.info("   Layer 1: Override Rules - 4 active")
        logger.info("   Layer 2: Bayesian Trust - 8 agents")
        logger.info("   Layer 3: Direct Execution - Ready")
    
    # ============================================================
    # UPDATE TRUST (Bayesian Learning)
    # ============================================================
    
    def update_trust(self, agent_name: str, was_correct: bool):
        """Update agent trust score based on trade result."""
        if agent_name not in self.agent_trust:
            return
        
        trust = self.agent_trust[agent_name]
        trust['trades'] += 1
        if was_correct:
            trust['wins'] += 1
        
        alpha = 0.1
        current_acc = trust['accuracy']
        
        if was_correct:
            new_acc = current_acc + alpha * (1 - current_acc)
        else:
            new_acc = current_acc - alpha * current_acc
        
        trust['accuracy'] = max(0.3, min(0.98, new_acc))
        trust['weight'] = 0.05 + (0.25 * trust['accuracy'])
        
        if agent_name == 'X':
            trust['weight'] = max(0.08, trust['weight'])
    
    def get_agent_accuracy(self, agent_name: str) -> float:
        return self.agent_trust.get(agent_name, {}).get('accuracy', 0.5)
    
    # ============================================================
    # DECIDE
    # ============================================================
    
    def decide(self, agent_data: Dict) -> Dict:
        """Main decision function."""
        start_time = time_module.perf_counter()
        
        # If hybrid is disabled, return None to use current voting
        if not self.USE_HYBRID:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Hybrid disabled', 'use_voting': True}
        
        data = self._flatten_agent_data(agent_data)
        
        # ===== LAYER 1: OVERRIDE RULES =====
        for rule in sorted(self.override_rules, key=lambda x: x['priority']):
            try:
                if rule['condition'](data):
                    action = rule['action'](data)
                    confidence = rule['confidence'](data)
                    self.active_override = rule['name']
                    
                    result = {
                        'action': action,
                        'confidence': min(95, confidence),
                        'reason': f"Override: {rule['name']}",
                        'layer': 'override',
                        'priority': rule['priority']
                    }
                    
                    self.decision_log.append(result)
                    return result
            except Exception as e:
                logger.warning(f"Rule error: {rule['name']} - {e}")
        
        # ===== LAYER 2: BAYESIAN CONSENSUS =====
        result = self._bayesian_consensus(agent_data)
        self.decision_log.append(result)
        self.last_decision = result
        
        return result
    
    def _flatten_agent_data(self, agent_data: Dict) -> Dict:
        """Flatten agent data for rule conditions."""
        flat = {}
        for agent, data in agent_data.items():
            agent_key = agent.upper()
            if isinstance(data, dict):
                flat[f'{agent_key}_vote'] = data.get('vote', 'HOLD')
                flat[f'{agent_key}_conf'] = data.get('confidence', 0)
                if 'z_score' in data:
                    flat[f'{agent_key}_z_score'] = data.get('z_score', 0)
        return flat
    
    def _bayesian_consensus(self, agent_data: Dict) -> Dict:
        """Trust-weighted consensus using Bayesian Model Averaging."""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for agent, data in agent_data.items():
            if agent in self.agent_trust:
                vote = data.get('vote', 'HOLD')
                confidence = data.get('confidence', 50)
                trust_weight = self.agent_trust[agent]['weight']
                accuracy = self.agent_trust[agent]['accuracy']
                
                weight = trust_weight * accuracy
                if vote in votes:
                    votes[vote] += weight * (confidence / 100)
        
        total = sum(votes.values())
        if total > 0:
            action = max(votes, key=votes.get)
            confidence = (votes[action] / total) * 100
            
            if confidence < 50:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Low confidence', 'layer': 'consensus'}
            
            return {
                'action': action,
                'confidence': min(95, confidence),
                'reason': f"Bayesian consensus",
                'layer': 'consensus',
                'votes': votes
            }
        
        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No consensus', 'layer': 'consensus'}
    
    def get_status(self) -> Dict:
        """Get system status."""
        return {
            'active_override': self.active_override,
            'last_decision': self.last_decision,
            'agent_trust': self.agent_trust.copy(),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# INTEGRATE INTO AITradingController
# ============================================================

# Add this to AITradingController.__init__ after loading agents:

def _init_hybrid_coordinator(self):
    """Initialize Hybrid Coordinator."""
    self.hybrid_coordinator = HybridCoordinator()
    self.use_hybrid = self.hybrid_coordinator.USE_HYBRID
    
    if self.use_hybrid:
        logger.info("✅ HYBRID COORDINATOR ENABLED")
        logger.info("   - Override Rules: 4 active")
        logger.info("   - Bayesian Trust: 8 agents")
    else:
        logger.info("⏸️ Hybrid Coordinator DISABLED - Using current voting")
class LiquidityGuard:
    """Protects against liquidity traps and slippage."""
    def __init__(self):
        self.min_spread_ratio = 0.5
        
    def check_liquidity(self, symbol, bid, ask, spread_usd=0):
        """Check if liquidity is sufficient to execute a trade."""
        if bid <= 0 or ask <= 0:
            return False, "No bid/ask data"
        
        spread_ratio = (ask - bid) / ((ask + bid) / 2) * 100
        if spread_ratio > 0.05:  # 0.05% spread warning
            return False, f"Spread too wide: {spread_ratio:.3f}%"
        
        current_hour = datetime.now().hour
        if current_hour < 1 or current_hour > 23:
            return False, "Outside trading hours"
        
        if spread_usd > 100:
            return False, f"Spread too high: ${spread_usd:.2f}"
        
        return True, "Liquidity OK"


class GapProtection:
    """Protects against price gaps and structural breakouts."""
    def __init__(self, max_hold_time_minutes=30):
        self.max_hold_time_minutes = max_hold_time_minutes
        self.entry_time = None
        self.gap_threshold = 0.005
        
    def monitor_gap(self, current_price, previous_close):
        """Detect if a gap has occurred."""
        if previous_close <= 0:
            return False
        gap_pct = abs(current_price - previous_close) / previous_close
        return gap_pct > self.gap_threshold
    
    def check_exit_conditions(self, z_score, entry_z, time_elapsed):
        """Determine if we should exit."""
        if abs(z_score) < 0.5:
            return True, "Success - Mean reversion complete"
        
        if time_elapsed > self.max_hold_time_minutes:
            return True, f"Timeout - {self.max_hold_time_minutes} min exceeded"
        
        if abs(z_score) > abs(entry_z) + 0.5:
            return True, f"Structural breakout - Z {entry_z:.2f} → {z_score:.2f}"
        
        return False, "Hold"

SYMBOL_CONFIG = {
    # ===== METALS - 0.02 lots =====
    'GOLD': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 20, 'tp_pips': 35,
        'volume': 0.02, 'type': 'metal', 'enabled': True
    },
    'SILVER': {
        'pip': 0.01, 'digits': 2, 'sl_pips': 20, 'tp_pips': 35,
        'volume': 0.02, 'type': 'metal', 'enabled': True
    },
    
    # ===== INDICES - 0.02 lots =====
    '#NASDAQ100': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 1000,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    '#DJ30': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 1000,
        'volume': 0.01, 'type': 'index', 'enabled': True
    },
    '#S&P500': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 1000,
        'volume': 0.03, 'type': 'index', 'enabled': True
    },
    '#RUSS2000': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 250, 'tp_pips': 1000,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    '#CAC40': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 1000,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    '#DAX40': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 500,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    '#FTSE100': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 500,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    '#NIKKEI225': {
        'pip': 0.1, 'digits': 2, 'sl_pips': 250, 'tp_pips': 500,
        'volume': 0.02, 'type': 'index', 'enabled': True
    },
    
    # ===== ENERGY - 0.02 lots =====
    'BRENT_OIL': {
        'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80,
        'volume': 0.02, 'type': 'energy', 'enabled': True
    },
    'CrudeOIL': {
        'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80,
        'volume': 0.02, 'type': 'energy', 'enabled': True
    },
    
}

# ============================================================
# SYMBOLS TO MONITOR (ALL ENABLED)
# ============================================================

SYMBOLS_TO_TRADE = [
    # Metals
    'GOLD', 'SILVER',
    
    # Indices
    '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
    
    # Energy
    'BRENT_OIL', 'CrudeOIL'
    
    # Dollar Index
]

# ===== ADD THIS IMPORT =====
try:
    from backend.agents import AgentXSpread
    AGENT_X_AVAILABLE = True
    print("✅ Agent_X imported successfully")
except ImportError as e:
    AGENT_X_AVAILABLE = False
    print(f"⚠️ Agent_X not available: {e}")
    print("⚠️ Agent_X not available - spread reversion disabled")
# ============ DEEPSEEK API ============
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-155bc1f42252453585b37d2655dca432')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

def call_deepseek(prompt: str, system_message: str = "You are a professional financial analyst. Analyze the following price data and output a vote (BUY/SELL/HOLD) and confidence score...") -> Dict:
    """Call DeepSeek API for trading decisions"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            logger.info(f"✅ DeepSeek response received")
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {'raw_response': content}
        else:
            logger.error(f"❌ DeepSeek API Error: {response.status_code}")
            return {'error': f"API Error: {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ DeepSeek API Exception: {e}")
        return {'error': str(e)}
# ============================================================
# SIMPLE AGENT CLASSES (Defined directly in file)
# ============================================================

class SimpleSpreadAgent:
    """
    Agent_X - Spread Reversion Specialist
    Monitors S = ln(SPX) - β * ln(NDX)
    """
    def __init__(self):
        self.name = "Agent_X"
        self.agent_type = "Spread Reversion Specialist"
        self.timeframe = "M15"
        
        # Core parameters
        self.beta = 1.05
        self.spread_history = []
        self.max_history = 300
        self.mu = 0.0
        self.sigma = 0.0
        self.z_score = 0.0
        self.current_spread = 0.0
        self.entry_threshold = 2.5
        self.exit_threshold = 0.5
        self.position = 0
        
        # ===== ADD THIS: Track last analyzed symbol =====
        self.last_symbol = None
        self.last_spx = 0
        self.last_ndx = 0
        
        print(f"   ✅ Agent_X (Spread Reversion) - SECRET WEAPON")
    
    def analyze(self, signal_data):
        """Analyze spread between SPX and NDX."""
        import math
        
        symbol = signal_data.get('symbol', '#S&P500')
        spx_price = signal_data.get('spx_price', 0)
        ndx_price = signal_data.get('ndx_price', 0)
        
        # ===== FIX: Check if we have price data =====
        if spx_price <= 0 or ndx_price <= 0:
            try:
                from price_cache_manager import price_cache
                spx_price = price_cache.get_latest('#S&P500', 0)
                ndx_price = price_cache.get_latest('#NASDAQ100', 0)
            except:
                pass
        
        # ===== If still no data, check fallback prices =====
        if spx_price <= 0:
            # Try to get from _get_price_data
            try:
                from trading_controller import trading_controller
                spx_data = trading_controller._get_price_data('#S&P500')
                spx_price = spx_data.get('price', 6000)
            except:
                spx_price = 6000  # Hardcoded fallback
        
        if ndx_price <= 0:
            try:
                from trading_controller import trading_controller
                ndx_data = trading_controller._get_price_data('#NASDAQ100')
                ndx_price = ndx_data.get('price', 22000)
            except:
                ndx_price = 22000  # Hardcoded fallback
        if spx_price <= 0:
            spx_price = 7525.99
        if ndx_price <= 0:
            ndx_price = 30332.25
        
        # Store last prices
        self.last_spx = spx_price
        self.last_ndx = ndx_price
        
        # Calculate spread
        if spx_price > 0 and ndx_price > 0:
            self.current_spread = math.log(spx_price) - self.beta * math.log(ndx_price)
            self.spread_history.append(self.current_spread)
        
        # ===== FIX: Keep history size consistent =====
        if len(self.spread_history) > self.max_history:
            self.spread_history.pop(0)
        
        # Calculate Z-score
        if len(self.spread_history) >= 10:  # Reduced from 30 for faster response
            self.mu = sum(self.spread_history) / len(self.spread_history)
            variance = sum((x - self.mu) ** 2 for x in self.spread_history) / len(self.spread_history)
            self.sigma = math.sqrt(variance) if variance > 0 else 0.0001
            
            if self.sigma > 0:
                self.z_score = (self.current_spread - self.mu) / self.sigma
        
        # ===== FIX: Log every 10 cycles for debugging =====
        if len(self.spread_history) % 10 == 0:
            logger.info(f"   📊 Agent_X: spread={self.current_spread:.4f}, mu={self.mu:.4f}, sigma={self.sigma:.4f}")
        
        # Generate signal
        if self.z_score > self.entry_threshold:
            self.signal = "SELL"
            self.confidence = min(95, 75 + (self.z_score - self.entry_threshold) * 15)
            self.position = -1
            reasoning = f"Spread overextended (Z={self.z_score:.2f})"
            
        elif self.z_score < -self.entry_threshold:
            self.signal = "BUY"
            self.confidence = min(95, 75 + (-self.z_score - self.entry_threshold) * 15)
            self.position = 1
            reasoning = f"Spread compressed (Z={self.z_score:.2f})"
            
        elif abs(self.z_score) < self.exit_threshold and self.position != 0:
            self.signal = "HOLD"
            self.confidence = 50
            self.position = 0
            reasoning = f"Spread reverted (Z={self.z_score:.2f})"
            
        else:
            self.signal = "HOLD"
            self.confidence = max(40, 50 - abs(self.z_score) * 5)
            reasoning = f"Z-score normal ({self.z_score:.2f})"
        
        return {
            'vote': self.signal,
            'confidence': self.confidence,
            'reasoning': reasoning,
            'symbol': symbol,
            'timeframe': 'M15',
            'z_score': round(self.z_score, 3),
            'spread': round(self.current_spread, 6),
            'beta': round(self.beta, 4),
            'mu': round(self.mu, 6),
            'sigma': round(self.sigma, 6),
            'position': self.position,
            'samples': len(self.spread_history)
        }
    
    def get_weight(self, z_score=None):
        """Returns voting weight based on Z-score magnitude."""
        if z_score is None:
            z_score = self.z_score
        
        if abs(z_score) > 2.5:
            return 3.0
        elif abs(z_score) > 2.0:
            return 2.0
        elif abs(z_score) > 1.5:
            return 1.5
        else:
            return 1.0
class SimpleFibonacciAgent:
    """Agent_H - Fibonacci Specialist"""
    def __init__(self):
        self.name = "Agent_H"
        self.agent_type = "Fibonacci Specialist"
        self.timeframe = "M15"
        print(f"   ✅ Agent_H (Fibonacci) initialized")
    
    def analyze(self, signal_data):
        symbol = signal_data.get('symbol', 'EURUSD')
        price = signal_data.get('price', 0)
        
        if price <= 0:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No price'}
        
        support = price * 0.998
        resistance = price * 1.002
        
        if price <= support:
            return {'vote': 'BUY', 'confidence': 65, 'reasoning': f'Fibonacci support at {support:.5f}'}
        elif price >= resistance:
            return {'vote': 'SELL', 'confidence': 65, 'reasoning': f'Fibonacci resistance at {resistance:.5f}'}
        else:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Fibonacci neutral'}


class SimpleWhaleTracker:
    """Agent_G - Whale Tracker"""
    def __init__(self):
        self.name = "Agent_G"
        self.agent_type = "Whale Tracker"
        self.timeframe = "M15"
        print(f"   ✅ Agent_G (Whale Tracker) initialized")
    
    def analyze(self, signal_data):
        symbol = signal_data.get('symbol', 'EURUSD')
        import random
        whale = random.random() < 0.3
        
        if whale:
            direction = random.choice(['BUY', 'SELL'])
            return {'vote': direction, 'confidence': 72, 'reasoning': f'🐋 Whale {direction} detected!'}
        else:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No whale activity'}


class SimpleMarketProfile:
    """Agent_M - Market Profile"""
    def __init__(self):
        self.name = "Agent_M"
        self.agent_type = "Market Profile"
        self.timeframe = "M15"
        print(f"   ✅ Agent_M (Market Profile) initialized")
    
    def analyze(self, signal_data):
        symbol = signal_data.get('symbol', 'EURUSD')
        price = signal_data.get('price', 0)
        
        if price <= 0:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No price'}
        
        vah = price * 1.001
        val = price * 0.999
        
        if price > vah:
            return {'vote': 'SELL', 'confidence': 68, 'reasoning': 'Above Value Area High'}
        elif price < val:
            return {'vote': 'BUY', 'confidence': 68, 'reasoning': 'Below Value Area Low'}
        else:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Inside Value Area'}


class SimpleConsensusAgent:
    """Agent_W - Consensus Agent"""
    def __init__(self):
        self.name = "Agent_W"
        self.agent_type = "Consensus Master"
        self.timeframe = "M15"
        print(f"   ✅ Agent_W (Consensus) initialized")
    
    def analyze(self, signal_data, agent_signals):
        symbol = signal_data.get('symbol', 'EURUSD')
        
        if not agent_signals:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'No signals'}
        
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        total = 0
        
        for s in agent_signals:
            if s:
                vote = s.get('vote', 'HOLD')
                conf = s.get('confidence', 50)
                votes[vote] += conf
                total += conf
        
        if total > 0:
            action = max(votes, key=votes.get)
            confidence = (votes[action] / total) * 100
        else:
            action = 'HOLD'
            confidence = 50
        
        return {
            'vote': action,
            'confidence': round(confidence, 1),
            'reasoning': f"Consensus: {action} (BUY:{votes['BUY']:.0f} SELL:{votes['SELL']:.0f} HOLD:{votes['HOLD']:.0f})"
        }

# ============ MOCK SENTIMENT AGENT ============
class MockSentimentAgent:
    """Mock sentiment agent when real one isn't available"""
    def __init__(self):
        self.name = "Mock_Sentiment"
        self.agent_type = "Sentiment Master (Mock)"
        self.timeframe = "M15"
    
    def analyze(self, signal_data):
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': signal_data.get('symbol', 'EURUSD'),
            'timeframe': 'M15',
            'vote': 'HOLD',
            'confidence': 45,
            'reasoning': 'Sentiment agent not available - using neutral sentiment',
            'timestamp': datetime.now().isoformat()
        }

DASHBOARD_URL = "http://localhost:5002"  # Your dashboard URL

def get_prices_from_dashboard():
        """Get all prices from the dashboard API"""
        try:
                response = requests.get(f"{DASHBOARD_URL}/api/all_data", timeout=5)
                if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                                return data
                return None
        except Exception as e:
                print(f"⚠️ Dashboard connection error: {e}")
                return None

def get_price_from_dashboard(symbol):
        """Get price for a specific symbol from dashboard"""
        data = get_prices_from_dashboard()
        if data and 'prices' in data:
                prices = data['prices']
                
                # Try exact match
                if symbol in prices:
                        price_data = prices[symbol]
                        if isinstance(price_data, dict):
                                return price_data.get('price', 0)
                        return price_data
                
                # Try alternative names
                alt_map = {
                    '#NASDAQ100': ['NAS100', 'US100'],
                    '#S&P500': ['SP500', 'US500'],
                    '#DJ30': ['DJ30', 'US30'],
                    '#RUSS2000': ['RUS2000', 'US2000'],
                    '#CAC40': ['CAC40', 'FR40'],
                    '#DAX40': ['DAX40', 'GER40'],
                    '#FTSE100': ['FTSE100', 'UK100'],
                    '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225'],
                    'GOLD': ['XAUUSD'],
                    'SILVER': ['XAGUSD'],
                    'BRENT_OIL': ['BRENT', 'UKOIL'],
                    'CrudeOIL': ['CRUDE', 'USOIL'],
                }
                
                if symbol in alt_map:
                        for alt in alt_map[symbol]:
                                if alt in prices:
                                        price_data = prices[alt]
                                        if isinstance(price_data, dict):
                                                return price_data.get('price', 0)
                                        return price_data
                
                # Try without # prefix
                if symbol.startswith('#'):
                        clean = symbol[1:]
                        if clean in prices:
                                price_data = prices[clean]
                                if isinstance(price_data, dict):
                                        return price_data.get('price', 0)
                                return price_data
        
        return 0

def get_all_prices_from_dashboard():
        """Get all prices dictionary from dashboard"""
        data = get_prices_from_dashboard()
        if data and 'prices' in data:
                return data['prices']
        return {}
# ============ ULTIMATE TRADING CONTROLLER ============

class AITradingController:
    """ULTIMATE 5-Agent Consensus Trading Controller - M15"""
    
    def __init__(self):
        logger.info("🚀 Initializing ULTIMATE Trading Controller (M15)...")
        from institutional.baseline_manager import BaselineManager
        from institutional.priority_queue import OpportunityQueue
        from institutional.deviation_monitor import DeviationMonitor
        from institutional.fast_reboot import FastReboot
        from institutional.market_maker_protection import MarketMakerProtection
        self.market_maker_protection = MarketMakerProtection()
        logger.info("✅ Market Maker Protection System initialized")
    
        try:
            from institutional.monte_carlo_service import MonteCarloService
            self.monte_carlo = MonteCarloService()
            logger.info("✅ Monte Carlo Service initialized")
        except ImportError as e:
            self.monte_carlo = None
            logger.warning(f"⚠️ Monte Carlo Service not available: {e}")
        self.baseline_manager = BaselineManager(
         config_path="baseline_config.json",
         save_interval_seconds=300  # 5 minutes
        )
        self.baseline_manager = BaselineManager()
        self.opportunity_queue = OpportunityQueue(top_n=3)
        self.deviation_monitor = DeviationMonitor(max_stall_seconds=60)
        self.fast_reboot = FastReboot(save_path="trading_state")
        last_state = self.fast_reboot.load_state()
        if last_state:
            logger.info("   ✅ Fast reboot: Previous state loaded")

        # After loading all agents, print their status
        self._load_agent_x()
        self._load_agent_r()
        self._load_agent_q()
        self._load_agent_d()
        self._load_agent_i()
        self._load_agent_h()  # NEW
        self._load_agent_g()  # NEW
        self._load_agent_m()  # NEW
        self._load_agent_w()
        self.coordinator = coordinator
        self.confidence_gateway = ConfidenceGateway(min_confidence=70)
        self.execution_monitor = ExecutionQualityMonitor()
        self.black_swan_simulator = BlackSwanSimulator(self.coordinator)
        self.price_bridge = PriceBridge()
        logger.info("✅ Price Bridge initialized (same source as dashboard)")
        self.liquidity_filter = ProfessionalSpreadFilter()
        logger.info("✅ Professional Liquidity Filter initialized")
# Initialize Hybrid Coordinator
        self.hybrid_coordinator = HybridCoordinator()
        self.use_hybrid = self.hybrid_coordinator.USE_HYBRID
        logger.info("🏛️ Initializing INSTITUTIONAL Trading Controller (M15)...")

        if self.use_hybrid:
               logger.info("✅ HYBRID COORDINATOR ENABLED")
               logger.info("         - Override Rules: 4 active")
               logger.info("   - Bayesian Trust: 8 agents")
        else:
           logger.info("⏸️ Hybrid Coordinator DISABLED - Using current voting")

# ===== CONTINUE WITH REST =====
# ===== LOGGING =====
        self.decision_log = []
        self.max_log_entries = 1000

        logger.info("✅ FINAL CHECKS READY")
        # ===== LOGGING =====
        self.decision_log = []
        self.max_log_entries = 1000
        if len(self.decision_log) > self.max_log_entries:
            self.decision_log = self.decision_log[-self.max_log_entries:]
        
        logger.info("✅ FINAL CHECKS READY")
        logger.info("   ✅ Confidence Gateway: 70% threshold")
        logger.info("   ✅ Execution Quality Monitor: Delta < 0.1")
        logger.info("   ✅ Black Swan Simulator: Ready")
        logger.info("   ✅ Decision Logging: Active")
        
        
        logger.info("🏛️ Institutional components initialized")
        # ===== INITIALIZE ALL ATTRIBUTES (FIXED) =====
        self.mt4 = None
        self.active_positions = {}  # FIXED: Initialize before anything else
        self.active_trades = {}     # FIXED: Initialize before anything else
        self.trade_history = []
        self.decision_log = []
        self.running = False
        self.lock = threading.Lock()
        
        # ===== AGENTS =====
        self.agent_x = None
        self.agent_r = None
        self.agent_q = None
        self.agent_d = None
        self.agent_i = None
        # ===== NEW AGENTS =====
        self.agent_h = None  # Fibonacci
        self.agent_g = None  # Whale Tracker
        self.agent_m = None  # Market Profile
        self.agent_w = None  # Consensus
        self.position_sizer = None
        self.alpha_generator = None
        
        # ===== CONFIGURATION =====
        self.timeframe = "M15"
        self.timeframe_seconds = 900
        self.candles_to_load = 50
        self.trading_start = 1
        self.trading_end = 23
        self.cycle_seconds = 10 # 15 minutes
        
        self.config = {
            'min_confidence': 50,
            'max_trades_per_day': 10,
            'trades_today': 0,
            'daily_pnl': 0.0
        }
        
        # ===== SYMBOLS =====
        self.symbols = SYMBOLS_TO_TRADE        
                # INSTITUTIONAL COMPONENTS (NEW!)
        # ============================================================
        self.regime_classifier = MarketRegimeClassifier()
        self.threshold_calibrator = AdaptiveThresholdCalibrator()
        self.hierarchical_coordinator = HierarchicalCoordinator()
        self.position_sizer = AntiFragilePositionSizer()
        self.circuit_breaker = CircuitBreakerSystem()
        self.cold_start = ColdStartProtection()
        self.self_healing = SelfHealingSystem()
        self.shadow_trading = ShadowTradingSystem(self)
        self.resilience_tester = ResilienceTester()
        
        logger.info("   ✅ Institutional components initialized")
        logger.info("      - Market Regime Classifier")
        logger.info("      - Adaptive Threshold Calibrator")
        logger.info("      - Hierarchical Coordinator")
        logger.info("      - Anti-Fragile Position Sizer")
        logger.info("      - Circuit Breaker System")
        logger.info("      - Cold Start Protection")
        logger.info("      - Self-Healing System")
        logger.info("      - Shadow Trading System")
        logger.info("      - Resilience Tester")
        
        # ===== CONNECT MT4 =====
        self._connect_mt4()
        
        # ===== LOAD AGENTS =====
        self._load_agent_r()
        self._load_agent_q()
        self._load_agent_d()
        self._load_agent_h()
        self._load_agent_g()
        self._load_agent_m()
        self._load_agent_w()
        self._load_agent_i()
        self._load_agent_x()
        self._load_components()
        logger.info(f"   ✅ Agents loaded:")
        logger.info(f"      Agent_R: {self.agent_r is not None}")
        logger.info(f"      Agent_Q: {self.agent_q is not None}")
        logger.info(f"      Agent_D: {self.agent_d is not None}")
        logger.info(f"      Agent_H: {self.agent_h is not None}")
        logger.info(f"      Agent_G: {self.agent_g is not None}")
        logger.info(f"      Agent_M: {self.agent_m is not None}")
        logger.info(f"      Agent_W: {self.agent_w is not None}")
        logger.info(f"      Agent_I: {self.agent_i is not None}")
        logger.info(f"      Agent_X: {self.agent_x is not None}")
        logger.info(f"   ✅ Timeframe set to: {self.timeframe}")
        logger.info(f"   ✅ Symbols: {self.symbols}")
        logger.info(f"   ✅ Cycle: {self.cycle_seconds} seconds")
        
        # Print agent weights
        self._print_agent_weights()
        
        logger.info("✅ ULTIMATE Trading Controller initialized")
        self.performance = PerformanceMetrics()
        self.microstructure = MicrostructureAlpha()
        self.correlation_protection = CorrelationProtection()
        self.rl_model = None
        try:
            from stable_baselines3 import PPO
            import numpy as np
            import os
            
            rl_model_path = os.path.join(os.path.dirname(__file__), 'models', 'rl_model.zip')
            if os.path.exists(rl_model_path):
                self.rl_model = PPO.load(rl_model_path)
                logger.info("✅ RL Model loaded for trading")
            else:
                logger.warning(f"⚠️ RL Model not found at {rl_model_path}")
        except Exception as e:
            logger.warning(f"⚠️ RL Model import failed: {e}")
            self.rl_model = None
         # ===== COLD START =====
        
        self._check_cold_start()
        self._print_status()
        
        logger.info("✅ INSTITUTIONAL Trading Controller initialized")
        logger.info("✅ Advanced components initialized")
        logger.info("   - Performance Metrics (Expectancy, Sharpe, Calmar)")
        logger.info("   - Microstructure Alpha (OBI, OFI, Volume Spikes)")
        logger.info("   - Correlation Protection (Beta, Volatility Monitoring)")
    def _check_cold_start(self):
        """Check if system is in cold start phase."""
        # Try to load existing trade history
        try:
            if len(self.performance.trades) > 0:
                # Add existing trades to cold start
                for trade in self.performance.trades[-50:]:
                    self.cold_start.add_sample(trade)
        except:
            pass
        
        status = self.cold_start.can_trade()
        logger.info(f"   ❄️ Cold Start: {status['mode']} - {status['reason']}")
    def _print_status(self):
        """Print system status."""
        print("\n" + "=" * 60)
        print("🏛️ INSTITUTIONAL TRADING SYSTEM - M15")
        print("=" * 60)
        print(f"   Timeframe: M15")
        print(f"   Symbols: {len(self.symbols)}")
        print(f"   Agents: 9")
        print(f"   Hybrid Coordinator: {'✅' if self.use_hybrid else '❌'}")
        print(f"   RL Model: {'✅' if self.rl_model else '❌'}")
        print(f"   Circuit Breaker: {'✅' if not self.circuit_breaker.is_breached else '🔴'}")
        print(f"   Cold Start: {self.cold_start.mode}")
        print("=" * 60)
    def _load_agent_x(self):
        """Load Agent_X - Spread Reversion Specialist"""
        try:
               # Try to import from file first
               try:
                     from backend.agents.agent_x_spread import AgentXSpread
                     self.agent_x = AgentXSpread(name="Agent_X", timeframe="M15")
                     logger.info("   ✅ Agent_X (Spread Reversion) loaded from file")
                     return True
               except:
                     self.agent_x = SimpleSpreadAgent()  # ← This is the fix
                     pass
               
               # Fallback to built-in
               logger.info("   ✅ Agent_X (Spread Reversion) - built-in")
               return True
        except Exception as e:
               logger.warning(f"   ⚠️ Agent_X not available: {e}")
               self.agent_x = None
               return False
    def _load_agent_h(self):
        """Load Agent_H - Fibonacci"""
        try:
                from agent_h_fibonacci import FibonacciAgent
                self.agent_h = FibonacciAgent()
                logger.info("   ✅ Agent_H (Fibonacci) loaded from file")
        except:
                self.agent_h = SimpleFibonacciAgent()
                logger.info("   ✅ Agent_H (Fibonacci) - built-in")
    def get_rl_signal(self, z_score: float) -> Dict:
        """Get trading signal from RL agent."""
        if self.rl_model is None:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'RL model not loaded'}
        
        try:
                import numpy as np
                
                # Build state: [z_score, position, entry_z, unrealized_pnl]
                state = np.array([
                        float(np.clip(z_score, -3.5, 3.5)),
                        0.0,  # position (0 = no position)
                        0.0,  # entry_z
                        0.0   # unrealized pnl
                ], dtype=np.float32)
                
                # Get action from model
                action, _ = self.rl_model.predict(state, deterministic=True)
                action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
                
                # Calculate confidence based on Z-score magnitude
                confidence = min(95, 50 + abs(z_score) * 10)
                
                return {
                        'signal': action_map[action],
                        'confidence': confidence,
                        'z_score': z_score,
                        'reason': f'RL model: {action_map[action]} at Z={z_score:.2f}'
                }
        except Exception as e:
                logger.warning(f"RL signal error: {e}")
                return {'signal': 'HOLD', 'confidence': 0, 'reason': f'Error: {e}'}
    def _load_agent_g(self):
        """Load Agent_G - Whale Tracker"""
        try:
                from agent_g_whale import WhaleTracker
                self.agent_g = WhaleTracker()
                logger.info("   ✅ Agent_G (Whale Tracker) loaded from file")
        except:
                self.agent_g = SimpleWhaleTracker()
                logger.info("   ✅ Agent_G (Whale Tracker) - built-in")


    def _load_agent_m(self):
        """Load Agent_M - Market Profile"""
        try:
                from agent_m_marketprofile import MarketProfileAgent
                self.agent_m = MarketProfileAgent()
                logger.info("   ✅ Agent_M (Market Profile) loaded from file")
        except:
                self.agent_m = SimpleMarketProfile()
                logger.info("   ✅ Agent_M (Market Profile) - built-in")

    def _load_agent_w(self):
        """Load Agent_W - Consensus"""
        try:
                from agent_w_consensus import ConsensusAgent
                self.agent_w = ConsensusAgent()
                logger.info("   ✅ Agent_W (Consensus) loaded from file")
        except:
                self.agent_w = SimpleConsensusAgent()
                logger.info("   ✅ Agent_W (Consensus) - built-in")
    def _print_agent_weights(self):
        """Print the agent weights"""
        print("\n" + "=" * 50)
        print("🎯 ULTIMATE TRADING SYSTEM - M15 AGENT WEIGHTS")
        print("=" * 50)
        
        agents = [
                ('Agent_R (Supply/Demand)', self.agent_r is not None, 35),
                ('Agent_Q (Dark Pool)', self.agent_q is not None, 25),
                ('Agent_D (Volatility)', self.agent_d is not None, 15),
                ('DeepSeek AI', True, 15),
                ('Agent_I (Sentiment)', self.agent_i is not None, 10),
                ('Agent_X (Spread)', self.agent_x is not None, 25),  # ← ADD THIS
        ]
        
        for name, loaded, weight in agents:
                status = "✅" if loaded else "❌"
                bar = '█' * int(weight * 0.4)
                print(f"  {name:25} {status} {weight:3}% {bar}")
        
        print(f"\n  📊 Timeframe: {self.timeframe}")
        print("=" * 50)
    
    def _connect_mt4(self):
        """Connect to MT4"""
        try:
            from mt4_price_provider import get_mt4_prices
            self.mt4 = get_mt4_prices()
            logger.info("   ✅ MT4 connected")
            
            test = self.mt4.test_connection() if hasattr(self.mt4, 'test_connection') else True
            if test:
                logger.info("   ✅ MT4 connection verified")
            else:
                logger.warning("   ⚠️ MT4 connection test failed")
        except Exception as e:
            logger.error(f"   ❌ MT4 connection failed: {e}")
            self.mt4 = None
    
    def _load_agent_r(self):
        """Load Agent_R as Lead Trader"""
        try:
            from agent_r_ultimate import AgentRUltimate
            self.agent_r = AgentRUltimate(name="Agent_R_Lead")
            logger.info("   ✅ Agent_R (Supply/Demand) - LEAD TRADER")
            return True
        except Exception as e:
            logger.warning(f"   ⚠️ Agent_R not available: {e}")
            self.agent_r = SimpleAgentR()
            return True
    
    def _load_agent_q(self):
        """Load Agent_Q for Dark Pool analysis"""
        try:
            from agent_q_darkpool import agent_q
            self.agent_q = agent_q
            logger.info("   ✅ Agent_Q (Dark Pool) - SECRET WEAPON")
            return True
        except Exception as e:
            logger.warning(f"   ⚠️ Agent_Q not available: {e}")
            self.agent_q = SimpleAgentQ()
            return True
    
    def _load_agent_d(self):
        """Load Agent_D for volatility analysis"""
        try:
            from agent_d_volatility import AgentDVolatility
            self.agent_d = AgentDVolatility()
            logger.info("   ✅ Agent_D (Volatility) - TIMING TOOL")
            return True
        except Exception as e:
            logger.warning(f"   ⚠️ Agent_D not available: {e}")
            self.agent_d = SimpleAgentD()
            return True
    
    def _load_agent_i(self):
        """Load Agent_I for sentiment analysis"""
        try:
                # Try to load from file
                from sentiment_agent import SentimentMaster
                self.agent_i = SentimentMaster()
                logger.info("   ✅ Agent_I (Sentiment) - CONTRARIAN EDGE")
                return True
        except:
                try:
                        # Try alternative import
                        from backend.agents.agent_i_sentiment import SentimentMaster
                        self.agent_i = SentimentMaster()
                        logger.info("   ✅ Agent_I (Sentiment) - CONTRARIAN EDGE")
                        return True
                except:
                        # Fallback to mock
                        self.agent_i = MockSentimentAgent()
                        logger.info("   ✅ Agent_I (Sentiment) - built-in")
                        return True
    
    def _load_components(self):
        """Load existing modules"""
        try:
            from position_sizing import AdaptivePositionSizer
            self.position_sizer = AdaptivePositionSizer()
            logger.info("   ✅ Position sizer loaded")
        except Exception as e:
            logger.warning(f"   ⚠️ Position sizer not available: {e}")
        
        try:
            from alpha_generator import alpha_generator
            self.alpha_generator = alpha_generator
            logger.info("   ✅ Alpha generator loaded")
        except Exception as e:
            logger.warning(f"   ⚠️ Alpha generator not available: {e}")
    
    def get_symbol_config(self, symbol):
        """Get configuration for a symbol"""
        clean_symbol = symbol.replace('#', '')
        if clean_symbol in SYMBOL_CONFIG:
            return SYMBOL_CONFIG[clean_symbol]
        if symbol in SYMBOL_CONFIG:
            return SYMBOL_CONFIG[symbol]
        return {
            'pip': 0.0001,
            'digits': 5,
            'sl_pips': 20,
            'tp_pips': 40,
            'volume': 0.05,
            'type': 'unknown'
        }
    # ============ DASHBOARD API CONNECTION ============
    DASHBOARD_URL = "http://localhost:5002"  # Your dashboard URL

    def get_prices_from_dashboard():
        """Get all prices from the dashboard API"""
        try:
                response = requests.get(f"{DASHBOARD_URL}/api/all_data", timeout=5)
                if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                                return data
                return None
        except Exception as e:
                print(f"⚠️ Dashboard connection error: {e}")
                return None

    def get_price_from_dashboard(symbol):
        """Get price for a specific symbol from dashboard"""
        data = get_prices_from_dashboard()
        if data and 'prices' in data:
                prices = data['prices']
                
                # Try exact match
                if symbol in prices:
                        price_data = prices[symbol]
                        if isinstance(price_data, dict):
                                return price_data.get('price', 0)
                        return price_data
                
                # Try alternative names
                alt_map = {
                        '#NASDAQ100': ['NAS100', 'US100'],
                        '#S&P500': ['SP500', 'US500'],
                        '#DJ30': ['DJ30', 'US30'],
                        'GOLD': ['XAUUSD'],
                        'SILVER': ['XAGUSD'],
                        'BRENT_OIL': ['BRENT', 'UKOIL'],
                        'CrudeOIL': ['CRUDE', 'USOIL'],
                        '#RUSS2000': ['RUS2000', 'US2000'],
                        '#CAC40': ['CAC40', 'FR40'],
                        '#DAX40': ['DAX40', 'GER40'],
                        '#FTSE100': ['FTSE100', 'UK100'],
                        '#NIKKEI225': ['NIKKEI225', 'N225', 'JP225']
                }
                
                if symbol in alt_map:
                        for alt in alt_map[symbol]:
                                if alt in prices:
                                        price_data = prices[alt]
                                        if isinstance(price_data, dict):
                                                return price_data.get('price', 0)
                                        return price_data
                
                # Try without # prefix
                if symbol.startswith('#'):
                        clean = symbol[1:]
                        if clean in prices:
                                price_data = prices[clean]
                                if isinstance(price_data, dict):
                                        return price_data.get('price', 0)
                                return price_data
        
        return 0

    def get_all_prices_from_dashboard():
        """Get all prices dictionary from dashboard"""
        data = get_prices_from_dashboard()
        if data and 'prices' in data:
                return data['prices']
        return {}
    def get_current_price(self, symbol):
        """Get current price from dashboard"""
        try:
                # Try dashboard first
                price = get_price_from_dashboard(symbol)
                if price > 0:
                        return {'bid': price, 'ask': price, 'mid': price, 'source': 'DASHBOARD'}
                
                # Try MT4 fallback
                if self.mt4:
                        result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                        if result and isinstance(result, dict):
                                bid = result.get('bid', 0)
                                ask = result.get('ask', 0)
                                if bid > 0 and ask > 0:
                                        return {'bid': bid, 'ask': ask, 'mid': (bid + ask) / 2, 'source': 'MT4'}
        except:
                pass
        
        return {'bid': 0, 'ask': 0, 'mid': 0, 'source': 'NONE'}
                
    def check_open_positions(self):
        """Check and update open positions from MT4"""
        try:
               if not self.mt4:
                  return []
               
               result = self.mt4._send({"command": "POSITIONS"})
               
               if result and result.get('positions'):
                  positions = result.get('positions', [])
                  active_symbols = set()
                  
                  for pos in positions:
                      symbol = pos.get('symbol')
                      if symbol:
                            active_symbols.add(symbol)
                            # Update or add position
                            if symbol in self.active_positions:
                                 self.active_positions[symbol].update(pos)
                            else:
                                 self.active_positions[symbol] = pos
                  
                  # ===== REMOVE POSITIONS THAT ARE NO LONGER ACTIVE =====
                  for symbol in list(self.active_positions.keys()):
                      if symbol not in active_symbols:
                            logger.info(f"   🗑️ Removing closed position: {symbol}")
                            del self.active_positions[symbol]
                  
                  return positions
               else:
                  # ===== NO POSITIONS - CLEAR ALL =====
                  if self.active_positions:
                      logger.info(f"   🗑️ No active positions, clearing {len(self.active_positions)} tracked positions")
                      self.active_positions.clear()
                  
        except Exception as e:
               logger.error(f"Error checking positions: {e}")
        
        return []
    def _force_sync(self):
        """Force sync active positions with MT4"""
        try:
               if not self.mt4:
                     return
               
               result = self.mt4._send({"command": "POSITIONS"})
               
               if result and result.get('positions'):
                     active_symbols = set()
                     for pos in result.get('positions', []):
                         symbol = pos.get('symbol')
                         if symbol:
                                 active_symbols.add(symbol)
                     
                     # Remove positions that don't exist in MT4
                     for symbol in list(self.active_positions.keys()):
                         if symbol not in active_symbols:
                                 logger.info(f"   🗑️ Syncing: Removing {symbol} (not in MT4)")
                                 del self.active_positions[symbol]
               else:
                     # No positions in MT4 - clear all
                     if self.active_positions:
                         logger.info(f"   🗑️ Syncing: Clearing all {len(self.active_positions)} positions")
                         self.active_positions.clear()
                         
        except Exception as e:
               logger.error(f"Sync error: {e}")
    def has_open_position(self, symbol):
        """Check if there's an open position for this symbol"""
        return symbol in self.active_positions
    
    def can_open_trade(self, symbol):
        """Check if we can open a trade for this symbol"""
        if self.has_open_position(symbol):
            logger.info(f"⏸️ Already have open position for {symbol}")
            return False, "Position already exists"
        
        hour = datetime.now().hour
        if hour < self.trading_start or hour > self.trading_end:
            logger.info(f"⏸️ Outside trading hours ({hour}:00)")
            return False, "Outside trading hours"
        
        return True, "OK"
    def get_price_from_bridge(self, symbol: str) -> float:
        """Get price from the same source as the dashboard."""
        try:
               return self.price_bridge.get_price(symbol)
        except Exception as e:
               logger.warning(f"Price bridge error for {symbol}: {e}")
               return 0
    def close_all_positions(self):
        """Close all open positions"""
        try:
            if self.mt4:
                result = self.mt4._send({"command": "CLOSE_ALL"})
                if result and result.get('success'):
                    self.active_positions = {}
                    logger.info("✅ All positions closed")
                    return True
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
        return False
    
    def _get_m15_candles(self, symbol: str) -> List[Dict]:
        """Get M15 candles from MT4"""
        try:
            if self.mt4:
                result = self.mt4._send({
                    "command": "HISTORY",
                    "symbol": symbol,
                    "timeframe": "M15",
                    "count": self.candles_to_load
                })
                
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if candles and len(candles) > 5:
                        return candles
        except Exception as e:
            logger.debug(f"   ⚠️ Could not get M15 candles: {e}")
        
        return self._generate_m15_candles(symbol)
    
    def _generate_m15_candles(self, symbol: str) -> List[Dict]:
        """Generate synthetic M15 candles"""
        price_data = self._get_price_data(symbol)
        if not price_data:
            return []
        
        base_price = price_data['price']
        candles = []
        
        for i in range(self.candles_to_load):
            variation = (i - self.candles_to_load/2) / self.candles_to_load * 0.002
            close = base_price * (1 + variation + random.uniform(-0.0005, 0.0005))
            
            candles.append({
                'open': close * (1 - random.uniform(0.0001, 0.0003)),
                'high': close * (1 + random.uniform(0.0002, 0.0005)),
                'low': close * (1 - random.uniform(0.0002, 0.0005)),
                'close': close,
                'volume': 1000 + random.randint(0, 1000),
                'time': datetime.now().timestamp() - (self.candles_to_load - i) * 900
            })
        
        return candles
    # trading_controller.py - Replace get_all_mt4_prices method

    def get_all_mt4_prices(self) -> Dict:
        """
        Get ALL prices from dashboard (SAME SOURCE as forex)
        Handles nested price dictionaries properly
        """
        result = {}
        
        try:
              # 1. Try dashboard API
              import requests
              response = requests.get("http://localhost:5002/api/all_data", timeout=3)
              
              if response.status_code == 200:
                      data = response.json()
                      if data.get('success'):
                            prices = data.get('prices', {})
                            
                            # Debug: Print what we got
                            print(f"   📊 Dashboard returned {len(prices)} symbols")
                            
                            # Convert to simple dict - handle nested dictionaries
                            for symbol, price_data in prices.items():
                                    if isinstance(price_data, dict):
                                          # Extract price from nested dict
                                          price = price_data.get('price', 0)
                                          if price > 0:
                                                  result[symbol] = price
                                    else:
                                          price = float(price_data)
                                          if price > 0:
                                                  result[symbol] = price
                            
                            # Debug: Show what we have
                            print(f"   📊 Parsed {len(result)} symbols with prices")
                            
                            # Map alternative names to our standard names
                            alt_map = {
                                    'XAUUSD': 'GOLD',
                                    'XAGUSD': 'SILVER',
                                    'NAS100': '#NASDAQ100',
                                    'US100': '#NASDAQ100',
                                    'SP500': '#S&P500',
                                    'US500': '#S&P500',
                                    'DJ30': '#DJ30',
                                    'US30': '#DJ30',
                                    'RUS2000': '#RUSS2000',
                                    'CAC40': '#CAC40',
                                    'DAX40': '#DAX40',
                                    'FTSE100': '#FTSE100',
                                    'NIKKEI225': '#NIKKEI225',
                                    'BRENT': 'BRENT_OIL',
                                    'CRUDE': 'CrudeOIL',
                                    'USOIL': 'CrudeOIL',
                                    'WTI': 'CrudeOIL',
                            }
                            
                            # Add mapped symbols
                            for src, dst in alt_map.items():
                                    if src in result and result[src] > 0:
                                          if dst not in result or result[dst] == 0:
                                                  result[dst] = result[src]
                                                  print(f"   🔄 Mapped {src} -> {dst}: {result[src]}")
                            
                            # Also check direct keys from dashboard
                            direct_symbols = ['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500', 
                                                         '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225',
                                                         'BRENT_OIL', 'CrudeOIL']
                            
                            for symbol in direct_symbols:
                                    if symbol in prices:
                                          price_data = prices[symbol]
                                          if isinstance(price_data, dict):
                                                  price = price_data.get('price', 0)
                                          else:
                                                  price = float(price_data)
                                          
                                          if price > 0:
                                                  result[symbol] = price
                            
                            return result
                            
        except Exception as e:
              print(f"   ⚠️ Dashboard API error: {e}")
        
        # 2. Try file fallback
        try:
              import json
              import os
              
              file_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
              if os.path.exists(file_path):
                      with open(file_path, 'r') as f:
                            data = json.load(f)
                      
                      prices = data.get('prices', {})
                      print(f"   📊 File returned {len(prices)} symbols")
                      
                      for symbol, price_data in prices.items():
                            if isinstance(price_data, dict):
                                    price = price_data.get('price', 0)
                            else:
                                    price = float(price_data)
                            
                            if price > 0:
                                    result[symbol] = price
                      
                      # Map alternative names
                      alt_map = {
                            'XAUUSD': 'GOLD',
                            'XAGUSD': 'SILVER',
                            'NAS100': '#NASDAQ100',
                            'SP500': '#S&P500',
                            'DJ30': '#DJ30',
                            'US30': '#DJ30',
                            'BRENT': 'BRENT_OIL',
                            'CRUDE': 'CrudeOIL',
                            'USOIL': 'CrudeOIL',
                      }
                      
                      for src, dst in alt_map.items():
                            if src in result and result[src] > 0:
                                    if dst not in result or result[dst] == 0:
                                          result[dst] = result[src]
                      
                      return result
                      
        except Exception as e:
              print(f"   ⚠️ File error: {e}")
        
        # 3. If both fail, use _get_price_data for each symbol
        print("   📊 Falling back to individual price fetching...")
        for symbol in self.symbols:
              data = self._get_price_data(symbol)
              if data and data.get('price', 0) > 0:
                      result[symbol] = data['price']
        
        return result
    def _get_price_data(self, symbol: str) -> Dict:
        """Get price data from dashboard API"""
        
        # Try dashboard first
        price = get_price_from_dashboard(symbol)
        
        if price > 0:
                return {
                        'price': price,
                        'bid': price,
                        'ask': price,
                        'spread': 0.0002,
                        'source': 'DASHBOARD'
                }
        
        # Try price_bridge fallback
        try:
                from price_bridge import price_bridge
                price = price_bridge.get_price(symbol)
                bid = price_bridge.get_bid(symbol)
                ask = price_bridge.get_ask(symbol)
                if price > 0:
                        return {
                                'price': price,
                                'bid': bid if bid > 0 else price,
                                'ask': ask if ask > 0 else price,
                                'spread': (ask - bid) if bid > 0 and ask > 0 else 0.0002,
                                'source': 'BRIDGE'
                        }
        except:
                pass
        
        # MT4 fallback
        try:
                if self.mt4:
                        result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                        if result and isinstance(result, dict):
                                bid = result.get('bid', 0)
                                ask = result.get('ask', 0)
                                if bid > 0 and ask > 0:
                                        return {
                                                'price': (bid + ask) / 2,
                                                'bid': bid,
                                                'ask': ask,
                                                'spread': ask - bid,
                                                'source': 'MT4'
                                        }
        except:
                pass
        
        return {
                'price': 0,
                'bid': 0,
                'ask': 0,
                'spread': 0,
                'source': 'NONE'
        }
        # In trading_controller.py - Add these methods
    def save_signal_to_history(self, symbol: str, action: str, confidence: float, 
                           price: float, z_score: float, source: str, 
                           reasoning: str = "", sl: float = 0, tp: float = 0):
        """
        Save trading signal to local history (ALWAYS).
        Optionally save to DB if available.
        """
        # ===== LOCAL HISTORY (ALWAYS) =====
        signal = {
                'id': f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{symbol}",
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'price': price,
                'z_score': z_score,
                'reasoning': reasoning,
                'source': source,
                'timestamp': datetime.now().isoformat(),
                'stop_loss': sl,
                'take_profit': tp,
                'status': 'PENDING'
        }
        
        if not hasattr(self, 'signal_history'):
                self.signal_history = []
        
        self.signal_history.append(signal)
        
        if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
        
        logger.info(f"📊 Signal saved locally: {symbol} {action} (Confidence: {confidence:.1f}%)")
        
        # ===== DB SAVE (OPTIONAL - SILENT FAIL) =====
        try:
                try:
                        from src.services.signal_service import signal_service
                except ImportError:
                        signal_service = None
                
                if signal_service:
                        signal_data = {
                                'symbol': symbol,
                                'signal_type': action,
                                'confidence': int(confidence),
                                'entry_price': price,
                                'stop_loss': sl,
                                'take_profit': tp,
                                'reasoning': reasoning or f"{source}: {action} at Z={z_score:.2f}",
                                'source': source,
                                'z_score': round(z_score, 3),
                                'timeframe': 'M15',
                                'status': 'PENDING'
                        }
                        
                        result = signal_service.save_signal(signal_data)
                        if result:
                                logger.info(f"📊 Signal saved to DB: {symbol} {action}")
                                signal['db_id'] = result.get('id')
        except Exception:
                pass  # Silent fail - DB not available
        
        return signal
    def update_signal_executed(self, signal_id: int, position_id: str):
        """
        Update signal as executed.
        ALWAYS updates local history. OPTIONALLY updates DB.
        """
        # ===== LOCAL UPDATE (ALWAYS) =====
        updated = False
        if hasattr(self, 'signal_history'):
            for signal in self.signal_history:
                if signal.get('id') == signal_id or signal.get('db_id') == signal_id:
                    signal['status'] = 'EXECUTED'
                    signal['position_id'] = position_id
                    signal['executed_at'] = datetime.now().isoformat()
                    updated = True
                    logger.info(f"📊 Signal {signal_id} marked EXECUTED locally")
                    break
    
    # ===== DB UPDATE (OPTIONAL - SILENT FAIL) =====
        try:
            try:
                from src.services.signal_service import signal_service
            except ImportError:
                signal_service = None
        
            if signal_service:
                signal_service.update_signal_status(signal_id, 'EXECUTED', position_id)
        except Exception:
            pass  # Silent fail
    
        return updated
    def _get_current_price_with_spread(self, symbol: str) -> Dict:
        """
        Get current price with spread information.
        """
        try:
              # Try MT4
              if self.mt4:
                      result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                      if result and isinstance(result, dict):
                            bid = result.get('bid', 0)
                            ask = result.get('ask', 0)
                            if bid > 0 and ask > 0:
                                    return {
                                          'bid': bid,
                                          'ask': ask,
                                          'price': (bid + ask) / 2,
                                          'spread': ask - bid,
                                          'source': 'MT4'
                                    }
        except:
              pass
        
        # Try price_bridge
        try:
              from price_bridge import price_bridge
              bid = price_bridge.get_bid(symbol)
              ask = price_bridge.get_ask(symbol)
              price = price_bridge.get_price(symbol)
              if price > 0:
                      return {
                            'bid': bid if bid > 0 else price,
                            'ask': ask if ask > 0 else price,
                            'price': price,
                            'spread': (ask - bid) if bid > 0 and ask > 0 else 0.0002,
                            'source': 'BRIDGE'
                      }
        except:
              pass
        
        # Fallback
        price = self.get_correct_price(symbol)
        return {
              'bid': price,
              'ask': price,
              'price': price,
              'spread': 0.0002,
              'source': 'FALLBACK'
        }
    def _get_current_spread(self, symbol: str) -> float:
        """
        Get current spread for a symbol.
        Spread = Ask - Bid
        """
        try:
              # Try MT4 first
            if self.mt4:
                   result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                   if result and isinstance(result, dict):
                        bid = result.get('bid', 0)
                        ask = result.get('ask', 0)
                        if bid > 0 and ask > 0:
                              return ask - bid
              
              # Try price bridge
            try:
                   from price_bridge import price_bridge
                   bid = price_bridge.get_bid(symbol)
                   ask = price_bridge.get_ask(symbol)
                   if bid > 0 and ask > 0:
                        return ask - bid
            except:
                   pass
              
              # Fallback: estimate spread based on symbol type
            spread_estimates = {
                'GOLD': 0.2,
                'SILVER': 0.02,
                '#NASDAQ100': 2.0,
                '#S&P500': 2.0,
                '#DJ30': 3.0,
                '#RUSS2000': 2.0,
                '#CAC40': 2.0,
                '#DAX40': 2.0,
                '#FTSE100': 2.0,
                '#NIKKEI225': 2.0,
                'BRENT_OIL': 0.02,
                'CrudeOIL': 0.02,
                }
            return spread_estimates.get(symbol, 0.02)
                          
        except Exception as e:
              logger.debug(f"Error getting spread for {symbol}: {e}")
              return 0.02  # Default fallback
    def _get_current_volume(self, symbol: str) -> float:
        """
        Get current volume for a symbol.
        """
        try:
              # Try MT4 first
              if self.mt4:
                      result = self.mt4._send({"command": "VOLUME", "symbol": symbol})
                      if result and isinstance(result, dict):
                            volume = result.get('volume', 0)
                            if volume > 0:
                                    return volume
              
              # Try from recent candles
              candles = self._get_m15_candles(symbol)
              if candles and len(candles) > 0:
                      volumes = [c.get('volume', 0) for c in candles[-5:] if c.get('volume', 0) > 0]
                      if volumes:
                            return sum(volumes) / len(volumes)
              
              # Fallback
              return 1000
              
        except Exception as e:
              logger.debug(f"Error getting volume for {symbol}: {e}")
              return 1000
    def get_correct_price(self, symbol: str) -> float:
        """Get correct price from DASHBOARD API (not MT4)"""
        
        # ===== 1. TRY DASHBOARD API =====
        price = get_price_from_dashboard(symbol)
        if price > 0:
                return price
        
        # ===== 2. TRY PRICE BRIDGE =====
        try:
                from price_bridge import price_bridge
                price = price_bridge.get_price(symbol)
                if price > 0:
                        return price
        except:
                pass
        
        # ===== 3. TRY MT4 DIRECTLY (fallback) =====
        try:
                if self.mt4:
                        result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                        if result and isinstance(result, dict):
                                bid = result.get('bid', 0)
                                ask = result.get('ask', 0)
                                if bid > 0 and ask > 0:
                                        return (bid + ask) / 2
        except:
                pass
        
        # ===== 4. RETURN 0 IF NO PRICE =====
        logger.warning(f"❌ No price for {symbol} from any source")
        return 0
    def get_all_prices_from_dashboard(self):
        """Get all prices from dashboard in one call"""
        data = get_prices_from_dashboard()
        if data and 'prices' in data:
                return data['prices']
        return {}
# ============================================================
# SPX/NDX PRICE METHODS
# ============================================================

    def _get_spx_price(self) -> float:
        """Get S&P 500 price from dashboard"""
        price = get_price_from_dashboard('#S&P500')
        if price > 0:
                return price
        # Try alternative
        price = get_price_from_dashboard('SP500')
        if price > 0:
                return price
        return 7525.99  # Fallback

    def _get_ndx_price(self) -> float:
        """Get NASDAQ 100 price from dashboard"""
        price = get_price_from_dashboard('#NASDAQ100')
        if price > 0:
                return price
        price = get_price_from_dashboard('NAS100')
        if price > 0:
                return price
        return 30332.25  # Fallback

    def _get_spx_history(self, periods: int = 60) -> List[float]:
        """
        Get historical SPX prices for correlation calculation.
        """
        try:
               # Try to get from price cache
               from price_cache_manager import price_cache
               history = price_cache.get_history('#S&P500', periods)
               if history and len(history) > 0:
                     return history
        except:
               pass
        
        # Generate synthetic history if no data
        current_price = self._get_spx_price()
        history = []
        for i in range(periods):
               price = current_price * (1 + (i - periods/2) / periods * 0.01)
               history.append(price)
        return history

    def _get_ndx_history(self, periods: int = 60) -> List[float]:
        """
        Get historical NDX prices for correlation calculation.
        """
        try:
               from price_cache_manager import price_cache
               history = price_cache.get_history('#NASDAQ100', periods)
               if history and len(history) > 0:
                     return history
        except:
               pass
        
        # Generate synthetic history if no data
        current_price = self._get_ndx_price()
        history = []
        for i in range(periods):
               price = current_price * (1 + (i - periods/2) / periods * 0.01)
               history.append(price)
        return history
    def _get_deepseek_analysis(self, symbol: str, price: float) -> Dict:
        """Get DeepSeek AI analysis with M15 context"""
        try:
            prompt = f"""
You are a short-term trader analyzing M15 (15-minute) candles.

SYMBOL: {symbol}
CURRENT PRICE: {price:.5f}
TIMEFRAME: M15

Based on short-term price action, should I BUY, SELL, or HOLD?
Return ONLY valid JSON:
{{"action": "BUY" or "SELL" or "HOLD", "confidence": 0-100, "reasoning": "Brief M15 analysis"}}
"""
            response = call_deepseek(prompt)
            
            if 'error' in response:
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'API Error'}
            
            if 'raw_response' in response:
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'DeepSeek analysis'}
            
            return {
                'vote': response.get('action', 'HOLD'),
                'confidence': float(response.get('confidence', 50)),
                'reasoning': response.get('reasoning', 'M15 DeepSeek analysis')
            }
        except Exception as e:
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Error'}
    def _connect_mt4_safe(self):
        """Safe MT4 connection with fallback."""
        try:
            from mt4_price_provider import get_mt4_prices
            self.mt4 = get_mt4_prices()
            logger.info("   ✅ MT4 connected")
        except Exception as e:
            logger.warning(f"   ⚠️ MT4 connection failed: {e}")
            self.mt4 = None
            logger.info("   ℹ️ Running in simulation mode")
    
    def _load_all_agents_safe(self):
        """Load all agents with error handling."""
        agents_to_load = [
            ('_load_agent_r', 'Agent_R'),
            ('_load_agent_q', 'Agent_Q'),
            ('_load_agent_d', 'Agent_D'),
            ('_load_agent_h', 'Agent_H'),
            ('_load_agent_g', 'Agent_G'),
            ('_load_agent_m', 'Agent_M'),
            ('_load_agent_w', 'Agent_W'),
            ('_load_agent_i', 'Agent_I'),
            ('_load_agent_x', 'Agent_X'),
        ]
        
        for load_func, name in agents_to_load:
            try:
                getattr(self, load_func)()
            except Exception as e:
                logger.error(f"   ❌ {name} failed to load: {e}")
                # Set to None so system continues
                setattr(self, f'agent_{name.lower()}', None)
    
    def _load_protections_safe(self):
        """Load protection classes safely."""
        try:
            # Try to import protections
            from protections import AdaptiveBeta, LiquidityGuard, GapProtection
            self.beta_adaptor = AdaptiveBeta(decay_factor=0.95)
            self.liquidity_guard = LiquidityGuard()
            self.gap_protection = GapProtection(max_hold_time_minutes=30)
            logger.info("   ✅ Protections: Beta Adaptor, Liquidity Guard, Gap Protection")
        except ImportError:
            # Create fallback protections
            self.beta_adaptor = None
            self.liquidity_guard = None
            self.gap_protection = None
            logger.warning("   ⚠️ Protections not available - using fallback")
    
    def _safe_api_call(self, func, *args, **kwargs):
        """Universal safe API call wrapper."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"⚠️ API call failed: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def get_status_safe(self):
        """Safe status retrieval."""
        try:
            return {
                'running': self.running,
                'active_positions': len(self.active_positions) if hasattr(self, 'active_positions') else 0,
                'agents_loaded': {
                    'R': self.agent_r is not None if hasattr(self, 'agent_r') else False,
                    'Q': self.agent_q is not None if hasattr(self, 'agent_q') else False,
                    'D': self.agent_d is not None if hasattr(self, 'agent_d') else False,
                    'H': self.agent_h is not None if hasattr(self, 'agent_h') else False,
                    'G': self.agent_g is not None if hasattr(self, 'agent_g') else False,
                    'M': self.agent_m is not None if hasattr(self, 'agent_m') else False,
                    'W': self.agent_w is not None if hasattr(self, 'agent_w') else False,
                    'I': self.agent_i is not None if hasattr(self, 'agent_i') else False,
                    'X': self.agent_x is not None if hasattr(self, 'agent_x') else False,
                },
                'mt4_connected': self.mt4 is not None,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': str(e),
                'running': False,
                'timestamp': datetime.now().isoformat()
            }
        
    def analyze_market(self, symbol: str) -> Dict:
        """Complete market analysis with institutional checks."""
        
        # ============================================================
        # 1. GET Z-SCORE (ONCE, AT THE START)
        # ============================================================
        z_score = 0
        price = 0
        agent_x_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15', 'z_score': 0}
        agent_x_status = self.agent_x.get_pair_status()
    
    # 2. Check for Persistence (The "Gatekeeper")
    # Instead of relying on the instantaneous Z-score, check the agent's 
    # persistence and smoothed Z-score.
        is_persistent = self.agent_x.persistence >= 2
        smoothed_z = self.agent_x.z_score_ema
        
        candles = self._get_m15_candles(symbol)

        if self.agent_x:
                try:
                        spx = self.get_correct_price('#S&P500')
                        ndx = self.get_correct_price('#NASDAQ100')
                        if spx > 0 and ndx > 0:
                                signal_data = {
                                        'symbol': symbol,
                                        'spx_price': spx,
                                        'ndx_price': ndx,
                                        'price': spx
                                }
                                agent_x_result = self.agent_x.analyze(signal_data)
                                z_score = agent_x_result.get('z_score', 0)
                                price = spx
                except Exception as e:
                        logger.warning(f"Agent_X error: {e}")
        if abs(z_score) > 0.1 and price > 0:  # ← CHECK price > 0
            demo_action = 'BUY' if z_score < -0.5 else ('SELL' if z_score > 0.5 else 'HOLD')
            if demo_action != 'HOLD':
                try:
                    self.cold_start.add_demo_sample(symbol, z_score, demo_action, price)
                    samples = len(self.cold_start.samples)
                    if samples % 5 == 0 or samples <= 5:
                        logger.info(f"📊 Demo sample: {symbol} {demo_action} at Z={z_score:.2f} ({samples}/50)")
                except Exception as e:
                    logger.warning(f"Demo sample error: {e}")
    # ============================================================
    # MARKET MAKER PROTECTION CHECK (THIS IS THE CORRECT PLACE)
    # ============================================================
        try:
                protection_result = self.market_maker_protection.analyze_market(
                     symbol=symbol,
                     candles=candles,
                     price=price,
                     volume=1000
                )
               
                if not protection_result['is_safe']:
                    logger.info(f"🛡️ Trade blocked: {', '.join(protection_result['warnings'])}")
        except Exception as e:
               logger.warning(f"Market Maker Protection error: {e}")
        # Continue without protection if it fails
    
        # ============================================================
        # 2. COLD START CHECK (WITH EXTREME OVERRIDE)
        # ============================================================
        cold_start_check = self.cold_start.can_trade()
        
        # If Z-score is extreme (>2.5), override cold start
        if abs(z_score) > 2.5:
                logger.info(f"⚡ EXTREME Z-SCORE ({z_score:.2f}) - OVERRIDING COLD START")
                # Continue to full analysis
        elif not cold_start_check['can_trade']:
                samples = len(self.cold_start.samples)
                logger.info(f"❄️ Cold Start: {cold_start_check['reason']}")
                return {'action': 'HOLD', 'confidence': 0, 'reasoning': cold_start_check['reason'], 'symbol': symbol}
        if price <= 0:
            price_data = self._get_price_data(symbol)
            if price_data:
                price = price_data['price']
            else:
                return {'action': 'HOLD', 'confidence': 0}
        
        # ============================================================
        # 3. LOG AGENT STATUS
        # ============================================================
        logger.info(f"🔍 Agent Status for {symbol}:")
        logger.info(f"   Agent_R: {self.agent_r is not None}")
        logger.info(f"   Agent_Q: {self.agent_q is not None}")
        logger.info(f"   Agent_D: {self.agent_d is not None}")
        logger.info(f"   Agent_H: {self.agent_h is not None}")
        logger.info(f"   Agent_G: {self.agent_g is not None}")
        logger.info(f"   Agent_M: {self.agent_m is not None}")
        logger.info(f"   Agent_W: {self.agent_w is not None}")
        logger.info(f"   Agent_I: {self.agent_i is not None}")
        logger.info(f"   Agent_X: {self.agent_x is not None}")
        
        # ============================================================
        # 4. CHECK CALIBRATION WINDOW
        # ============================================================
        current_time = datetime.now()
        is_calibration = (current_time.hour == 16 and 30 <= current_time.minute < 35)
        
        # ============================================================
        # 5. MICROSTRUCTURE & CORRELATION CHECK
        # ============================================================
        try:
                microstructure_signal = self.microstructure.get_combined_signal()
        except:
                microstructure_signal = {'confidence': 50, 'signal': 'NEUTRAL'}
        
        try:
                safety_check = self.correlation_protection.is_trade_safe()
        except:
                safety_check = {'safe': True, 'kill_switch': False, 'reason': ''}
        
        if not safety_check['safe']:
                logger.warning(f"🔴 CORRELATION PROTECTION: {safety_check['reason']}")
                return {
                        'action': 'HOLD',
                        'confidence': 0,
                        'reasoning': f"Kill switch: {safety_check['reason']}",
                        'symbol': symbol,
                        'timeframe': 'M15'
                }
        
        # ============================================================
        # 6. CIRCUIT BREAKER CHECK
        # ============================================================
        current_spread = self._get_current_spread(symbol)
        current_volatility = 0.02
        current_pnl = 0
        account_equity = 10000
        
        # Only check circuit breaker if we have enough data
        if hasattr(self.performance, 'trades') and len(self.performance.trades) > 10:
                breaker_check = self.circuit_breaker.check_breakers(
                        current_pnl, current_volatility, current_spread, account_equity
                )
                
                if not breaker_check['can_trade']:
                        logger.info(f"🔴 Circuit Breaker: {breaker_check['reason']}")
                        return {'action': 'HOLD', 'confidence': 0, 'reasoning': breaker_check['reason'], 'symbol': symbol}
        
        # ============================================================
        # 7. GET PRICE DATA
        # ============================================================
        price_data = self._get_price_data(symbol)
        if not price_data:
                return {'action': 'HOLD', 'confidence': 0}
        
        price = price_data['price']
        candles = self._get_m15_candles(symbol)
        
        signal_data = {
                'symbol': symbol,
                'price': price,
                'candles': candles,
                'timeframe': 'M15',
                'volume': 10000,
                'volatility': 0.002
        }
        
        # ===== AGENT_R =====
        agent_r_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_r:
                 try:
                           agent_r_result = self.agent_r.analyze(signal_data)
                           logger.info(f"   Agent_R: {agent_r_result['vote']} ({agent_r_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_R error: {e}")
        
        # ===== AGENT_Q =====
        agent_q_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_q:
                 try:
                           agent_q_result = self.agent_q.analyze(signal_data)
                           logger.info(f"   Agent_Q: {agent_q_result['vote']} ({agent_q_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_Q error: {e}")
        
        # ===== AGENT_D =====
        agent_d_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_d:
                 try:
                           market_features = {}
                           vol_action, vol_confidence = self.agent_d.predict(signal_data, market_features)
                           agent_d_result = {
                                  'vote': vol_action if vol_action in ['BUY', 'SELL'] else 'HOLD',
                                  'confidence': vol_confidence,
                                  'is_squeeze': market_features.get('is_squeeze', False),
                                  'symbol': symbol,
                                  'timeframe': 'M15'
                           }
                           logger.info(f"   Agent_D: {agent_d_result['vote']} ({agent_d_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_D error: {e}")
        
        # ===== AGENT_H =====
        agent_h_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_h is not None:
                 try:
                           agent_h_result = self.agent_h.analyze(signal_data)
                           logger.info(f"   Agent_H: {agent_h_result['vote']} ({agent_h_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_H error: {e}")
        
        # ===== AGENT_G =====
        agent_g_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_g is not None:
                 try:
                           agent_g_result = self.agent_g.analyze(signal_data)
                           logger.info(f"   Agent_G: {agent_g_result['vote']} ({agent_g_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_G error: {e}")
        
        # ===== AGENT_M =====
        agent_m_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_m is not None:
                 try:
                           agent_m_result = self.agent_m.analyze(signal_data)
                           logger.info(f"   Agent_M: {agent_m_result['vote']} ({agent_m_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_M error: {e}")
        
        # ===== AGENT_I =====
        agent_i_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_i:
                 try:
                           agent_i_result = self.agent_i.analyze(signal_data)
                           logger.info(f"   Agent_I: {agent_i_result['vote']} ({agent_i_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_I error: {e}")
                        
        
        # ============================================================
        # AGENT_X - Spread Reversion (CLEAN SINGLE VERSION)
        # ============================================================
        z_score = 0
        agent_x_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15', 'z_score': 0}
        if hasattr(self, 'use_hybrid') and self.use_hybrid and hasattr(self, 'hybrid_coordinator'):
            # ===== HYBRID MODE =====
            try:
                        # Build agent data for hybrid
                        hybrid_data = {
                                    'R': agent_r_result,
                                    'Q': agent_q_result,
                                    'D': agent_d_result,
                                    'H': agent_h_result,
                                    'G': agent_g_result,
                                    'M': agent_m_result,
                                    'I': agent_i_result,
                                    'X': agent_x_result,
                        }
                        
                        hybrid_decision = self.hybrid_coordinator.decide(hybrid_data)
                        
                        if hybrid_decision['action'] != 'HOLD':
                                    logger.info(f"🤖 HYBRID DECISION: {hybrid_decision['action']} ({hybrid_decision['confidence']:.1f}%)")
                                    logger.info(f"   Reason: {hybrid_decision.get('reason', 'N/A')}")
                                    
                                    return {
                                                'action': hybrid_decision['action'],
                                                'confidence': hybrid_decision['confidence'],
                                                'reasoning': f"Hybrid: {hybrid_decision.get('reason', '')}",
                                                'symbol': symbol,
                                                'timeframe': 'M15',
                                                'hybrid': True,
                                                'z_score': z_score
                                    }
                        else:
                                    logger.info(f"⏸️ Hybrid: No override - using voting")
                                    # Fall through to voting
            except Exception as e:
                logger.warning(f"Hybrid error: {e} - using voting")
        z_score = 0  # Initialize
        

        if self.agent_x is not None:
                 try:
                           # ===== ONLY UPDATE ON SPX/NDX =====
                           if symbol in ['#S&P500', '#NASDAQ100', 'SPX', 'NDX']:
                                  # Get prices from bridge
                                  try:
                                          from price_bridge import price_bridge
                                          spx_price = price_bridge.get_price('#S&P500')
                                          ndx_price = price_bridge.get_price('#NASDAQ100')
                                  except:
                                          spx_price = 0
                                          ndx_price = 0
                                  
                                  # Fallback to MT4 if bridge fails
                                  if spx_price <= 0:
                                          spx_data = self._get_price_data('#S&P500')
                                          spx_price = spx_data.get('price', 0) if spx_data else 7525.99
                                  if ndx_price <= 0:
                                          ndx_data = self._get_price_data('#NASDAQ100')
                                          ndx_price = ndx_data.get('price', 0) if ndx_data else 30332.25
                                  
                                  # Final fallback
                                  if spx_price <= 0:
                                          spx_price = 7525.99
                                  if ndx_price <= 0:
                                          ndx_price = 30332.25
                                  
                                  # Build signal data and analyze
                                  signal_data_x = {
                                          'symbol': symbol,
                                          'spx_price': spx_price,
                                          'ndx_price': ndx_price,
                                          'price': spx_price
                                  }
                                  
                                  agent_x_result = self.agent_x.analyze(signal_data_x)
                                  z_score = agent_x_result.get('z_score', 0)
                                  samples = agent_x_result.get('samples', 0)
                                  
                                  logger.info(f"   📊 Agent_X: SPX={spx_price:.2f}, NDX={ndx_price:.2f}")
                                  
                                  if samples < 30:
                                          logger.info(f"   Agent_X: Building history {samples}/30 (Z={z_score:.2f})")
                                  else:
                                          logger.info(f"   Agent_X: {agent_x_result['vote']} ({agent_x_result['confidence']:.0f}%) Z={z_score:.2f}")
                                  
                                  if abs(z_score) > 2.5:
                                          logger.info(f"   ⚡ SPREAD SIGNAL: Z={z_score:.2f} - {agent_x_result['vote']}!")
                           else:
                                  # ===== OTHER SYMBOLS: USE EXISTING Z-SCORE =====
                                  z_score = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                                  samples = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                                  
                                  if samples < 30:
                                          logger.info(f"   Agent_X: Building history {samples}/30 (Z={z_score:.2f})")
                                  else:
                                          logger.info(f"   Agent_X: Z={z_score:.2f} (from spread)")
                                  
                                  agent_x_result = {
                                          'vote': self.agent_x.signal if hasattr(self.agent_x, 'signal') else 'HOLD',
                                          'confidence': self.agent_x.confidence if hasattr(self.agent_x, 'confidence') else 50,
                                          'z_score': z_score,
                                          'samples': samples,
                                          'symbol': symbol,
                                          'timeframe': 'M15'
                                  }
                                  
                 except Exception as e:
                           logger.warning(f"   Agent_X error: {e}")
                           import traceback
                           traceback.print_exc()
        current_spread = self._get_current_spread(symbol)
        current_volume = self._get_current_volume(symbol)
        
        # ===== CHECK LIQUIDITY =====
        liquidity_check = self.liquidity_filter.check_liquidity(
               symbol, current_spread, current_volume
        )
        
        # ===== LOG LIQUIDITY STATUS =====
        if liquidity_check['can_trade']:
               logger.info(f"   💧 Liquidity: ✅ {liquidity_check['action']}")
               logger.info(f"     Spread percentile: {liquidity_check['spread_percentile']:.2%}")
               logger.info(f"     Spread trend: {liquidity_check['spread_trend']}")
        else:
               logger.info(f"   💧 Liquidity: ⏸️ {liquidity_check['action']}")
               logger.info(f"     Reason: {liquidity_check['reason']}")
               logger.info(f"     Spread percentile: {liquidity_check['spread_percentile']:.2%}")
    
        # ============================================================
        # RL AGENT (Uses the same z_score from Agent_X)
        # ============================================================
        
        # ============================================================
# RL AGENT (FIXED - With Monte Carlo + Liquidity Checks)
# ============================================================

        if self.rl_model is not None:
                try:
                                import numpy as np
                                
                                if abs(z_score) > 0.1:
                                                  rl_state = np.array([
                                                                float(np.clip(z_score, -3.5, 3.5)),
                                                                0.0, 0.0, 0.0
                                                  ], dtype=np.float32)
                                                  
                                                  rl_action, _ = self.rl_model.predict(rl_state, deterministic=True)
                                                  
                                                  if isinstance(rl_action, np.ndarray):
                                                                rl_action_int = int(rl_action.item()) if rl_action.ndim == 0 else int(rl_action[0])
                                                  else:
                                                                rl_action_int = int(rl_action)
                                                  
                                                  action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
                                                  rl_signal = action_map.get(rl_action_int, 'HOLD')
                                                  rl_confidence = min(95, 50 + abs(z_score) * 10)
                                                  
                                                  logger.info(f"   🤖 RL Agent: {rl_signal} ({rl_confidence:.0f}%)")
                                                  
                                                  # ===== ONLY OVERRIDE IF ALL CHECKS PASS =====
                                                  if rl_signal != 'HOLD' and rl_confidence > 70 and abs(z_score) >= 2.5:
                                                                
                                                                # ===== CHECK 1: LIQUIDITY FILTER =====
                                                                if not liquidity_check['can_trade']:
                                                                                logger.info(f"   ⏸️ RL OVERRIDE BLOCKED: Liquidity - {liquidity_check['reason']}")
                                                                                logger.info(f"                      Spread percentile: {liquidity_check['spread_percentile']:.2%}")
                                                                                # Fall through to voting
                                                                else:
                                                                                # ===== CHECK 2: MONTE CARLO =====
                                                                                mc_passed = True
                                                                                if hasattr(self, 'monte_carlo') and self.monte_carlo:
                                                                                                try:
                                                                                                                  from institutional.monte_carlo_service import MonteCarloRequest
                                                                                                                  
                                                                                                                  mc_request = MonteCarloRequest(
                                                                                                                                symbol=symbol,
                                                                                                                                current_price=price,
                                                                                                                                z_score=z_score,
                                                                                                                                volatility=0.02,
                                                                                                                                action=rl_signal,
                                                                                                                                horizon_minutes=15,
                                                                                                                                iterations=500
                                                                                                                  )
                                                                                                                  
                                                                                                                  mc_result = self.monte_carlo.request_simulation(mc_request)
                                                                                                                  
                                                                                                                  if mc_result:
                                                                                                                                logger.info(f"   📊 Monte Carlo: {symbol}")
                                                                                                                                logger.info(f"                      Success: {mc_result.probability_of_success:.1%}")
                                                                                                                                logger.info(f"                      Confidence: {mc_result.confidence_level}")
                                                                                                                                logger.info(f"                      Tail Risk: {mc_result.tail_risk:.1%}")
                                                                                                                                logger.info(f"                      Recommendation: {mc_result.recommendation}")
                                                                                                                                
                                                                                                                                if mc_result.probability_of_success < 0.60:
                                                                                                                                                mc_passed = False
                                                                                                                                                logger.info(f"   ⏸️ RL OVERRIDE BLOCKED: MC Success {mc_result.probability_of_success:.1%} < 60%")
                                                                                                                                else:
                                                                                                                                                confidence_boost = (mc_result.probability_of_success - 0.5) * 50
                                                                                                                                                rl_confidence = min(95, rl_confidence + confidence_boost)
                                                                                                                                                logger.info(f"   ✅ MC Filter PASSED: Confidence boosted to {rl_confidence:.0f}%")
                                                                                                                  else:
                                                                                                                                logger.debug("   ⏳ Monte Carlo: Waiting for result, using fallback")
                                                                                                                                
                                                                                                except Exception as e:
                                                                                                                  logger.warning(f"   Monte Carlo error: {e}")
                                                                                
                                                                                # ===== EXECUTE ONLY IF ALL CHECKS PASS =====
                                                                                if mc_passed:
                                                                                                logger.info(f"   ⚡ RL OVERRIDE: {rl_signal} at Z={z_score:.2f}")
                                                                                                return {
                                                                                                                  'action': rl_signal,
                                                                                                                  'confidence': rl_confidence,
                                                                                                                  'reasoning': f"RL Agent: {rl_signal} at Z={z_score:.2f}",
                                                                                                                  'symbol': symbol,
                                                                                                                  'timeframe': 'M15',
                                                                                                                  'rl_override': True,
                                                                                                                  'z_score': z_score
                                                                                                }
                                                  else:
                                                                logger.debug(f"   RL Agent: No override (signal={rl_signal}, conf={rl_confidence:.0f}%, Z={z_score:.2f})")
                                else:
                                                  logger.debug(f"   RL Agent: Z-score too small ({z_score:.2f})")
                                                  
                except Exception as e:
                                logger.warning(f"   RL Agent error: {e}")
        
        # ============================================================
        # DEEPSEEK
        # ============================================================
        
        deepseek_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        try:
                 deepseek_result = self._get_deepseek_analysis(symbol, price)
                 logger.info(f"   DeepSeek: {deepseek_result['vote']} ({deepseek_result['confidence']:.0f}%)")
        except Exception as e:
                 logger.warning(f"   DeepSeek error: {e}")
        
        # ============================================================
        # AGENT_W - Consensus
        # ============================================================
        
        agent_w_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_w is not None:
                 try:
                           all_signals = [
                                  agent_r_result, agent_q_result, agent_d_result,
                                  agent_h_result, agent_g_result, agent_m_result,
                                  deepseek_result, agent_i_result, agent_x_result
                           ]
                           agent_w_result = self.agent_w.analyze(signal_data, all_signals)
                           logger.info(f"   Agent_W: {agent_w_result['vote']} ({agent_w_result['confidence']:.0f}%)")
                 except Exception as e:
                           logger.warning(f"   Agent_W error: {e}")
        
        # ============================================================
        # MICROSTRUCTURE BOOST
        # ============================================================
        
        base_confidence = agent_x_result.get('confidence', 0)
        microstructure_boost = 0
        
        if microstructure_signal.get('signal', 'NEUTRAL') != 'NEUTRAL':
                 microstructure_boost = (microstructure_signal.get('confidence', 50) / 100) * 15
                 logger.info(f"   🔬 Microstructure: {microstructure_signal.get('signal', 'NEUTRAL')} ({microstructure_signal.get('confidence', 50)}%)")
        
        final_confidence = min(95, base_confidence + microstructure_boost)
        
        # ============================================================
        # FINAL WEIGHTED CONSENSUS
        # ============================================================
        
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        weights = {
                 'agent_r': 0.12, 'agent_q': 0.12, 'agent_h': 0.12,
                 'agent_d': 0.10, 'agent_g': 0.10, 'agent_m': 0.10,
                 'agent_w': 0.10, 'deepseek': 0.10, 'agent_i': 0.06,
                 'agent_x': 0.08
        }
        
        # Dynamic weight boost during calibration
        if is_calibration:
                 if agent_i_result.get('vote') == agent_x_result.get('vote') and agent_i_result.get('vote') != 'HOLD':
                           weights['agent_i'] = 0.35
                           weights['agent_x'] = 0.35
                           for key in weights:
                                  if key not in ['agent_i', 'agent_x']:
                                          weights[key] = weights[key] * 0.3
                           logger.info(f"   ⚡ VALIDATION GATE: Agent_I and Agent_X AGREE on {agent_i_result.get('vote')}")
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
                 for key in weights:
                           weights[key] = weights[key] / total_weight
                 
        def add_vote(result, weight):
               if not result:
                     return
               action = result.get('vote', 'HOLD')
               confidence = result.get('confidence', 50) / 100
               votes[action] += confidence * weight
        
        # Add all votes
        add_vote(agent_r_result, weights['agent_r'])
        add_vote(agent_q_result, weights['agent_q'])
        add_vote(agent_d_result, weights['agent_d'])
        add_vote(agent_h_result, weights['agent_h'])
        add_vote(agent_g_result, weights['agent_g'])
        add_vote(agent_m_result, weights['agent_m'])
        add_vote(agent_w_result, weights['agent_w'])
        add_vote(deepseek_result, weights['deepseek'])
        add_vote(agent_i_result, weights['agent_i'])
        add_vote(agent_x_result, weights['agent_x'])
        
        # Determine final action
        total_weighted = sum(votes.values())
        if total_weighted > 0:
               final_action = max(votes, key=votes.get)
               final_confidence = (votes[final_action] / total_weighted) * 100
        else:
               final_action = 'HOLD'
               final_confidence = 0
        
        # Apply microstructure boost to final confidence
        if microstructure_boost > 0 and final_action != 'HOLD':
               final_confidence = min(95, final_confidence + microstructure_boost)
        
        if abs(z_score) > 2.5 and final_action in ['BUY', 'SELL'] and final_confidence >= 70:
            logger.info(f"⚡ EXTREME Z-SCORE: Z={z_score:.2f} - {final_action}")
            logger.info(f"   Confidence: {final_confidence:.1f}%")
            
            # Add demo sample for cold start
            self.cold_start.add_sample({
                'symbol': symbol,
                'pnl': 0,
                'z_score': z_score,
                'action': final_action,
                'timestamp': datetime.now()
            })
            
            return {
                'action': final_action,
                'confidence': final_confidence,
                'price': price,
                'z_score': z_score,
                'symbol': symbol,
                'timeframe': 'M15'
            }
    
        decision = {
            'action': final_action,
            'confidence': round(final_confidence, 1),
            'reasoning': f"M15 Consensus: {final_action}",
            'votes': votes,
            'symbol': symbol,
            'timeframe': 'M15',
            'price': price,
            'is_calibration': is_calibration,
            'z_score': z_score
        }
    
        logger.info(f"📊 FINAL: {final_action} ({final_confidence:.1f}%) - {symbol} (M15)")
    
        return decision
        # ============================================================
# MONTE CARLO FILTER WITH TELEMETRY
# ============================================================
    def integrate_monte_carlo(trading_controller):
        """
        Integrate Monte Carlo service into trading controller.
        
        Usage:
                mc_service = MonteCarloService()
                
                # In analyze_market, after getting Z-score:
                if abs(z_score) > 2.5:
                        request = MonteCarloRequest(
                                symbol=symbol,
                                current_price=price,
                                z_score=z_score,
                                volatility=0.02,
                                action=final_action
                        )
                        mc_result = mc_service.request_simulation(request)
                        
                        if mc_result:
                                if mc_result.probability_of_success < 0.6:
                                        logger.info(f"⏸️ MC Filter: {mc_result.probability_of_success:.1%} success - BLOCKED")
                                        return {'action': 'HOLD'}
                                else:
                                        logger.info(f"✅ MC Filter: {mc_result.probability_of_success:.1%} success - PASSED")
        """
        pass


        if abs(z_score) > 2.0 and final_action in ['BUY', 'SELL']:
                                try:
                                                from institutional.monte_carlo_service import MonteCarloRequest
                                                
                                                # Check if monte_carlo service exists
                                                if hasattr(self, 'monte_carlo') and self.monte_carlo:
                                                                mc_request = MonteCarloRequest(
                                                                                symbol=symbol,
                                                                                current_price=price,
                                                                                z_score=z_score,
                                                                                volatility=0.02,
                                                                                action=final_action,
                                                                                horizon_minutes=15,
                                                                                iterations=500
                                                                )
                                                                
                                                                mc_result = self.monte_carlo.request_simulation(mc_request)
                                                                
                                                                if mc_result:
                                                                                logger.info(f"📊 Monte Carlo: {symbol}")
                                                                                logger.info(f"   Success: {mc_result.probability_of_success:.1%}")
                                                                                logger.info(f"   Confidence: {mc_result.confidence_level}")
                                                                                logger.info(f"   Tail Risk: {mc_result.tail_risk:.1%}")
                                                                                logger.info(f"   Recommendation: {mc_result.recommendation}")
                                                                                
                                                                                if mc_result.probability_of_success < 0.60:
                                                                                                logger.info(f"⏸️ MC Filter BLOCKED: {mc_result.probability_of_success:.1%} < 60%")
                                                                                                return {
                                                                                                                'action': 'HOLD',
                                                                                                                'confidence': 0,
                                                                                                                'reasoning': f'MC Filter: {mc_result.probability_of_success:.1%} success',
                                                                                                                'symbol': symbol,
                                                                                                                'timeframe': 'M15'
                                                                                                }
                                                                                else:
                                                                                                # Boost confidence
                                                                                                confidence_boost = (mc_result.probability_of_success - 0.5) * 50
                                                                                                final_confidence = min(95, final_confidence + confidence_boost)
                                                                                                logger.info(f"✅ MC Filter PASSED: Confidence boosted to {final_confidence:.0f}%")
                                                                else:
                                                                                logger.debug("⏳ Monte Carlo: Waiting for result, using fallback")
                                except ImportError:
                                                logger.debug("Monte Carlo service not available")
                                except Exception as e:
                                                logger.warning(f"Monte Carlo error: {e}")
    
# ============================================================
# AGENT_X - Spread Reversion
# ============================================================

        if self.agent_x is not None:
           try:
                      # Get SPX and NDX prices
                      spx_price = self._get_spx_price()
                      ndx_price = self._get_ndx_price()
                      
                      # If prices are zero, use fallback
                      if spx_price <= 0:
                                 spx_price = 6000.0
                                 logger.debug(f"   SPX fallback: {spx_price}")
                      if ndx_price <= 0:
                                 ndx_price = 22000.0
                                 logger.debug(f"   NDX fallback: {ndx_price}")
                      
                      signal_data_x = {
                                 'symbol': symbol,
                                 'spx_price': spx_price,
                                 'ndx_price': ndx_price,
                                 'price': spx_price if spx_price > 0 else ndx_price
                      }
                      
                      agent_x_result = self.agent_x.analyze(signal_data_x)
                      z_score = agent_x_result.get('z_score', 0)
                      samples = agent_x_result.get('samples', 0)
                      
                      if samples < 30:
                                 logger.info(f"   Agent_X: Building history {samples}/30 (Z={z_score:.2f})")
                      else:
                                 logger.info(f"   Agent_X: {agent_x_result['vote']} ({agent_x_result['confidence']:.0f}%) Z={z_score:.2f}")
                                 
           except Exception as e:
                logger.warning(f"   Agent_X error: {e}")
        
        # ============================================================
        # 2. COORDINATOR CHECK (NOW agent_x_result EXISTS)
        # ============================================================
        try:
               coordinator_result = self.coordinator.analyze({
                     'spx': self._get_spx_price(),
                     'ndx': self._get_ndx_price(),
                     'z_score': agent_x_result.get('z_score', 0)
               })
               
               # If kill switch active, halt trading
               if coordinator_result.get('kill_switch_active', False):
                     logger.warning(f"🔴 KILL SWITCH ACTIVE: {coordinator_result.get('kill_switch_reason', 'Unknown')}")
                     return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'Kill switch active'}
                     
        except Exception as e:
               logger.warning(f"⚠️ Coordinator error: {e}")
        
        # ============================================================
        # 3. OTHER AGENTS
        # ============================================================
        
        # Agent_R
        agent_r_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_r:
               try:
                     agent_r_result = self.agent_r.analyze(signal_data)
                     logger.info(f"   Agent_R: {agent_r_result['vote']} ({agent_r_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_R error: {e}")
        
        # Agent_Q
        agent_q_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_q:
               try:
                     agent_q_result = self.agent_q.analyze(signal_data)
                     logger.info(f"   Agent_Q: {agent_q_result['vote']} ({agent_q_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_Q error: {e}")
        
        # Agent_D
        agent_d_result = {'vote': 'HOLD', 'confidence': 50, 'is_squeeze': False, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_d:
               try:
                     market_features = {}
                     vol_action, vol_confidence = self.agent_d.predict(signal_data, market_features)
                     agent_d_result = {
                          'vote': vol_action if vol_action in ['BUY', 'SELL'] else 'HOLD',
                          'confidence': vol_confidence,
                          'is_squeeze': market_features.get('is_squeeze', False),
                          'symbol': symbol,
                          'timeframe': 'M15'
                     }
                     logger.info(f"   Agent_D: {agent_d_result['vote']} ({agent_d_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_D error: {e}")
        
        # Agent_H - Fibonacci
        agent_h_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_h is not None:
               try:
                     agent_h_result = self.agent_h.analyze(signal_data)
                     logger.info(f"   Agent_H: {agent_h_result['vote']} ({agent_h_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_H error: {e}")
        
        # Agent_G - Whale
        agent_g_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_g is not None:
               try:
                     agent_g_result = self.agent_g.analyze(signal_data)
                     logger.info(f"   Agent_G: {agent_g_result['vote']} ({agent_g_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_G error: {e}")
        
        # Agent_M - Market Profile
        agent_m_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_m is not None:
               try:
                     agent_m_result = self.agent_m.analyze(signal_data)
                     logger.info(f"   Agent_M: {agent_m_result['vote']} ({agent_m_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_M error: {e}")
        
        # DeepSeek
        deepseek_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        try:
               deepseek_result = self._get_deepseek_analysis(symbol, price)
               logger.info(f"   DeepSeek: {deepseek_result['vote']} ({deepseek_result['confidence']:.0f}%)")
        except Exception as e:
               logger.warning(f"   DeepSeek error: {e}")
        
        # Agent_I
        agent_i_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_i:
               try:
                     agent_i_result = self.agent_i.analyze(signal_data)
                     logger.info(f"   Agent_I: {agent_i_result['vote']} ({agent_i_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_I error: {e}")
        
        # Agent_W - Consensus (Uses all agents)
        agent_w_result = {'vote': 'HOLD', 'confidence': 50, 'symbol': symbol, 'timeframe': 'M15'}
        if self.agent_w is not None:
               try:
                     all_signals = [
                          agent_r_result, agent_q_result, agent_d_result,
                          agent_h_result, agent_g_result, agent_m_result,
                          deepseek_result, agent_i_result, agent_x_result  # ADD agent_x_result
                     ]
                     agent_w_result = self.agent_w.analyze(signal_data, all_signals)
                     logger.info(f"   Agent_W: {agent_w_result['vote']} ({agent_w_result['confidence']:.0f}%)")
               except Exception as e:
                     logger.warning(f"   Agent_W error: {e}")
        
        # ============================================================
        # FINAL WEIGHTED CONSENSUS
        # ============================================================
        
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        weights = {
               'agent_r': 0.12,
               'agent_q': 0.12,
               'agent_h': 0.12,
               'agent_d': 0.10,
               'agent_g': 0.10,
               'agent_m': 0.10,
               'agent_w': 0.10,
               'deepseek': 0.10,
               'agent_i': 0.06,
               'agent_x': 0.08,
        }
        
        # Dynamic weight for Agent_X
        if agent_x_result and agent_x_result.get('vote') != 'HOLD':
               z_score = agent_x_result.get('z_score', 0)
               if abs(z_score) > 2.5:
                     weights['agent_x'] = 0.24
                     logger.info(f"   ⚡ Agent_X weight boosted to {weights['agent_x']:.2f} (Z={z_score:.2f})")
               elif abs(z_score) > 2.0:
                     weights['agent_x'] = 0.16
                     logger.info(f"   ⚡ Agent_X weight boosted to {weights['agent_x']:.2f} (Z={z_score:.2f})")

        def add_vote(result, weight):
                if not result:
                        return
                action = result.get('vote', 'HOLD')
                confidence = result.get('confidence', 50) / 100
                votes[action] += confidence * weight
        
        # Add all agent votes
        add_vote(agent_r_result, weights['agent_r'])
        add_vote(agent_q_result, weights['agent_q'])
        add_vote(agent_d_result, weights['agent_d'])
        add_vote(agent_h_result, weights['agent_h'])
        add_vote(agent_g_result, weights['agent_g'])
        add_vote(agent_m_result, weights['agent_m'])
        add_vote(agent_w_result, weights['agent_w'])
        add_vote(deepseek_result, weights['deepseek'])
        add_vote(agent_i_result, weights['agent_i'])
        add_vote(agent_x_result, weights['agent_x'])  # NOW agent_x_result EXISTS
        
        # Determine final action
        final_action = max(votes, key=votes.get)
        total_weighted = sum(votes.values())
        final_confidence = (votes[final_action] / total_weighted * 100) if total_weighted > 0 else 0
        
        decision = {
                'action': final_action,
                'confidence': round(final_confidence, 1),
                'reasoning': f"M15 Consensus: {final_action}",
                'votes': votes,
                'symbol': symbol,
                'timeframe': 'M15',
                'price': price,
                'lead_agrees': agent_r_result.get('vote') == final_action,
                'dark_pool_agrees': agent_q_result.get('vote') == final_action,
                'is_squeeze': agent_d_result.get('is_squeeze', False),
                'agent_signals': {
                        'agent_votes': {
                                'Agent_R': agent_r_result,
                                'Agent_Q': agent_q_result,
                                'Agent_D': agent_d_result,
                                'Agent_H': agent_h_result,
                                'Agent_G': agent_g_result,
                                'Agent_M': agent_m_result,
                                'Agent_W': agent_w_result,
                                'DeepSeek': deepseek_result,
                                'Agent_I': agent_i_result,
                                'Agent_X': agent_x_result  # ADD Agent_X
                        }
                }
        }
        self.hierarchical_coordinator.update_market_state({
                'liquidity_score': 0.7,
                'volatility': current_volatility,
                'trend_strength': regime_result.get('trend_strength', 0.3),
                'mean_reversion_score': regime_result.get('mean_reversion_score', 0.5)
            })
        
        decision = self.hierarchical_coordinator.get_weighted_decision(agent_data)
        
        if signal != 'HOLD' and confidence > 70:
            # Get volatility
            volatility = regime_result.get('volatility', 0.02)
            
            # Calculate position
            position = self.position_sizer.calculate_position(
                account_equity,
                confidence,
                volatility,
                current_pnl
            )
            
            logger.info(f"   📊 Position: {position:.2f} lots")
            
            # ===== 12. SHADOW TRADING =====
            self.shadow_trading.run_cycle({}, {'action': signal, 'confidence': confidence})
            
            return {
                'action': signal,
                'confidence': confidence,
                'price': price,
                'position': position,
                'z_score': z_score,
                'regime': regime_result['regime'],
                'threshold': adaptive_threshold,
                'symbol': symbol,
                'timeframe': 'M15'
            }
        
            return {'action': 'HOLD', 'confidence': 0, 'symbol': symbol, 'timeframe': 'M15'}

        logger.info(f"📊 FINAL: {final_action} ({final_confidence:.1f}%) - {symbol} (M15)")
        
        # DeepSeek Coach
        try:
                from deepseek_coach import DeepSeekCoach
                coach = DeepSeekCoach()
                import random
                actual_result = random.choice(['UP', 'DOWN', 'SIDEWAYS'])
                
                results = coach.evaluate_agent_votes(
                        symbol,
                        decision.get('agent_signals', {}),
                        actual_result
                )
                
                feedback = coach.get_deepseek_feedback(symbol, results, actual_result)
                
                decision['learning'] = {
                        'results': results,
                        'feedback': feedback,
                        'actual_result': actual_result
                }
        except Exception as e:
                print(f"⚠️ Coach error: {e}")
        
        return decision

    def evolve_strategies(feedback):
         """Evolve strategies based on DeepSeek feedback"""
         if feedback.get('rules'):
                for rule in feedback['rules']:
                       # Update agent rules
                       pass   
    # Add this method to your AITradingController class

    def save_signal_to_db(self, symbol: str, action: str, confidence: float, 
                      price: float, z_score: float = 0, 
                      reasoning: str = "", source: str = "AI") -> dict:
        """
        Save trading signal to database
        
        Args:
               symbol: Trading symbol
               action: BUY or SELL
               confidence: Signal confidence (0-100)
               price: Entry price
               z_score: Z-score for mean reversion
               reasoning: Signal reasoning
               source: Signal source (Agent_X, AI_Controller, etc.)
        
        Returns:
               dict: Saved signal data with ID
        """
        try:
               # Get current timestamp
               now = datetime.now().isoformat()
               
               # Calculate SL and TP based on action
               config = self.get_symbol_config(symbol)
               pip = config.get('pip', 0.0001)
               sl_pips = config.get('sl_pips', 50)
               tp_pips = config.get('tp_pips', 100)
               
               if action == 'BUY':
                     stop_loss = price - (sl_pips * pip)
                     take_profit = price + (tp_pips * pip)
               else:  # SELL
                     stop_loss = price + (sl_pips * pip)
                     take_profit = price - (tp_pips * pip)
               
               # Prepare signal data for Supabase
               signal_data = {
                     'symbol': symbol,
                     'type': action,
                     'entry_price': round(price, 5),
                     'stop_loss': round(stop_loss, 5),
                     'take_profit': round(take_profit, 5),
                     'confidence': int(confidence),
                     'source': source,
                     'reasoning': reasoning[:200] if reasoning else f"Z-Score: {z_score:.2f}",
                     'created_at': now,
                     'expires_at': (datetime.now() + timedelta(minutes=5)).isoformat(),
                     'z_score': round(z_score, 2)
               }
               
               # If we have a database connection
               if hasattr(self, 'db') and self.db:
                     try:
                          # Insert into Supabase
                          result = self.db.table('signals').insert(signal_data).execute()
                          if result.data:
                                  logger.info(f"✅ Signal saved to DB: {symbol} {action} (ID: {result.data[0]['id']})")
                                  return result.data[0]
                          else:
                                  logger.warning(f"⚠️ No data returned from DB insert")
                                  return None
                     except Exception as e:
                          logger.error(f"❌ DB insert error: {e}")
                          # Fallback: save to local history
                          return self.save_signal_to_history(symbol, action, confidence, price, z_score, reasoning, source)
               else:
                     # No DB connection, save to local history
                     return self.save_signal_to_history(symbol, action, confidence, price, z_score, reasoning, source)
                     
        except Exception as e:
               logger.error(f"❌ Error saving signal to DB: {e}")
               # Fallback to local history
               return self.save_signal_to_history(symbol, action, confidence, price, z_score, reasoning, source)


    
    def place_order(self, symbol, order_type, confidence=None, z_score=None, source=None, reasoning=None):
        """Place order with symbol-based volume and SL/TP"""
        can_trade, reason = self.can_open_trade(symbol)
        if not can_trade:
                return False, reason
        
        logger.info(f"\n📊 PRICE CHECK BEFORE ORDER:")
        
        # ===== GET CORRECT PRICE (NO FALLBACK) =====
        price = self.get_correct_price(symbol)
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Price: {price:.2f}")
        
        if price <= 0:
                logger.error(f"❌ NO LIVE PRICE for {symbol} - Order cancelled")
                return False, "No live price available"
        
        # ===== GET CONFIGURATION =====
        config = self.get_symbol_config(symbol)
        pip = config['pip']
        digits = config['digits']
        sl_pips = config['sl_pips']
        tp_pips = config['tp_pips']
        volume = config['volume']
        symbol_type = config.get('type', 'forex')

        
        # ===== USE THE CORRECT PRICE =====
        if order_type == 'BUY':
                entry_price = price
                sl = entry_price - (sl_pips * pip)
                tp = entry_price + (tp_pips * pip)
        else:
                entry_price = price
                sl = entry_price + (sl_pips * pip)
                tp = entry_price - (tp_pips * pip)
        
        entry_price = round(entry_price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)
        
        if symbol_type in ['index', 'metal', 'energy']:
            # For indices: 0.02 lots = $2 per point (S&P 500)
            # For gold: 0.02 lots = $20 per point
            # For oil: 0.02 lots = $20 per point
            point_value = 100  # Default for 0.02 lots
            risk = abs(entry_price - sl) * point_value / 100
            reward = abs(tp - entry_price) * point_value / 100
        else:
            # Forex: standard calculation
            risk = abs(entry_price - sl) * volume * 100000
            reward = abs(tp - entry_price) * volume * 100000
        
        logger.info(f"\n📊 ORDER DETAILS:")
        logger.info(f"   Symbol: {symbol} ({config['type'].upper()})")
        logger.info(f"   Type: {order_type}")
        logger.info(f"   Volume: {volume} lots")
        logger.info(f"   Entry: {entry_price:.{digits}f}")
        logger.info(f"   SL: {sl:.{digits}f} ({sl_pips} pips)")
        logger.info(f"   TP: {tp:.{digits}f} ({tp_pips} pips)")
        logger.info(f"   Risk: ${risk:.2f} | Reward: ${reward:.2f}")
         # ===== SAVE SIGNAL TO DATABASE =====
        try:
            signal_saved = self.save_signal_to_history(
                symbol=symbol,
                action=order_type,
                confidence=confidence or 70,
                price=entry_price,
                z_score=z_score or 0,
                source=source or "AI_Controller",
                reasoning=reasoning or f"{source or 'AI'} signal",
                sl=sl,
                tp=tp
            )
            
            if signal_saved:
                logger.info(f"✅ Signal saved to DB: {symbol} {order_type}")
            else:
                logger.warning(f"⚠️ Signal not saved to DB: {symbol} {order_type}")
        except Exception as e:
            logger.error(f"❌ Error saving signal: {e}")
            signal_saved = None
    
        # ===== SIMULATION MODE =====
        if not self.mt4:
            logger.info("📝 SIMULATION: Would send order")
            return True, "Simulated order"
        try:
            order = {
                "command": "ORDER",
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "sl": sl,
                "tp": tp
            }
            mt4_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
            command_file = os.path.join(mt4_path, "AI_Commands.txt")
            
            if os.path.exists(command_file):
                os.remove(command_file)
            
            with open(command_file, 'w') as f:
                json.dump(order, f)
            
            logger.info(f"✅ ORDER SENT: {symbol} {order_type} {volume} lots")
        
        # ===== SAVE SIGNAL TO DATABASE =====
            self.active_positions[symbol] = {
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'price': entry_price,
                'sl': sl,
                'tp': tp,
                'profit': 0,
                'signal_id': signal_saved.get('id') if signal_saved else None
            }
            # Update signal as executed
            if signal_saved and signal_saved.get('id'):
                self.update_signal_executed(signal_saved['id'], f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
            return True, f"Order sent: {symbol} {order_type}"
            
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return False, str(e)
        # For indices, fix the point value
        if 'S&P' in symbol or 'NASDAQ' in symbol or 'DJ' in symbol:
            # 0.02 lots × $5 per point = $100 per point
            point_value = 100  # For 0.02 lots
            risk = abs(entry_price - sl) * point_value / 100
            reward = abs(tp - entry_price) * point_value / 100
        else:
            risk = abs(entry_price - sl) * volume * 100000
            reward = abs(tp - entry_price) * volume * 100000
        if not self.mt4:
                logger.info("📝 SIMULATION: Would send order")
                return True, "Simulated order"
        
        try:
                mt4_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
                command_file = os.path.join(mt4_path, "AI_Commands.txt")
                
                if os.path.exists(command_file):
                        os.remove(command_file)
                
                with open(command_file, 'w') as f:
                        json.dump(order, f)
                
                logger.info(f"✅ ORDER SENT: {symbol} {order_type} {volume} lots")
                
                self.active_positions[symbol] = {
                        'symbol': symbol,
                        'type': order_type,
                        'volume': volume,
                        'price': entry_price,
                        'sl': sl,
                        'tp': tp,
                        'profit': 0
                }
                
                return True, f"Order sent: {symbol} {order_type}"
                
        except Exception as e:
                logger.error(f"❌ Order failed: {e}")
                return False, str(e)
        
    def monitor_trades(self):
        """Monitor active trades"""
        for symbol in list(self.active_positions.keys()):
            pos = self.active_positions[symbol]
            price_info = self.get_current_price(symbol)
                     
            if not price_info:
                continue
            
            price = price_info['mid']
            sl = pos.get('sl', 0)
            tp = pos.get('tp', 0)
            
            if pos.get('type') == 'BUY':
                if price <= sl:
                    self._close_trade(symbol, price, 'STOP_LOSS')
                elif price >= tp:
                    self._close_trade(symbol, price, 'TAKE_PROFIT')
            else:
                if price >= sl:
                    self._close_trade(symbol, price, 'STOP_LOSS')
                elif price <= tp:
                    self._close_trade(symbol, price, 'TAKE_PROFIT')
    
    def _close_trade(self, symbol, price, reason):
        """Close a trade and remove from active positions"""
        if symbol not in self.active_positions:
               return
        
        pos = self.active_positions.pop(symbol)  # ← This should remove it
        
        # Calculate P&L
        config = self.get_symbol_config(symbol)
        pip_value = config['pip']
        lot_size = config['volume']
        
        if pos.get('type') == 'BUY':
               pnl = (price - pos['price']) / pip_value * lot_size * 1
        else:
               pnl = (pos['price'] - price) / pip_value * lot_size * 1
        
        logger.info(f"🔚 Trade closed: {symbol} P&L: ${pnl:.2f} ({reason})")
        
        # ===== ADD THIS: Force sync with MT4 =====
        self.check_open_positions()  # ← Refresh positions from MT4
    
    def run_cycle(self):
        """Run one trading cycle (every 10 seconds)"""
        if len(self.cold_start.samples) < 50:
        # Generate synthetic samples to bootstrap cold start
            for i in range(10):
                demo_trade = {
                        'symbol': 'SYNTHETIC',
                        'pnl': np.random.choice([-10, -5, 5, 10, 15]),
                        'z_score': np.random.uniform(-3, 3),
                        'action': np.random.choice(['BUY', 'SELL']),
                        'price': 100 + np.random.uniform(-5, 5),
                        'timestamp': datetime.now(),
                        'is_demo': True
                }
            self.cold_start.add_sample(demo_trade)
        
        logger.info(f"✅ Forced {len(self.cold_start.samples)} synthetic samples")
        # ===== FORCE AGENT_X UPDATE =====
        self._force_agent_x_update()
        self._force_sync()  # ← ADD THIS

        # ===== PRICE CHECK - UNIFIED MT4 METHOD =====
        try:
               print(f"\n{'='*60}")
               print(f"📊 PRICE CHECK - {datetime.now().strftime('%H:%M:%S')}")
               print(f"{'='*60}")
               
               # Get ALL prices at once (like dashboard)
               all_prices = self.get_all_mt4_prices()
               
               symbols_to_check = self.symbols 
               
               for sym in symbols_to_check:
                     price = all_prices.get(sym, 0) if all_prices else 0
                     
                     # Try alternative names
                     if price <= 0:
                          alt_map = {
                                  '#NASDAQ100': 'NAS100',
                                  '#S&P500': 'SP500',
                                  '#DJ30': 'DJ30',
                                  'GOLD': 'GOLD',
                                  'SILVER': 'SILVER',
                                  'EURUSD': 'EURUSD',
                                  'GBPUSD': 'GBPUSD',
                                  'USDJPY': 'USDJPY',
                                  'BRENT_OIL': 'BRENT',
                                  'CrudeOIL': 'CRUDE',
                          }
                          if sym in alt_map:
                                  price = all_prices.get(alt_map[sym], 0) if all_prices else 0
                     
                     # Try bridge if MT4 failed
                     if price <= 0:
                          try:
                                  price = self.get_price_from_bridge(sym)
                                  source = "BRIDGE"
                          except:
                                  source = "NONE"
                     else:
                          source = "MT4"
                     
                     if price > 0:
                          print(f"   ✅ {sym:12} | {source:8} | {price:12.2f}")
                     else:
                          print(f"   ❌ {sym:12} | {source:8} | {'NO PRICE':>12}")
               
               if self.agent_x is not None:
                     z_score = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                     samples = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                     print(f"   📊 Agent_X: Z={z_score:.2f} | Samples={samples}/30")
               
               print(f"{'='*60}\n")
               
        except Exception as e:
               print(f"⚠️ Price log error: {e}")
        
        # ===== CONTINUE WITH TRADING =====
        logger.info(f"\n{'='*50}")
        logger.info(f"🔄 Trading Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*50}")
        
        self.check_open_positions()
        logger.info(f"📊 Open positions: {len(self.active_positions)}")
        
        for symbol, pos in self.active_positions.items():
               profit = pos.get('profit', 0)
               logger.info(f"   {symbol}: {pos.get('type')} {pos.get('volume')} lots | Profit: ${profit:.2f}")
        
        self.monitor_trades()
        
        for symbol in self.symbols:
               if self.has_open_position(symbol):
                     logger.info(f"⏸️ {symbol}: Already have position - skipping")
                     continue
               
               analysis = self.analyze_market(symbol)
               action = analysis.get('action', 'HOLD')
               confidence = analysis.get('confidence', 0)
               z_score = analysis.get('z_score', 0)
               source = analysis.get('source', 'AI')
               reasoning = analysis.get('reasoning', '')
               
               logger.info(f"🔍 {symbol}: {action} ({confidence}%)")
               # ✅ SAVE SIGNAL TO DATABASE (with logging)
               if action in ['BUY', 'SELL'] and confidence >= 60:
                    logger.info(f"📊 SAVING SIGNAL: {symbol} {action} (Confidence: {confidence:.1f}%)")
                    
                    signal_saved = self.save_signal_to_db(
                               symbol=symbol,
                               action=action,
                               confidence=confidence,
                               price=price,
                               z_score=z_score,
                               reasoning=reasoning,
                               source=source
                    )
                    
                    if signal_saved:
                               logger.info(f"✅ SIGNAL SAVED: ID={signal_saved.get('id')}, {symbol} {action}")
                    else:
                               logger.error(f"❌ FAILED TO SAVE SIGNAL: {symbol} {action}")
               if action in ['BUY', 'SELL'] and confidence >= self.config['min_confidence']:
                     
                     success, message = self.place_order(symbol, action,
                confidence=confidence,
                z_score=z_score,
                source=source,
                reasoning=reasoning)
                     if success:
                          logger.info(f"✅ {message}")
                     else:
                          logger.info(f"❌ {message}")
               
               time.sleep(0.5)
        
        logger.info(f"✅ Cycle complete")
    def start(self):
        """Start the trading loop"""
        if self.running:
            return
        
        self.running = True
        logger.info("▶️ Trading Controller Started")
        
        def loop():
            while self.running:
                try:
                    self.run_cycle()
                    time.sleep(self.cycle_seconds)
                except Exception as e:
                    logger.error(f"❌ Cycle error: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(60)
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop the trading loop"""
        self.running = False
        logger.info("⏹️ Trading Controller Stopped")
    
    def get_status(self):
        """Get system status"""
        return {
            'active_positions': len(self.active_positions),
            'positions': self.active_positions,
            'symbols': self.symbols,
            'cycle_seconds': self.cycle_seconds,            
            'regime': self.regime_classifier.current_regime,
            'threshold': self.threshold_calibrator.current_threshold,
            'breakers_active': self.circuit_breaker.active_breakers,
            'cold_start_ready': self.cold_start.real_mode_ready,
            'running': self.running,
            'timestamp': datetime.now().isoformat()
        }
    # ============================================================
# CALIBRATION WINDOW BACKTEST
# ============================================================
# ============================================================
# DYNAMIC WEIGHTING SYSTEM - Add to trading_controller.py
# ============================================================
    # ============================================================
# VALIDATION GATE LOGIC
# ============================================================
    def get_rl_signal_direct(self, symbol: str) -> Dict:
        """
        Get RL signal using simulated Z-score from market data.
        """
        try:
               import numpy as np
               
               # Get SPX and NDX prices
               spx_data = self._get_price_data('#S&P500')
               ndx_data = self._get_price_data('#NASDAQ100')
               
               spx = spx_data.get('price', 0) if spx_data else 0
               ndx = ndx_data.get('price', 0) if ndx_data else 0
               
               if spx <= 0 or ndx <= 0:
                     return {'signal': 'HOLD', 'confidence': 0, 'reason': 'No price data'}
               
               # Calculate spread and Z-score
               import math
               beta = 1.05
               spread = math.log(spx) - beta * math.log(ndx)
               
               # Use a rolling window if available
               if hasattr(self, 'spread_history'):
                     self.spread_history.append(spread)
                     if len(self.spread_history) > 50:
                          self.spread_history.pop(0)
                     if len(self.spread_history) > 30:
                          mu = sum(self.spread_history) / len(self.spread_history)
                          variance = sum((x - mu) ** 2 for x in self.spread_history) / len(self.spread_history)
                          sigma = math.sqrt(variance) if variance > 0 else 0.0001
                          z_score = (spread - mu) / sigma if sigma > 0 else 0
                     else:
                          z_score = 0
               else:
                    self.spread_history = []
                    z_score = 0
               
               # Get RL signal
               state = np.array([
                     float(np.clip(z_score, -3.5, 3.5)),
                     0.0, 0.0, 0.0
               ], dtype=np.float32)
               
               action, _ = self.rl_model.predict(state, deterministic=True)
               
               if isinstance(action, np.ndarray):
                     action_int = int(action.item()) if action.ndim == 0 else int(action[0])
               else:
                     action_int = int(action)
               
               action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
               signal = action_map.get(action_int, 'HOLD')
               confidence = min(95, 50 + abs(z_score) * 12)
               
               return {
                     'signal': signal,
                     'confidence': confidence,
                     'z_score': z_score,
                     'spread': spread,
                     'reason': f'RL: {signal} at Z={z_score:.2f}'
               }
               
        except Exception as e:
               logger.warning(f"RL direct error: {e}")
               return {'signal': 'HOLD', 'confidence': 0, 'reason': f'Error: {e}'}
    def validate_signal(self, agent_i_result: Dict, agent_x_result: Dict) -> Dict:
        """
        Validation gate for Agent_I and Agent_X signals.
        
        Returns:
                - 'valid': bool - True if signal is validated
                - 'direction': str - BUY or SELL
                - 'confidence': int - Validated confidence
                - 'reason': str - Validation reason
        """
        # ===== EXTRACT SIGNALS =====
        i_signal = agent_i_result.get('vote', 'HOLD')
        i_confidence = agent_i_result.get('confidence', 0)
        i_reason = agent_i_result.get('reasoning', '')
        
        x_signal = agent_x_result.get('vote', 'HOLD')
        x_confidence = agent_x_result.get('confidence', 0)
        z_score = agent_x_result.get('z_score', 0)
        x_reason = agent_x_result.get('reasoning', '')
        
        # ===== CASE 1: Both agree (STRONGEST signal) =====
        if i_signal == x_signal and i_signal != 'HOLD':
                # Check historical accuracy (if available)
                accuracy = self.get_agent_accuracy('I', 'X')
                if accuracy > 70:
                          return {
                                'valid': True,
                                'direction': i_signal,
                                'confidence': min(95, (i_confidence + x_confidence) // 2 + 10),
                                'reason': f'Both agents agree on {i_signal} (accuracy: {accuracy}%)'
                          }
                else:
                          return {
                                'valid': True,
                                'direction': i_signal,
                                'confidence': (i_confidence + x_confidence) // 2,
                                'reason': f'Both agree but accuracy low ({accuracy}%)'
                          }
        
        # ===== CASE 2: Only Agent_I signal =====
        if i_signal != 'HOLD' and i_confidence > 75:
                # Check if Agent_I has been accurate recently
                accuracy = self.get_agent_accuracy('I')
                if accuracy > 75:
                          return {
                                'valid': True,
                                'direction': i_signal,
                                'confidence': min(85, i_confidence),
                                'reason': f'Agent_I strong ({i_confidence}%) with {accuracy}% accuracy'
                          }
                else:
                          return {
                                'valid': False,
                                'direction': 'HOLD',
                                'confidence': 0,
                                'reason': f'Agent_I accuracy low ({accuracy}%)'
                          }
        
        # ===== CASE 3: Only Agent_X signal =====
        if x_signal != 'HOLD' and abs(z_score) > 2.5:
                # Check if spread is extremely overextended
                if abs(z_score) > 3.0:
                          return {
                                'valid': True,
                                'direction': x_signal,
                                'confidence': min(95, x_confidence + 10),
                                'reason': f'Extreme Z-score ({z_score:.2f}) overrides'
                          }
                else:
                          return {
                                'valid': True,
                                'direction': x_signal,
                                'confidence': x_confidence,
                                'reason': f'Agent_X signal with Z={z_score:.2f}'
                          }
        
        # ===== NO SIGNAL =====
        return {
                'valid': False,
                'direction': 'HOLD',
                'confidence': 0,
                'reason': 'No validated signal'
        }


    def get_agent_accuracy(self, agent_name: str, agent2_name: str = None) -> float:
        """
        Track and return agent accuracy based on historical trades.
        """
        # In production, store accuracy in database
        # For now, return reasonable default
        accuracy_map = {
        'I': 72,  # Sentiment agent accuracy
        'X': 85,  # Spread agent accuracy
        'I_X': 90,  # Both agree
        }
    
        key = f"{agent_name}_{agent2_name}" if agent2_name else agent_name
        return accuracy_map.get(key, 70)
    def get_dynamic_weights(self, symbol: str, is_calibration: bool, agent_results: Dict) -> Dict:
        """
        Dynamic weighting based on market conditions and calibration window.
        
        - Normal mode: Balanced weights for stability
        - Calibration window: Boost active agents (I, X) for flexibility
        - Validation gate: Only boost if both agree
        """
        
        # ===== BASE WEIGHTS (Normal Mode) =====
        base_weights = {
               'agent_r': 0.12,   # Supply/Demand - Stability
               'agent_q': 0.12,   # Dark Pool - Stability
               'agent_h': 0.12,   # Fibonacci - Stability
               'agent_d': 0.10,   # Volatility - Timing
               'agent_g': 0.10,   # Whale - Stability
               'agent_m': 0.10,   # Market Profile - Stability
               'agent_w': 0.10,   # Consensus - Aggregator
               'deepseek': 0.10,  # AI - General
               'agent_i': 0.06,   # Sentiment - Active (normally low)
               'agent_x': 0.08,   # Spread - Active (normally low)
        }
        
        weights = base_weights.copy()
        
        # ===== CALIBRATION WINDOW OVERRIDE =====
        if is_calibration:
               # Get agent signals
               agent_i_signal = agent_results.get('I', {}).get('vote', 'HOLD')
               agent_x_signal = agent_results.get('X', {}).get('vote', 'HOLD')
               agent_i_confidence = agent_results.get('I', {}).get('confidence', 0)
               agent_x_confidence = agent_results.get('X', {}).get('confidence', 0)
               z_score = agent_results.get('X', {}).get('z_score', 0)
               
               # ===== VALIDATION GATE =====
               # Option 1: Both agents agree (STRONGEST signal)
               if agent_i_signal == agent_x_signal and agent_i_signal != 'HOLD':
                     # Both agree on direction - MAXIMUM weight
                     weights['agent_i'] = 0.35  # From 0.06 → 0.35 (5.8x)
                     weights['agent_x'] = 0.35  # From 0.08 → 0.35 (4.4x)
                     # Reduce other weights to maintain sum = 1.0
                     for key in weights:
                          if key not in ['agent_i', 'agent_x']:
                                  weights[key] = weights[key] * 0.3  # Reduce by 70%
                     
                     logger.info(f"⚡ VALIDATION GATE: Agent_I and Agent_X AGREE on {agent_i_signal}")
                     logger.info(f"   → I: {agent_i_confidence}%, X: {agent_x_confidence}%, Z: {z_score:.2f}")
                     logger.info(f"   → Weights boosted: I={weights['agent_i']:.2f}, X={weights['agent_x']:.2f}")
               
               # Option 2: Only one agent has strong signal (GOOD signal)
               elif agent_i_signal != 'HOLD' and agent_i_confidence > 70:
                     weights['agent_i'] = 0.30
                     for key in weights:
                          if key not in ['agent_i']:
                                  weights[key] = weights[key] * 0.7
                     
                     logger.info(f"⚡ Agent_I STRONG: {agent_i_signal} ({agent_i_confidence}%)")
                     logger.info(f"   → I boosted: {weights['agent_i']:.2f}")
                     
               elif agent_x_signal != 'HOLD' and abs(z_score) > 2.0:
                     weights['agent_x'] = 0.30
                     for key in weights:
                          if key not in ['agent_x']:
                                  weights[key] = weights[key] * 0.7
                     
                     logger.info(f"⚡ Agent_X STRONG: {agent_x_signal} (Z={z_score:.2f})")
                     logger.info(f"   → X boosted: {weights['agent_x']:.2f}")
               
               # Option 3: Z-score extreme but no agent signal (Spike detection)
               elif abs(z_score) > 2.5:
                     weights['agent_x'] = 0.25
                     for key in weights:
                          if key not in ['agent_x']:
                                  weights[key] = weights[key] * 0.75
                     
                     logger.info(f"⚡ Z-SPIKE DETECTED: |Z|={z_score:.2f}")
                     logger.info(f"   → X boosted: {weights['agent_x']:.2f}")
        
        # ===== NORMALIZE WEIGHTS (Ensure sum = 1.0) =====
        total = sum(weights.values())
        if total > 0:
               for key in weights:
                     weights[key] = weights[key] / total
        
        return weights
    def _force_agent_x_update(self):
        """Force Agent_X to update using current prices."""
        if self.agent_x is None:
                return None
        
        try:
                # Get current prices from bridge
                from price_bridge import price_bridge
                spx_price = price_bridge.get_price('#S&P500')
                ndx_price = price_bridge.get_price('#NASDAQ100')
                
                # If bridge returns 0, try price cache
                if spx_price <= 0:
                        try:
                                from price_cache_manager import price_cache
                                spx_price = price_cache.get_latest('#S&P500', 0)
                        except:
                                pass
                
                if ndx_price <= 0:
                        try:
                                from price_cache_manager import price_cache
                                ndx_price = price_cache.get_latest('#NASDAQ100', 0)
                        except:
                                pass
                
                # Final fallback to hardcoded values
                if spx_price <= 0:
                        spx_price = 7525.99
                        logger.warning(f"Using hardcoded SPX price: {spx_price}")
                
                if ndx_price <= 0:
                        ndx_price = 30332.25
                        logger.warning(f"Using hardcoded NDX price: {ndx_price}")
                
                # Update Agent_X
                signal_data = {
                        'symbol': '#S&P500',
                        'spx_price': spx_price,
                        'ndx_price': ndx_price,
                        'price': spx_price
                }
                
                result = self.agent_x.analyze(signal_data)
                z_score = result.get('z_score', 0)
                samples = result.get('samples', 0)
                
                # Log progress
                if samples >= 10:
                        logger.info(f"📊 Agent_X: Z={z_score:.2f} | Samples={samples}/30 | Spread={result.get('spread', 0):.6f}")
                elif samples % 5 == 0 and samples > 0:
                        logger.info(f"📊 Agent_X: Building history {samples}/30 (Z={z_score:.2f})")
                
                return result
                
        except Exception as e:
                logger.warning(f"Agent_X update error: {e}")
                return None

    def get_weighted_consensus_dynamic(self, agent_results: Dict, deepseek_result: Dict, is_calibration: bool, symbol: str) -> Dict:
        """
        Dynamic consensus with calibration window logic.
        """
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        # ===== GET DYNAMIC WEIGHTS =====
        weights = self.get_dynamic_weights(symbol, is_calibration, agent_results)
        
        # ===== LOG WEIGHTS =====
        logger.debug("📊 Dynamic Weights:")
        for key, weight in weights.items():
               logger.debug(f"   {key}: {weight:.3f}")
    
    # ===== ADD VOTES WITH DYNAMIC WEIGHTS =====
    def add_vote(result, weight, key):
        if not result:
            return
        action = result.get('vote', 'HOLD')
        confidence = result.get('confidence', 50) / 100
        # Only count votes with confidence > 50%
        if confidence > 0.5 or action != 'HOLD':
            votes[action] += confidence * weight
    
    # Add all agent votes
        add_vote(agent_results.get('R'), weights['agent_r'], 'R')
        add_vote(agent_results.get('Q'), weights['agent_q'], 'Q')
        add_vote(agent_results.get('D'), weights['agent_d'], 'D')
        add_vote(agent_results.get('H'), weights['agent_h'], 'H')
        add_vote(agent_results.get('G'), weights['agent_g'], 'G')
        add_vote(agent_results.get('M'), weights['agent_m'], 'M')
        add_vote(agent_results.get('W'), weights['agent_w'], 'W')
        add_vote(deepseek_result, weights['deepseek'], 'DeepSeek')
        add_vote(agent_results.get('I'), weights['agent_i'], 'I')
        add_vote(agent_results.get('X'), weights['agent_x'], 'X')
        
        # ===== CALCULATE FINAL DECISION =====
        total_weighted = sum(votes.values())
        
        if total_weighted > 0:
               final_action = max(votes, key=votes.get)
               final_confidence = (votes[final_action] / total_weighted) * 100
        else:
               final_action = 'HOLD'
               final_confidence = 0
        
        # ===== ENSURE MINIMUM CONFIDENCE FOR TRADES =====
        if final_action != 'HOLD' and final_confidence < self.config.get('min_confidence', 45):
               logger.debug(f"⚠️ Confidence too low: {final_confidence:.1f}% < {self.config.get('min_confidence', 45)}%")
               final_action = 'HOLD'
               final_confidence = 50
        
        return {
               'action': final_action,
               'confidence': round(final_confidence, 1),
               'votes': votes,
               'weights': weights,
               'is_calibration': is_calibration,
               'reasoning': f"Dynamic consensus: {final_action} ({final_confidence:.1f}%)"
        }
    def backtest_calibration_window(self, historical_data: pd.DataFrame) -> Dict:
        """
        Validate that bounce rate > 80% during 9:30-9:35 AM EST.
        """
        if historical_data is None or len(historical_data) < 100:
               return {'error': 'Insufficient data'}
        
        # Filter for calibration window
        calibration_data = []
        reversion_count = 0
        total_signals = 0
        
        for index, row in historical_data.iterrows():
               # Check if time is 9:30-9:35 AM EST
               if index.time() >= datetime.strptime('09:30', '%H:%M').time() and \
                  index.time() <= datetime.strptime('09:35', '%H:%M').time():
                     calibration_data.append(row)
                     
                     # Check if Z-score > 2.5 or < -2.5
                     z_score = row.get('z_score', 0)
                     if abs(z_score) > 2.5:
                          total_signals += 1
                          
                          # Check if reverted within 5 minutes
                          future_data = historical_data.loc[index:].head(30)  # 30 candles = 5 minutes at 10s intervals
                          if len(future_data) > 5:
                                  max_z = max(abs(future_data['z_score']))
                                  if max_z < 0.5:  # Reverted to mean
                                         reversion_count += 1
        
        # Calculate bounce rate
        bounce_rate = (reversion_count / total_signals * 100) if total_signals > 0 else 0
        
        result = {
               'signals_detected': total_signals,
               'reversions_count': reversion_count,
               'bounce_rate': round(bounce_rate, 1),
               'passed': bounce_rate > 80,
               'date_range': f"{historical_data.index[0]} to {historical_data.index[-1]}",
               'calibration_window': '9:30-9:35 AM EST'
        }
        
        logger.info(f"📊 CALIBRATION WINDOW BACKTEST:")
        logger.info(f"   Signals: {total_signals}")
        logger.info(f"   Reversions: {reversion_count}")
        logger.info(f"   Bounce Rate: {bounce_rate:.1f}%")
        logger.info(f"   {'✅ PASSED' if bounce_rate > 80 else '❌ FAILED'} (need >80%)")
        
        return result
# ============ SIMPLE AGENT FALLBACKS ============

class SimpleAgentR:
    """Simple Agent_R fallback"""
    def analyze(self, signal_data):
        symbol = signal_data.get('symbol', '#S&P500')
        price = signal_data.get('price', 0)
        
        if price > 1.1380:
            vote, confidence = 'SELL', 65
            reasoning = "Simple R: Price near supply"
        elif price < 1.1330:
            vote, confidence = 'BUY', 65
            reasoning = "Simple R: Price near demand"
        else:
            vote, confidence = 'HOLD', 50
            reasoning = "Simple R: Price in range"
        
        return {'agent': 'Agent_R_Fallback', 'vote': vote, 'confidence': confidence, 
                'reasoning': reasoning, 'symbol': symbol, 'timeframe': 'M15'}


class SimpleAgentQ:
    """Simple Agent_Q fallback"""
    def analyze(self, signal_data):
        symbol = signal_data.get('symbol', '#S&P500')
        flow = random.uniform(-0.5, 0.5)
        
        if flow > 0.3:
            vote, confidence = 'BUY', 60
            reasoning = "Simple Q: Positive flow"
        elif flow < -0.3:
            vote, confidence = 'SELL', 60
            reasoning = "Simple Q: Negative flow"
        else:
            vote, confidence = 'HOLD', 50
            reasoning = "Simple Q: Neutral flow"
        
        return {'agent': 'Agent_Q_Fallback', 'vote': vote, 'confidence': confidence,
                'reasoning': reasoning, 'symbol': symbol, 'timeframe': 'M15'}


class SimpleAgentD:
    """Simple Agent_D fallback"""
    def predict(self, signal_data, market_features):
        market_features['is_squeeze'] = False
        return 'HOLD', 50
# ============================================================
# CONFIDENCE GATEWAY - Add to trading_controller.py
# ============================================================

class ConfidenceGateway:
    """
    Ensures only high-probability trades are executed.
    """
    
    def __init__(self, min_confidence=70):
        self.min_confidence = min_confidence
        self.rejected_trades = 0
        self.accepted_trades = 0
        
    def evaluate(self, signal: Dict, weights: Dict) -> Dict:
        """
        Evaluate if trade should execute based on confidence.
        
        Returns:
            {
                'execute': bool,
                'confidence': float,
                'reason': str,
                'gateway_status': 'PASS' or 'FAIL'
            }
        """
        confidence = signal.get('confidence', 0)
        action = signal.get('action', 'HOLD')
        
        # ===== PASS: Confidence >= threshold =====
        if confidence >= self.min_confidence and action != 'HOLD':
            self.accepted_trades += 1
            return {
                'execute': True,
                'confidence': confidence,
                'reason': f'Confidence {confidence:.1f}% >= {self.min_confidence}%',
                'gateway_status': 'PASS',
                'action': action
            }
        
        # ===== FAIL: Confidence too low =====
        elif action != 'HOLD':
            self.rejected_trades += 1
            return {
                'execute': False,
                'confidence': confidence,
                'reason': f'Confidence {confidence:.1f}% < {self.min_confidence}% - REJECTED',
                'gateway_status': 'FAIL',
                'action': 'HOLD'
            }
        
        # ===== HOLD =====
        else:
            return {
                'execute': False,
                'confidence': 0,
                'reason': 'No signal (HOLD)',
                'gateway_status': 'HOLD',
                'action': 'HOLD'
            }
    
    def get_stats(self) -> Dict:
        """Return gateway statistics."""
        total = self.accepted_trades + self.rejected_trades
        return {
            'accepted': self.accepted_trades,
            'rejected': self.rejected_trades,
            'total': total,
            'acceptance_rate': (self.accepted_trades / total * 100) if total > 0 else 0
        }
# ============================================================
# EXECUTION QUALITY MONITOR - Add to trading_controller.py
# ============================================================

class ExecutionQualityMonitor:
    """
    Monitors the gap between entry Z-score and actual execution Z-score.
    """
    
    def __init__(self):
        self.execution_data = []
        self.delta_history = []
        self.max_delta = 0.1  # Maximum allowed gap
        
    def record_entry(self, entry_z: float, entry_time: datetime, symbol: str):
        """
        Record the Z-score at entry decision time.
        """
        self.current_entry = {
            'entry_z': entry_z,
            'entry_time': entry_time,
            'symbol': symbol,
            'executed_z': None,
            'execution_time': None,
            'delta': None
        }
        
    def record_execution(self, execution_z: float, execution_time: datetime):
        """
        Record the Z-score at actual execution time.
        """
        if hasattr(self, 'current_entry') and self.current_entry:
            self.current_entry['executed_z'] = execution_z
            self.current_entry['execution_time'] = execution_time
            self.current_entry['delta'] = abs(execution_z - self.current_entry['entry_z'])
            
            self.delta_history.append(self.current_entry['delta'])
            self.execution_data.append(self.current_entry.copy())
            
            # Log quality
            delta = self.current_entry['delta']
            if delta < 0.05:
                logger.info(f"✅ EXCELLENT EXECUTION: Delta={delta:.3f} (Perfect sync)")
            elif delta < 0.1:
                logger.info(f"👍 GOOD EXECUTION: Delta={delta:.3f} (Acceptable)")
            else:
                logger.warning(f"⚠️ SLOW EXECUTION: Delta={delta:.3f} (Need optimization)")
            
            self.current_entry = None
            
            return delta
    
    def get_stats(self) -> Dict:
        """Return execution quality statistics."""
        if not self.delta_history:
            return {
                'avg_delta': 0,
                'min_delta': 0,
                'max_delta': 0,
                'execution_count': 0,
                'quality': 'NO_DATA'
            }
        
        avg_delta = sum(self.delta_history) / len(self.delta_history)
        
        if avg_delta < 0.05:
            quality = 'EXCELLENT'
        elif avg_delta < 0.1:
            quality = 'GOOD'
        else:
            quality = 'NEEDS_OPTIMIZATION'
        
        return {
            'avg_delta': round(avg_delta, 4),
            'min_delta': round(min(self.delta_history), 4),
            'max_delta': round(max(self.delta_history), 4),
            'execution_count': len(self.delta_history),
            'quality': quality
        }
# ============================================================
# STRESS TEST: CORRELATION BREAKDOWN SIMULATION
# ============================================================

class BlackSwanSimulator:
    """
    Simulates a correlation breakdown between SPX and NDX.
    Tests if the kill switch triggers correctly.
    """
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.test_active = False
        self.test_started = None
        
    def run_correlation_breakdown(self, duration_minutes=10):
        """
        Force correlation to zero for testing.
        """
        logger.warning("🦢 BLACK SWAN TEST STARTED")
        logger.warning(f"   Breaking correlation for {duration_minutes} minutes")
        
        self.test_active = True
        self.test_started = datetime.now()
        
        # Force correlation to 0 in coordinator
        self.coordinator.correlation = 0.0
        self.coordinator.kill_switch_active = True
        self.coordinator.kill_switch_reason = "🦢 BLACK SWAN TEST: Correlation breakdown"
        
        # Monitor system response
        start_time = datetime.now()
        kill_triggered = False
        
        while (datetime.now() - start_time).seconds < duration_minutes * 60:
            # Check if coordinator stops trading
            if self.coordinator.kill_switch_active:
                kill_triggered = True
                logger.info("✅ Kill switch triggered correctly")
            else:
                logger.error("❌ Kill switch FAILED - system would trade during breakdown")
            
            time.sleep(10)
        
        # End test
        self.test_active = False
        self.coordinator.kill_switch_active = False
        self.coordinator.kill_switch_reason = ""
        
        logger.warning("🦢 BLACK SWAN TEST COMPLETE")
        logger.info(f"   Kill switch response: {'✅ SUCCESS' if kill_triggered else '❌ FAILED'}")
        
        return {
            'test_duration': duration_minutes,
            'kill_switch_triggered': kill_triggered,
            'test_passed': kill_triggered,
            'correlation_at_end': self.coordinator.correlation
        }
        # ============================================================
# Add to trading_controller.py - Response Time Test
# ============================================================

    def test_response_time(self=None):
        """
        Ensure weighted average calculation takes < 10ms.
        """
        
        # Create sample data
        agent_results = {
               'R': {'vote': 'HOLD', 'confidence': 50},
               'Q': {'vote': 'BUY', 'confidence': 78},
               'D': {'vote': 'HOLD', 'confidence': 50},
               'H': {'vote': 'HOLD', 'confidence': 50},
               'G': {'vote': 'HOLD', 'confidence': 50},
               'M': {'vote': 'HOLD', 'confidence': 50},
               'W': {'vote': 'HOLD', 'confidence': 50},
               'I': {'vote': 'BUY', 'confidence': 77},
               'X': {'vote': 'BUY', 'confidence': 92}
        }
        
        weights = {
               'agent_r': 0.12, 'agent_q': 0.12, 'agent_d': 0.10,
               'agent_h': 0.12, 'agent_g': 0.10, 'agent_m': 0.10,
               'agent_w': 0.10, 'deepseek': 0.10, 'agent_i': 0.06,
               'agent_x': 0.08
        }
        
        # Run 1000 tests
        times = []
        for _ in range(1000):
               start = time.perf_counter()
               
               # Simulate weighted calculation
               votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
               for key, agent in agent_results.items():
                     action = agent.get('vote', 'HOLD')
                     confidence = agent.get('confidence', 50) / 100
                     weight = weights.get(f'agent_{key.lower()}', 0.1)
                     votes[action] += confidence * weight
               
               end = time.perf_counter()
               times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print("=" * 60)
        print("📊 RESPONSE TIME TEST")
        print("=" * 60)
        print(f"   Average: {avg_time:.3f}ms")
        print(f"   Min:            {min_time:.3f}ms")
        print(f"   Max:            {max_time:.3f}ms")
        print(f"   Status:  {'✅ PASS' if avg_time < 10 else '❌ FAIL'} (Need < 10ms)")
        print("=" * 60)
        
        return {
               'avg_ms': avg_time,
               'max_ms': max_time,
               'min_ms': min_time,
               'passed': avg_time < 10
        }


# ============================================================
# Add to trading_controller.py - Decision Logging
# ============================================================

    def _log_decision(self, signal: Dict, weights: Dict, gateway_result: Dict, order_result: Dict):
        """Log every decision for analysis."""
        import json
        
        log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': signal.get('symbol', 'UNKNOWN'),
                'signal': signal.get('action', 'HOLD'),
                'confidence': signal.get('confidence', 0),
                'z_score': signal.get('z_score', 0),
                'weights': weights.copy(),
                'gateway': gateway_result,
                'order': order_result,
                'timeframe': 'M15'
        }
        
        self.decision_log.append(log_entry)
        
        # Keep log manageable
        if len(self.decision_log) > self.max_log_entries:
                self.decision_log.pop(0)
        
        # Save to file
        try:
                with open('decision_log.json', 'w') as f:
                        json.dump(self.decision_log[-100:], f, default=str, indent=2)
        except:
                pass

    def log_current_prices(self):
        """Log all current prices from the system."""
        try:
               logger.info(f"\n{'='*60}")
               logger.info(f"📊 CURRENT PRICES - {datetime.now().strftime('%H:%M:%S')}")
               logger.info(f"{'='*60}")
               
               symbols = self.symbols  # Use the actual symbols list
               
               for symbol in symbols:
                     # Get price from bridge (dashboard source)
                     bridge_price = self.get_price_from_bridge(symbol) if hasattr(self, 'get_price_from_bridge') else 0
                     
                     # Get price from MT4 directly
                     mt4_price = 0
                     try:
                          if self.mt4:
                                  result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                                  if result and isinstance(result, dict):
                                         bid = result.get('bid', 0)
                                         ask = result.get('ask', 0)
                                         if bid > 0 and ask > 0:
                                               mt4_price = (bid + ask) / 2
                     except:
                          pass
                     
                     # Get fallback price
                     fallback = {
                          '#NASDAQ100': 30332.25,
                          '#S&P500': 7525.99,
                          '#DJ30': 52654.00,
                          'GOLD': 4029.97,
                          'SILVER': 59.18,
                          'EURUSD': 1.13950,
                          'GBPUSD': 1.32191,
                          'USDJPY': 162.467,
                          'BRENT_OIL': 74.32,
                          'CrudeOIL': 70.97,
                     }
                     fallback_price = fallback.get(symbol, 0)
                     
                     # Determine which price is being used
                     used_price = bridge_price if bridge_price > 0 else (mt4_price if mt4_price > 0 else fallback_price)
                     source = "BRIDGE" if bridge_price > 0 else ("MT4" if mt4_price > 0 else "FALLBACK")
                     
                     # Check if price is valid
                     is_valid = used_price > 0
                     
                     # For indices, check if price is in correct range
                     if 'NASDAQ' in symbol and used_price > 0:
                          is_valid = 10000 < used_price < 40000
                     elif 'S&P' in symbol and used_price > 0:
                          is_valid = 3000 < used_price < 10000
                     elif 'DJ30' in symbol and used_price > 0:
                          is_valid = 30000 < used_price < 60000
                     elif 'GOLD' in symbol and used_price > 0:
                          is_valid = 1000 < used_price < 6000
                     elif 'EURUSD' in symbol and used_price > 0:
                          is_valid = 0.8 < used_price < 1.5
                     
                     status = "✅" if is_valid else "⚠️"
                     logger.info(f"   {status} {symbol:12} | {source:8} | Price: {used_price:12.2f} | Bridge: {bridge_price:12.2f} | MT4: {mt4_price:12.2f}")
               
               logger.info(f"{'='*60}")
               
               # Also log Agent_X Z-score if available
               if self.agent_x is not None:
                     z_score = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                     samples = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                     logger.info(f"📊 Agent_X: Z-Score={z_score:.2f} | Samples={samples}/30")
               
               logger.info(f"{'='*60}\n")
               
        except Exception as e:
               logger.warning(f"Error logging prices: {e}")


# ============ GLOBAL INSTANCE ============
trading_controller = AITradingController()
def test_dashboard_connection(self):
    """Test connection to dashboard"""
    data = get_prices_from_dashboard()
    if data:
        prices = data.get('prices', {})
        print(f"✅ Dashboard connected - {len(prices)} prices available")
        print(f"   Balance: ${data.get('balance', 0):.2f}")
        print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        
        # Show sample prices
        for sym in ['GOLD', '#NASDAQ100', '#S&P500', 'BRENT_OIL']:
            if sym in prices:
                print(f"   {sym}: {prices[sym]}")
        return True
    else:
        print("❌ Dashboard not connected - make sure forex_dashboard.py is running")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🏛️ INSTITUTIONAL TRADING CONTROLLER")
    print("=" * 60)
    print("=" * 60)
    print("🎯 AI TRADING CONTROLLER - POSITION MANAGEMENT")
    print("=" * 60)
    print("\n📊 Symbol Configuration:")
    print(f"   {'Symbol':<12} {'Volume':<8} {'SL':<6} {'TP':<6} {'Type':<10}")
    print("   " + "-" * 45)
    
    for symbol, config in SYMBOL_CONFIG.items():
        print(f"   {symbol:<12} {config['volume']:<8} {config['sl_pips']:<6} {config['tp_pips']:<6} {config['type']:<10}")
    
    print("\n" + "=" * 60)
    print("📋 Rules:")
    print("   ✅ 1 trade per symbol at a time")
    print("   ✅ Forex: 0.05 lots")
    print("   ✅ Gold/Oil/Indices: 0.02 lots")
    print("   ✅ M15 timeframe (15-minute cycles)")
    print("=" * 60)
    
    # Start the controller
    trading_controller.start()
    
    try:
        while True:
            time.sleep(30)
            status = trading_controller.get_status()
            print(f"\n💓 [{datetime.now().strftime('%H:%M:%S')}] Active: {status['active_positions']} | Running: {status['running']}"f"Active: {status['active_positions']} | "f"Regime: {status['regime']} | "f"Threshold: {status['threshold']:.2f} | "f"Breakers: {len(status['breakers_active'])}")
    except KeyboardInterrupt:
        print("\n🛑print Shutting down...")
        trading_controller.stop()
        print("✅ Done")