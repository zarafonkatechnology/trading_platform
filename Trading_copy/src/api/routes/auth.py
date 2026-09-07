# src/api/routes/auth.py
"""
Authentication routes with PostgreSQL Database (Supabase)
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import bcrypt
import secrets
import re
from pydantic import BaseModel, EmailStr, Field, validator

# Import database client
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.database.supabase_client import db
    DB_AVAILABLE = True
    print(f"✅ Database connected: {db._connected}")
except ImportError as e:
    DB_AVAILABLE = False
    print(f"⚠️ Database not available: {e}")
except Exception as e:
    DB_AVAILABLE = False
    print(f"⚠️ Database error: {e}")

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ============================================================
# JWT Configuration
# ============================================================

JWT_SECRET = "your-super-secret-key-change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # hours

# ============================================================
# PYDANTIC MODELS
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    trading_balance: float
    is_active: bool
    created_at: str

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Handle both string and bytes password_hash
        if isinstance(password_hash, str):
            password_hash_bytes = password_hash.encode('utf-8')
        else:
            password_hash_bytes = password_hash
        
        return bcrypt.checkpw(password.encode('utf-8'), password_hash_bytes)
    except (ValueError, TypeError) as e:
        print(f"❌ Password verification error: {e}")
        return False

def create_access_token(user_id: int, email: str) -> str:
    """Create JWT access token"""
    payload = {
        'sub': str(user_id),
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_session_token() -> str:
    """Generate a unique session token"""
    return f"sess_{secrets.token_hex(32)}"

# ============================================================
# FALLBACK USER (if database not available)
# ============================================================

FALLBACK_USER = {
    "id": 1,
    "email": "test@example.com",
    "password_hash": hash_password("password123"),
    "full_name": "Test User",
    "trading_balance": 1000.00,
    "is_active": True
}

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post("/register")
async def register_user(user: UserCreate):
    """Register a new user"""
    try:
        if DB_AVAILABLE:
            # Check if user exists
            existing = db.get_user_by_email(user.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Hash password
            password_hash = hash_password(user.password)
            
            # Create user in database
            new_user = db.create_user({
                'email': user.email,
                'password_hash': password_hash,
                'full_name': user.full_name,
                'phone': user.phone,
                'trading_balance': 0.0,
                'created_at': datetime.now().isoformat()
            })
            
            if not new_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user in database"
                )
            
            # Create session
            session_token = generate_session_token()
            db.create_session(
                user_id=new_user['id'],
                session_token=session_token
            )
            
            # Log audit
            db.log_audit(
                user_id=new_user['id'],
                action='REGISTER',
                details=f'User registered with email: {user.email}'
            )
            
            # Create token
            access_token = create_access_token(new_user['id'], new_user['email'])
            
            return {
                'success': True,
                'message': 'User registered successfully',
                'access_token': access_token,
                'token_type': 'bearer',
                'user': {
                    'id': new_user['id'],
                    'email': new_user['email'],
                    'full_name': new_user.get('full_name'),
                    'trading_balance': float(new_user.get('trading_balance', 0))
                }
            }
        else:
            # Fallback: Use test user
            return {
                'success': True,
                'message': 'User registered successfully (fallback mode)',
                'user': {
                    'email': user.email,
                    'full_name': user.full_name
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint"""
    try:
        if DB_AVAILABLE:
            # Get user from database
            user = db.get_user_by_email(form_data.username)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if user is active
            if not user.get('is_active', True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify password
            if not verify_password(form_data.password, user['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create session
            session_token = generate_session_token()
            db.create_session(
                user_id=user['id'],
                session_token=session_token
            )
            
            # Update last login
            db.update_user(user['id'], {
                'last_login': datetime.now().isoformat()
            })
            
            # Log audit
            db.log_audit(
                user_id=user['id'],
                action='LOGIN',
                details=f'User logged in'
            )
            
            # Create token
            access_token = create_access_token(user['id'], user['email'])
            
            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            # Fallback: Use test user
            if form_data.username == FALLBACK_USER["email"] and verify_password(form_data.password, FALLBACK_USER["password_hash"]):
                token = jwt.encode(
                    {
                        "sub": form_data.username,
                        "user_id": FALLBACK_USER["id"],
                        "exp": datetime.utcnow() + timedelta(hours=24)
                    },
                    JWT_SECRET,
                    algorithm=JWT_ALGORITHM
                )
                return {"access_token": token, "token_type": "bearer"}
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user"""
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get('sub'))
        email = payload.get('email')
        
        print(f"🔍 /auth/me - Decoded token: user_id={user_id}, email={email}")
        
        if DB_AVAILABLE:
            print(f"🔍 DB_AVAILABLE: Looking up user {user_id} in database")
            # Get user from database
            user = db.get_user_by_id(user_id)
            if not user:
                print(f"❌ User {user_id} not found in database!")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            print(f"✅ User found: {user.get('email')}")
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "full_name": user.get('full_name'),
                    "phone": user.get('phone'),
                    "trading_balance": float(user.get('trading_balance', 0)),
                    "is_active": user.get('is_active', True),
                    "created_at": user.get('created_at')
                }
            }
        else:
            # Fallback
            print(f"🔍 DB_AVAILABLE is False, using fallback. Email: {email}, FALLBACK_USER['email']: {FALLBACK_USER['email']}")
            if email == FALLBACK_USER["email"]:
                print(f"✅ Fallback user matched!")
                return {
                    "success": True,
                    "user": {
                        "id": FALLBACK_USER["id"],
                        "email": FALLBACK_USER["email"],
                        "full_name": FALLBACK_USER["full_name"],
                        "trading_balance": FALLBACK_USER["trading_balance"],
                        "is_active": True
                    }
                }
            
            print(f"❌ Fallback: Email mismatch! Got {email}, expected {FALLBACK_USER['email']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        print(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )

@router.post("/logout")
async def logout_user(token: str = Depends(oauth2_scheme)):
    """Logout user"""
    try:
        if DB_AVAILABLE:
            # Decode token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = int(payload.get('sub'))
            
            # Log audit
            db.log_audit(
                user_id=user_id,
                action='LOGOUT',
                details='User logged out'
            )
            
            return {
                "success": True,
                "message": "Logged out successfully"
            }
        else:
            return {
                "success": True,
                "message": "Logged out successfully"
            }
            
    except Exception as e:
        print(f"Logout error: {e}")
        return {
            "success": False,
            "message": f"Logout failed: {str(e)}"
        }