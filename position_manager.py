# position_manager.py - COMPLETE UPDATED VERSION
"""
Position Sizing & Daily Transaction Manager for Small Account
Account: $989 | Max Daily Loss: 5% ($49.45)
With Anti-Slippage, Monte Carlo Integration, and Emergency Stop
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import threading
import time
import numpy as np

@dataclass
class TradeLimit:
    """Daily trading limits for $989 account"""
    
    # ============ DAILY LIMITS (HARD STOP) ============
    max_daily_loss: float = -49.45        # 5% of $989 = STOP ALL TRADING
    max_daily_risk: float = -30.00        # Stop after $30 floating loss
    max_daily_trades: int = 3             # Maximum 3 trades per day (REDUCED for safety)
    max_daily_volume: float = 0.30        # Maximum 0.30 lots per day
    
    # ============ POSITION LIMITS ============
    max_position_size: float = 0.05       # Maximum 0.05 lots per trade (REDUCED)
    min_position_size: float = 0.01       # Minimum 0.01 lots
    risk_per_trade: float = 0.01          # Risk 1% of account per trade ($9.89)
    max_concurrent_positions: int = 1     # ONLY 1 trade at a time (REDUCED)
    
    # ============ PER-SYMBOL LIMITS ============
    max_symbol_exposure: float = 0.15     # Max 15% of account per symbol
    
    # ============ SPREAD LIMITS ============
    max_spread_forex: float = 0.0005      # 5 pips max for forex
    max_spread_metal: float = 0.50        # 50 cents max for metals
    max_spread_index: float = 5.0         # 5 points max for indices
    max_spread_oil: float = 0.10          # 10 cents max for oil
    
    # ============ VOLATILITY LIMITS ============
    max_volatility_zscore: float = 3.0    # 3 standard deviations = structural break


@dataclass
class PositionSize:
    """Calculated position size"""
    lots: float
    risk_amount: float
    stop_loss_points: float
    take_profit_points: float
    account_percentage: float


class PositionManager:
    """Manages position sizing and daily trading limits for small account"""
    
    def __init__(self):
        self.limits = TradeLimit()
        self.daily_trades = 0
        self.daily_volume = 0
        self.daily_pnl = 0
        self.daily_risk_used = 0
        self.open_positions = []
        self.trade_history = deque(maxlen=1000)
        self.current_date = date.today()
        self.lock = threading.Lock()
        
        # Per-symbol position tracking
        self.symbol_positions = {}
        
        # Account balance (updated from MT4)
        self.account_balance = 989.00
        
        # ============ EMERGENCY STOP ============
        self.emergency_stop_triggered = False
        self.emergency_stop_reason = ""
        
        # ============ MONTE CARLO INTEGRATION ============
        self.monte_carlo_expected_vol = 0.15
        self.vol_std = 0.05
        self.structural_break_detected = False
        
        # ============ PERFORMANCE TRACKING ============
        self.win_count = 0
        self.loss_count = 0
        self.total_pnl = 0
        
        print("✅ Position Manager Initialized")
        print(f"   Account: ${self.account_balance:.2f}")
        print(f"   Max Daily Loss: ${abs(self.limits.max_daily_loss):.2f} (5%)")
        print(f"   Max Trades/Day: {self.limits.max_daily_trades}")
        print(f"   Max Position: {self.limits.max_position_size} lots")
        print(f"   Max Concurrent: {self.limits.max_concurrent_positions}")
    
    # ============================================================
    # ACCOUNT MANAGEMENT
    # ============================================================
    
    def update_balance(self, balance: float):
        """Update current account balance"""
        self.account_balance = balance
        # Recalculate limits based on new balance
        self.limits.max_daily_loss = -balance * 0.05  # 5% of balance
        self.limits.risk_per_trade = 0.01  # 1% risk per trade
        
    def reset_daily_counters(self):
        """Reset daily counters at midnight"""
        today = date.today()
        if today != self.current_date:
            with self.lock:
                self.daily_trades = 0
                self.daily_volume = 0
                self.daily_pnl = 0
                self.daily_risk_used = 0
                self.win_count = 0
                self.loss_count = 0
                self.total_pnl = 0
                self.current_date = today
                self.emergency_stop_triggered = False
                self.emergency_stop_reason = ""
                print(f"📅 Daily counters reset for {today}")
                print(f"   Max Daily Loss: ${abs(self.limits.max_daily_loss):.2f} (5%)")
    
    # ============================================================
    # POSITION SIZING
    # ============================================================
    
    def calculate_position_size(self, account_balance: float, 
                                  entry_price: float,
                                  stop_loss_price: float,
                                  symbol: str,
                                  confidence: float = 50) -> PositionSize:
        """
        Calculate position size based on risk management rules
        
        For $989 account: 1% risk per trade = $9.89
        """
        self.reset_daily_counters()
        self.update_balance(account_balance)
        
        # Check if trading is allowed
        if self.emergency_stop_triggered:
            return PositionSize(0, 0, 0, 0, 0)
        
        # Calculate risk amount (1% of account = $9.89)
        risk_amount = account_balance * self.limits.risk_per_trade
        
        # Adjust risk based on confidence (50-100%)
        confidence_multiplier = min(1.2, max(0.6, confidence / 80))
        adjusted_risk = risk_amount * confidence_multiplier
        
        # Calculate stop loss distance in pips/points
        sl_distance = self._calculate_sl_distance(symbol, entry_price, stop_loss_price)
        
        if sl_distance <= 0:
            sl_distance = 10  # Minimum 10 pips/points
        
        # Calculate lots based on risk
        pip_value = self._get_pip_value(symbol)
        lots = (adjusted_risk / (sl_distance * pip_value)) * 0.01
        
        # Apply position size limits
        lots = max(self.limits.min_position_size, min(self.limits.max_position_size, lots))
        lots = round(lots, 2)
        
        # Ensure we don't exceed daily volume limit
        if self.daily_volume + lots > self.limits.max_daily_volume:
            lots = max(0, self.limits.max_daily_volume - self.daily_volume)
        
        # Ensure we don't exceed daily trades
        if self.daily_trades >= self.limits.max_daily_trades:
            lots = 0
        
        actual_risk = lots * sl_distance * pip_value / 0.01
        risk_percent = (actual_risk / account_balance) * 100 if account_balance > 0 else 0
        
        return PositionSize(
            lots=lots,
            risk_amount=actual_risk,
            stop_loss_points=sl_distance,
            take_profit_points=sl_distance * 2,  # 2:1 risk/reward
            account_percentage=risk_percent
        )
    
    def _calculate_sl_distance(self, symbol: str, entry_price: float, stop_loss_price: float) -> float:
        """Calculate stop loss distance in pips/points"""
        if symbol in ['EURUSD', 'GBPUSD', 'USDCAD', 'AUDUSD', 'NZDUSD']:
            return abs(entry_price - stop_loss_price) * 10000
        elif symbol == 'USDJPY':
            return abs(entry_price - stop_loss_price) * 100
        else:
            return abs(entry_price - stop_loss_price)
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol (micro lots)"""
        if symbol in ['EURUSD', 'GBPUSD', 'USDCAD', 'AUDUSD', 'NZDUSD']:
            return 0.10  # $0.10 per pip for 0.01 lots
        elif symbol == 'USDJPY':
            return 0.08  # ~$0.08 per pip for JPY pairs
        else:
            return 0.10  # Default
    
    # ============================================================
    # TRADE VALIDATION
    # ============================================================
    
    def can_open_trade(self, symbol: str, lots: float, account_balance: float) -> Tuple[bool, str]:
        """
        Check if a new trade can be opened based on limits
        """
        self.reset_daily_counters()
        self.update_balance(account_balance)
        
        with self.lock:
            # Check emergency stop
            if self.emergency_stop_triggered:
                return False, f"🚨 Emergency stop: {self.emergency_stop_reason}"
            
            # Check daily trade count
            if self.daily_trades >= self.limits.max_daily_trades:
                return False, f"Daily trade limit reached ({self.limits.max_daily_trades} trades)"
            
            # Check daily volume
            if self.daily_volume + lots > self.limits.max_daily_volume:
                remaining = self.limits.max_daily_volume - self.daily_volume
                return False, f"Daily volume limit: can trade max {remaining:.2f} lots"
            
            # Check daily loss limit
            if self.daily_pnl <= self.limits.max_daily_loss:
                return False, f"Daily loss limit reached (${abs(self.limits.max_daily_loss):.2f})"
            
            # Check concurrent positions
            if len(self.open_positions) >= self.limits.max_concurrent_positions:
                return False, f"Max positions reached ({self.limits.max_concurrent_positions})"
            
            # Check symbol exposure
            symbol_exposure = self.symbol_positions.get(symbol, 0) + lots
            max_symbol_lots = (account_balance / 10000) * self.limits.max_symbol_exposure
            if symbol_exposure > max_symbol_lots:
                return False, f"Max exposure for {symbol}: {max_symbol_lots:.2f} lots"
            
            # Check minimum lot size
            if lots < self.limits.min_position_size and lots > 0:
                return False, f"Min position size: {self.limits.min_position_size} lots"
            
            # Check risk per trade
            risk_percent = (lots * 100) / account_balance * 100 if account_balance > 0 else 0
            if risk_percent > 2.0:
                return False, f"Risk per trade would be {risk_percent:.1f}% (max 2%)"
            
            return True, "OK"
    
    # ============================================================
    # TRADE REGISTRATION
    # ============================================================
    
    def register_trade(self, symbol: str, lots: float, entry_price: float, 
                       stop_loss: float, take_profit: float, confidence: float):
        """Register a new trade in the manager"""
        with self.lock:
            self.daily_trades += 1
            self.daily_volume += lots
            self.symbol_positions[symbol] = self.symbol_positions.get(symbol, 0) + lots
            
            trade_record = {
                'symbol': symbol,
                'lots': lots,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            self.open_positions.append(trade_record)
            self.trade_history.append(trade_record)
            
            print(f"📊 Trade #{self.daily_trades}: {symbol} {lots} lots @ {entry_price}")
            print(f"   Risk: ${abs((entry_price - stop_loss) * lots * 100):.2f}")
    
    def close_trade(self, symbol: str, exit_price: float, pnl: float):
        """Close a trade and update P&L"""
        with self.lock:
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            if pnl > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            
            # Remove from open positions
            self.open_positions = [p for p in self.open_positions if p['symbol'] != symbol]
            if symbol in self.symbol_positions:
                self.symbol_positions[symbol] = 0
            
            print(f"🔒 Trade closed: {symbol} | P&L: ${pnl:.2f} | Daily: ${self.daily_pnl:.2f}")
            
            # Check daily loss limit
            if self.daily_pnl <= self.limits.max_daily_loss:
                self.trigger_emergency_stop(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
    
    # ============================================================
    # EMERGENCY STOP
    # ============================================================
    
    def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop"""
        self.emergency_stop_triggered = True
        self.emergency_stop_reason = reason
        print(f"🚨 EMERGENCY STOP TRIGGERED: {reason}")
        
        # Send alert
        try:
            from telegram import telegram_bot
            alert = f"""
🚨 *EMERGENCY STOP TRIGGERED* 🚨
━━━━━━━━━━━━━━━━━━━━━
📋 *Reason:* {reason}
💰 *Daily P&L:* ${self.daily_pnl:.2f}
📊 *Trades Today:* {self.daily_trades}
━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            telegram_bot.send_message(alert)
        except:
            pass
    
    def resume_trading(self):
        """Resume trading after emergency stop"""
        self.emergency_stop_triggered = False
        self.emergency_stop_reason = ""
        print("✅ Trading resumed")
    
    # ============================================================
    # MONTE CARLO INTEGRATION
    # ============================================================
    
    def check_market_structure(self, symbol: str = 'EURUSD') -> bool:
        """Check if market structure has changed"""
        try:
            # Get MT4 prices
            from mt4_price_provider import get_mt4_prices
            mt4 = get_mt4_prices()
            
            prices = []
            for i in range(30):
                price_data = mt4.get_price(symbol)
                if price_data.get('success'):
                    prices.append(float(price_data.get('bid', 0)))
                time.sleep(0.1)
            
            if len(prices) < 10:
                return True
            
            # Calculate volatility
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)
            
            if len(returns) < 2:
                return True
            
            current_vol = np.std(returns) * np.sqrt(252 * 24 * 60)
            current_vol = min(current_vol, 0.50)
            
            # Z-score
            z_score = (current_vol - self.monte_carlo_expected_vol) / self.vol_std
            
            if abs(z_score) > self.limits.max_volatility_zscore:
                print(f"⚠️ STRUCTURAL BREAK DETECTED! Z-score: {z_score:.2f}")
                self.structural_break_detected = True
                self.trigger_emergency_stop(f"Structural break: Z-score {z_score:.2f}")
                return False
            
            self.structural_break_detected = False
            return True
            
        except Exception as e:
            print(f"Structure check error: {e}")
            return True
    
    # ============================================================
    # STATUS REPORTING
    # ============================================================
    
    def get_status(self, account_balance: float) -> Dict:
        """Get current position manager status"""
        self.reset_daily_counters()
        self.update_balance(account_balance)
        
        daily_loss_limit = abs(self.limits.max_daily_loss)
        daily_loss_used = max(0, abs(self.daily_pnl))
        win_rate = (self.win_count / (self.win_count + self.loss_count) * 100) if (self.win_count + self.loss_count) > 0 else 0
        
        return {
            'account_balance': account_balance,
            'daily_trades': self.daily_trades,
            'daily_trades_remaining': max(0, self.limits.max_daily_trades - self.daily_trades),
            'daily_volume': round(self.daily_volume, 2),
            'daily_volume_remaining': round(max(0, self.limits.max_daily_volume - self.daily_volume), 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_loss_limit': daily_loss_limit,
            'daily_loss_percent': (daily_loss_used / account_balance * 100) if account_balance > 0 else 0,
            'daily_loss_remaining': round(max(0, daily_loss_limit - daily_loss_used), 2),
            'open_positions': len(self.open_positions),
            'max_concurrent': self.limits.max_concurrent_positions,
            'max_position_size': self.limits.max_position_size,
            'min_position_size': self.limits.min_position_size,
            'risk_per_trade': f"{self.limits.risk_per_trade * 100}%",
            'risk_per_trade_usd': round(account_balance * self.limits.risk_per_trade, 2),
            'symbol_exposure': self.symbol_positions,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(self.total_pnl, 2),
            'emergency_stop': self.emergency_stop_triggered,
            'emergency_stop_reason': self.emergency_stop_reason,
            'structural_break': self.structural_break_detected,
            'can_trade': (
                self.daily_trades < self.limits.max_daily_trades and
                self.daily_pnl > self.limits.max_daily_loss and
                len(self.open_positions) < self.limits.max_concurrent_positions and
                not self.emergency_stop_triggered and
                not self.structural_break_detected
            ),
            'trading_enabled': self.daily_trades < self.limits.max_daily_trades,
            'loss_limit_ok': self.daily_pnl > self.limits.max_daily_loss,
            'position_limit_ok': len(self.open_positions) < self.limits.max_concurrent_positions,
            'volume_limit_ok': self.daily_volume < self.limits.max_daily_volume,
            'daily_loss_percent_limit': 5.0
        }


# Global instance
position_manager = PositionManager()


def get_position_manager() -> PositionManager:
    """Get the global position manager instance"""
    return position_manager


if __name__ == "__main__":
    # Test the position manager with $989 account
    pm = PositionManager()
    balance = 989.00
    
    print("=" * 60)
    print("POSITION MANAGER TEST - $989 ACCOUNT")
    print("=" * 60)
    print(f"Account Balance: ${balance:.2f}")
    print(f"Max Daily Loss: ${abs(pm.limits.max_daily_loss):.2f} (5%)")
    print(f"Risk per Trade: ${balance * 0.01:.2f} (1%)")
    print(f"Max Trades/Day: {pm.limits.max_daily_trades}")
    print(f"Max Volume/Day: {pm.limits.max_daily_volume} lots")
    print(f"Max Position: {pm.limits.max_position_size} lots")
    
    # Test position calculation
    print("\n📊 Position Size Calculation:")
    pos = pm.calculate_position_size(balance, 1.1000, 1.0980, "EURUSD", 75)
    print(f"   EURUSD: {pos.lots} lots (risk ${pos.risk_amount:.2f})")
    
    pos = pm.calculate_position_size(balance, 19500, 19400, "#NASDAQ100", 80)
    print(f"   NASDAQ: {pos.lots} lots (risk ${pos.risk_amount:.2f})")
    
    pos = pm.calculate_position_size(balance, 2350, 2340, "GOLD", 70)
    print(f"   GOLD: {pos.lots} lots (risk ${pos.risk_amount:.2f})")
    
    # Get status
    status = pm.get_status(balance)
    print(f"\n📋 Daily Status:")
    print(f"   Trades Remaining: {status['daily_trades_remaining']}")
    print(f"   Volume Remaining: {status['daily_volume_remaining']} lots")
    print(f"   Loss Remaining: ${status['daily_loss_remaining']:.2f}")
    print(f"   Can Trade: {'✅' if status['can_trade'] else '❌'}")
    print(f"   Emergency Stop: {'✅' if status['emergency_stop'] else '❌'}")