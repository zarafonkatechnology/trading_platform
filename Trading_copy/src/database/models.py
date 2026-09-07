# src/database/models.py - Complete working version

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "admin"
    TRADER = "trader"
    CLIENT = "client"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone = Column(String(20))
    role = Column(Enum(UserRole), default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    trading_balance = Column(Float, default=0.0)
    trading_equity = Column(Float, default=0.0)
    trading_profit = Column(Float, default=0.0)
    max_volume = Column(Float, default=0.01)
    max_positions = Column(Integer, default=2)
    leverage = Column(Integer, default=10)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    positions = relationship("Position", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    login_time = Column(DateTime, server_default=func.now())
    logout_time = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(50), unique=True, index=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    volume = Column(Float, nullable=False)
    strength = Column(String(10))
    source = Column(String(50))
    confidence = Column(Float)
    description = Column(Text)
    timestamp = Column(DateTime, server_default=func.now())
    expiry_time = Column(DateTime)
    is_executed = Column(Boolean, default=False)
    
    # Relationships
    trades = relationship("Trade", back_populates="signal")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    signal_id = Column(Integer, ForeignKey("signals.id"))
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(10), nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    pnl = Column(Float, default=0.0)
    fee = Column(Float, default=0.0)
    performance_fee = Column(Float, default=0.0)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    signal = relationship("Signal", back_populates="trades")

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(10), nullable=False)
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    current_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    profit = Column(Float, default=0.0)
    fee_at_entry = Column(Float, default=0.0)
    is_open = Column(Boolean, default=True)
    open_time = Column(DateTime, server_default=func.now())
    close_time = Column(DateTime)
    mt4_ticket = Column(Integer)
    
    # Relationships
    user = relationship("User", back_populates="positions")

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mt4_account_id = Column(String(50), unique=True)
    mt4_account_password = Column(String(255))
    mt4_server = Column(String(100))
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    free_margin = Column(Float, default=0.0)
    risk_per_trade = Column(Float, default=0.02)
    max_volume = Column(Float, default=10.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User")

class TradingConfig(Base):
    __tablename__ = "trading_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    max_position_size = Column(Float, default=10.0)
    daily_loss_limit = Column(Float, default=100.0)
    max_trades_per_day = Column(Integer, default=5)
    stop_loss_pips = Column(Integer, default=50)
    take_profit_pips = Column(Integer, default=100)
    copy_trading_enabled = Column(Boolean, default=True)
    auto_trading_enabled = Column(Boolean, default=False)
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class PrepaidCard(Base):
    __tablename__ = "prepaid_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    card_token = Column(String(255), unique=True, index=True, nullable=False)
    rfid_card_number = Column(String(50))
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="active")
    used_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    type = Column(String(20), nullable=False)  # DEPOSIT, WITHDRAW, FEE, TRADE
    amount = Column(Float, nullable=False)
    description = Column(Text)
    balance_after = Column(Float)
    reference_id = Column(String(100))
    status = Column(String(20), default="COMPLETED")
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User")