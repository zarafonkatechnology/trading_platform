# ============================================================
# position_sizer.py - Anti-Fragile Position Sizing
# ============================================================
# Kelly Criterion + Volatility Adjustment + Drawdown Protection
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime  # ← FIX THIS
import logging

logger = logging.getLogger(__name__)


class AntiFragilePositionSizer:
    """
    Anti-Fragile Position Sizing.
    
    Features:
    - Kelly Criterion (optimal bet sizing)
    - Volatility adjustment
    - Drawdown protection
    - Daily loss limit
    """
    
    def __init__(self):
        self.max_position = 0.05  # Max 5% of account per trade
        self.max_daily_loss = 0.02  # 2% max daily loss
        self.max_monthly_loss = 0.10  # 10% max monthly loss
        
        self.daily_pnl = []
        self.monthly_pnl = []
        self.trade_history = []
        
        self.position_size_multiplier = 1.0
        self.volatility_multiplier = 1.0
        self.drawdown_multiplier = 1.0
        
        self.today = datetime.now().date()
        self.month = datetime.now().month
        
        logger.info("✅ AntiFragilePositionSizer initialized")
        logger.info(f"   Max Position: {self.max_position*100:.1f}% of account")
        logger.info(f"   Max Daily Loss: {self.max_daily_loss*100:.1f}%")
    
    def calculate_position(self, account_equity: float, confidence: float, volatility: float, current_pnl: float = 0) -> float:
        """
        Calculate optimal position size.
        
        Args:
            account_equity: Current account equity
            confidence: Trade confidence (0-100)
            volatility: Current market volatility
            current_pnl: Current trade PnL
        
        Returns:
            Position size in lots
        """
        # Reset daily tracking if new day
        current_date = datetime.now().date()
        if current_date != self.today:
            self.daily_pnl = []
            self.today = current_date
        
        # Reset monthly tracking if new month
        current_month = datetime.now().month
        if current_month != self.month:
            self.monthly_pnl = []
            self.month = current_month
        
        # ===== 1. KELLY CRITERION =====
        kelly_fraction = self._calculate_kelly()
        
        # ===== 2. VOLATILITY ADJUSTMENT =====
        self.volatility_multiplier = self._calculate_volatility_multiplier(volatility)
        
        # ===== 3. DRAWDOWN PROTECTION =====
        self.drawdown_multiplier = self._calculate_drawdown_multiplier()
        
        # ===== 4. CONFIDENCE ADJUSTMENT =====
        confidence_multiplier = confidence / 100
        
        # ===== 5. DAILY LOSS PROTECTION =====
        daily_loss = sum(self.daily_pnl)
        if daily_loss < 0:
            daily_loss_multiplier = max(0.1, 1 - (abs(daily_loss) / (account_equity * self.max_daily_loss)))
        else:
            daily_loss_multiplier = 1.0
        
        # ===== 6. COMBINE =====
        base_position = kelly_fraction * confidence_multiplier
        adjusted_position = base_position * self.volatility_multiplier * self.drawdown_multiplier * daily_loss_multiplier
        
        # ===== 7. CAP POSITION =====
        max_position = self.max_position * self.position_size_multiplier
        final_position = min(adjusted_position, max_position)
        
        # ===== 8. CONVERT TO LOTS =====
        lots = (final_position * account_equity) / 100000
        lots = round(lots, 2)
        lots = max(0.01, min(2.0, lots))  # Between 0.01 and 2.0 lots
        
        # ===== 9. LOG =====
        logger.debug(f"Position Sizing: Kelly={kelly_fraction:.3f}, Vol={self.volatility_multiplier:.2f}, DD={self.drawdown_multiplier:.2f}")
        logger.debug(f"   Final: {lots:.2f} lots ({final_position*100:.2f}% of account)")
        
        return lots
    
    def _calculate_kelly(self) -> float:
        """Calculate Kelly fraction from trade history."""
        if len(self.trade_history) < 10:
            # Default Kelly for unknown system
            return 0.02
        
        recent_trades = self.trade_history[-50:]
        wins = [t for t in recent_trades if t > 0]
        losses = [abs(t) for t in recent_trades if t < 0]
        
        win_rate = len(wins) / len(recent_trades) if recent_trades else 0.5
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        if avg_loss > 0:
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
        else:
            kelly = 0.02
        
        # Half-Kelly for safety
        kelly = max(0.01, min(0.25, kelly * 0.5))
        
        return kelly
    
    def _calculate_volatility_multiplier(self, volatility: float) -> float:
        """Calculate volatility-based position multiplier."""
        if volatility < 0.01:
            return 1.2  # Low volatility - increase position
        elif volatility < 0.02:
            return 1.0  # Normal volatility
        elif volatility < 0.035:
            return 0.8  # Increased volatility
        elif volatility < 0.05:
            return 0.5  # High volatility
        else:
            return 0.3  # Extreme volatility
    
    def _calculate_drawdown_multiplier(self) -> float:
        """Calculate drawdown-based position multiplier."""
        if len(self.trade_history) < 20:
            return 1.0
        
        # Calculate max drawdown
        cumulative = np.cumsum(self.trade_history[-100:])
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / (peak + 1e-8)
        max_drawdown = np.max(drawdown)
        
        if max_drawdown < 0.05:
            return 1.0
        elif max_drawdown < 0.10:
            return 0.75
        elif max_drawdown < 0.15:
            return 0.5
        else:
            return 0.25
    
    def update_trade_history(self, pnl: float):
        """Update trade history with new PnL."""
        self.trade_history.append(pnl)
        self.daily_pnl.append(pnl)
        self.monthly_pnl.append(pnl)
        
        # Keep history limited
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]
    
    def get_status(self) -> Dict:
        """Get current position sizing status."""
        return {
            'position_size_multiplier': self.position_size_multiplier,
            'volatility_multiplier': self.volatility_multiplier,
            'drawdown_multiplier': self.drawdown_multiplier,
            'max_position_percent': self.max_position * 100,
            'trade_count': len(self.trade_history)
        }