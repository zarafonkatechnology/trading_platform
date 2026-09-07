# C:\trading_platform\forex_engine\brokers\__init__.py

from .base_broker import BaseBroker
from .eurusd_broker import EURUSDBroker
from .eurgbp_broker import EURGBPBroker
from .gbpusd_broker import GBPUSDBroker
from .usdjpy_broker import USDJPYBroker
from .usdchf_broker import USDCHFBroker
from .audusd_broker import AUDUSDBroker
from .usdcad_broker import USDCADBroker  # ADD THIS
from .nzdusd_broker import NZDUSDBroker
from .eurjpy_broker import EURJPYBroker
from .eurcad_broker import EURCADBroker
from .eurnzd_broker import EURNZDBroker
from .eurchf_broker import EURCHFBroker
from .broker_manager import BrokerManager

BROKER_MAP = {
    'EURUSD': EURUSDBroker,
    'EURGBP': EURGBPBroker,
    'GBPUSD': GBPUSDBroker,
    'USDJPY': USDJPYBroker,
    'USDCHF': USDCHFBroker,
    'AUDUSD': AUDUSDBroker,
    'USDCAD': USDCADBroker,  # ADD THIS
    'NZDUSD': NZDUSDBroker,
    'EURJPY': EURJPYBroker,
    'EURCAD': EURCADBroker,
    'EURNZD': EURNZDBroker,
    'EURCHF': EURCHFBroker,
}

__all__ = [
    'BaseBroker',
    'EURUSDBroker',
    'EURGBPBroker',
    'GBPUSDBroker',
    'USDJPYBroker',
    'USDCHFBroker',
    'AUDUSDBroker',
    'USDCADBroker',
    'NZDUSDBroker',
    'EURJPYBroker',
    'EURCADBroker',
    'EURNZDBroker',
    'EURCHFBroker',
    'BrokerManager',
    'BROKER_MAP',
]