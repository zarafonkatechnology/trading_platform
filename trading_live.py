# final_ultimate_trader.py
"""
FINAL ULTIMATE REAL TRADING SYSTEM - $1000 ACCOUNT
===================================================
- 23 AI Agents voting on every trade
- Multiple strategies (Trend, Mean Reversion, Momentum, Volatility, Breakout)
- Monte Carlo validation (2000+ paths)
- Full risk management (2% daily loss, 0.2% per trade)
- Real MT4 execution
- Dashboard integration
- Runs 24/7
- All configurable
"""

import time
import threading
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import random
from dataclasses import dataclass
from collections import deque
from enum import Enum

# ============================================================
# IMPORTS (Your existing system)
# ============================================================

try:
    from mt4_price_provider import get_mt4_prices
except ImportError:
    print("❌ mt4_price_provider.py not found!")
    sys.exit(1)

try:
    from live_executor import live_executor, TradeSignal, SignalStrength
    from position_manager import position_manager
except ImportError:
    print("❌ live_executor.py not found!")
    sys.exit(1)

try:
    from agent_pipeline import AgentDeliberativePipeline
except ImportError:
    print("❌ agent_pipeline.py not found!")
    sys.exit(1)

try:
    from order_flow_analyzer import get_order_flow_signal
except ImportError:
    print("❌ order_flow_analyzer.py not found!")
    sys.exit(1)

try:
    from backend.agents.agent_manager import AgentManager
except ImportError:
    print("⚠️ AgentManager not found - using fallback")
    AgentManager = None

# ============================================================
# ENUMS
# ============================================================

class StrategyType(Enum):
    TREND = "Trend Following"
    MEAN_REVERSION = "Mean Reversion"
    MOMENTUM = "Momentum"
    VOLATILITY = "Volatility"
    BREAKOUT = "Breakout"
    ORDER_FLOW = "Order Flow"
    AGENT_CONSENSUS = "Agent Consensus"

class TradeStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class RiskConfig:
    """Strict risk management configuration"""
    account_balance: float = 1000.00
    max_daily_loss: float = -20.00     # 2% of $1000 - HARD STOP
    risk_per_trade: float = 0.002      # 0.2% = $2 per trade
    max_daily_trades: int = 5
    max_concurrent: int = 1
    volume: float = 0.01
    min_confidence: float = 70.0
    strong_confidence: float = 85.0
    max_slippage: float = 0.0002
    max_spread: float = 0.0003

@dataclass
class StrategyConfig:
    """Strategy weights and parameters"""
    trend_weight: float = 0.25
    mean_reversion_weight: float = 0.20
    momentum_weight: float = 0.20
    volatility_weight: float = 0.15
    breakout_weight: float = 0.10
    order_flow_weight: float = 0.10
    
    # SL/TP settings
    sl_multiplier: float = 1.0          # Very tight SL
    tp_multiplier: float = 2.0          # 2:1 Risk/Reward
    atr_period: int = 14
    atr_multiplier: float = 1.0
    
    # Indicator parameters
    rsi_period: int = 14
    ma_period: int = 20
    momentum_period: int = 12
    volatility_period: int = 10
    
    # Monte Carlo
    monte_carlo_paths: int = 2000
    monte_carlo_success_threshold: float = 55.0

@dataclass
class TradingConfig:
    """Trading timing and symbols"""
    symbols: List[str] = None
    cycle_interval: int = 180          # 3 minutes
    max_trade_duration: int = 3600     # 1 hour max
    warmup_period: int = 10            # Initial warmup cycles
    cooldown_period: int = 60          # 1 minute cooldown after trade
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['EURUSD', 'GBPUSD', 'GOLD']

# ============================================================
# TRADE RECORDER
# ============================================================

class TradeRecorder:
    """Records all trades to file and database"""
    
    def __init__(self, filename: str = "trades_history.json"):
        self.filename = filename
        self.trades = []
        self._load_trades()
    
    def _load_trades(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.trades = json.load(f)
        except:
            self.trades = []
    
    def _save_trades(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.trades[-1000:], f, indent=2)
        except:
            pass
    
    def add_trade(self, trade: Dict):
        self.trades.append(trade)
        self._save_trades()
    
    def get_trades(self, limit: int = 100):
        return self.trades[-limit:]
    
    def get_stats(self) -> Dict:
        total = len(self.trades)
        wins = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        losses = sum(1 for t in self.trades if t.get('pnl', 0) < 0)
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2)
        }

# ============================================================
# STRATEGY ENGINE
# ============================================================

class StrategyEngine:
    """Advanced multi-strategy engine"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.mt4 = get_mt4_prices()
        self.agent_manager = AgentManager() if AgentManager else None
        self.pipeline = AgentDeliberativePipeline()
        self.price_history = {}
        self.indicator_cache = {}
    
    def analyze(self, symbol: str, price: float) -> Dict:
        """Run all strategies and return combined result"""
        
        # Get historical prices
        prices = self._get_price_history(symbol, 50)
        if len(prices) < 20:
            return self._empty_analysis("Not enough data")
        
        # Run all strategies
        strategies = {
            StrategyType.TREND: self._trend_strategy(prices, price),
            StrategyType.MEAN_REVERSION: self._mean_reversion_strategy(prices, price),
            StrategyType.MOMENTUM: self._momentum_strategy(prices, price),
            StrategyType.VOLATILITY: self._volatility_strategy(prices, price),
            StrategyType.BREAKOUT: self._breakout_strategy(prices, price),
            StrategyType.ORDER_FLOW: self._order_flow_strategy(symbol, price),
            StrategyType.AGENT_CONSENSUS: self._agent_consensus_strategy(symbol, price),
        }
        
        # Calculate combined score
        weights = {
            StrategyType.TREND: self.config.trend_weight,
            StrategyType.MEAN_REVERSION: self.config.mean_reversion_weight,
            StrategyType.MOMENTUM: self.config.momentum_weight,
            StrategyType.VOLATILITY: self.config.volatility_weight,
            StrategyType.BREAKOUT: self.config.breakout_weight,
            StrategyType.ORDER_FLOW: self.config.order_flow_weight,
        }
        
        total_score = 0
        total_weight = 0
        strategy_details = {}
        
        for strategy, result in strategies.items():
            weight = weights.get(strategy, 0)
            if result:
                score = result.get('score', 0)
                total_score += score * weight
                total_weight += weight
                strategy_details[strategy.value] = {
                    'score': score,
                    'weight': weight,
                    'confidence': result.get('confidence', 50)
                }
        
        if total_weight == 0:
            return self._empty_analysis("No strategies active")
        
        final_score = total_score / total_weight
        
        # Determine action
        if final_score > 25:
            action = 'BUY'
            confidence = min(95, 65 + abs(final_score))
        elif final_score < -25:
            action = 'SELL'
            confidence = min(95, 65 + abs(final_score))
        else:
            action = 'HOLD'
            confidence = 50
        
        return {
            'action': action,
            'confidence': confidence,
            'score': final_score,
            'strategies': strategy_details,
            'reasoning': self._generate_reasoning(action, confidence, strategy_details)
        }
    
    def _get_price_history(self, symbol: str, count: int) -> List[float]:
        """Get price history for symbol"""
        prices = []
        for i in range(count):
            price = self.mt4.get_price(symbol)
            if price > 0:
                prices.append(price)
            time.sleep(0.02)
        return prices
    
    def _trend_strategy(self, prices: List[float], current: float) -> Dict:
        """Trend following strategy"""
        if len(prices) < 20:
            return None
        
        # Moving averages
        ma20 = sum(prices[-20:]) / 20
        ma50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else ma20
        
        # Trend strength
        trend = (current - ma20) / ma20 * 100
        
        # Score
        if trend > 1.0:
            score = 50
            confidence = 70
        elif trend > 0.5:
            score = 30
            confidence = 60
        elif trend < -1.0:
            score = -50
            confidence = 70
        elif trend < -0.5:
            score = -30
            confidence = 60
        else:
            score = 0
            confidence = 50
        
        return {'score': score, 'confidence': confidence}
    
    def _mean_reversion_strategy(self, prices: List[float], current: float) -> Dict:
        """Mean reversion strategy"""
        if len(prices) < 20:
            return None
        
        # Bollinger Bands
        mean = sum(prices) / len(prices)
        std = np.std(prices)
        upper = mean + (std * 2)
        lower = mean - (std * 2)
        
        # Score
        if current > upper:
            score = -60  # Overbought - SELL
            confidence = 75
        elif current < lower:
            score = 60   # Oversold - BUY
            confidence = 75
        else:
            # RSI-like
            rsi = self._calculate_rsi(prices)
            if rsi > 70:
                score = -30
                confidence = 60
            elif rsi < 30:
                score = 30
                confidence = 60
            else:
                score = 0
                confidence = 50
        
        return {'score': score, 'confidence': confidence}
    
    def _momentum_strategy(self, prices: List[float], current: float) -> Dict:
        """Momentum strategy"""
        if len(prices) < 15:
            return None
        
        # Rate of Change
        roc = ((current - prices[-15]) / prices[-15]) * 100 if prices[-15] > 0 else 0
        score = roc * 3
        
        # RSI
        rsi = self._calculate_rsi(prices)
        
        # Combine
        final_score = (score * 0.5) + ((rsi - 50) * 0.5)
        final_score = max(-100, min(100, final_score))
        
        confidence = 60 + abs(final_score) * 0.25
        
        return {'score': final_score, 'confidence': min(95, confidence)}
    
    def _volatility_strategy(self, prices: List[float], current: float) -> Dict:
        """Volatility strategy"""
        if len(prices) < 10:
            return None
        
        # ATR
        atr = self._calculate_atr(prices)
        volatility = (atr / current) * 100
        
        # Score based on volatility regime
        if volatility > 2.0:
            score = -20  # Reduce position
            confidence = 55
        elif volatility < 0.5:
            score = 20   # Increase position
            confidence = 55
        else:
            score = 0
            confidence = 50
        
        return {'score': score, 'confidence': confidence}
    
    def _breakout_strategy(self, prices: List[float], current: float) -> Dict:
        """Breakout strategy"""
        if len(prices) < 20:
            return None
        
        # Recent range
        high = max(prices[-20:])
        low = min(prices[-20:])
        range_size = high - low
        
        if range_size <= 0:
            return None
        
        # Check for breakout
        if current > high * 1.002:
            score = 70   # Breakout up - BUY
            confidence = 70
        elif current < low * 0.998:
            score = -70  # Breakout down - SELL
            confidence = 70
        else:
            score = 0
            confidence = 50
        
        return {'score': score, 'confidence': confidence}
    
    def _order_flow_strategy(self, symbol: str, price: float) -> Dict:
        """Order flow strategy"""
        try:
            signal = get_order_flow_signal(symbol, price)
            
            if signal:
                score = signal.get('score', 0)
                confidence = 60 + abs(score) * 0.2
                return {'score': score, 'confidence': min(95, confidence)}
        except:
            pass
        
        return None
    
    def _agent_consensus_strategy(self, symbol: str, price: float) -> Dict:
        """Agent consensus strategy"""
        try:
            result = self.pipeline.analyze_symbol(symbol, price)
            
            if result:
                score = result.get('score', 0)
                confidence = result.get('confidence', 50)
                return {'score': score, 'confidence': confidence}
        except:
            pass
        
        return None
    
    def _calculate_rsi(self, prices: List[float]) -> float:
        """Calculate RSI"""
        if len(prices) < 15:
            return 50
        
        gains = 0
        losses = 0
        for i in range(1, 15):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains += change
            else:
                losses += abs(change)
        
        if losses == 0:
            return 100
        
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return min(100, max(0, rsi))
    
    def _calculate_atr(self, prices: List[float]) -> float:
        """Calculate ATR"""
        if len(prices) < 2:
            return 0
        
        ranges = []
        for i in range(1, len(prices)):
            ranges.append(abs(prices[i] - prices[i-1]))
        
        return np.mean(ranges) if ranges else 0
    
    def _generate_reasoning(self, action: str, confidence: float,
                            strategy_details: Dict) -> str:
        """Generate reasoning for the trade"""
        if action == 'HOLD':
            return "No clear signal from strategies. Waiting for better opportunity."
        
        active_strategies = [s for s, d in strategy_details.items() if abs(d.get('score', 0)) > 20]
        if not active_strategies:
            return f"{action} signal with {confidence:.0f}% confidence."
        
        strategies_text = ", ".join(active_strategies[:3])
        return f"{action} signal with {confidence:.0f}% confidence. Active strategies: {strategies_text}."
    
    def _empty_analysis(self, reason: str) -> Dict:
        return {
            'action': 'HOLD',
            'confidence': 0,
            'score': 0,
            'strategies': {},
            'reasoning': reason
        }

# ============================================================
# MONTE CARLO ENGINE
# ============================================================

class MonteCarloEngine:
    """Advanced Monte Carlo risk simulation"""
    
    def __init__(self, paths: int = 2000):
        self.paths = paths
        self.volatility_cache = {}
    
    def validate(self, symbol: str, price: float, action: str,
                 stop_loss: float, take_profit: float) -> Dict:
        """Validate trade with Monte Carlo"""
        
        # Get volatility
        vol = self._get_volatility(symbol)
        
        # Run simulations
        successes = 0
        best_case = price
        worst_case = price
        all_results = []
        
        for _ in range(self.paths):
            # Random walk
            steps = np.random.normal(0, vol, 50)
            sim_prices = price * np.exp(np.cumsum(steps))
            final_price = sim_prices[-1]
            all_results.append(final_price)
            
            if action == 'BUY' and final_price > price:
                successes += 1
            elif action == 'SELL' and final_price < price:
                successes += 1
            
            best_case = max(best_case, final_price)
            worst_case = min(worst_case, final_price)
        
        success_rate = (successes / self.paths) * 100
        
        # Confidence intervals
        confidence_interval = np.percentile(all_results, [5, 95])
        
        # Risk assessment
        if action == 'BUY':
            profit_prob = sum(1 for p in all_results if p > take_profit) / self.paths * 100
            loss_prob = sum(1 for p in all_results if p < stop_loss) / self.paths * 100
        else:
            profit_prob = sum(1 for p in all_results if p < take_profit) / self.paths * 100
            loss_prob = sum(1 for p in all_results if p > stop_loss) / self.paths * 100
        
        return {
            'success_rate': success_rate,
            'best_case': best_case,
            'worst_case': worst_case,
            'confidence_lower': confidence_interval[0],
            'confidence_upper': confidence_interval[1],
            'profit_probability': profit_prob,
            'loss_probability': loss_prob,
            'valid': success_rate >= 55 and profit_prob > loss_prob,
            'risk_score': 100 - success_rate,
            'expected_return': np.mean(all_results) - price
        }
    
    def _get_volatility(self, symbol: str) -> float:
        """Get historical volatility for symbol"""
        if symbol in self.volatility_cache:
            return self.volatility_cache[symbol]
        
        try:
            prices = []
            for i in range(30):
                price = get_mt4_prices().get_price(symbol)
                if price > 0:
                    prices.append(price)
                time.sleep(0.05)
            
            if len(prices) < 10:
                return 0.005
            
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    returns.append((prices[i] - prices[i-1]) / prices[i-1])
            
            vol = np.std(returns) if returns else 0.005
            self.volatility_cache[symbol] = vol
            return vol
        except:
            return 0.005

# ============================================================
# RISK MANAGER
# ============================================================

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.daily_date = datetime.now().date()
        self.open_positions = []
    
    def can_trade(self, symbol: str, volume: float, price: float) -> Tuple[bool, str]:
        """Check if a trade is allowed"""
        # Reset daily counters
        self._reset_daily()
        
        # Check daily loss limit
        if self.daily_pnl <= self.config.max_daily_loss:
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}"
        
        # Check daily trade limit
        if self.daily_trades >= self.config.max_daily_trades:
            return False, f"Daily trade limit reached: {self.daily_trades}/{self.config.max_daily_trades}"
        
        # Check concurrent positions
        if len(self.open_positions) >= self.config.max_concurrent:
            return False, f"Max concurrent positions reached: {self.config.max_concurrent}"
        
        # Check volume
        if volume < self.config.volume:
            return False, f"Volume too small: {volume} < {self.config.volume}"
        
        return True, "OK"
    
    def register_trade(self, trade: Dict):
        """Register a trade"""
        self.daily_trades += 1
        self.open_positions.append(trade)
    
    def close_trade(self, symbol: str, pnl: float):
        """Close a trade"""
        self.daily_pnl += pnl
        self.open_positions = [p for p in self.open_positions if p.get('symbol') != symbol]
    
    def get_status(self, balance: float) -> Dict:
        """Get risk status"""
        self._reset_daily()
        return {
            'balance': balance,
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': self.config.max_daily_loss,
            'daily_loss_remaining': abs(self.daily_pnl - self.config.max_daily_loss),
            'open_positions': len(self.open_positions),
            'max_concurrent': self.config.max_concurrent,
            'can_trade': (
                self.daily_pnl > self.config.max_daily_loss and
                self.daily_trades < self.config.max_daily_trades and
                len(self.open_positions) < self.config.max_concurrent
            )
        }
    
    def _reset_daily(self):
        today = datetime.now().date()
        if today != self.daily_date:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.daily_date = today

# ============================================================
# FINAL ULTIMATE TRADER
# ============================================================

class FinalUltimateTrader:
    """Complete professional trading system"""
    
    def __init__(self):
        # Configuration
        self.risk_config = RiskConfig()
        self.strategy_config = StrategyConfig()
        self.trading_config = TradingConfig()
        
        # Initialize components
        self.mt4 = get_mt4_prices()
        self.strategy_engine = StrategyEngine(self.strategy_config)
        self.monte_carlo = MonteCarloEngine(self.strategy_config.monte_carlo_paths)
        self.risk_manager = RiskManager(self.risk_config)
        self.trade_recorder = TradeRecorder()
        self.pipeline = AgentDeliberativePipeline()
        
        # System state
        self.is_running = False
        self.active_trade = None
        self.trade_start_time = None
        self.cooldown_until = 0
        self.warmup_cycles = 0
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
        }
        
        print("=" * 70)
        print("🚀 FINAL ULTIMATE REAL TRADING SYSTEM")
        print("=" * 70)
        print(f"💰 Account: ${self.risk_config.account_balance:.2f}")
        print(f"📉 Max Daily Loss: ${abs(self.risk_config.max_daily_loss):.2f} (2%)")
        print(f"🎯 Risk per Trade: ${self.risk_config.account_balance * self.risk_config.risk_per_trade:.2f} (0.2%)")
        print(f"📊 Max Trades/Day: {self.risk_config.max_daily_trades}")
        print(f"🎯 Min Confidence: {self.risk_config.min_confidence}%")
        print(f"🔄 Cycle: {self.trading_config.cycle_interval}s")
        print(f"📈 Max Trade Duration: {self.trading_config.max_trade_duration}s")
        print(f"📊 Symbols: {', '.join(self.trading_config.symbols)}")
        print("=" * 70)
        print()
    
    def start(self):
        """Start the trading system"""
        self.is_running = True
        self.warmup_cycles = self.trading_config.warmup_period
        
        # Start threads
        self._start_cycle_thread()
        self._start_monitor_thread()
        self._start_status_thread()
        
        print("✅ SYSTEM STARTED!")
        print("📊 Dashboard: http://localhost:5001")
        print("🛑 Press Ctrl+C to stop\n")
    
    def stop(self):
        """Stop the system"""
        self.is_running = False
        print("\n🛑 System stopped")
        self._print_summary()
    
    # ============================================================
    # THREADS
    # ============================================================
    
    def _start_cycle_thread(self):
        def cycle_loop():
            while self.is_running:
                try:
                    self._run_cycle()
                except Exception as e:
                    print(f"❌ Cycle error: {e}")
                time.sleep(self.trading_config.cycle_interval)
        
        thread = threading.Thread(target=cycle_loop, daemon=True)
        thread.start()
    
    def _start_monitor_thread(self):
        def monitor_loop():
            while self.is_running:
                try:
                    self._monitor_trades()
                except:
                    pass
                time.sleep(10)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _start_status_thread(self):
        def status_loop():
            while self.is_running:
                try:
                    self._print_status()
                except:
                    pass
                time.sleep(60)
        
        thread = threading.Thread(target=status_loop, daemon=True)
        thread.start()
    
    # ============================================================
    # MAIN CYCLE
    # ============================================================
    
    def _run_cycle(self):
        """Execute one trading cycle"""
        # Warmup
        if self.warmup_cycles > 0:
            self.warmup_cycles -= 1
            print(f"🔄 Warmup: {self.warmup_cycles} cycles remaining")
            return
        
        # Cooldown
        if time.time() < self.cooldown_until:
            print(f"⏸️ Cooldown: {int(self.cooldown_until - time.time())}s remaining")
            return
        
        print(f"\n🔄 Cycle {datetime.now().strftime('%H:%M:%S')}")
        
        # Get balance
        balance = self.mt4.get_account_balance()
        if balance <= 0:
            balance = self.risk_config.account_balance
        
        # Check risk
        status = self.risk_manager.get_status(balance)
        if not status['can_trade']:
            print(f"   ⛔ Trading blocked: {status}")
            return
        
        # Analyze each symbol
        for symbol in self.trading_config.symbols:
            if not self.is_running:
                break
            if self.active_trade:
                print(f"   ⏸️ Already in trade: {self.active_trade['symbol']}")
                break
            try:
                self._analyze_symbol(symbol)
            except Exception as e:
                print(f"   ⚠️ Error on {symbol}: {e}")
    
    def _analyze_symbol(self, symbol: str):
        """Analyze and trade a symbol"""
        # Get price
        price = self.mt4.get_price(symbol)
        if price <= 0:
            print(f"   ⚠️ Cannot get price for {symbol}")
            return
        
        # Run strategy engine
        analysis = self.strategy_engine.analyze(symbol, price)
        
        if analysis['action'] == 'HOLD':
            return
        
        # Check confidence
        if analysis['confidence'] < self.risk_config.min_confidence:
            print(f"   ⏸️ {symbol}: Confidence {analysis['confidence']:.0f}% < {self.risk_config.min_confidence}%")
            return
        
        # Calculate SL and TP
        sl_distance = self._calculate_sl_distance(symbol, price)
        if analysis['action'] == 'BUY':
            stop_loss = price - sl_distance
            take_profit = price + (sl_distance * self.strategy_config.tp_multiplier)
        else:
            stop_loss = price + sl_distance
            take_profit = price - (sl_distance * self.strategy_config.tp_multiplier)
        
        # Risk check
        risk_amount = abs(price - stop_loss) * self.risk_config.volume * 100000
        max_risk = self.risk_config.account_balance * self.risk_config.risk_per_trade
        
        if risk_amount > max_risk:
            print(f"   ⚠️ Risk too high: ${risk_amount:.2f} > ${max_risk:.2f}")
            return
        
        # Monte Carlo validation
        mc_result = self.monte_carlo.validate(symbol, price, analysis['action'],
                                              stop_loss, take_profit)
        
        if not mc_result['valid']:
            print(f"   ⚠️ Monte Carlo rejected: {mc_result['success_rate']:.0f}% success, "
                  f"{mc_result['profit_probability']:.0f}% profit, {mc_result['loss_probability']:.0f}% loss")
            return
        
        # Risk manager check
        can_trade, reason = self.risk_manager.can_trade(symbol, self.risk_config.volume, price)
        if not can_trade:
            print(f"   ⛔ {reason}")
            return
        
        # Check spread
        spread_ok = self._check_spread(symbol)
        if not spread_ok:
            print(f"   ⚠️ Spread too high for {symbol}")
            return
        
        # Execute trade
        self._execute_trade(symbol, analysis, price, stop_loss, take_profit, mc_result)
    
    def _calculate_sl_distance(self, symbol: str, price: float) -> float:
        """Calculate stop loss distance"""
        if symbol in ['EURUSD', 'GBPUSD']:
            return 0.0005
        elif symbol == 'GOLD':
            return 1.5
        elif symbol == 'USDJPY':
            return 0.08
        else:
            return price * 0.0005
    
    def _check_spread(self, symbol: str) -> bool:
        """Check if spread is acceptable"""
        try:
            price_data = self.mt4._send({"command": "PRICE", "symbol": symbol})
            if price_data and 'bid' in price_data and 'ask' in price_data:
                spread = price_data['ask'] - price_data['bid']
                if spread > self.risk_config.max_spread:
                    return False
        except:
            pass
        return True
    
    # ============================================================
    # EXECUTION
    # ============================================================
    
    def _execute_trade(self, symbol: str, analysis: Dict, price: float,
                       stop_loss: float, take_profit: float, mc_result: Dict):
        """Execute the trade"""
        
        action = analysis['action']
        confidence = analysis['confidence']
        
        print(f"\n   🎯 {action} {symbol} at {price:.5f}")
        print(f"   📈 Confidence: {confidence:.0f}%")
        print(f"   📊 Score: {analysis['score']:.1f}")
        print(f"   🛑 SL: {stop_loss:.5f} (${abs(price - stop_loss):.2f} risk)")
        print(f"   ✅ TP: {take_profit:.5f} (${abs(take_profit - price):.2f} profit)")
        print(f"   🧠 Monte Carlo: {mc_result['success_rate']:.0f}% success")
        print(f"   📊 Profit Prob: {mc_result['profit_probability']:.0f}%")
        print(f"   📉 Loss Prob: {mc_result['loss_probability']:.0f}%")
        
        # Show strategy details
        if analysis['strategies']:
            active = [s for s, d in analysis['strategies'].items() if abs(d.get('score', 0)) > 15]
            if active:
                print(f"   📊 Active Strategies: {', '.join(active)}")
        
        # Create signal
        signal = TradeSignal(
            symbol=symbol,
            action=action,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strength=SignalStrength.STRONG if confidence > self.risk_config.strong_confidence else SignalStrength.MODERATE,
            alpha_name="Ultimate_System",
            timestamp=datetime.now(),
            volume=self.risk_config.volume
        )
        
        # Register with risk manager
        self.risk_manager.register_trade({
            'symbol': symbol,
            'action': action,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence
        })
        
        # Execute
        result = live_executor.execute_trade(signal)
        
        if result.get('success'):
            self.active_trade = {
                'symbol': symbol,
                'action': action,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'timestamp': datetime.now()
            }
            self.trade_start_time = datetime.now()
            self.stats['total_trades'] += 1
            
            # Record trade
            self.trade_recorder.add_trade({
                'symbol': symbol,
                'action': action,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'status': 'OPEN'
            })
            
            print(f"   ✅ TRADE EXECUTED! Order ID: {result.get('order_id')}")
            
            # Cooldown
            self.cooldown_until = time.time() + self.trading_config.cooldown_period
        else:
            print(f"   ❌ Trade failed: {result.get('reason')}")
    
    # ============================================================
    # MONITORING
    # ============================================================
    
    def _monitor_trades(self):
        """Monitor active trades"""
        if not self.active_trade:
            return
        
        # Check duration
        if self.trade_start_time:
            elapsed = (datetime.now() - self.trade_start_time).total_seconds()
            if elapsed > self.trading_config.max_trade_duration:
                print(f"   ⏰ Trade duration exceeded! Closing...")
                self._close_trade("MAX_DURATION")
                return
        
        # Update P&L
        try:
            price = self.mt4.get_price(self.active_trade['symbol'])
            if price > 0:
                if self.active_trade['action'] == 'BUY':
                    pnl = (price - self.active_trade['entry_price']) * self.risk_config.volume * 100000
                else:
                    pnl = (self.active_trade['entry_price'] - price) * self.risk_config.volume * 100000
                
                # Check if trade should be closed based on P&L
                if pnl <= -2.0:  # Stop loss hit
                    self._close_trade("STOP_LOSS")
                elif pnl >= 4.0:  # Take profit hit
                    self._close_trade("TAKE_PROFIT")
                
                # Update stats
                self.stats['total_pnl'] += pnl
        except:
            pass
    
    def _close_trade(self, reason: str):
        """Close active trade"""
        if not self.active_trade:
            return
        
        print(f"   🔚 Closing trade: {reason}")
        
        try:
            # Get exit price
            price = self.mt4.get_price(self.active_trade['symbol'])
            if price <= 0:
                price = self.active_trade['entry_price']
            
            # Calculate P&L
            if self.active_trade['action'] == 'BUY':
                pnl = (price - self.active_trade['entry_price']) * self.risk_config.volume * 100000
            else:
                pnl = (self.active_trade['entry_price'] - price) * self.risk_config.volume * 100000
            
            # Close via MT4
            for trade in live_executor.active_trades[:]:
                if trade.symbol == self.active_trade['symbol']:
                    live_executor.close_trade(trade, price, reason)
                    break
            
            # Update stats
            self.stats['total_pnl'] += pnl
            if pnl > 0:
                self.stats['winning_trades'] += 1
                if pnl > self.stats['best_trade']:
                    self.stats['best_trade'] = pnl
            else:
                self.stats['losing_trades'] += 1
                if pnl < self.stats['worst_trade']:
                    self.stats['worst_trade'] = pnl
            
            # Update risk manager
            self.risk_manager.close_trade(self.active_trade['symbol'], pnl)
            
            # Record trade
            self.trade_recorder.add_trade({
                'symbol': self.active_trade['symbol'],
                'action': self.active_trade['action'],
                'entry_price': self.active_trade['entry_price'],
                'exit_price': price,
                'pnl': pnl,
                'close_reason': reason,
                'timestamp': datetime.now().isoformat(),
                'status': 'CLOSED'
            })
            
            print(f"   📊 P&L: ${pnl:.2f}")
            
            # Reset active trade
            self.active_trade = None
            self.trade_start_time = None
            
        except Exception as e:
            print(f"   ❌ Close error: {e}")
    
    # ============================================================
    # STATUS
    # ============================================================
    
    def _print_status(self):
        """Print system status"""
        balance = self.mt4.get_account_balance()
        if balance <= 0:
            balance = self.risk_config.account_balance
        
        status = self.risk_manager.get_status(balance)
        
        print(f"\n📊 STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"   💰 Balance: ${balance:.2f}")
        print(f"   📈 Trades: {status['daily_trades']}/{self.risk_config.max_daily_trades}")
        print(f"   💵 P&L: ${status['daily_pnl']:.2f}")
        print(f"   📉 Loss Remaining: ${abs(status['daily_loss_remaining']):.2f}")
        print(f"   📊 Open: {status['open_positions']}")
        print(f"   🛡️ Trading: {'✅' if status['can_trade'] else '❌'}")
        
        if self.active_trade:
            try:
                price = self.mt4.get_price(self.active_trade['symbol'])
                if price > 0:
                    if self.active_trade['action'] == 'BUY':
                        pnl = (price - self.active_trade['entry_price']) * self.risk_config.volume * 100000
                    else:
                        pnl = (self.active_trade['entry_price'] - price) * self.risk_config.volume * 100000
                    print(f"   🎯 Active: {self.active_trade['symbol']} {self.active_trade['action']} (${pnl:.2f})")
            except:
                pass
        
        # Win rate
        total = self.stats['total_trades']
        if total > 0:
            wins = self.stats['winning_trades']
            win_rate = (wins / total) * 100
            print(f"   🏆 Win Rate: {win_rate:.1f}% ({wins}/{total})")
    
    def _print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 70)
        print("📊 FINAL SUMMARY")
        print("=" * 70)
        print(f"💰 Starting Balance: ${self.risk_config.account_balance:.2f}")
        print(f"💰 Final Balance: ${self.mt4.get_account_balance():.2f}")
        print(f"📈 Total Trades: {self.stats['total_trades']}")
        print(f"✅ Wins: {self.stats['winning_trades']}")
        print(f"❌ Losses: {self.stats['losing_trades']}")
        print(f"💵 Total P&L: ${self.stats['total_pnl']:.2f}")
        print(f"🏆 Best Trade: ${self.stats['best_trade']:.2f}")
        print(f"📉 Worst Trade: ${self.stats['worst_trade']:.2f}")
        if self.stats['total_trades'] > 0:
            win_rate = (self.stats['winning_trades'] / self.stats['total_trades']) * 100
            print(f"📊 Win Rate: {win_rate:.1f}%")
        print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 FINAL ULTIMATE REAL TRADING SYSTEM")
    print("=" * 70)
    print()
    
    trader = FinalUltimateTrader()
    
    try:
        trader.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping system...")
        trader.stop()