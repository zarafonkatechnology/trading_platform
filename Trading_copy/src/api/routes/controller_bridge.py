# src/services/controller_bridge.py
"""
Bridge between trading_controller2.py and the FastAPI
"""

import sys
import os
from pathlib import Path

# Add path to controller
controller_path = Path(__file__).parent.parent.parent.parent / "trading_copy"
sys.path.insert(0, str(controller_path))

from trading_controller2 import ForexTradingController, FOREX_PAIRS
from config.settings import settings

class ControllerBridge:
    """Bridge between trading controller and API"""
    
    def __init__(self):
        self.controller = None
        self.is_initialized = False
        
    def initialize(self):
        """Initialize the trading controller"""
        if not self.is_initialized:
            config = {
                'pairs': FOREX_PAIRS,
                'min_confidence': 60,
                'cycle_interval': 10,
                'rl_enabled': True,
                'cold_start_threshold': 50,
                'cold_start_min_win_rate': 0.0,
                'enable_entry_confirmation': True,
                'engine_config': {
                    'factor_weights': {
                        'interest_rate_diff': 0.35,
                        'yield_curve_slope': 0.25,
                        'carry_trade_flow': 0.15,
                        'positioning_sentiment': 0.15,
                        'central_bank_actions': 0.10,
                    }
                }
            }
            
            self.controller = ForexTradingController(config)
            self.controller.start()
            self.is_initialized = True
            print("✅ Controller Bridge initialized")
        
        return self.controller
    
    def get_status(self):
        """Get controller status"""
        if not self.is_initialized:
            self.initialize()
        return self.controller.get_status()
    
    def process_cycle(self):
        """Process one trading cycle"""
        if not self.is_initialized:
            self.initialize()
        market_data = self.controller.build_market_data()
        return self.controller.process_cycle(market_data)
    
    def get_prices(self):
        """Get current prices"""
        if not self.is_initialized:
            self.initialize()
        return self.controller.get_all_mt4_prices()
    
    def execute_trade(self, symbol: str, order_type: str, volume: float,
                     stop_loss: float = 0, take_profit: float = 0):
        """Execute a trade directly"""
        if not self.is_initialized:
            self.initialize()
        
        price = self.controller.get_price(symbol)
        if price <= 0:
            return {'success': False, 'error': f'No price for {symbol}'}
        
        # Use the controller's send_real_order method
        result = self.controller.send_real_order(
            symbol=symbol,
            action=order_type,
            price=price,
            sl=stop_loss,
            tp=take_profit,
            volume=volume
        )
        return result
    
    def get_positions(self):
        """Get all positions"""
        if not self.is_initialized:
            self.initialize()
        return self.controller.execution_engine.positions

# Global instance
controller_bridge = ControllerBridge()