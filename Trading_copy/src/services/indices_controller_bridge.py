# src/services/indices_controller_bridge.py
"""
Bridge between indices trading_controller.py and FastAPI
"""

import sys
import os
from pathlib import Path

# Add path to indices controller
controller_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(controller_path))

try:
    from trading_controller import AITradingController, SYMBOL_CONFIG, SYMBOLS_TO_TRADE
    INDICES_AVAILABLE = True
    print("✅ Indices Controller loaded")
except ImportError as e:
    INDICES_AVAILABLE = False
    print(f"⚠️ Indices Controller not available: {e}")

class IndicesControllerBridge:
    """Bridge between indices controller and API"""
    
    def __init__(self):
        self.controller = None
        self.is_initialized = False
        
    def initialize(self):
        """Initialize the indices controller"""
        if not self.is_initialized and INDICES_AVAILABLE:
            self.controller = AITradingController()
            self.controller.start()
            self.is_initialized = True
            print("✅ Indices Controller Bridge initialized")
        return self.controller
    
    def get_status(self):
        if not self.is_initialized:
            self.initialize()
        return self.controller.get_status() if self.controller else {}
    
    def get_prices(self):
        if not self.is_initialized:
            self.initialize()
        return self.controller.get_all_mt4_prices() if self.controller else {}
    
    def analyze_symbol(self, symbol: str):
        if not self.is_initialized:
            self.initialize()
        return self.controller.analyze_market(symbol) if self.controller else {}
    
    def get_symbols(self):
        return SYMBOLS_TO_TRADE if INDICES_AVAILABLE else []

# Global instance
indices_bridge = IndicesControllerBridge()