"""
Correlation-Based Pair Trading System
- Automatic pair discovery using correlation and cointegration
- Real-time spread monitoring
- Mean-reversion trading signals
- Position management and risk controls
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import json
import os
import threading
import time
from enum import Enum


class PairStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    PAUSED = "paused"


class TradeDirection(Enum):
    LONG_SPREAD = "long_spread"      # Buy asset1, sell asset2
    SHORT_SPREAD = "short_spread"    # Sell asset1, buy asset2


@dataclass
class TradingPair:
    """Represents a tradable asset pair"""
    asset1: str
    asset2: str
    correlation: float = 0.0
    hedge_ratio: float = 1.0
    cointegration_pvalue: float = 0.0
    spread_mean: float = 0.0
    spread_std: float = 1.0
    current_spread: float = 0.0
    zscore: float = 0.0
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    stop_zscore: float = 3.0
    position: int = 0  # 1=long, -1=short, 0=flat
    pnl: float = 0.0
    trades_count: int = 0
    win_count: int = 0
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PairTrade:
    """Record of a completed pair trade"""
    pair_name: str
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_zscore: float
    exit_zscore: float
    pnl: float
    pnl_pct: float
    duration_minutes: float


class CorrelationDetector:
    """
    Detects correlated asset pairs using rolling correlation and cointegration tests.
    """
    
    def __init__(self, min_correlation: float = 0.7, 
                 lookback_days: int = 30,
                 min_data_points: int = 50):
        self.min_correlation = min_correlation
        self.lookback_days = lookback_days
        self.min_data_points = min_data_points
        self.price_history: Dict[str, deque] = {}
        self.correlation_cache: Dict[Tuple[str, str], float] = {}
        self.last_update = None
    
    def update_price(self, asset: str, price: float, timestamp: datetime = None):
        """Update price history for an asset"""
        if asset not in self.price_history:
            self.price_history[asset] = deque(maxlen=self.lookback_days * 24)
        
        self.price_history[asset].append({
            'price': price,
            'timestamp': timestamp or datetime.now()
        })
    
    def get_price_series(self, asset: str, hours: int = None) -> List[float]:
        """Get price series for an asset"""
        if asset not in self.price_history:
            return []
        
        if hours:
            cutoff = datetime.now() - timedelta(hours=hours)
            recent = [p for p in self.price_history[asset] 
                     if p['timestamp'] >= cutoff]
            return [p['price'] for p in recent]
        
        return [p['price'] for p in self.price_history[asset]]
    
    def calculate_correlation(self, prices1: List[float], prices2: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(prices1) < 20 or len(prices2) < 20:
            return 0.0
        
        # Use returns for correlation
        returns1 = np.diff(np.log(prices1))
        returns2 = np.diff(np.log(prices2))
        
        min_len = min(len(returns1), len(returns2))
        if min_len < 10:
            return 0.0
        
        correlation = np.corrcoef(returns1[-min_len:], returns2[-min_len:])[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def calculate_hedge_ratio(self, prices1: List[float], prices2: List[float]) -> float:
        """Calculate hedge ratio using linear regression"""
        if len(prices1) < 20 or len(prices2) < 20:
            return 1.0
        
        min_len = min(len(prices1), len(prices2))
        p1 = np.array(prices1[-min_len:])
        p2 = np.array(prices2[-min_len:])
        
        # Linear regression: p1 = hedge_ratio * p2 + intercept
        A = np.vstack([p2, np.ones(len(p2))]).T
        try:
            hedge_ratio, intercept = np.linalg.lstsq(A, p1, rcond=None)[0]
            return abs(hedge_ratio)
        except:
            return 1.0
    
    def test_cointegration(self, prices1: List[float], prices2: List[float]) -> float:
        """Test for cointegration using Augmented Dickey-Fuller test"""
        try:
            from statsmodels.tsa.stattools import adfuller
            from statsmodels.api import OLS, add_constant
            
            if len(prices1) < 30 or len(prices2) < 30:
                return 1.0
            
            min_len = min(len(prices1), len(prices2))
            y = np.array(prices1[-min_len:])
            x = np.array(prices2[-min_len:])
            
            # Run regression
            x_with_const = add_constant(x)
            model = OLS(y, x_with_const).fit()
            residuals = model.resid
            
            # ADF test on residuals
            adf_result = adfuller(residuals, autolag='AIC')
            p_value = adf_result[1]
            
            return p_value
        except ImportError:
            return 0.0  # Assume cointegrated if statsmodels not available
        except:
            return 1.0
    
    def find_pairs(self, assets: List[str]) -> List[TradingPair]:
        """Find all viable trading pairs among assets"""
        pairs = []
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                asset1 = assets[i]
                asset2 = assets[j]
                
                prices1 = self.get_price_series(asset1)
                prices2 = self.get_price_series(asset2)
                
                if len(prices1) < self.min_data_points or len(prices2) < self.min_data_points:
                    continue
                
                # Calculate metrics
                correlation = self.calculate_correlation(prices1, prices2)
                
                if correlation >= self.min_correlation:
                    hedge_ratio = self.calculate_hedge_ratio(prices1, prices2)
                    coint_pvalue = self.test_cointegration(prices1, prices2)
                    
                    # Only use cointegrated pairs (p-value < 0.05)
                    if coint_pvalue < 0.05:
                        pair = TradingPair(
                            asset1=asset1,
                            asset2=asset2,
                            correlation=correlation,
                            hedge_ratio=hedge_ratio,
                            cointegration_pvalue=coint_pvalue
                        )
                        pairs.append(pair)
        
        # Sort by correlation (highest first)
        pairs.sort(key=lambda x: x.correlation, reverse=True)
        
        # Cache results
        for pair in pairs:
            self.correlation_cache[(pair.asset1, pair.asset2)] = pair.correlation
        
        return pairs


class SpreadCalculator:
    """Calculates and tracks spread between two assets"""
    
    def __init__(self, lookback_window: int = 20):
        self.lookback_window = lookback_window
        self.spread_history = deque(maxlen=lookback_window * 2)
    
    def calculate_spread(self, price1: float, price2: float, hedge_ratio: float) -> float:
        """Calculate current spread: price1 - hedge_ratio * price2"""
        return price1 - hedge_ratio * price2
    
    def update_spread_history(self, spread: float):
        """Update spread history for statistical calculation"""
        self.spread_history.append(spread)
    
    def get_spread_stats(self) -> Tuple[float, float]:
        """Get mean and standard deviation of recent spreads"""
        if len(self.spread_history) < self.lookback_window:
            return 0.0, 1.0
        
        recent = list(self.spread_history)[-self.lookback_window:]
        return np.mean(recent), np.std(recent)
    
    def calculate_zscore(self, spread: float, mean: float, std: float) -> float:
        """Calculate z-score of current spread"""
        if std == 0:
            return 0.0
        return (spread - mean) / std


class PairTradeExecutor:
    """Executes and manages pair trades"""
    
    def __init__(self, initial_capital: float = 100000, 
                 max_position_pct: float = 0.1,
                 commission_pct: float = 0.001):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.commission_pct = commission_pct
        self.active_trades: Dict[str, TradingPair] = {}
        self.trade_history: List[PairTrade] = []
        self.daily_pnl = 0.0
        self.current_date = datetime.now().date()
    
    def calculate_position_size(self, pair: TradingPair, zscore: float) -> float:
        """Calculate position size based on z-score deviation"""
        # Larger deviation = larger position (up to max)
        deviation = abs(zscore) - pair.entry_zscore
        size_pct = min(self.max_position_pct, deviation / pair.stop_zscore * self.max_position_pct)
        return size_pct
    
    def should_enter(self, pair: TradingPair, zscore: float) -> Tuple[bool, TradeDirection, float]:
        """Determine if we should enter a trade"""
        if pair.position != 0:
            return False, None, 0
        
        if zscore > pair.entry_zscore:
            # Spread too wide - expect mean reversion
            # Long spread = buy asset1, sell asset2
            return True, TradeDirection.LONG_SPREAD, abs(zscore)
        elif zscore < -pair.entry_zscore:
            # Spread too narrow - expect widening
            # Short spread = sell asset1, buy asset2
            return True, TradeDirection.SHORT_SPREAD, abs(zscore)
        
        return False, None, 0
    
    def should_exit(self, pair: TradingPair, zscore: float) -> Tuple[bool, str]:
        """Determine if we should exit the trade"""
        if pair.position == 0:
            return False, ""
        
        # Exit on mean reversion
        if abs(zscore) <= pair.exit_zscore:
            return True, "mean_reversion"
        
        # Stop loss
        if abs(zscore) >= pair.stop_zscore:
            return True, "stop_loss"
        
        # Timeout after 5 days
        if (datetime.now() - pair.created_at).days >= 5:
            return True, "timeout"
        
        return False, ""
    
    def execute_entry(self, pair: TradingPair, direction: TradeDirection, 
                      current_price1: float, current_price2: float, zscore: float) -> Dict:
        """Execute trade entry"""
        pair_name = f"{pair.asset1}_{pair.asset2}"
        
        # Calculate position size
        size_pct = self.calculate_position_size(pair, zscore)
        position_value = self.capital * size_pct
        
        if direction == TradeDirection.LONG_SPREAD:
            # Buy asset1, sell asset2
            size1 = position_value / current_price1
            size2 = position_value / current_price2 / pair.hedge_ratio
            
            pair.position = 1
            pair.entry_zscore = zscore
            
            entry_msg = f"LONG SPREAD: Buy {pair.asset1}, Sell {pair.asset2}"
        else:
            # Sell asset1, buy asset2
            size1 = position_value / current_price1
            size2 = position_value / current_price2 / pair.hedge_ratio
            
            pair.position = -1
            pair.entry_zscore = zscore
            
            entry_msg = f"SHORT SPREAD: Sell {pair.asset1}, Buy {pair.asset2}"
        
        # Store position sizes
        pair.position_size1 = size1
        pair.position_size2 = size2
        pair.entry_price1 = current_price1
        pair.entry_price2 = current_price2
        
        self.active_trades[pair_name] = pair
        
        # Reduce capital (commission)
        commission = position_value * self.commission_pct * 2
        self.capital -= commission
        
        return {
            'entered': True,
            'pair': pair_name,
            'direction': direction.value,
            'position_value': position_value,
            'commission': commission,
            'message': entry_msg
        }
    
    def execute_exit(self, pair: TradingPair, current_price1: float, 
                     current_price2: float, zscore: float, reason: str) -> Dict:
        """Execute trade exit"""
        pair_name = f"{pair.asset1}_{pair.asset2}"
        
        # Calculate PnL
        if pair.position == 1:  # Long spread
            pnl1 = (current_price1 - pair.entry_price1) * pair.position_size1
            pnl2 = (pair.entry_price2 - current_price2) * pair.position_size2
        else:  # Short spread
            pnl1 = (pair.entry_price1 - current_price1) * pair.position_size1
            pnl2 = (current_price2 - pair.entry_price2) * pair.position_size2
        
        pnl = pnl1 + pnl2
        pnl -= (pair.position_size1 * current_price1 + pair.position_size2 * current_price2) * self.commission_pct
        
        # Update capital
        self.capital += pnl
        pair.pnl += pnl
        pair.trades_count += 1
        
        if pnl > 0:
            pair.win_count += 1
        
        # Record trade
        trade = PairTrade(
            pair_name=pair_name,
            entry_time=pair.created_at,
            exit_time=datetime.now(),
            direction='LONG' if pair.position == 1 else 'SHORT',
            entry_zscore=pair.entry_zscore,
            exit_zscore=zscore,
            pnl=pnl,
            pnl_pct=pnl / (pair.entry_price1 * pair.position_size1) * 100,
            duration_minutes=(datetime.now() - pair.created_at).total_seconds() / 60
        )
        self.trade_history.append(trade)
        
        # Update daily PnL
        today = datetime.now().date()
        if today != self.current_date:
            self.daily_pnl = 0
            self.current_date = today
        self.daily_pnl += pnl
        
        # Remove from active trades
        pair.position = 0
        pair.status = "closed"
        if pair_name in self.active_trades:
            del self.active_trades[pair_name]
        
        return {
            'exited': True,
            'pair': pair_name,
            'pnl': pnl,
            'pnl_pct': trade.pnl_pct,
            'reason': reason,
            'message': f"Closed {direction}: PnL ${pnl:.2f} ({trade.pnl_pct:.2f}%)"
        }
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        return self.capital
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.trade_history:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        winning_trades = [t for t in self.trade_history if t.pnl > 0]
        total_pnl = sum(t.pnl for t in self.trade_history)
        
        # Calculate Sharpe ratio
        daily_returns = []
        # Simplified Sharpe calculation
        if len(self.trade_history) > 5:
            returns = [t.pnl_pct for t in self.trade_history]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)
        else:
            sharpe = 0
        
        return {
            'total_trades': len(self.trade_history),
            'winning_trades': len(winning_trades),
            'win_rate': len(winning_trades) / len(self.trade_history) * 100 if self.trade_history else 0,
            'total_pnl': total_pnl,
            'total_return_pct': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'sharpe_ratio': sharpe,
            'avg_trade_pnl': total_pnl / len(self.trade_history) if self.trade_history else 0,
            'best_trade': max(t.pnl for t in self.trade_history) if self.trade_history else 0,
            'worst_trade': min(t.pnl for t in self.trade_history) if self.trade_history else 0
        }


class PairTradingSystem:
    """
    Complete pair trading system integrating detection, monitoring, and execution.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.detector = CorrelationDetector(
            min_correlation=self.config.get('min_correlation', 0.7),
            lookback_days=self.config.get('lookback_days', 30)
        )
        self.executor = PairTradeExecutor(
            initial_capital=self.config.get('initial_capital', 100000),
            max_position_pct=self.config.get('max_position_pct', 0.1)
        )
        self.spread_calculators: Dict[str, SpreadCalculator] = {}
        self.trading_pairs: Dict[str, TradingPair] = {}
        self.assets = [
            'XAU/USD', 'XAG/USD', 'EURUSD', 'GBPUSD', 'USDJPY',
            'S&P500/USD', 'NAS100/USD', 'BCO/USD', 'WTICO/USD'
        ]
        self.is_running = False
        self._thread = None
        
        # Create data directory
        os.makedirs('pair_trading_data', exist_ok=True)
    
    def update_prices(self, prices: Dict[str, float]):
        """Update prices for all assets"""
        for asset, price in prices.items():
            if asset in self.assets or asset.replace('/', '_') in self.assets:
                self.detector.update_price(asset, price)
    
    def discover_pairs(self) -> List[TradingPair]:
        """Discover new trading pairs"""
        new_pairs = self.detector.find_pairs(self.assets)
        
        # Add to trading pairs if not already tracked
        for pair in new_pairs:
            pair_name = f"{pair.asset1}_{pair.asset2}"
            if pair_name not in self.trading_pairs:
                self.trading_pairs[pair_name] = pair
                self.spread_calculators[pair_name] = SpreadCalculator()
                print(f"📊 New pair discovered: {pair.asset1} - {pair.asset2} (corr: {pair.correlation:.3f})")
        
        return new_pairs
    
    def update_pair_status(self):
        """Update spread and z-score for all trading pairs"""
        for pair_name, pair in self.trading_pairs.items():
            # Get current prices
            prices1 = self.detector.get_price_series(pair.asset1, hours=1)
            prices2 = self.detector.get_price_series(pair.asset2, hours=1)
            
            if not prices1 or not prices2:
                continue
            
            current_price1 = prices1[-1]
            current_price2 = prices2[-1]
            
            # Calculate spread
            spread = self.spread_calculators[pair_name].calculate_spread(
                current_price1, current_price2, pair.hedge_ratio
            )
            pair.current_spread = spread
            
            # Update spread history
            self.spread_calculators[pair_name].update_spread_history(spread)
            
            # Calculate statistics and z-score
            mean, std = self.spread_calculators[pair_name].get_spread_stats()
            pair.spread_mean = mean
            pair.spread_std = std
            pair.zscore = self.spread_calculators[pair_name].calculate_zscore(spread, mean, std)
            pair.last_updated = datetime.now()
    
    def check_trade_signals(self) -> List[Dict]:
        """Check for trade signals on all pairs"""
        signals = []
        
        for pair_name, pair in self.trading_pairs.items():
            # Skip if trade already active
            if pair_name in self.executor.active_trades:
                continue
            
            # Get current prices
            prices1 = self.detector.get_price_series(pair.asset1, hours=1)
            prices2 = self.detector.get_price_series(pair.asset2, hours=1)
            
            if not prices1 or not prices2:
                continue
            
            current_price1 = prices1[-1]
            current_price2 = prices2[-1]
            
            # Check entry conditions
            should_enter, direction, deviation = self.executor.should_enter(pair, pair.zscore)
            
            if should_enter:
                signal = {
                    'pair_name': pair_name,
                    'asset1': pair.asset1,
                    'asset2': pair.asset2,
                    'direction': direction.value,
                    'zscore': pair.zscore,
                    'deviation': deviation,
                    'hedge_ratio': pair.hedge_ratio,
                    'correlation': pair.correlation,
                    'confidence': min(95, 50 + deviation * 20),
                    'price1': current_price1,
                    'price2': current_price2
                }
                signals.append(signal)
        
        return signals
    
    def execute_signal(self, signal: Dict) -> Dict:
        """Execute a trading signal"""
        pair_name = signal['pair_name']
        pair = self.trading_pairs[pair_name]
        
        direction = TradeDirection.LONG_SPREAD if signal['direction'] == 'long_spread' else TradeDirection.SHORT_SPREAD
        
        result = self.executor.execute_entry(
            pair, direction, signal['price1'], signal['price2'], signal['zscore']
        )
        
        return result
    
    def monitor_active_trades(self) -> List[Dict]:
        """Monitor and close active trades when conditions met"""
        closed_trades = []
        
        for pair_name, pair in list(self.executor.active_trades.items()):
            # Get current prices
            prices1 = self.detector.get_price_series(pair.asset1, hours=1)
            prices2 = self.detector.get_price_series(pair.asset2, hours=1)
            
            if not prices1 or not prices2:
                continue
            
            current_price1 = prices1[-1]
            current_price2 = prices2[-1]
            
            # Update spread
            spread = self.spread_calculators[pair_name].calculate_spread(
                current_price1, current_price2, pair.hedge_ratio
            )
            mean, std = self.spread_calculators[pair_name].get_spread_stats()
            zscore = self.spread_calculators[pair_name].calculate_zscore(spread, mean, std)
            
            # Check exit conditions
            should_exit, reason = self.executor.should_exit(pair, zscore)
            
            if should_exit:
                result = self.executor.execute_exit(
                    pair, current_price1, current_price2, zscore, reason
                )
                closed_trades.append(result)
        
        return closed_trades
    
    def run_cycle(self) -> Dict:
        """Run one complete trading cycle"""
        # Update all pair statuses
        self.update_pair_status()
        
        # Discover new pairs (periodically)
        if datetime.now().hour % 6 == 0 and datetime.now().minute < 5:
            self.discover_pairs()
        
        # Monitor existing trades
        closed = self.monitor_active_trades()
        
        # Check for new signals
        signals = self.check_trade_signals()
        
        executed = []
        for signal in signals:
            result = self.execute_signal(signal)
            executed.append(result)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'active_trades': len(self.executor.active_trades),
            'signals_found': len(signals),
            'trades_executed': len(executed),
            'trades_closed': len(closed),
            'portfolio_value': self.executor.get_portfolio_value(),
            'total_return_pct': (self.executor.get_portfolio_value() - self.executor.initial_capital) / self.executor.initial_capital * 100
        }
    
    def start_auto_trading(self, cycle_seconds: int = 60):
        """Start automatic trading in background"""
        if self.is_running:
            return
        
        self.is_running = True
        
        def trading_loop():
            while self.is_running:
                try:
                    result = self.run_cycle()
                    if result['trades_executed'] > 0 or result['trades_closed'] > 0:
                        print(f"📊 Pair Trading: {result['trades_executed']} entered, {result['trades_closed']} closed")
                        print(f"   Portfolio: ${result['portfolio_value']:,.2f} ({result['total_return_pct']:.2f}%)")
                    time.sleep(cycle_seconds)
                except Exception as e:
                    print(f"Pair trading error: {e}")
                    time.sleep(cycle_seconds)
        
        self._thread = threading.Thread(target=trading_loop, daemon=True)
        self._thread.start()
        print("🔄 Pair trading system started")
    
    def stop_auto_trading(self):
        """Stop automatic trading"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("⏹️ Pair trading system stopped")
    
    def get_status(self) -> Dict:
        """Get complete system status"""
        return {
            'active_pairs': len(self.trading_pairs),
            'active_trades': len(self.executor.active_trades),
            'portfolio_value': self.executor.get_portfolio_value(),
            'total_return_pct': (self.executor.get_portfolio_value() - self.executor.initial_capital) / self.executor.initial_capital * 100,
            'performance': self.executor.get_performance_stats(),
            'active_positions': [
                {
                    'pair': name,
                    'direction': 'LONG_SPREAD' if p.position == 1 else 'SHORT_SPREAD',
                    'entry_zscore': p.entry_zscore,
                    'current_zscore': p.zscore,
                    'pnl': p.pnl
                }
                for name, p in self.executor.active_trades.items()
            ]
        }


# ============================================================
# Integration with Main Trading System
# ============================================================

class PairTradingIntegration:
    """Integrates pair trading with your main multi-agent system"""
    
    def __init__(self):
        self.pair_system = PairTradingSystem()
        self.telegram_bot = None
    
    def set_telegram_bot(self, bot):
        """Set Telegram bot for notifications"""
        self.telegram_bot = bot
    
    def update_prices(self, prices: Dict[str, float]):
        """Update prices from main system"""
        self.pair_system.update_prices(prices)
    
    def get_trading_signals(self) -> List[Dict]:
        """Get pair trading signals to merge with agent votes"""
        signals = self.pair_system.check_trade_signals()
        
        # Convert to format compatible with main system
        formatted_signals = []
        for signal in signals:
            formatted_signals.append({
                'type': 'PAIR_TRADE',
                'asset': signal['pair_name'],
                'action': 'BUY' if 'long' in signal['direction'] else 'SELL',
                'confidence': signal['confidence'],
                'reasoning': f"Pair trade: {signal['asset1']} - {signal['asset2']} at z-score {signal['zscore']:.2f}",
                'details': signal
            })
        
        return formatted_signals
    
    def run_cycle(self) -> Dict:
        """Run one pair trading cycle"""
        return self.pair_system.run_cycle()
    
    def start(self):
        """Start pair trading system"""
        self.pair_system.start_auto_trading(cycle_seconds=60)
    
    def stop(self):
        """Stop pair trading system"""
        self.pair_system.stop_auto_trading()
    
    def get_status_message(self) -> str:
        """Get status message for Telegram"""
        status = self.pair_system.get_status()
        perf = status['performance']
        
        message = f"""
📊 *PAIR TRADING SYSTEM*

💰 *Portfolio:* ${status['portfolio_value']:,.2f}
📈 *Return:* {status['total_return_pct']:.2f}%

🎯 *Performance:*
   • Trades: {perf['total_trades']}
   • Win Rate: {perf['win_rate']:.1f}%
   • Sharpe: {perf['sharpe_ratio']:.2f}
   • Total PnL: ${perf['total_pnl']:.2f}

🔗 *Active Pairs:* {status['active_pairs']}
🎲 *Open Positions:* {status['active_trades']}

📋 *Active Positions:*
"""
        for pos in status['active_positions'][:5]:
            message += f"\n   • {pos['pair']}: {pos['direction']} (z={pos['current_zscore']:.2f})"
        
        return message


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("PAIR TRADING SYSTEM - TEST")
    print("=" * 60)
    
    # Initialize system
    pair_system = PairTradingSystem()
    
    # Simulate price updates
    print("\n📊 Simulating correlated price movements...")
    
    # Generate synthetic data for correlated pairs
    import random
    np.random.seed(42)
    
    # Simulate gold and silver (correlated)
    gold_prices = [2000]
    silver_prices = [25]
    
    for i in range(200):
        # Correlated movement
        shock = np.random.normal(0, 0.005)
        gold_prices.append(gold_prices[-1] * (1 + shock))
        silver_prices.append(silver_prices[-1] * (1 + shock * 0.9 + np.random.normal(0, 0.001)))
        
        # Create temporary divergence
        if 100 < i < 120:
            silver_prices[-1] = silver_prices[-1] * 0.95
        
        # Update system
        prices = {
            'XAU/USD': gold_prices[-1],
            'XAG/USD': silver_prices[-1],
            'EURUSD': 1.0950 + np.random.normal(0, 0.001),
            'GBPUSD': 1.2850 + np.random.normal(0, 0.001)
        }
        
        pair_system.update_prices(prices)
        
        if i % 50 == 0:
            pair_system.run_cycle()
    
    # Get final status
    print("\n" + "=" * 60)
    status = pair_system.get_status()
    print(json.dumps(status, indent=2, default=str))
    
    print("\n✅ Pair trading system ready")
