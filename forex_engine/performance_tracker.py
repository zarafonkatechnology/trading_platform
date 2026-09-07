# C:\trading_platform\forex_engine\performance_tracker.py

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """
    Tracks performance of all agents, brokers, and the system over time.
    Provides metrics for adaptive weighting and decision improvement.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize PerformanceTracker.
        
        Args:
            config: Configuration dictionary with optional settings
        """
        self.config = config or {}
        self.filename = self.config.get('performance_file', 'performance_data.json')
        self.max_history = self.config.get('performance_history', 1000)
        self.save_interval = self.config.get('save_interval', 50)  # ← FIX: Added
        
        # ===== PERFORMANCE DATA STRUCTURES =====
        self.trades = deque(maxlen=self.max_history)
        self.agent_stats = {}  # ← FIX: Added
        self.pair_stats = {}   # ← FIX: Added
        self.system_stats = {  # ← FIX: Added
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'equity_curve': [],
            'daily_pnl': {},
            'monthly_pnl': {},
        }
        
        # ===== ROLLING METRICS =====
        self.win_rate_window = deque(maxlen=100)
        self.pnl_window = deque(maxlen=100)
        
        # ===== STATE =====
        self.current_equity = 0.0      # ← FIX: Added
        self.peak_equity = 0.0         # ← FIX: Added
        self.trade_counter = 0         # ← FIX: Added
        self.start_time = datetime.now()  # ← FIX: Added
        
        # Load existing data
        self.load()
        
        logger.info("✅ PerformanceTracker initialized")
        logger.info(f"   Max history: {self.max_history} trades")
        logger.info(f"   File: {self.filename}")
        logger.info(f"   Save interval: {self.save_interval} trades")
    
    def record_trade(self, trade: Dict):
        """
        Record a trade and update all statistics.
        trade should contain: pair, signal, price, pnl, agents_involved, timestamp, etc.
        """
        self.trade_counter += 1
        self.system_stats['total_trades'] += 1
        
        pnl = trade.get('pnl', 0)
        pair = trade.get('pair', 'unknown')
        agents = trade.get('agents_involved', [])
        signal = trade.get('signal', 'unknown')
        confidence = trade.get('confidence', 0)
        timestamp = trade.get('timestamp', datetime.now().isoformat())
        
        # Determine if trade was a win
        was_win = pnl > 0
        
        # Update system stats
        if was_win:
            self.system_stats['wins'] += 1
            self.system_stats['total_pnl'] += pnl
            if pnl > self.system_stats['max_win']:
                self.system_stats['max_win'] = pnl
        else:
            self.system_stats['losses'] += 1
            self.system_stats['total_pnl'] += pnl
            if pnl < self.system_stats['max_loss']:
                self.system_stats['max_loss'] = pnl
        
        # Update current equity and drawdown
        self.current_equity += pnl
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        drawdown = (self.peak_equity - self.current_equity) if self.peak_equity > 0 else 0
        if drawdown > self.system_stats['max_drawdown']:
            self.system_stats['max_drawdown'] = drawdown
        
        # Update equity curve
        self.system_stats['equity_curve'].append({
            'timestamp': timestamp,
            'equity': self.current_equity,
            'pnl': pnl
        })
        if len(self.system_stats['equity_curve']) > 1000:
            self.system_stats['equity_curve'] = self.system_stats['equity_curve'][-500:]
        
        # Update daily PnL
        date_key = timestamp[:10] if isinstance(timestamp, str) else datetime.now().strftime('%Y-%m-%d')
        if date_key not in self.system_stats['daily_pnl']:
            self.system_stats['daily_pnl'][date_key] = 0
        self.system_stats['daily_pnl'][date_key] += pnl
        
        # Update monthly PnL
        month_key = timestamp[:7] if isinstance(timestamp, str) else datetime.now().strftime('%Y-%m')
        if month_key not in self.system_stats['monthly_pnl']:
            self.system_stats['monthly_pnl'][month_key] = 0
        self.system_stats['monthly_pnl'][month_key] += pnl
        
        # Update pair stats
        if pair not in self.pair_stats:
            self.pair_stats[pair] = {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0}
        self.pair_stats[pair]['trades'].append(trade)
        self.pair_stats[pair]['trades'] = self.pair_stats[pair]['trades'][-100:]  # Keep last 100
        if was_win:
            self.pair_stats[pair]['wins'] += 1
        else:
            self.pair_stats[pair]['losses'] += 1
        self.pair_stats[pair]['total_pnl'] += pnl
        
        # Update agent stats
        if not agents:
            agents = ['unknown']
        for agent in agents:
            if agent not in self.agent_stats:
                self.agent_stats[agent] = {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0}
            self.agent_stats[agent]['trades'].append(trade)
            self.agent_stats[agent]['trades'] = self.agent_stats[agent]['trades'][-100:]  # Keep last 100
            if was_win:
                self.agent_stats[agent]['wins'] += 1
            else:
                self.agent_stats[agent]['losses'] += 1
            self.agent_stats[agent]['total_pnl'] += pnl
        
        # Update rolling windows
        self.win_rate_window.append(1 if was_win else 0)
        self.pnl_window.append(pnl)
        
        # Calculate derived metrics
        self._update_derived_metrics()
        
        # Save periodically
        if self.trade_counter % self.save_interval == 0:
            self.save()
    
    def _update_derived_metrics(self):
        """Update derived metrics like win rate, Sharpe ratio, profit factor."""
        total = self.system_stats['total_trades']
        if total > 0:
            self.system_stats['win_rate'] = self.system_stats['wins'] / total
            
            wins = self.system_stats['wins']
            losses = self.system_stats['losses']
            
            # Average win/loss
            if wins > 0:
                self.system_stats['avg_win'] = self.system_stats['total_pnl'] / wins if wins > 0 else 0
            if losses > 0:
                self.system_stats['avg_loss'] = abs(self.system_stats['total_pnl']) / losses if losses > 0 else 0
            
            # Profit factor
            total_wins = self.system_stats['avg_win'] * wins if wins > 0 else 0
            total_losses = self.system_stats['avg_loss'] * losses if losses > 0 else 0
            self.system_stats['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
            
            # Calculate Sharpe ratio (assuming risk-free rate = 0)
            equity_curve = self.system_stats['equity_curve']
            if len(equity_curve) > 10:
                returns = [e['pnl'] for e in equity_curve]
                mean_return = np.mean(returns) if returns else 0
                std_return = np.std(returns) if len(returns) > 1 else 1
                self.system_stats['sharpe_ratio'] = mean_return / std_return if std_return > 0 else 0
    
    def get_agent_performance(self, agent_name: str) -> Dict:
        """Get performance summary for a specific agent."""
        if agent_name not in self.agent_stats:
            return {'error': 'Agent not found'}
        
        data = self.agent_stats[agent_name]
        total = len(data['trades'])
        win_rate = data['wins'] / total if total > 0 else 0
        return {
            'trades': total,
            'wins': data['wins'],
            'losses': data['losses'],
            'win_rate': win_rate,
            'total_pnl': data['total_pnl'],
            'avg_pnl': data['total_pnl'] / total if total > 0 else 0
        }
    
    def get_pair_performance(self, pair: str) -> Dict:
        """Get performance summary for a specific pair."""
        if pair not in self.pair_stats:
            return {'error': 'Pair not found'}
        
        data = self.pair_stats[pair]
        total = len(data['trades'])
        win_rate = data['wins'] / total if total > 0 else 0
        return {
            'trades': total,
            'wins': data['wins'],
            'losses': data['losses'],
            'win_rate': win_rate,
            'total_pnl': data['total_pnl'],
            'avg_pnl': data['total_pnl'] / total if total > 0 else 0
        }
    
    def get_top_agents(self, n: int = 3) -> List[Dict]:
        """Get top N agents by win rate or PnL."""
        agents = []
        for name, data in self.agent_stats.items():
            total = len(data['trades'])
            if total > 5:  # Minimum sample size
                win_rate = data['wins'] / total if total > 0 else 0
                agents.append({
                    'name': name,
                    'win_rate': win_rate,
                    'total_pnl': data['total_pnl'],
                    'trades': total
                })
        agents.sort(key=lambda x: x['win_rate'], reverse=True)
        return agents[:n]
    
    def get_bottom_agents(self, n: int = 3) -> List[Dict]:
        """Get bottom N agents by win rate."""
        agents = []
        for name, data in self.agent_stats.items():
            total = len(data['trades'])
            if total > 5:
                win_rate = data['wins'] / total if total > 0 else 0
                agents.append({
                    'name': name,
                    'win_rate': win_rate,
                    'total_pnl': data['total_pnl'],
                    'trades': total
                })
        agents.sort(key=lambda x: x['win_rate'])
        return agents[:n]
    
    def save(self):
        """Save performance data to file."""
        save_data = {
            'agent_stats': self.agent_stats,
            'pair_stats': self.pair_stats,
            'system_stats': self.system_stats,
            'start_time': self.start_time.isoformat(),
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'trade_counter': self.trade_counter,
            'last_save': datetime.now().isoformat()
        }
        try:
            with open(self.filename, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            logger.debug("✅ Performance data saved.")
        except Exception as e:
            logger.warning(f"Failed to save performance data: {e}")
    
    def load(self):
        """Load performance data from file."""
        if not os.path.exists(self.filename):
            return False
        
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            self.agent_stats = data.get('agent_stats', {})
            self.pair_stats = data.get('pair_stats', {})
            self.system_stats = data.get('system_stats', {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'max_win': 0.0,
                'max_loss': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'equity_curve': [],
                'daily_pnl': {},
                'monthly_pnl': {},
            })
            self.start_time = datetime.fromisoformat(data.get('start_time', datetime.now().isoformat()))
            self.current_equity = data.get('current_equity', 0)
            self.peak_equity = data.get('peak_equity', 0)
            self.trade_counter = data.get('trade_counter', 0)
            logger.info(f"✅ Loaded performance data: {self.system_stats['total_trades']} trades")
            return True
        except Exception as e:
            logger.warning(f"Failed to load performance data: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """Get a summary of overall performance."""
        return {
            'total_trades': self.system_stats['total_trades'],
            'wins': self.system_stats['wins'],
            'losses': self.system_stats['losses'],
            'win_rate': self.system_stats['win_rate'] * 100 if self.system_stats['total_trades'] > 0 else 0,
            'total_pnl': self.system_stats['total_pnl'],
            'max_drawdown': self.system_stats['max_drawdown'],
            'sharpe_ratio': self.system_stats['sharpe_ratio'],
            'profit_factor': self.system_stats['profit_factor'],
            'avg_win': self.system_stats['avg_win'],
            'avg_loss': self.system_stats['avg_loss'],
            'max_win': self.system_stats['max_win'],
            'max_loss': self.system_stats['max_loss'],
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'agents_monitored': len(self.agent_stats),
            'pairs_traded': len(self.pair_stats),
            'running_time': (datetime.now() - self.start_time).total_seconds() / 3600,
        }
    
    def print_summary(self):
        """Print a summary of performance to console."""
        summary = self.get_summary()
        print("\n" + "="*60)
        print("📊 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Win Rate: {summary['win_rate']:.1f}% ({summary['wins']}W / {summary['losses']}L)")
        print(f"   Total P&L: ${summary['total_pnl']:.2f}")
        print(f"   Profit Factor: {summary['profit_factor']:.2f}")
        print(f"   Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: ${summary['max_drawdown']:.2f}")
        print(f"   Current Equity: ${summary['current_equity']:.2f}")
        print(f"   Peak Equity: ${summary['peak_equity']:.2f}")
        print(f"   Avg Win: ${summary['avg_win']:.2f} | Avg Loss: ${summary['avg_loss']:.2f}")
        print(f"   Max Win: ${summary['max_win']:.2f} | Max Loss: ${summary['max_loss']:.2f}")
        print(f"   Running Time: {summary['running_time']:.1f} hours")
        print(f"   Agents: {summary['agents_monitored']} | Pairs: {summary['pairs_traded']}")
        print("="*60)
    
    def print_agent_ranking(self):
        """Print agent performance ranking."""
        print("\n" + "="*60)
        print("🏆 AGENT PERFORMANCE RANKING")
        print("="*60)
        print(f"{'Agent':<12} {'Trades':<8} {'Win Rate':<10} {'PnL':<10} {'Status'}")
        print("-"*60)
        
        agents = []
        for name, data in self.agent_stats.items():
            total = len(data['trades'])
            if total > 0:
                win_rate = data['wins'] / total if total > 0 else 0
                agents.append({
                    'name': name,
                    'trades': total,
                    'win_rate': win_rate,
                    'pnl': data['total_pnl']
                })
        
        agents.sort(key=lambda x: x['win_rate'], reverse=True)
        if not agents:
            print("   No agent data yet.")
        else:
            for agent in agents:
                status = "✅ Active" if agent['win_rate'] > 0.5 else "⚠️ Underperforming"
                print(f"{agent['name']:<12} {agent['trades']:<8} {agent['win_rate']*100:.1f}%{'':<5} ${agent['pnl']:.2f}  {status}")
        print("="*60)
    
    def print_pair_ranking(self):
        """Print pair performance ranking."""
        print("\n" + "="*60)
        print("📈 PAIR PERFORMANCE RANKING")
        print("="*60)
        print(f"{'Pair':<10} {'Trades':<8} {'Win Rate':<10} {'PnL':<10} {'Status'}")
        print("-"*60)
        
        pairs = []
        for name, data in self.pair_stats.items():
            total = len(data['trades'])
            if total > 0:
                win_rate = data['wins'] / total if total > 0 else 0
                pairs.append({
                    'name': name,
                    'trades': total,
                    'win_rate': win_rate,
                    'pnl': data['total_pnl']
                })
        
        pairs.sort(key=lambda x: x['win_rate'], reverse=True)
        if not pairs:
            print("   No pair data yet.")
        else:
            for pair in pairs:
                status = "✅ Profitable" if pair['pnl'] > 0 else "⚠️ Loss"
                print(f"{pair['name']:<10} {pair['trades']:<8} {pair['win_rate']*100:.1f}%{'':<5} ${pair['pnl']:.2f}  {status}")
        print("="*60)