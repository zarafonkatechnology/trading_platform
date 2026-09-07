"""
Client Authentication Routes - Supabase Version
Login, Registration, and Session Management with Supabase
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import bcrypt
import jwt
import uuid
import hashlib

# ✅ Import the correct functions
from src.database.supabase_client import get_user_auth_service, get_trading_service

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# ============================================================
# JWT SETTINGS
# ============================================================
JWT_SECRET = "your-super-secret-key-change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token using trading_platform_db"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # ✅ USE TRADING PLATFORM DB
        db = get_trading_service()
        result = db.client.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = result.data[0]
        
        if not user.get('is_active', True):
            raise HTTPException(status_code=403, detail="Account deactivated")
        
        # ✅ Get trading balance (don't fail if not exists)
        try:
            balance_result = db.client.table('trading_balances').select('*').eq('user_id', str(user_id)).execute()
            if balance_result.data:
                user['trading_balance'] = balance_result.data[0].get('balance', 0)
                user['equity'] = balance_result.data[0].get('equity', 0)
            else:
                user['trading_balance'] = 0
                user['equity'] = 0
        except Exception as e:
            logger.warning(f"Could not get trading balance: {e}")
            user['trading_balance'] = 0
            user['equity'] = 0
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
# ============================================================
# CLIENT DATA FUNCTIONS (for master.py compatibility)
# ============================================================

CLIENTS = {}  # Empty dict since we're using Supabase

def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """Get client by ID from Supabase"""
    try:
        db = get_user_auth_service()
        result = db.client.table('users').select('*').eq('id', client_id).execute()
        
        if not result.data:
            return None
        
        user = result.data[0]
        
        # Get trading balance
        trading_db = get_trading_service()
        balance_result = trading_db.client.table('trading_balances').select('*').eq('user_id', str(client_id)).execute()
        
        trading_balance = balance_result.data[0].get('balance', 0) if balance_result.data else 0
        
        return {
            'id': user['id'],
            'email': user.get('email'),
            'full_name': user.get('full_name'),
            'role': user.get('role', 'client'),
            'trading_balance': trading_balance,
            'is_active': user.get('is_active', True)
        }
    except Exception as e:
        logger.error(f"❌ Get client by ID error: {e}")
        return None


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post("/login")
async def client_login(
    request: Request
):
    """Client login - CHECKS trading_platform_db.users!"""
    try:
        # Parse request body
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
        
        email = str(payload.get("email", "") or "").strip()
        password = str(payload.get("password", "") or "").strip()
        
        logger.info(f"📡 Login attempt: {email}")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # ✅ FIX: USE TRADING PLATFORM DB (NOT user_auth_db!)
        db = get_trading_service()  # ← trading_platform_db!
        
        logger.info(f"🔍 Checking trading_platform_db.users for email: {email}")
        
        # ✅ Check users in trading_platform_db
        result = db.client.table('users').select('*').eq('email', email).execute()
        
        if not result.data:
            logger.warning(f"❌ User not found in trading_platform_db: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user = result.data[0]
        logger.info(f"✅ User found in trading_platform_db: {user.get('email')}, ID: {user['id']}")
        
        # Check if user is active
        if not user.get('is_active', True):
            logger.warning(f"❌ Account deactivated: {email}")
            raise HTTPException(status_code=403, detail="Account deactivated")
        
        # ============================================================
        # PASSWORD VERIFICATION
        # ============================================================
        password_hash = user.get('password_hash', '')
        password_valid = False
        
        logger.info(f"🔐 Password hash from DB: {password_hash[:20] if password_hash else 'EMPTY'}...")
        
        # CASE 1: Plain text password
        if password_hash == password:
            password_valid = True
            logger.info(f"✅ Password verified (plain text): {email}")
        
        # CASE 2: bcrypt hash
        elif password_hash and password_hash.startswith('$2'):
            try:
                password_valid = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
                if password_valid:
                    logger.info(f"✅ Password verified (bcrypt): {email}")
            except Exception as e:
                logger.warning(f"❌ bcrypt verification error: {e}")
        
        # CASE 3: SHA-256 hash
        elif password_hash and len(password_hash) == 64:
            test_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if test_hash == password_hash:
                password_valid = True
                logger.info(f"✅ Password verified (SHA-256): {email}")
        
        if not password_valid:
            logger.warning(f"❌ Invalid password for user: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # ============================================================
        # CREATE SESSION
        # ============================================================
        
        # Create JWT token
        user_id_str = str(user['id'])
        token_data = {
            'user_id': user_id_str,
            'email': user.get('email'),
            'role': user.get('role', 'client'),
        }
        token = create_access_token(token_data)
        
        # ✅ Update login status in trading_balances (same DB)
        session_token = str(uuid.uuid4())
        
        try:
            # Check if trading_balance exists
            balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id_str).execute()
            
            if balance_result.data:
                # Update existing
                db.client.table('trading_balances').update({
                    'is_logged_in': True,
                    'last_login': datetime.now().isoformat(),
                    'session_token': session_token,
                    'login_count': balance_result.data[0].get('login_count', 0) + 1
                }).eq('user_id', user_id_str).execute()
                logger.info(f"✅ Updated trading balance for user: {user_id_str}")
            else:
                # Create new balance
                db.client.table('trading_balances').insert({
                    'user_id': user_id_str,
                    'balance': 0,
                    'equity': 0,
                    'margin': 0,
                    'free_margin': 0,
                    'pnl': 0,
                    'is_logged_in': True,
                    'last_login': datetime.now().isoformat(),
                    'session_token': session_token,
                    'login_count': 1,
                    'total_volume': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_deposited': 0,
                    'total_withdrawn': 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).execute()
                logger.info(f"✅ Created new trading balance for user: {user_id_str}")
        except Exception as e:
            logger.warning(f"Could not update login status: {e}")
        
        # Log audit
        try:
            db.client.table('trading_audit_logs').insert({
                'user_id': user_id_str,
                'action': 'LOGIN',
                'description': f'User {email} logged in',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Could not log audit: {e}")
        
        logger.info(f"✅ Login successful: {email}")
        
        # Get trading balance for response
        try:
            balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id_str).execute()
            trading_balance = balance_result.data[0].get('balance', 0) if balance_result.data else 0
        except Exception as e:
            trading_balance = 0
        
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user.get('email'),
                "full_name": user.get('full_name'),
                "role": user.get('role', 'client'),
                "trading_balance": trading_balance
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/register")
async def client_register(
    request: Request
):
    """Register a new client - WRITES TO USER AUTH DB"""
    try:
        # Parse request body
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
        
        # ✅ Use 'email' and 'full_name' (NOT 'username')
        email = str(payload.get("email", "") or "").strip()
        password = str(payload.get("password", "") or "").strip()
        full_name = str(payload.get("full_name", "") or "").strip()
        phone = str(payload.get("phone", "") or "").strip()
        
        logger.info(f"📡 Registration attempt: {email}")
        
        # Validation
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")
        
        if '@' not in email:
            raise HTTPException(status_code=400, detail="Valid email is required")
        
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        # ✅ USE USER AUTH DB
        db = get_user_auth_service()
        
        # Check if email already exists
        existing = db.client.table('users').select('*').eq('email', email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password with bcrypt
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Create user (WITHOUT 'username' column!)
        user_data = {
            'email': email,
            'password_hash': hashed_password,
            'full_name': full_name if full_name else email.split('@')[0],
            'phone': phone if phone else None,
            'is_active': True,
            'role': 'client',
            'created_at': datetime.now().isoformat()
        }
        
        result = db.client.table('users').insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        user = result.data[0]
        logger.info(f"✅ User created: {email}, ID: {user['id']}")
        
        # ✅ Create trading balance in TRADING DB
        trading_db = get_trading_service()
        user_id_str = str(user['id'])
        try:
            trading_db.client.table('trading_balances').insert({
                'user_id': user_id_str,
                'balance': 0,
                'equity': 0,
                'margin': 0,
                'free_margin': 0,
                'pnl': 0,
                'total_volume': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'is_logged_in': True,
                'last_login': datetime.now().isoformat(),
                'session_token': session_token,
                'login_count': 1,
                'total_deposited': 0,
                'total_withdrawn': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Could not create trading balance: {e}")
        
        # Log audit
        try:
            trading_db.client.table('trading_audit_logs').insert({
                'user_id': user_id_str,
                'action': 'REGISTER',
                'description': f'User {email} registered',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Could not log audit: {e}")
        
        logger.info(f"✅ Registration successful: {email}")
        
        return {
            "success": True,
            "message": "Account created successfully",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": user.get('full_name'),
                "role": user.get('role', 'client'),
                "trading_balance": 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def client_logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Client logout"""
    try:
        # Get current user
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        email = payload.get('email', 'unknown')
        
        logger.info(f"📡 Logout attempt for user: {email}")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # ✅ USE TRADING PLATFORM DB
        db = get_trading_service()
        
        # ✅ Check if trading_balance exists first
        balance_result = db.client.table('trading_balances').select('*').eq('user_id', user_id).execute()
        
        if balance_result.data:
            # Update existing
            db.client.table('trading_balances').update({
                'is_logged_in': False,
                'last_logout': datetime.now().isoformat(),
                'session_token': None
            }).eq('user_id', user_id).execute()
            logger.info(f"✅ Updated logout status for user: {user_id}")
        else:
            # No balance found - create one with logged_out status
            db.client.table('trading_balances').insert({
                'user_id': user_id,
                'balance': 0,
                'equity': 0,
                'margin': 0,
                'free_margin': 0,
                'pnl': 0,
                'is_logged_in': False,
                'last_logout': datetime.now().isoformat(),
                'login_count': 0,
                'total_volume': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_deposited': 0,
                'total_withdrawn': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
            logger.info(f"✅ Created new trading balance for user: {user_id}")
        
        # Log audit
        try:
            db.client.table('trading_audit_logs').insert({
                'user_id': user_id,
                'action': 'LOGOUT',
                'description': f'User {email} logged out',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Could not log audit: {e}")
        
        logger.info(f"✅ Logout successful: {email}")
        
        # Clear local storage on client side (frontend will handle this)
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/me")
async def get_current_user_info(
    user: dict = Depends(get_current_user)
):
    """Get current user info"""
    try:
        # Remove sensitive data
        user_data = {**user}
        user_data.pop('password_hash', None)
        
        return {
            "success": True,
            "user": user_data
        }
        
    except Exception as e:
        logger.error(f"❌ Get user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance")
async def get_user_balance(
    user: dict = Depends(get_current_user)
):
    """Get user's trading balance"""
    try:
        trading_db = get_trading_service()
        user_id_str = str(user['id'])
        result = trading_db.client.table('trading_balances').select('*').eq('user_id', user_id_str).execute()
        
        if not result.data:
            return {"success": True, "balance": {"balance": 0, "equity": 0}}
        
        return {"success": True, "balance": result.data[0]}
        
    except Exception as e:
        logger.error(f"❌ Balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def auth_health():
    """Health check for auth service"""
    try:
        db = get_user_auth_service()
        db.client.table('users').select('count').limit(1).execute()
        return {
            "status": "healthy",
            "service": "auth",
            "supabase": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "auth",
            "supabase": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# ============================================================

# Alias for client_trades.py
get_current_client = get_current_user