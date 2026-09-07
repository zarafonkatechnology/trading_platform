# tests/conftest.py
"""
Pytest configuration for trading platform tests
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import after path is set
from src.api.main import app
from src.database.models import Base
from config.settings import settings

# Test database - use SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def test_client():
    """Create a test client for FastAPI"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup test database"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def mock_mt4_data():
    """Mock MT4 data for testing"""
    return {
        "balance": 10000.00,
        "equity": 10250.50,
        "profit": 250.50,
        "margin": 500.00,
        "free_margin": 9500.00,
        "prices": {
            "EURUSD": {"price": 1.0945, "bid": 1.0943, "ask": 1.0947, "change": 0.02},
            "GBPUSD": {"price": 1.2680, "bid": 1.2678, "ask": 1.2682, "change": -0.01},
            "USDJPY": {"price": 162.426, "bid": 162.400, "ask": 162.452, "change": 0.15},
            "GOLD": {"price": 3987.55, "bid": 3987.00, "ask": 3988.10, "change": 0.05},
            "#NASDAQ100": {"price": 21500.00, "bid": 21490.00, "ask": 21510.00, "change": 0.30}
        },
        "stats": {
            "total_trades": 365,
            "win_rate": 38.4,
            "total_pnl": 909.14,
            "profit_factor": 2.28,
            "active_agents": 1
        },
        "timestamp": "2024-01-15 14:30:00"
    }

@pytest.fixture
def mock_order():
    """Mock order data"""
    return {
        "symbol": "EURUSD",
        "order_type": "BUY",
        "volume": 0.01,
        "stop_loss": 1.0900,
        "take_profit": 1.1000,
        "comment": "Test order"
    }

@pytest.fixture
def mock_user():
    """Mock user data"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }