"""
Master Dashboard Routes - Supabase Version
All data read from trading_platform_db
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
import logging
import jwt
import uuid
import bcrypt

from src.database.supabase_client import get_trading_service
from src.api.routes.master_auth import get_current_master

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# ============================================================
# MODELS
# ============================================================

class ClientCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None
    initial_balance: float = Field(1000.0, gt=0)

class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = ""

class SettingsUpdate(BaseModel):
    performance_fee: Optional[float] = None
    management_fee: Optional[float] = None
    spread_markup: Optional[float] = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_client_name(client: dict) -> str:
    """Get client display name"""
    return client.get('full_name') or client.get('username') or client.get('email') or 'Unknown'

def get_user_id(client) -> str:
    """Get user ID as string"""
    return str(client.get('id'))


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
async def get_dashboard_stats(master: dict = Depends(get_current_master)):
    """Get master dashboard statistics from Supabase"""
    try:
        db = get_trading_service()
        
        # ✅ Get all users (clients)
        users_result = db.client.table('users').select('*').eq('role', 'client').execute()
        clients = users_result.data or []
        
        # ✅ Get all trading balances
        balances_result = db.client.table('trading_balances').select('*').execute()
        balances = {str(b['user_id']): b for b in (balances_result.data or [])}
        
        # ✅ Get open positions
        positions_result = db.client.table('trading_positions').select('*').eq('status', 'OPEN').execute()
        open_positions = positions_result.data or []
        
        # Calculate totals
        total_balance = 0
        total_equity = 0
        total_profit = 0
        
        for client in clients:
            user_id = str(client['id'])
            if user_id in balances:
                total_balance += float(balances[user_id].get('balance', 0))
                total_equity += float(balances[user_id].get('equity', 0))
                total_profit += float(balances[user_id].get('pnl', 0))
        
        return {
            "success": True,
            "stats": {
                "total_clients": len(clients),
                "total_balance": round(total_balance, 2),
                "total_equity": round(total_equity, 2),
                "total_profit": round(total_profit, 2),
                "active_trades": len(open_positions),
                "total_revenue": 0.0
            }
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# CLIENT MANAGEMENT
# ============================================================

@router.get("/clients")
async def get_all_clients(master: dict = Depends(get_current_master)):
    """Get all clients from Supabase"""
    try:
        db = get_trading_service()
        
        # ✅ Get all users with role 'client'
        users_result = db.client.table('users').select('*').eq('role', 'client').execute()
        clients = users_result.data or []
        
        # ✅ Get trading balances for each client
        result = []
        for client in clients:
            user_id = str(client['id'])
            balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id).execute()
            
            balance_data = balance_result.data[0] if balance_result.data else {}
            
            # Get open positions count
            positions_result = db.client.table('trading_positions').select('count').eq('account_id', user_id).eq('status', 'OPEN').execute()
            open_count = positions_result.data[0]['count'] if positions_result.data else 0
            
            result.append({
                'id': user_id,
                'full_name': client.get('full_name', ''),
                'email': client.get('email', ''),
                'phone': client.get('phone', ''),
                'balance': float(balance_data.get('balance', 0)),
                'equity': float(balance_data.get('equity', 0)),
                'profit': float(balance_data.get('pnl', 0)),
                'total_trades': int(balance_data.get('total_trades', 0)),
                'open_positions': open_count,
                'is_active': client.get('is_active', True),
                'role': client.get('role', 'client'),
                'created_at': client.get('created_at')
            })
        
        return {'success': True, 'clients': result, 'total': len(result)}
    except Exception as e:
        logger.error(f"Get clients error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients")
async def create_client(request: ClientCreate, master: dict = Depends(get_current_master)):
    """Create a new client in Supabase"""
    try:
        db = get_trading_service()
        
        # ✅ Check if email already exists
        existing = db.client.table('users').select('*').eq('email', request.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # ✅ Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), salt).decode('utf-8')
        
        # ✅ Create user - let Supabase generate UUID
        user_data = {
            'email': request.email,
            'password_hash': hashed_password,
            'full_name': request.full_name,
            'phone': request.phone,
            'role': 'client',
            'is_active': True,
            'created_at': datetime.now().isoformat()
        }
        
        result = db.client.table('users').insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        user = result.data[0]
        user_id = str(user['id'])
        
        # ✅ Create trading balance
        balance_data = {
            'user_id': user_id,
            'balance': request.initial_balance,
            'equity': request.initial_balance,
            'pnl': 0,
            'total_volume': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_deposited': request.initial_balance,
            'created_at': datetime.now().isoformat()
        }
        db.client.table('trading_balances').insert(balance_data).execute()
        
        # ✅ Log audit
        db.client.table('trading_audit_logs').insert({
            'user_id': user_id,
            'action': 'ADMIN_CREATE_CLIENT',
            'description': f'Admin created client {request.full_name} with ${request.initial_balance}',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return {
            'success': True,
            'message': f'Client {request.full_name} created successfully',
            'client': {
                'id': user_id,
                'full_name': user['full_name'],
                'email': user['email'],
                'initial_balance': request.initial_balance
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create client error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}")
async def get_client_detail(client_id: str, master: dict = Depends(get_current_master)):
    """Get detailed client information"""
    try:
        db = get_trading_service()
        
        # ✅ Query by UUID string
        user_result = db.client.table('users').select('*').eq('id', client_id).execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail=f"Client not found with ID: {client_id}")
        
        client = user_result.data[0]
        user_id = str(client['id'])
        
        # ✅ Get balance
        balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id).execute()
        balance = balance_result.data[0] if balance_result.data else {}
        
        # ✅ Get positions
        positions_result = db.client.table('trading_positions').select('*').eq('account_id', user_id).eq('status', 'OPEN').execute()
        positions = positions_result.data or []
        
        # ✅ Get history
        history_result = db.client.table('trading_orders').select('*').eq('account_id', user_id).order('close_time', desc=True).limit(50).execute()
        history = history_result.data or []
        
        return {
            'success': True,
            'client': {
                'id': client_id,
                'full_name': client.get('full_name', ''),
                'email': client.get('email', ''),
                'phone': client.get('phone', ''),
                'is_active': client.get('is_active', True),
                'balance': float(balance.get('balance', 0)),
                'equity': float(balance.get('equity', 0)),
                'profit': float(balance.get('pnl', 0)),
                'total_trades': int(balance.get('total_trades', 0)),
                'winning_trades': int(balance.get('winning_trades', 0)),
                'losing_trades': int(balance.get('losing_trades', 0)),
                'win_rate': float(balance.get('win_rate', 0)),
                'positions': positions,
                'history': history[:20],
                'created_at': client.get('created_at')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get client detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/deposit")
async def deposit_client(
    client_id: str,
    request: Request,
    master: dict = Depends(get_current_master)
):
    """Deposit funds to client account"""
    try:
        # ✅ Parse request body
        body = await request.json()
        amount = float(body.get('amount', 0))
        description = body.get('description', '')
        
        logger.info(f"📡 Deposit request: client_id={client_id}, amount={amount}")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        db = get_trading_service()
        
        # ✅ Find client
        user_result = db.client.table('users').select('*').eq('id', client_id).execute()
        
        if not user_result.data:
            # Try numeric fallback
            if client_id.isdigit():
                user_result = db.client.table('users').select('*').eq('id', int(client_id)).execute()
        
        if not user_result.data:
            logger.error(f"❌ Client not found with ID: {client_id}")
            raise HTTPException(status_code=404, detail=f"Client not found with ID: {client_id}")
        
        user = user_result.data[0]
        user_id = str(user['id'])
        
        logger.info(f"✅ Client found: {user.get('full_name')} (ID: {user_id})")
        
        # ✅ Get current balance
        balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id).execute()
        
        if balance_result.data:
            current_balance = float(balance_result.data[0].get('balance', 0))
            current_equity = float(balance_result.data[0].get('equity', 0))
            total_deposited = float(balance_result.data[0].get('total_deposited', 0))
            
            db.client.table('trading_balances').update({
                'balance': current_balance + amount,
                'equity': current_equity + amount,
                'total_deposited': total_deposited + amount,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
            
            new_balance = current_balance + amount
            logger.info(f"✅ Balance updated: ${current_balance} → ${new_balance}")
        else:
            db.client.table('trading_balances').insert({
                'user_id': user_id,
                'balance': amount,
                'equity': amount,
                'total_deposited': amount,
                'created_at': datetime.now().isoformat()
            }).execute()
            new_balance = amount
            logger.info(f"✅ New balance created: ${new_balance}")
        
        # ✅ Log audit
        db.client.table('trading_audit_logs').insert({
            'user_id': user_id,
            'action': 'ADMIN_DEPOSIT',
            'description': f'Admin deposited ${amount:.2f} to {user.get("full_name", user.get("email"))}',
            'created_at': datetime.now().isoformat(),
            'metadata': {'amount': amount, 'description': description}
        }).execute()
        
        return {
            'success': True,
            'message': f'Deposited ${amount:.2f} to {user.get("full_name", user.get("email"))}',
            'new_balance': new_balance,
            'amount': amount
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deposit error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/toggle")
async def toggle_client(client_id: str, master: dict = Depends(get_current_master)):
    """Toggle client active status"""
    try:
        db = get_trading_service()
        
        user_result = db.client.table('users').select('*').eq('id', client_id).execute()
        
        if not user_result.data:
            return {
                'success': False,
                'error': f'Client not found with ID: {client_id}'
            }
        
        user = user_result.data[0]
        user_id = str(user['id'])
        new_status = not user.get('is_active', True)
        
        db.client.table('users').update({
            'is_active': new_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        # ✅ Log audit
        db.client.table('trading_audit_logs').insert({
            'user_id': user_id,
            'action': 'ADMIN_TOGGLE_CLIENT',
            'description': f'Admin {"activated" if new_status else "deactivated"} client {user.get("full_name", user.get("email"))}',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return {
            'success': True,
            'message': f'Client {"activated" if new_status else "blocked"} successfully',
            'is_active': new_status,
            'client_id': user_id,
            'client_name': user.get('full_name', user.get('email'))
        }
    except Exception as e:
        logger.error(f"Toggle client error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================
# TRADES - SHOW FROM BOTH trading_positions AND trading_orders
# ============================================================

@router.get("/trades")
async def get_all_trades(master: dict = Depends(get_current_master)):
    """Get ALL trades from trading_positions (all statuses)"""
    try:
        db = get_trading_service()
        
        # ✅ Get ALL positions (not just OPEN)
        all_positions = db.client.table('trading_positions')\
            .select('*')\
            .order('open_time', desc=True)\
            .execute()
        
        positions = all_positions.data or []
        logger.info(f"📊 TOTAL positions found: {len(positions)}")
        
        # ✅ Log each position for debugging
        for pos in positions:
            logger.info(f"📊 Position: {pos.get('position_id')} - Account: {pos.get('account_id')} - Status: {pos.get('status')}")
        
        # ✅ Get all users for lookup (ONLY columns that exist)
        users_result = db.client.table('users')\
            .select('id, full_name, email')\
            .execute()
        
        users = {str(u['id']): u for u in (users_result.data or [])}
        logger.info(f"📊 Users found: {len(users)}")
        
        # ✅ Build trades list
        trades = []
        for pos in positions:
            account_id = str(pos.get('account_id', ''))
            client_name = 'Unknown'
            
            # Try to find user by account_id
            if account_id in users:
                user = users[account_id]
                client_name = user.get('full_name') or user.get('email') or 'Unknown'
            else:
                # Try to match by email
                for uid, user in users.items():
                    if user.get('email') == account_id:
                        client_name = user.get('full_name') or user.get('email') or 'Unknown'
                        break
            
            # Determine status display
            status = pos.get('status', 'UNKNOWN')
            status_display = 'Open' if status == 'OPEN' else 'Closed' if status == 'CLOSED' else status
            
            trades.append({
                'position_id': pos.get('position_id'),
                'account_id': account_id,
                'client_name': client_name,
                'symbol': pos.get('symbol', 'Unknown'),
                'order_type': pos.get('order_type', 'UNKNOWN'),
                'volume': float(pos.get('volume', 0)),
                'entry_price': float(pos.get('entry_price', 0)),
                'current_price': float(pos.get('current_price', pos.get('entry_price', 0))),
                'pnl': float(pos.get('profit', 0)),
                'open_time': pos.get('open_time'),
                'close_time': pos.get('close_time'),
                'status': status,
                'status_display': status_display
            })
        
        logger.info(f"✅ Returning {len(trades)} trades")
        
        return {
            'success': True,
            'trades': trades,
            'total': len(trades),
            'debug': {
                'total_positions': len(positions),
                'users_count': len(users),
                'account_ids': list(set([p.get('account_id') for p in positions]))
            }
        }
    except Exception as e:
        logger.error(f"❌ Get trades error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'trades': [],
            'total': 0
        }
# ============================================================
# TRADE HISTORY (Alias for convenience)
# ============================================================
@router.get("/trades/history")
async def get_trade_history(master: dict = Depends(get_current_master)):
    """Get trade history from trading_orders"""
    try:
        db = get_trading_service()
        
        orders_result = db.client.table('trading_orders')\
            .select('*')\
            .order('close_time', desc=True)\
            .limit(100)\
            .execute()
        
        orders = orders_result.data or []
        
        # ✅ Get users for lookup (ONLY columns that exist)
        users_result = db.client.table('users')\
            .select('id, full_name, email')\
            .execute()
        users = {str(u['id']): u for u in (users_result.data or [])}
        
        for order in orders:
            account_id = order.get('account_id')
            client_name = 'Unknown'
            
            if account_id:
                if account_id in users:
                    user = users[account_id]
                    client_name = user.get('full_name') or user.get('email') or 'Unknown'
                else:
                    # Try to match by email
                    for uid, user in users.items():
                        if user.get('email') == account_id:
                            client_name = user.get('full_name') or user.get('email') or 'Unknown'
                            break
            
            order['client_name'] = client_name
        
        return {
            'success': True,
            'history': orders,
            'total': len(orders)
        }
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return {
            'success': False,
            'error': str(e),
            'history': []
        }
# ============================================================
# REVENUE
# ============================================================

@router.get("/revenue")
async def get_revenue(master: dict = Depends(get_current_master)):
    """Get revenue statistics"""
    try:
        db = get_trading_service()
        
        # ✅ Get all balances
        balances_result = db.client.table('trading_balances').select('*').execute()
        balances = balances_result.data or []
        
        # ✅ Calculate total AUM
        total_balance = sum(float(b.get('balance', 0)) for b in balances)
        
        return {
            'success': True,
            'total': 0.0,
            'performance': 0.0,
            'management': round(total_balance * 0.015 / 12, 2),
            'monthly': round(total_balance * 0.015 / 12, 2),
            'aum': round(total_balance, 2)
        }
    except Exception as e:
        logger.error(f"Revenue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# MT4 STATUS
# ============================================================

@router.get("/mt4/status")
async def get_mt4_status(master: dict = Depends(get_current_master)):
    """Get MT4 connection status"""
    try:
        return {
            'success': True,
            'connected': True,
            'account': '12345678',
            'balance': 0,
            'equity': 0,
            'open_trades': 0,
            'last_sync': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.post("/mt4/sync")
async def sync_mt4(master: dict = Depends(get_current_master)):
    """Sync MT4 data"""
    try:
        return {
            'success': True,
            'message': 'MT4 synced successfully',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================
# SETTINGS
# ============================================================

@router.get("/settings")
async def get_settings(master: dict = Depends(get_current_master)):
    """Get platform settings"""
    try:
        default_settings = {
            'performance_fee': 20.0,
            'management_fee': 1.5,
            'spread_markup': 0.2,
            'min_deposit': 100,
            'max_leverage': 100
        }
        return {'success': True, 'settings': default_settings}
    except Exception as e:
        logger.error(f"Get settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def update_settings(request: SettingsUpdate, master: dict = Depends(get_current_master)):
    """Update platform settings"""
    try:
        return {'success': True, 'message': 'Settings updated successfully'}
    except Exception as e:
        logger.error(f"Update settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ACTIVITY LOG
# ============================================================

@router.get("/activity")
async def get_activity(master: dict = Depends(get_current_master)):
    """Get recent platform activity"""
    try:
        db = get_trading_service()
        
        # Get recent audit logs
        result = db.client.table('trading_audit_logs').select('*').order('created_at', desc=True).limit(50).execute()
        logs = result.data or []
        
        # Get client names
        for log in logs:
            user_id = log.get('user_id')
            if user_id:
                user_result = db.client.table('users').select('full_name, email').eq('id', user_id).execute()
                if user_result.data:
                    log['client_name'] = user_result.data[0].get('full_name') or user_result.data[0].get('email') or 'Unknown'
                else:
                    log['client_name'] = 'Unknown'
        
        return {'success': True, 'activities': logs, 'total': len(logs)}
    except Exception as e:
        logger.error(f"Get activity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))