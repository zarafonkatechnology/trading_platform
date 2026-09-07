"""Core modules for unified trading system"""

from .price_service import PriceService, price_service
from .risk_manager import RiskManager
from .signal_service import SignalService, signal_service
from .ewma_zscore import EWMAZScore  # ← ADD THIS

__all__ = [
    'PriceService',
    'price_service',
    'RiskManager',
    'SignalService',
    'signal_service',
    'EWMAZScore'  # ← ADD THIS

]