# alpha_generator.py - COMPLETE FIXED VERSION

import math
import time
import random
import logging
import traceback
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# PRICE CACHE FALLBACK
# ============================================================

try:
    from price_cache_manager import price_cache
except ImportError:
    class price_cache:
        @staticmethod
        def get_latest(symbol, default=0):
            return default


# ============================================================
# HISTORICAL DATA PROVIDER
# ============================================================

class HistoricalDataProvider:
    """Provides historical price data for backtesting."""
    
    def __init__(self):
        self.cache = {}
    
    def get_price_history(self, symbol: str, days: int = 30, timeframe: str = '5min') -> Optional[pd.DataFrame]:
        """Get historical price data."""
        try:
            cache_key = f"{symbol}_{days}_{timeframe}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Generate synthetic data for testing
            base_price = self._get_base_price(symbol)
            periods = int(days * 24 * 60 / 5)
            
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
            prices = []
            
            for i in range(periods):
                if i == 0:
                    price = base_price
                else:
                    shock = np.random.normal(0, 0.001)
                    trend = 0.0001 * math.sin(i / 100)
                    price = prices[-1] * (1 + shock + trend)
                prices.append(price)
            
            df = pd.DataFrame({
                'close': prices,
                'high': [p * 1.001 for p in prices],
                'low': [p * 0.999 for p in prices],
                'open': [p * 0.9995 for p in prices],
                'volume': [1000 + random.randint(0, 2000) for _ in prices]
            }, index=dates)
            
            self.cache[cache_key] = df
            return df
            
        except Exception as e:
            logger.warning(f"Historical data error: {e}")
            return None
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for symbol."""
        base_prices = {
            '#S&P500': 7500.00,
            '#NASDAQ100': 28500.00,
            'EURUSD': 1.1000,
            'GBPUSD': 1.3400,
            'GOLD': 4000.00,
        }
        return base_prices.get(symbol, 100.00)


# ============================================================
# SPREAD ARBITRAGE ALPHA
# ============================================================

class SpreadArbitrageAlpha:
    """
    Specialized alpha generator for spread arbitrage.
    Generates alpha based on Z-score deviations between SPX and NDX.
    """
    
    def __init__(self):
        self.name = "Spread_Arbitrage_Alpha"
        self.beta = 1.05
        self.spread_history = []
        self.max_history = 300
        self.mu = 0.0
        self.sigma = 0.0
        self.z_score = 0.0
        self.current_spread = 0.0
        
        # Alpha parameters
        self.entry_threshold = 2.5
        self.exit_threshold = 0.5
        
        # Performance tracking
        self.alphas_generated = 0
        self.alphas_executed = 0
        self.performance = []
        self.confidence_history = deque(maxlen=100)
        
        logger.info(f"✅ {self.name} initialized")
    
    def calculate_spread(self, spx_price: float, ndx_price: float) -> float:
        """S(t) = ln(SPX) - β * ln(NDX)"""
        if spx_price <= 0 or ndx_price <= 0:
            return self.current_spread
        
        self.current_spread = math.log(spx_price) - self.beta * math.log(ndx_price)
        return self.current_spread
    
    def calculate_z_score(self) -> float:
        """Z = (S - μ) / σ"""
        self.spread_history.append(self.current_spread)
        
        if len(self.spread_history) > self.max_history:
            self.spread_history.pop(0)
        
        if len(self.spread_history) < 30:
            return 0
        
        self.mu = sum(self.spread_history) / len(self.spread_history)
        variance = sum((x - self.mu) ** 2 for x in self.spread_history) / len(self.spread_history)
        self.sigma = math.sqrt(variance) if variance > 0 else 0.0001
        
        if self.sigma > 0:
            self.z_score = (self.current_spread - self.mu) / self.sigma
        else:
            self.z_score = 0
        
        return self.z_score
    
    def generate_alpha(self, spx_price: float, ndx_price: float) -> Dict:
        """Generate alpha based on spread deviation."""
        
        self.calculate_spread(spx_price, ndx_price)
        z_score = self.calculate_z_score()
        
        if z_score > self.entry_threshold:
            alpha_type = "SELL_SPREAD"
            alpha_strength = min(1.0, (z_score - self.entry_threshold) / 1.0)
            confidence = min(95, 75 + (z_score - self.entry_threshold) * 15)
            reasoning = f"Spread overextended: Z={z_score:.2f}"
            
        elif z_score < -self.entry_threshold:
            alpha_type = "BUY_SPREAD"
            alpha_strength = min(1.0, (-z_score - self.entry_threshold) / 1.0)
            confidence = min(95, 75 + (-z_score - self.entry_threshold) * 15)
            reasoning = f"Spread compressed: Z={z_score:.2f}"
            
        else:
            alpha_type = "HOLD"
            alpha_strength = 0
            confidence = max(40, 50 - abs(z_score) * 5)
            reasoning = f"Spread at equilibrium: Z={z_score:.2f}"
        
        self.alphas_generated += 1
        if alpha_type != 'HOLD':
            self.alphas_executed += 1
        
        self.confidence_history.append(confidence)
        
        return {
            'type': 'SPREAD_ARBITRAGE',
            'name': 'Spread_Arbitrage_Alpha',
            'action': alpha_type,
            'alpha_strength': round(alpha_strength, 3),
            'confidence': confidence,
            'z_score': round(z_score, 3),
            'spread': round(self.current_spread, 6),
            'beta': round(self.beta, 4),
            'mu': round(self.mu, 6),
            'sigma': round(self.sigma, 6),
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat(),
            'samples': len(self.spread_history)
        }
    
    def get_expected_reversion(self, z_score: float) -> float:
        """Calculate expected reversion magnitude."""
        if abs(z_score) <= self.entry_threshold:
            return 0
        return abs(z_score) - self.entry_threshold
    
    def get_avg_confidence(self) -> float:
        """Get average confidence over recent signals."""
        if not self.confidence_history:
            return 50
        return sum(self.confidence_history) / len(self.confidence_history)
    
    def backtest(self, spx_history: List[float], ndx_history: List[float]) -> Dict:
        """Backtest spread alpha on historical data."""
        if len(spx_history) < 60 or len(ndx_history) < 60:
            return {'passed': False, 'reason': 'Insufficient data', 'total_trades': 0, 'win_rate': 0}
        
        trades = []
        spread_history = []
        
        for i in range(30, len(spx_history)):
            spread = math.log(spx_history[i]) - self.beta * math.log(ndx_history[i])
            spread_history.append(spread)
            
            if len(spread_history) < 30:
                continue
            
            mu = sum(spread_history[-30:]) / 30
            variance = sum((x - mu) ** 2 for x in spread_history[-30:]) / 30
            sigma = math.sqrt(variance) if variance > 0 else 0.0001
            z_score = (spread - mu) / sigma if sigma > 0 else 0
            
            if abs(z_score) > self.entry_threshold:
                trade_type = 'SELL' if z_score > 0 else 'BUY'
                entry_spread = spread
                entry_price = spx_history[i]
                
                exit_idx = min(i + 10, len(spx_history) - 1)
                exit_spread = math.log(spx_history[exit_idx]) - self.beta * math.log(ndx_history[exit_idx])
                exit_price = spx_history[exit_idx]
                
                if trade_type == 'SELL':
                    pnl = entry_price - exit_price
                else:
                    pnl = exit_price - entry_price
                
                trades.append({
                    'type': trade_type,
                    'entry_z': z_score,
                    'exit_z': (exit_spread - mu) / sigma if sigma > 0 else 0,
                    'pnl': pnl,
                    'win': pnl > 0
                })
        
        total_trades = len(trades)
        if total_trades == 0:
            return {'passed': False, 'reason': 'No trades generated', 'total_trades': 0, 'win_rate': 0}
        
        wins = sum(1 for t in trades if t['win'])
        win_rate = wins / total_trades * 100
        avg_pnl = sum(t['pnl'] for t in trades) / total_trades if total_trades > 0 else 0
        
        return {
            'passed': win_rate >= 50.0 and total_trades >= 5,
            'win_rate': round(win_rate, 2),
            'total_trades': total_trades,
            'total_pnl': round(sum(t['pnl'] for t in trades), 4),
            'avg_pnl': round(avg_pnl, 4),
            'wins': wins,
            'losses': total_trades - wins
        }


# ============================================================
# ALPHA GENERATOR
# ============================================================

class AlphaGenerator:
    """Generates, backtests, and manages trading alphas"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.generated_alphas = []
        self.active_alphas = []
        self.alpha_history = []
        self.data_provider = HistoricalDataProvider()
        self.spread_alpha = SpreadArbitrageAlpha()
        
        logger.info("   ✅ Spread Arbitrage Alpha integrated")
    
    def generate_spread_alpha(self, spx_price: float, ndx_price: float) -> Dict:
        """Generate spread arbitrage alpha using real-time prices."""
        alpha = self.spread_alpha.generate_alpha(spx_price, ndx_price)
        self.alpha_history.append(alpha)
        if len(self.alpha_history) > 1000:
            self.alpha_history.pop(0)
        return alpha
    
    def get_spread_alpha_status(self) -> Dict:
        """Get current spread alpha status"""
        return {
            'total_generated': self.spread_alpha.alphas_generated,
            'total_executed': self.spread_alpha.alphas_executed,
            'current_z_score': self.spread_alpha.z_score,
            'current_spread': self.spread_alpha.current_spread,
            'beta': self.spread_alpha.beta,
            'mu': self.spread_alpha.mu,
            'sigma': self.spread_alpha.sigma,
            'samples': len(self.spread_alpha.spread_history),
            'is_ready': len(self.spread_alpha.spread_history) >= 30,
            'avg_confidence': self.spread_alpha.get_avg_confidence()
        }
    
    def generate_new_alpha(self) -> Dict:
        """Generate a new random alpha strategy."""
        strategies = ['MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT', 'VOLATILITY', 'MACHINE_LEARNING']
        
        alpha = {
            'name': f"Alpha_{random.randint(1000, 9999)}",
            'strategy': random.choice(strategies),
            'parameters': {
                'lookback': random.randint(10, 50),
                'threshold': round(random.uniform(1.5, 3.0), 1),
                'weight': round(random.uniform(0.5, 1.5), 2)
            },
            'symbol': random.choice(['#S&P500', '#NASDAQ100', 'EURUSD']),
            'created_at': datetime.now().isoformat(),
            'status': 'PENDING'
        }
        
        self.generated_alphas.append(alpha)
        return alpha
    
    def backtest_and_validate(self, alpha: Dict, symbol: str = None, days: int = 30) -> Dict:
        """Backtest and validate an alpha strategy."""
        if symbol is None:
            symbol = alpha.get('symbol', '#S&P500')
        
        history = self.data_provider.get_price_history(symbol, days=days, timeframe='5min')
        
        if history is None:
            return {'passed': False, 'reason': 'No data available', 'win_rate': 0, 'total_trades': 0}
        
        prices = history['close'].values.tolist()
        
        if len(prices) < 50:
            return {'passed': False, 'reason': 'Insufficient data', 'win_rate': 0, 'total_trades': 0}
        
        lookback = alpha.get('parameters', {}).get('lookback', 20)
        threshold = alpha.get('parameters', {}).get('threshold', 2.0)
        
        trades = []
        
        for i in range(lookback, len(prices) - 10):
            window = prices[i-lookback:i]
            mean = sum(window) / len(window)
            std = math.sqrt(sum((x - mean) ** 2 for x in window) / len(window)) if window else 0.0001
            
            if std == 0:
                continue
            
            z_score = (prices[i] - mean) / std
            
            if z_score > threshold:
                entry = prices[i]
                for j in range(i + 1, min(i + 20, len(prices))):
                    if abs(prices[j] - mean) / std < 0.5 or j == len(prices) - 1:
                        pnl = entry - prices[j]
                        trades.append({'entry': entry, 'exit': prices[j], 'pnl': pnl, 'win': pnl > 0})
                        break
            
            elif z_score < -threshold:
                entry = prices[i]
                for j in range(i + 1, min(i + 20, len(prices))):
                    if abs(prices[j] - mean) / std < 0.5 or j == len(prices) - 1:
                        pnl = prices[j] - entry
                        trades.append({'entry': entry, 'exit': prices[j], 'pnl': pnl, 'win': pnl > 0})
                        break
        
        total_trades = len(trades)
        if total_trades == 0:
            return {'passed': False, 'reason': 'No trades generated', 'win_rate': 0, 'total_trades': 0}
        
        winning_trades = sum(1 for t in trades if t['win'])
        win_rate = winning_trades / total_trades * 100
        
        pnls = [t['pnl'] for t in trades]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        total_pnl = sum(pnls)
        
        std_pnl = np.std(pnls) if len(pnls) > 1 else 1
        sharpe = (avg_pnl / std_pnl) * (252 ** 0.5) if std_pnl > 0 else 0
        
        passed = win_rate >= 50.0 and total_trades >= 5
        
        return {
            'passed': passed,
            'win_rate': round(win_rate, 2),
            'sharpe': round(sharpe, 3),
            'total_trades': total_trades,
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_pnl, 2),
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades
        }
    
    def backtest_spread_alpha(self, spx_history: List[float], ndx_history: List[float]) -> Dict:
        """Backtest spread alpha on historical data."""
        return self.spread_alpha.backtest(spx_history, ndx_history)
    
    def save_alpha_to_db(self, alpha: Dict):
        """Save alpha to database."""
        logger.info(f"💾 Saving alpha: {alpha['name']}")
    
    def rank_alphas(self) -> List[Dict]:
        """Rank alphas by performance."""
        return sorted(self.generated_alphas, 
                     key=lambda x: x.get('performance', {}).get('win_rate', 0), 
                     reverse=True)
    
    def get_status(self) -> Dict:
        """Get generator status."""
        return {
            'total_generated': len(self.generated_alphas),
            'active_alphas': len(self.active_alphas),
            'spread_alpha_ready': self.get_spread_alpha_status()['is_ready'],
            'spread_z_score': self.get_spread_alpha_status()['current_z_score']
        }


# ============================================================
# ALPHA SCHEDULER
# ============================================================

class AlphaScheduler:
    """Schedules and manages alpha generation and backtesting"""
    
    def __init__(self, generator: AlphaGenerator, interval_hours: int = 24):
        self.generator = generator
        self.interval_hours = interval_hours
        self.is_running = False
        self.thread = None
        self.last_spread_check = None
        self.spread_alphas = []
        
        logger.info("✅ Alpha Scheduler initialized with Spread Alpha integration")
    
    def start(self):
        """Start the scheduler."""
        self.is_running = True
        import threading
        self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.thread.start()
        print("🔄 Alpha Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        print("⏹️ Alpha Scheduler stopped")
    
    def check_spread_alpha(self, spx_price: float, ndx_price: float) -> Optional[Dict]:
        """Check if spread alpha should be generated."""
        if spx_price <= 0 or ndx_price <= 0:
            return None
        
        alpha = self.generator.generate_spread_alpha(spx_price, ndx_price)
        
        self.spread_alphas.append(alpha)
        if len(self.spread_alphas) > 1000:
            self.spread_alphas.pop(0)
        
        if alpha['action'] != 'HOLD':
            print(f"📊 SPREAD ALPHA: {alpha['action']} (Z={alpha['z_score']:.2f})")
        
        return alpha
    
    def get_spread_alpha_stats(self) -> Dict:
        """Get statistics for spread alphas."""
        recent = self.spread_alphas[-100:] if self.spread_alphas else []
        
        if not recent:
            return {
                'total_generated': 0,
                'total_signals': 0,
                'current_z': 0,
                'signal_rate': 0
            }
        
        signals = [a for a in recent if a['action'] != 'HOLD']
        
        return {
            'total_generated': len(self.spread_alphas),
            'total_signals': len(signals),
            'current_z': recent[-1]['z_score'] if recent else 0,
            'signal_rate': round(len(signals) / len(recent) * 100, 1) if recent else 0
        }
    
    def _schedule_loop(self):
        """Main scheduling loop."""
        while self.is_running:
            try:
                print(f"\n🧠 Alpha Generation Cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 60)
                
                for i in range(3):
                    print(f"\n📝 Generating Alpha #{i+1}...")
                    alpha = self.generator.generate_new_alpha()
                    print(f"   Generated: {alpha['name']}")
                    
                    current_symbol = alpha.get('symbol') or '#NASDAQ100'
                    
                    backtest_results = self.generator.backtest_and_validate(alpha, symbol=current_symbol, days=30)
                    
                    if backtest_results.get('passed', False):
                        print(f"   ✅ PASSED: WR={backtest_results['win_rate']:.1f}%, Trades={backtest_results['total_trades']}")
                        self.generator.save_alpha_to_db(alpha)
                    else:
                        print(f"   ❌ FAILED: {backtest_results.get('reason', 'Unknown')}")
                
                print("\n📊 SPREAD ALPHA STATUS:")
                spread_stats = self.get_spread_alpha_stats()
                print(f"   Generated: {spread_stats['total_generated']}")
                print(f"   Signals: {spread_stats['total_signals']} ({spread_stats['signal_rate']}%)")
                print(f"   Current Z: {spread_stats['current_z']:.2f}")
                
                print("\n" + "=" * 60)
                print("🏆 TOP PERFORMING ALPHAS")
                print("=" * 60)
                
                ranked = self.generator.rank_alphas()[:5]
                for idx, alpha in enumerate(ranked, 1):
                    name = alpha.get('name', 'Unknown')
                    print(f"{idx}. {name}")
                
                print("\n" + "=" * 60)
                print(f"⏳ Next cycle in {self.interval_hours} hours")
                
            except Exception as e:
                print(f"❌ Alpha generation error: {e}")
                traceback.print_exc()
            
            time.sleep(self.interval_hours * 3600)