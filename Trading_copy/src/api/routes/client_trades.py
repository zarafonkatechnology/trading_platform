"""
Client trade execution endpoints - Complete P&L Logic
FIXED: NO MARGIN DEDUCTION
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from src.api.routes.client_auth import get_current_user
from src.database.supabase_client import get_trading_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# SYMBOL CONFIGURATION
# ============================================================

SYMBOL_CONFIG = {
    'EURUSD': {'pip': 0.0001, 'point_value': 10},
    'GBPUSD': {'pip': 0.0001, 'point_value': 10},
    'USDJPY': {'pip': 0.01, 'point_value': 1000},
    'USDCHF': {'pip': 0.0001, 'point_value': 10},
    'AUDUSD': {'pip': 0.0001, 'point_value': 10},
    'USDCAD': {'pip': 0.0001, 'point_value': 10},
    'NZDUSD': {'pip': 0.0001, 'point_value': 10},
    'EURGBP': {'pip': 0.0001, 'point_value': 10},
    'EURJPY': {'pip': 0.01, 'point_value': 1000},
    'EURCAD': {'pip': 0.0001, 'point_value': 10},
    'EURNZD': {'pip': 0.0001, 'point_value': 10},
    'EURCHF': {'pip': 0.0001, 'point_value': 10},
    'GOLD': {'pip': 0.1, 'point_value': 1},
    'SILVER': {'pip': 0.01, 'point_value': 50},
    '#NASDAQ100': {'pip': 0.1, 'point_value': 1},
    '#DJ30': {'pip': 0.1, 'point_value': 1},
    '#S&P500': {'pip': 0.1, 'point_value': 1},
    '#RUSS2000': {'pip': 0.1, 'point_value': 1},
    '#CAC40': {'pip': 0.1, 'point_value': 1},
    '#DAX40': {'pip': 0.1, 'point_value': 1},
    '#FTSE100': {'pip': 0.1, 'point_value': 1},
    '#NIKKEI225': {'pip': 0.1, 'point_value': 1},
    'BRENT_OIL': {'pip': 0.01, 'point_value': 100},
    'CrudeOIL': {'pip': 0.01, 'point_value': 100}
}


def get_symbol_config(symbol: str) -> Dict[str, Any]:
    """Get symbol configuration"""
    if not symbol:
        return {'pip': 0.0001, 'point_value': 10}
    symbol = symbol.strip().upper()
    return SYMBOL_CONFIG.get(symbol, {'pip': 0.0001, 'point_value': 10})


def calculate_profit(symbol: str, order_type: str, entry_price: float, exit_price: float, volume: float) -> float:
    """Calculate profit for a trade"""
    config = get_symbol_config(symbol)
    pip = config['pip']
    point_value = config['point_value']
    if order_type == 'BUY':
        return ((exit_price - entry_price) / pip) * point_value * volume
    return ((entry_price - exit_price) / pip) * point_value * volume


# ============================================================
# MODELS
# ============================================================

class TradeRequest(BaseModel):
    symbol: str
    order_type: str  # BUY or SELL
    volume: float
    stop_loss: Optional[float] = 0
    take_profit: Optional[float] = 0
    entry_price: Optional[float] = None  # ✅ Added for marked-up entry price


# ============================================================
# TRADE ENDPOINTS
# ============================================================

@router.post("/trade")
async def execute_client_trade(
    trade: TradeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Execute a trade - ✅ NO MARGIN DEDUCTION
    Balance stays the SAME when opening a trade.
    """
    try:
        logger.info(f"📡 Trade request: {trade.symbol} {trade.order_type} {trade.volume} by user: {user.get('email')}")
        
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        # ✅ Get current balance BEFORE trade
        balance_result = trading_db.client.table('trading_balances')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        if not balance_result.data:
            # Create balance if not exists
            trading_db.client.table('trading_balances')\
                .insert({
                    'user_id': user_id_str,
                    'balance': 100.00,
                    'equity': 100.00,
                    'pnl': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .execute()
            
            balance_result = trading_db.client.table('trading_balances')\
                .select('*')\
                .eq('user_id', user_id_str)\
                .execute()
        
        current_balance = float(balance_result.data[0].get('balance', 0))
        current_equity = float(balance_result.data[0].get('equity', 0))
        
        logger.info(f"💰 BEFORE TRADE - Balance: ${current_balance:.2f}, Equity: ${current_equity:.2f}")
        
        # ✅ Check if balance is 0 - CANNOT TRADE
        if current_balance <= 0:
            raise HTTPException(status_code=400, detail="❌ Balance is $0. Please deposit funds to trade.")
        
        # ✅ Check volume limits
        if trade.volume <= 0:
            raise HTTPException(status_code=400, detail="Volume must be positive")
        if trade.volume > 10:
            raise HTTPException(status_code=400, detail="Max volume is 10 lots")
        
        # ✅ Get current price from MT4
        try:
            from src.mt4_gateway.mt4_bridge import MT4Bridge
            bridge = MT4Bridge()
            price = bridge.get_price(trade.symbol)
            if not price:
                price = 1.0
                logger.warning(f"⚠️ Using fallback price: {price}")
        except Exception as e:
            logger.warning(f"⚠️ MT4 price error: {e}, using fallback")
            price = 1.0
        
        logger.info(f"📊 Price for {trade.symbol}: {price}")
        
        # ✅ Set SL/TP defaults
        config = get_symbol_config(trade.symbol)
        pip = config['pip']
        digits = 5 if pip == 0.0001 else 3
        
        # ✅ Use provided entry price or default to market price
        entry_price = trade.entry_price if trade.entry_price and trade.entry_price > 0 else price
        
        if trade.order_type == 'BUY':
            stop_loss = trade.stop_loss or round(entry_price - 50 * pip, digits)
            take_profit = trade.take_profit or round(entry_price + 100 * pip, digits)
        else:
            stop_loss = trade.stop_loss or round(entry_price + 50 * pip, digits)
            take_profit = trade.take_profit or round(entry_price - 100 * pip, digits)
        
        # ✅ Create position record
        position_id = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        
        position_data = {
            'account_id': user_id_str,
            'position_id': position_id,
            'symbol': trade.symbol,
            'order_type': trade.order_type,
            'volume': trade.volume,
            'entry_price': entry_price,  # ✅ Use marked-up entry price
            'current_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'profit': 0,
            'open_time': datetime.now().isoformat(),
            'status': 'OPEN'
        }
        
        # ✅ Save to Supabase
        result = trading_db.client.table('trading_positions')\
            .insert(position_data)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create position")
        
        position = result.data[0]
        
        # ✅ IMPORTANT: Balance stays the SAME when opening a trade
        new_balance = current_balance  # ← KEEP THE SAME
        new_equity = current_equity    # ← KEEP THE SAME
        
        logger.info(f"💰 AFTER TRADE - Balance: ${new_balance:.2f} (UNCHANGED), Equity: ${new_equity:.2f}")
        
        # ✅ Update balance (unchanged)
        update_result = trading_db.client.table('trading_balances')\
            .update({
                'balance': new_balance,
                'equity': new_equity,
                'updated_at': datetime.now().isoformat()
            })\
            .eq('user_id', user_id_str)\
            .execute()
        
        # ✅ Log audit
        try:
            trading_db.client.table('trading_audit_logs')\
                .insert({
                    'user_id': user_id_str,
                    'action': 'TRADE_OPENED',
                    'description': f'{trade.order_type} {trade.volume} {trade.symbol} @ {entry_price:.5f}',
                    'created_at': datetime.now().isoformat(),
                    'metadata': {
                        'position_id': position_id,
                        'symbol': trade.symbol,
                        'order_type': trade.order_type,
                        'volume': trade.volume,
                        'entry_price': entry_price,
                        'balance_before': current_balance,
                        'balance_after': new_balance,
                        'balance_unchanged': True
                    }
                })\
                .execute()
        except Exception as e:
            logger.warning(f"Could not log audit: {e}")
        
        logger.info(f"✅ Position opened: {position_id} - Balance UNCHANGED: ${new_balance:.2f}")
        
        return {
            "success": True,
            "message": f"{trade.order_type} executed on {trade.symbol}",
            "position": position,
            "balance": new_balance,
            "equity": new_equity,
            "balance_before": current_balance,
            "balance_after": new_balance,
            "balance_unchanged": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Trade execution error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_client_positions(
    user: dict = Depends(get_current_user)
):
    """Get all positions for current user"""
    try:
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        # ✅ Get open positions
        open_result = trading_db.client.table('trading_positions')\
            .select('*')\
            .eq('account_id', user_id_str)\
            .eq('status', 'OPEN')\
            .order('open_time', desc=True)\
            .execute()
        
        # ✅ Get closed positions (recent)
        closed_result = trading_db.client.table('trading_positions')\
            .select('*')\
            .eq('account_id', user_id_str)\
            .eq('status', 'CLOSED')\
            .order('close_time', desc=True)\
            .limit(50)\
            .execute()
        
        return {
            "success": True,
            "open_positions": open_result.data,
            "closed_positions": closed_result.data,
            "open_count": len(open_result.data),
            "closed_count": len(closed_result.data)
        }
    except Exception as e:
        logger.error(f"❌ Get positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_client_history(
    user: dict = Depends(get_current_user),
    limit: int = 100
):
    """Get trade history for current user"""
    try:
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        logger.info(f"📡 Getting history for user: {user_id_str}")
        
        # ✅ Get from trading_orders first
        result = trading_db.client.table('trading_orders')\
            .select('*')\
            .eq('account_id', user_id_str)\
            .order('close_time', desc=True)\
            .limit(limit)\
            .execute()
        
        history = result.data or []
        
        # ✅ If no orders, get closed positions
        if not history:
            logger.info("No orders found, checking closed positions")
            positions_result = trading_db.client.table('trading_positions')\
                .select('*')\
                .eq('account_id', user_id_str)\
                .eq('status', 'CLOSED')\
                .order('close_time', desc=True)\
                .limit(limit)\
                .execute()
            history = positions_result.data or []
        
        logger.info(f"✅ Found {len(history)} history items")
        
        # ✅ Calculate stats
        total_trades = len(history)
        winning_trades = sum(1 for t in history if t.get('profit', 0) > 0)
        losing_trades = sum(1 for t in history if t.get('profit', 0) < 0)
        total_profit = sum(t.get('profit', 0) for t in history)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        return {
            "success": True,
            "history": history,
            "count": total_trades,
            "stats": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_profit": round(total_profit, 2),
                "win_rate": round(win_rate, 2),
                "avg_profit": round(avg_profit, 2)
            }
        }
    except Exception as e:
        logger.error(f"❌ Get history error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close/{position_id}")
async def close_client_position(
    position_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Close a position - ✅ ADD P&L to balance
    """
    try:
        logger.info(f"📡 Close position request: {position_id} by user: {user.get('email')}")
        
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        # ✅ Get position from Supabase
        result = trading_db.client.table('trading_positions')\
            .select('*')\
            .eq('position_id', position_id)\
            .eq('status', 'OPEN')\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Position not found or already closed")
        
        position = result.data[0]
        
        # ✅ Get current price
        try:
            from src.mt4_gateway.mt4_bridge import MT4Bridge
            bridge = MT4Bridge()
            price = bridge.get_price(position['symbol'])
            if not price:
                price = position['entry_price']
        except:
            price = position['entry_price']
        
        # ✅ Calculate P&L
        pnl = calculate_profit(
            position['symbol'],
            position['order_type'],
            position['entry_price'],
            price,
            position['volume']
        )
        pnl = round(pnl, 2)
        
        logger.info(f"💰 P&L for position: ${pnl:.2f}")
        
        # ✅ Get current balance BEFORE close
        balance_result = trading_db.client.table('trading_balances')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        if not balance_result.data:
            raise HTTPException(status_code=404, detail="Balance not found")
        
        current_balance = float(balance_result.data[0].get('balance', 0))
        current_equity = float(balance_result.data[0].get('equity', 0))
        
        logger.info(f"💰 BEFORE CLOSE - Balance: ${current_balance:.2f}, Equity: ${current_equity:.2f}")
        
        # ✅ Update position as closed
        trading_db.client.table('trading_positions')\
            .update({
                'status': 'CLOSED',
                'close_time': datetime.now().isoformat(),
                'current_price': price,
                'profit': pnl
            })\
            .eq('position_id', position_id)\
            .execute()
        
        # ✅ Save to trading_orders (history)
        order_data = {
            'account_id': user_id_str,
            'order_id': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}",
            'symbol': position['symbol'],
            'order_type': position['order_type'],
            'volume': position['volume'],
            'entry_price': position['entry_price'],
            'exit_price': price,
            'stop_loss': position.get('stop_loss'),
            'take_profit': position.get('take_profit'),
            'profit': pnl,
            'open_time': position['open_time'],
            'close_time': datetime.now().isoformat(),
            'status': 'CLOSED'
        }
        trading_db.client.table('trading_orders')\
            .insert(order_data)\
            .execute()
        
        # ✅ Closing a position: ADD P&L to balance
        new_balance = current_balance + pnl
        new_equity = current_equity + pnl
        
        # ✅ Ensure balance never goes below 0
        if new_balance < 0:
            logger.warning(f"⚠️ Balance would be negative: ${new_balance:.2f}, setting to 0")
            new_balance = 0
        
        logger.info(f"💰 AFTER CLOSE - Balance: ${current_balance:.2f} → ${new_balance:.2f} (P&L: ${pnl:.2f})")
        
        # ✅ Update balance
        trading_db.client.table('trading_balances')\
            .update({
                'balance': new_balance,
                'equity': new_equity,
                'pnl': balance_result.data[0].get('pnl', 0) + pnl,
                'total_trades': balance_result.data[0].get('total_trades', 0) + 1,
                'updated_at': datetime.now().isoformat()
            })\
            .eq('user_id', user_id_str)\
            .execute()
        
        # ✅ Update win/loss stats
        if pnl > 0:
            trading_db.client.table('trading_balances')\
                .update({
                    'winning_trades': balance_result.data[0].get('winning_trades', 0) + 1
                })\
                .eq('user_id', user_id_str)\
                .execute()
        else:
            trading_db.client.table('trading_balances')\
                .update({
                    'losing_trades': balance_result.data[0].get('losing_trades', 0) + 1
                })\
                .eq('user_id', user_id_str)\
                .execute()
        
        # ✅ Update win rate
        total_trades = balance_result.data[0].get('total_trades', 0) + 1
        winning_trades = balance_result.data[0].get('winning_trades', 0) + (1 if pnl > 0 else 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        trading_db.client.table('trading_balances')\
            .update({
                'win_rate': round(win_rate, 2)
            })\
            .eq('user_id', user_id_str)\
            .execute()
        
        # ✅ Log audit
        try:
            trading_db.client.table('trading_audit_logs')\
                .insert({
                    'user_id': user_id_str,
                    'action': 'POSITION_CLOSED',
                    'description': f'Closed {position["symbol"]} P&L: ${pnl:.2f}',
                    'created_at': datetime.now().isoformat(),
                    'metadata': {
                        'position_id': position_id,
                        'symbol': position['symbol'],
                        'pnl': pnl,
                        'new_balance': new_balance
                    }
                })\
                .execute()
        except Exception as e:
            logger.warning(f"Could not log audit: {e}")
        
        logger.info(f"✅ Position closed: {position_id}, P&L: ${pnl:.2f}, New Balance: ${new_balance:.2f}")
        
        return {
            "success": True,
            "message": f"Position closed. P&L: ${pnl:.2f}",
            "pnl": pnl,
            "new_balance": new_balance,
            "new_equity": new_equity,
            "balance_before": current_balance,
            "balance_after": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Close position error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance")
async def get_client_balance(
    user: dict = Depends(get_current_user)
):
    """Get current balance for user"""
    try:
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        result = trading_db.client.table('trading_balances')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        if not result.data:
            # Create balance if not exists
            trading_db.client.table('trading_balances')\
                .insert({
                    'user_id': user_id_str,
                    'balance': 100.00,
                    'equity': 100.00,
                    'pnl': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .execute()
            
            return {
                "success": True,
                "balance": {
                    "balance": 100.00,
                    "equity": 100.00,
                    "pnl": 0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0
                }
            }
        
        balance_data = result.data[0]
        return {
            "success": True,
            "balance": {
                "balance": float(balance_data.get('balance', 0)),
                "equity": float(balance_data.get('equity', 0)),
                "pnl": float(balance_data.get('pnl', 0)),
                "total_trades": int(balance_data.get('total_trades', 0)),
                "winning_trades": int(balance_data.get('winning_trades', 0)),
                "losing_trades": int(balance_data.get('losing_trades', 0)),
                "win_rate": float(balance_data.get('win_rate', 0))
            }
        }
    except Exception as e:
        logger.error(f"❌ Get balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))