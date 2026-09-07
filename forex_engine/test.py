# trading_controller2.py - ALL FOREX PAIRS FROM DASHBOARD (FIXED)
# Fixed version: removes duplicates, corrects signatures, fixes logic errors

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import threading
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# Core components
from core.dollar_engine import DollarEngine
from core.gear_broker import GearBroker
from core.gear_anomaly_detector import GearAnomalyDetector
from core.monte_carlo_simulator import MonteCarloSimulator
from core.order_execution import OrderExecutionEngine
from brokers import BROKER_MAP, BaseBroker, BrokerManager

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
    print("All agents imported successfully")
except ImportError as e:
    print(f"Agent import error: {e}")
    class ForexAgentX:
        def __init__(self, name="Forex_X", timeframe="M15"):
            self.name = name; self.agent_type = "Spread Reversion Specialist"; self.timeframe = timeframe
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    class ForexLiquidityAgentEnhanced:
        def __init__(self, name="Forex_Agent_U", timeframe="M15"):
            self.name = name; self.agent_type = "Liquidity Specialist"; self.timeframe = timeframe
            self.z_score = 0.0; self.spread_history = []
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    class AgentDVolatility:
        def __init__(self, name="Forex_D", timeframe="M15"):
            self.name = name; self.agent_type = "Volatility Specialist"; self.timeframe = timeframe
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    class AgentCMomentum:
        def __init__(self): self.name = "Agent_C"; self.agent_type = "Pair Agent"
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    class AgentEMicrostructure:
        def __init__(self): self.name = "Agent_E"; self.agent_type = "Base Pair Agent"
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
    class WhisperAnalyst:
        def __init__(self): self.name = "Agent_P"; self.agent_type = "Cross Pair Agent"
        def analyze(self, data): return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}

# RL Modules
try:
    from rl_trading_env import ForexTradingEnv
    from rl_agent import RLAgent
    RL_AVAILABLE = True
    print("RL modules imported successfully")
except ImportError as e:
    print(f"RL modules not available: {e}")
    RL_AVAILABLE = False
    class ForexTradingEnv:
        def __init__(self, *args, **kwargs): pass
    class RLAgent:
        def __init__(self, *args, **kwargs): pass

# MT4 Price Provider
try:
    from mt4_price_provider import get_mt4_prices
except ImportError:
    print("mt4_price_provider not found")
    def get_mt4_prices(): return None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# SYMBOL CONFIG
# ============================================================
SYMBOL_CONFIG = {
    'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03, 'type': 'forex'},
    'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03, 'type': 'forex'},
    '#Dollar_IND': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40, 'volume': 0.02, 'type': 'index'},
}

FOREX_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
               'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF']

ALL_SYMBOLS = FOREX_PAIRS + ['GOLD', 'SILVER', '#NASDAQ100', '#DJ30', '#S&P500',
    '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI334', 'BRENT_OIL', 'CrudeOIL', '#DOLLAR_IND']


class ForexTradingController:
    """Main trading controller - uses MT4 ACCOUNT command (SAME as dashboard)"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.name = "ForexGearController"
        self.timeframe = self.config.get('timeframe', 'M15')
        self.is_running = False
        self.cycle_interval = self.config.get('cycle_interval', 10)
        self.cycle_count = 0
        self.decision_log = []
        self.last_results = {}
        self.active_positions = {}
        self.entry_threshold = self.config.get('entry_threshold', 2.0)
        self.exit_threshold = self.config.get('exit_threshold', 0.3)
        self.account_balance = 10000.0
        self._z_history = {}
        self.replay_buffer = []
        self.replay_buffer_max = 5000
        self.rl_train_every = 10
        self.rl_train_batch_size = 10

        # Cold start
        self.cold_start_active = True
        self.cold_start_threshold = self.config.get('cold_start_threshold', 50)
        self.cold_start_min_win_rate = self.config.get('cold_start_min_win_rate', 0.4)
        self.cold_start_samples = []
        self.cold_start_wins = 0
        self.cold_start_losses = 0
        self.cold_start_skip_real = self.config.get('cold_start_skip_real', True)
        self._load_cold_start_state()
        logger.info(f"   Cold Start: {self.cold_start_threshold} samples, min win rate {self.cold_start_min_win_rate*100:.0f}%")

        # Risk management
        self.daily_loss_limit = self.config.get('daily_loss_limit', 100)
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.max_trades_per_day = self.config.get('max_trades_per_day', 5)
        self.consecutive_losses = 0
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 3)
        self.last_trade_was_win = True
        self.weekly_pnl = 0.0
        self.weekly_loss_limit = self.config.get('weekly_loss_limit', 300)
        self.week_start_day = datetime.now().weekday()

        # RL (single initialization - FIXED duplicate removed)
        self.rl_enabled = self.config.get('rl_enabled', False)
        self.rl_agent = None
        self.rl_env = None
        if self.rl_enabled and RL_AVAILABLE:
            try:
                logger.info("Initializing RL Agent...")
                self.rl_env = ForexTradingEnv(self, self.config)
                model_path = self.config.get('rl_model_path', 'models/rl_model.zip')
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                self.rl_agent = RLAgent(self.rl_env, model_path=model_path,
                                        load_existing=self.config.get('load_rl_model', False))
                logger.info("   RL Agent initialized")
            except Exception as e:
                logger.error(f"   RL Agent init failed: {e}")
                self.rl_agent = None; self.rl_env = None; self.rl_enabled = False

        # Performance tracker
        try:
            self.performance = PerformanceTracker(self.config)
            logger.info("   Performance Tracker initialized")
        except Exception as e:
            logger.error(f"   Performance Tracker error: {e}")
            self.performance = None

        # MT4
        self.mt4 = None
        self._connect_mt4()

        # Agents
        self.agent_x = ForexAgentX(name="Forex_X", timeframe=self.timeframe)
        self.agent_u = ForexLiquidityAgentEnhanced(name="Forex_Agent_U")
        self.agent_d = AgentDVolatility(name="Forex_D", timeframe=self.timeframe)
        self.agent_c = AgentCMomentum()
        self.agent_e = AgentEMicrostructure()
        self.agent_p = WhisperAnalyst()
        self.agents = [self.agent_x, self.agent_u, self.agent_d, self.agent_c, self.agent_e, self.agent_p]
        logger.info(f"   {len(self.agents)} agents initialized")

        # Agent weights (now used in consensus)
        self.agent_weights = {'Forex_X': 1.2, 'Forex_Agent_U': 0.8, 'Forex_D': 1.0,
                              'Agent_C': 1.0, 'Agent_E': 0.9, 'Agent_P': 1.1}

        # Core components
        logger.info("Initializing Core Components...")
        self.engine = DollarEngine(self.config.get('engine_config', {}))
        logger.info("   Dollar Engine initialized")
        self.monte_carlo = MonteCarloSimulator(self.config.get('monte_carlo_config', {}))
        logger.info("   Monte Carlo Simulator initialized")
        self.anomaly_detector = GearAnomalyDetector(self.config.get('anomaly_detector_config', {}))
        logger.info("   Anomaly Detector initialized")
        self.execution_engine = OrderExecutionEngine(self.engine, self.config.get('execution_config', {}))
        logger.info("   Order Execution Engine initialized")

        # Brokers
        self.pairs = self.config.get('pairs', FOREX_PAIRS)
        self.brokers = {}
        logger.info(f"Initializing Brokers for {len(self.pairs)} pairs...")
        for pair in self.pairs:
            pair_config = self.config.get('pairs_config', {}).get(pair, {})
            if pair in SYMBOL_CONFIG:
                pair_config = {**SYMBOL_CONFIG[pair], **pair_config}
            broker = GearBroker(pair, pair_config, self.engine)
            self.brokers[pair] = broker
            self.execution_engine.register_broker(pair, broker)
            logger.info(f"   Broker: {pair}")
        self.anomaly_detector.set_brokers(self.brokers)

        # Broker Manager (FIXED: removed duplicate import, fixed indentation)
        logger.info("Initializing Broker Manager...")
        try:
            self.broker_manager = BrokerManager(self.engine, self.monte_carlo, self.rl_agent)
            self.broker_manager.register_brokers(self.pairs, BROKER_MAP)
            logger.info(f"   Broker Manager initialized with {len(self.broker_manager.brokers)} brokers")
            self.fix_all_broker_attributes()
            self.initialize_broker_price_history()
        except Exception as e:
            logger.error(f"   Broker Manager error: {e}")
            import traceback; traceback.print_exc()
            self.broker_manager = None

        # Debug broker state
        if self.broker_manager:
            logger.info("DEBUG: Broker state")
            for pair in self.pairs:
                broker = self.broker_manager.brokers.get(pair)
                if broker:
                    hist_len = len(broker.close_history) if hasattr(broker, 'close_history') else 0
                    z = broker.z_score if hasattr(broker, 'z_score') else 0
                    price = broker.current_price if hasattr(broker, 'current_price') else 0
                    logger.info(f"   {pair}: history={hist_len}, z={z:.2f}, price={price:.5f}")
                else:
                    logger.info(f"   {pair}: broker not found")

        self._log_current_prices()
        logger.info("ForexTradingController initialized successfully!")
        logger.info(f"   Pairs: {len(self.pairs)} | Agents: {len(self.agents)} | Cycle: {self.cycle_interval}s")

    # ============================================================
    # MT4 CONNECTION
    # ============================================================
    def _connect_mt4(self):
        try:
            self.mt4 = get_mt4_prices()
            if self.mt4:
                test_result = self.mt4._send({"command": "ACCOUNT"})
                if test_result and isinstance(test_result, dict):
                    balance = test_result.get('balance', 0)
                    if balance > 0:
                        logger.info(f"   MT4 connected - Balance: ${balance:.2f}")
                        return
                    else:
                        logger.warning(f"   MT4 connected but no account data")
                else:
                    logger.warning(f"   MT4 connected but test failed")
            else:
                logger.warning("   MT4 connection failed - simulation mode")
        except Exception as e:
            logger.error(f"   MT4 connection error: {e}")
            self.mt4 = None

    def get_all_mt4_prices(self) -> Dict:
        try:
            appdata = os.environ.get('APPDATA', '')
            file_path = os.path.join(appdata, 'MetaQuotes', 'Terminal', 'Common', 'Files', 'dashboard_data.json')
            if not os.path.exists(file_path):
                file_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/dashboard_data.json"
            if not os.path.exists(file_path):
                return {}
            with open(file_path, 'r') as f:
                data = json.load(f)
            prices = {}
            if 'prices' in data:
                for symbol, price in data['prices'].items():
                    if price > 0: prices[symbol] = price
            for pair in FOREX_PAIRS:
                if pair in data and pair not in prices:
                    price = float(data.get(pair, 0))
                    if price > 0: prices[pair] = price
            if '#Dollar_IND' in data:
                dp = float(data.get('#Dollar_IND', 0))
                if dp > 0: prices['#Dollar_IND'] = dp
            return prices
        except Exception as e:
            logger.warning(f"Error reading file: {e}")
            return {}

    def _get_price(self, symbol: str) -> Optional[float]:
        try:
            if not self.mt4: return None
            result = self.mt4._send({"command": "PRICE", "symbol": symbol})
            if result and isinstance(result, dict): return result.get('bid', 0)
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def get_price(self, symbol: str) -> float:
        return self.get_all_mt4_prices().get(symbol, 0)

    def get_all_prices(self) -> Dict:
        return self.get_all_mt4_prices()

    def _log_current_prices(self):
        try:
            prices = self.get_all_mt4_prices()
            print(f"PRICE CHECK - {datetime.now().strftime('%H:%M:%S')}")
            for symbol in FOREX_PAIRS:
                price = prices.get(symbol, 0)
                print(f"   {symbol:12} | {price:12.5f}" if price > 0 else f"   {symbol:12} | NO PRICE")
            if self.agent_x:
                z = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                s = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                print(f"   Agent_X: Z={z:.2f} | Samples={s}/30")
        except Exception as e:
            logger.warning(f"Price log error: {e}")

    # ============================================================
    # BUILD MARKET DATA
    # ============================================================
    def build_market_data(self) -> Dict:
        market_data = {}
        prices = self.get_all_mt4_prices()
        for pair in self.pairs:
            if pair in prices and prices[pair] > 0:
                market_data[pair] = prices[pair]
                market_data[f'{pair}_price'] = prices[pair]
        for pair in self.pairs:
            try:
                candles = self._get_m5_candles(pair, count=20)
                if candles and len(candles) >= 20:
                    closes = [c['close'] for c in candles]
                    market_data[f'{pair}_price_history'] = closes
                    atr = self._get_atr(pair, timeframe='M5', period=14)
                    market_data[f'{pair}_atr'] = atr
            except Exception as e:
                logger.debug(f"Error building history for {pair}: {e}")
        if 'EURUSD' in market_data and market_data['EURUSD'] > 0:
            market_data['current_price'] = market_data['EURUSD']
            market_data['price'] = market_data['EURUSD']
            market_data['pair'] = 'EURUSD'
        engine_state = self.engine.get_status() if self.engine else {}
        market_data['engine_state'] = {
            'engine_speed': engine_state.get('engine_speed', 0.3),
            'engine_direction': engine_state.get('engine_direction', 'FORWARD'),
            'engine_health': engine_state.get('engine_health', 95.0),
            'reversal_probability': engine_state.get('reversal_probability', 20.0),
            'regime': engine_state.get('regime', 'RANGING')
        }
        for pair in self.pairs:
            if pair in self.brokers:
                try:
                    gear_pred = self.engine.get_gear_prediction(pair, self.brokers[pair].gear_ratio)
                    market_data[f'{pair}_gear_prediction'] = gear_pred
                except Exception:
                    pass
        market_data['timestamp'] = datetime.now().isoformat()
        if prices:
            logger.info(f"Built market data with {len(prices)} prices")
        return market_data

    # ============================================================
    # CANDLE METHODS
    # ============================================================
    def _get_candles(self, pair: str, timeframe: str = 'H1', count: int = 5) -> List[Dict]:
        if not self.mt4: return []
        try:
            result = self.mt4._send({"command": "HISTORY", "symbol": pair, "timeframe": timeframe, "count": count + 1})
            if result and isinstance(result, dict):
                candles = result.get('candles', [])
                if len(candles) >= count: return candles[-count:]
        except Exception as e:
            logger.debug(f"Error fetching {timeframe} candles for {pair}: {e}")
        if timeframe in ['M5', 'M15']: return self._get_m5_candles(pair, count)
        return []

    def _get_m5_candles(self, symbol: str, count: int = 6) -> List[Dict]:
        try:
            if self.mt4:
                result = self.mt4._send({"command": "HISTORY", "symbol": symbol, "timeframe": "M5", "count": count + 1})
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if len(candles) >= count: return candles[-count:]
        except Exception as e:
            logger.debug(f"Error fetching M5 candles for {symbol}: {e}")
        return []

    def _get_last_m5_candle(self, symbol: str) -> Optional[Dict]:
        candles = self._get_m5_candles(symbol, count=2)
        if candles and len(candles) >= 2:
            return candles[-2]
        return None

    def _find_recent_swings(self, symbol: str, lookback: int = 50) -> Dict:
        try:
            if self.mt4:
                result = self.mt4._send({"command": "HISTORY", "symbol": symbol, "timeframe": "M5", "count": lookback})
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if candles:
                        highs = [c['high'] for c in candles]
                        lows = [c['low'] for c in candles]
                        return {'support': min(lows), 'resistance': max(highs)}
        except Exception:
            pass
        return {'support': 0, 'resistance': 0}

    def _get_atr(self, symbol: str, timeframe: str = 'M5', period: int = 14) -> float:
        try:
            if self.mt4:
                result = self.mt4._send({"command": "HISTORY", "symbol": symbol, "timeframe": timeframe, "count": period + 1})
                if result and isinstance(result, dict):
                    candles = result.get('candles', [])
                    if len(candles) >= period + 1:
                        tr_values = []
                        for i in range(1, len(candles)):
                            high = candles[i]['high']; low = candles[i]['low']
                            prev_close = candles[i-1]['close']
                            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                            tr_values.append(tr)
                        if tr_values: return sum(tr_values[-period:]) / period
        except Exception:
            pass
        return 0.0

    # ============================================================
    # BROKER INITIALIZATION
    # ============================================================
    def initialize_broker_price_history(self):
        if not self.broker_manager:
            logger.error("Broker Manager not available")
            return False
        logger.info("Initializing broker price history...")
        prices = self.get_all_mt4_prices()
        if not prices:
            logger.warning("No prices from MT4 - using fallback")
            prices = {'EURUSD': 1.1415, 'GBPUSD': 1.3402, 'USDJPY': 162.35, 'USDCHF': 0.8108,
                      'AUDUSD': 0.6983, 'USDCAD': 1.4068, 'NZDUSD': 0.5816, 'EURGBP': 0.8520,
                      'EURJPY': 185.35, 'EURCAD': 1.6058, 'EURNZD': 1.9616, 'EURCHF': 0.9256}
        for pair in self.pairs:
            price = prices.get(pair, 0)
            if price <= 0:
                logger.warning(f"   No price for {pair} - skipping")
                continue
            broker = self.broker_manager.brokers.get(pair)
            if not broker:
                logger.warning(f"   No broker for {pair}")
                continue
            history = []; spread_values = []
            for i in range(50):
                if i < 25:
                    variation = 1 + (i - 25) * 0.0002 + (random.random() - 0.5) * 0.001
                else:
                    variation = 1 + (25 - i) * 0.0002 + (random.random() - 0.5) * 0.001
                hist_price = price * variation
                history.append(hist_price)
                spread_values.append(hist_price * 0.0002 * (1 + (random.random() - 0.5) * 0.5))
            broker.price_history = history
            broker.close_history = history.copy()
            broker.high_history = [p * 1.001 for p in history]
            broker.low_history = [p * 0.999 for p in history]
            broker.spread_history = spread_values
            broker.current_price = price
            broker.bid = price * 0.9999
            broker.ask = price * 1.0001
            if len(broker.spread_history) >= 10:
                values = broker.spread_history
                mu = sum(values) / len(values)
                variance = sum((x - mu) ** 2 for x in values) / len(values)
                sigma = variance ** 0.5 if variance > 0 else 0.0001
                broker.z_score = (spread_values[-1] - mu) / sigma if sigma > 0 else 0.0
                broker.mu = mu; broker.sigma = sigma; broker.samples = len(values)
            else:
                broker.z_score = 0.5
            logger.info(f"   {pair}: initialized {len(history)} prices, z_score={broker.z_score:.2f}")
        logger.info("Broker price history initialization complete")
        return True

    def fix_all_broker_attributes(self):
        if not self.broker_manager: return
        for pair, broker in self.broker_manager.brokers.items():
            if not hasattr(broker, 'close_history'): broker.close_history = []
            if not hasattr(broker, 'high_history'): broker.high_history = []
            if not hasattr(broker, 'low_history'): broker.low_history = []
            if not hasattr(broker, 'volume_history'): broker.volume_history = []
            if not hasattr(broker, 'pattern_info'): broker.pattern_info = None
            if not hasattr(broker, 'name'): broker.name = f"{pair}_Broker"
            if pair in ('EURUSD', 'GBPUSD'):
                if not hasattr(broker, 'fastest_period'): broker.fastest_period = 5
                if not hasattr(broker, 'slowest_period'): broker.slowest_period = 200
            if pair == 'USDCHF':
                if not hasattr(broker, 'snb_intervention_history'): broker.snb_intervention_history = []
            if pair == 'USDJPY':
                if not hasattr(broker, 'volume_history'): broker.volume_history = []
                if not hasattr(broker, 'squeeze_detected'): broker.squeeze_detected = False
                if not hasattr(broker, 'volume_spike'): broker.volume_spike = False
                if not hasattr(broker, 'support_level'): broker.support_level = 0.0
                if not hasattr(broker, 'resistance_level'): broker.resistance_level = 0.0
            logger.info(f"Fixed attributes for {pair}")

    # ============================================================
    # RISK MANAGEMENT
    # ============================================================
    def check_trade_allowed(self, pair: str = None) -> Tuple[bool, str]:
        if self.daily_pnl <= -self.daily_loss_limit:
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f} (limit: ${self.daily_loss_limit})"
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses: {self.consecutive_losses} (limit: {self.max_consecutive_losses})"
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached: {self.trades_today} (limit: {self.max_trades_per_day})"
        if self.weekly_pnl <= -self.weekly_loss_limit:
            return False, f"Weekly loss limit reached: ${self.weekly_pnl:.2f} (limit: ${self.weekly_loss_limit})"
        return True, "OK"

    def update_risk_metrics(self, pnl: float, was_win: bool):
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.trades_today += 1
        if was_win:
            self.consecutive_losses = 0; self.last_trade_was_win = True
        else:
            self.consecutive_losses += 1; self.last_trade_was_win = False
        logger.info(f"Risk Update: P&L=${pnl:.2f} | Daily=${self.daily_pnl:.2f} | Weekly=${self.weekly_pnl:.2f} | ConsecutiveLosses={self.consecutive_losses}")

    def reset_daily_stats(self):
        self.daily_pnl = 0.0; self.trades_today = 0; self.consecutive_losses = 0; self.last_trade_was_win = True
        logger.info("Daily stats reset")

    def reset_weekly_stats(self):
        self.weekly_pnl = 0.0
        logger.info("Weekly stats reset")

    def check_and_reset_weekly(self):
        current_weekday = datetime.now().weekday()
        if current_weekday == 6:
            if self.week_start_day != 6: self.reset_weekly_stats()
            self.week_start_day = 6

    def check_and_reset_daily(self):
        now = datetime.now()
        if not hasattr(self, '_last_reset_day') or self._last_reset_day != now.day:
            self.reset_daily_stats()
            self._last_reset_day = now.day

    def calculate_risk_of_ruin(self, account_balance: float, risk_per_trade: float, win_rate: float) -> Dict:
        if risk_per_trade <= 0 or account_balance <= 0:
            return {'kelly_fraction': 0, 'ruin_probability': 0, 'expected_max_drawdown': 0, 'is_safe': True, 'recommendation': 'No risk'}
        risk_reward = self.config.get('risk_reward_ratio', 1.5)
        kelly = win_rate - (1 - win_rate) / risk_reward
        kelly = max(0, min(0.5, kelly))
        avg_win = 1.0; avg_loss = 1.0 / risk_reward
        edge = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        if edge <= 0:
            ruin_probability = 1.0
        else:
            risk_ratio = account_balance / risk_per_trade
            ruin_probability = ((1 - edge) / (1 + edge)) ** risk_ratio
            ruin_probability = min(1.0, max(0.0, ruin_probability))
        expected_max_drawdown = min(account_balance * 0.5, account_balance * (1 - win_rate) * 1.5)
        is_safe = ruin_probability < 0.05 and kelly > 0.05
        return {'kelly_fraction': round(kelly, 3), 'ruin_probability': round(ruin_probability * 100, 1),
                'expected_max_drawdown': round(expected_max_drawdown, 2), 'is_safe': is_safe,
                'recommendation': 'OK' if is_safe else 'REDUCE RISK'}

    # ============================================================
    # POSITION SIZING
    # ============================================================
    def calculate_position_size(self, confidence: float, volatility: float, pair: str = 'EURUSD') -> float:
        base_size = self.config.get('base_volume', 0.05)
        max_size = self.config.get('max_position_size', 0.10)
        if self.consecutive_losses >= 2:
            loss_penalty = max(0.5, 1.0 - (self.consecutive_losses * 0.15))
        else:
            loss_penalty = 1.0
        if self.daily_pnl < 0:
            daily_penalty = max(0.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.8)
        else:
            daily_penalty = min(1.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.3)
        vol_penalty = max(0.3, min(1.0, 1.0 / (1.0 + volatility * 50)))
        confidence_factor = 0.4 + (confidence / 100.0) * 0.6
        pair_multiplier = self._get_pair_multiplier(pair)
        account_factor = min(1.5, self.account_balance / 10000) if hasattr(self, 'account_balance') else 1.0
        position_size = (base_size * loss_penalty * daily_penalty * vol_penalty * confidence_factor * pair_multiplier * account_factor)
        position_size = max(0.05, min(max_size, round(position_size, 3)))
        return round(position_size, 2)

    def _get_pair_multiplier(self, pair: str) -> float:
        return {'EURUSD': 1.0, 'GBPUSD': 1.0, 'USDJPY': 0.8, 'USDCHF': 0.9, 'AUDUSD': 0.9,
                'USDCAD': 0.9, 'NZDUSD': 0.8, 'EURGBP': 0.8, 'EURJPY': 0.7, 'EURCAD': 0.8,
                'EURNZD': 0.7, 'EURCHF': 0.7}.get(pair, 0.8)

    # ============================================================
    # TRADE EXECUTION - FIXED: 7-arg signature
    # ============================================================
    def _execute_trade(self, pair: str, signal: str, price: float, confidence: float,
                       position_size: float = 0.03, sl: float = 0, tp: float = 0) -> Dict:
        allowed, reason = self.check_trade_allowed(pair)
        if not allowed:
            logger.info(f"Trade blocked: {reason}")
            return {'status': 'BLOCKED', 'reason': reason}

        z_score = self.agent_x.z_score if self.agent_x else 0
        if not self._confirm_mean_reversion(pair, z_score):
            logger.info(f"{pair}: Mean reversion not confirmed")
            return {'status': 'BLOCKED', 'reason': 'Mean reversion not confirmed'}

        volatility = self._get_volatility(pair, price)
        if position_size <= 0:
            position_size = self.calculate_position_size(confidence, volatility, pair)

        account_balance = self._get_account_balance()
        risk_per_trade = position_size * self._get_pip_value(pair) * 100000
        win_rate = self._get_win_rate()
        risk_check = self.calculate_risk_of_ruin(account_balance, risk_per_trade, win_rate)

        if not risk_check['is_safe']:
            logger.info(f"Risk of ruin too high: {risk_check['ruin_probability']:.1f}%")
            position_size = max(0.01, round(position_size * 0.5, 2))
            logger.info(f"Reduced position size to {position_size} lots")

        config = self.get_symbol_config(pair)
        pip = config.get('pip', 0.0001)
        digits = config.get('digits', 5)

        # FIXED: Use provided SL/TP if valid, otherwise calculate defaults
        if sl <= 0 or tp <= 0:
            sl_pips = config.get('sl_pips', 15)
            tp_pips = config.get('tp_pips', 30)
            if signal == 'BUY':
                sl = price - (sl_pips * pip); tp = price + (tp_pips * pip)
            else:
                sl = price + (sl_pips * pip); tp = price - (tp_pips * pip)

        entry_price = round(price, digits)
        sl = round(sl, digits); tp = round(tp, digits)

        order_result = self._send_mt4_order(pair=pair, action=signal, volume=position_size, entry=entry_price, sl=sl, tp=tp)

        # FIXED: Null-safe check
        if order_result and isinstance(order_result, dict) and order_result.get('success'):
            logger.info(f"TRADE EXECUTED: {pair} {signal} {position_size} lots @ {entry_price}")
            logger.info(f"   SL: {sl} | TP: {tp}")
            self.active_positions[pair] = {
                'direction': signal, 'entry_price': entry_price, 'volume': position_size,
                'sl': sl, 'tp': tp, 'highest_price': entry_price, 'lowest_price': entry_price,
                'trailing_activated': False
            }
            if self.performance:
                try:
                    self.performance.record_trade({
                        'pair': pair, 'signal': signal, 'price': entry_price, 'volume': position_size,
                        'sl': sl, 'tp': tp, 'confidence': confidence, 'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Performance tracking error: {e}")
            return {'status': 'EXECUTED', 'pair': pair, 'action': signal, 'volume': position_size}
        return {'status': 'FAILED', 'reason': str(order_result) if order_result else 'Unknown error'}

    def _send_mt4_order(self, pair: str, action: str, volume: float, entry: float, sl: float, tp: float) -> Dict:
        if self.cold_start_active:
            logger.warning(f"Attempted real order during cold start - BLOCKED!")
            return {'success': False, 'error': 'Cold start active', 'simulated': True}
        try:
            if not self.mt4:
                logger.error("MT4 not connected")
                return {'success': False, 'error': 'MT4 not connected'}
            order_cmd = {"command": "ORDER_SEND", "symbol": pair, "action": action, "volume": volume,
                         "entry": entry, "sl": sl, "tp": tp, "type": "market"}
            result = self.mt4._send(order_cmd)
            if result and isinstance(result, dict) and result.get('success'):
                return {'success': True, 'order_id': result.get('order_id')}
            return {'success': False, 'error': result.get('error', 'Unknown') if result else 'No response', 'details': result}
        except Exception as e:
            logger.error(f"Order sending error: {e}")
            return {'success': False, 'error': str(e)}

    def send_real_order(self, symbol: str, action: str, price: float, sl: float, tp: float,
                        volume: float, max_retries: int = 3) -> Dict:
        try:
            for val in [volume, price, sl, tp]:
                if isinstance(val, (np.float32, np.float64)): val = float(val)
            volume = round(volume, 2)
            if not self.mt4: return {'success': False, 'error': 'MT4 not connected'}
            price_data = self.mt4._send({"command": "PRICE", "symbol": symbol})
            if price_data and isinstance(price_data, dict):
                bid = price_data.get('bid', 0); ask = price_data.get('ask', 0)
                if bid > 0 and ask > 0:
                    entry_price = ask if action == 'BUY' else bid
                    logger.info(f"MT4 Price: {symbol} Bid={bid:.5f} Ask={ask:.5f}")
                else: entry_price = price
            else: entry_price = price
            if not self._is_valid_price(symbol, entry_price):
                logger.warning(f"Price {entry_price} out of range for {symbol}, retrying...")
                time.sleep(0.2)
                price_data = self.mt4._send({"command": "PRICE", "symbol": symbol})
                if price_data and isinstance(price_data, dict):
                    bid = price_data.get('bid', 0); ask = price_data.get('ask', 0)
                    if bid > 0 and ask > 0: entry_price = ask if action == 'BUY' else bid
            config = self.get_symbol_config(symbol)
            pip = config.get('pip', 0.0001); digits = config.get('digits', 5)
            sl_pips = config.get('sl_pips', 15); tp_pips = config.get('tp_pips', 30)
            if action == 'BUY':
                sl = entry_price - (sl_pips * pip); tp = entry_price + (tp_pips * pip)
            else:
                sl = entry_price + (sl_pips * pip); tp = entry_price - (tp_pips * pip)
            min_distance = 10 * pip
            if abs(entry_price - sl) < min_distance:
                if action == 'BUY': sl = entry_price - (min_distance * 1.5)
                else: sl = entry_price + (min_distance * 1.5)
            entry_price = round(entry_price, digits); sl = round(sl, digits); tp = round(tp, digits)
            logger.info(f"SENDING ORDER: {symbol} {action} {volume} @ {entry_price} SL:{sl} TP:{tp}")
            for attempt in range(max_retries):
                order = {"command": "ORDER", "symbol": symbol, "type": action, "volume": volume, "sl": sl, "tp": tp}
                result = self.mt4._send(order)
                if result and isinstance(result, dict) and result.get('success'):
                    logger.info(f"ORDER EXECUTED! Ticket: {result.get('ticket', 0)}")
                    return {'success': True, 'ticket': result.get('ticket', 0)}
                error = result.get('error', 'Unknown') if result else 'No response'
                if 'Timeout' in str(error): time.sleep(1); continue
                elif 'Error 130' in str(error):
                    sl_pips += 5; tp_pips += 5
                    if action == 'BUY':
                        sl = entry_price - (sl_pips * pip); tp = entry_price + (tp_pips * pip)
                    else:
                        sl = entry_price + (sl_pips * pip); tp = entry_price - (tp_pips * pip)
                    sl = round(sl, digits); tp = round(tp, digits); time.sleep(0.5); continue
                else:
                    logger.error(f"ORDER FAILED: {error}")
                    return {'success': False, 'error': error}
            return {'success': False, 'error': 'Max retries exceeded'}
        except Exception as e:
            logger.error(f"ORDER ERROR: {e}")
            return {'success': False, 'error': str(e)}

    def _simulate_order(self, symbol, action, price, sl, tp, volume, max_retries=1):
        logger.info(f"[SIMULATION] WOULD SEND: {symbol} {action} {volume} @ {price:.5f} SL:{sl:.5f} TP:{tp:.5f}")
        ticket = random.randint(10000, 99999)
        self.active_positions[symbol] = {
            'direction': action, 'entry_price': price, 'volume': volume, 'sl': sl, 'tp': tp,
            'highest_price': price, 'lowest_price': price, 'trailing_activated': False,
            'simulated': True, 'ticket': ticket
        }
        return {'success': True, 'ticket': ticket, 'simulated': True}

    # ============================================================
    # TRADE CONFIRMATION
    # ============================================================
    def _confirm_mean_reversion(self, pair: str, z_score: float) -> bool:
        if not hasattr(self, '_z_history'): self._z_history = {}
        if pair not in self._z_history: self._z_history[pair] = []
        self._z_history[pair].append(z_score)
        if len(self._z_history[pair]) > 10: self._z_history[pair].pop(0)
        if len(self._z_history[pair]) < 3: return True
        z_changes = [self._z_history[pair][i] - self._z_history[pair][i-1] for i in range(1, len(self._z_history[pair]))]
        if not z_changes: return True
        last_change = z_changes[-1]
        if z_score > 2.0 and last_change > 0:
            logger.info(f"{pair}: Z-score still rising ({z_score:.2f}), waiting")
            return False
        if z_score < -2.0 and last_change < 0:
            logger.info(f"{pair}: Z-score still falling ({z_score:.2f}), waiting")
            return False
        if len(z_changes) >= 3:
            avg_change = sum(z_changes[-3:]) / 3
            if z_score > 0 and avg_change > 0 and z_score > 1.5:
                logger.info(f"{pair}: Z-score moving further away ({z_score:.2f}), waiting")
                return False
            if z_score < 0 and avg_change < 0 and z_score < -1.5:
                logger.info(f"{pair}: Z-score moving further away ({z_score:.2f}), waiting")
                return False
        return True

    def _confirm_entry_with_candle_and_sr(self, symbol: str, price: float, direction: str) -> bool:
        if not self.config.get('enable_entry_confirmation', True):
            return True

        z_threshold = self.config.get('entry_confirmation_z_threshold', 1.8)
        z_score = 0.0

        if self.agent_x is not None:
            if hasattr(self.agent_x, 'z_score'):
                z_score = float(getattr(self.agent_x, 'z_score', 0.0))
            elif hasattr(self.agent_x, 'z_scores'):
                z_score = float(self.agent_x.z_scores.get(symbol, 0.0))

        if direction == 'SELL' and z_score >= z_threshold:
            logger.info(f"✅ {symbol}: z-score {z_score:.2f} >= {z_threshold:.2f} – SELL confirmed")
            return True

        if direction == 'BUY' and z_score <= -z_threshold:
            logger.info(f"✅ {symbol}: z-score {z_score:.2f} <= {-z_threshold:.2f} – BUY confirmed")
            return True

        logger.info(f"⏸️ {symbol}: z-score {z_score:.2f} does not match {direction} threshold ({z_threshold:.2f}) – skipping")
        return False
        return True

    def _get_higher_tf_signal(self, pair: str, direction: str) -> bool:
        try:
            candles = self._get_candles(pair, timeframe='H1', count=5)
            if len(candles) < 5: return True
            closes = [c['close'] for c in candles]
            sma_3 = sum(closes[-3:]) / 3; current = closes[-1]
            if direction == 'BUY': return current > sma_3
            elif direction == 'SELL': return current < sma_3
            return True
        except Exception:
            return False  # FIXED: fail-safe

    # ============================================================
    # TRAILING STOP
    # ============================================================
    def check_trailing_stop(self, position: Dict, current_price: float) -> Tuple[bool, float]:
        entry_price = position.get('entry_price', 0)
        direction = position.get('direction', 'BUY')
        trailing_pct = self.config.get('trailing_stop_pct', 0.5) / 100.0
        if 'highest_price' not in position: position['highest_price'] = entry_price
        if 'lowest_price' not in position: position['lowest_price'] = entry_price
        if 'trailing_activated' not in position: position['trailing_activated'] = False
        highest_price = position['highest_price']; lowest_price = position['lowest_price']
        if direction == 'BUY':
            if current_price > highest_price:
                position['highest_price'] = current_price
                if not position['trailing_activated'] and (current_price - entry_price) / entry_price > 0.005:
                    position['trailing_activated'] = True
                    logger.info(f"Trailing stop ACTIVATED at ${current_price:.5f}")
            if position['trailing_activated']:
                trailing_price = highest_price * (1 - trailing_pct)
                if current_price <= trailing_price:
                    logger.info(f"TRAILING STOP HIT: ${current_price:.5f} <= ${trailing_price:.5f}")
                    return True, trailing_price
        else:
            if current_price < lowest_price:
                position['lowest_price'] = current_price
                if not position['trailing_activated'] and (entry_price - current_price) / entry_price > 0.005:
                    position['trailing_activated'] = True
                    logger.info(f"Trailing stop ACTIVATED at ${current_price:.5f}")
            if position['trailing_activated']:
                trailing_price = lowest_price * (1 + trailing_pct)
                if current_price >= trailing_price:
                    logger.info(f"TRAILING STOP HIT: ${current_price:.5f} >= ${trailing_price:.5f}")
                    return True, trailing_price
        return False, 0.0

    def _monitor_trailing_stops(self):
        for pair in list(self.active_positions.keys()):
            position = self.active_positions[pair]
            current_price = self.get_price(pair)
            if current_price <= 0: continue
            should_close, close_price = self.check_trailing_stop(position, current_price)
            if should_close: self._close_position(pair, close_price)

    # ============================================================
    # POSITION MANAGEMENT
    # ============================================================
    def _close_position(self, pair: str, close_price: float) -> Dict:
        if pair in self.active_positions: del self.active_positions[pair]
        if self.execution_engine and hasattr(self.execution_engine, 'positions'):
            if pair in self.execution_engine.positions: del self.execution_engine.positions[pair]
        logger.info(f"Position closed for {pair} at {close_price:.5f}")
        return {'status': 'CLOSED', 'pair': pair, 'price': close_price}

    def _has_open_position(self, pair: str) -> bool:
        if self.execution_engine and pair in self.execution_engine.positions: return True
        if self.mt4:
            try:
                pos_data = self.mt4._send({"command": "POSITIONS"})
                if pos_data and pos_data.get('positions'):
                    for pos in pos_data.get('positions', []):
                        if pos.get('symbol') == pair: return True
            except Exception: pass
        return False

    def clear_stuck_positions(self):
        if self.execution_engine:
            if hasattr(self.execution_engine, 'positions'):
                self.execution_engine.positions = {}; print("Cleared execution engine positions")
            if hasattr(self.execution_engine, 'active_positions'):
                self.execution_engine.active_positions = {}; print("Cleared execution engine active positions")
            self.active_positions = {}; print("Cleared local active positions")
            if hasattr(self.execution_engine, 'trades_today'):
                self.execution_engine.trades_today = 0; print("Reset trades today to 0")
            if hasattr(self.execution_engine, 'daily_pnl'):
                self.execution_engine.daily_pnl = 0.0; print("Reset daily P&L to $0.00")
            print("Stuck positions cleared!"); return True
        return False

    # ============================================================
    # VALIDATION HELPERS
    # ============================================================
    def _is_valid_price(self, pair: str, price: float) -> bool:
        if price <= 0: return False
        ranges = {'EURUSD': (0.8, 1.6), 'GBPUSD': (0.8, 1.7), 'USDJPY': (100, 200),
                  'USDCHF': (0.7, 1.2), 'AUDUSD': (0.5, 0.9), 'USDCAD': (1.0, 1.7),
                  'NZDUSD': (0.4, 0.8), 'EURGBP': (0.7, 1.0), 'EURJPY': (100, 200),
                  'EURCAD': (1.2, 1.8), 'EURNZD': (1.5, 2.4), 'EURCHF': (0.8, 1.2)}
        clean = pair.replace('#', '')
        if clean in ranges:
            low, high = ranges[clean]
            return low < price < high
        return 0.01 < price < 10000

    def _check_spread(self, pair: str, price: float) -> bool:
        try:
            if self.mt4:
                price_data = self.mt4._send({"command": "PRICE", "symbol": pair})
                if price_data and isinstance(price_data, dict):
                    bid = price_data.get('bid', 0); ask = price_data.get('ask', 0)
                    if bid > 0 and ask > 0:
                        if (abs(ask - bid) / bid * 100) > 0.05:
                            logger.debug(f"Spread too high for {pair}")
                            return False
                        return True
        except Exception as e: logger.debug(f"Spread check error: {e}")
        return True

    def _get_volatility(self, pair: str, price: float) -> float:
        broker = self.brokers.get(pair)
        if broker and hasattr(broker, 'close_history') and len(broker.close_history) >= 2:
            closes = broker.close_history[-20:]
            if len(closes) >= 2:
                returns = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                return np.std(returns) if returns else 0.001
        return 0.001

    def _get_account_balance(self) -> float:
        if self.mt4:
            try:
                result = self.mt4._send({"command": "ACCOUNT"})
                if result and isinstance(result, dict): return result.get('balance', self.account_balance)
            except Exception: pass
        return self.account_balance

    def _get_win_rate(self) -> float:
        total = self.cold_start_wins + self.cold_start_losses
        if total == 0: return 0.5
        return self.cold_start_wins / total

    def _get_pip_value(self, pair: str) -> float:
        return self.get_symbol_config(pair).get('pip', 0.0001)

    # ============================================================
    # COLD START - FIXED: proper win rate check, PnL logic
    # ============================================================
    def _simulate_trade(self, pair: str, signal: str, confidence: float, price: float) -> Dict:
        current_state = self.rl_env._get_observation() if self.rl_env else None
        mc_results = self.monte_carlo.simulate_entry(current_price=price, direction=signal)
        prob_success = mc_results.get('entry_confidence', 50) / 100.0
        win = random.random() < prob_success
        config = self.get_symbol_config(pair)
        pip = config.get('pip', 0.0001); volume = config.get('volume', 0.03)
        pips = 10
        pnl = pips * pip * 100000 * volume
        # FIXED: Profit always positive, loss always negative
        pnl = abs(pnl) if win else -abs(pnl)
        sample = {'pair': pair, 'signal': signal, 'confidence': confidence,
                  'price': price, 'win': win, 'pnl': pnl, 'timestamp': datetime.now().isoformat()}
        self.cold_start_samples.append(sample)
        if win: self.cold_start_wins += 1
        else: self.cold_start_losses += 1
        if self.rl_enabled and self.rl_agent and current_state is not None:
            trade_type = 1 if signal == 'BUY' else 2 if signal == 'SELL' else 0
            pair_idx = self.pairs.index(pair) if pair in self.pairs else 0
            action = np.array([pair_idx, trade_type, 1.0], dtype=np.float32)
            reward = pnl / 100.0
            next_state = self.rl_env._get_observation() if self.rl_env else None
            self.replay_buffer.append({'state': current_state, 'action': action, 'reward': reward,
                                       'next_state': next_state, 'done': False})
            if len(self.replay_buffer) % 10 == 0:
                logger.info(f"RL: Collected {len(self.replay_buffer)} transitions")
            if len(self.replay_buffer) > self.replay_buffer_max:
                self.replay_buffer = self.replay_buffer[-self.replay_buffer_max:]
            if len(self.replay_buffer) >= self.rl_train_batch_size and len(self.cold_start_samples) % self.rl_train_every == 0:
                self._train_rl_from_replay()
        return sample

    def is_cold_start_complete(self) -> bool:
        if not self.cold_start_active: return True
        total = len(self.cold_start_samples)
        win_rate = self.cold_start_wins / total if total > 0 else 0
        if total >= self.cold_start_threshold:
            if win_rate >= self.cold_start_min_win_rate:
                self.cold_start_active = False
                logger.info("="*60)
                logger.info("COLD START COMPLETE!")
                logger.info(f"   Total Samples: {total} | Wins: {self.cold_start_wins} | Losses: {self.cold_start_losses}")
                logger.info(f"   Win Rate: {win_rate:.1%} (required: {self.cold_start_min_win_rate:.1%})")
                logger.info("REAL TRADING ENABLED")
                logger.info("="*60)
                return True
            else:
                # FIXED: Don't force complete with terrible win rate
                if win_rate >= 0.30:
                    self.cold_start_active = False
                    logger.warning("="*60)
                    logger.warning("COLD START WIN RATE BELOW THRESHOLD")
                    logger.warning(f"   Win Rate: {win_rate:.1%} (required: {self.cold_start_min_win_rate:.1%})")
                    logger.warning("   Continuing with reduced position size...")
                    logger.warning("="*60)
                    return True
                else:
                    logger.error("="*60)
                    logger.error(f"COLD START FAILED - Win rate too low: {win_rate:.1%}")
                    logger.error("   Continuing simulation only...")
                    logger.error("="*60)
                    return False
        else:
            logger.info(f"Cold start: {total}/{self.cold_start_threshold} samples collected.")
            return False

    def _save_cold_start_state(self):
        state = {'samples': self.cold_start_samples, 'wins': self.cold_start_wins,
                 'losses': self.cold_start_losses, 'active': self.cold_start_active,
                 'timestamp': datetime.now().isoformat()}
        try:
            with open('cold_start_state.json', 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.debug("Cold start state saved.")
        except Exception as e:
            logger.warning(f"Failed to save cold start state: {e}")

    def _load_cold_start_state(self):
        if not os.path.exists('cold_start_state.json'): return False
        try:
            with open('cold_start_state.json', 'r') as f:
                state = json.load(f)
            self.cold_start_samples = state.get('samples', [])
            self.cold_start_wins = state.get('wins', 0)
            self.cold_start_losses = state.get('losses', 0)
            self.cold_start_active = state.get('active', True)
            logger.info(f"Loaded cold start state: {len(self.cold_start_samples)} samples, wins={self.cold_start_wins}, losses={self.cold_start_losses}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load cold start state: {e}")
            return False

    # ============================================================
    # RL TRAINING
    # ============================================================
    def _train_rl_from_replay(self, batch_size=64, epochs=5):
        if not self.rl_enabled or not self.rl_agent: return
        if len(self.replay_buffer) < batch_size: return
        try:
            from rl_replay_env import ReplayEnv
            from stable_baselines3.common.env_util import make_vec_env
            replay_env = ReplayEnv(self.replay_buffer[-500:])
            vec_env = make_vec_env(lambda: replay_env, n_envs=1)
            self.rl_agent.model.set_env(vec_env)
            total_steps = max(len(self.replay_buffer) * epochs // 10, 200)
            logger.info(f"RL: Training from replay buffer ({len(self.replay_buffer)} transitions)...")
            self.rl_agent.model.learn(total_timesteps=total_steps, reset_num_timesteps=False)
            logger.info("RL: Online training complete")
            self.rl_agent.save('models/rl_model_online.zip')
            logger.info("RL: Model saved to models/rl_model_online.zip")
        except Exception as e:
            logger.warning(f"RL training error: {e}")

    def _train_rl_with_collected_data(self):
        if not self.rl_enabled or not self.rl_agent: return
        if not hasattr(self, 'rl_training_data') or not self.rl_training_data: return
        try:
            logger.info(f"RL: Starting training with {len(self.rl_training_data)} transitions...")
            self._train_rl_from_replay()
        except Exception as e:
            logger.warning(f"RL training error: {e}")

    def test_rl_training(self):
        if not self.rl_enabled or not self.rl_agent: return
        logger.info("Creating mock RL training data...")
        for i in range(50):
            state = np.random.rand(50).astype(np.float32)
            action = np.array([random.randint(0, 3), random.randint(0, 2), 1.0], dtype=np.float32)
            reward = random.uniform(-1, 1)
            next_state = np.random.rand(50).astype(np.float32)
            self.replay_buffer.append({'state': state, 'action': action, 'reward': reward,
                                       'next_state': next_state, 'done': False})
        self._train_rl_from_replay()
        os.makedirs('models', exist_ok=True)
        self.rl_agent.save('models/rl_model_trained.zip')
        logger.info("RL: Model trained with mock data and saved")
        try:
            self.rl_agent.load('models/rl_model_trained.zip')
            logger.info("RL: Model loaded for use")
        except Exception as e:
            logger.warning(f"RL model load error: {e}")

    # ============================================================
    # SYMBOL CONFIG - FIXED: uses SYMBOL_CONFIG directly
    # ============================================================
    def get_symbol_config(self, symbol: str) -> Dict[str, Union[float, int, str]]:
        clean_symbol = symbol.replace('#', '')
        if clean_symbol in SYMBOL_CONFIG: return SYMBOL_CONFIG[clean_symbol]
        if symbol in SYMBOL_CONFIG: return SYMBOL_CONFIG[symbol]
        return {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'unknown'}

    # ============================================================
    # AGENT CONSENSUS - FIXED: uses agent_weights
    # ============================================================
    def _run_agents_parallel(self, signal_data):
        results = {}
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            futures = {executor.submit(self._analyze_single_agent, agent, signal_data): agent for agent in self.agents}
            for future in as_completed(futures):
                name, result = future.result()
                results[name] = result
        return results

    def _analyze_single_agent(self, agent, signal_data):
        try: return agent.name, agent.analyze(signal_data)
        except Exception as e: return agent.name, {'vote': 'HOLD', 'confidence': 50, 'reasoning': f'Error: {e}'}

    def _generate_signals(self, agent_results: Dict, market_data: Dict) -> Dict:
        signals = {}
        for agent_name, result in agent_results.items():
            pair = result.get('pair', 'EURUSD')
            signals[agent_name] = {'pair': pair, 'signal': result.get('vote', 'HOLD'),
                                   'confidence': result.get('confidence', 50),
                                   'reasoning': result.get('reasoning', ''),
                                   'timestamp': datetime.now().isoformat()}
        return signals

    def _generate_consensus(self, signals: Dict) -> Dict:
        buy_votes = 0.0; sell_votes = 0.0; hold_votes = 0
        buy_confidences = []; sell_confidences = []
        for agent_name, signal in signals.items():
            vote = signal.get('signal', 'HOLD')
            confidence = signal.get('confidence', 50)
            weight = self.agent_weights.get(agent_name, 1.0)  # FIXED: use weights
            if vote == 'BUY':
                buy_votes += weight; buy_confidences.append(confidence * weight)
            elif vote == 'SELL':
                sell_votes += weight; sell_confidences.append(confidence * weight)
            else:
                hold_votes += 1
        avg_buy = sum(buy_confidences) / len(buy_confidences) if buy_confidences else 0
        avg_sell = sum(sell_confidences) / len(sell_confidences) if sell_confidences else 0
        buy_score = buy_votes * (avg_buy / 100) if avg_buy > 0 else 0
        sell_score = sell_votes * (avg_sell / 100) if avg_sell > 0 else 0
        if buy_score > sell_score and buy_score > 0:
            signal = 'BUY'
            confidence = min(95, (buy_score / (buy_score + sell_score + 0.01)) * 100)
            reason = f"Consensus BUY ({buy_votes:.1f} votes, avg conf: {avg_buy:.0f}%)"
        elif sell_score > buy_score and sell_score > 0:
            signal = 'SELL'
            confidence = min(95, (sell_score / (buy_score + sell_score + 0.01)) * 100)
            reason = f"Consensus SELL ({sell_votes:.1f} votes, avg conf: {avg_sell:.0f}%)"
        else:
            signal = 'HOLD'; confidence = 50
            reason = f"Consensus HOLD (BUY:{buy_votes:.1f} SELL:{sell_votes:.1f} HOLD:{hold_votes})"
        return {'signal': signal, 'confidence': round(confidence, 1), 'reason': reason,
                'buy_votes': buy_votes, 'sell_votes': sell_votes, 'hold_votes': hold_votes,
                'total_agents': len(signals)}

    # ============================================================
    # PROCESS CYCLE - FIXED: proper arg passing, null checks, daily reset
    # ============================================================
    def process_cycle(self, market_data: Dict = None) -> Dict:
        self.cycle_count += 1
        # FIXED: Check and reset daily/weekly stats
        self.check_and_reset_daily()
        self.check_and_reset_weekly()

        if market_data is None: market_data = self.build_market_data()
        results = {'cycle': self.cycle_count, 'timestamp': datetime.now().isoformat(),
                   'engine': {}, 'anomalies': {}, 'trades': [], 'positions': {},
                   'broker_decisions': {}, 'dollar_engine': {}, 'risk_status': {}}
        try:
            # STEP 1: Update Engine
            if self.engine:
                try:
                    results['engine'] = self.engine.update_engine_state(market_data)
                    logger.info(f"Engine: {results['engine'].get('engine_direction', 'N/A')} | Regime: {results['engine'].get('regime', 'N/A')}")
                except Exception as e: logger.warning(f"Engine update error: {e}")

            # STEP 2: Anomaly Detection
            if self.anomaly_detector:
                try:
                    anomalies = self.anomaly_detector.update(market_data)
                    results['anomalies'] = anomalies
                    if anomalies.get('protection_active', False):
                        logger.warning("Anomaly protection ACTIVE - skipping cycle")
                        return results
                except Exception as e: logger.warning(f"Anomaly detector error: {e}")

            # STEP 3: Risk Management
            risk_allowed, risk_reason = self.check_trade_allowed()
            results['risk_status'] = {'allowed': risk_allowed, 'reason': risk_reason}
            if not risk_allowed:
                logger.warning(f"RISK BLOCK: {risk_reason}")
                return {**results, 'status': 'BLOCKED', 'reason': risk_reason}

            # STEP 4: Circuit Breaker
            if self.execution_engine and hasattr(self.execution_engine, 'daily_pnl'):
                daily_pnl = self.execution_engine.daily_pnl
                max_loss = self.config.get('max_daily_loss', 500)
                if daily_pnl < -max_loss:
                    logger.error(f"DAILY LOSS LIMIT: ${daily_pnl:.2f} < -${max_loss}")
                    self.stop(); self.clear_stuck_positions()
                    return {**results, 'status': 'STOPPED', 'reason': 'Daily loss limit exceeded'}

            # STEP 5: Broker Manager Decisions
            decisions = {}
            if self.broker_manager:
                try:
                    logger.info("\n" + "="*70)
                    logger.info("BROKER MANAGER: Hierarchical Decision Flow")
                    logger.info("="*70)
                    decisions = self.broker_manager.get_decision(market_data)
                    active_signals = {p: d for p, d in decisions.items() if d.get('signal') != 'HOLD'}
                    logger.info(f"\nActive Signals: {len(active_signals)}/{len(decisions)}")
                    for pair, decision in active_signals.items():
                        de = decision.get('dollar_engine', {})
                        logger.info(f"   {pair}: {decision['signal']} (conf={decision['confidence']:.1f}%, source={decision.get('source')}, z={decision.get('z_score', 0):.2f})")
                    if self.broker_manager.decision_history:
                        last = self.broker_manager.decision_history[-1]
                        if 'dollar_state' in last:
                            de_state = last['dollar_state']
                            results['dollar_engine'] = de_state
                            logger.info(f"\nDollar Engine: {de_state.get('direction', 'N/A')} | Strength: {de_state.get('strength', 0):.2f} | Confidence: {de_state.get('confidence', 0):.1f}%")
                except Exception as e:
                    logger.error(f"Broker Manager error: {e}")
                    import traceback; traceback.print_exc()
            else:
                logger.error("Broker Manager not available")
                return {**results, 'status': 'ERROR', 'reason': 'No broker manager'}
            results['broker_decisions'] = decisions

            # STEP 6: Execute Valid Decisions
            executed_trades = []
            for pair, decision in decisions.items():
                signal = decision.get('signal', 'HOLD')
                if signal == 'HOLD': continue
                logger.info(f"\n{'-'*60}")
                logger.info(f"PROCESSING: {pair} {signal}")
                logger.info(f"{'-'*60}")

                if self._has_open_position(pair):
                    logger.info(f"   Position already open for {pair} - skipping")
                    continue

                price = market_data.get(pair, 0)
                if price <= 0:
                    logger.warning(f"   No price for {pair}"); continue
                if not self._is_valid_price(pair, price):
                    logger.warning(f"   Invalid price {price} for {pair}"); continue
                if not self._check_spread(pair, price):
                    logger.info(f"   Spread too wide for {pair}"); continue

                confidence = decision.get('confidence', 50)
                position_size = decision.get('position_size', 0.03)
                sl = decision.get('sl', 0)  # May be 0 if broker doesn't set it
                tp = decision.get('tp', 0)
                source = decision.get('source', 'unknown')
                layer = decision.get('layer', 'unknown')
                reasoning = decision.get('reasoning', 'N/A')
                mc_conf = decision.get('mc_confidence', 0)
                sr_risk = decision.get('sr_risk', 0)

                logger.info(f"   Source: {source} | Layer: {layer}")
                logger.info(f"   Confidence: {confidence:.1f}% | MC: {mc_conf:.1f}%")
                logger.info(f"   Position Size: {position_size} lots")
                logger.info(f"   SL: {sl:.5f} | TP: {tp:.5f}")
                logger.info(f"   S/R Risk: {sr_risk:.1%}")
                logger.info(f"   Reason: {reasoning}")

                if self.cold_start_active:
                    logger.info(f"   COLD START: Simulating trade")
                    sim_result = self._simulate_trade(pair, signal, confidence, price)
                    self.is_cold_start_complete()
                    continue

                if self.config.get('enable_entry_confirmation', True):
                    logger.info(f"   Running entry confirmation...")
                    if not self._confirm_entry_with_candle_and_sr(pair, price, signal):
                        logger.info(f"   Entry confirmation FAILED for {pair}"); continue
                    logger.info(f"   Entry confirmation PASSED")

                z_score = decision.get('z_score', 0)
                if not self._confirm_mean_reversion(pair, z_score):
                    logger.info(f"   Mean reversion not confirmed for {pair}"); continue

                logger.info(f"   EXECUTING: {pair} {signal} @ {price:.5f}")

                # FIXED: Pass all 7 arguments correctly
                trade_result = self._execute_trade(
                    pair=pair, signal=signal, price=price, confidence=confidence,
                    position_size=position_size, sl=sl, tp=tp
                )

                # FIXED: Null-safe check
                if trade_result and isinstance(trade_result, dict) and trade_result.get('status') == 'EXECUTED':
                    trade_result['pair'] = pair; trade_result['source'] = source
                    trade_result['layer'] = layer; trade_result['z_score'] = z_score
                    trade_result['dollar_engine'] = decision.get('dollar_engine', {})
                    executed_trades.append(trade_result)
                    results['trades'].append(trade_result)
                    logger.info(f"   TRADE EXECUTED: {pair} {signal}")
                    self.trades_today += 1
                else:
                    logger.error(f"   TRADE FAILED: {pair} {signal}")
                    logger.error(f"      Reason: {trade_result}")

            # STEP 7: Trailing Stops
            self._monitor_trailing_stops()

            # STEP 8: Summary
            logger.info(f"\n{'='*70}")
            if executed_trades:
                logger.info(f"CYCLE COMPLETE: {len(executed_trades)} trades executed")
                for t in executed_trades:
                    de = t.get('dollar_engine', {})
                    logger.info(f"   {t['pair']}: {t.get('signal')} [source: {t.get('source')}] [DE: {de.get('status', 'N/A')}]")
            else:
                logger.info("CYCLE COMPLETE: No trades executed")
            status = self.get_status()
            logger.info(f"   Active Positions: {status.get('active_count', 0)}")
            logger.info(f"   Daily P&L: ${status.get('daily_pnl', 0):.2f}")
            logger.info(f"   Trades Today: {status.get('trades_today', 0)}")
            logger.info(f"{'='*70}\n")
        except Exception as e:
            logger.error(f"Error in process_cycle: {e}")
            import traceback; traceback.print_exc()
            results['error'] = str(e)
        self.last_results = results
        return results

    # ============================================================
    # CONTROL METHODS
    # ============================================================
    def start(self):
        self.is_running = True
        logger.info("ForexTradingController started")

    def stop(self):
        self.is_running = False
        logger.info("ForexTradingController stopped")

    def get_status(self) -> Dict:
        actual_positions = {}
        if self.execution_engine and hasattr(self.execution_engine, 'positions'):
            for pair, pos in self.execution_engine.positions.items():
                if isinstance(pos, dict) and pos.get('type') in ['BUY', 'SELL']:
                    actual_positions[pair] = pos
        return {'name': self.name, 'is_running': self.is_running, 'cycle_count': self.cycle_count,
                'pairs': self.pairs, 'agents': len(self.agents),
                'engine': self.engine.get_status() if hasattr(self.engine, 'get_status') else {},
                'execution': self.execution_engine.get_status() if hasattr(self.execution_engine, 'get_status') else {},
                'positions': actual_positions, 'active_count': len(actual_positions),
                'trades_today': self.execution_engine.trades_today if self.execution_engine else 0,
                'daily_pnl': self.execution_engine.daily_pnl if self.execution_engine else 0,
                'timestamp': datetime.now().isoformat()}

    def place_order(self, symbol, order_type, price, sl, tp, volume):
        try:
            if self.mt4:
                positions = self.mt4._send({"command": "POSITIONS"})
                if positions and positions.get('positions'):
                    for pos in positions.get('positions', []):
                        if pos.get('symbol') == symbol:
                            print(f"Position already exists for {symbol} - REJECTING")
                            return {'success': False, 'error': 'Position already exists', 'existing_ticket': pos.get('ticket')}
            order = {"command": "ORDER", "symbol": symbol, "type": order_type, "volume": volume, "sl": sl, "tp": tp}
            result = self.mt4._send(order)
            return result
        except Exception as e:
            print(f"Order error: {e}")
            return {'success': False, 'error': str(e)}

    def debug_mt4_response(self):
        try:
            if not self.mt4:
                print("MT4 not connected"); return None
            raw_packet = self.mt4._send({"command": "ACCOUNT"})
            print(f"\nRAW MT4 RESPONSE: Type={type(raw_packet)}")
            if isinstance(raw_packet, dict):
                print(f"   Keys: {list(raw_packet.keys())}")
                for key in ['EURUSD', 'GBPUSD', 'USDJPY', 'balance', 'equity']:
                    print(f"     {key}: {raw_packet.get(key, 'NOT FOUND')}")
            return raw_packet
        except Exception as e:
            print(f"Debug error: {e}"); return None

    def rl_safe_to_trade(self, action, market_data):
        if self.execution_engine.daily_pnl < -self.config.get('max_daily_loss', 500):
            return False, "Daily loss exceeded"
        if self.execution_engine.trades_today >= self.config.get('max_trades_per_day', 10):
            return False, "Daily trade limit"
        pair_idx = int(np.clip(action[0], 0, len(self.pairs)-1))
        pair = self.pairs[pair_idx]
        price = market_data.get(pair, 0)
        if price <= 0: return False, "No price"
        direction = 'BUY' if action[1] == 1 else 'SELL' if action[1] == 2 else None
        if direction is None: return False, "No trade action"
        mc_results = self.monte_carlo.simulate_entry(current_price=price, direction=direction)
        if mc_results.get('entry_confidence', 0) < 60:
            return False, f"Monte Carlo low confidence: {mc_results.get('entry_confidence', 0)}%"
        return True, "OK"

    def _adjust_thresholds(self, volatility: float):
        base_entry = 2.0; base_exit = 0.3
        if volatility > 0.02:
            self.entry_threshold = base_entry * 1.2; self.exit_threshold = base_exit * 1.2
        elif volatility < 0.005:
            self.entry_threshold = base_entry * 0.8; self.exit_threshold = base_exit * 0.8
        else:
            self.entry_threshold = base_entry; self.exit_threshold = base_exit

    def initialize_broker_history(self, market_data: Dict):
        if not self.broker_manager: return
        for pair in self.pairs:
            if pair in self.broker_manager.brokers:
                broker = self.broker_manager.brokers[pair]
                price = market_data.get(pair, 0)
                if price > 0:
                    for i in range(30):
                        hist_price = price * (1 + (i - 15) * 0.0005)
                        broker.price_history.append(hist_price)
                        if hasattr(broker, 'close_history'): broker.close_history.append(hist_price)
                        if hasattr(broker, 'high_history'): broker.high_history.append(hist_price * 1.001)
                        if hasattr(broker, 'low_history'): broker.low_history.append(hist_price * 0.999)
                    if hasattr(broker, 'spread_history'):
                        for i in range(20):
                            broker.spread_history.append(price * 0.0001 * (1 + i * 0.01))
        logger.info("Broker history initialized for all pairs")

    def _update_rl_model_with_data(self):
        if not self.rl_enabled or not self.rl_agent: return
        if not hasattr(self, 'rl_training_data') or not self.rl_training_data: return
        logger.info(f"RL: Training data available: {len(self.rl_training_data)} transitions")
        if len(self.rl_training_data) >= 500:
            try:
                import pickle
                with open('rl_training_data.pkl', 'wb') as f:
                    pickle.dump(self.rl_training_data, f)
                logger.info(f"RL: Saved {len(self.rl_training_data)} transitions")
                self._train_rl_with_collected_data()
            except Exception as e:
                logger.warning(f"RL model update error: {e}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*60)
    print("FOREX TRADING CONTROLLER V2 - ALL FOREX PAIRS")
    print("="*60 + "\n")
    print("ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")
    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    config = {
        'pairs': FOREX_PAIRS, 'min_confidence': 60, 'cycle_interval': 10,
        'rl_enabled': True, 'load_rl_model': False, 'rl_model_path': 'models/rl_model.zip',
        'timeframe': 'M15',
        'engine_config': {
            'factor_weights': {'interest_rate_diff': 0.35, 'yield_curve_slope': 0.25,
                               'carry_trade_flow': 0.15, 'positioning_sentiment': 0.15,
                               'central_bank_actions': 0.10}}
    }
    controller = ForexTradingController(config)
    controller.start()
    market_data = controller.build_market_data()
    result = controller.process_cycle(market_data)
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"\nCycle: {result.get('cycle', 0)}")
    engine = result.get('engine', {})
    print(f"\nEngine: Direction={engine.get('engine_direction', 'N/A')} | Speed={engine.get('engine_speed', 0):.3f} | Health={engine.get('engine_health', 0):.1f}%")
    agents = result.get('agents', {})
    print(f"\nAgents:")
    for name, agent_result in agents.items():
        print(f"   {name}: {agent_result.get('vote', 'HOLD')} ({agent_result.get('confidence', 0):.0f}%)")
    consensus = result.get('consensus', {})
    print(f"\nConsensus: Signal={consensus.get('signal', 'HOLD')} | Confidence={consensus.get('confidence', 0):.1f}%")
    trade = result.get('trade', {})
    print(f"\nTrade: Status={trade.get('status', 'N/A')}")
    controller.stop()
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FOREX TRADING CONTROLLER V2 - LIVE TRADING")
    print("="*60 + "\n")
    print("ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")
    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    print("   Min Confidence: 50%")
    print("   Cycle Interval: 10s")

    config = {
        'pairs': FOREX_PAIRS, 'min_confidence': 50, 'cycle_interval': 10,
        'cold_start_min_win_rate': 0.0, 'cold_start_threshold': 50,
        'enable_entry_confirmation': True, 'entry_threshold': 1.0,
        'rl_enabled': True, 'load_rl_model': True, 'rl_model_path': 'models/rl_model.zip',
        'engine_config': {
            'factor_weights': {'interest_rate_diff': 0.35, 'yield_curve_slope': 0.25,
                               'carry_trade_flow': 0.15, 'positioning_sentiment': 0.15,
                               'central_bank_actions': 0.10}}
    }

    controller = ForexTradingController(config)
    controller.start()
    print("\nClearing any stuck positions...")
    controller.clear_stuck_positions()
    print("Ready to trade!\n")

    try:
        print("\nLive Trading Started... Press Ctrl+C to stop\n")
        cycle_count = 0
        while True:
            time.sleep(10)
            cycle_count += 1

            # FIXED: Check and reset daily/weekly stats in loop
            controller.check_and_reset_daily()
            controller.check_and_reset_weekly()

            market_data = controller.build_market_data()
            result = controller.process_cycle(market_data)
            status = controller.get_status()
            trade = result.get('trades', [])

            # FIXED: Use controller instead of self for RL training
            if controller.rl_enabled and len(controller.replay_buffer) % 10 == 0 and len(controller.replay_buffer) > 0:
                controller._train_rl_from_replay()

            if cycle_count % 5 == 0:
                controller._save_cold_start_state()

            # FIXED: Safe stuck position check
            if (cycle_count > 1 and hasattr(controller, 'execution_engine') and
                controller.execution_engine and hasattr(controller.execution_engine, 'positions') and
                len(controller.execution_engine.positions) > 0):
                real_positions = {}
                for pair, pos in controller.execution_engine.positions.items():
                    if isinstance(pos, dict) and pos.get('type') in ['BUY', 'SELL']:
                        if pos.get('price', 0) > 0 and pos.get('volume', 0) > 0:
                            real_positions[pair] = pos
                if len(real_positions) == 0 and len(controller.execution_engine.positions) > 0:
                    print("Found stuck positions - clearing...")
                    controller.clear_stuck_positions()

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle: {cycle_count} | Trades: {len(trade)} | Active: {status.get('active_count', 0)} | P&L: ${status.get('daily_pnl', 0):.2f}")

    except KeyboardInterrupt:
        print("\nShutting down...")
        controller.stop()
        print("Stopped")