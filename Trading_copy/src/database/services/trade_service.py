# src/services/trade_service.py
"""
Trade service for executing trades
"""

import logging
from typing import Dict, Any, Optional
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
                           comment: str = "") -> Dict[str, Any]:
        """Execute a trade"""
        try:
            # Get current price
            price = self.mt4_bridge.get_price(symbol)
            if not price:
                return {
                    'success': False,
                    'error': f"Symbol {symbol} not found"
                }
            
            # Check risk
            risk_ok, risk_message = await self.risk_manager.check_risk(
                symbol=symbol,
                volume=volume,
                is_buy=order_type.upper() == 'BUY'
            )
            
            if not risk_ok:
                return {
                    'success': False,
                    'error': risk_message
                }
            
            # Create order
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
            
            # Execute through MT4
            mt4_success = self.mt4_bridge.execute_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=comment
            )
            
            if mt4_success:
                return {
                    'success': True,
                    'order_id': order.order_id,
                    'symbol': symbol,
                    'type': order_type,
                    'volume': volume,
                    'price': price,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'MT4 execution failed'
                }
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }