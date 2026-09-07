"""
Guardrail Middleware for Live Trading
Hard-coded safety checks between AI agents and broker
"""

import threading
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class OrderRequest:
    """Structured order request from AI agent"""
    id: str
    agent_name: str
    symbol: str
    action: str  # BUY or SELL
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    rejection_reason: str = ""


class RiskGuardian:
    """
    Hard-coded risk limits that cannot be overridden by AI
    """
    
    # ========== HARD LIMITS (NEVER CHANGE THESE) ==========
    MAX_POSITION_SIZE = 0.5  # Max 0.5 lots (50,000 units)
    MAX_DAILY_TRADES = 10
    MAX_DAILY_LOSS_PERCENT = 2.0  # 2% max daily loss
    MAX_DRAWDOWN_PERCENT = 5.0  # 5% max drawdown
    MIN_STOP_DISTANCE_PIPS = 10  # Min 10 pips stop loss
    MAX_SPREAD_PIPS = 30  # Max 30 pips spread
    COOLDOWN_SECONDS = 60  # Min 60 seconds between trades on same symbol
    
    # Asset-specific limits
    ASSET_LIMITS = {
        'EURUSD': {'max_volume': 0.5, 'min_volume': 0.01, 'pip_size': 0.0001},
        'GBPUSD': {'max_volume': 0.5, 'min_volume': 0.01, 'pip_size': 0.0001},
        'USDJPY': {'max_volume': 0.5, 'min_volume': 0.01, 'pip_size': 0.01},
        'GOLD': {'max_volume': 0.5, 'min_volume': 0.01, 'pip_size': 0.01},
        'NAS100': {'max_volume': 0.5, 'min_volume': 0.01, 'pip_size': 0.1},
    }
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_trade_time: Dict[str, datetime] = {}
        self.trade_history = deque(maxlen=100)
        self.current_drawdown = 0.0
        self.peak_balance = initial_balance
        self.trading_enabled = True
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
    def _reset_daily_if_needed(self):
        """Reset daily counters at midnight"""
        now = datetime.now()
        if now.date() > self.daily_reset_time.date():
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0)
            logger.info("📅 Daily counters reset")
    
    def check_order(self, order: OrderRequest, current_price: float, spread: float) -> Tuple[bool, str]:
        """
        Validate order against hard limits.
        Returns: (is_allowed, rejection_reason)
        """
        self._reset_daily_if_needed()
        
        # ========== HARD LIMIT CHECKS ==========
        
        # 1. Trading enabled?
        if not self.trading_enabled:
            return False, "Trading is disabled (manual override)"
        
        # 2. Volume limits
        asset_limits = self.ASSET_LIMITS.get(order.symbol, self.ASSET_LIMITS['EURUSD'])
        
        if order.volume > self.MAX_POSITION_SIZE:
            return False, f"Volume {order.volume} exceeds max position size {self.MAX_POSITION_SIZE}"
        
        if order.volume > asset_limits['max_volume']:
            return False, f"Volume {order.volume} exceeds asset limit {asset_limits['max_volume']} for {order.symbol}"
        
        if order.volume < asset_limits['min_volume']:
            return False, f"Volume {order.volume} below minimum {asset_limits['min_volume']} for {order.symbol}"
        
        # 3. Daily trade limit
        if self.daily_trades >= self.MAX_DAILY_TRADES:
            return False, f"Daily trade limit reached ({self.daily_trades}/{self.MAX_DAILY_TRADES})"
        
        # 4. Daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.current_balance * 100
        if self.daily_pnl < 0 and daily_loss_pct >= self.MAX_DAILY_LOSS_PERCENT:
            return False, f"Daily loss limit reached ({daily_loss_pct:.1f}%)"
        
        # 5. Drawdown limit
        if self.current_drawdown >= self.MAX_DRAWDOWN_PERCENT:
            return False, f"Drawdown limit reached ({self.current_drawdown:.1f}%)"
        
        # 6. Cooldown on same symbol
        if order.symbol in self.last_trade_time:
            time_since = (datetime.now() - self.last_trade_time[order.symbol]).total_seconds()
            if time_since < self.COOLDOWN_SECONDS:
                return False, f"Cooldown active for {order.symbol} ({time_since:.0f}s < {self.COOLDOWN_SECONDS}s)"
        
        # 7. Spread check
        if spread > self.MAX_SPREAD_PIPS:
            return False, f"Spread too high ({spread:.1f} pips > {self.MAX_SPREAD_PIPS})"
        
        # 8. Stop loss distance check
        pip_size = asset_limits['pip_size']
        if order.action == 'BUY':
            stop_distance = (order.entry_price - order.stop_loss) / pip_size
        else:
            stop_distance = (order.stop_loss - order.entry_price) / pip_size
        
        if stop_distance < self.MIN_STOP_DISTANCE_PIPS:
            return False, f"Stop loss too tight ({stop_distance:.0f} pips < {self.MIN_STOP_DISTANCE_PIPS})"
        
        # 9. Agent confidence check
        if order.confidence < 60:
            return False, f"Agent confidence too low ({order.confidence:.0f}% < 60%)"
        
        # 10. Master Risk Agent sign-off (additional layer)
        if not self._master_risk_approval(order):
            return False, "Master Risk Agent veto"
        
        return True, "Approved"
    
    def _master_risk_approval(self, order: OrderRequest) -> bool:
        """
        Master Risk Agent hard-coded rules
        Cannot be bypassed by any agent
        """
        # Rule 1: No trading during major news (simplified)
        current_hour = datetime.now().hour
        if 13 <= current_hour <= 15:  # NFP/CPI hours
            logger.warning(f"Master Risk Agent: Blocking trade during news hours")
            return False
        
        # Rule 2: Reduce position size for low-confidence strategies
        if order.strategy == 'CONTRARIAN' and order.confidence < 75:
            logger.warning(f"Master Risk Agent: Contrarian strategy needs >75% confidence")
            return False
        
        # Rule 3: No position > 0.3 lots
        if order.volume > 0.3:
            logger.warning(f"Master Risk Agent: Volume {order.volume} > 0.3 requires manual approval")
            return False
        
        return True
    
    def record_trade_result(self, order: OrderRequest, pnl: float, was_win: bool):
        """Update risk metrics after trade closes"""
        self.daily_trades += 1
        self.daily_pnl += pnl
        self.current_balance += pnl
        self.last_trade_time[order.symbol] = datetime.now()
        
        # Update drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': order.symbol,
            'action': order.action,
            'volume': order.volume,
            'pnl': pnl,
            'was_win': was_win,
            'balance': self.current_balance
        })
        
        logger.info(f"📊 Trade recorded: {order.symbol} {order.action} | PnL: ${pnl:.2f} | Balance: ${self.current_balance:.2f}")
    
    def get_status(self) -> Dict:
        """Get current risk status"""
        self._reset_daily_if_needed()
        daily_loss_pct = abs(self.daily_pnl) / self.current_balance * 100 if self.current_balance > 0 else 0
        
        return {
            'trading_enabled': self.trading_enabled,
            'current_balance': round(self.current_balance, 2),
            'initial_balance': self.initial_balance,
            'total_return_pct': round((self.current_balance - self.initial_balance) / self.initial_balance * 100, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_loss_pct': round(daily_loss_pct, 2),
            'daily_trades': self.daily_trades,
            'max_daily_trades': self.MAX_DAILY_TRADES,
            'current_drawdown': round(self.current_drawdown, 2),
            'max_drawdown': self.MAX_DRAWDOWN_PERCENT
        }


class HeartbeatMonitor:
    """
    Heartbeat monitor for ZeroMQ connection
    Sends ping every 1000ms, alerts if connection drops
    """
    
    def __init__(self, bridge, callback, ping_interval_ms: int = 1000):
        self.bridge = bridge
        self.callback = callback
        self.ping_interval = ping_interval_ms / 1000
        self.is_running = False
        self.last_pong = datetime.now()
        self.thread = None
        self.consecutive_failures = 0
        
    def start(self):
        """Start heartbeat monitor"""
        self.is_running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info(f"💓 Heartbeat monitor started (interval: {self.ping_interval}s)")
    
    def stop(self):
        """Stop heartbeat monitor"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("💔 Heartbeat monitor stopped")
    
    def _heartbeat_loop(self):
        """Send periodic pings and check responses"""
        while self.is_running:
            try:
                # Send ping
                if self.bridge and hasattr(self.bridge, 'ping'):
                    result = self.bridge.ping()
                    
                    if result:
                        self.last_pong = datetime.now()
                        self.consecutive_failures = 0
                    else:
                        self.consecutive_failures += 1
                        logger.warning(f"⚠️ Heartbeat ping failed ({self.consecutive_failures})")
                        
                        if self.consecutive_failures >= 3:
                            self._alert_connection_lost()
                else:
                    self.consecutive_failures += 1
                    
            except Exception as e:
                self.consecutive_failures += 1
                logger.error(f"Heartbeat error: {e}")
                
                if self.consecutive_failures >= 3:
                    self._alert_connection_lost()
            
            time.sleep(self.ping_interval)
    
    def _alert_connection_lost(self):
        """Send alert when connection is lost"""
        message = f"""
🚨 *CRITICAL ALERT* - MT4 Connection Lost

⚠️ *Heartbeat failed* for {self.consecutive_failures} consecutive checks
⏰ *Last successful ping:* {self.last_pong.strftime('%H:%M:%S')}

📋 *Actions Required:*
1. Check MT4 terminal is running
2. Verify EA is attached to chart
3. Check ZeroMQ port (5555)
4. Restart MT4 bridge if needed

⚠️ *Check for orphaned positions manually!*
"""
        if self.callback:
            self.callback(message)
        
        logger.error("🚨 HEARTBEAT FAILED - CONNECTION LOST")
        self.consecutive_failures = 0  # Reset to avoid spam


class GuardrailMiddleware:
    """
    Complete guardrail system combining:
    - Risk Guardian (hard limits)
    - Heartbeat Monitor (connection check)
    - Master Risk Agent (veto power)
    """
    
    def __init__(self, bridge, initial_balance: float = 10000):
        self.bridge = bridge
        self.risk_guardian = RiskGuardian(initial_balance)
        self.heartbeat = None
        self.pending_orders: Dict[str, OrderRequest] = {}
        self.order_counter = 0
        self.telegram_callback = None
        
    def set_telegram_callback(self, callback):
        """Set callback for Telegram alerts"""
        self.telegram_callback = callback
        # Start heartbeat with callback
        self.heartbeat = HeartbeatMonitor(self.bridge, callback)
        self.heartbeat.start()
    
    def _send_alert(self, message: str):
        """Send alert via Telegram"""
        if self.telegram_callback:
            self.telegram_callback(message)
        else:
            logger.warning(message)
    
    def submit_order(self, agent_name: str, symbol: str, action: str,
                     volume: float, entry_price: float, stop_loss: float,
                     take_profit: float, confidence: float, strategy: str) -> Dict:
        """
        Submit an order through the guardrail system
        """
        self.order_counter += 1
        order = OrderRequest(
            id=f"ORD_{self.order_counter:04d}",
            agent_name=agent_name,
            symbol=symbol,
            action=action,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strategy=strategy,
            timestamp=datetime.now()
        )
        
        # Step 1: Get current market data
        market_data = self.bridge.get_price(symbol) if self.bridge else {}
        current_price = market_data.get('bid' if action == 'SELL' else 'ask', entry_price)
        spread = market_data.get('spread', 10)
        
        # Step 2: Risk Guardian check
        is_allowed, reason = self.risk_guardian.check_order(order, current_price, spread)
        
        if not is_allowed:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            self._send_alert(f"""
❌ *ORDER REJECTED*

🤖 *Agent:* {agent_name}
📊 *Symbol:* {symbol}
🎯 *Action:* {action}
📦 *Volume:* {volume}
💡 *Reason:* {reason}
""")
            return {'success': False, 'error': reason, 'order_id': order.id}
        
        # Step 3: Execute via bridge
        order.status = OrderStatus.APPROVED
        self.pending_orders[order.id] = order
        
        # Execute order
        if action == 'BUY':
            result = self.bridge.buy(symbol, volume, stop_loss, take_profit, f"AI_{strategy}")
        else:
            result = self.bridge.sell(symbol, volume, stop_loss, take_profit, f"AI_{strategy}")
        
        if result.get('success'):
            order.status = OrderStatus.EXECUTED
            self._send_alert(f"""
✅ *ORDER EXECUTED*

🤖 *Agent:* {agent_name}
📊 *Symbol:* {symbol}
🎯 *Action:* {action}
💰 *Price:* {result.get('price', 'N/A')}
📦 *Volume:* {volume}
📈 *Ticket:* {result.get('ticket', 'N/A')}
🛡️ *Risk Check:* Passed
""")
            return {'success': True, 'order_id': order.id, 'ticket': result.get('ticket')}
        else:
            order.status = OrderStatus.FAILED
            order.rejection_reason = result.get('error', 'Unknown')
            self._send_alert(f"""
❌ *ORDER FAILED*

🤖 *Agent:* {agent_name}
📊 *Symbol:* {symbol}
🎯 *Action:* {action}
❌ *Error:* {result.get('error', 'Unknown')}
""")
            return {'success': False, 'error': result.get('error'), 'order_id': order.id}
    
    def record_trade_result(self, order_id: str, pnl: float):
        """Update risk metrics after trade closes"""
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            self.risk_guardian.record_trade_result(order, pnl, pnl > 0)
    
    def get_status(self) -> Dict:
        """Get complete guardrail status"""
        risk_status = self.risk_guardian.get_status()
        return {
            'risk': risk_status,
            'pending_orders': len([o for o in self.pending_orders.values() if o.status == OrderStatus.PENDING]),
            'total_orders': len(self.pending_orders),
            'heartbeat_active': self.heartbeat.is_running if self.heartbeat else False
        }
    
    def emergency_stop(self):
        """Emergency stop - blocks all new orders"""
        self.risk_guardian.trading_enabled = False
        self._send_alert("""
🛑 *EMERGENCY STOP ACTIVATED*

All trading has been halted immediately.
Manual intervention required to resume.

Use /mt4_resume to re-enable trading after checking positions.
""")
    
    def emergency_resume(self):
        """Resume trading after emergency stop"""
        self.risk_guardian.trading_enabled = True
        self._send_alert("✅ Trading resumed")
