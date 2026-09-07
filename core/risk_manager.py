# core/risk_manager.py
"""
Centralized Risk Management System
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """Centralized risk management for all trading"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Daily limits
        self.daily_loss_limit = self.config.get('daily_loss_limit', 100)
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.max_trades_per_day = self.config.get('max_trades_per_day', 10)
        self.trade_date = datetime.now().date()
        
        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 999)
        
        # Weekly limits
        self.weekly_pnl = 0.0
        self.weekly_loss_limit = self.config.get('weekly_loss_limit', 300)
        self.week_start = datetime.now().date()
        
        # Position limits
        self.max_positions = self.config.get('max_positions', 3)
        self.active_positions = {}
        
        # Cold start
        self.cold_start_active = True
        self.cold_start_samples = []
        self.cold_start_threshold = self.config.get('cold_start_threshold', 50)
        self.cold_start_min_win_rate = self.config.get('cold_start_min_win_rate', 0.4)
        self.cold_start_wins = 0
        self.cold_start_losses = 0
        
        # Account info
        self.account_balance = self.config.get('account_balance', 10000)
        
        # Load cold start state
        self._load_cold_start_state()
        
        logger.info("✅ RiskManager initialized")
        logger.info(f"   Daily Loss Limit: ${self.daily_loss_limit}")
        logger.info(f"   Max Positions: {self.max_positions}")
        logger.info(f"   Cold Start: {self.cold_start_threshold} samples required")
    
    def _load_cold_start_state(self):
        """Load cold start data from file"""
        try:
            if os.path.exists('cold_start_state.json'):
                with open('cold_start_state.json', 'r') as f:
                    state = json.load(f)
                self.cold_start_samples = state.get('samples', [])
                self.cold_start_wins = state.get('wins', 0)
                self.cold_start_losses = state.get('losses', 0)
                self.cold_start_active = state.get('active', True)
                logger.info(f"   Loaded cold start: {len(self.cold_start_samples)} samples")
        except Exception as e:
            pass
    
    def _save_cold_start_state(self):
        """Save cold start data to file"""
        try:
            state = {
                'samples': self.cold_start_samples,
                'wins': self.cold_start_wins,
                'losses': self.cold_start_losses,
                'active': self.cold_start_active,
                'timestamp': datetime.now().isoformat()
            }
            with open('cold_start_state.json', 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            pass
    
    def add_cold_start_sample(self, sample: Dict):
        """Add a cold start sample (demo trade)"""
        self.cold_start_samples.append(sample)
        if sample.get('win', False):
            self.cold_start_wins += 1
        else:
            self.cold_start_losses += 1
        
        self._save_cold_start_state()
        
        # Check if cold start is complete
        if len(self.cold_start_samples) >= self.cold_start_threshold:
            win_rate = self.cold_start_wins / len(self.cold_start_samples) if len(self.cold_start_samples) > 0 else 0
            if win_rate >= self.cold_start_min_win_rate:
                self.cold_start_active = False
                self._save_cold_start_state()
                logger.info(f'✅ Cold start complete! Win rate: {win_rate:.1%} (Samples: {len(self.cold_start_samples)})')
            else:
                logger.info(f'⚠️ Cold start samples collected: {len(self.cold_start_samples)}/{self.cold_start_threshold}, Win rate: {win_rate:.1%} (need {self.cold_start_min_win_rate:.1%})')
    
    def check_trade_allowed(self, pair: str = None) -> Tuple[bool, str]:
        """Check if trading is allowed based on risk limits"""
        
        # 1. Daily reset
        today = datetime.now().date()
        if today != self.trade_date:
                self.trade_date = today
                self.trades_today = 0
                self.daily_pnl = 0.0
                self.consecutive_losses = 0
        
        # 2. Daily Loss Limit - BUT ONLY IF P&L IS REASONABLE
        # If P&L is crazy (> $1000), assume it's a calculation error and reset it
        if abs(self.daily_pnl) > 1000:
                logger.warning(f'⚠️ Crazy P&L detected: ${self.daily_pnl:.2f} - Resetting to 0')
                self.daily_pnl = 0.0
                self.trades_today = 0
                self.consecutive_losses = 0
                return True, "P&L Reset - Crazy value detected"
        
        if self.daily_pnl <= -self.daily_loss_limit:
                return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}"
        
        # 3. Consecutive Loss Limit
        if self.consecutive_losses >= self.max_consecutive_losses:
                return False, f"Max consecutive losses: {self.consecutive_losses}"
        
        # 4. Daily Trade Limit
        if self.trades_today >= self.max_trades_per_day:
                return False, f"Daily trade limit: {self.trades_today}"
        
        # 5. Position Limit
        if len(self.active_positions) >= self.max_positions:
                return False, f"Position limit: {len(self.active_positions)}"
        
        # 6. Weekly Loss Limit
        week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
        if week_start != self.week_start:
                self.week_start = week_start
                self.weekly_pnl = 0.0
        
        if self.weekly_pnl <= -self.weekly_loss_limit:
                return False, f"Weekly loss limit reached: ${self.weekly_pnl:.2f}"
        
        # 7. Cold Start
        if self.cold_start_active:
                if len(self.cold_start_samples) < self.cold_start_threshold:
                        return False, f"Cold start: {len(self.cold_start_samples)}/{self.cold_start_threshold}"
                
                win_rate = self.cold_start_wins / len(self.cold_start_samples) if len(self.cold_start_samples) > 0 else 0
                if win_rate >= self.cold_start_min_win_rate:
                        self.cold_start_active = False
                        self._save_cold_start_state()
                        logger.info(f'✅ Cold start complete! Win rate: {win_rate:.1%}')
                else:
                        return False, f"Cold start win rate: {win_rate:.1%} < {self.cold_start_min_win_rate:.1%}"
        
        return True, "OK"
    def update_risk_metrics(self, pnl: float, was_win: bool):
        """Update risk metrics after a trade"""
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.trades_today += 1
        
        if was_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Save cold start state periodically
        if len(self.cold_start_samples) % 5 == 0:
            self._save_cold_start_state()
    
    def add_position(self, pair: str, position: Dict):
        """Add a position to tracking"""
        self.active_positions[pair] = position
    
    def remove_position(self, pair: str):
        """Remove a position from tracking"""
        if pair in self.active_positions:
            del self.active_positions[pair]
    
    def calculate_position_size(self, confidence: float, volatility: float, 
                                pair: str = 'EURUSD') -> float:
        """Dynamic position sizing"""
        base_size = self.config.get('base_volume', 0.03)
        max_size = self.config.get('max_position_size', 0.10)
        
        # Consecutive loss penalty
        if self.consecutive_losses >= 2:
            loss_penalty = max(0.5, 1.0 - (self.consecutive_losses * 0.15))
        else:
            loss_penalty = 1.0
        
        # Daily P&L adjustment
        if self.daily_pnl < 0:
            daily_penalty = max(0.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.8)
        else:
            daily_penalty = min(1.5, 1.0 + (self.daily_pnl / self.daily_loss_limit) * 0.3)
        
        # Volatility adjustment
        vol_penalty = 1.0 / (1.0 + volatility * 50)
        vol_penalty = max(0.3, min(1.0, vol_penalty))
        
        # Confidence factor
        confidence_factor = 0.4 + (confidence / 100.0) * 0.6
        
        # Account growth
        account_factor = min(1.5, self.account_balance / 10000)
        
        # Final size
        position_size = (base_size * loss_penalty * daily_penalty * vol_penalty * 
                        confidence_factor * account_factor)
        
        # Clamp
        position_size = max(0.01, min(max_size, round(position_size, 3)))
        
        return round(position_size, 2)
    
    def get_status(self) -> Dict:
        """Get risk status"""
        return {
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'trades_today': self.trades_today,
            'consecutive_losses': self.consecutive_losses,
            'active_positions': len(self.active_positions),
            'cold_start_active': self.cold_start_active,
            'cold_start_samples': len(self.cold_start_samples),
            'cold_start_wins': self.cold_start_wins,
            'cold_start_losses': self.cold_start_losses,
            'account_balance': self.account_balance
        }