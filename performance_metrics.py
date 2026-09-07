# ============================================================
# performance_metrics.py - Complete Performance Metrics
# ============================================================

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Advanced performance evaluation for statistical arbitrage.
    """
    
    def __init__(self):
        self.trades = []
        self.daily_returns = []
        self.equity_curve = [10000]  # Starting capital
        
    def add_trade(self, trade: Dict):
        """
        Add a completed trade with full details.
        
        trade = {
            'entry_time': datetime,
            'exit_time': datetime,
            'entry_price': float,
            'exit_price': float,
            'quantity': float,
            'pnl': float,
            'entry_z': float,
            'exit_z': float,
            'hold_minutes': float,
            'symbol': str,
            'signal': str  # 'BUY' or 'SELL'
        }
        """
        self.trades.append(trade)
        self._update_equity(trade)
        
    def _update_equity(self, trade: Dict):
        """Update equity curve after each trade."""
        current_equity = self.equity_curve[-1]
        new_equity = current_equity + trade['pnl']
        self.equity_curve.append(new_equity)
        
        # Update daily returns
        day = trade['exit_time'].date()
        if not self.daily_returns or self.daily_returns[-1]['date'] != day:
            self.daily_returns.append({
                'date': day,
                'pnl': trade['pnl'],
                'trades': 1
            })
        else:
            self.daily_returns[-1]['pnl'] += trade['pnl']
            self.daily_returns[-1]['trades'] += 1
    
    def get_expectancy(self) -> Dict:
        """
        Expectancy = (Avg Win × Win Rate) - (Avg Loss × Loss Rate)
        """
        if not self.trades:
            return {'expectancy': 0, 'status': 'NO_DATA'}
        
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in self.trades if t['pnl'] <= 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        total = win_count + loss_count
        
        win_rate = win_count / total if total > 0 else 0
        loss_rate = loss_count / total if total > 0 else 0
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        expectancy = (avg_win * win_rate) - (avg_loss * loss_rate)
        
        if avg_loss > 0:
            kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_loss
        else:
            kelly = 0
        
        return {
            'expectancy': round(expectancy, 2),
            'win_rate': round(win_rate * 100, 1),
            'loss_rate': round(loss_rate * 100, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'total_trades': total,
            'win_count': win_count,
            'loss_count': loss_count,
            'kelly_percentage': round(kelly * 100, 1),
            'status': '✅ PROFITABLE' if expectancy > 0.5 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    def get_profit_factor(self) -> Dict:
        """Profit Factor = Gross Profit / Gross Loss"""
        if not self.trades:
            return {'profit_factor': 0, 'status': 'NO_DATA'}
        
        gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        gross_loss = sum(abs(t['pnl']) for t in self.trades if t['pnl'] <= 0)
        
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = gross_profit / 0.01
        
        return {
            'profit_factor': round(profit_factor, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'net_profit': round(gross_profit - gross_loss, 2),
            'status': '✅ EXCELLENT' if profit_factor > 1.5 else '👍 GOOD' if profit_factor > 1.3 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Dict:
        """Sharpe Ratio = (Return - Risk-Free) / Volatility"""
        if len(self.daily_returns) < 10:
            return {'sharpe': 0, 'status': 'INSUFFICIENT_DATA'}
        
        daily_pnls = [d['pnl'] for d in self.daily_returns]
        daily_returns = np.array(daily_pnls)
        
        avg_return = np.mean(daily_returns) / 10000
        std_return = np.std(daily_returns) / 10000
        
        if std_return > 0:
            sharpe = (avg_return * 365 - risk_free_rate) / (std_return * np.sqrt(365))
        else:
            sharpe = 0
        
        return {
            'sharpe_ratio': round(sharpe, 2),
            'avg_daily_return': round(avg_return * 100, 2),
            'std_daily_return': round(std_return * 100, 2),
            'total_days': len(self.daily_returns),
            'status': '✅ EXCELLENT' if sharpe > 2.0 else '👍 GOOD' if sharpe > 1.0 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    def get_calmar_ratio(self) -> Dict:
        """Calmar Ratio = Annualized Return / Max Drawdown"""
        if len(self.equity_curve) < 10:
            return {'calmar': 0, 'status': 'INSUFFICIENT_DATA'}
        
        peak = self.equity_curve[0]
        max_drawdown = 0
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        total_return = (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0]
        days = len(self.equity_curve) / 60
        annualized_return = total_return / (days / 365) if days > 0 else 0
        
        calmar = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        return {
            'calmar_ratio': round(calmar, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'status': '✅ EXCELLENT' if calmar > 2.0 else '👍 GOOD' if calmar > 1.0 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    def get_execution_quality(self) -> Dict:
        """Evaluate execution quality based on Z-score deltas."""
        if not self.trades:
            return {'quality': 'NO_DATA', 'avg_delta': 0}
        
        deltas = [abs(t['entry_z'] - t['exit_z']) for t in self.trades]
        avg_delta = np.mean(deltas)
        
        adverse_moves = [1 for t in self.trades if t['pnl'] < 0 and abs(t['exit_z']) > abs(t['entry_z'])]
        
        return {
            'avg_z_delta': round(avg_delta, 3),
            'avg_hold_minutes': round(np.mean([t['hold_minutes'] for t in self.trades]), 1),
            'adverse_moves': len(adverse_moves),
            'adverse_percentage': round(len(adverse_moves) / len(self.trades) * 100, 1) if self.trades else 0,
            'quality': 'EXCELLENT' if avg_delta < 0.5 else 'GOOD' if avg_delta < 1.0 else 'POOR'
        }
    
    def get_comprehensive_report(self) -> Dict:
        """Complete performance report with all metrics."""
        return {
            'expectancy': self.get_expectancy(),
            'profit_factor': self.get_profit_factor(),
            'sharpe_ratio': self.get_sharpe_ratio(),
            'calmar_ratio': self.get_calmar_ratio(),
            'execution_quality': self.get_execution_quality(),
            'total_trades': len(self.trades),
            'equity_curve': self.equity_curve[-10:],
            'timestamp': datetime.now().isoformat()
        }
    
    def print_report(self):
        """Print formatted performance report."""
        report = self.get_comprehensive_report()
        
        print("=" * 70)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("=" * 70)
        print()
        
        print("🎯 EXPECTANCY ANALYSIS:")
        e = report['expectancy']
        print(f"   Expectancy:        ${e['expectancy']:.2f} per trade")
        print(f"   Win Rate:          {e['win_rate']}%")
        print(f"   Avg Win:           ${e['avg_win']:.2f}")
        print(f"   Avg Loss:          ${e['avg_loss']:.2f}")
        print(f"   Kelly:             {e['kelly_percentage']}%")
        print(f"   Status:            {e['status']}")
        print()
        
        print("📈 PROFIT FACTOR:")
        pf = report['profit_factor']
        print(f"   Profit Factor:     {pf['profit_factor']:.2f}")
        print(f"   Gross Profit:      ${pf['gross_profit']:.2f}")
        print(f"   Gross Loss:        ${pf['gross_loss']:.2f}")
        print(f"   Net Profit:        ${pf['net_profit']:.2f}")
        print(f"   Status:            {pf['status']}")
        print()
        
        print("📊 RISK-ADJUSTED RETURNS:")
        sr = report['sharpe_ratio']
        cr = report['calmar_ratio']
        print(f"   Sharpe Ratio:      {sr['sharpe_ratio']:.2f} ({sr['status']})")
        print(f"   Calmar Ratio:      {cr['calmar_ratio']:.2f} ({cr['status']})")
        print(f"   Max Drawdown:      {cr['max_drawdown']}%")
        print(f"   Annualized Return: {cr['annualized_return']}%")
        print()
        
        print("⚡ EXECUTION QUALITY:")
        eq = report['execution_quality']
        print(f"   Avg Z-Delta:       {eq['avg_z_delta']:.3f}")
        print(f"   Avg Hold Time:     {eq['avg_hold_minutes']} minutes")
        print(f"   Adverse Moves:     {eq['adverse_percentage']}%")
        print(f"   Quality:           {eq['quality']}")
        print()
        
        print(f"📊 TOTAL TRADES: {report['total_trades']}")
        print("=" * 70)