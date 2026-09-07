# src/api/routes/indices.py
"""
Indices trading routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel

from src.services.indices_controller_bridge import indices_bridge
from src.api.middleware.auth import get_current_user

router = APIRouter()

class IndicesTradeRequest(BaseModel):
    symbol: str
    order_type: str  # BUY or SELL
    volume: float = 0.02

@router.get("/symbols")
async def get_indices_symbols():
    """Get all indices/commodities symbols"""
    try:
        symbols = indices_bridge.get_symbols()
        return {
            "success": True,
            "symbols": symbols,
            "count": len(symbols)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_indices_status():
    """Get indices controller status"""
    try:
        status = indices_bridge.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices")
async def get_indices_prices():
    """Get all indices/commodities prices"""
    try:
        prices = indices_bridge.get_prices()
        return {
            "success": True,
            "prices": prices,
            "count": len(prices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{symbol}")
async def analyze_indices_symbol(symbol: str):
    """Analyze a symbol with all agents"""
    try:
        result = indices_bridge.analyze_symbol(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "analysis": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_indices_trade(
    trade: IndicesTradeRequest,
    current_user = Depends(get_current_user)
):
    """Execute a trade on indices/commodities"""
    try:
        result = indices_bridge.controller.place_order(
            symbol=trade.symbol,
            order_type=trade.order_type
        )
        
        if result[0]:
            return {
                "success": True,
                "message": result[1],
                "symbol": trade.symbol,
                "order_type": trade.order_type
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result[1]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))