# C:\trading_platform\Trading_copy\backend\routes\account.py

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# SYMBOL CONFIGURATION
# ============================================================

SYMBOL_CONFIG = {
    'EURUSD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'GBPUSD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'USDJPY': {'pip': 0.01, 'point_value': 1000, 'contract_size': 100000, 'leverage': 20},
    'USDCHF': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'AUDUSD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'USDCAD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'NZDUSD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'EURGBP': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'EURJPY': {'pip': 0.01, 'point_value': 1000, 'contract_size': 100000, 'leverage': 20},
    'EURCAD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'EURNZD': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'EURCHF': {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20},
    'GOLD': {'pip': 0.1, 'point_value': 1, 'contract_size': 100, 'leverage': 10},
    'SILVER': {'pip': 0.01, 'point_value': 50, 'contract_size': 100, 'leverage': 10},
    '#NASDAQ100': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#DJ30': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#S&P500': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#RUSS2000': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#CAC40': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#DAX40': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#FTSE100': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    '#NIKKEI225': {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20},
    'BRENT_OIL': {'pip': 0.01, 'point_value': 100, 'contract_size': 1000, 'leverage': 10},
    'CrudeOIL': {'pip': 0.01, 'point_value': 100, 'contract_size': 1000, 'leverage': 10},
}


def get_symbol_config(symbol: str) -> dict:
    """Get symbol configuration"""
    if not symbol:
        return {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20}
    symbol = symbol.strip().upper()
    # Handle special symbols
    if symbol in ['GOLD', 'SILVER']:
        return SYMBOL_CONFIG.get(symbol, {'pip': 0.1, 'point_value': 1, 'contract_size': 100, 'leverage': 10})
    if symbol.startswith('#'):
        return SYMBOL_CONFIG.get(symbol, {'pip': 0.1, 'point_value': 1, 'contract_size': 1, 'leverage': 20})
    return SYMBOL_CONFIG.get(symbol, {'pip': 0.0001, 'point_value': 10, 'contract_size': 100000, 'leverage': 20})


# ============================================================
# GET ACCOUNT STATE - FULL IMPLEMENTATION
# ============================================================

@router.get("/account/state")
async def get_account_state(user: dict = Depends(get_current_user)):
    """
    Get complete account state with all margin calculations
    """
    try:
        user_id = user['id']
        logger.info(f"📡 Fetching account state for user: {user_id}")
        
        # ===== GET CLIENT DATA =====
        client = await get_client_from_db(user_id)
        if not client:
            logger.warning(f"⚠️ Client not found for user: {user_id}")
            return {
                'success': False,
                'error': 'Client not found'
            }
        
        # ===== GET OPEN POSITIONS =====
        positions = await get_open_positions_from_db(user_id)
        logger.info(f"📊 Found {len(positions)} open positions")
        
        # ===== CALCULATE ALL METRICS =====
        balance = float(client.get('balance', 0))
        used_margin = 0.0
        unrealized_pnl = 0.0
        position_details = []
        
        # If no positions, return simple state
        if not positions:
            logger.info("📊 No open positions - returning base state")
            return {
                'success': True,
                'data': {
                    'balance': round(balance, 2),
                    'equity': round(balance, 2),
                    'unrealized_pnl': 0.0,
                    'used_margin': 0.0,
                    'free_margin': round(balance, 2),
                    'margin_level': 0.0,
                    'position_count': 0,
                    'daily_pnl': 0.0,
                    'positions': [],
                    'risk_alerts': [],
                    'timestamp': datetime.now().isoformat()
                }
            }
        
        # ===== PROCESS EACH POSITION =====
        for pos in positions:
            try:
                symbol = pos.get('symbol', 'EURUSD')
                order_type = pos.get('order_type', 'BUY')
                volume = float(pos.get('volume', 0))
                entry_price = float(pos.get('entry_price', 0))
                
                # Get current price
                current_price = await get_current_price(symbol)
                if current_price <= 0:
                    current_price = entry_price
                    logger.warning(f"⚠️ No price for {symbol}, using entry price")
                
                # Get config
                config = get_symbol_config(symbol)
                contract_size = config.get('contract_size', 100000)
                leverage = config.get('leverage', 20)
                pip = config.get('pip', 0.0001)
                point_value = config.get('point_value', 10)
                
                # ===== CALCULATE P&L =====
                if order_type == 'BUY':
                    pnl = (current_price - entry_price) * volume * contract_size
                else:
                    pnl = (entry_price - current_price) * volume * contract_size
                
                unrealized_pnl += pnl
                
                # ===== CALCULATE MARGIN =====
                notional_value = volume * contract_size * current_price
                position_margin = notional_value / leverage
                used_margin += position_margin
                
                logger.info(f"📊 {symbol}: Volume={volume}, Entry={entry_price}, Current={current_price}, P&L={pnl:.2f}, Margin={position_margin:.2f}")
                
                position_details.append({
                    'id': pos.get('position_id') or pos.get('id'),
                    'symbol': symbol,
                    'type': order_type,
                    'volume': round(volume, 2),
                    'entry': round(entry_price, 5),
                    'current': round(current_price, 5),
                    'gross_pnl': round(pnl, 2),
                    'swap': float(pos.get('swap', 0)),
                    'commission': float(pos.get('commission', 0)),
                    'net_pnl': round(pnl - float(pos.get('swap', 0)) - float(pos.get('commission', 0)), 2),
                    'used_margin': round(position_margin, 2),
                    'leverage': leverage,
                    'lot_size': round(volume, 2)
                })
                
            except Exception as e:
                logger.error(f"❌ Error processing position {pos}: {e}")
                continue
        
        # ===== CALCULATE ACCOUNT METRICS =====
        equity = balance + unrealized_pnl
        free_margin = equity - used_margin
        margin_level = (equity / used_margin * 100) if used_margin > 0 else 0
        
        # Get daily P&L
        daily_pnl = await get_daily_pnl_from_db(user_id)
        
        # Get risk alerts
        risk_alerts = await get_risk_alerts_from_db(user_id)
        
        # ===== LOG RESULTS =====
        logger.info(f"💰 Account State for {user_id}:")
        logger.info(f"   Balance: ${balance:.2f}")
        logger.info(f"   Equity: ${equity:.2f}")
        logger.info(f"   Used Margin: ${used_margin:.2f}")
        logger.info(f"   Free Margin: ${free_margin:.2f}")
        logger.info(f"   Margin Level: {margin_level:.2f}%")
        logger.info(f"   Positions: {len(positions)}")
        
        # ===== RETURN FULL DATA =====
        return {
            'success': True,
            'data': {
                'balance': round(balance, 2),
                'equity': round(equity, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'used_margin': round(used_margin, 2),
                'free_margin': round(free_margin, 2),
                'margin_level': round(margin_level, 2),
                'position_count': len(positions),
                'daily_pnl': round(daily_pnl, 2),
                'positions': position_details,
                'risk_alerts': risk_alerts,
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting account state: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SIMPLE BALANCE ENDPOINT
# ============================================================

@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    """Get simple balance for client"""
    try:
        user_id = user['id']
        client = await get_client_from_db(user_id)
        
        if not client:
            return {
                'success': False,
                'error': 'Client not found'
            }
        
        balance = float(client.get('balance', 0))
        equity = float(client.get('equity', balance))
        
        return {
            'success': True,
            'balance': {
                'balance': round(balance, 2),
                'equity': round(equity, 2)
            }
        }
    except Exception as e:
        logger.error(f"❌ Error getting balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

async def get_client_from_db(user_id: str) -> dict:
    """Get client data from database"""
    try:
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        # Try clients table first
        result = trading_db.client.table('clients')\
            .select('*')\
            .eq('id', user_id)\
            .execute()
        
        if result.data:
            logger.info(f"✅ Found client in clients table")
            return result.data[0]
        
        # Try trading_accounts table as fallback
        result = trading_db.client.table('trading_accounts')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
        
        if result.data:
            logger.info(f"✅ Found client in trading_accounts table")
            return result.data[0]
        
        logger.warning(f"⚠️ No client found for user: {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting client from DB: {e}")
        return None


async def get_open_positions_from_db(user_id: str) -> List[dict]:
    """Get open positions from database"""
    try:
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        # Try positions table
        result = trading_db.client.table('positions')\
            .select('*')\
            .eq('client_id', user_id)\
            .eq('status', 'OPEN')\
            .execute()
        
        if result.data:
            logger.info(f"✅ Found {len(result.data)} positions in positions table")
            return result.data
        
        # Try trading_positions table as fallback
        result = trading_db.client.table('trading_positions')\
            .select('*')\
            .eq('account_id', user_id)\
            .eq('status', 'OPEN')\
            .execute()
        
        if result.data:
            logger.info(f"✅ Found {len(result.data)} positions in trading_positions table")
            return result.data
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Error getting positions from DB: {e}")
        return []


async def get_current_price(symbol: str) -> float:
    """Get current price for symbol"""
    try:
        # Try price_ticker table first
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        result = trading_db.client.table('price_ticker')\
            .select('bid')\
            .eq('symbol', symbol)\
            .execute()
        
        if result.data and result.data[0].get('bid'):
            return float(result.data[0]['bid'])
        
        # Try MT4 bridge
        try:
            from src.mt4_gateway.mt4_bridge import MT4Bridge
            bridge = MT4Bridge()
            price = bridge.get_price(symbol)
            if price and price > 0:
                return float(price)
        except Exception as e:
            logger.debug(f"MT4 price error: {e}")
        
        # Fallback to default price
        return get_fallback_price(symbol)
        
    except Exception as e:
        logger.error(f"❌ Error getting price for {symbol}: {e}")
        return get_fallback_price(symbol)


def get_fallback_price(symbol: str) -> float:
    """Get fallback price for symbol"""
    prices = {
        'EURUSD': 1.14337,
        'GBPUSD': 1.34509,
        'USDJPY': 162.449,
        'USDCHF': 0.89500,
        'AUDUSD': 0.67250,
        'USDCAD': 1.36520,
        'NZDUSD': 0.61230,
        'EURGBP': 0.85200,
        'EURJPY': 185.620,
        'EURCAD': 1.56000,
        'EURNZD': 1.86500,
        'EURCHF': 0.95400,
        'GOLD': 4010.20,
        'SILVER': 55.90,
        '#NASDAQ100': 28906.00,
        '#DJ30': 52460.00,
        '#S&P500': 7517.00,
        '#RUSS2000': 2981.00,
        '#CAC40': 8377.00,
        '#DAX40': 24996.00,
        '#FTSE100': 10564.00,
        '#NIKKEI225': 65180.00,
        'BRENT_OIL': 87.96,
        'CrudeOIL': 81.75
    }
    return prices.get(symbol, 1.0)


async def get_daily_pnl_from_db(user_id: str) -> float:
    """Get today's P&L"""
    try:
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        today = datetime.now().date().isoformat()
        
        # Try trade_history
        result = trading_db.client.table('trade_history')\
            .select('net_pnl')\
            .eq('client_id', user_id)\
            .gte('close_time', today)\
            .execute()
        
        if result.data:
            total = sum(float(t.get('net_pnl', 0)) for t in result.data)
            return total
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error getting daily P&L: {e}")
        return 0.0


async def get_risk_alerts_from_db(user_id: str) -> List[dict]:
    """Get active risk alerts"""
    try:
        from src.database.supabase_client import get_trading_service
        trading_db = get_trading_service()
        
        result = trading_db.client.table('margin_alerts')\
            .select('*')\
            .eq('client_id', user_id)\
            .eq('is_resolved', False)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        if result.data:
            return result.data
        return []
        
    except Exception as e:
        logger.error(f"Error getting risk alerts: {e}")
        return []


# ============================================================
# TEST ENDPOINT - FOR DEBUGGING
# ============================================================

@router.get("/account/debug")
async def debug_account(user: dict = Depends(get_current_user)):
    """Debug endpoint to check account data"""
    try:
        user_id = user['id']
        logger.info(f"🔍 Debug account for user: {user_id}")
        
        # Get client data
        client = await get_client_from_db(user_id)
        
        # Get positions
        positions = await get_open_positions_from_db(user_id)
        
        # Get prices for positions
        prices = {}
        for pos in positions:
            symbol = pos.get('symbol', 'EURUSD')
            price = await get_current_price(symbol)
            prices[symbol] = price
        
        return {
            'success': True,
            'debug': {
                'user_id': user_id,
                'client': client,
                'positions': positions,
                'prices': prices,
                'position_count': len(positions),
                'timestamp': datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"❌ Debug error: {e}")
        return {
            'success': False,
            'error': str(e)
        }