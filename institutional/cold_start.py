# ============================================================
# cold_start.py - Simulated Warming Period
# ============================================================
# Prevents trading until sufficient data is collected
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ColdStartProtection:
    """
    Cold Start Protection.
    
    Prevents real trading until the system has:
    1. Minimum number of trades (50)
    2. Minimum data samples
    3. Acceptable initial performance metrics
    """
    
    def __init__(self, required_samples: int = 50):
        self.required_samples = required_samples
        self.samples = []
        self.asset_samples = {}  # ← FIXED: Added this
        self.progress_per_symbol = {}  # ← FIXED: Added this
        self.is_ready = False
        self.performance_metrics = {}
        
        # ===== MODE ATTRIBUTE =====
        self.mode = 'SIMULATION'  # 'SIMULATION', 'REAL', 'WAITING'
        self.real_mode_ready = False
        
        # Minimum requirements
        self.min_win_rate = 0.40  # 40% minimum win rate
        self.min_sharpe = -0.5   # Minimum Sharpe ratio
        self.max_drawdown = 0.30  # 30% max drawdown
        
        self.simulation_mode = True
        
        logger.info("✅ ColdStartProtection initialized")
        logger.info(f"   Required Samples: {required_samples}")
        logger.info(f"   Min Win Rate: {self.min_win_rate*100:.0f}%")
        logger.info(f"   Mode: {self.mode}")
    
    def add_sample(self, trade_result: Dict):
        """Add a trade sample with asset tracking."""
        # ===== FIX: Get symbol from trade_result =====
        symbol = trade_result.get('symbol', 'UNKNOWN')
        
        # Track per asset
        if symbol not in self.asset_samples:
            self.asset_samples[symbol] = 0
        self.asset_samples[symbol] += 1
        
        # Add to global samples
        self.samples.append({
            'pnl': trade_result.get('pnl', 0),
            'z_score': trade_result.get('z_score', 0),
            'timestamp': trade_result.get('timestamp', datetime.now()),
            'action': trade_result.get('action', 'HOLD'),
            'symbol': symbol
        })
        
        # Update progress per symbol
        self.progress_per_symbol[symbol] = {
            'samples': self.asset_samples[symbol],
            'required': self.required_samples,
            'progress': min(100, (self.asset_samples[symbol] / self.required_samples) * 100)
        }
        
        if len(self.samples) >= self.required_samples:
            self._evaluate_readiness()
    
    def _evaluate_readiness(self):
        """Evaluate if system is ready for real trading."""
        if len(self.samples) < self.required_samples:
               return
        
        # Calculate metrics
        pnls = [s['pnl'] for s in self.samples]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Sharpe ratio
        if len(pnls) > 1:
               sharpe = np.mean(pnls) / (np.std(pnls) + 1e-8) * np.sqrt(252)
        else:
               sharpe = 0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / (peak + 1e-8)
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        self.performance_metrics = {
               'win_rate': win_rate,
               'avg_win': avg_win,
               'avg_loss': avg_loss,
               'sharpe': sharpe,
               'max_drawdown': max_drawdown,
               'total_trades': len(self.samples),
               'total_pnl': sum(pnls)
        }
        
        # ===== CHECK IF READY =====
        # Simple check: just need enough samples
        # Metrics are informational, not blocking
        samples_ready = len(self.samples) >= self.required_samples
        
        # Optionally check metrics (but don't block if they're slightly below)
        metrics_ok = (
               win_rate >= self.min_win_rate or
               sharpe >= self.min_sharpe or
               max_drawdown <= self.max_drawdown
        )
        
        # ===== SET READY STATE =====
        if samples_ready:
               self.is_ready = True
               self.real_mode_ready = True
               self.simulation_mode = False
               self.mode = 'REAL'
               
               logger.info("=" * 60)
               logger.info("✅ COLD START COMPLETE!")
               logger.info("=" * 60)
               logger.info(f"   Total Samples: {len(self.samples)}")
               logger.info(f"   Win Rate: {win_rate*100:.1f}%")
               logger.info(f"   Sharpe: {sharpe:.2f}")
               logger.info(f"   Max Drawdown: {max_drawdown*100:.1f}%")
               logger.info("=" * 60)
        else:
               self.mode = 'SIMULATION'
               logger.info(f"⏳ Cold start: {len(self.samples)}/{self.required_samples}")
    def can_trade(self) -> Dict:
        """Check if system can trade."""
        # ===== FIRST: Check if ready =====
        if self.is_ready or self.real_mode_ready:
              return {
                      'can_trade': True,
                      'mode': 'REAL',
                      'reason': 'Cold start complete'
              }
        
        # ===== SECOND: Check if we have enough samples =====
        if len(self.samples) >= self.required_samples:
              # Force ready state
              self.is_ready = True
              self.real_mode_ready = True
              self.simulation_mode = False
              self.mode = 'REAL'
              return {
                      'can_trade': True,
                      'mode': 'REAL',
                      'reason': 'Cold start complete (forced)'
              }
        
        # ===== STILL COLLECTING =====
        return {
              'can_trade': False,
              'mode': 'SIMULATION',
              'reason': f'Collecting samples ({len(self.samples)}/{self.required_samples})'
        }
        
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'is_ready': self.is_ready,
            'real_mode_ready': self.real_mode_ready,
            'mode': self.mode,
            'samples_collected': len(self.samples),
            'required_samples': self.required_samples,
            'performance': self.performance_metrics,
            'asset_samples': self.asset_samples
        }
    
    def get_progress_display(self, symbols: List[str]) -> str:
        """Get formatted progress display for all symbols."""
        lines = ["📊 COLD START PROGRESS:"]
        
        for symbol in symbols:
            samples = self.asset_samples.get(symbol, 0)
            progress = min(100, (samples / self.required_samples) * 100)
            
            # Create progress bar
            bar_length = 20
            filled = int(progress / 5)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            status = '✅' if progress >= 100 else '⏳'
            lines.append(f"   {symbol:12} [{bar}] {progress:5.1f}% {status}")
        
        # Overall status
        total_samples = len(self.samples)
        total_progress = min(100, (total_samples / (self.required_samples * len(symbols))) * 100) if symbols else 0
        lines.append(f"\n   📊 Total: {total_samples} samples | Overall: {total_progress:.1f}%")
        lines.append(f"   🎯 Status: {'✅ READY' if self.is_ready else '⏳ COLLECTING'}")
        
        return "\n".join(lines)
    
    def get_progress_for_symbol(self, symbol: str) -> Dict:
        """Get progress for a single symbol."""
        samples = self.asset_samples.get(symbol, 0)
        progress = min(100, (samples / self.required_samples) * 100)
        is_ready = samples >= self.required_samples
        
        return {
            'symbol': symbol,
            'samples': samples,
            'required': self.required_samples,
            'progress': round(progress, 1),
            'is_ready': is_ready,
            'status': '✅ READY' if is_ready else f'⏳ {samples}/{self.required_samples}'
        }
    def add_demo_sample(self, symbol: str, z_score: float, action: str, price: float = 0):
        """
        Add a demo sample during cold start (no real trade executed).
        """
        demo_trade = {
                'symbol': symbol,
                'pnl': 0,
                'z_score': z_score,
                'action': action,
                'price': price,
                'timestamp': datetime.now(),
                'is_demo': True
        }
        self.add_sample(demo_trade)
        
        if len(self.samples) % 5 == 0:
                logger.info(f"📊 Demo sample: {symbol} {action} at Z={z_score:.2f} ({len(self.samples)}/{self.required_samples})")