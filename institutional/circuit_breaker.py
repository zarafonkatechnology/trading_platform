# ============================================================
# circuit_breaker.py - Multi-Layer Protection
# ============================================================
# Circuit breakers that automatically stop trading
# ============================================================

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CircuitBreakerSystem:
    """
    Multi-layer Circuit Breaker System.
    
    Breakers:
    - Daily loss limit (-2%)
    - Weekly loss limit (-5%)
    - Monthly loss limit (-10%)
    - Max drawdown (-15%)
    - Volatility spike (>8%)
    - Liquidity crisis (>30% spread)
    - Consecutive losses (5 in a row)
    - Max trades per day (10)
    """
    
    def __init__(self):
        self.breakers = {
            'DAILY_LOSS': {
                'threshold': 0.02,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'WEEKLY_LOSS': {
                'threshold': 0.05,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'MONTHLY_LOSS': {
                'threshold': 0.10,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'DRAWDOWN': {
                'threshold': 0.15,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'VOLATILITY_SPIKE': {
                'threshold': 0.08,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'LIQUIDITY_CRISIS': {
                'threshold': 0.3,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'CONSECUTIVE_LOSSES': {
                'threshold': 5,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            },
            'MAX_TRADES': {
                'threshold': 10,
                'active': False,
                'trigger_time': None,
                'current_value': 0
            }
        }
        
        self.daily_pnl = []
        self.weekly_pnl = []
        self.monthly_pnl = []
        self.trade_sequence = []
        self.trades_today = 0
        
        self.today = datetime.now().date()
        self.week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        self.month_start = datetime.now().replace(day=1)
        
        self.is_breached = False
        self.active_breakers = []
        
        logger.info("✅ CircuitBreakerSystem initialized")
    
    def check_breakers(self, current_pnl: float, current_volatility: float, current_spread: float, account_equity: float) -> Dict:
        """
        Check all circuit breakers.
        
        Returns:
            can_trade: bool
            active_breakers: List[str]
            reason: str
        """
        # Reset daily tracking if new day
        current_date = datetime.now().date()
        if current_date != self.today:
            self.daily_pnl = []
            self.trades_today = 0
            self.breakers['DAILY_LOSS']['active'] = False
            self.breakers['MAX_TRADES']['active'] = False
            self.today = current_date
        
        # Reset weekly tracking if new week
        current_week = datetime.now() - timedelta(days=datetime.now().weekday())
        if current_week != self.week_start:
            self.weekly_pnl = []
            self.breakers['WEEKLY_LOSS']['active'] = False
            self.week_start = current_week
        
        # Reset monthly tracking if new month
        current_month = datetime.now().replace(day=1)
        if current_month != self.month_start:
            self.monthly_pnl = []
            self.breakers['MONTHLY_LOSS']['active'] = False
            self.month_start = current_month
        
        # Update sequences
        if current_pnl != 0:
            self.trade_sequence.append(current_pnl)
            self.daily_pnl.append(current_pnl)
            self.weekly_pnl.append(current_pnl)
            self.monthly_pnl.append(current_pnl)
            self.trades_today += 1
        
        # Calculate metrics
        daily_loss = sum(self.daily_pnl)
        weekly_loss = sum(self.weekly_pnl)
        monthly_loss = sum(self.monthly_pnl)
        
        # ===== CHECK EACH BREAKER =====
        active_breakers = []
        
        # 1. Daily Loss
        if daily_loss < -account_equity * self.breakers['DAILY_LOSS']['threshold']:
            self.breakers['DAILY_LOSS']['active'] = True
            self.breakers['DAILY_LOSS']['trigger_time'] = datetime.now()
            self.breakers['DAILY_LOSS']['current_value'] = daily_loss
            active_breakers.append('DAILY_LOSS')
        
        # 2. Weekly Loss
        if weekly_loss < -account_equity * self.breakers['WEEKLY_LOSS']['threshold']:
            self.breakers['WEEKLY_LOSS']['active'] = True
            self.breakers['WEEKLY_LOSS']['trigger_time'] = datetime.now()
            self.breakers['WEEKLY_LOSS']['current_value'] = weekly_loss
            active_breakers.append('WEEKLY_LOSS')
        
        # 3. Monthly Loss
        if monthly_loss < -account_equity * self.breakers['MONTHLY_LOSS']['threshold']:
            self.breakers['MONTHLY_LOSS']['active'] = True
            self.breakers['MONTHLY_LOSS']['trigger_time'] = datetime.now()
            self.breakers['MONTHLY_LOSS']['current_value'] = monthly_loss
            active_breakers.append('MONTHLY_LOSS')
        
        # 4. Drawdown
        if len(self.trade_sequence) > 20:
            cumulative = np.cumsum(self.trade_sequence[-100:])
            peak = np.maximum.accumulate(cumulative)
            drawdown = (peak - cumulative) / (peak + 1e-8)
            max_drawdown = np.max(drawdown)
            
            if max_drawdown > self.breakers['DRAWDOWN']['threshold']:
                self.breakers['DRAWDOWN']['active'] = True
                self.breakers['DRAWDOWN']['trigger_time'] = datetime.now()
                self.breakers['DRAWDOWN']['current_value'] = max_drawdown
                active_breakers.append('DRAWDOWN')
        
        # 5. Consecutive Losses
        recent_losses = 0
        for pnl in reversed(self.trade_sequence[-10:]):
            if pnl < 0:
                recent_losses += 1
            else:
                break
        
        if recent_losses >= self.breakers['CONSECUTIVE_LOSSES']['threshold']:
            self.breakers['CONSECUTIVE_LOSSES']['active'] = True
            self.breakers['CONSECUTIVE_LOSSES']['trigger_time'] = datetime.now()
            self.breakers['CONSECUTIVE_LOSSES']['current_value'] = recent_losses
            active_breakers.append('CONSECUTIVE_LOSSES')
        
        # 6. Max Trades
        if self.trades_today >= self.breakers['MAX_TRADES']['threshold']:
            self.breakers['MAX_TRADES']['active'] = True
            self.breakers['MAX_TRADES']['trigger_time'] = datetime.now()
            self.breakers['MAX_TRADES']['current_value'] = self.trades_today
            active_breakers.append('MAX_TRADES')
        
        # 7. Volatility Spike
        if current_volatility > self.breakers['VOLATILITY_SPIKE']['threshold']:
            self.breakers['VOLATILITY_SPIKE']['active'] = True
            self.breakers['VOLATILITY_SPIKE']['trigger_time'] = datetime.now()
            self.breakers['VOLATILITY_SPIKE']['current_value'] = current_volatility
            active_breakers.append('VOLATILITY_SPIKE')
        
        # 8. Liquidity Crisis
        if current_spread > 0 and current_spread < 100:  # Sanity check
        # Normalize spread (assuming typical spread is 0.0002)
            normalized_spread = current_spread / 0.001  # 0.001 = 10 pips
        if normalized_spread > self.breakers['LIQUIDITY_CRISIS']['threshold']:
            self.breakers['LIQUIDITY_CRISIS']['active'] = True
            self.breakers['LIQUIDITY_CRISIS']['trigger_time'] = datetime.now()
            self.breakers['LIQUIDITY_CRISIS']['current_value'] = normalized_spread
            active_breakers.append('LIQUIDITY_CRISIS')
            
        if self.is_breached:
            logger.warning(f"🔴 Circuit Breakers TRIGGERED:")
            for breaker in active_breakers:
                data = self.breakers[breaker]
                logger.warning(f"   - {breaker}: {data['current_value']:.2f} (threshold: {data['threshold']})")
        
        return {
            'can_trade': not self.is_breached,
            'active_breakers': active_breakers,
            'reason': ', '.join(active_breakers) if active_breakers else 'All clear'
        }
    
    def reset_breaker(self, breaker_name: str):
        """Reset a specific breaker."""
        if breaker_name in self.breakers:
            self.breakers[breaker_name]['active'] = False
            self.breakers[breaker_name]['trigger_time'] = None
            self.active_breakers = [b for b in self.active_breakers if b != breaker_name]
            self.is_breached = len(self.active_breakers) > 0
            logger.info(f"🔄 Reset breaker: {breaker_name}")
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for name in self.breakers:
            self.breakers[name]['active'] = False
            self.breakers[name]['trigger_time'] = None
        self.active_breakers = []
        self.is_breached = False
        logger.info("🔄 All circuit breakers reset")
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status."""
        return {
            'is_breached': self.is_breached,
            'active_breakers': self.active_breakers,
            'breakers': self.breakers,
            'trades_today': self.trades_today
        }