"""
Correlation-Based Pair Trading Module
- Identifies highly correlated asset pairs
- Tracks spread deviations
- Generates mean-reversion signals when spread diverges
- Calculates hedge ratios using cointegration
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import threading
import time


@dataclass
class PairConfig:
    """Configuration for pair trading."""
    # Correlation thresholds
    min_correlation: float = 0.7      # Minimum correlation to be a pair
    lookback_days: int = 30           # Days for correlation calculation
    spread_window: int = 20           # Period for z-score calculation
    
    # Entry/exit thresholds (z-scores)
    entry_zscore: float = 2.0         # Entry when spread > 2 sigma
    exit_zscore: float = 0.5          # Exit when spread reverts
    stop_zscore: float = 3.0          # Stop loss at 3 sigma
    
    # Position limits
    max_position_units: int = 5
    max_pair_exposure_pct: float = 0.10  # Max 10% per pair
    
    # Cointegration
    cointegration_pvalue_threshold: float = 0.05


@dataclass
class TradingPair:
    """Represents a trading pair and its current state."""
    asset1: str
    asset2: str
    correlation: float = 0.0
    hedge_ratio: float = 1.0          # How much of asset2 to trade per unit of asset1
    spread: float = 0.0
    spread_mean: float = 0.0
    spread_std: float = 1.0
    zscore: float = 0.0
    position: int = 0                  # 1=long spread, -1=short spread, 0=flat
    entry_zscore: float = 0.0
    last_signal: str = "NEUTRAL"       # LONG_SPREAD, SHORT_SPREAD, NEUTRAL
    pnl: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'asset1': self.asset1,
            'asset2': self.asset2,
            'correlation': round(self.correlation, 3),
            'hedge_ratio': round(self.hedge_ratio, 3),
            'spread': round(self.spread, 5),
            'zscore': round(self.zscore, 2),
            'position': self.position,
            'signal': self.last_signal,
            'pnl': round(self.pnl, 2)
        }


class PairDetector:
    """
    Detects correlated pairs for pair trading.
    """
    
    def __init__(self, config: Optional[PairConfig] = None):
        self.config = config or PairConfig()
        self.pairs: Dict[str, TradingPair] = {}
        self.price_history: Dict[str, deque] = {}
        self.last_update = None
    
    def update_price(self, asset: str, price: float, timestamp: datetime = None):
        """Update price history for an asset."""
        if asset not in self.price_history:
            self.price_history[asset] = deque(maxlen=self.config.lookback_days * 24)  # Hourly data
        
        self.price_history[asset].append({
            'price': price,
            'timestamp': timestamp or datetime.now()
        })
    
    def get_price_series(self, asset: str, hours: int = None) -> List[float]:
        """Get price series for an asset."""
        if asset not in self.price_history:
            return []
        
        if hours:
            recent = [p for p in self.price_history[asset] 
                     if (datetime.now() - p['timestamp']).total_seconds() < hours * 3600]
            return [p['price'] for p in recent]
        
        return [p['price'] for p in self.price_history[asset]]
    
    def calculate_correlation(self, prices1: List[float], prices2: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(prices1) < 20 or len(prices2) < 20:
            return 0.0
        
        returns1 = np.diff(np.log(prices1))
        returns2 = np.diff(np.log(prices2))
        
        min_len = min(len(returns1), len(returns2))
        if min_len < 10:
            return 0.0
        
        correlation = np.corrcoef(returns1[-min_len:], returns2[-min_len:])[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def calculate_hedge_ratio(self, prices1: List[float], prices2: List[float]) -> float:
        """
        Calculate hedge ratio using linear regression.
        price1 = hedge_ratio * price2 + intercept
        """
        if len(prices1) < 20 or len(prices2) < 20:
            return 1.0
        
        min_len = min(len(prices1), len(prices2))
        p1 = np.array(prices1[-min_len:])
        p2 = np.array(prices2[-min_len:])
        
        # Linear regression
        A = np.vstack([p2, np.ones(len(p2))]).T
        try:
            hedge_ratio, intercept = np.linalg.lstsq(A, p1, rcond=None)[0]
            return abs(hedge_ratio)
        except:
            return 1.0
    
    def test_cointegration(self, prices1: List[float], prices2: List[float]) -> float:
        """
        Test for cointegration using augmented Dickey-Fuller test.
        Returns p-value; lower p-value = stronger cointegration.
        """
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
        """
        Find all correlated pairs among assets.
        """
        pairs = []
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                asset1 = assets[i]
                asset2 = assets[j]
                
                prices1 = self.get_price_series(asset1)
                prices2 = self.get_price_series(asset2)
                
                if len(prices1) < 50 or len(prices2) < 50:
                    continue
                
                correlation = self.calculate_correlation(prices1, prices2)
                
                if correlation >= self.config.min_correlation:
                    hedge_ratio = self.calculate_hedge_ratio(prices1, prices2)
                    coint_pvalue = self.test_cointegration(prices1, prices2)
                    
                    # Only use cointegrated pairs
                    if coint_pvalue <= self.config.cointegration_pvalue_threshold:
                        pair = TradingPair(
                            asset1=asset1,
                            asset2=asset2,
                            correlation=correlation,
                            hedge_ratio=hedge_ratio
                        )
                        pairs.append(pair)
        
        # Sort by correlation
        pairs.sort(key=lambda x: x.correlation, reverse=True)
        return pairs
    
    def calculate_spread(self, pair: TradingPair) -> Tuple[float, float, float]:
        """
        Calculate current spread and its statistics.
        Spread = price1 - hedge_ratio * price2
        """
        prices1 = self.get_price_series(pair.asset1)
        prices2 = self.get_price_series(pair.asset2)
        
        if len(prices1) < self.config.spread_window or len(prices2) < self.config.spread_window:
            return 0.0, 0.0, 0.0
        
        min_len = min(len(prices1), len(prices2))
        p1 = np.array(prices1[-min_len:])
        p2 = np.array(prices2[-min_len:])
        
        spreads = p1 - pair.hedge_ratio * p2
        current_spread = spreads[-1]
        mean_spread = np.mean(spreads[-self.config.spread_window:])
        std_spread = np.std(spreads[-self.config.spread_window:])
        
        return current_spread, mean_spread, std_spread


class PairTrader:
    """
    Executes pair trading strategies based on spread deviations.
    """
    
    def __init__(self, detector: PairDetector, config: Optional[PairConfig] = None):
        self.detector = detector
        self.config = config or PairConfig()
        self.active_pairs: Dict[str, TradingPair] = {}
        self.trade_history = []
    
    def update_all_pairs(self, assets: List[str]):
        """Update all pairs and generate signals."""
        # Find all potential pairs
        potential_pairs = self.detector.find_pairs(assets)
        
        for pair in potential_pairs:
            # Calculate spread
            spread, mean, std = self.detector.calculate_spread(pair)
            pair.spread = spread
            pair.spread_mean = mean
            pair.spread_std = std
            pair.zscore = (spread - mean) / std if std > 0 else 0
            
            # Generate signal based on z-score
            pair_name = f"{pair.asset1}_{pair.asset2}"
            
            if pair.zscore > self.config.entry_zscore and pair.position <= 0:
                # Spread is too wide - expect mean reversion
                # Long spread = buy asset1, sell asset2 (short)
                pair.position = 1
                pair.entry_zscore = pair.zscore
                pair.last_signal = "LONG_SPREAD"
                
            elif pair.zscore < -self.config.entry_zscore and pair.position >= 0:
                # Spread is too narrow - expect widening
                # Short spread = sell asset1, buy asset2
                pair.position = -1
                pair.entry_zscore = pair.zscore
                pair.last_signal = "SHORT_SPREAD"
                
            elif abs(pair.zscore) <= self.config.exit_zscore and pair.position != 0:
                # Spread reverted to mean - close position
                # Calculate PnL
                if pair.position == 1:
                    # Closed long spread
                    pnl = (self.config.exit_zscore - pair.entry_zscore) / pair.entry_zscore
                else:
                    pnl = (pair.entry_zscore + self.config.exit_zscore) / abs(pair.entry_zscore)
                
                pair.pnl += pnl
                pair.position = 0
                pair.last_signal = "CLOSED"
                
                # Record trade
                self.trade_history.append({
                    'pair': pair_name,
                    'entry_zscore': pair.entry_zscore,
                    'exit_zscore': pair.zscore,
                    'pnl': pnl,
                    'timestamp': datetime.now()
                })
                
            elif abs(pair.zscore) >= self.config.stop_zscore and pair.position != 0:
                # Stop loss hit
                if pair.position == 1:
                    pnl = (self.config.stop_zscore - pair.entry_zscore) / pair.entry_zscore
                else:
                    pnl = (pair.entry_zscore + self.config.stop_zscore) / abs(pair.entry_zscore)
                
                pair.pnl += pnl
                pair.position = 0
                pair.last_signal = "STOPPED"
                
                self.trade_history.append({
                    'pair': pair_name,
                    'entry_zscore': pair.entry_zscore,
                    'exit_zscore': pair.zscore,
                    'pnl': pnl,
                    'timestamp': datetime.now(),
                    'reason': 'stop_loss'
                })
            
            self.active_pairs[pair_name] = pair
    
    def get_signals(self) -> Dict[str, Dict]:
        """Get current pair trading signals."""
        signals = {}
        for name, pair in self.active_pairs.items():
            if pair.last_signal in ['LONG_SPREAD', 'SHORT_SPREAD']:
                signals[name] = {
                    'signal': pair.last_signal,
                    'zscore': pair.zscore,
                    'asset1': pair.asset1,
                    'asset2': pair.asset2,
                    'hedge_ratio': pair.hedge_ratio,
                    'confidence': min(100, abs(pair.zscore) * 30),
                    'action1': 'BUY' if pair.position == 1 else 'SELL',
                    'action2': 'SELL' if pair.position == 1 else 'BUY'
                }
        return signals
    
    def get_pair_status(self) -> List[Dict]:
        """Get status of all monitored pairs."""
        return [pair.to_dict() for pair in self.active_pairs.values()]
    
    def get_performance(self) -> Dict:
        """Get pair trading performance metrics."""
        if not self.trade_history:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        
        return {
            'total_trades': len(self.trade_history),
            'winning_trades': len(winning_trades),
            'win_rate': len(winning_trades) / len(self.trade_history) * 100,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(self.trade_history),
            'best_trade': max(self.trade_history, key=lambda x: x['pnl'])['pnl'] if self.trade_history else 0,
            'worst_trade': min(self.trade_history, key=lambda x: x['pnl'])['pnl'] if self.trade_history else 0
        }


# ============================================================
# Integration with Main Trading System
# ============================================================

class PairTradingIntegration:
    """
    Integrates pair trading with your existing multi-agent system.
    """
    
    def __init__(self, config: Optional[PairConfig] = None):
        self.config = config or PairConfig()
        self.detector = PairDetector(config)
        self.trader = PairTrader(self.detector, config)
        self.assets = [
            'XAU/USD', 'XAG/USD', 'EURUSD', 'GBPUSD', 'USDJPY',
            'S&P500/USD', 'NAS100/USD', 'BCO/USD', 'WTICO/USD'
        ]
    
    def update_prices(self, prices: Dict[str, float]):
        """Update prices for all assets."""
        for asset, price in prices.items():
            self.detector.update_price(asset, price)
        
        # Update pair trading signals
        self.trader.update_all_pairs(self.assets)
    
    def get_trading_signals(self) -> Dict:
        """Get pair trading signals to integrate with main system."""
        signals = self.trader.get_signals()
        
        # Convert to format compatible with main system
        formatted_signals = {}
        for pair_name, signal in signals.items():
            formatted_signals[pair_name] = {
                'asset': pair_name,
                'action': signal['signal'],
                'confidence': signal['confidence'],
                'type': 'PAIR_TRADE',
                'details': {
                    'asset1': signal['asset1'],
                    'asset2': signal['asset2'],
                    'action1': signal['action1'],
                    'action2': signal['action2'],
                    'hedge_ratio': signal['hedge_ratio'],
                    'zscore': signal['zscore']
                }
            }
        
        return formatted_signals
    
    def get_status(self) -> Dict:
        """Get comprehensive pair trading status."""
        return {
            'active_pairs': self.trader.get_pair_status(),
            'performance': self.trader.get_performance(),
            'total_correlations': len(self.detector.price_history)
        }


# ============================================================
# Example Usage and Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CORRELATION-BASED PAIR TRADING - TEST")
    print("=" * 60)
    
    # Initialize
    pair_trader = PairTradingIntegration()
    
    # Simulate price updates
    print("\n📊 Simulating price updates...")
    
    # Generate correlated price movements
    np.random.seed(42)
    base_price = 100
    prices1 = [base_price]
    prices2 = [base_price * 0.8]
    
    for i in range(200):
        # Highly correlated movements
        shock = np.random.normal(0, 0.01)
        prices1.append(prices1[-1] * (1 + shock))
        prices2.append(prices2[-1] * (1 + shock * 0.95 + np.random.normal(0, 0.002)))
        
        # Create temporary divergence
        if 100 < i < 120:
            prices2[-1] = prices2[-1] * 0.95
        
        # Update the trader with simulated prices
        mock_prices = {
            'XAU/USD': prices1[-1],
            'XAG/USD': prices2[-1],
            'EURUSD': 1.0950 + np.random.normal(0, 0.001),
            'GBPUSD': 1.2850 + np.random.normal(0, 0.001)
        }
        
        pair_trader.update_prices(mock_prices)
        
        if i % 50 == 0:
            signals = pair_trader.get_trading_signals()
            if signals:
                print(f"\n📊 Signals at step {i}:")
                for name, signal in signals.items():
                    print(f"   {name}: {signal['action']} (conf: {signal['confidence']:.0f}%)")
    
    # Get final status
    print("\n" + "=" * 60)
    print("PAIR TRADING STATUS")
    print("=" * 60)
    
    status = pair_trader.get_status()
    print(f"\nActive Pairs: {len(status['active_pairs'])}")
    
    for pair in status['active_pairs'][:5]:
        print(f"\n   {pair['asset1']} - {pair['asset2']}")
        print(f"      Correlation: {pair['correlation']}")
        print(f"      Z-Score: {pair['zscore']}")
        print(f"      Signal: {pair['signal']}")
    
    perf = status['performance']
    print(f"\n📈 Performance:")
    print(f"   Total Trades: {perf['total_trades']}")
    print(f"   Win Rate: {perf['win_rate']:.1f}%")
    print(f"   Total PnL: {perf['total_pnl']:.4f}")
    
    print("\n✅ Pair trading module ready")
