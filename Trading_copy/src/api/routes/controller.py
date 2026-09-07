# src/api/routes/controller.py
"""
Routes for trading controller
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel

from src.services.controller_bridge import controller_bridge
from src.api.middleware.auth import get_current_user

router = APIRouter()

class TradeRequest(BaseModel):
    symbol: str
    order_type: str  # BUY or SELL
    volume: float
    stop_loss: float = 0
    take_profit: float = 0

@router.get("/status")
async def get_controller_status():
    """Get controller status"""
    try:
        status = controller_bridge.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices")
async def get_all_prices():
    """Get all prices from controller"""
    try:
        prices = controller_bridge.get_prices()
        return {
            "success": True,
            "prices": prices,
            "count": len(prices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices/{symbol}")
async def get_price(symbol: str):
    """Get price for a symbol"""
    try:
        prices = controller_bridge.get_prices()
        price = prices.get(symbol, 0)
        if price <= 0:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        return {
            "success": True,
            "symbol": symbol,
            "price": price
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_trade(
    trade: TradeRequest,
    current_user = Depends(get_current_user)
):
    """Execute a trade through the controller"""
    try:
        result = controller_bridge.execute_trade(
            symbol=trade.symbol,
            order_type=trade.order_type,
            volume=trade.volume,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit
        )
        
        if result.get('success'):
            return {
                "success": True,
                "data": result
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Trade execution failed')
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_positions():
    """Get all positions"""
    try:
        positions = controller_bridge.get_positions()
        return {
            "success": True,
            "positions": positions,
            "count": len(positions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cycle")
async def process_cycle():
    """Process one trading cycle"""
    try:
        result = controller_bridge.process_cycle()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols")
async def get_symbols():
    """Get all symbols"""
    try:
        from trading_controller2 import FOREX_PAIRS
        return {
            "success": True,
            "symbols": FOREX_PAIRS,
            "count": len(FOREX_PAIRS)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def get_agents_status():
    """Get status of all agents"""
    try:
        status = controller_bridge.get_status()
        agents = status.get('agents', [])
        return {
            "success": True,
            "agents": [
                {
                    "name": agent.name,
                    "type": agent.agent_type if hasattr(agent, 'agent_type') else "Unknown"
                }
                for agent in agents
            ] if agents else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics():
    """Get trading metrics"""
    try:
        status = controller_bridge.get_status()
        return {
            "success": True,
            "metrics": {
                "daily_pnl": status.get('daily_pnl', 0),
                "trades_today": status.get('trades_today', 0),
                "active_positions": status.get('active_count', 0),
                "cycle_count": status.get('cycle_count', 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))