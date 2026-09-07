# trading_controller2.py - ENTRY CONFIRMATION VERSION
"""
FOREX TRADING CONTROLLER V2 - WITH M5 CANDLE & S/R CONFIRMATION
"""

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import threading
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# Core components
from core.dollar_engine import DollarEngine
from core.gear_broker import GearBroker
from core.gear_anomaly_detector import GearAnomalyDetector
from core.monte_carlo_simulator import MonteCarloSimulator
from core.order_execution import OrderExecutionEngine

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
    # Fallback classes (keep your existing fallbacks)
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

# RL Modules (optional)
try:
    from rl_trading_env import ForexTradingEnv
    from rl_agent import RLAgent
    RL_AVAILABLE = True
    print("✅ RL modules loaded")
except ImportError as e:
    print(f"⚠️ RL not available: {e}")
    RL_AVAILABLE = False
    # Dummy classes
    class ForexTradingEnv: pass
    class RLAgent: pass

# MT4 Price Provider
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
# ALL FOREX PAIRS
# ============================================================

SYMBOL_CONFIG = {
    'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
    'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03, 'type': 'forex'},
}

FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
]


class ForexTradingController:
    """Main trading controller with entry confirmation via M5 candles and S/R."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.name = "ForexGearController"
        self.timeframe = self.config.get('timeframe', 'M15')
        self.is_running = False
        self.cycle_interval = self.config.get('cycle_interval', 10)
        self.cycle_count = 0

        # ===== MT4 CONNECTION =====
        self.mt4 = None
        self._connect_mt4()

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

        # ===== AGENTS =====
        logger.info("🤖 Initializing Agents...")
        self.agent_x = ForexAgentX(name="Forex_X", timeframe=self.timeframe)
        self.agent_u = ForexLiquidityAgentEnhanced(name="Forex_Agent_U")
        self.agent_d = AgentDVolatility(name="Forex_D", timeframe=self.timeframe)
        self.agent_c = AgentCMomentum()
        self.agent_e = AgentEMicrostructure()
        self.agent_p = WhisperAnalyst()

        self.agents = [self.agent_x, self.agent_u, self.agent_d, self.agent_c, self.agent_e, self.agent_p]
        logger.info(f"   ✅ {len(self.agents)} agents initialized")
        for agent in self.agents:
            logger.info(f"      - {agent.name}")

        # ===== BROKERS =====
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

        # ===== STATE =====
        self.decision_log = []
        self.last_results = {}
        self.last_agent_results = {}  # for RL observation

        # ===== PRICE CHECK =====
        self._log_current_prices()

        logger.info("✅ ForexTradingController initialized successfully!")
        logger.info(f"   📊 Pairs: {len(self.pairs)}")
        logger.info(f"   🤖 Agents: {len(self.agents)}")
        logger.info(f"   🔄 Cycle Interval: {self.cycle_interval}s")
        logger.info(f"   🤖 RL Enabled: {self.rl_enabled}")

    # ============================================================
    # MT4 CONNECTION
    # ============================================================

    def _connect_mt4(self):
        """Connect to MT4."""
        try:
            self.mt4 = get_mt4_prices()
            if self.mt4:
                test_result = self.mt4._send({"command": "ACCOUNT"})
                if test_result and isinstance(test_result, dict):
                    balance = test_result.get('balance', 0)
                    if balance > 0:
                        logger.info(f"   ✅ MT4 connected - Balance: ${balance:.2f}")
                        return
                    else:
                        logger.warning("   ⚠️ MT4 connected but no account data")
                else:
                    logger.warning("   ⚠️ MT4 test failed")
            else:
                logger.warning("   ⚠️ MT4 connection failed")
        except Exception as e:
            logger.error(f"   ❌ MT4 connection error: {e}")
            self.mt4 = None

    # ============================================================
    # PRICE METHODS
    # ============================================================

    def get_all_mt4_prices(self) -> Dict:
        """Get ALL prices from dashboard file."""
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
                    if price > 0:
                        prices[symbol] = price
            for pair in FOREX_PAIRS:
                if pair in data and pair not in prices:
                    price = float(data.get(pair, 0))
                    if price > 0:
                        prices[pair] = price
            return prices
        except Exception as e:
            logger.warning(f"Error reading file: {e}")
            return {}

    def get_price(self, symbol: str) -> float:
        prices = self.get_all_mt4_prices()
        return prices.get(symbol, 0)

    def get_all_prices(self) -> Dict:
        return self.get_all_mt4_prices()

    def _log_current_prices(self):
        """Log current prices."""
        try:
            prices = self.get_all_mt4_prices()
            print(f"\n{'='*60}")
            print(f"📊 PRICE CHECK - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            for symbol in FOREX_PAIRS:
                price = prices.get(symbol, 0)
                if price > 0:
                    print(f"   ✅ {symbol:12} | MT4      | {price:12.5f}")
                else:
                    print(f"   ❌ {symbol:12} | N/A      | {'NO PRICE':>12}")
            if self.agent_x is not None:
                z_score = self.agent_x.z_score if hasattr(self.agent_x, 'z_score') else 0
                samples = len(self.agent_x.spread_history) if hasattr(self.agent_x, 'spread_history') else 0
                print(f"   📊 Agent_X: Z={z_score:.2f} | Samples={samples}/30")
            print(f"{'='*60}\n")
        except Exception as e:
            logger.warning(f"Price log error: {e}")

    # ============================================================
    # BUILD MARKET DATA
    # ============================================================

    def build_market_data(self) -> Dict:
        """Build market data from MT4."""
        market_data = {}
        prices = self.get_all_mt4_prices()
        for pair in self.pairs:
            if pair in prices and prices[pair] > 0:
                market_data[pair] = prices[pair]
                market_data[f'{pair}_price'] = prices[pair]
        if 'EURUSD' in market_data and market_data['EURUSD'] > 0:
            market_data['current_price'] = market_data['EURUSD']
            market_data['price'] = market_data['EURUSD']
            market_data['pair'] = 'EURUSD'
        engine_state = self.engine.get_status() if self.engine else {}
        market_data['engine_state'] = engine_state
        for pair in self.pairs:
            if pair in self.brokers:
                gear_pred = self.engine.get_gear_prediction(pair, self.brokers[pair].gear_ratio)
                market_data[f'{pair}_gear_prediction'] = gear_pred
        market_data['timestamp'] = datetime.now().isoformat()
        return market_data

    # ============================================================
    # ENTRY CONFIRMATION: M5 CANDLE + SUPPORT/RESISTANCE
    # ============================================================

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
        Confirm entry using:
        - Last completed M5 candle (green for BUY, red for SELL)
        - Support/resistance distance (avoid buying at resistance, selling at support)
        Returns True if all conditions pass.
        """
        # 1. Get last completed M5 candle
        candle = self._get_last_m5_candle(symbol)
        if not candle:
            logger.warning(f"⚠️ No M5 candle for {symbol} – skipping confirmation")
            return False   # strict: if no data, do not trade

        candle_close = candle['close']
        candle_open = candle['open']
        is_green = candle_close > candle_open
        is_red = candle_close < candle_open

        if direction == 'BUY' and not is_green:
            logger.info(f"⏸️ {symbol}: Last M5 candle is NOT green – skipping BUY")
            return False
        if direction == 'SELL' and not is_red:
            logger.info(f"⏸️ {symbol}: Last M5 candle is NOT red – skipping SELL")
            return False

        # 2. Support/Resistance using recent swings
        swings = self._find_recent_swings(symbol, lookback=50)
        support = swings.get('support', 0)
        resistance = swings.get('resistance', 0)

        # ATR for buffer
        atr = self._get_atr(symbol, timeframe='M5', period=14)
        if atr == 0:
            atr = price * 0.001   # 0.1% fallback

        buffer = 0.5 * atr   # half ATR

        if direction == 'BUY':
            min_price = support + buffer
            if price < min_price:
                logger.info(f"⏸️ {symbol}: Price {price:.5f} too close to support ({support:.5f}) – skipping BUY")
                return False
        elif direction == 'SELL':
            max_price = resistance - buffer
            if price > max_price:
                logger.info(f"⏸️ {symbol}: Price {price:.5f} too close to resistance ({resistance:.5f}) – skipping SELL")
                return False

        return True

    # ============================================================
    # AGENT EXECUTION
    # ============================================================

    def _has_open_position(self, pair: str) -> bool:
        if self.execution_engine and pair in self.execution_engine.positions:
            return True
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

    # ============================================================
    # SIGNAL GENERATION
    # ============================================================

    def _generate_signals(self, agent_results: Dict, market_data: Dict) -> Dict:
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
    # CLEAR STUCK POSITIONS
    # ============================================================

    def clear_stuck_positions(self):
        if self.execution_engine:
            if hasattr(self.execution_engine, 'positions'):
                self.execution_engine.positions = {}
                print("🗑️ Cleared execution engine positions")
            if hasattr(self.execution_engine, 'active_positions'):
                self.execution_engine.active_positions = {}
                print("🗑️ Cleared execution engine active positions")
            if hasattr(self.execution_engine, 'trades_today'):
                self.execution_engine.trades_today = 0
                print("📊 Reset trades today to 0")
            if hasattr(self.execution_engine, 'daily_pnl'):
                self.execution_engine.daily_pnl = 0.0
                print("💰 Reset daily P&L to $0.00")
            print("✅ Stuck positions cleared!")
            return True
        return False

    # ============================================================
    # ORDER SENDING WITH RETRY & PRICE VALIDATION
    # ============================================================

    def get_symbol_config(self, symbol):
        """Get symbol config with fallback."""
        clean = symbol.replace('#', '')
        if clean in SYMBOL_CONFIG:
            return SYMBOL_CONFIG[clean]
        if symbol in SYMBOL_CONFIG:
            return SYMBOL_CONFIG[symbol]
        return {'pip': 0.0001, 'digits': 5, 'sl_pips': 20, 'tp_pips': 40, 'volume': 0.03, 'type': 'unknown'}

    def _is_valid_price(self, symbol: str, price: float) -> bool:
        ranges = {
            'EURUSD': (0.8, 1.6), 'GBPUSD': (0.8, 1.7), 'USDJPY': (100, 200),
            'USDCHF': (0.7, 1.2), 'AUDUSD': (0.5, 0.9), 'USDCAD': (1.0, 1.7),
            'NZDUSD': (0.4, 0.8), 'EURGBP': (0.7, 1.0), 'EURJPY': (100, 200),
            'EURCAD': (1.2, 1.8), 'EURNZD': (1.5, 2.4), 'EURCHF': (0.8, 1.2),
        }
        clean = symbol.replace('#', '')
        if clean in ranges:
            low, high = ranges[clean]
            if price < low or price > high:
                return False
        else:
            if price < 0.01 or price > 10000:
                return False
        return True

    def send_real_order(self, symbol, action, price, sl, tp, volume, max_retries=3):
        """Send real order with retry and price validation."""
        try:
            from mt4_price_provider import get_mt4_prices
            mt4 = get_mt4_prices()

            # Get fresh price from MT4
            price_data = mt4._send({"command": "PRICE", "symbol": symbol})
            entry_price = price
            if price_data and isinstance(price_data, dict):
                bid = price_data.get('bid', 0)
                ask = price_data.get('ask', 0)
                if bid > 0 and ask > 0:
                    entry_price = ask if action == 'BUY' else bid
                    logger.info(f"   MT4 Price: {symbol} Bid={bid:.5f} Ask={ask:.5f}")

            # Validate
            if not self._is_valid_price(symbol, entry_price):
                logger.warning(f"⚠️ Invalid price {entry_price:.5f} for {symbol} – using fallback")
                entry_price = price

            config = self.get_symbol_config(symbol)
            pip = config['pip']
            digits = config['digits']
            sl_pips = max(config.get('sl_pips', 15), 15)
            tp_pips = max(config.get('tp_pips', 30), 30)

            if action == 'BUY':
                sl = entry_price - (sl_pips * pip)
                tp = entry_price + (tp_pips * pip)
            else:
                sl = entry_price + (sl_pips * pip)
                tp = entry_price - (tp_pips * pip)

            # Ensure minimum distance
            min_dist = 10 * pip
            if abs(entry_price - sl) < min_dist:
                if action == 'BUY':
                    sl = entry_price - (min_dist * 1.5)
                else:
                    sl = entry_price + (min_dist * 1.5)
            if abs(tp - entry_price) < min_dist:
                if action == 'BUY':
                    tp = entry_price + (min_dist * 2)
                else:
                    tp = entry_price - (min_dist * 2)

            entry_price = round(entry_price, digits)
            sl = round(sl, digits)
            tp = round(tp, digits)

            logger.info(f"\n📤 SENDING ORDER:")
            logger.info(f"   Pair: {symbol}")
            logger.info(f"   Action: {action}")
            logger.info(f"   Volume: {volume}")
            logger.info(f"   Entry: {entry_price:.{digits}f}")
            logger.info(f"   SL: {sl:.{digits}f} ({sl_pips} pips)")
            logger.info(f"   TP: {tp:.{digits}f} ({tp_pips} pips)")

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
                if 'Timeout' in str(error):
                    logger.warning(f"   ⏳ Timeout, retrying ({attempt+1}/{max_retries})...")
                    time.sleep(1)
                    continue
                elif 'Error 130' in str(error):
                    sl_pips += 5
                    tp_pips += 5
                    logger.warning(f"   ⚠️ Error 130 – adjusting SL/TP (SL={sl_pips}pips, TP={tp_pips}pips)")
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
                    logger.error(f"   ❌ ORDER FAILED: {error}")
                    return {'success': False, 'error': error}

            return {'success': False, 'error': 'Max retries exceeded'}

        except Exception as e:
            logger.error(f"   ❌ ORDER ERROR: {e}")
            return {'success': False, 'error': str(e)}

    # ============================================================
    # MAIN PROCESS CYCLE (WITH ENTRY CONFIRMATION)
    # ============================================================

    def process_cycle(self, market_data: Dict = None) -> Dict:
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
            'rl_used': False
        }

        try:
            # 1. Update engine
            if self.engine:
                results['engine'] = self.engine.update_engine_state(market_data)

            # 2. Anomaly detection
            if self.anomaly_detector:
                anomalies = self.anomaly_detector.update(market_data)
                results['anomalies'] = anomalies
                if anomalies.get('protection_active', False):
                    return results

            # 3. Circuit breaker
            if self.execution_engine and self.execution_engine.daily_pnl < -self.config.get('max_daily_loss', 500):
                logger.warning(f"🔴 DAILY LOSS LIMIT REACHED: ${self.execution_engine.daily_pnl:.2f}")
                self.stop()
                self.clear_stuck_positions()
                return {'status': 'STOPPED', 'reason': 'Daily loss limit exceeded'}

            # 4. Process each pair
            min_confidence = self.config.get('min_confidence', 60)
            executed_trades = []

            print(f"\n{'='*60}")
            print(f"📊 TRADING CYCLE - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")

            for pair in self.pairs:
                if self._has_open_position(pair):
                    print(f"⏸️ {pair}: Already has position - skipping")
                    continue

                price = market_data.get(pair, 0)
                if price <= 0:
                    print(f"❌ {pair}: No price available")
                    continue

                # Validate price range
                if not self._is_valid_price(pair, price):
                    print(f"⚠️ {pair}: Invalid price {price:.5f} – skipping")
                    continue

                signal_data = {'pair': pair, 'price': price, 'current_price': price, 'symbol': pair}

                # Parallel agent analysis
                agent_results = self._run_agents_parallel(signal_data)
                self.last_agent_results = agent_results  # for RL observation

                signals = self._generate_signals(agent_results, market_data)
                consensus = self._generate_consensus(signals)

                signal = consensus.get('signal', 'HOLD')
                confidence = consensus.get('confidence', 0)
                rl_override = False

                # RL override (if enabled)
                if self.rl_enabled and self.rl_agent:
                    obs = self.rl_env._get_observation()
                    rl_action = self.rl_agent.predict(obs, deterministic=not self.rl_agent.training)
                    rl_pair_idx = int(np.clip(rl_action[0], 0, len(self.pairs)-1))
                    rl_trade_type = int(np.clip(rl_action[1], 0, 2))
                    rl_size_mult = np.clip(rl_action[2], 0.0, 2.0)
                    if rl_trade_type != 0 and self.pairs[rl_pair_idx] == pair:
                        # safety check for RL
                        if self._is_valid_price(pair, price):
                            rl_signal = 'BUY' if rl_trade_type == 1 else 'SELL'
                            logger.info(f"🤖 RL OVERRIDE: {rl_signal} on {pair} size {rl_size_mult:.2f}x")
                            signal = rl_signal
                            confidence = 85
                            rl_override = True
                            results['rl_used'] = True

                print(f"\n🔍 {pair}: Signal={signal} ({confidence:.1f}%) "
                      f"BUY={consensus['buy_votes']} SELL={consensus['sell_votes']} HOLD={consensus['hold_votes']}")

                # ===== ENTRY CONFIRMATION (NEW) =====
                if signal != 'HOLD' and confidence >= min_confidence:
                    # Confirm with M5 candle and S/R
                    if not self._confirm_entry_with_candle_and_sr(pair, price, signal):
                        print(f"   ⏸️ SKIPPED: Entry confirmation failed")
                        continue

                # ===== MONTE CARLO =====
                if signal != 'HOLD' and confidence >= min_confidence:
                    mc_confidence = 100
                    if not self.config.get('bypass_mc', False) and not rl_override:
                        mc_results = self.monte_carlo.simulate_entry(current_price=price, direction=signal)
                        mc_confidence = mc_results.get('entry_confidence', 0) if mc_results else 0
                        print(f"   MC Confidence: {mc_confidence:.1f}%")

                    if mc_confidence > 50:
                        # Use RL size if overridden
                        size_mult = rl_size_mult if rl_override else 1.0
                        # Execute
                        trade_result = self.execution_engine.execute_signal(
                            consensus, market_data, position_size=size_mult
                        )
                        trade_result['pair'] = pair
                        trade_result['rl_override'] = rl_override
                        executed_trades.append(trade_result)
                        logger.info(f"💼 TRADE EXECUTED: {pair} {signal} @ {price:.4f}")
                        print(f"   ✅ TRADE EXECUTED!")
                    else:
                        print(f"   ❌ SKIPPED: MC confidence {mc_confidence:.1f}%")
                else:
                    if signal == 'HOLD':
                        print(f"   ⏸️ SKIPPED: HOLD")
                    else:
                        print(f"   ❌ SKIPPED: Confidence {confidence:.1f}% < {min_confidence}%")

            results['trades'] = executed_trades

            if self.execution_engine:
                results['pnl'] = self.execution_engine.update_pnl(market_data)

        except Exception as e:
            logger.error(f"Error processing cycle: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)

        self.last_results = results
        return results

    # ============================================================
    # CONTROL METHODS
    # ============================================================

    def start(self):
        self.is_running = True
        logger.info("🚀 ForexTradingController started")

    def stop(self):
        self.is_running = False
        logger.info("🛑 ForexTradingController stopped")

    def get_status(self) -> Dict:
        actual_positions = {}
        if self.execution_engine and hasattr(self.execution_engine, 'positions'):
            for pair, pos in self.execution_engine.positions.items():
                if isinstance(pos, dict) and pos.get('type') in ['BUY', 'SELL']:
                    actual_positions[pair] = pos
        return {
            'name': self.name,
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'pairs': self.pairs,
            'agents': len(self.agents),
            'rl_enabled': self.rl_enabled,
            'engine': self.engine.get_status() if hasattr(self.engine, 'get_status') else {},
            'execution': self.execution_engine.get_status() if hasattr(self.execution_engine, 'get_status') else {},
            'positions': actual_positions,
            'active_count': len(actual_positions),
            'trades_today': self.execution_engine.trades_today if self.execution_engine else 0,
            'daily_pnl': self.execution_engine.daily_pnl if self.execution_engine else 0,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FOREX TRADING CONTROLLER V2 - ENTRY CONFIRMATION")
    print("="*60 + "\n")

    print("📊 ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")

    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    print(f"   Min Confidence: 60%")
    print(f"   Cycle Interval: 10s")

    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 60,
        'cycle_interval': 10,
        'rl_enabled': False,          # set to True after training
        'load_rl_model': False,
        'rl_model_path': 'models/rl_model.zip',
        'simulation_mode': False,     # live trading
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

            market_data = controller.build_market_data()
            result = controller.process_cycle(market_data)
            status = controller.get_status()

            trades = result.get('trades', [])
            engine = result.get('engine', {})
            rl_used = result.get('rl_used', False)

            print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Cycle: {cycle_count} | "
                  f"Trades: {len(trades)} | "
                  f"Active: {status['active_count']} | "
                  f"RL: {'✅' if rl_used else '❌'} | "
                  f"Engine: {engine.get('engine_direction', 'N/A')} | "
                  f"P&L: ${status['daily_pnl']:.2f}")

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        controller.stop()
        print("✅ Stopped")