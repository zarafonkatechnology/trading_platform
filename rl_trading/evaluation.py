# ============================================================
# evaluation.py - Backtesting & Validation
# ============================================================

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine for validating RL agents.
    """
    
    def __init__(self, model, env):
        self.model = model
        self.env = env
        self.results = []
        
    def run_backtest(self, n_episodes: int = 100, deterministic: bool = True) -> Dict:
        """
        Run backtest over multiple episodes.
        """
        logger.info(f"📊 Running backtest: {n_episodes} episodes")
        
        all_trades = []
        all_returns = []
        win_count = 0
        total_pnl = 0
        
        for episode in range(n_episodes):
            obs = self.env.reset()
            done = False
            episode_pnl = 0
            episode_trades = []
            
            while not done:
                action, _ = self.model.predict(obs, deterministic=deterministic)
                obs, reward, done, info = self.env.step(action)
                
                if info.get('trades', 0) > len(episode_trades):
                    # New trade executed
                    if self.env.trades:
                        latest_trade = self.env.trades[-1]
                        episode_trades.append(latest_trade)
                        episode_pnl += latest_trade.get('pnl', 0)
            
            all_trades.extend(episode_trades)
            all_returns.append(episode_pnl)
            total_pnl += episode_pnl
            
            if episode_pnl > 0:
                win_count += 1
        
        # Calculate metrics
        win_rate = (win_count / n_episodes) * 100 if n_episodes > 0 else 0
        avg_return = np.mean(all_returns) if all_returns else 0
        std_return = np.std(all_returns) if all_returns else 0
        sharpe = avg_return / (std_return + 1e-8)
        max_drawdown = self._calculate_max_drawdown(all_returns)
        
        results = {
            'n_episodes': n_episodes,
            'win_count': win_count,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_return': round(avg_return, 2),
            'std_return': round(std_return, 2),
            'sharpe_ratio': round(sharpe, 3),
            'max_drawdown': round(max_drawdown, 2),
            'total_trades': len(all_trades),
            'timestamp': datetime.now().isoformat()
        }
        
        self.results.append(results)
        
        return results
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0
        
        cumulative = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / (peak + 1e-8)
        return np.max(drawdown) * 100
    
    def print_report(self, results: Dict):
        """Print backtest report."""
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)
        print(f"   Episodes:        {results['n_episodes']}")
        print(f"   Win Rate:        {results['win_rate']}%")
        print(f"   Total P&L:       ${results['total_pnl']:.2f}")
        print(f"   Avg Return:      ${results['avg_return']:.2f}")
        print(f"   Std Return:      ${results['std_return']:.2f}")
        print(f"   Sharpe Ratio:    {results['sharpe_ratio']:.3f}")
        print(f"   Max Drawdown:    {results['max_drawdown']:.2f}%")
        print(f"   Total Trades:    {results['total_trades']}")
        print("=" * 60)
    
    def validate_6_months(self, model_path: str, data_path: str) -> Dict:
        """
        Run 6-month validation test.
        """
        logger.info("=" * 60)
        logger.info("🔬 6-MONTH VALIDATION TEST")
        logger.info("=" * 60)
        
        # Load model and data
        from stable_baselines3 import PPO
        from rl_trading.environment import SpreadArbitrageEnv
        from rl_trading.config import Config
        
        model = PPO.load(model_path)
        config = Config()
        
        # Load data
        data = pd.read_csv(data_path, index_col=0, parse_dates=True)
        
        # Get last 6 months
        six_months_ago = datetime.now() - timedelta(days=180)
        val_data = data[data.index >= six_months_ago]
        
        env = SpreadArbitrageEnv(val_data, config)
        
        # Run backtest
        backtest = BacktestEngine(model, env)
        results = backtest.run_backtest(n_episodes=50)
        
        # Print report
        backtest.print_report(results)
        
        # Check if passed
        passed = (
            results['win_rate'] > 80 and
            results['sharpe_ratio'] > 0.5 and
            results['max_drawdown'] < 15
        )
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"   Validation Status: {status}")
        logger.info(f"   Criteria: WR>80%, Sharpe>0.5, DD<15%")
        
        return results