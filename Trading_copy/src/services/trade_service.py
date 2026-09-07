# src/services/trade_service.py
"""
Trade service for executing and managing trades - FIXED: No margin deduction
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.trading_engine import TradingEngine, Order, OrderType
from src.core.risk_manager import RiskManager
from src.mt4_gateway.mt4_bridge import MT4Bridge

logger = logging.getLogger(__name__)

class TradeService:
    """Service for managing trades"""
    
    def __init__(self):
        self.trading_engine = TradingEngine()
        self.risk_manager = RiskManager()
        self.mt4_bridge = MT4Bridge()
    
    async def execute_trade(self, 
                           symbol: str, 
                           order_type: str, 
                           volume: float,
                           stop_loss: float = 0,
                           take_profit: float = 0,
                           comment: str = "",
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a trade - ✅ NO MARGIN DEDUCTION
        Balance stays the SAME when opening a trade.
        """
        try:
            logger.info(f"📡 TradeService: {order_type} {volume} {symbol}")
            
            # Get current price
            price = self.mt4_bridge.get_price(symbol)
            if not price:
                return {
                    'success': False,
                    'error': f"Symbol {symbol} not found"
                }
            
            logger.info(f"💰 Price for {symbol}: {price}")
            
            # Check risk (but don't deduct margin)
            risk_ok, risk_message = await self.risk_manager.check_risk(
                symbol=symbol,
                volume=volume,
                is_buy=order_type.upper() == 'BUY'
            )
            
            if not risk_ok:
                logger.warning(f"⚠️ Risk check failed: {risk_message}")
                return {
                    'success': False,
                    'error': risk_message
                }
            
            # ✅ Create order WITHOUT margin deduction
            # We'll use the trading engine but bypass margin deduction
            order = Order(
                order_id=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                symbol=symbol,
                order_type=OrderType.BUY if order_type.upper() == 'BUY' else OrderType.SELL,
                volume=volume,
                price=price,
                stop_loss=stop_loss if stop_loss > 0 else None,
                take_profit=take_profit if take_profit > 0 else None,
                comment=comment
            )
            
            # ✅ Submit to trading engine WITHOUT margin deduction
            # We need to bypass the margin check in trading_engine
            result = await self._submit_order_no_margin(order, user_id)
            
            # Execute through MT4
            mt4_success = self.mt4_bridge.execute_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=comment
            )
            
            if mt4_success and result.get('status') == 'EXECUTED':
                logger.info(f"✅ Trade executed: {order.order_id}")
                return {
                    'success': True,
                    'order_id': order.order_id,
                    'symbol': symbol,
                    'type': order_type,
                    'volume': volume,
                    'price': price,
                    'timestamp': datetime.now().isoformat(),
                    'balance': result.get('balance', 0),  # ✅ Return unchanged balance
                    'margin_deducted': False  # ✅ Flag that margin was NOT deducted
                }
            else:
                logger.error(f"❌ MT4 execution failed")
                return {
                    'success': False,
                    'error': 'MT4 execution failed'
                }
                
        except Exception as e:
            logger.error(f"❌ Trade execution error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _submit_order_no_margin(self, order: Order, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit order WITHOUT margin deduction.
        This bypasses the margin check in trading_engine.
        """
        try:
            # ✅ Store order in trading engine without margin check
            self.trading_engine.orders[order.order_id] = order
            
            # ✅ Update order status to EXECUTED
            order.status = OrderStatus.EXECUTED
            order.executed_at = datetime.now()
            
            # ✅ Add to positions
            position = self.trading_engine._create_position_from_order(order)
            self.trading_engine.positions[position.position_id] = position
            
            # ✅ Get user balance (unchanged)
            balance = await self._get_user_balance(user_id) if user_id else 0
            
            logger.info(f"✅ Order submitted: {order.order_id} - Balance UNCHANGED: ${balance:.2f}")
            
            return {
                'status': 'EXECUTED',
                'order_id': order.order_id,
                'balance': balance,
                'margin_deducted': False
            }
            
        except Exception as e:
            logger.error(f"❌ Order submission error: {e}")
            order.status = OrderStatus.REJECTED
            return {
                'status': 'REJECTED',
                'error': str(e)
            }
    
    async def _get_user_balance(self, user_id: str) -> float:
        """Get user's current balance from database"""
        try:
            from src.database.supabase_client import get_trading_service
            trading_db = get_trading_service()
            
            result = trading_db.client.table('trading_balances')\
                .select('balance')\
                .eq('user_id', str(user_id))\
                .execute()
            
            if result.data:
                return float(result.data[0].get('balance', 0))
            return 100.00  # Default balance if not found
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 100.00
    
    async def close_position(self, position_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Close a position - ✅ ADD P&L to balance
        """
        try:
            logger.info(f"📡 Closing position: {position_id}")
            
            # Get position from trading engine
            position = self.trading_engine.positions.get(position_id)
            if not position:
                return {
                    'success': False,
                    'error': f'Position {position_id} not found or already closed'
                }
            
            # ✅ Calculate P&L
            pnl = position.profit
            logger.info(f"💰 P&L for position: ${pnl:.2f}")
            
            # ✅ Close position in trading engine
            result = await self.trading_engine.close_position(position_id)
            
            if result:
                # ✅ Add P&L to user balance
                if user_id:
                    new_balance = await self._update_user_balance(user_id, pnl)
                else:
                    new_balance = 0
                
                return {
                    'success': True,
                    'message': f'Position {position_id} closed',
                    'pnl': pnl,
                    'new_balance': new_balance
                }
            else:
                return {
                    'success': False,
                    'error': f'Position {position_id} not found or already closed'
                }
                
        except Exception as e:
            logger.error(f"❌ Error closing position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _update_user_balance(self, user_id: str, pnl: float) -> float:
        """Update user's balance with P&L"""
        try:
            from src.database.supabase_client import get_trading_service
            trading_db = get_trading_service()
            
            # Get current balance
            result = trading_db.client.table('trading_balances')\
                .select('balance')\
                .eq('user_id', str(user_id))\
                .execute()
            
            if result.data:
                current_balance = float(result.data[0].get('balance', 0))
                new_balance = current_balance + pnl
                
                # Ensure balance never goes below 0
                if new_balance < 0:
                    logger.warning(f"⚠️ Balance would be negative: ${new_balance:.2f}, setting to 0")
                    new_balance = 0
                
                # Update balance
                trading_db.client.table('trading_balances')\
                    .update({
                        'balance': new_balance,
                        'equity': new_balance,
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('user_id', str(user_id))\
                    .execute()
                
                logger.info(f"💰 Balance updated: ${current_balance:.2f} → ${new_balance:.2f} (P&L: ${pnl:.2f})")
                return new_balance
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error updating balance: {e}")
            return 0.0
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        positions = self.trading_engine.positions
        return [
            {
                'position_id': pos.position_id,
                'symbol': pos.symbol,
                'type': pos.order_type.value,
                'volume': pos.volume,
                'open_price': pos.open_price,
                'current_price': pos.current_price,
                'profit': pos.profit,
                'open_time': pos.open_time.isoformat()
            }
            for pos in positions.values() if pos.is_open
        ]
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        orders = self.trading_engine.orders
        return [
            {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'type': order.order_type.value,
                'volume': order.volume,
                'price': order.price,
                'status': order.status.value,
                'created_at': order.created_at.isoformat()
            }
            for order in orders.values()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics"""
        return {
            'positions': len(self.get_positions()),
            'orders': len(self.get_orders()),
            'risk': self.risk_manager.get_risk_metrics()
        }