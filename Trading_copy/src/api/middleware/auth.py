# src/api/middleware/auth.py
"""
Authentication middleware for FastAPI
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Simple in-memory user store (replace with database in production)
USERS = {
    "test@example.com": {
        "password": "password123",
        "full_name": "Test User",
        "role": "admin"
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "your-secret-key", algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user from token"""
    try:
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = USERS.get(email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "email": email,
            "full_name": user.get("full_name", ""),
            "role": user.get("role", "user"),
            "authenticated": True
        }
        
    except jwt.PyJWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, else None"""
    try:
        return await get_current_user(token)
    except HTTPException:
        return None

class AuthMiddleware:
    """Authentication middleware for FastAPI"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip auth for public endpoints
        public_paths = ["/", "/health", "/ping", "/docs", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/register"]
        
        path = scope.get("path", "")
        if any(path.startswith(p) for p in public_paths):
            await self.app(scope, receive, send)
            return
        
        # Check for token
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        
        if not auth_header.startswith("Bearer "):
            # For testing, allow requests without auth
            # In production, this should be required
            await self.app(scope, receive, send)
            return
        
        # Token validation would happen here
        # For now, just pass through
        await self.app(scope, receive, send)