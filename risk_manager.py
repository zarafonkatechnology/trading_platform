# risk_manager.py
"""
Advanced Risk Management System
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

class RiskManager:
    def __init__(self):
        self.daily_pnl = 0
        self.daily_trades = 0
        self.daily_loss_limit = -500  # -$500 daily limit
        self.max_daily_trades = 10
        self.max_drawdown_limit = 0.15  # 15% max drawdown
        self.position_sizes = {}
        self.exposure_limit = 0.5  # 50% max exposure
        self.risk_per_trade = 0.02  # 2% risk per trade
        
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        self.trade_log = deque(maxlen=1000)
        
    def check_risk_limits(self, symbol: str, position_size: float, account_balance: float) -> Tuple[bool, str]:
        """
        Check all risk limits before a trade
        """
        # Reset daily counters if new day
        if datetime.now().date() > self.reset_time.date():
            self.daily_pnl = 0
            self.daily_trades = 0
            self.reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Check daily loss limit
        if self.daily_pnl <= self.daily_loss_limit:
            return False, f"Daily loss limit reached (${self.daily_loss_limit})"
        
        # Check max daily trades
        if self.daily_trades >= self.max_daily_trades:
            return False, f"Max daily trades reached ({self.max_daily_trades})"
        
        # Check total exposure
        total_exposure = sum(self.position_sizes.values())
        exposure_ratio = total_exposure / account_balance
        
        if exposure_ratio >= self.exposure_limit:
            return False, f"Exposure limit reached ({exposure_ratio*100:.0f}%)"
        
        # Check symbol exposure
        symbol_exposure = self.position_sizes.get(symbol, 0) / account_balance
        if symbol_exposure >= self.exposure_limit / 3:
            return False, f"Symbol exposure limit reached for {symbol}"
        
        return True, "Risk limits passed"
    
    def update_after_trade(self, symbol: str, pnl: float, position_size: float):
        """
        Update risk metrics after a trade
        """
        self.daily_pnl += pnl
        self.daily_trades += 1
        self.position_sizes[symbol] = self.position_sizes.get(symbol, 0) + position_size
        
        self.trade_log.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'pnl': pnl,
            'position_size': position_size,
            'daily_pnl': self.daily_pnl
        })
    
    def update_after_close(self, symbol: str, position_size: float):
        """
        Update after closing a position
        """
        self.position_sizes[symbol] = max(0, self.position_sizes.get(symbol, 0) - position_size)
        if self.position_sizes[symbol] == 0:
            del self.position_sizes[symbol]
    
    def get_risk_status(self, account_balance: float) -> Dict:
        """
        Get current risk status
        """
        total_exposure = sum(self.position_sizes.values())
        exposure_ratio = total_exposure / account_balance if account_balance > 0 else 0
        
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'daily_loss_remaining': abs(min(0, self.daily_pnl - self.daily_loss_limit)) if self.daily_pnl < 0 else 0,
            'trades_remaining': max(0, self.max_daily_trades - self.daily_trades),
            'exposure_ratio': exposure_ratio * 100,
            'open_positions': len(self.position_sizes),
            'risk_per_trade': self.risk_per_trade * 100,
            'is_trading_allowed': self.daily_pnl > self.daily_loss_limit and self.daily_trades < self.max_daily_trades
        }


risk_manager = RiskManager()