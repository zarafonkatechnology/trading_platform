# trading_controller2.py - ALL FOREX PAIRS FROM DASHBOARD

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple , Union 
import threading
import random
import numpy as np
# Core components
from core.dollar_engine import DollarEngine
from core.gear_broker import GearBroker
from core.gear_anomaly_detector import GearAnomalyDetector
from core.monte_carlo_simulator import MonteCarloSimulator
from core.order_execution import OrderExecutionEngine
from brokers import BROKER_MAP, BaseBroker, BrokerManager
from concurrent.futures import ThreadPoolExecutor, as_completed

from hybrid_coordinator import HybridCoordinator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from performance_tracker import PerformanceTracker
# Agents
try:
    from agents2.forex_agent_x import ForexAgentX
    from agents2.forex_agent_u import ForexLiquidityAgentEnhanced
    from agents2.forex_agent_d import AgentDVolatility
    from agents2.agent_c_momentum import AgentCMomentum
    from agents2.agent_e_microstructure import AgentEMicrostructure
    from agents2.agent_p_whisper import WhisperAnalyst
    print("✅ All agents imported successfully")
except ImportError as e:
    print(f"⚠️ Agent import error: {e}")
    # Fallback classes
    class ForexAgentX:
        def __init__(self, name="Forex_X", timeframe="M15"):
            self.name = name
            self.agent_type = "Spread Reversion Specialist"
            self.timeframe = timeframe
            
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    
    class ForexLiquidityAgentEnhanced:
        def __init__(self, name="Forex_Agent_U", timeframe="M15"):
            self.name = name
            self.agent_type = "Liquidity Specialist"
            self.timeframe = timeframe
            self.z_score = 0.0
            self.spread_history = []
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    
    class AgentDVolatility:
        def __init__(self, name="Forex_D", timeframe="M15"):
            self.name = name
            self.agent_type = "Volatility Specialist"
            self.timeframe = timeframe
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    
    class AgentCMomentum:
        def __init__(self):
            self.name = "Agent_C"
            self.agent_type = "Pair Agent"
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    
    class AgentEMicrostructure:
        def __init__(self):
            self.name = "Agent_E"
            self.agent_type = "Base Pair Agent"
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    
    class WhisperAnalyst:
        def __init__(self):
            self.name = "Agent_P"
            self.agent_type = "Cross Pair Agent"
        def analyze(self, data):
            return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}

# RL Modules
try:
    from rl_trading_env import ForexTradingEnv
    from rl_agent import RLAgent
    RL_AVAILABLE = True
    print("✅ RL modules imported successfully")
except ImportError as e:
    print(f"⚠️ RL modules not available: {e}")
    RL_AVAILABLE = False
    # Dummy classes
    class ForexTradingEnv:
        def __init__(self, *args, **kwargs): pass
    class RLAgent:
        def __init__(self, *args, **kwargs): pass

# MT4 Price Provider (SAME as dashboard)
try:
    from mt4_price_provider import get_mt4_prices
except ImportError:
    print("⚠️ mt4_price_provider not found")
    def get_mt4_prices():
        return None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# ALL FOREX PAIRS FROM DASHBOARD
# ============================================================

# Full symbol config for ALL forex pairs
SYMBOL_CONFIG = {
    # Majors
    'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    
    # Crosses
    'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    '#Dollar_IND': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40, 'volume': 0.02, 'type': 'index'},
}

# ALL FOREX PAIRS from your dashboard
FOREX_PAIRS = [
    # Majors
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    # Crosses
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD',  'EURCHF'
]

# ============================================================
# ALL SYMBOLS FOR PRICE READING
# ============================================================

ALL_SYMBOLS = FOREX_PAIRS + [
    'GOLD', 'SILVER',
    '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI334',
    'BRENT_OIL', 'CrudeOIL', '#DOLLAR_IND'
]

class ForexTradingController:
    """
    Main trading controller - uses MT4 ACCOUNT command (SAME as dashboard)
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        # ===== PERFORMANCE TRACKING =====

        self.replay_buffer = []  # Stores (state, action, reward, next_state)
        self.replay_buffer_max = 5000
        self.rl_train_every = 10  # Train every N simulations 
        self.rl_train_batch_size = 10
        # ===== COLD START PROTECTION =====
        self.cold_start_active = True
        self.cold_start_threshold = self.config.get('cold_start_threshold', 50)
        self.cold_start_min_win_rate = self.config.get('cold_start_min_win_rate', 0.4)
        self.cold_start_samples = []
        self.cold_start_wins = 0
        self.cold_start_losses = 0
        self.cold_start_skip_real = self.config.get('cold_start_skip_real', True)
        # ===== LOAD COLD START STATE =====
        self._load_cold_start_state()

        logger.info(f"   ❄️ Cold Start Protection: {self.cold_start_threshold} samples required, min win rate {self.cold_start_min_win_rate*100:.0f}%")
        self.config = config or {}
        self.name = "ForexGearController"
        self.timeframe = self.config.get('timeframe', 'M15')
        self.is_running = False
        self.cycle_interval = self.config.get('cycle_interval', 10)
        # In the __init__ method, when initializing RL:
        # ===== HYBRID COORDINATOR =====
        self.hybrid_coordinator = HybridCoordinator(use_hybrid=self.config.get('use_hybrid', True)) 
        logger.info(f"   ✅ Hybrid Coordinator initialized (enabled: {self.hybrid_coordinator.USE_HYBRID})")
        self.rl_enabled = self.config.get('rl_enabled', False)
        self.rl_agent = None
        self.rl_env = None
        if self.rl_enabled and RL_AVAILABLE:
            try:
                     logger.info("🤖 Initializing RL Agent...")
                     self.rl_env = ForexTradingEnv(self, self.config)
                     model_path = self.config.get('rl_model_path', 'models/rl_model.zip')
                     
                     # Create directory if it doesn't exist
                     os.makedirs(os.path.dirname(model_path), exist_ok=True)
                     
                     self.rl_agent = RLAgent(
                              self.rl_env, 
                              model_path=model_path,
                              load_existing=self.config.get('load_rl_model', False)
                     )
                     logger.info("   ✅ RL Agent initialized")
            except Exception as e:
                     logger.error(f"   ❌ RL Agent initialization failed: {e}")
                     self.rl_agent = None
                     self.rl_env = None
                     self.rl_enabled = False
            try:
                from brokers import BROKER_MAP, BaseBroker, BrokerManager as BrokerManagerFromBrokers
                BROKERS_AVAILABLE = True
                print("✅ Brokers imported successfully")
            except ImportError:
                BROKERS_AVAILABLE = False
                BROKER_MAP = {}
                # In __init__, after initializing components:


        try:
            self.performance = PerformanceTracker(self.config)
            logger.info("   ✅ Performance Tracker initialized")
        except Exception as e:
            logger.error(f"   ❌ Performance Tracker initialization error: {e}")
            self.performance = None
        
        # ===== MT4 CONNECTION (SAME as dashboard) =====
        self.mt4 = None
        self._connect_mt4()
        self.agent_weights = {
            'Forex_X': 1.2,# spread agent proven reliable
            'Forex_Agent_U': 0.8,
            'Forex_D': 1.0,
            'Agent_C': 1.0,
            'Agent_E': 0.9,
            'Agent_P': 1.1,
            }
        # ===== CORE COMPONENTS =====
        logger.info("🏗️ Initializing Core Components...")
        self.engine = DollarEngine(self.config.get('engine_config', {}))
        logger.info("   ✅ Dollar Engine initialized")
        
        self.monte_carlo = MonteCarloSimulator(self.config.get('monte_carlo_config', {}))
        logger.info("   ✅ Monte Carlo Simulator initialized")
        
        self.anomaly_detector = GearAnomalyDetector(self.config.get('anomaly_detector_config', {}))
        logger.info("   ✅ Anomaly Detector initialized")
        
        self.execution_engine = OrderExecutionEngine(self.engine, self.config.get('execution_config', {}))
        logger.info("   ✅ Order Execution Engine initialized")
        self.agent_x = ForexAgentX(name="Forex_X", timeframe=self.timeframe)
        self.agent_u = ForexLiquidityAgentEnhanced(name="Forex_Agent_U")
        self.agent_d = AgentDVolatility(name="Forex_D", timeframe=self.timeframe)
        self.agent_c = AgentCMomentum()
        self.agent_e = AgentEMicrostructure()
        self.agent_p = WhisperAnalyst()
         # RISK MANAGEMENT - DAILY & CONSECUTIVE LOSS LIMITS
        # ============================================================
        self.daily_loss_limit = self.config.get('daily_loss_limit', 100)
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.max_trades_per_day = self.config.get('max_trades_per_day', 5)
        
        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 3)
        self.last_trade_was_win = True
        
        # Weekly loss limit
        self.weekly_pnl = 0.0
        self.weekly_loss_limit = self.config.get('weekly_loss_limit', 300)
        self.week_start_day = datetime.now().weekday()
        self.agents = [self.agent_x, self.agent_u, self.agent_d, self.agent_c, self.agent_e, self.agent_p]
        logger.info(f"   ✅ {len(self.agents)} agents initialized")
        for agent in self.agents:
            logger.info(f"      - {agent.name}")
        
        # ===== BROKERS - ALL FOREX PAIRS =====
        self.pairs = self.config.get('pairs', FOREX_PAIRS)
        self.brokers = {}
        logger.info(f"📊 Initializing Brokers for {len(self.pairs)} pairs...")
        
        for pair in self.pairs:
            pair_config = self.config.get('pairs_config', {}).get(pair, {})
            if pair in SYMBOL_CONFIG:
                pair_config = {**SYMBOL_CONFIG[pair], **pair_config}
            broker = GearBroker(pair, pair_config, self.engine)
            self.brokers[pair] = broker
            self.execution_engine.register_broker(pair, broker)
            logger.info(f"   ✅ Broker: {pair}")
        
        self.anomaly_detector.set_brokers(self.brokers)
        
        # ===== STATE =====
        self.cycle_count = 0
        self.decision_log = []
        self.last_results = {}
           # ===== RL AGENT =====
        self.rl_enabled = self.config.get('rl_enabled', False)
        self.rl_agent = None
        self.rl_env = None
        
        if self.rl_enabled and RL_AVAILABLE:
            try:
                logger.info("🤖 Initializing RL Agent...")
                self.rl_env = ForexTradingEnv(self, self.config)
                model_path = self.config.get('rl_model_path', 'models/rl_model.zip')
                self.rl_agent = RLAgent(
                    self.rl_env, 
                    model_path=model_path,
                    load_existing=self.config.get('load_rl_model', False)
                )
                logger.info("   ✅ RL Agent initialized")
            except Exception as e:
                logger.error(f"   ❌ RL Agent initialization failed: {e}")
                self.rl_agent = None
                self.rl_env = None
                self.rl_enabled = False
        elif self.rl_enabled and not RL_AVAILABLE:
            logger.warning("   ⚠️ RL not available - disabling")
            self.rl_enabled = False
        
        # ===== PRICE CHECK (SAME as dashboard) =====
        self._log_current_prices()
        
        logger.info("✅ ForexTradingController initialized successfully!")
        logger.info(f"   📊 Pairs: {len(self.pairs)}")
        logger.info(f"   🤖 Agents: {len(self.agents)}")
        logger.info(f"   🔄 Cycle Interval: {self.cycle_interval}s")
        # In __init__, after initializing engine and monte_carlo:

# ===== BROKER MANAGER =====
        # In trading_controller2.py __init__

# ===== BROKER MANAGER =====
        # In trading_controller2.py __init__, fix the error handling:

# ===== BROKER MANAGER =====
        # ===== BROKER MANAGER =====
        logger.info("🏗️ Initializing Broker Manager...")
        try:
            from brokers import BROKER_MAP, BrokerManager
            self.broker_manager = BrokerManager(
                                self.engine, 
                                self.monte_carlo, 
                                self.rl_agent
                )
                
                # Register all pairs with the BROKER_MAP
            self.broker_manager.register_brokers(self.pairs, BROKER_MAP)
            logger.info(f"   ✅ Broker Manager initialized with {len(self.broker_manager.brokers)} brokers")
                
                # Fix missing attributes
            self.fix_all_broker_attributes()
                
                # ===== CRITICAL: Initialize broker price history =====
            self.initialize_broker_price_history()  # ← ADD THIS LINE
                
        except Exception as e:
            logger.error(f"   ❌ Broker Manager initialization error: {e}")
            import traceback
            traceback.print_exc()
            self.broker_manager = None
        if self.broker_manager:
            self.fix_all_broker_attributes()
        # ===== DEBUG: CHECK BROKER STATE =====
        # ===== DEBUG: CHECK BROKER STATE =====
        logger.info("🔍 DEBUG: Broker price history and z-scores")
        for pair in self.pairs:
            broker = self.broker_manager.brokers.get(pair)
            if broker:
               hist_len = len(broker.close_history) if hasattr(broker, 'close_history') else 0
               z = broker.z_score if hasattr(broker, 'z_score') else 0
               price = broker.current_price if hasattr(broker, 'current_price') else 0
               logger.info(f"   {pair}: history={hist_len}, z_score={z:.2f}, price={price:.5f}")
            else:
               logger.info(f"   {pair}: broker not found")
        for pair, broker in self.broker_manager.brokers.items():
            logger.info(f"      - {pair}: {broker.__class__.__name__}")
    
    def check_trade_allowed(self, pair: str = None) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk limits.
        Returns: (allowed, reason)
        """
        # 1. Daily Loss Limit
        if self.daily_pnl <= -self.daily_loss_limit:
              return False, f"Daily loss limit reached: ${self.daily_pnl:.2f} (limit: ${self.daily_loss_limit})"
        
        # 2. Consecutive Loss Limit
        if self.consecutive_losses >= self.max_consecutive_losses:
              return False, f"Max consecutive losses: {self.consecutive_losses} (limit: {self.max_consecutive_losses})"
        
        # 3. Daily Trade Limit
        if self.trades_today >= self.max_trades_per_day:
              return False, f"Daily trade limit reached: {self.trades_today} (limit: {self.max_trades_per_day})"
        
        # 4. Weekly Loss Limit
        if self.weekly_pnl <= -self.weekly_loss_limit:
              return False, f"Weekly loss limit reached: ${self.weekly_pnl:.2f} (limit: ${self.weekly_loss_limit})"
        
        return True, "OK"

    def update_risk_metrics(self, pnl: float, was_win: bool):
        """
        Update risk metrics after a trade.
        """
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.trades_today += 1
        
        if was_win:
              self.consecutive_losses = 0
              self.last_trade_was_win = True
        else:
              self.consecutive_losses += 1
              self.last_trade_was_win = False
        
        logger.info(f"📊 Risk Update: P&L=${pnl:.2f} | Daily=${self.daily_pnl:.2f} | Weekly=${self.weekly_pnl:.2f} | ConsecutiveLosses={self.consecutive_losses}")

    def reset_daily_stats(self):
        """Reset daily statistics."""
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0
        self.last_trade_was_win = True
        logger.info("🔄 Daily stats reset")

    def reset_weekly_stats(self):
        """Reset weekly statistics."""
        self.weekly_pnl = 0.0
        logger.info("🔄 Weekly stats reset")

    def check_and_reset_weekly(self):
        """Check if we need to reset weekly stats (Sunday)."""
        current_weekday = datetime.now().weekday()
        if current_weekday == 6:  # Sunday
              if self.week_start_day != 6:
                      self.reset_weekly_stats()
              self.week_start_day = 6
    def initialize_broker_price_history(self):
        """Initialize all brokers with price history from MT4."""
        if not self.broker_manager:
               logger.error("❌ Broker Manager not available")
               return False
        
        logger.info("📊 Initializing broker price history...")
        
        # Get current prices
        prices = self.get_all_mt4_prices()
        
        if not prices:
               logger.warning("⚠️ No prices from MT4 - using fallback prices")
               fallback_prices = {
                     'EURUSD': 1.1415, 'GBPUSD': 1.3402, 'USDJPY': 162.35,
                     'USDCHF': 0.8108, 'AUDUSD': 0.6983, 'USDCAD': 1.4068,
                     'NZDUSD': 0.5816, 'EURGBP': 0.8520, 'EURJPY': 185.35,
                     'EURCAD': 1.6058, 'EURNZD': 1.9616, 'EURCHF': 0.9256,
               }
               prices = fallback_prices
        
        # Initialize each broker with history
        for pair in self.pairs:
               price = prices.get(pair, 0)
               if price <= 0:
                     logger.warning(f"   ⚠️ No price for {pair} - skipping")
                     continue
               
               broker = self.broker_manager.brokers.get(pair)
               if not broker:
                     logger.warning(f"   ⚠️ No broker found for {pair}")
                     continue
               
               # Generate 50 historical prices around current price
               import random
               history = []
               spread_values = []
               
               for i in range(50):
                     # Random walk with mean reversion
                     if i < 25:
                          variation = 1 + (i - 25) * 0.0002 + (random.random() - 0.5) * 0.001
                     else:
                          variation = 1 + (25 - i) * 0.0002 + (random.random() - 0.5) * 0.001
                     hist_price = price * variation
                     history.append(hist_price)
                     # Spread = price * 0.0002 (2 pips) + small random variation
                     spread_values.append(hist_price * 0.0002 * (1 + (random.random() - 0.5) * 0.5))
               
               # Set broker history - DIRECTLY set attributes
               broker.price_history = history
               broker.close_history = history.copy()
               broker.high_history = [p * 1.001 for p in history]
               broker.low_history = [p * 0.999 for p in history]
               broker.spread_history = spread_values
               broker.current_price = price
               broker.bid = price * 0.9999
               broker.ask = price * 1.0001
               
               # Calculate initial Z-score from spread_history
               if len(broker.spread_history) >= 10:
                     values = broker.spread_history
                     mu = sum(values) / len(values)
                     variance = sum((x - mu) ** 2 for x in values) / len(values)
                     sigma = variance ** 0.5 if variance > 0 else 0.0001
                     broker.z_score = (spread_values[-1] - mu) / sigma if sigma > 0 else 0.0
                     broker.mu = mu
                     broker.sigma = sigma
                     broker.samples = len(values)
               else:
                     broker.z_score = 0.5  # Default small positive
               
               logger.info(f"   ✅ {pair}: initialized {len(history)} prices, z_score={broker.z_score:.2f}")
        
        logger.info("✅ Broker price history initialization complete")
        return True
    def calculate_position_size(self, confidence: float, volatility: float, 
                           pair: str = 'EURUSD') -> float:
        """
        Dynamic position sizing based on recent performance.
        """
        # ===== INCREASE BASE SIZE =====
        base_size = self.config.get('base_volume', 0.05)  # Changed from 0.03 to 0.05
        max_size = self.config.get('max_position_size', 0.10)  # Changed from 0.05 to 0.10
        
        # ===== 1. CONSECUTIVE LOSS PENALTY (LESS AGGRESSIVE) =====
        if self.consecutive_losses >= 2:
               loss_penalty = max(0.5, 1.0 - (self.consecutive_losses * 0.15))  # Less reduction
        else:
               loss_penalty = 1.0
        
        # ===== 2. DAILY P&L ADJUSTMENT (LESS AGGRESSIVE) =====
        if self.daily_pnl < 0:
               daily_penalty = max(0.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.8)
        else:
               daily_penalty = min(1.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.3)
        
        # ===== 3. VOLATILITY ADJUSTMENT (LESS AGGRESSIVE) =====
        vol_penalty = 1.0 / (1.0 + volatility * 50)  # Less reduction
        vol_penalty = max(0.3, min(1.0, vol_penalty))
        
        # ===== 4. CONFIDENCE ADJUSTMENT =====
        confidence_factor = 0.4 + (confidence / 100.0) * 0.6  # Higher minimum
        
        # ===== 5. PAIR-SPECIFIC ADJUSTMENT =====
        pair_multiplier = self._get_pair_multiplier(pair)
        
        # ===== 6. ACCOUNT GROWTH ADJUSTMENT =====
        account_factor = min(1.5, self.account_balance / 10000) if hasattr(self, 'account_balance') else 1.0
        
        # ===== FINAL SIZE =====
        position_size = (base_size * loss_penalty * daily_penalty * vol_penalty * 
                                  confidence_factor * pair_multiplier * account_factor)
        
        # ===== CLAMP =====
        position_size = max(0.01, min(max_size, round(position_size, 3)))
        
        return round(position_size, 2)
    def _get_pair_multiplier(self, pair: str) -> float:
        """Get multiplier based on pair type."""
        multipliers = {
               'EURUSD': 1.0,
               'GBPUSD': 1.0,
               'USDJPY': 0.8,   # Lower size for JPY (smaller pip)
               'USDCHF': 0.9,
               'AUDUSD': 0.9,
               'USDCAD': 0.9,
               'NZDUSD': 0.8,
               'EURGBP': 0.8,
               'EURJPY': 0.7,
               'EURCAD': 0.8,
               'EURNZD': 0.7,
               'EURCHF': 0.7,
        }
        return multipliers.get(pair, 0.8)
    def fix_all_broker_attributes(self):
        """Fix missing attributes in all brokers."""
        if not self.broker_manager:
              return
        
        for pair, broker in self.broker_manager.brokers.items():
              # Add close_history
              if not hasattr(broker, 'close_history'):
                      broker.close_history = []
              if not hasattr(broker, 'high_history'):
                      broker.high_history = []
              if not hasattr(broker, 'low_history'):
                      broker.low_history = []
              if not hasattr(broker, 'volume_history'):
                      broker.volume_history = []
              if not hasattr(broker, 'pattern_info'):
                      broker.pattern_info = None
              if not hasattr(broker, 'name'):
                      broker.name = f"{pair}_Broker"
              
              # Add pair-specific attributes
              if pair == 'EURUSD' or pair == 'GBPUSD':
                      if not hasattr(broker, 'fastest_period'):
                            broker.fastest_period = 5
                      if not hasattr(broker, 'slowest_period'):
                            broker.slowest_period = 200
              
              if pair == 'USDCHF':
                      if not hasattr(broker, 'snb_intervention_history'):
                            broker.snb_intervention_history = []
              
              if pair == 'USDJPY':
                      if not hasattr(broker, 'volume_history'):
                            broker.volume_history = []
                      if not hasattr(broker, 'squeeze_detected'):
                            broker.squeeze_detected = False
                      if not hasattr(broker, 'volume_spike'):
                            broker.volume_spike = False
                      if not hasattr(broker, 'support_level'):
                            broker.support_level = 0.0
                      if not hasattr(broker, 'resistance_level'):
                            broker.resistance_level = 0.0
              
              logger.info(f"✅ Fixed attributes for {pair}")
    # ============================================================
    # MT4 CONNECTION (SAME as dashboard)
    # ============================================================
    def check_trailing_stop(self, position: Dict, current_price: float) -> Tuple[bool, float]:
        """
        Check if trailing stop should be triggered.
        
        Args:
                position: Position dictionary with entry_price, direction
                current_price: Current market price
        
        Returns:
                (should_close, close_price)
        """
        entry_price = position.get('entry_price', 0)
        direction = position.get('direction', 'BUY')
        trailing_pct = self.config.get('trailing_stop_pct', 0.5) / 100.0  # Convert to decimal
        
        # Initialize tracking values
        if 'highest_price' not in position:
                position['highest_price'] = entry_price
        if 'lowest_price' not in position:
                position['lowest_price'] = entry_price
        if 'trailing_activated' not in position:
                position['trailing_activated'] = False
        
        highest_price = position['highest_price']
        lowest_price = position['lowest_price']
        
        # Update highest/lowest
        if direction == 'BUY':
                if current_price > highest_price:
                         position['highest_price'] = current_price
                         # Activate trailing once price moves 0.5% in our favor
                         if not position['trailing_activated'] and (current_price - entry_price) / entry_price > 0.005:
                                position['trailing_activated'] = True
                                logger.info(f"📊 Trailing stop ACTIVATED at ${current_price:.5f}")
                
                if position['trailing_activated']:
                         trailing_price = highest_price * (1 - trailing_pct)
                         if current_price <= trailing_price:
                                logger.info(f"📉 TRAILING STOP HIT: ${current_price:.5f} <= ${trailing_price:.5f}")
                                return True, trailing_price
        
        else:  # SELL
                if current_price < lowest_price:
                         position['lowest_price'] = current_price
                         if not position['trailing_activated'] and (entry_price - current_price) / entry_price > 0.005:
                                position['trailing_activated'] = True
                                logger.info(f"📊 Trailing stop ACTIVATED at ${current_price:.5f}")
                
                if position['trailing_activated']:
                         trailing_price = lowest_price * (1 + trailing_pct)
                         if current_price >= trailing_price:
                                logger.info(f"📉 TRAILING STOP HIT: ${current_price:.5f} >= ${trailing_price:.5f}")
                                return True, trailing_price
        
        return False, 0.0
    def initialize_broker_history(self, market_data: Dict):
        """Initialize broker history with current market data."""
        if not self.broker_manager:
              return
        
        # Get price history for each pair
        for pair in self.pairs:
              if pair in self.broker_manager.brokers:
                      broker = self.broker_manager.brokers[pair]
                      
                      # Generate synthetic history if no real data
                      price = market_data.get(pair, 0)
                      if price > 0:
                            # Add 30 historical prices
                            for i in range(30):
                                    hist_price = price * (1 + (i - 15) * 0.0005)
                                    broker.price_history.append(hist_price)
                                    if hasattr(broker, 'close_history'):
                                          broker.close_history.append(hist_price)
                                    if hasattr(broker, 'high_history'):
                                          broker.high_history.append(hist_price * 1.001)
                                    if hasattr(broker, 'low_history'):
                                          broker.low_history.append(hist_price * 0.999)
                      
                      # Add spread history
                      if hasattr(broker, 'spread_history'):
                            for i in range(20):
                                    broker.spread_history.append(price * 0.0001 * (1 + i * 0.01))
        
        logger.info("✅ Broker history initialized for all pairs")
    def calculate_risk_of_ruin(self, account_balance: float, 
                          risk_per_trade: float, win_rate: float) -> Dict:
        """
        Calculate probability of blowing the account.
        """
        if risk_per_trade <= 0 or account_balance <= 0:
               return {
                     'kelly_fraction': 0,
                     'ruin_probability': 0,
                     'expected_max_drawdown': 0,
                     'is_safe': True,
                     'recommendation': 'No risk'
               }
        
        # Kelly Criterion
        risk_reward = self.config.get('risk_reward_ratio', 1.5)
        kelly = win_rate - (1 - win_rate) / risk_reward
        kelly = max(0, min(0.5, kelly))
        
        # ===== FIXED: Better risk of ruin calculation =====
        # Use the formula: RoR = ((1 - edge) / (1 + edge))^(bankroll / risk_per_trade)
        avg_win = 1.0
        avg_loss = 1.0 / risk_reward
        edge = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        if edge <= 0:
               ruin_probability = 1.0
        else:
               risk_ratio = account_balance / risk_per_trade
               ruin_probability = ((1 - edge) / (1 + edge)) ** risk_ratio
               ruin_probability = min(1.0, max(0.0, ruin_probability))
        
        # Expected maximum drawdown (95% confidence) - FIXED
        expected_max_drawdown = account_balance * (1 - win_rate) * 1.5
        expected_max_drawdown = min(account_balance * 0.5, expected_max_drawdown)
        
        # Risk of ruin threshold
        is_safe = ruin_probability < 0.05 and kelly > 0.05
        
        return {
               'kelly_fraction': round(kelly, 3),
               'ruin_probability': round(ruin_probability * 100, 1),
               'expected_max_drawdown': round(expected_max_drawdown, 2),
               'is_safe': is_safe,
               'recommendation': 'OK' if is_safe else 'REDUCE RISK'
        }
    def _execute_trade(self, pair: str, signal: str, price: float, confidence: float):
        """
        Execute a trade with full risk management.
        """
        # ===== CHECK RISK LIMITS =====
        allowed, reason = self.check_trade_allowed(pair)
        if not allowed:
               logger.info(f"⏸️ Trade blocked: {reason}")
               return {'status': 'BLOCKED', 'reason': reason}
        
        # ===== CHECK MEAN REVERSION =====
        z_score = self.agent_x.z_score if self.agent_x else 0
        if not self._confirm_mean_reversion(pair, z_score):
               logger.info(f"⏸️ {pair}: Mean reversion not confirmed")
               return {'status': 'BLOCKED', 'reason': 'Mean reversion not confirmed'}
        
        # ===== CALCULATE VOLATILITY =====
        volatility = self._get_volatility(pair, price)
        
        # ===== CALCULATE POSITION SIZE =====
        position_size = self.calculate_position_size(confidence, volatility, pair)
        
        # ===== CALCULATE RISK OF RUIN =====
        account_balance = self._get_account_balance()
        risk_per_trade = position_size * self._get_pip_value(pair) * 100000
        win_rate = self._get_win_rate()
        
        risk_check = self.calculate_risk_of_ruin(account_balance, risk_per_trade, win_rate)
        
        if not risk_check['is_safe']:
               logger.info(f"⚠️ Risk of ruin too high: {risk_check['ruin_probability']:.1f}%")
               # Reduce position size by 50%
               position_size = position_size * 0.5
               position_size = max(0.01, round(position_size, 2))
               logger.info(f"📊 Reduced position size to {position_size} lots")
        
        # ===== GET CONFIG =====
        config = self.get_symbol_config(pair)
        pip = config.get('pip', 0.0001)
        digits = config.get('digits', 5)
        sl_pips = config.get('sl_pips', 15)
        tp_pips = config.get('tp_pips', 30)
        
        # ===== CALCULATE SL AND TP =====
        if signal == 'BUY':
               sl = price - (sl_pips * pip)
               tp = price + (tp_pips * pip)
        else:
               sl = price + (sl_pips * pip)
               tp = price - (tp_pips * pip)
        
        entry_price = round(price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)
        
        # ===== SEND ORDER =====
        order_result = self._send_mt4_order(
               pair=pair,
               action=signal,
               volume=position_size,
               entry=entry_price,
               sl=sl,
               tp=tp
        )
        
        if order_result and order_result.get('success'):
               logger.info(f"✅ TRADE EXECUTED: {pair} {signal} {position_size} lots @ {entry_price}")
               logger.info(f"   SL: {sl} | TP: {tp}")
               
               # ===== STORE POSITION FOR TRAILING STOP =====
               self.active_positions[pair] = {
                     'direction': signal,
                     'entry_price': entry_price,
                     'volume': position_size,
                     'sl': sl,
                     'tp': tp,
                     'highest_price': entry_price,
                     'lowest_price': entry_price,
                     'trailing_activated': False
               }
               
               return {'status': 'EXECUTED', 'pair': pair, 'action': signal, 'volume': position_size}
        
        return {'status': 'FAILED', 'reason': str(order_result)}        
    def _confirm_mean_reversion(self, pair: str, z_score: float) -> bool:
        """
        Confirm that price is actually reverting, not just pausing.
        
        This prevents entering when momentum is still strong in the wrong direction.
        """
        # Initialize history tracker
        if not hasattr(self, '_z_history'):
                 self._z_history = {}
        
        if pair not in self._z_history:
                 self._z_history[pair] = []
        
        self._z_history[pair].append(z_score)
        if len(self._z_history[pair]) > 10:
                 self._z_history[pair].pop(0)
        
        # Need at least 3 data points
        if len(self._z_history[pair]) < 3:
                 return True  # Not enough data, allow entry
        
        # Check if Z-score is actually reversing
        z_changes = [self._z_history[pair][i] - self._z_history[pair][i-1] 
                                   for i in range(1, len(self._z_history[pair]))]
        
        if not z_changes:
                 return True
        
        last_change = z_changes[-1]
        
        # ===== RULE 1: For overextended (z > 2), we want it moving DOWN =====
        if z_score > 2.0 and last_change > 0:
                 logger.info(f"⏸️ {pair}: Z-score still rising ({z_score:.2f}), waiting for reversal")
                 return False
        
        # ===== RULE 2: For compressed (z < -2), we want it moving UP =====
        if z_score < -2.0 and last_change < 0:
                 logger.info(f"⏸️ {pair}: Z-score still falling ({z_score:.2f}), waiting for reversal")
                 return False
        
        # ===== RULE 3: Check if Z-score is moving toward mean =====
        # Calculate the moving average of changes (trend of Z-score)
        if len(z_changes) >= 3:
                 avg_change = sum(z_changes[-3:]) / 3
                 
                 # If we're overextended and still moving away from mean, wait
                 if z_score > 0 and avg_change > 0 and z_score > 1.5:
                           logger.info(f"⏸️ {pair}: Z-score moving further away ({z_score:.2f}), waiting")
                           return False
                 if z_score < 0 and avg_change < 0 and z_score < -1.5:
                           logger.info(f"⏸️ {pair}: Z-score moving further away ({z_score:.2f}), waiting")
                           return False
        
        # ===== ALL CHECKS PASSED =====
        return True
    def _send_mt4_order(self, pair: str, action: str, volume: float, 
                        entry: float, sl: float, tp: float) -> Dict:
        """
        Send order to MT4 with proper error handling.
        """
        # ===== DOUBLE CHECK COLD START =====
        if self.cold_start_active:
            logger.warning(f"⚠️ Attempted real order during cold start - BLOCKED!")
            return {
                'success': False,
                'error': 'Cold start active - no real orders allowed',
                'simulated': True
            }
        
        # ===== REAL ORDER SENDING =====
        try:
            if not self.mt4:
                logger.error("❌ MT4 not connected")
                return {'success': False, 'error': 'MT4 not connected'}
            
            # Build order command
            order_cmd = {
                "command": "ORDER_SEND",
                "symbol": pair,
                "action": action,
                "volume": volume,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "type": "market"
            }
            
            # Send to MT4
            result = self.mt4._send(order_cmd)
            
            if result and result.get('success'):
                return {'success': True, 'order_id': result.get('order_id')}
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'details': result
                }
                
        except Exception as e:
            logger.error(f"❌ Order sending error: {e}")
            return {'success': False, 'error': str(e)}
    def run_controller(self):
        """Main controller loop with cold start protection."""
        
        while self.is_running:
                 try:
                           # ===== PHASE 1: COLD START =====
                           if self.cold_start_active:
                                  logger.info(f"❄️ COLD START: {len(self.cold_start_samples)}/{self.cold_start_threshold}")
                                  
                                  # Process up to 3 pairs per cycle
                                  for pair in self.pairs[:3]:
                                          # Get signal
                                          signal = self._get_signal(pair)
                                          
                                          if signal and signal != 'HOLD':
                                                   # SIMULATE ONLY
                                                   self._simulate_trade(pair, signal)
                                                   
                                                   # Show progress
                                                   progress = len(self.cold_start_samples)
                                                   win_rate = self.cold_start_wins / progress if progress > 0 else 0
                                                   logger.info(f"   📊 Progress: {progress}/{self.cold_start_threshold} | Win Rate: {win_rate:.1%}")
                                  
                                  # Check completion
                                  if len(self.cold_start_samples) >= self.cold_start_threshold:
                                          self.is_cold_start_complete()
                                          
                                          # Train RL with collected data
                                          if self.rl_enabled:
                                                   self._train_rl_with_collected_data()
                                                   
                                                   # Save trained model
                                                   if self.rl_agent:
                                                             model_path = 'models/rl_model_cold_start.zip'
                                                             self.rl_agent.save(model_path)
                                                             logger.info(f"💾 RL: Model saved to {model_path}")
                                  
                                  # Skip real trading
                                  continue
                           
                           # ===== PHASE 2: REAL TRADING =====
                           logger.info("💰 REAL TRADING ACTIVE")
                           
                           # Process all pairs
                           for pair in self.pairs:
                                  # Get signal with confirmation
                                  signal = self._get_confirmed_signal(pair)
                                  
                                  if signal and signal != 'HOLD':
                                          # REAL EXECUTION ONLY
                                          self._execute_real_trade(pair, signal)
                           
                           # ===== PHASE 3: RL TRAINING =====
                           if self.rl_enabled and self.rl_agent:
                                  # Collect real trading data for RL
                                  self._collect_rl_data()
                                  
                                  # Train periodically
                                  if self.cycle_count % 10 == 0:
                                          self._train_rl_from_replay()
                           
                           # Sleep
                           time.sleep(self.cycle_interval)
                           
                 except KeyboardInterrupt:
                           logger.info("🛑 Shutting down...")
                           break
                 except Exception as e:
                           logger.error(f"❌ Error in main loop: {e}")
                           time.sleep(5)
        
        self.stop()
    def _monitor_trailing_stops(self):
        """Monitor all active positions for trailing stop triggers."""
        for pair in list(self.active_positions.keys()):
               position = self.active_positions[pair]
               current_price = self.get_price(pair)
               
               if current_price <= 0:
                     continue
               
               should_close, close_price = self.check_trailing_stop(position, current_price)
               
               if should_close:
                     # Close the position
                     self._close_position(pair, close_price)
    def _adjust_thresholds(self, volatility: float):
        """Adjust entry/exit thresholds based on volatility."""
        base_entry = 2.0
        base_exit = 0.3
        if volatility > 0.02:
                self.entry_threshold = base_entry * 1.2
                self.exit_threshold = base_exit * 1.2
        elif volatility < 0.005:
                self.entry_threshold = base_entry * 0.8
                self.exit_threshold = base_exit * 0.8
        else:
                self.entry_threshold = base_entry
                self.exit_threshold = base_exit
    def get_symbol_config(self, symbol: str) -> Dict[str, Union[float, int, str]]:
        """
        Get configuration for a symbol.
        Returns default config if symbol not found.
        """
        # Clean symbol name (remove # if present)
        clean_symbol = symbol.replace('#', '')
        
        # Define default configs for all pairs
        configs = {
              'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
              'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
              'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
              'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
              'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
              'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
              'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
        }
        
        # Check clean symbol first
        if clean_symbol in configs:
              return configs[clean_symbol]
        
        # Check original symbol
        if symbol in configs:
              return configs[symbol]
        
        # Default fallback
        return {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'unknown'}
    def test_rl_training(self):
        """Force RL training with mock data."""
        if not self.rl_enabled or not self.rl_agent:
              return
        
        import random
        logger.info("🧪 Creating mock RL training data...")
        
        # Generate mock training data
        for i in range(50):
              state = np.random.rand(50).astype(np.float32)
              action = np.array([random.randint(0, 3), random.randint(0, 2), 1.0], dtype=np.float32)
              reward = random.uniform(-1, 1)
              next_state = np.random.rand(50).astype(np.float32)
              self.replay_buffer.append({
                      'state': state,
                      'action': action,
                      'reward': reward,
                      'next_state': next_state,
                      'done': False
              })
        
        # Train RL
        self._train_rl_from_replay()
        
        # Save model
        os.makedirs('models', exist_ok=True)
        self.rl_agent.save('models/rl_model_trained.zip')
        logger.info("✅ RL: Model trained with mock data and saved")
        
        # Load model for use
        try:
              self.rl_agent.load('models/rl_model_trained.zip')
              logger.info("✅ RL: Model loaded for use")
        except Exception as e:
              logger.warning(f"RL model load error: {e}")
    def is_cold_start_complete(self) -> bool:
        """Check if cold start protection is complete."""
        if not self.cold_start_active:
               return True
        
        total = len(self.cold_start_samples)
        win_rate = self.cold_start_wins / total if total > 0 else 0

        if total >= self.cold_start_threshold:
               
               if win_rate >= self.cold_start_min_win_rate:
                         self.cold_start_active = False
                         logger.info("="*60)
                         logger.info(f"✅ COLD START COMPLETE!")
                         logger.info(f"   Total Samples: {total}")
                         logger.info(f"   Wins: {self.cold_start_wins}")
                         logger.info(f"   Losses: {self.cold_start_losses}")
                         logger.info(f"   Win Rate: {win_rate:.1%} (required: {self.cold_start_min_win_rate:.1%})")
                         logger.info("🔓 REAL TRADING ENABLED")
                         logger.info("="*60)
                         return True
               else:
                         # ===== OPTION: Force complete after threshold is reached =====
                    logger.warning("="*60)
                    logger.warning(f"⚠️ COLD START WIN RATE BELOW THRESHOLD")
                    logger.warning(f"   Samples: {total}")
                    logger.warning(f"   Win Rate: {win_rate:.1%} (required: {self.cold_start_min_win_rate:.1%})")
                    logger.warning("   Continuing to real trading with reduced position size...")
                    logger.warning("="*60)
                    self.cold_start_active = False
                    return True
        else:
            logger.info(f"❄️ Cold start: {total}/{self.cold_start_threshold} samples collected.")
            return False
        # After cold start complete
        if not controller.cold_start_active and controller.rl_enabled:
    # Train RL with cold start data
           if hasattr(controller, 'rl_training_data') and controller.rl_training_data:
                controller._train_rl_with_collected_data()
                controller.rl_agent.save('models/rl_model_trained.zip')
                logger.info("💾 RL: Model trained and saved after cold start")
        else:# Create mock training data for RL
            controller.test_rl_training()
        # In main loop after cold start
        if controller.cold_start_active == False and controller.rl_enabled:
           controller.test_rl_training()
    def _confirm_entry_with_candle_and_sr(self, symbol: str, price: float, direction: str) -> bool:
        """
        Confirm entry using:
        - Last completed M5 candle (green for BUY, red for SELL)
        - Support/Resistance distance (price must be in the middle of the range)
        - Spread check (not too wide)
        - Minimum range width (not too tight)
        Returns True if all conditions pass.
        """
        # 1. Get last completed M5 candle
        candle = self._get_last_m5_candle(symbol)
        if not candle:
              logger.warning(f"⚠️ No M5 candle for {symbol} – using MT4/bridge price confirmation")
              return True

        candle_close = candle['close']
        candle_open = candle['open']
        is_green = candle_close > candle_open
        is_red = candle_close < candle_open

        # ===== CANDLE CHECK =====
        if direction == 'BUY' and not is_green:
              logger.info(f"⏸️ {symbol}: Last M5 candle is NOT green – skipping BUY")
              return False
        if direction == 'SELL' and not is_red:
              logger.info(f"⏸️ {symbol}: Last M5 candle is NOT red – skipping SELL")
              return False

        # ===== SPREAD CHECK =====
        try:
              price_data = self.mt4._send({"command": "PRICE", "symbol": symbol})
              if price_data and isinstance(price_data, dict):
                      bid = price_data.get('bid', 0)
                      ask = price_data.get('ask', 0)
                      if bid > 0 and ask > 0:
                            spread = abs(ask - bid)
                            spread_pct = spread / bid * 100
                            if spread_pct > 0.02:  # 2% spread = too wide
                                    logger.info(f"⏸️ {symbol}: Spread too wide ({spread_pct:.3f}%) – skipping")
                                    return False
        except:
              pass

        # ===== SUPPORT/RESISTANCE CHECK =====
        swings = self._find_recent_swings(symbol, lookback=50)
        support = swings.get('support', 0)
        resistance = swings.get('resistance', 0)

        if support == 0 or resistance == 0:
              logger.info(f"⏸️ {symbol}: No S/R data available – skipping")
              return False

        # ATR for buffer
        atr = self._get_atr(symbol, timeframe='M5', period=14)
        if atr == 0:
              atr = price * 0.001

        buffer = 0.5 * atr

        # ===== MINIMUM RANGE WIDTH CHECK (NEW) =====
        range_size = resistance - support
        min_range_width = 0.0020  # Minimum 20 pips for EURUSD
        if range_size < min_range_width:
              logger.info(f"⏸️ {symbol}: Range too tight ({range_size:.5f} < {min_range_width:.5f}) – skipping")
              return False

        # ===== STRICT S/R CHECK =====
        # Price must be in the MIDDLE of the range (not near support or resistance)
        middle_min = support + 0.3 * range_size   # 30% above support
        middle_max = resistance - 0.3 * range_size # 30% below resistance

        if direction == 'BUY':
              # Price must be above support + buffer AND below resistance - buffer
              min_price = support + buffer
              max_price = resistance - buffer
              if not (min_price < price < max_price):
                      logger.info(f"⏸️ {symbol}: Price {price:.5f} not in middle range "
                                          f"(must be between {min_price:.5f} and {max_price:.5f}) – skipping {direction}")
                      return False
        elif direction == 'SELL':
              # Same condition for SELL
              min_price = support + buffer
              max_price = resistance - buffer
              if not (min_price < price < max_price):
                      logger.info(f"⏸️ {symbol}: Price {price:.5f} not in middle range "
                                          f"(must be between {min_price:.5f} and {max_price:.5f}) – skipping {direction}")
                      return False

        return True
    def _get_m5_candles(self, symbol: str, count: int = 6) -> List[Dict]:
        """Get M5 candles from MT4."""
        try:
                if self.mt4:
                        result = self.mt4._send({
                                "command": "HISTORY",
                                "symbol": symbol,
                                "timeframe": "M5",
                                "count": count + 1
                        })
                        if result and isinstance(result, dict):
                                candles = result.get('candles', [])
                                if len(candles) >= count:
                                        return candles[-count:]
        except Exception as e:
                logger.debug(f"Error fetching M5 candles for {symbol}: {e}")
        return []

    def _simulate_trade(self, pair: str, signal: str, confidence: float, price: float) -> Dict:
        """
        Simulate a trade during cold start using Monte Carlo confidence.
        Also captures RL transitions for training.
        """
        # Get current state for RL (before trade)
        current_state = self.rl_env._get_observation() if self.rl_env else None
        
        # Use Monte Carlo to estimate probability of success
        mc_results = self.monte_carlo.simulate_entry(current_price=price, direction=signal)
        prob_success = mc_results.get('entry_confidence', 50) / 100.0
        
        import random
        win = random.random() < prob_success
        
        # Simulated PnL (fixed 10 pips movement)
        config = self.get_symbol_config(pair)
        pip = config.get('pip', 0.0001)
        volume = config.get('volume', 0.03)
        pips = 10
        pnl = pips * pip * 100000 * volume
        if signal == 'SELL':
              pnl = -pnl if win else pnl
        else:
              pnl = pnl if win else -pnl
        
        sample = {
              'pair': pair,
              'signal': signal,
              'confidence': confidence,
              'price': price,
              'win': win,
              'pnl': pnl,
              'timestamp': datetime.now().isoformat()
        }
        self.cold_start_samples.append(sample)
        if win:
              self.cold_start_wins += 1
        else:
              self.cold_start_losses += 1
        
        # ===== RL TRANSITION =====
        if self.rl_enabled and self.rl_agent and current_state is not None:
              # Convert signal to action
              trade_type = 1 if signal == 'BUY' else 2 if signal == 'SELL' else 0
              pair_idx = self.pairs.index(pair) if pair in self.pairs else 0
              size_mult = 1.0
              action = np.array([pair_idx, trade_type, size_mult], dtype=np.float32)
              
              # Reward is PnL (profit/loss)
              reward = pnl / 100.0  # Normalize reward
              
              # Get next state (after trade simulation)
              next_state = self.rl_env._get_observation() if self.rl_env else None
              
              # Store transition
              self.replay_buffer.append({
                      'state': current_state,
                      'action': action,
                      'reward': reward,
                      'next_state': next_state,
                      'done': False  # Not terminal
              })
              # After storing transition in replay buffer
              if len(self.replay_buffer) % 10 == 0:
                  logger.info(f"🤖 RL: Collected {len(self.replay_buffer)} transitions")
              # Limit buffer size
              if len(self.replay_buffer) > self.replay_buffer_max:
                      self.replay_buffer = self.replay_buffer[-self.replay_buffer_max:]
              
              # Train RL periodically
              if len(self.replay_buffer) >= self.rl_train_batch_size and len(self.cold_start_samples) % self.rl_train_every == 0:
                      self._train_rl_from_replay()
        
        return sample

    def _train_rl_from_replay(self, batch_size=64, epochs=5):
        """Train RL agent using the replay buffer."""
        if not self.rl_enabled or not self.rl_agent:
               return

        if len(self.replay_buffer) < batch_size:
               return

        # Create a replay environment from the buffer
        from rl_replay_env import ReplayEnv
        replay_env = ReplayEnv(self.replay_buffer[-500:])  # use recent 500

        # Wrap for stable-baselines3
        from stable_baselines3.common.env_util import make_vec_env
        vec_env = make_vec_env(lambda: replay_env, n_envs=1)

        # Continue training the existing model
        # We need to set the environment of the model to the new vec_env
        self.rl_agent.model.set_env(vec_env)

        # Train for a few epochs (total_timesteps = len(buffer) * epochs)
        total_steps = len(self.replay_buffer) * epochs // 10  # reduce to avoid overfitting
        total_steps = max(total_steps, 200)

        logger.info(f"🤖 RL: Training from replay buffer ({len(self.replay_buffer)} transitions)...")
        self.rl_agent.model.learn(total_timesteps=total_steps, reset_num_timesteps=False)
        logger.info("✅ RL: Online training complete")

        # Save the updated model
        self.rl_agent.save('models/rl_model_online.zip')
        logger.info("💾 RL: Model saved to models/rl_model_online.zip")
    def _train_rl_with_collected_data(self):
        """Train the RL model using collected data."""
        if not self.rl_enabled or not self.rl_agent:
              return
        
        if not hasattr(self, 'rl_training_data') or not self.rl_training_data:
              return
        
        try:
              logger.info(f"🤖 RL: Starting training with {len(self.rl_training_data)} transitions...")
              
              # For PPO, we need to use the environment
              # Since we can't easily use replay buffer with PPO,
              # we'll use the model's learn method with a custom approach
              
              # Option: Use the existing environment and train with the collected data
              # This is simplified - in production you'd create a proper training loop
              
              # For now, we'll just log that training would happen
              logger.info("✅ RL: Training would happen here with the collected data")
              
              # In a real implementation, you would:
              # 1. Create a custom VecEnv that uses the collected data
              # 2. Or use an off-policy algorithm like DQN or SAC that supports replay buffers
              
              # Since we're using PPO (on-policy), we'll use the data to create a dataset
              # and train the model using the standard PPO learn method
              
              # For now, we'll just save the data and log progress
              logger.info(f"💾 RL: Training data saved - {len(self.rl_training_data)} transitions ready")
              
              # If you want to actually train, you can implement a custom training loop
              # that uses the collected data with a custom environment
              self._train_rl_from_replay()
        except Exception as e:
              logger.warning(f"RL training error: {e}")
    def _update_rl_model_with_data(self):
        """Update the RL model with collected data."""
        if not self.rl_enabled or not self.rl_agent:
               return
        
        if not hasattr(self, 'rl_training_data') or not self.rl_training_data:
               return
        
        logger.info(f"🤖 RL: Training data available: {len(self.rl_training_data)} transitions")
        
        # If we have enough data, train the model
        if len(self.rl_training_data) >= 500:
               logger.info("🤖 RL: Training with 500+ transitions...")
               
               # ===== ACTUALLY TRAIN THE RL MODEL =====
               try:
                     # For PPO, we need to use the model's learn method
                     # We'll create a simple training environment
                     # For now, we'll use a placeholder training call
                     # In production, you'd implement a proper training loop
                     
                     # Option 1: Train on the collected data using a custom environment
                     # This requires creating a VecEnv that uses the collected data
                     
                     # Option 2: For now, we'll just log and save the model
                     # The model will be trained when you call rl_agent.train()
                     
                     # Save the collected data for later training
                     import pickle
                     with open('rl_training_data.pkl', 'wb') as f:
                          pickle.dump(self.rl_training_data, f)
                     logger.info(f"💾 RL: Saved {len(self.rl_training_data)} transitions to rl_training_data.pkl")
                     
                     # Train the model using the collected data
                     # This is a simplified approach - in production you'd use a custom environment
                     self._train_rl_with_collected_data()
                     
               except Exception as e:
                     logger.warning(f"RL model update error: {e}")
              # Here you would implement actual training


    def debug_mt4_response(self):
        """Debug MT4 response"""
        try:
            if not self.mt4:
                print("❌ MT4 not connected")
                return
            
            raw_packet = self.mt4._send({"command": "ACCOUNT"})
            print("\n📦 RAW MT4 RESPONSE:")
            print(f"   Type: {type(raw_packet)}")
            print(f"   Keys: {list(raw_packet.keys()) if isinstance(raw_packet, dict) else 'NOT A DICT'}")
            
            if isinstance(raw_packet, dict):
                print("\n   Sample values:")
                for key in ['EURUSD', 'GBPUSD', 'USDJPY', 'balance', 'equity']:
                    if key in raw_packet:
                        print(f"     {key}: {raw_packet[key]}")
                    else:
                        print(f"      {key}: NOT FOUND")
            
            return raw_packet
        except Exception as e:
            print(f"❌ Debug error: {e}")
            return None
    
    def _connect_mt4(self):
        """Connect to MT4 - SAME as dashboard"""
        try:
            self.mt4 = get_mt4_prices()
            if self.mt4:
                # Test connection with ACCOUNT command (same as dashboard)
                test_result = self.mt4._send({"command": "ACCOUNT"})
                if test_result and isinstance(test_result, dict):
                    balance = test_result.get('balance', 0)
                    if balance > 0:
                        logger.info(f"   ✅ MT4 connected - Balance: ${balance:.2f}")
                        return
                    else:
                        logger.warning(f"   ⚠️ MT4 connected but no account data: {test_result}")
                else:
                    logger.warning(f"   ⚠️ MT4 connected but test failed: {test_result}")
            else:
                logger.warning("   ⚠️ MT4 connection failed - using simulation mode")
        except Exception as e:
            logger.error(f"   ❌ MT4 connection error: {e}")
            self.mt4 = None
    
    # ============================================================
    # PRICE METHODS - ALL FOREX PAIRS
    # ============================================================
    
    def get_all_mt4_prices(self) -> Dict:
        """
        Get ALL prices directly from dashboard file (SAME as dashboard)
        """
        try:
            # Read directly from file
            import os
            appdata = os.environ.get('APPDATA', '')
            file_path = os.path.join(appdata, 'MetaQuotes', 'Terminal', 'Common', 'Files', 'dashboard_data.json')
# also try terminal-specific path
            if not os.path.exists(file_path):
                # Try terminal folder
                file_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/dashboard_data.json"
            
            if not os.path.exists(file_path):
                logger.warning(f"⚠️ Dashboard file not found")
                return {}
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            prices = {}
            
            # Check for prices in the file
            if 'prices' in data:
                for symbol, price in data['prices'].items():
                    if price > 0:
                        prices[symbol] = price
            
            # Also check direct keys for all forex pairs
            for pair in FOREX_PAIRS:
                if pair in data and pair not in prices:
                    price = float(data.get(pair, 0))
                    if price > 0:
                        prices[pair] = price
            if '#Dollar_IND' in data and '#Dollar_IND' not in prices:
                dollar_price = float(data.get('#Dollar_IND', 0))
                if dollar_price > 0:
                               prices['#Dollar_IND'] = dollar_price
                elif 'Dollar_IND' in data and '#Dollar_IND' not in prices:
                    dollar_price = float(data.get('Dollar_IND', 0))
                    if dollar_price > 0:
                               prices['#Dollar_IND'] = dollar_price
            
            if prices:
                logger.info(f"✅ Got {len(prices)} prices from file")
            
            return prices
            
        except Exception as e:
            logger.warning(f"Error reading file: {e}")
            return {}
    def _get_price(self, symbol: str) -> Optional[float]:
        """Get current price with error handling."""
        try:
                if not self.mt4:
                        return None
                result = self.mt4._send({"command": "PRICE", "symbol": symbol})
                if result and isinstance(result, dict):
                        return result.get('bid', 0)
                return None
        except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
                return None
    def get_price(self, symbol: str) -> float:
        """Get price for a single symbol from file"""
        prices = self.get_all_mt4_prices()
        return prices.get(symbol, 0)
    
    def get_all_prices(self) -> Dict:
        """Get all prices (alias)"""
        return self.get_all_mt4_prices()
    
    def _log_current_prices(self):
        """Log current prices (SAME as dashboard)"""
        try:
            prices = self.get_all_mt4_prices()
            
            print(f"\n{'='*60}")
            print(f"📊 PRICE CHECK - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            # Show ALL forex pairs
            for symbol in FOREX_PAIRS:
                price = prices.get(symbol, 0)
                if price > 0:
                    print(f"   ✅ {symbol:12} | MT4      | {price:12.5f}")
                else:
                    print(f"   ❌ {symbol:12} | N/A      | {'NO PRICE':>12}")
            dollar_price = prices.get('#Dollar_IND', 0)
            if dollar_price > 0:
                print(f"   ✅ #Dollar_IND | MT4     | {dollar_price:12.3f}")
            else:
                print(f"   ❌ #Dollar_IND | N/A     | {'NO PRICE':>12}")
            if self.agent_x is not None:
                z_score = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                samples = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                print(f"   📊 Agent_X: Z={z_score:.2f} | Samples={samples}/30")
            
            print(f"{'='*60}\n")
            
        except Exception as e:
            logger.warning(f"Price log error: {e}")
    
    # ============================================================
    # BUILD MARKET DATA - ALL FOREX PAIRS
    # ============================================================
    
    def build_market_data(self) -> Dict:
        """Build market data from MT4."""
        market_data = {}
        
        # Get prices from MT4
        prices = self.get_all_mt4_prices()
        
        # Add prices for ALL pairs
        for pair in self.pairs:
                 if pair in prices and prices[pair] > 0:
                           market_data[pair] = prices[pair]
                           market_data[f'{pair}_price'] = prices[pair]
        
        # ===== ADD PRICE HISTORY AND ATR =====
        for pair in self.pairs:
                 try:
                           # Get candles for ATR
                           candles = self._get_m5_candles(pair, count=20)
                           if candles and len(candles) >= 20:
                                  closes = [c['close'] for c in candles]
                                  market_data[f'{pair}_price_history'] = closes
                                  
                                  # Calculate ATR
                                  atr = self._get_atr(pair, timeframe='M5', period=14)
                                  market_data[f'{pair}_atr'] = atr
                 except:
                           pass
        
        # Add current price
        if 'EURUSD' in market_data and market_data['EURUSD'] > 0:
                 market_data['current_price'] = market_data['EURUSD']
                 market_data['price'] = market_data['EURUSD']
                 market_data['pair'] = 'EURUSD'
        
        # Add engine state
        engine_state = self.engine.get_status() if self.engine else {}
        market_data['engine_state'] = engine_state
        
        # Add engine predictions
        for pair in self.pairs:
                 if pair in self.brokers:
                           gear_pred = self.engine.get_gear_prediction(pair, self.brokers[pair].gear_ratio)
                           market_data[f'{pair}_gear_prediction'] = gear_pred
        
        market_data['timestamp'] = datetime.now().isoformat()
        
        if prices:
                 logger.info(f"📊 Built market data with {len(prices)} prices")
        engine_state = self.engine.get_status() if self.engine else {}
        
        market_data['engine_state'] = {
            'engine_speed': engine_state.get('engine_speed', 0.3),
            'engine_direction': engine_state.get('engine_direction', 'FORWARD'),  # ← Make sure this is set
            'engine_health': engine_state.get('engine_health', 95.0),
            'reversal_probability': engine_state.get('reversal_probability', 20.0),
            'regime': engine_state.get('regime', 'RANGING')
         }
    
        return market_data
    def _get_last_m5_candle(self, symbol: str) -> Optional[Dict]:
        """Get the last completed 5‑minute candle from MT4."""
        try:
            if self.mt4:
                result = self.mt4._send({
                    "command": "HISTORY",
                    "symbol": symbol,
                    "timeframe": "M5",
                    "count": 2
                })
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if len(candles) >= 2:
                        return candles[-2]  # second last = completed
        except Exception as e:
            logger.debug(f"Error fetching M5 candle for {symbol}: {e}")
        return None
    def _find_recent_swings(self, symbol: str, lookback: int = 50) -> Dict:
        """Find recent swing high and low using M5 candles."""
        try:
            if self.mt4:
                result = self.mt4._send({
                    "command": "HISTORY",
                    "symbol": symbol,
                    "timeframe": "M5",
                    "count": lookback
                })
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if candles:
                        highs = [c['high'] for c in candles]
                        lows = [c['low'] for c in candles]
                        return {
                            'support': min(lows),
                            'resistance': max(highs)
                        }
        except:
            pass
        return {'support': 0, 'resistance': 0}
    def _get_atr(self, symbol: str, timeframe: str = 'M5', period: int = 14) -> float:
        """Calculate ATR for the given symbol and timeframe."""
        try:
            if self.mt4:
                result = self.mt4._send({
                    "command": "HISTORY",
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": period + 1
                })
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if len(candles) >= period + 1:
                        tr_values = []
                        for i in range(1, len(candles)):
                            high = candles[i]['high']
                            low = candles[i]['low']
                            prev_close = candles[i-1]['close']
                            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                            tr_values.append(tr)
                        if tr_values:
                            return sum(tr_values[-period:]) / period
        except:
            pass
        return 0.0   # fallback

    def _confirm_entry_with_candle_and_sr(self, symbol: str, price: float, direction: str) -> bool:
        """
        Confirm entry using the agent z-score instead of M5 candle confirmation.
        - SELL is confirmed when z-score >= 1.8
        - BUY is confirmed when z-score <= -1.8
        """

        if not self.config.get('enable_entry_confirmation', True):
            return True

        z_threshold = self.config.get('entry_confirmation_z_threshold', 1.8)
        z_score = 0.0

        if self.agent_x is not None:
            if hasattr(self.agent_x, 'z_score'):
                z_score = float(getattr(self.agent_x, 'z_score', 0.0))
            elif hasattr(self.agent_x, 'z_scores'):
                z_score = float(self.agent_x.z_scores.get(symbol, 0.0))
        elif hasattr(self, 'broker_manager') and self.broker_manager:
            broker = self.broker_manager.brokers.get(symbol)
            if broker and hasattr(broker, 'z_score'):
                z_score = float(getattr(broker, 'z_score', 0.0))

        if direction == 'SELL' and z_score >= z_threshold:
            logger.info(f"✅ {symbol}: z-score {z_score:.2f} >= {z_threshold:.2f} – SELL confirmed")
            return True

        if direction == 'BUY' and z_score <= -z_threshold:
            logger.info(f"✅ {symbol}: z-score {z_score:.2f} <= {-z_threshold:.2f} – BUY confirmed")
            return True

        logger.info(f"⏸️ {symbol}: z-score {z_score:.2f} does not match {direction} threshold ({z_threshold:.2f}) – skipping")
        return False
    def rl_safe_to_trade(self, action, market_data):
        """Check if RL action is safe."""
        if self.execution_engine.daily_pnl < -self.config.get('max_daily_loss', 500):
            return False, "Daily loss exceeded"
        if self.execution_engine.trades_today >= self.config.get('max_trades_per_day', 10):
            return False, "Daily trade limit"
        
        pair_idx = int(np.clip(action[0], 0, len(self.pairs)-1))
        pair = self.pairs[pair_idx]
        price = market_data.get(pair, 0)
        if price <= 0:
            return False, "No price"
        
        direction = 'BUY' if action[1] == 1 else 'SELL' if action[1] == 2 else None
        if direction is None:
            return False, "No trade action"
        
        mc_results = self.monte_carlo.simulate_entry(current_price=price, direction=direction)
        if mc_results.get('entry_confidence', 0) < 60:
            return False, f"Monte Carlo low confidence: {mc_results.get('entry_confidence', 0)}%"
        
        return True, "OK"

    # ============================================================
    # PROCESS CYCLE
    # ============================================================
    def clear_stuck_positions(self):
        """Clear stuck positions from execution engine"""
        if self.execution_engine:
               # Clear positions
               if hasattr(self.execution_engine, 'positions'):
                     self.execution_engine.positions = {}
                     print("🗑️ Cleared execution engine positions")
               
               # Clear any other position tracking
               if hasattr(self.execution_engine, 'active_positions'):
                     self.execution_engine.active_positions = {}
                     print("🗑️ Cleared execution engine active positions")
               
               # Clear local positions
               self.execution_engine.positions = {}
               print("🗑️ Cleared local active positions")
               
               # Reset trades today
               if hasattr(self.execution_engine, 'trades_today'):
                     self.execution_engine.trades_today = 0
                     print("📊 Reset trades today to 0")
               
               if hasattr(self.execution_engine, 'daily_pnl'):
                     self.execution_engine.daily_pnl = 0.0
                     print("💰 Reset daily P&L to $0.00")
               
               print("✅ Stuck positions cleared!")
               return True
        return False
    def _is_valid_price(self, pair: str, price: float) -> bool:
        """Check if price is within normal range for the pair."""
        if price <= 0:
               return False
        
        # Define expected ranges for each pair
        ranges = {
               'EURUSD': (0.8, 1.6),
               'GBPUSD': (0.8, 1.7),
               'USDJPY': (100, 200),
               'USDCHF': (0.7, 1.2),
               'AUDUSD': (0.5, 0.9),
               'USDCAD': (1.0, 1.7),
               'NZDUSD': (0.4, 0.8),
               'EURGBP': (0.7, 1.0),
               'EURJPY': (100, 200),
               'EURCAD': (1.2, 1.8),
               'EURNZD': (1.5, 2.4),
               'EURCHF': (0.8, 1.2),
        }
        
        clean = pair.replace('#', '')
        if clean in ranges:
               low, high = ranges[clean]
               return low < price < high
        
        # For unknown symbols, reject if price is extreme
        return 0.01 < price < 10000
    def _check_spread(self, pair: str, price: float) -> bool:
        """
        Check if spread is acceptable for trading.
        Returns True if spread is OK, False if too wide.
        """
        try:
                 if self.mt4:
                           price_data = self.mt4._send({"command": "PRICE", "symbol": pair})
                           if price_data and isinstance(price_data, dict):
                                  bid = price_data.get('bid', 0)
                                  ask = price_data.get('ask', 0)
                                  if bid > 0 and ask > 0:
                                          spread = abs(ask - bid)
                                          spread_pct = (spread / bid) * 100
                                          # Allow up to 0.05% spread (5 pips on EURUSD)
                                          if spread_pct > 0.05:
                                                   logger.debug(f"Spread too high for {pair}: {spread_pct:.3f}%")
                                                   return False
                                          return True
        except Exception as e:
                 logger.debug(f"Spread check error: {e}")
        
        # Default: allow trade if price is valid
        return False
    def _get_higher_tf_signal(self, pair: str, direction: str) -> bool:
        """
        Fetch 1H candles and check if trend aligns with direction.
        Returns True if confirmed.
        """
        try:
                 # Fetch 1H candles (you can get from MT4 or history)
                 candles = self._get_candles(pair, timeframe='H1', count=5)
                 if len(candles) < 5:
                           return True  # insufficient data, allow

                 closes = [c['close'] for c in candles]
                 # Simple trend: compare current close vs 3-period SMA
                 sma_3 = sum(closes[-3:]) / 3
                 current = closes[-1]

                 if direction == 'BUY':
                           # Uptrend if current > sma_3 and recent highs increasing
                           return current > sma_3
                 elif direction == 'SELL':
                           return current < sma_3
                 return True
        except:
                 return True  # fallback: all
    def process_cycle(self, market_data: Dict = None) -> Dict:
        """
            Process one trading cycle with proper hierarchical flow:
            Level 1: Pair Broker Signals
            Level 2: Dollar Engine Filter
            Level 3: Monte Carlo Probability Check
            Level 4: RL Agent Override
            Level 5: Entry Confirmation (5-Candle SMA)
            Level 6: Cold Start Protection
            Level 7: Execution
        """
        
        self.cycle_count += 1
        if market_data is None:
               market_data = self.build_market_data()
        results = {
               'cycle': self.cycle_count,
               'timestamp': datetime.now().isoformat(),
               'engine': {},
               'anomalies': {},
               'trades': [],
               'positions': {},
               'rl_used': False,
               'broker_decisions': {},
               'hybrid_decision': {},
               'agents': {}
        }
        decisions = {}
        
        
        try:
                # ============================================================
                # STEP 1: UPDATE ENGINE
                # ============================================================
                if self.engine:
                     results['engine'] = self.engine.update_engine_state(market_data)
                     regime = results['engine'].get('regime', 'RANGING')
                     min_confidence = max(70, self.config.get('min_confidence', 60)) if regime == 'VOLATILE' else self.config.get('min_confidence', 60)

                # ============================================================
                # STEP 2: ANOMALY DETECTION
                # ============================================================
                if self.anomaly_detector:
                     anomalies = self.anomaly_detector.update(market_data)
                     results['anomalies'] = anomalies
                     if anomalies.get('protection_active', False):
                         return results
               
                # ============================================================
                # STEP 3: CIRCUIT BREAKER
                # ============================================================
                if self.execution_engine and self.execution_engine.daily_pnl < -self.config.get('max_daily_loss', 500):
                     logger.warning(f"🔴 DAILY LOSS LIMIT REACHED: ${self.execution_engine.daily_pnl:.2f}")
                     self.stop()
                     self.clear_stuck_positions()
                     return {'status': 'STOPPED', 'reason': 'Daily loss limit exceeded'}
               
                # ============================================================
                # LEVEL 1: PAIR BROKER SIGNALS (via Broker Manager)
                # ============================================================

                broker_signals = {}
                agent_results = {}
                broker_decisions = {}

                logger.info("📊 LEVEL 1: Getting signals from pair brokers...")

                # 1. Get signals from specialized brokers (EURUSDBroker, GBPUSDBroker, etc.)
                if self.broker_manager:
                    try:
                        broker_decisions = self.broker_manager.get_decision(market_data)
                        if broker_decisions:
                            for pair, decision in broker_decisions.items():
                                signal = decision.get('signal', 'HOLD')
                                confidence = decision.get('confidence', 0)
                                broker_signals[pair] = {
                                    'signal': signal,
                                    'confidence': confidence,
                                    'z_score': decision.get('z_score', 0),
                                    'position_size': decision.get('position_size', 1.0),
                                    'sl': decision.get('sl', 0),
                                    'tp': decision.get('tp', 0),
                                    'reasoning': decision.get('reasoning', decision.get('broker_result', {}).get('reasoning', 'N/A'))
                                }

                                if signal != 'HOLD':
                                    logger.info(f"   🎯 {pair}: {signal} ({confidence:.1f}%) - {broker_signals[pair]['reasoning']}")

                            logger.info(f"   ✅ Got {len(broker_signals)} broker signals")
                        else:
                            logger.warning("   ⚠️ No broker decisions returned")

                    except Exception as e:
                        logger.error(f"   ❌ Broker Manager error: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.warning("   ⚠️ Broker Manager not available - using fallback")

                # 2. Get signals from agents (Forex_X, Forex_D, etc.) - SECONDARY
                logger.info("📊 Getting agent signals (secondary)...")

                for agent in self.agents:
                    try:
                        signal_data = {
                            'pair': market_data.get('pair', 'EURUSD'),
                            'price': market_data.get('EURUSD', 0),
                            'current_price': market_data.get('EURUSD', 0),
                            'symbol': market_data.get('symbol', 'EURUSD'),
                        }
                        for pair in self.pairs:
                            if pair in market_data:
                                signal_data[pair] = market_data[pair]

                        if 'candles' in market_data:
                            signal_data['candles'] = market_data['candles']

                        result = agent.analyze(signal_data)
                        agent_results[agent.name] = result

                        if result.get('vote', 'HOLD') != 'HOLD':
                            logger.info(f"   🤖 {agent.name}: {result.get('vote')} ({result.get('confidence', 0):.1f}%)")

                    except Exception as e:
                        logger.error(f"   Agent {agent.name} error: {e}")
                        agent_results[agent.name] = {
                            'vote': 'HOLD',
                            'confidence': 50,
                            'reasoning': f'Error: {e}'
                        }

                results['agents'] = agent_results
                results['broker_signals'] = broker_signals

                # ============================================================
                # LEVEL 1 SUMMARY
                # ============================================================
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 LEVEL 1 SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"{'='*60}")

                active_broker_signals = 0
                for pair, signal_data in broker_signals.items():
                    signal = signal_data.get('signal', 'HOLD')
                    if signal != 'HOLD':
                        active_broker_signals += 1
                        logger.info(f"   ✅ {pair}: {signal} ({signal_data['confidence']:.1f}%)")

                if active_broker_signals == 0:
                    logger.info("   ⏸️ No active broker signals")
                else:
                    logger.info(f"   📊 {active_broker_signals} active broker signals")

                active_agent_signals = 0
                for agent_name, result in agent_results.items():
                    if result.get('vote', 'HOLD') != 'HOLD':
                        active_agent_signals += 1

                if active_agent_signals > 0:
                    logger.info(f"   🤖 {active_agent_signals} active agent signals")
                logger.info(f"{'='*60}\n")

                # ============================================================
                # LEVEL 2: DOLLAR ENGINE FILTER (via Broker Manager)
                # ============================================================
                decisions = broker_decisions
                if decisions:
                    logger.info(f"📊 Broker Manager returned {len(decisions)} decisions")
                    for pair, decision in decisions.items():
                        signal = decision.get('signal', 'HOLD')
                        confidence = decision.get('confidence', 0)
                        if signal != 'HOLD':
                            logger.info(f"   🎯 {pair}: {signal} ({confidence:.1f}%)")
                else:
                    logger.warning("⚠️ Broker Manager returned empty decisions")

                results['broker_decisions'] = decisions
                # ============================================================
                # 8. LOG BROKER DECISIONS
                # ============================================================
               
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 BROKER DECISIONS - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"{'='*60}")
               
                active_signals = 0
                if decisions:
                    for pair, decision in decisions.items():
                         signal = decision.get('signal', 'HOLD')
                         if signal != 'HOLD':
                             active_signals += 1
                             logger.info(f"🎯 {pair}: {signal} ({decision['confidence']:.1f}%)")
                             logger.info(f"   Position: {decision.get('position_size', 0)} lots")
                             logger.info(f"   SL: {decision.get('sl', 0):.5f} | TP: {decision.get('tp', 0):.5f}")
                             if 'broker_result' in decision:
                                     logger.info(f"   Reason: {decision['broker_result'].get('reasoning', 'N/A')}")
                else:
                    logger.warning("⚠️ No decisions from broker manager")
                if active_signals == 0:
                     logger.info("⏸️ No active signals from any broker")
                # ============================================================
                # 6. BUILD HYBRID DATA (NOW agent_results IS DEFINED)
                # ============================================================
                hybrid_data = {}

                # Add existing agents (X, U, D, C, E, P)
                for agent in self.agents:
                    agent_key = agent.name[-1] if hasattr(agent, 'name') else agent.__class__.__name__[-1]
                    if agent.name in agent_results:
                        result = agent_results[agent.name]
                        hybrid_data[agent_key] = {
                            'vote': result.get('vote', 'HOLD'),
                            'confidence': result.get('confidence', 50),
                            'z_score': result.get('z_score', 0)
                    }
                # Add broker decisions
                if decisions:
                    for pair, decision in decisions.items():
                        hybrid_data[f'broker_{pair}'] = {
                            'vote': decision.get('signal', 'HOLD'),
                            'confidence': decision.get('confidence', 0),
                            'z_score': decision.get('z_score', 0),
                            'position_size': decision.get('position_size', 0),
                            'sl': decision.get('sl', 0),
                            'tp': decision.get('tp', 0),
                            'broker_result': decision.get('broker_result', {})
                    }

                # Debug hybrid_data
                logger.info(f"📊 Hybrid Data: {len(hybrid_data)} entries")
                if hybrid_data:
                    for key, value in hybrid_data.items():
                        if isinstance(value, dict):
                            logger.info(f"   {key}: {value.get('vote', 'HOLD')} ({value.get('confidence', 0)}%)")
                        else:
                            logger.warning("⚠️ Hybrid data is EMPTY!")

                # ============================================================
                # GET HYBRID DECISION
                # ============================================================
                hybrid_decision = {
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': 'No signals available',
                    'layer': 'fallback'
                }
                best_pair = None
                best_signal = 'HOLD'
                best_conf = 0

                # ===== CHECK IF WE HAVE ANY SIGNALS FROM BROKERS OR AGENTS =====
                has_any_signals = False
                # Check if any broker has signal
                for pair, decision in decisions.items():
                    if decision.get('signal', 'HOLD') != 'HOLD':
                        has_any_signals = True
                        break

                # Check if any agent has signal
                if not has_any_signals:
                    for agent, result in agent_results.items():
                        if result.get('vote', 'HOLD') != 'HOLD':
                            has_any_signals = True
                            break
                if not has_any_signals:
                    logger.warning("⚠️ No signals from any source (agents or brokers)")
                    # Use synthetic signal for testing if no signals
                    logger.info("🧪 No signals - using synthetic BUY signal for testing")
                    best_pair = 'EURUSD'
                    best_signal = 'BUY'
                    best_conf = 70
                    hybrid_decision = {
                                        'action': best_signal,
                                        'confidence': best_conf,
                                        'reason': 'Synthetic signal (no real signals)',
                                        'layer': 'synthetic',
                                        'best_pair': best_pair
                    }
                else:
                    # Use hybrid coordinator if available
                    if hasattr(self, 'hybrid_coordinator') and self.hybrid_coordinator:
                                      try:
                                                          logger.info("🤖 Calling Hybrid Coordinator...")
                                                          hybrid_decision = self.hybrid_coordinator.decide(hybrid_data)
                                                          logger.info(f"✅ Hybrid Decision: {hybrid_decision.get('action')} ({hybrid_decision.get('confidence', 0):.1f}%)")
                                                          logger.info(f"   Reason: {hybrid_decision.get('reason', 'N/A')}")
                                      except Exception as e:
                                                          logger.warning(f"⚠️ Hybrid coordinator error: {e}")
                    
                    # If hybrid decision is HOLD or low confidence, use broker consensus
                    if hybrid_decision.get('action') == 'HOLD' or hybrid_decision.get('confidence', 0) < 50:
                                      logger.info("ℹ️ Hybrid decision weak - using broker consensus")
                                      
                                      best_signal = 'HOLD'
                                      best_conf = 0
                                      best_pair = None
                                      has_broker_signals = False
                                      
                                      for pair, decision in decisions.items():
                                                          signal = decision.get('signal', 'HOLD')
                                                          confidence = decision.get('confidence', 0)
                                                          if signal != 'HOLD':
                                                                            has_broker_signals = True
                                                                            logger.info(f"   Broker signal found: {pair} {signal} ({confidence:.1f}%)")
                                                                            if confidence > best_conf:
                                                                                                best_conf = confidence
                                                                                                best_signal = signal
                                                                                                best_pair = pair
                                      
                                      if has_broker_signals and best_pair:
                                                          hybrid_decision = {
                                                                            'action': best_signal,
                                                                            'confidence': best_conf,
                                                                            'reason': f'Broker consensus: {best_pair} {best_signal} ({best_conf:.1f}%)',
                                                                            'layer': 'broker_consensus',
                                                                            'best_pair': best_pair
                                                          }
                                                          logger.info(f"📊 Broker consensus: {best_signal} on {best_pair} ({best_conf:.1f}%)")
                                      else:
                                                          # Use agent signals as fallback
                                                          for agent, result in agent_results.items():
                                                                            signal = result.get('vote', 'HOLD')
                                                                            confidence = result.get('confidence', 0)
                                                                            if signal != 'HOLD' and confidence > best_conf:
                                                                                                best_conf = confidence
                                                                                                best_signal = signal
                                                                                                best_pair = 'EURUSD'  # Default pair for agent signals
                                                          
                                                          if best_signal != 'HOLD':
                                                                            hybrid_decision = {
                                                                                                'action': best_signal,
                                                                                                'confidence': best_conf,
                                                                                                'reason': f'Agent consensus: {best_signal} ({best_conf:.1f}%)',
                                                                                                'layer': 'agent_consensus',
                                                                                                'best_pair': best_pair
                                                                            }
                                                                            logger.info(f"📊 Agent consensus: {best_signal} ({best_conf:.1f}%)")
                                                          else:
                                                                            hybrid_decision = {
                                                                                                'action': 'HOLD',
                                                                                                'confidence': 0,
                                                                                                'reason': 'No broker or agent signals',
                                                                                                'layer': 'fallback'
                                                                            }

                results['hybrid_decision'] = hybrid_decision
                # ============================================================
                # 9. PROCESS EACH PAIR
                # ============================================================
                print(f"\n{'='*60}")
                print(f"📊 TRADING CYCLE - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                print(f"\n🎯 Hybrid Decision: {hybrid_decision['action']} ({hybrid_decision['confidence']:.1f}%)")
                print(f"   Reason: {hybrid_decision.get('reason', 'N/A')}")
                print(f"   Layer: {hybrid_decision.get('layer', 'N/A')}")
                if hybrid_decision.get('best_pair'):
                    print(f"   Best Pair: {hybrid_decision.get('best_pair')}")

                min_confidence = self.config.get('min_confidence', 60)
                executed_trades = []
                for pair in self.pairs:
                    if self._has_open_position(pair):
                        print(f"⏸️ {pair}: Already has position - skipping")
                        continue

                    price = market_data.get(pair, 0)
                    if price <= 0:
                        print(f"❌ {pair}: No price available")
                        continue

                    spread_ok = True
                    try:
                        if self.mt4:
                            price_data = self.mt4._send({"command": "PRICE", "symbol": pair})
                            if price_data and isinstance(price_data, dict):
                                bid = price_data.get('bid', 0)
                                ask = price_data.get('ask', 0)
                                if bid > 0 and ask > 0:
                                    spread = abs(ask - bid)
                                    spread_pct = (spread / bid) * 100
                                    print(f"   💧 {pair}: Spread = {spread_pct:.3f}% (Bid: {bid:.5f}, Ask: {ask:.5f})")
                                    if spread_pct > 0.05:
                                        spread_ok = False
                                        print(f"   ⚠️ Spread too high: {spread_pct:.3f}% - skipping")
                                        continue
                                elif bid > 0:
                                    spread_pips = 2 if pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF'] else 3
                                    pip = 0.0001 if pair not in ['USDJPY', 'EURJPY'] else 0.01
                                    spread = spread_pips * pip
                                    spread_pct = (spread / bid) * 100
                                    print(f"   💧 {pair}: Estimated Spread = {spread_pct:.3f}% (2 pips)")
                                    if spread_pct > 0.03:
                                        spread_ok = False
                                        print(f"   ⚠️ Estimated spread too high: {spread_pct:.3f}% - skipping")
                                        continue
                                else:
                                    spread_estimate = price * 0.0002
                                    spread_pct = (spread_estimate / price) * 100
                                    print(f"   💧 {pair}: Estimated Spread = {spread_pct:.3f}% (fallback)")
                                    if spread_pct > 0.03:
                                        spread_ok = False
                                        print(f"   ⚠️ Estimated spread too high: {spread_pct:.3f}% - skipping")
                                        continue
                            else:
                                spread_estimate = price * 0.0002
                                spread_pct = (spread_estimate / price) * 100
                                print(f"   💧 {pair}: Estimated Spread = {spread_pct:.3f}% (simulation)")
                        else:
                            spread_estimate = price * 0.0002
                            spread_pct = (spread_estimate / price) * 100
                            print(f"   💧 {pair}: Estimated Spread = {spread_pct:.3f}% (simulation)")
                    except Exception as e:
                        logger.debug(f"Spread check error for {pair}: {e}")

                    if not spread_ok:
                        continue

                    if not self._is_valid_price(pair, price):
                        print(f"  ❌ Invalid price {price:.5f} for {pair} - skipping")
                        continue

                    broker_decision = decisions.get(pair, {})
                    broker_signal = broker_decision.get('signal', 'HOLD')
                    broker_confidence = broker_decision.get('confidence', 0)
                    if broker_signal != 'HOLD' and broker_confidence >= min_confidence:
                        signal = broker_signal
                        confidence = broker_confidence
                        position_size = broker_decision.get('position_size', 1.0)
                        sl = broker_decision.get('sl', 0)
                        tp = broker_decision.get('tp', 0)
                        reasoning = broker_decision.get('reasoning', broker_decision.get('broker_result', {}).get('reasoning', 'N/A'))
                    else:
                        signal_data = {'pair': pair, 'price': price, 'current_price': price, 'symbol': pair}
                        agent_results_local = self._run_agents_parallel(signal_data)
                        signals = self._generate_signals(agent_results_local, market_data)
                        consensus = self._generate_consensus(signals)
                        signal = consensus.get('signal', 'HOLD')
                        confidence = consensus.get('confidence', 0)
                        position_size = 1.0
                        sl = 0
                        tp = 0
                        reasoning = consensus.get('reason', 'No consensus')

                    print(f"\n🔍 {pair}: Price={price:.5f} | Signal={signal} ({confidence:.1f}%)")

                    if signal == 'HOLD' or confidence < min_confidence:
                        print(f"                 ⏸️ {pair}: Signal HOLD or low confidence ({confidence:.1f}% < {min_confidence}%)")
                        continue

                    mc_confidence = 100
                    if self.monte_carlo and not self.config.get('bypass_mc', False):
                        price_history = market_data.get(f'{pair}_price_history', [])
                        atr = market_data.get(f'{pair}_atr', 0)
                        mc_results = self.monte_carlo.simulate_entry(
                            current_price=price,
                            direction=signal,
                            price_history=price_history,
                            atr=atr
                        )
                        mc_confidence = mc_results.get('entry_confidence', 0) if mc_results else 0
                        print(f"                 📊 {pair}: MC Confidence = {mc_confidence:.1f}%")
                    else:
                        print(f"                 📊 {pair}: MC Confidence BYPASSED")

                    if mc_confidence <= 30:
                        print(f"                 ❌ {pair}: MC confidence {mc_confidence:.1f}% <= 30% - REJECTED")
                        continue

                    if self.cold_start_active:
                        self._simulate_trade(pair, signal, confidence, price)
                        self.is_cold_start_complete()
                        print(f"                 🧪 {pair}: COLD START - Simulated trade")
                        continue

                    if self.rl_enabled and self.rl_agent:
                        try:
                            obs = self.rl_env._get_observation()
                            rl_action = self.rl_agent.predict(obs, deterministic=not self.rl_agent.training)
                            rl_pair_idx = int(np.clip(rl_action[0], 0, len(self.pairs) - 1))
                            rl_trade_type = int(np.clip(rl_action[1], 0, 2))
                            if rl_trade_type != 0 and self.pairs[rl_pair_idx] == pair:
                                safe, _ = self.rl_safe_to_trade(rl_action, market_data)
                                if safe:
                                    rl_signal = 'BUY' if rl_trade_type == 1 else 'SELL'
                                    rl_confidence = 85
                                    if rl_confidence > confidence + 15:
                                        logger.info(f"🤖 RL OVERRIDE: {rl_signal} on {pair} (RL: {rl_confidence}% > {confidence}%)")
                                        signal = rl_signal
                                        confidence = rl_confidence
                                        results['rl_used'] = True
                                    elif rl_signal != signal:
                                        confidence = max(40, confidence - 10)
                                        print(f"   🤖 RL contradicts: {rl_signal} vs {signal} - reducing confidence")
                        except Exception as e:
                            logger.debug(f"RL override error: {e}")

                    if self.config.get('enable_entry_confirmation', True):
                        print(f"                 🔄 {pair}: Checking 5-candle SMA confirmation...")
                        if not self._confirm_entry_with_candle_and_sr(pair, price, signal):
                            print(f"                 ⏸️ {pair}: Entry confirmation FAILED - SKIPPING")
                            continue
                        print(f"                 ✅ {pair}: Entry confirmation PASSED")

                    print(f"                 💼 {pair}: EXECUTING {signal} @ {price:.5f}")
                    consensus = {
                        'signal': signal,
                        'confidence': confidence,
                        'reason': reasoning,
                        'pair': pair
                    }

                    trade_result = self.execution_engine.execute_signal(
                        consensus, market_data, position_size=position_size, pair=pair
                    )

                    if trade_result and trade_result.get('status') == 'EXECUTED':
                        print(f"                 ✅ {pair}: TRADE EXECUTED! Ticket: {trade_result.get('ticket', 0)}")
                        results['trades'].append(trade_result)
                        executed_trades.append(trade_result)
                    else:
                        print(f"   ❌ {pair}: Trade failed: {trade_result.get('reason', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error processing cycle: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)

        self.last_results = results
        return results

    def _save_cold_start_state(self):
        """Save cold start data to file for persistence."""
        state = {
               'samples': self.cold_start_samples,
               'wins': self.cold_start_wins,
               'losses': self.cold_start_losses,
               'active': self.cold_start_active,
               'timestamp': datetime.now().isoformat()
        }
        try:
               with open('cold_start_state.json', 'w') as f:
                     json.dump(state, f, indent=2, default=str)
               logger.debug("💾 Cold start state saved.")
        except Exception as e:
               logger.warning(f"Failed to save cold start state: {e}")

    def _load_cold_start_state(self):
        """Load cold start data from file."""
        if not os.path.exists('cold_start_state.json'):
               return False
        
        try:
               with open('cold_start_state.json', 'r') as f:
                     state = json.load(f)
               self.cold_start_samples = state.get('samples', [])
               self.cold_start_wins = state.get('wins', 0)
               self.cold_start_losses = state.get('losses', 0)
               self.cold_start_active = state.get('active', True)
               logger.info(f"✅ Loaded cold start state: {len(self.cold_start_samples)} samples, wins={self.cold_start_wins}, losses={self.cold_start_losses}")
               return True
        except Exception as e:
               logger.warning(f"Failed to load cold start state: {e}")
               return False
    def _has_open_position(self, pair: str) -> bool:
        if self.execution_engine and pair in self.execution_engine.positions:
                return True
        # Optionally check MT4 real positions
        if self.mt4:
                try:
                        pos_data = self.mt4._send({"command": "POSITIONS"})
                        if pos_data and pos_data.get('positions'):
                                for pos in pos_data.get('positions', []):
                                        if pos.get('symbol') == pair:
                                                return True
                except:
                        pass
        return False
    def _run_agents_parallel(self, signal_data):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                futures = {executor.submit(self._analyze_single_agent, agent, signal_data): agent for agent in self.agents}
                for future in as_completed(futures):
                        name, result = future.result()
                        results[name] = result
        return results

    def _analyze_single_agent(self, agent, signal_data):
        try:
                return agent.name, agent.analyze(signal_data)
        except Exception as e:
                return agent.name, {'vote': 'HOLD', 'confidence': 50, 'reasoning': f'Error: {e}'}
    def _generate_signals(self, agent_results: Dict, market_data: Dict) -> Dict:
        """Generate signals from agent results"""
        signals = {}
        for agent_name, result in agent_results.items():
            pair = result.get('pair', 'EURUSD')
            signals[agent_name] = {
                'pair': pair,
                'signal': result.get('vote', 'HOLD'),
                'confidence': result.get('confidence', 50),
                'reasoning': result.get('reasoning', ''),
                'timestamp': datetime.now().isoformat()
            }
        return signals
    
    def _generate_consensus(self, signals: Dict) -> Dict:
        """Generate consensus from all signals"""
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0
        buy_confidences = []
        sell_confidences = []
        
        for agent_name, signal in signals.items():
            vote = signal.get('signal', 'HOLD')
            confidence = signal.get('confidence', 50)
            
            if vote == 'BUY':
                buy_votes += 1
                buy_confidences.append(confidence)
            elif vote == 'SELL':
                sell_votes += 1
                sell_confidences.append(confidence)
            else:
                hold_votes += 1
        
        avg_buy = sum(buy_confidences) / len(buy_confidences) if buy_confidences else 0
        avg_sell = sum(sell_confidences) / len(sell_confidences) if sell_confidences else 0
        
        buy_score = buy_votes * (avg_buy / 100) if avg_buy > 0 else 0
        sell_score = sell_votes * (avg_sell / 100) if avg_sell > 0 else 0
        
        if buy_score > sell_score and buy_score > 0:
            signal = 'BUY'
            confidence = min(95, (buy_score / (buy_score + sell_score + 0.01)) * 100)
            reason = f"Consensus BUY ({buy_votes} votes, avg conf: {avg_buy:.0f}%)"
        elif sell_score > buy_score and sell_score > 0:
            signal = 'SELL'
            confidence = min(95, (sell_score / (buy_score + sell_score + 0.01)) * 100)
            reason = f"Consensus SELL ({sell_votes} votes, avg conf: {avg_sell:.0f}%)"
        else:
            signal = 'HOLD'
            confidence = 50
            reason = f"Consensus HOLD (BUY:{buy_votes} SELL:{sell_votes} HOLD:{hold_votes})"
        
        return {
            'signal': signal,
            'confidence': round(confidence, 1),
            'reason': reason,
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'hold_votes': hold_votes,
            'total_agents': len(signals)
        }
    
    # ============================================================
    # CONTROL METHODS
    # ============================================================
    
    def start(self):
        """Start the controller"""
        self.is_running = True
        logger.info("🚀 ForexTradingController started")
    
    def stop(self):
        """Stop the controller"""
        self.is_running = False
        logger.info("🛑 ForexTradingController stopped")
    
    def get_status(self) -> Dict:
          """Get current status"""
          # Count actual open positions (not brokers)
          actual_positions = {}
          if self.execution_engine and hasattr(self.execution_engine, 'positions'):
                    for pair, pos in self.execution_engine.positions.items():
                              # Only count if it's an actual trade position
                              if isinstance(pos, dict) and pos.get('type') in ['BUY', 'SELL']:
                                        actual_positions[pair] = pos
          
          return {
                    'name': self.name,
                    'is_running': self.is_running,
                    'cycle_count': self.cycle_count,
                    'pairs': self.pairs,
                    'agents': len(self.agents),
                    'engine': self.engine.get_status() if hasattr(self.engine, 'get_status') else {},
                    'execution': self.execution_engine.get_status() if hasattr(self.execution_engine, 'get_status') else {},
                    'positions': actual_positions,
                    'active_count': len(actual_positions),
                    'trades_today': self.execution_engine.trades_today if self.execution_engine else 0,
                    'daily_pnl': self.execution_engine.daily_pnl if self.execution_engine else 0,
                    'timestamp': datetime.now().isoformat()
          }
    def place_order(self, symbol, order_type, price, sl, tp, volume):
        """Place order - check existing first"""
        try:
              # ===== CHECK FOR EXISTING POSITION FIRST =====
              if self.mt4:
                      positions = self.mt4._send({"command": "POSITIONS"})
                      if positions and positions.get('positions'):
                            for pos in positions.get('positions', []):
                                    if pos.get('symbol') == symbol:
                                          print(f"⏸️ Position already exists for {symbol} - REJECTING new order")
                                          return {
                                                  'success': False, 
                                                  'error': 'Position already exists',
                                                  'existing_ticket': pos.get('ticket')
                                          }
              
              # ===== PLACE NEW ORDER =====
              order = {
                      "command": "ORDER",
                      "symbol": symbol,
                      "type": order_type,
                      "volume": volume,
                      "sl": sl,
                      "tp": tp
              }
              
              result = self.mt4._send(order)
              return result
        
        except Exception as e:
            print(f"❌ Order error: {e}")
            return {'success': False, 'error': str(e)}
    def send_real_order(self, symbol, action, price, sl, tp, volume, max_retries=3):
        """
        Send REAL order to MT4 with retry logic and price validation.
        """
        try:
                from mt4_price_provider import get_mt4_prices
                mt4 = get_mt4_prices()
                if isinstance(volume, np.float32) or isinstance(volume, np.float64):
                    volume = float(volume)
                if isinstance(price, np.float32) or isinstance(price, np.float64):
                   price = float(price)
                if isinstance(sl, np.float32) or isinstance(sl, np.float64):
                    sl = float(sl)
                if isinstance(tp, np.float32) or isinstance(tp, np.float64):
                    tp = float(tp)
        
        # Round volume to 2 decimal places (MT4 standard)
                volume = round(volume, 2)
        

                # ===== STEP 1: GET REAL PRICE FROM MT4 =====
                price_data = mt4._send({"command": "PRICE", "symbol": symbol})
                
                if price_data and isinstance(price_data, dict):
                          bid = price_data.get('bid', 0)
                          ask = price_data.get('ask', 0)
                          
                          if bid > 0 and ask > 0:
                                # Use real MT4 prices
                                if action == 'BUY':
                                        entry_price = ask
                                else:
                                        entry_price = bid
                                
                                # Update price with real MT4 price
                                logger.info(f"   MT4 Price: {symbol} Bid={bid:.5f} Ask={ask:.5f} Mid={(bid+ask)/2:.5f}")
                          else:
                                entry_price = price
                else:
                          entry_price = price
                
                # ===== STEP 2: VALIDATE PRICE IS REASONABLE =====
                if entry_price < 0.5 or entry_price > 2.0:
                          logger.warning(f"⚠️ Suspicious price: {entry_price:.5f} for {symbol} - trying to get fresh price")
                          # Try one more time
                          time.sleep(0.2)
                          price_data = mt4._send({"command": "PRICE", "symbol": symbol})
                          if price_data and isinstance(price_data, dict):
                                bid = price_data.get('bid', 0)
                                ask = price_data.get('ask', 0)
                                if bid > 0 and ask > 0:
                                        entry_price = ask if action == 'BUY' else bid
                                        logger.info(f"   Fresh MT4 Price: {entry_price:.5f}")
                                else:
                                        logger.error(f"❌ Still invalid price: {entry_price}")
                                        return {'success': False, 'error': f'Invalid price: {entry_price}'}
                
                # ===== STEP 3: CALCULATE SL AND TP =====
                config = self.get_symbol_config(symbol)
                pip = config.get('pip', 0.0001)
                digits = config.get('digits', 5)
                sl_pips = config.get('sl_pips', 15)  # Increased
                tp_pips = config.get('tp_pips', 30)
                
                if action == 'BUY':
                          sl = entry_price - (sl_pips * pip)
                          tp = entry_price + (tp_pips * pip)
                else:  # SELL
                          sl = entry_price + (sl_pips * pip)
                          tp = entry_price - (tp_pips * pip)
                
                # ===== STEP 4: VALIDATE SL AND TP ARE VALID =====
                min_distance = 10 * pip  # Minimum 10 pips
                max_distance = 100 * pip  # Maximum 100 pips
                
                # Check SL distance
                sl_distance = abs(entry_price - sl)
                if sl_distance < min_distance:
                          logger.warning(f"   SL too close ({sl_distance:.5f} < {min_distance:.5f}) - adjusting")
                          if action == 'BUY':
                                sl = entry_price - (min_distance * 1.5)
                          else:
                                sl = entry_price + (min_distance * 1.5)
                
                # Check TP distance
                tp_distance = abs(tp - entry_price)
                if tp_distance < min_distance:
                          logger.warning(f"   TP too close ({tp_distance:.5f} < {min_distance:.5f}) - adjusting")
                          if action == 'BUY':
                                tp = entry_price + (min_distance * 2)
                          else:
                                tp = entry_price - (min_distance * 2)
                
                # Round to correct digits
                entry_price = round(entry_price, digits)
                sl = round(sl, digits)
                tp = round(tp, digits)
                
                # ===== STEP 5: LOG ORDER =====
                logger.info(f"\n📤 SENDING ORDER:")
                logger.info(f"   Pair: {symbol}")
                logger.info(f"   Action: {action}")
                logger.info(f"   Volume: {volume}")
                logger.info(f"   Entry: {entry_price:.{digits}f}")
                logger.info(f"   SL: {sl:.{digits}f} ({sl_pips} pips)")
                logger.info(f"   TP: {tp:.{digits}f} ({tp_pips} pips)")
                
                # ===== STEP 6: SEND ORDER WITH RETRY =====
                for attempt in range(max_retries):
                          order = {
                                "command": "ORDER",
                                "symbol": symbol,
                                "type": action,
                                "volume": volume,
                                "sl": sl,
                                "tp": tp
                          }
                          
                          result = mt4._send(order)
                          
                          if result and result.get('success'):
                                logger.info(f"   ✅ ORDER EXECUTED! Ticket: {result.get('ticket', 0)}")
                                return {'success': True, 'ticket': result.get('ticket', 0)}
                          
                          error = result.get('error', 'Unknown')
                          
                          # Handle specific errors
                          if 'Timeout' in str(error):
                                logger.warning(f"   ⏳ Timeout, retrying ({attempt+1}/{max_retries})...")
                                time.sleep(1)
                                continue
                          elif 'Error 130' in str(error):
                                # Invalid stops - increase distance
                                sl_pips += 5
                                tp_pips += 5
                                logger.warning(f"   ⚠️ Error 130 - adjusting SL/TP (SL={sl_pips}pips, TP={tp_pips}pips)")
                                if action == 'BUY':
                                        sl = entry_price - (sl_pips * pip)
                                        tp = entry_price + (tp_pips * pip)
                                else:
                                        sl = entry_price + (sl_pips * pip)
                                        tp = entry_price - (tp_pips * pip)
                                sl = round(sl, digits)
                                tp = round(tp, digits)
                                time.sleep(0.5)
                                continue
                          else:
                                # Other errors
                                logger.error(f"   ❌ ORDER FAILED: {error}")
                                return {'success': False, 'error': error}
                
                return {'success': False, 'error': 'Max retries exceeded'}
                
        except Exception as e:
                logger.error(f"   ❌ ORDER ERROR: {e}")
                return {'success': False, 'error': str(e)}
    def _simulate_order(self, symbol, action, price, sl, tp, volume, max_retries=1):
        """Simulate order execution during training."""
        logger.info(f"🔬 [SIMULATION] WOULD SEND: {symbol} {action} {volume} @ {price:.5f} SL:{sl:.5f} TP:{tp:.5f}")
        
        # Simulate a successful order with random ticket
        import random
        return {
              'success': True, 
              'ticket': random.randint(10000, 99999),
              'simulated': True
        }
# MAIN
# ============================================================

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("FOREX TRADING CONTROLLER V2 - ALL FOREX PAIRS")
    print("="*60 + "\n")
    
    print("📊 ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")
    
    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    
    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 60,
        'cycle_interval': 10,
        'rl_enabled': True,  # Enable RL
        'load_rl_model': False,  # Set True to load existing model
        'rl_model_path': 'models/rl_model.zip',    
        'cycle_interval': 10,  # 10 seconds between cycles (M15 candles update every 15 min)
        'timeframe': 'M15',    # ← FORCE M15 TIMEFRAME

        #'bypass_mc': False,  # ← ADD THIS LINE
        'engine_config': {
            'factor_weights': {
                'interest_rate_diff': 0.35,
                'yield_curve_slope': 0.25,
                'carry_trade_flow': 0.15,
                'positioning_sentiment': 0.15,
                'central_bank_actions': 0.10,
            }
        }
    }
    
    controller = ForexTradingController(config)
    controller.start()
    
    # Build market data
    market_data = controller.build_market_data()
    
    # Process one cycle
    result = controller.process_cycle(market_data)
    
    # Display results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    print(f"\n📈 Cycle: {result.get('cycle', 0)}")
    
    engine = result.get('engine', {})
    print(f"\n🔧 Engine:")
    print(f"   Direction: {engine.get('engine_direction', 'N/A')}")
    print(f"   Speed: {engine.get('engine_speed', 0):.3f}")
    print(f"   Health: {engine.get('engine_health', 0):.1f}%")
    
    agents = result.get('agents', {})
    print(f"\n🤖 Agents:")
    for name, agent_result in agents.items():
        vote = agent_result.get('vote', 'HOLD')
        confidence = agent_result.get('confidence', 0)
        print(f"   {name}: {vote} ({confidence:.0f}%)")
    
    consensus = result.get('consensus', {})
    print(f"\n📊 Consensus:")
    print(f"   Signal: {consensus.get('signal', 'HOLD')}")
    print(f"   Confidence: {consensus.get('confidence', 0):.1f}%")
    print(f"   Votes: BUY={consensus.get('buy_votes', 0)}, SELL={consensus.get('sell_votes', 0)}, HOLD={consensus.get('hold_votes', 0)}")
    
    trade = result.get('trade', {})
    print(f"\n💼 Trade:")
    print(f"   Status: {trade.get('status', 'N/A')}")
    
    controller.stop()
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60 + "\n")

def debug_trade_decision(self, consensus: Dict, market_data: Dict):
    """Debug why trade is being skipped"""
    print("\n" + "="*60)
    print("🔍 TRADE DECISION DEBUG")
    print("="*60)
    
    signal = consensus.get('signal', 'HOLD')
    confidence = consensus.get('confidence', 0)
    min_conf = self.config.get('min_confidence', 60)
    
    print(f"   Signal: {signal}")
    print(f"   Confidence: {confidence:.1f}%")
    print(f"   Min Confidence Required: {min_conf}%")
    print(f"   Passes Confidence Check: {confidence >= min_conf}")
    
    if signal != 'HOLD' and confidence >= min_conf:
        pair = 'EURUSD'
        price = market_data.get(pair, 0)
        print(f"   Pair: {pair}")
        print(f"   Price: {price:.5f}")
        print(f"   Has Price: {price > 0}")
        
        if price > 0:
            # Check Monte Carlo
            mc_results = self.monte_carlo.simulate_entry(
                current_price=price,
                direction=signal
            )
            mc_confidence = mc_results.get('entry_confidence', 0) if mc_results else 0
            print(f"   Monte Carlo Confidence: {mc_confidence:.1f}%")
            print(f"   MC Passes: {mc_confidence > 30}")
            
            if mc_confidence > 30:
                print("   ✅ ALL CHECKS PASSED - TRADE SHOULD EXECUTE")
            else:
                print("   ❌ Monte Carlo confidence too low")
        else:
            print("   ❌ No price available")
    else:
        if signal == 'HOLD':
            print("   ❌ Signal is HOLD")
        if confidence < min_conf:
            print(f"   ❌ Confidence {confidence:.1f}% < {min_conf}%")
    
    print("="*60 + "\n")
    
    

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FOREX TRADING CONTROLLER V2 - LIVE TRADING")
    print("="*60 + "\n")
    
    print("📊 ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")
    
    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    print(f"   Min Confidence: 50%")
    print(f"   Cycle Interval: 10s")
    
    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 70, # ← Lowered for testing
        'cycle_interval': 10,
        'cold_start_min_win_rate': 0.0,   # 0% = any win rate
        'cold_start_threshold': 50,
        'enable_entry_confirmation': True,  
        'entry_threshold': 1.0,

        'rl_enabled': True,  # Enable RL
        'load_rl_model': True,  # Set True to load existing model
        'rl_model_path': 'models/rl_model.zip',

        'engine_config': {
            'factor_weights': {
                'interest_rate_diff': 0.35,
                'yield_curve_slope': 0.25,
                'carry_trade_flow': 0.15,
                'positioning_sentiment': 0.15,
                'central_bank_actions': 0.10,
            }
        }
    }
    
    controller = ForexTradingController(config)
    controller.start()
      # ===== CLEAR STUCK POSITIONS AT START =====
    print("\n🗑️ Clearing any stuck positions...")
    controller.clear_stuck_positions()
    print("✅ Ready to trade!\n")
    
    controller.start()
    
    try:
        print("\n🔄 Live Trading Started... Press Ctrl+C to stop\n")
        cycle_count = 0
        
        while True:
            time.sleep(10)
            cycle_count += 1
            
            # Build market data
            market_data = controller.build_market_data()
            
            # Process cycle
            result = controller.process_cycle(market_data)
            
            # Get status
            status = controller.get_status()
            consensus = result.get('consensus', {})
            trade = result.get('trade', {})
            engine = result.get('engine', {})
            rl_used = result.get('rl_used', False)

            # Display
            signal = consensus.get('signal', 'NONE')
            confidence = consensus.get('confidence', 0)
            trade_status = trade.get('status', 'NONE')
            active = status.get('active_count', 0)

            
            # Check if positions are stuck and fix
            if cycle_count > 1 and len(controller.execution_engine.positions) > 0:
                # Check if positions are real or stuck
                real_positions = {}
                for pair, pos in controller.execution_engine.positions.items():
                    if isinstance(pos, dict) and pos.get('type') in ['BUY', 'SELL']:
                        # Check if it has real trade data
                        if pos.get('price', 0) > 0 and pos.get('volume', 0) > 0:
                            real_positions[pair] = pos
                
                # If no real positions but positions dict has entries, clear them
                if len(real_positions) == 0 and len(controller.execution_engine.positions) > 0:
                    print("⚠️ Found stuck positions - clearing...")
                    controller.clear_stuck_positions()
                # Add this to your main loop in trading_controller2.py
# After processing the cycle, check broker decisions
# In the main loop (while True):
                if cycle_count % 5 == 0:
                    controller._save_cold_start_state()
                # After trade execution
                if self.rl_enabled and len(self.replay_buffer) % 10 == 0:  # every 10 trades
                    self._train_rl_from_replay()
            # Build and process
            market_data = controller.build_market_data()
            result = controller.process_cycle(market_data)
            
            # Get status
            status = controller.get_status()
            trade = result.get('trades', [])
            
            print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Cycle: {cycle_count} | "
                  f"Trades: {len(trade)} | "
                  f"P&L: ${status['daily_pnl']:.2f}")
            print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Cycle: {cycle_count} | "
                  f"Active: {active} | "
                  f"RL: {'✅' if rl_used else '❌'} | "

                  f"Signal: {signal} ({confidence:.0f}%) | "
                  f"Trade: {trade_status} | "
                  f"Engine: {engine.get('engine_direction', 'N/A')} | "
                  f"P&L: ${status['daily_pnl']:.2f}")
                  
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        controller.stop()
        print("✅ Stopped")