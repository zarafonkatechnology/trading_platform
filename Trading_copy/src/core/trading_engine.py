import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class OrderStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class Order:
    order_id: str
    symbol: str
    order_type: OrderType
    volume: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    execution_price: Optional[float] = None
    comment: str = ""
    magic_number: int = 0

@dataclass
class Position:
    position_id: str
    symbol: str
    order_type: OrderType
    volume: float
    open_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    profit: float = 0.0
    open_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    is_open: bool = True

class TradingEngine:
    """Main trading engine responsible for order management and execution"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self._order_counter = 0
        self._active_symbols: List[str] = []
        self._price_cache: Dict[str, float] = {}
        self._running = False
        
    async def start(self):
        """Start the trading engine"""
        self._running = True
        logger.info("Trading engine started")
        
    async def stop(self):
        """Stop the trading engine"""
        self._running = False
        logger.info("Trading engine stopped")
        
    async def submit_order(self, order: Order) -> Order:
        """Submit a new order"""
        try:
            # Validate order
            if not await self._validate_order(order):
                order.status = OrderStatus.REJECTED
                logger.warning(f"Order {order.order_id} rejected - validation failed")
                return order
            
            # Store order
            self.orders[order.order_id] = order
            logger.info(f"Order {order.order_id} submitted for {order.symbol}")
            
            # Execute order if market order
            if order.order_type in [OrderType.BUY, OrderType.SELL]:
                await self._execute_market_order(order)
            else:
                # For limit/stop orders, add to pending queue
                await self._add_pending_order(order)
            
            return order
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    async def _validate_order(self, order: Order) -> bool:
        """Validate order before submission"""
        # Check symbol exists
        if order.symbol not in self._active_symbols:
            return False
        
        # Check volume limits
        if order.volume <= 0 or order.volume > 100:
            return False
        
        # Check price is reasonable
        if order.price <= 0:
            return False
        
        return True
    
    async def _execute_market_order(self, order: Order) -> None:
        """Execute a market order"""
        try:
            # Get current market price
            current_price = await self._get_market_price(order.symbol)
            
            # Execute order
            order.execution_price = current_price
            order.executed_at = datetime.now()
            order.status = OrderStatus.EXECUTED
            
            # Create position
            position = Position(
                position_id=f"POS-{uuid.uuid4().hex[:8]}",
                symbol=order.symbol,
                order_type=order.order_type,
                volume=order.volume,
                open_price=current_price,
                current_price=current_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit
            )
            self.positions[position.position_id] = position
            
            logger.info(f"Market order {order.order_id} executed at {current_price}")
            
        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            order.status = OrderStatus.REJECTED
    
    async def _add_pending_order(self, order: Order) -> None:
        """Add pending order to queue"""
        logger.info(f"Pending order {order.order_id} added for {order.symbol}")
    
    async def _get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        # Return from cache or fetch from broker
        return self._price_cache.get(symbol, 1.0)
    
    async def update_position(self, position_id: str, current_price: float) -> None:
        """Update position with current price"""
        if position_id in self.positions:
            position = self.positions[position_id]
            position.current_price = current_price
            
            # Calculate profit/loss
            if position.order_type == OrderType.BUY:
                position.profit = (current_price - position.open_price) * position.volume
            else:
                position.profit = (position.open_price - current_price) * position.volume
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        return self.positions.get(position_id)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Order {order_id} cancelled")
                return True
        return False
    
    async def close_position(self, position_id: str) -> bool:
        """Close an open position"""
        if position_id in self.positions:
            position = self.positions[position_id]
            if position.is_open:
                position.is_open = False
                position.close_time = datetime.now()
                logger.info(f"Position {position_id} closed")
                return True
        return False
    
    def update_price(self, symbol: str, price: float) -> None:
        """Update price cache"""
        self._price_cache[symbol] = price
        
        # Update all positions for this symbol
        for position in self.positions.values():
            if position.symbol == symbol and position.is_open:
                position.current_price = price