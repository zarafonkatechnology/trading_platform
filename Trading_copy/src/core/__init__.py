# src/core/__init__.py
"""
Core trading components
"""

from src.core.signal_generator import (
    SignalGenerator, 
    TradeSignal, 
    SignalType, 
    SignalStrength
)
from src.core.trading_engine import TradingEngine, Order, OrderType, OrderStatus, Position
from src.core.risk_manager import RiskManager, RiskMetrics
from src.core.copy_engine import CopyEngine, CopyClient, CopyTrade

__all__ = [
    'SignalGenerator',
    'TradeSignal',
    'SignalType',
    'SignalStrength',
    'TradingEngine',
    'Order',
    'OrderType',
    'OrderStatus',
    'Position',
    'RiskManager',
    'RiskMetrics',
    'CopyEngine',
    'CopyClient',
    'CopyTrade'
]