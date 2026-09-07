import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # ============================================================
    # SUPABASE 1: TRADING PLATFORM DATABASE
    # ============================================================
    SUPABASE_URL: str = "https://db.jcvisgkvwlzdohilimni.supabase.co"
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3MTcxODMsImV4cCI6MjEwMDI5MzE4M30.STwnGvjXLNoeXeq3uY0q783FrGaCY8ZJtB2Yyt115fI"
    SUPABASE_SERVICE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDcxNzE4MywiZXhwIjoyMTAwMjkzMTgzfQ.Fb5gcBleB_Xvv0bV0t2AF-o402nBNBz8qnFKkTUKGJk"
    
    # ============================================================
    # SUPABASE 2: USER AUTH DATABASE (for trading_cards)
    # ============================================================
    USER_AUTH_SUPABASE_URL: str = "https://unyronpybahqltrbzxas.supabase.co"
    USER_AUTH_SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ2NTQ3MjUsImV4cCI6MjEwMDIzMDcyNX0.DMIrAaIpvvWKxbuRTN3MF9UryqnXBD9R-u47B5cUEZM"
    USER_AUTH_SUPABASE_SERVICE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVueXJvbnB5YmFocWx0cmJ6eGFzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDY1NDcyNSwiZXhwIjoyMTAwMjMwNzI1fQ.57uzkxCpLLhxnK8WUTppGJgQd0a3CKu1E3pFufA_d0o"
    
    # ============================================================
    # API Settings
    # ============================================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = True
    API_WORKERS: int = 1
    
    # ============================================================
    # JWT Settings (For User Authentication)
    # ============================================================
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    
    # ============================================================
    # Database (PostgreSQL - for direct connections)
    # ============================================================
    DATABASE_URL = "postgresql://postgres:Trading_Platfor@34.120.238.99:5432/postgres"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # ============================================================
    # Trading Settings
    # ============================================================
    DEMO_BALANCE: float = 10000.0
    MAX_LEVERAGE: int = 100
    MIN_VOLUME: float = 0.01
    MAX_VOLUME: float = 10.0
    STOP_LOSS_PIPS: int = 50
    TAKE_PROFIT_PIPS: int = 100
    MAX_SLIPPAGE_PIPS: int = 5
    
    # Risk Management
    DAILY_LOSS_LIMIT: float = 100.0
    MAX_CONSECUTIVE_LOSSES: int = 3
    MAX_TRADES_PER_DAY: int = 5
    MIN_MARGIN_RATIO: float = 0.05
    MAX_POSITION_SIZE: float = 10.0
    
    # ============================================================
    # Security
    # ============================================================
    SIGNAL_SECRET: str = ""
    ENCRYPTION_KEY: str = ""
    
    # ============================================================
    # Logging
    # ============================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/trading.log"
    
    # ============================================================
    # CORS
    # ============================================================
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # ============================================================
    # Symbol Configuration
    # ============================================================
    @property
    def SYMBOLS(self) -> dict:
        return {
            "EURUSD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "GBPUSD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "USDJPY": {"pip": 0.01, "digits": 3, "point_value": 1000, "margin_per_lot": 1000},
            "USDCHF": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "AUDUSD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "USDCAD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "NZDUSD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "EURGBP": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "EURJPY": {"pip": 0.01, "digits": 3, "point_value": 1000, "margin_per_lot": 1000},
            "EURCAD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "EURNZD": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "EURCHF": {"pip": 0.0001, "digits": 5, "point_value": 10, "margin_per_lot": 1000},
            "GOLD": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "SILVER": {"pip": 0.01, "digits": 2, "point_value": 50, "margin_per_lot": 1000},
            "#NASDAQ100": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#DJ30": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#S&P500": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#RUSS2000": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#CAC40": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#DAX40": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#FTSE100": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "#NIKKEI225": {"pip": 0.1, "digits": 2, "point_value": 1, "margin_per_lot": 1000},
            "BRENT_OIL": {"pip": 0.01, "digits": 2, "point_value": 100, "margin_per_lot": 1000},
            "CrudeOIL": {"pip": 0.01, "digits": 2, "point_value": 100, "margin_per_lot": 1000},
        }
    
    # ============================================================
    # Demo Users Configuration
    # ============================================================
    @property
    def DEMO_USERS(self) -> dict:
        return {
            'client1': {'password': 'password123', 'balance': 20, 'role': 'client', 'email': 'client1@example.com'},
            'client2': {'password': 'password123', 'balance': 500, 'role': 'client', 'email': 'client2@example.com'},
            'client3': {'password': 'password123', 'balance': 10000, 'role': 'client', 'email': 'client3@example.com'},
            'client4': {'password': 'password123', 'balance': 50, 'role': 'client', 'email': 'client4@example.com'},
            'admin': {'password': 'admin123', 'balance': 0, 'role': 'admin', 'email': 'admin@example.com'}
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()