# src/mt4_gateway/mt4_orders.py
"""
MT4 Order Manager - Handles order management
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MT4OrderManager:
    """MT4 Order Manager for trade management"""
    
    def __init__(self):
        self.orders = {}
        self._order_counter = 0
    
    def create_order(self, symbol: str, order_type: str, volume: float,
                    price: float, stop_loss: float = 0, take_profit: float = 0,
                    comment: str = "") -> Dict[str, Any]:
        """Create a new order"""
        self._order_counter += 1
        
        order = {
            'ticket': self._order_counter,
            'symbol': symbol,
            'type': order_type,
            'volume': volume,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'comment': comment,
            'status': 'PENDING',
            'created_at': datetime.now().isoformat()
        }
        
        self.orders[self._order_counter] = order
        logger.info(f"Order created: {self._order_counter} - {symbol} {order_type}")
        return order
    
    def get_order(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get order by ticket number"""
        return self.orders.get(ticket)
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        return list(self.orders.values())
    
    def update_order_status(self, ticket: int, status: str) -> bool:
        """Update order status"""
        if ticket in self.orders:
            self.orders[ticket]['status'] = status
            self.orders[ticket]['updated_at'] = datetime.now().isoformat()
            return True
        return False
    
    def cancel_order(self, ticket: int) -> bool:
        """Cancel an order"""
        if ticket in self.orders:
            self.orders[ticket]['status'] = 'CANCELLED'
            self.orders[ticket]['cancelled_at'] = datetime.now().isoformat()
            return True
        return False