# src/api/routes/trades.py
"""
Trade execution routes - FIXED: No margin deduction
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.trading_engine import TradingEngine, Order, OrderType
from src.core.risk_manager import RiskManager
from src.mt4_gateway.mt4_bridge import MT4Bridge
from src.api.middleware.auth import get_current_user

router = APIRouter()

# Initialize components
trading_engine = TradingEngine()
risk_manager = RiskManager()
mt4_bridge = MT4Bridge()

# Request/Response Models
class TradeRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., EURUSD)")
    order_type: str = Field(..., description="BUY or SELL")
    volume: float = Field(..., gt=0, le=10, description="Trade volume (0.01 - 10)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    comment: Optional[str] = Field("", description="Trade comment")

class TradeResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    order_type: Optional[str] = None
    volume: Optional[float] = None
    price: Optional[float] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None
    balance: Optional[float] = None  # ✅ Added balance to response

class SymbolPrice(BaseModel):
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: str

# Routes
@router.get("/symbols", response_model=List[str])
async def get_symbols():
    """Get all available trading symbols"""
    try:
        symbols = mt4_bridge.get_symbols()
        return symbols
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get symbols: {str(e)}"
        )

@router.get("/price/{symbol}", response_model=SymbolPrice)
async def get_price(symbol: str):
    """Get current price for a symbol"""
    try:
        price = mt4_bridge.get_price(symbol)
        if price is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Symbol {symbol} not found"
            )
        
        bid_ask = mt4_bridge.get_bid_ask(symbol)
        
        return SymbolPrice(
            symbol=symbol,
            price=price,
            bid=bid_ask.get('bid') if bid_ask else None,
            ask=bid_ask.get('ask') if bid_ask else None,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get price: {str(e)}"
        )

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    current_user = Depends(get_current_user)
):
    """
    Execute a trade - ✅ NO MARGIN DEDUCTION
    Balance stays the SAME when opening a trade.
    """
    try:
        # Get current price
        price = mt4_bridge.get_price(trade_request.symbol)
        if price is None:
            return TradeResponse(
                success=False,
                error=f"Symbol {trade_request.symbol} not found"
            )
        
        # Check risk (but don't deduct margin)
        risk_ok, risk_message = await risk_manager.check_risk(
            symbol=trade_request.symbol,
            volume=trade_request.volume,
            is_buy=trade_request.order_type.upper() == 'BUY'
        )
        
        if not risk_ok:
            return TradeResponse(
                success=False,
                error=f"Risk check failed: {risk_message}"
            )
        
        # Create order
        order = Order(
            order_id=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=trade_request.symbol,
            order_type=OrderType.BUY if trade_request.order_type.upper() == 'BUY' else OrderType.SELL,
            volume=trade_request.volume,
            price=price,
            stop_loss=trade_request.stop_loss,
            take_profit=trade_request.take_profit,
            comment=trade_request.comment
        )
        
        # Submit order
        result = await trading_engine.submit_order(order)
        
        # Execute through MT4
        mt4_success = mt4_bridge.execute_order(
            symbol=trade_request.symbol,
            order_type=trade_request.order_type,
            volume=trade_request.volume,
            stop_loss=trade_request.stop_loss or 0,
            take_profit=trade_request.take_profit or 0,
            comment=trade_request.comment
        )
        
        if mt4_success and result.status == OrderStatus.EXECUTED:
            # ✅ Get current balance (unchanged)
            user_balance = await get_user_balance(current_user.id)
            
            return TradeResponse(
                success=True,
                order_id=order.order_id,
                symbol=trade_request.symbol,
                order_type=trade_request.order_type,
                volume=trade_request.volume,
                price=price,
                timestamp=datetime.now().isoformat(),
                balance=user_balance  # ✅ Return unchanged balance
            )
        else:
            return TradeResponse(
                success=False,
                error="MT4 execution failed"
            )
            
    except Exception as e:
        return TradeResponse(
            success=False,
            error=str(e)
        )

@router.post("/close/{order_id}")
async def close_trade(
    order_id: str,
    current_user = Depends(get_current_user)
):
    """
    Close an open trade - ✅ ADD P&L to balance
    """
    try:
        # Get position P&L
        position = trading_engine.get_position(order_id)
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade {order_id} not found"
            )
        
        # Calculate P&L
        pnl = position.profit
        
        # Close the position
        result = await trading_engine.close_position(order_id)
        
        if result:
            # ✅ Add P&L to user balance
            user_id = current_user.id
            await update_user_balance(user_id, pnl)
            
            return {
                "success": True, 
                "message": f"Trade {order_id} closed",
                "pnl": pnl,
                "new_balance": await get_user_balance(user_id)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade {order_id} not found or already closed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close trade: {str(e)}"
        )

@router.get("/positions")
async def get_positions(current_user = Depends(get_current_user)):
    """Get all open positions"""
    try:
        positions = trading_engine.positions
        return {
            "count": len(positions),
            "positions": [
                {
                    "position_id": pos.position_id,
                    "symbol": pos.symbol,
                    "type": pos.order_type.value,
                    "volume": pos.volume,
                    "open_price": pos.open_price,
                    "current_price": pos.current_price,
                    "profit": pos.profit,
                    "open_time": pos.open_time.isoformat()
                }
                for pos in positions.values() if pos.is_open
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )

@router.get("/orders")
async def get_orders(current_user = Depends(get_current_user)):
    """Get all orders"""
    try:
        orders = trading_engine.orders
        return {
            "count": len(orders),
            "orders": [
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "type": order.order_type.value,
                    "volume": order.volume,
                    "price": order.price,
                    "status": order.status.value,
                    "created_at": order.created_at.isoformat()
                }
                for order in orders.values()
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )

@router.get("/stats")
async def get_stats(current_user = Depends(get_current_user)):
    """Get trading statistics"""
    try:
        stats = mt4_bridge.get_stats()
        risk_metrics = risk_manager.get_risk_metrics()
        
        return {
            "trading": stats,
            "risk": risk_metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def get_user_balance(user_id: str) -> float:
    """Get user's current balance"""
    try:
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        result = trading_db.client.table('trading_balances')\
            .select('balance')\
            .eq('user_id', str(user_id))\
            .execute()
        
        if result.data:
            return float(result.data[0].get('balance', 0))
        return 0.0
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return 0.0


async def update_user_balance(user_id: str, pnl: float):
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
            
            # Update balance
            trading_db.client.table('trading_balances')\
                .update({
                    'balance': new_balance,
                    'equity': new_balance,
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('user_id', str(user_id))\
                .execute()
            
            logger.info(f"✅ Balance updated: ${current_balance:.2f} → ${new_balance:.2f} (P&L: ${pnl:.2f})")
            return new_balance
        return 0.0
    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        return 0.0