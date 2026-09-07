import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    total_profit: float = 0.0
    total_loss: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0

class RiskManager:
    """Risk management system with 6 protection shields"""
    
    def __init__(self, 
                 daily_loss_limit: float = 100.0,
                 max_consecutive_losses: int = 3,
                 max_trades_per_day: int = 5,
                 max_position_size: float = 10.0,
                 stop_loss_pips: int = 50,
                 take_profit_pips: int = 100):
        
        # Shield 1: Daily Loss Limit
        self.daily_loss_limit = daily_loss_limit
        self.daily_pnl: Dict[str, float] = defaultdict(float)
        
        # Shield 2: Max Consecutive Losses
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0
        
        # Shield 3: Max Trades Per Day
        self.max_trades_per_day = max_trades_per_day
        self.daily_trades: Dict[str, int] = defaultdict(int)
        
        # Shield 4: Max Position Size
        self.max_position_size = max_position_size
        
        # Shield 5: Stop Loss & Take Profit
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips
        
        # Shield 6: Margin Ratio
        self.min_margin_ratio = 0.05
        
        # Risk Metrics
        self.metrics = RiskMetrics()
        
        # Trade history
        self.trade_history: List[Dict] = []
        
    async def check_risk(self, 
                         symbol: str, 
                         volume: float, 
                         is_buy: bool,
                         account_balance: float = 1000.0) -> tuple[bool, str]:
        """Check all risk shields before executing a trade"""
        
        # Shield 1: Daily Loss Limit
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_pnl[today] <= -self.daily_loss_limit:
            return False, "Daily loss limit reached"
        
        # Shield 2: Max Consecutive Losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, "Max consecutive losses reached"
        
        # Shield 3: Max Trades Per Day
        if self.daily_trades[today] >= self.max_trades_per_day:
            return False, "Max trades per day reached"
        
        # Shield 4: Max Position Size
        if volume > self.max_position_size:
            return False, "Position size exceeds maximum"
        
        # Shield 6: Margin Ratio
        required_margin = volume * 1000 * 0.01  # Simplified margin calculation
        margin_ratio = required_margin / account_balance
        if margin_ratio > self.min_margin_ratio:
            return False, "Insufficient margin"
        
        return True, "OK"
    
    def update_metrics(self, trade_result: Dict[str, Any]) -> None:
        """Update risk metrics after trade completion"""
        pnl = trade_result.get('pnl', 0)
        
        # Update daily PnL
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_pnl[today] += pnl
        
        # Update daily trades
        self.daily_trades[today] += 1
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            self.metrics.losing_trades += 1
        else:
            self.consecutive_losses = 0
            self.metrics.winning_trades += 1
        
        # Update metrics
        self.metrics.total_trades += 1
        self.metrics.total_profit += max(0, pnl)
        self.metrics.total_loss += abs(min(0, pnl))
        self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades if self.metrics.total_trades > 0 else 0
        
        # Update drawdown
        if self.metrics.total_trades > 0:
            running_pnl = sum(t.get('pnl', 0) for t in self.trade_history[-10:])
            if running_pnl < self.metrics.current_drawdown:
                self.metrics.current_drawdown = running_pnl
            self.metrics.max_drawdown = min(self.metrics.max_drawdown, self.metrics.current_drawdown)
        
        # Store history
        self.trade_history.append(trade_result)
        
        logger.info(f"Risk metrics updated - Win Rate: {self.metrics.win_rate:.2%}, Drawdown: {self.metrics.current_drawdown:.2f}")
    
    def reset_daily_limits(self) -> None:
        """Reset daily limits at midnight"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_pnl:
            self.daily_pnl.clear()
            self.daily_trades.clear()
            self.consecutive_losses = 0
            logger.info("Daily limits reset")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        return {
            'win_rate': self.metrics.win_rate,
            'total_trades': self.metrics.total_trades,
            'winning_trades': self.metrics.winning_trades,
            'losing_trades': self.metrics.losing_trades,
            'max_drawdown': self.metrics.max_drawdown,
            'current_drawdown': self.metrics.current_drawdown,
            'daily_pnl': dict(self.daily_pnl),
            'daily_trades': dict(self.daily_trades),
            'consecutive_losses': self.consecutive_losses,
            'total_profit': self.metrics.total_profit,
            'total_loss': self.metrics.total_loss
        }