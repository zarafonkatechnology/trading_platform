# src/api/routes/controllers.py
"""
API routes for trading controllers
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

import sys
from pathlib import Path
from src.api.routes.auth import oauth2_scheme  # or wherever your auth is defined

# Add trading_copy to path
trading_path = Path(__file__).parent.parent.parent.parent / "trading_copy"
sys.path.insert(0, str(trading_path))

router = APIRouter()

# Import controllers
try:
    from trading_controller import AITradingController, SYMBOLS_TO_TRADE
    INDICES_CONTROLLER_AVAILABLE = True
except ImportError:
    INDICES_CONTROLLER_AVAILABLE = False
    print("⚠️ Indices controller not available")

try:
    from trading_controller2 import ForexTradingController, FOREX_PAIRS
    FOREX_CONTROLLER_AVAILABLE = True
except ImportError:
    FOREX_CONTROLLER_AVAILABLE = False
    print("⚠️ Forex controller not available")
try:
    from forex_dashboard import get_all_prices, get_account_info, get_price
    FOREX_DASHBOARD_AVAILABLE = True
    print("✅ Forex Dashboard available")
except ImportError:
    FOREX_DASHBOARD_AVAILABLE = False
    print("⚠️ Forex Dashboard not available")

# ============================================================
# GLOBAL CONTROLLER INSTANCES
# ============================================================

_indices_controller = None
_forex_controller = None

def get_indices_controller():
    """Get or create indices controller singleton"""
    global _indices_controller
    if _indices_controller is None and INDICES_CONTROLLER_AVAILABLE:
        _indices_controller = AITradingController()
    return _indices_controller

def get_forex_controller():
    """Get or create forex controller singleton"""
    global _forex_controller
    if _forex_controller is None and FOREX_CONTROLLER_AVAILABLE:
        config = {
            'pairs': FOREX_PAIRS,
            'min_confidence': 60,
            'cycle_interval': 10,
            'rl_enabled': True,
            'cold_start_threshold': 50,
            'cold_start_min_win_rate': 0.0,
            'enable_entry_confirmation': True,
        }
        _forex_controller = ForexTradingController(config)
    return _forex_controller

# ============================================================
# MODELS
# ============================================================

class ControllerStatus(BaseModel):
    running: bool
    active_positions: int
    symbols: List[str]
    agents: int
    timestamp: str

class TradeRequest(BaseModel):
    symbol: str
    order_type: str  # BUY or SELL
    volume: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradeResponse(BaseModel):
    success: bool
    message: str
    symbol: str
    order_type: str
    price: Optional[float] = None
    timestamp: str

class PriceResponse(BaseModel):
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: str

# ============================================================
# INDICES CONTROLLER ENDPOINTS
# ============================================================

@router.get("/indices/status")
async def indices_status():
    """Get indices controller status"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    try:
        controller = get_indices_controller()
        status = controller.get_status()
        return {
            "success": True,
            "data": status,
            "type": "indices",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indices/symbols")
async def indices_symbols():
    """Get all indices/commodities symbols"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    return {
        "success": True,
        "symbols": SYMBOLS_TO_TRADE,
        "count": len(SYMBOLS_TO_TRADE)
    }

@router.get("/indices/prices")
async def indices_prices():
    """Get all indices/commodities prices"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    try:
        controller = get_indices_controller()
        prices = controller.get_all_mt4_prices()
        if not prices:
            raise HTTPException(status_code=503, detail="No live MT4 indices prices available")
        return {
            "success": True,
            "prices": prices,
            "count": len(prices),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indices/price/{symbol}", response_model=PriceResponse)
async def indices_price(symbol: str):
    """Get price for a specific indices/commodity symbol"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    try:
        controller = get_indices_controller()
        price_data = controller._get_price_data(symbol)
        price = price_data.get('price', 0)
        
        if price <= 0:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        return PriceResponse(
            symbol=symbol,
            price=price,
            bid=price_data.get('bid', price),
            ask=price_data.get('ask', price),
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/indices/analyze/{symbol}")
async def indices_analyze(symbol: str):
    """Analyze a symbol with all indices agents"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    try:
        controller = get_indices_controller()
        analysis = controller.analyze_market(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/indices/trade", response_model=TradeResponse)
async def indices_trade(trade: TradeRequest):
    """Execute a trade on indices/commodities"""
    if not INDICES_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Indices controller not available")
    
    try:
        controller = get_indices_controller()
        
        # Check if symbol is valid
        if trade.symbol not in SYMBOLS_TO_TRADE:
            raise HTTPException(status_code=400, detail=f"Invalid symbol: {trade.symbol}")
        
        # Execute trade
        success, message = controller.place_order(trade.symbol, trade.order_type)
        
        return TradeResponse(
            success=success,
            message=message,
            symbol=trade.symbol,
            order_type=trade.order_type,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# FOREX CONTROLLER ENDPOINTS
# ============================================================

@router.get("/forex/status")
async def forex_status():
    """Get forex controller status"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    try:
        controller = get_forex_controller()
        status = controller.get_status()
        return {
            "success": True,
            "data": status,
            "type": "forex",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forex/pairs")
async def forex_pairs():
    """Get all forex pairs"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    return {
        "success": True,
        "pairs": FOREX_PAIRS,
        "count": len(FOREX_PAIRS)
    }

@router.get("/forex/prices")
async def forex_prices():
    """Get all forex prices"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    try:
        controller = get_forex_controller()
        prices = controller.get_all_mt4_prices()
        if not prices:
            raise HTTPException(status_code=503, detail="No live MT4 forex prices available")
        return {
            "success": True,
            "prices": prices,
            "count": len(prices),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forex/price/{pair}", response_model=PriceResponse)
async def forex_price(pair: str):
    """Get price for a specific forex pair"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    try:
        controller = get_forex_controller()
        price = controller.get_price(pair)
        
        if price <= 0:
            raise HTTPException(status_code=404, detail=f"Pair {pair} not found")
        
        return PriceResponse(
            symbol=pair,
            price=price,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forex/trade", response_model=TradeResponse)
async def forex_trade(trade: TradeRequest):
    """Execute a trade on forex"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    try:
        controller = get_forex_controller()
        
        # Check if pair is valid
        if trade.symbol not in FOREX_PAIRS:
            raise HTTPException(status_code=400, detail=f"Invalid pair: {trade.symbol}")
        
        # Execute trade
        success, message = controller.place_order(trade.symbol, trade.order_type)
        
        return TradeResponse(
            success=success,
            message=message,
            symbol=trade.symbol,
            order_type=trade.order_type,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forex/cycle")
async def forex_cycle():
    """Run one forex trading cycle"""
    if not FOREX_CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex controller not available")
    
    try:
        controller = get_forex_controller()
        market_data = controller.build_market_data()
        result = controller.process_cycle(market_data)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# In src/api/routes/controllers.py

@router.get("/client/balance")
async def get_client_balance(token: str = Depends(oauth2_scheme)):
    """Get client balance"""
    try:
        # Get the current user from token
        user = await get_current_user(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get balance from database
        from src.database.supabase_client import get_trading_service
        db = get_trading_service()
        
        result = db.client.table('client_balances')\
            .select('*')\
            .eq('client_id', user['id'])\
            .execute()
        
        if result.data and len(result.data) > 0:
            balance_data = result.data[0]
            return {
                "success": True,
                "balance": {
                    "balance": balance_data.get('balance', 0),
                    "equity": balance_data.get('equity', 0),
                    "margin": balance_data.get('margin', 0),
                    "free_margin": balance_data.get('free_margin', 0)
                }
            }
        else:
            # Create default balance if none exists
            return {
                "success": True,
                "balance": {
                    "balance": 0,
                    "equity": 0,
                    "margin": 0,
                    "free_margin": 0
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return {
            "success": False,
            "error": str(e)
        }
# ============================================================
# COMBINED ENDPOINTS
# ============================================================

@router.get("/all/prices")
async def all_prices():
    """Get all prices from both controllers"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "indices": {},
        "forex": {}
    }
    
    if INDICES_CONTROLLER_AVAILABLE:
        try:
            controller = get_indices_controller()
            result["indices"] = controller.get_all_mt4_prices()
        except Exception as exc:
            result["indices_error"] = str(exc)
            result["indices"] = {}
    
    if FOREX_CONTROLLER_AVAILABLE:
        try:
            controller = get_forex_controller()
            result["forex"] = controller.get_all_mt4_prices()
        except Exception as exc:
            result["forex_error"] = str(exc)
            result["forex"] = {}
    
    if not result["indices"] and not result["forex"]:
        raise HTTPException(status_code=503, detail="No live MT4 prices available")
    
    return {
        "success": True,
        "data": result
    }
@router.get("/forex/dashboard/prices")
async def forex_dashboard_prices():
    """Get prices from forex_price_provider"""
    if not FOREX_DASHBOARD_AVAILABLE:
        raise HTTPException(status_code=503, detail="Forex price provider not available")
    
    try:
        prices = get_all_prices()
        account = get_account_info()
        
        return {
            "success": True,
            "prices": prices,
            "account": account,
            "count": len(prices) if prices else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting forex prices: {e}")
        return {
            "success": False,
            "error": str(e)
        }
@router.get("/all/status")
async def all_status():
    """Get status from both controllers"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "indices": {"available": INDICES_CONTROLLER_AVAILABLE},
        "forex": {"available": FOREX_CONTROLLER_AVAILABLE}
    }
    
    if INDICES_CONTROLLER_AVAILABLE:
        try:
            controller = get_indices_controller()
            status = controller.get_status()
            result["indices"]["status"] = status
        except Exception as e:
            result["indices"]["error"] = str(e)
    
    if FOREX_CONTROLLER_AVAILABLE:
        try:
            controller = get_forex_controller()
            status = controller.get_status()
            result["forex"]["status"] = status
        except Exception as e:
            result["forex"]["error"] = str(e)
    
    return {
        "success": True,
        "data": result
    }