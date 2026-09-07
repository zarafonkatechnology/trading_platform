"""
Master Authentication Routes - Checks role in users table
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging
import jwt
import bcrypt

from src.database.supabase_client import get_user_auth_service, get_trading_service

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# JWT Settings
JWT_SECRET = "your-super-secret-key-change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_master(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current master/admin user from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # ✅ Use TRADING PLATFORM DB (where users are stored)
        db = get_trading_service()
        result = db.client.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = result.data[0]
        
        # ✅ Check if user is admin or master (role column)
        role = user.get('role', 'client')
        if role not in ['admin', 'master']:
            logger.warning(f"❌ User {user.get('email')} is not admin. Role: {role}")
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not user.get('is_active', True):
            raise HTTPException(status_code=403, detail="Account deactivated")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/login")
async def master_login(
    request: Request
):
    """
    Master login - checks users table in TRADING PLATFORM DB
    Requires role = 'admin' or 'master'
    """
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
        
        logger.info(f"📡 Master login attempt: {email}")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # ✅ USE TRADING PLATFORM DB (users are stored here)
        db = get_trading_service()
        
        # Check by email
        result = db.client.table('users').select('*').eq('email', email).execute()
        
        if not result.data:
            logger.warning(f"❌ User not found: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = result.data[0]
        
        # ✅ Check role - must be admin or master
        role = user.get('role', 'client')
        if role not in ['admin', 'master']:
            logger.warning(f"❌ User {email} is not admin. Role: {role}")
            raise HTTPException(status_code=403, detail="Admin access required")
        
        logger.info(f"✅ Admin user found: {email}, Role: {role}")
        
        # ✅ Check if user is active
        if not user.get('is_active', True):
            logger.warning(f"❌ Account deactivated: {email}")
            raise HTTPException(status_code=403, detail="Account deactivated")
        
        # ✅ Verify password
        password_hash = user.get('password_hash', '')
        password_valid = False
        
        # CASE 1: Plain text password (for testing)
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
            import hashlib
            test_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if test_hash == password_hash:
                password_valid = True
                logger.info(f"✅ Password verified (SHA-256): {email}")
        
        if not password_valid:
            logger.warning(f"❌ Invalid password for admin: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # ✅ Create JWT token
        token_data = {
            'user_id': str(user['id']),
            'email': user.get('email'),
            'role': role,
            'username': user.get('username', user.get('email'))
        }
        token = create_access_token(token_data)
        
        logger.info(f"✅ Master login successful: {email}")
        
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user.get('email'),
                "username": user.get('username'),
                "full_name": user.get('full_name'),
                "role": role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Master login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_master_info(
    user: dict = Depends(get_current_master)
):
    """Get current master/admin info"""
    try:
        user_data = {**user}
        user_data.pop('password_hash', None)
        return {
            "success": True,
            "user": user_data
        }
    except Exception as e:
        logger.error(f"❌ Get master info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def master_health():
    """Health check for master auth"""
    try:
        db = get_trading_service()
        db.client.table('users').select('count').limit(1).execute()
        return {
            "status": "healthy",
            "service": "master_auth",
            "supabase": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "master_auth",
            "supabase": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }