"""
Walk-Forward Analysis Module
- Validates strategy robustness on out-of-sample data
- Automatically retrains models periodically
- Tracks performance metrics over time
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import threading
import time


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""
    # Time periods
    train_days: int = 90       # Training period length
    test_days: int = 10        # Testing period length
    retrain_frequency_days: int = 7  # Retrain every 7 days
    
    # Performance thresholds
    min_sharpe_ratio: float = 0.5
    min_win_rate: float = 0.45
    max_drawdown_pct: float = 0.15
    
    # Data sources
    data_dir: str = "market_data"
    results_dir: str = "walk_forward_results"


@dataclass
class WalkForwardResult:
    """Results from a walk-forward test period."""
    period_start: datetime
    period_end: datetime
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    # Performance metrics
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    num_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Model info
    model_version: str = ""
    features_used: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'train_start': self.train_start.isoformat(),
            'train_end': self.train_end.isoformat(),
            'test_start': self.test_start.isoformat(),
            'test_end': self.test_end.isoformat(),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'win_rate': round(self.win_rate * 100, 1),
            'total_return': round(self.total_return * 100, 2),
            'max_drawdown': round(self.max_drawdown * 100, 2),
            'num_trades': self.num_trades,
            'avg_win': round(self.avg_win * 100, 2),
            'avg_loss': round(self.avg_loss * 100, 2),
            'profit_factor': round(self.profit_factor, 2),
            'model_version': self.model_version
        }


class WalkForwardAnalyzer:
    """
    Walk-Forward Analysis Harness.
    Tests strategy on rolling out-of-sample periods.
    """
    
    def __init__(self, config: Optional[WalkForwardConfig] = None):
        self.config = config or WalkForwardConfig()
        self.results: List[WalkForwardResult] = []
        self.current_performance = {}
        self.is_running = False
        self._thread = None
        
        # Create directories
        os.makedirs(self.config.data_dir, exist_ok=True)
        os.makedirs(self.config.results_dir, exist_ok=True)
        
        # Load previous results
        self._load_results()
    
    def _load_results(self):
        """Load previous walk-forward results."""
        results_file = os.path.join(self.config.results_dir, "walk_forward_results.json")
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    self.results = [WalkForwardResult(**r) for r in data.get('results', [])]
                print(f"📊 Loaded {len(self.results)} previous walk-forward results")
            except Exception as e:
                print(f"⚠️ Failed to load results: {e}")
    
    def _save_results(self):
        """Save walk-forward results."""
        results_file = os.path.join(self.config.results_dir, "walk_forward_results.json")
        try:
            with open(results_file, 'w') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'config': {
                        'train_days': self.config.train_days,
                        'test_days': self.config.test_days,
                        'retrain_frequency_days': self.config.retrain_frequency_days
                    },
                    'results': [r.to_dict() for r in self.results]
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save results: {e}")
    
    def load_market_data(self, asset: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Load market data for a specific period.
        Replace with your actual data source (OANDA, CSV, etc.)
        """
        # This is a placeholder - integrate with your actual data source
        # For now, generates synthetic data
        days = (end_date - start_date).days
        dates = pd.date_range(start=start_date, end=end_date, freq='1H')
        
        np.random.seed(hash(asset) % 2**32)
        returns = np.random.normal(0.0001, 0.01, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'datetime': dates,
            'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
            'high': prices * (1 + abs(np.random.normal(0, 0.003, len(dates)))),
            'low': prices * (1 - abs(np.random.normal(0, 0.003, len(dates)))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        
        return df
    
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """
        Calculate performance metrics from trade list.
        """
        if not trades:
            return {
                'sharpe_ratio': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'num_trades': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        pnls = [t['pnl'] for t in trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        total_return = sum(pnls)
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        # Calculate drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / (running_max + 1e-10)
        max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
        
        # Sharpe ratio (assuming 252 trading days, 6.5 hours per day)
        if len(pnls) > 1:
            sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252 * 6.5)
        else:
            sharpe = 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'num_trades': len(trades),
            'avg_win': np.mean(winning_trades) if winning_trades else 0,
            'avg_loss': abs(np.mean(losing_trades)) if losing_trades else 0,
            'profit_factor': profit_factor
        }
    
    def run_walk_forward(self, asset: str, strategy_func, start_date: datetime, 
                         end_date: datetime) -> List[WalkForwardResult]:
        """
        Run walk-forward analysis.
        
        Args:
            asset: Asset symbol
            strategy_func: Function that takes (train_data, test_data) and returns trades
            start_date: Start of analysis period
            end_date: End of analysis period
        """
        print(f"\n{'='*60}")
        print(f"WALK-FORWARD ANALYSIS: {asset}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Train: {self.config.train_days} days, Test: {self.config.test_days} days")
        print(f"{'='*60}")
        
        current_start = start_date
        results = []
        period_num = 0
        
        while current_start + timedelta(days=self.config.train_days + self.config.test_days) <= end_date:
            period_num += 1
            
            # Define training period
            train_start = current_start
            train_end = current_start + timedelta(days=self.config.train_days)
            
            # Define testing period
            test_start = train_end
            test_end = test_start + timedelta(days=self.config.test_days)
            
            print(f"\n📊 Period {period_num}: {test_start.date()} to {test_end.date()}")
            print(f"   Training: {train_start.date()} to {train_end.date()}")
            
            # Load data
            train_data = self.load_market_data(asset, train_start, train_end)
            test_data = self.load_market_data(asset, test_start, test_end)
            
            # Run strategy
            trades = strategy_func(train_data, test_data)
            
            # Calculate performance
            metrics = self.calculate_performance_metrics(trades)
            
            # Create result
            result = WalkForwardResult(
                period_start=current_start,
                period_end=test_end,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                **metrics
            )
            
            results.append(result)
            
            # Print summary
            print(f"   Trades: {result.num_trades}")
            print(f"   Win Rate: {result.win_rate*100:.1f}%")
            print(f"   Return: {result.total_return*100:.2f}%")
            print(f"   Sharpe: {result.sharpe_ratio:.2f}")
            print(f"   Max DD: {result.max_drawdown*100:.2f}%")
            
            # Check if strategy passed
            passed = (result.sharpe_ratio >= self.config.min_sharpe_ratio and
                     result.win_rate >= self.config.min_win_rate and
                     result.max_drawdown <= self.config.max_drawdown_pct)
            
            print(f"   {'✅ PASSED' if passed else '❌ FAILED'}")
            
            # Move to next period
            current_start += timedelta(days=self.config.test_days)
        
        # Save results
        self.results.extend(results)
        self._save_results()
        
        # Print overall summary
        self.print_summary()
        
        return results
    
    def print_summary(self):
        """Print overall walk-forward summary."""
        if not self.results:
            print("No results to display")
            return
        
        print("\n" + "=" * 60)
        print("WALK-FORWARD SUMMARY")
        print("=" * 60)
        
        # Calculate aggregate metrics
        total_trades = sum(r.num_trades for r in self.results)
        avg_win_rate = np.mean([r.win_rate for r in self.results])
        avg_sharpe = np.mean([r.sharpe_ratio for r in self.results])
        avg_return = np.mean([r.total_return for r in self.results])
        avg_dd = np.mean([r.max_drawdown for r in self.results])
        
        passed_count = sum(1 for r in self.results 
                          if r.sharpe_ratio >= self.config.min_sharpe_ratio and
                             r.win_rate >= self.config.min_win_rate and
                             r.max_drawdown <= self.config.max_drawdown_pct)
        
        print(f"Total Periods: {len(self.results)}")
        print(f"Passed: {passed_count}/{len(self.results)} ({passed_count/len(self.results)*100:.1f}%)")
        print(f"\nAverage Metrics:")
        print(f"   Win Rate: {avg_win_rate*100:.1f}%")
        print(f"   Sharpe: {avg_sharpe:.2f}")
        print(f"   Return: {avg_return*100:.2f}%")
        print(f"   Max Drawdown: {avg_dd*100:.2f}%")
        print(f"   Total Trades: {total_trades}")
        
        # Determine if strategy is robust
        is_robust = passed_count / len(self.results) >= 0.7
        print(f"\n✅ Strategy is {'ROBUST' if is_robust else 'NOT ROBUST'} (70%+ passing rate required)")
    
    def get_latest_performance(self) -> Dict:
        """Get latest performance metrics."""
        if not self.results:
            return {'status': 'No data yet'}
        
        latest = self.results[-1]
        return {
            'status': 'Active',
            'last_test_date': latest.test_end.isoformat(),
            'win_rate': latest.win_rate * 100,
            'sharpe_ratio': latest.sharpe_ratio,
            'total_return': latest.total_return * 100,
            'max_drawdown': latest.max_drawdown * 100,
            'num_trades': latest.num_trades,
            'is_healthy': (latest.sharpe_ratio >= self.config.min_sharpe_ratio and
                          latest.win_rate >= self.config.min_win_rate and
                          latest.max_drawdown <= self.config.max_drawdown_pct)
        }


class AutoRetrainer:
    """
    Automatic model retraining based on walk-forward results.
    """
    
    def __init__(self, analyzer: WalkForwardAnalyzer, retrain_callback):
        """
        Args:
            analyzer: WalkForwardAnalyzer instance
            retrain_callback: Function to call when retraining is needed
        """
        self.analyzer = analyzer
        self.retrain_callback = retrain_callback
        self.last_retrain = datetime.now() - timedelta(days=analyzer.config.retrain_frequency_days)
        self.is_running = False
        
    def check_and_retrain(self) -> bool:
        """
        Check if retraining is needed based on:
        1. Time since last retrain
        2. Recent performance degradation
        """
        now = datetime.now()
        days_since_retrain = (now - self.last_retrain).days
        
        # Check if it's time to retrain
        if days_since_retrain >= self.analyzer.config.retrain_frequency_days:
            print(f"⏰ Time to retrain (last retrain: {days_since_retrain} days ago)")
            return self._perform_retrain()
        
        # Check performance degradation
        if self.analyzer.results:
            recent_results = self.analyzer.results[-3:]
            if len(recent_results) >= 3:
                avg_win_rate = np.mean([r.win_rate for r in recent_results])
                if avg_win_rate < self.analyzer.config.min_win_rate:
                    print(f"⚠️ Performance degradation detected (Win rate: {avg_win_rate*100:.1f}%)")
                    return self._perform_retrain()
        
        return False
    
    def _perform_retrain(self) -> bool:
        """Execute retraining."""
        print(f"🔄 Starting model retraining...")
        
        try:
            # Call the retrain callback
            success = self.retrain_callback()
            
            if success:
                self.last_retrain = datetime.now()
                print(f"✅ Model retrained successfully")
                
                # Save retrain record
                record = {
                    'timestamp': self.last_retrain.isoformat(),
                    'success': True
                }
                retrain_file = os.path.join(self.analyzer.config.results_dir, "retrain_history.json")
                
                history = []
                if os.path.exists(retrain_file):
                    with open(retrain_file, 'r') as f:
                        history = json.load(f)
                
                history.append(record)
                with open(retrain_file, 'w') as f:
                    json.dump(history, f, indent=2)
            else:
                print(f"❌ Retraining failed")
            
            return success
            
        except Exception as e:
            print(f"❌ Retraining error: {e}")
            return False
    
    def start_auto_retrain(self, check_interval_hours: int = 24):
        """Start automatic retraining in background thread."""
        if self.is_running:
            return
        
        self.is_running = True
        
        def retrain_loop():
            while self.is_running:
                try:
                    self.check_and_retrain()
                    time.sleep(check_interval_hours * 3600)
                except Exception as e:
                    print(f"Auto-retrain error: {e}")
                    time.sleep(3600)
        
        self._thread = threading.Thread(target=retrain_loop, daemon=True)
        self._thread.start()
        print(f"🤖 Auto-retrain started (check every {check_interval_hours} hours)")
    
    def stop_auto_retrain(self):
        """Stop automatic retraining."""
        self.is_running = False
        print("Auto-retrain stopped")


# ============================================================
# Example Strategy Function (Replace with your actual strategy)
# ============================================================

def example_strategy(train_data: pd.DataFrame, test_data: pd.DataFrame) -> List[Dict]:
    """
    Example strategy that generates trades based on moving average crossover.
    Replace with your actual agent-based strategy.
    """
    trades = []
    
    # Simple moving average strategy (example)
    train_data['ma_fast'] = train_data['close'].rolling(10).mean()
    train_data['ma_slow'] = train_data['close'].rolling(30).mean()
    test_data['ma_fast'] = test_data['close'].rolling(10).mean()
    test_data['ma_slow'] = test_data['close'].rolling(30).mean()
    
    position = None
    entry_price = 0
    
    for i in range(1, len(test_data)):
        if test_data['ma_fast'].iloc[i] > test_data['ma_slow'].iloc[i] and position != 'long':
            if position == 'short':
                # Close short
                pnl = (entry_price - test_data['close'].iloc[i]) / entry_price
                trades.append({'pnl': pnl, 'type': 'close_short'})
            # Open long
            position = 'long'
            entry_price = test_data['close'].iloc[i]
            trades.append({'pnl': 0, 'type': 'open_long', 'entry': entry_price})
            
        elif test_data['ma_fast'].iloc[i] < test_data['ma_slow'].iloc[i] and position != 'short':
            if position == 'long':
                # Close long
                pnl = (test_data['close'].iloc[i] - entry_price) / entry_price
                trades.append({'pnl': pnl, 'type': 'close_long'})
            # Open short
            position = 'short'
            entry_price = test_data['close'].iloc[i]
            trades.append({'pnl': 0, 'type': 'open_short', 'entry': entry_price})
    
    # Close any open position at the end
    if position == 'long':
        pnl = (test_data['close'].iloc[-1] - entry_price) / entry_price
        trades.append({'pnl': pnl, 'type': 'close_long_final'})
    elif position == 'short':
        pnl = (entry_price - test_data['close'].iloc[-1]) / entry_price
        trades.append({'pnl': pnl, 'type': 'close_short_final'})
    
    # Filter only closed trades with PnL
    closed_trades = [t for t in trades if t['pnl'] != 0]
    return closed_trades


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("WALK-FORWARD ANALYSIS - TEST")
    print("=" * 60)
    
    # Create analyzer
    analyzer = WalkForwardAnalyzer()
    
    # Define test period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Run walk-forward
    results = analyzer.run_walk_forward(
        asset="EURUSD",
        strategy_func=example_strategy,
        start_date=start_date,
        end_date=end_date
    )
    
    print("\n✅ Walk-forward analysis complete")
