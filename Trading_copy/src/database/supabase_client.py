# src/database/supabase_client.py - CORRECT APPROACH

import os
from supabase import create_client, Client
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import socket

logger = logging.getLogger(__name__)

# ============================================================
# YOUR SUPABASE CREDENTIALS - CORRECT URL FORMAT
# ============================================================

# TRADING PLATFORM DATABASE
TRADING_SUPABASE_URL = "https://jcvisgkvwlzdohilimni.supabase.co"
TRADING_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDcxNzE4MywiZXhwIjoyMTAwMjkzMTgzfQ.Fb5gcBleB_Xvv0bV0t2AF-o402nBNBz8qnFKkTUKGJk"

# USER AUTH DATABASE
USER_AUTH_SUPABASE_URL = "https://unyronpybahqltrbzxas.supabase.co"
USER_AUTH_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDY1NDcyNSwiZXhwIjoyMTAwMjMwNzI1fQ.57uzkxCpLLhxnK8WUTppGJgQd0a3CKu1E3pFufA_d0o"

print("=" * 60)
print("🔗 Connecting to Supabase")
print("=" * 60)

class SupabaseDB:
    """Supabase Database wrapper using SDK"""
    
    def __init__(self, name: str = "default", url: Optional[str] = None, key: Optional[str] = None):
        self.name = name
        self.url = url or TRADING_SUPABASE_URL
        self.key = key or TRADING_SUPABASE_KEY
        self.client = None
        self._connected = False
        self._connect()
    
    def _connect(self):
        """Connect to Supabase"""
        try:
            print(f"\n📡 Connecting to Supabase [{self.name}]...")
            print(f"   URL: {self.url}")
            self.client = create_client(self.url, self.key)
            self._connected = True
            print("✅ Connected to Supabase successfully!")
            
            # Test connection - try to query users table
            try:
                result = self.client.table('users').select('*').limit(1).execute()
                print(f"   ✅ Users table found! {len(result.data) if result.data else 0} users.")
            except Exception as e:
                print(f"   ⚠️ Could not query users table: {e}")
            
            return
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.client = None
            self._connected = False
    
    # ============================================================
    # USER OPERATIONS
    # ============================================================
    
    def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user"""
        if not self._connected or not self.client:
            print("❌ No database connection - cannot create user")
            return None
        
        try:
            print(f"\n📝 Creating user: {user_data.get('email')}")
            
            # Check if user already exists
            existing = self.client.table('users').select('*').eq('email', user_data.get('email')).execute()
            if existing.data:
                print(f"⚠️ User already exists: {user_data.get('email')}")
                return None
            
            # Insert new user
            result = self.client.table('users').insert({
                'email': user_data.get('email'),
                'password_hash': user_data.get('password_hash'),
                'full_name': user_data.get('full_name'),
                'phone': user_data.get('phone'),
                'is_active': True,
                'role': 'client',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            if result.data:
                print(f"✅ User created: {result.data[0].get('email')}")
                return result.data[0]
            return None
                
        except Exception as e:
            print(f"❌ Create user error: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        if not self._connected or not self.client:
            return None
        
        try:
            result = self.client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Get user error: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        if not self._connected or not self.client:
            return None
        
        try:
            result = self.client.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Get user error: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
        """Update user"""
        if not self._connected or not self.client:
            return None
        
        try:
            result = self.client.table('users').update(update_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Update user error: {e}")
            return None

# ============================================================
# CREATE DATABASE INSTANCES
# ============================================================

# User Auth DB
user_auth_db = SupabaseDB(
    name="User Auth",
    url=USER_AUTH_SUPABASE_URL,
    key=USER_AUTH_SUPABASE_KEY
)

# Trading Platform DB
trading_db = SupabaseDB(
    name="Trading Platform",
    url=TRADING_SUPABASE_URL,
    key=TRADING_SUPABASE_KEY
)


def get_user_auth_service() -> SupabaseDB:
    """Return the Supabase service used for user auth and trading card tables."""
    return user_auth_db


def get_trading_service() -> SupabaseDB:
    """Return the Supabase service used for trading balances, orders, and audit logs."""
    return trading_db

print(f"\n✅ SupabaseDB ready. Connected: user_auth={user_auth_db._connected}, trading_platform={trading_db._connected}")