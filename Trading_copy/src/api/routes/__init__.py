# src/api/routes/__init__.py
"""
API Routes
"""

from src.api.routes.auth import router as auth_router
from src.api.routes.signals import router as signals_router
from src.api.routes.trades import router as trades_router
from src.api.routes.dashboard_bridge import router as dashboard_bridge_router
from src.api.routes.controllers import router as controllers_router
from src.api.routes.client_auth import router as client_auth_router
from src.api.routes.client_trades import router as client_trades_router
from src.api.routes.master import router as master_router
# Add master_auth router
from src.api.routes.master_auth import router as master_auth_router
from src.api.routes.cards import router as client_cards_router


# Then register it in main.py
__all__ = [
    'client_cards_router',
    'auth_router',
    'signals_router',
    'trades_router',
    'dashboard_bridge_router',
    'controllers_router',
    'client_auth_router',
    'client_trades_router',
    'master_router'
]