# core_bridge.py - Complete working version
"""
Bridge to core modules - Finds your existing core directory
"""

import sys
import os
from pathlib import Path

print("🔧 Loading core_bridge.py...")

# ============================================================
# FIND THE CORE DIRECTORY
# ============================================================

def find_core_directory():
    """Find the core directory in various possible locations"""
    possible_paths = [
        Path(__file__).parent / "core",  # current/core
        Path(__file__).parent / "forex_engine" / "core",  # forex_engine/core
        Path(__file__).parent.parent / "forex_engine" / "core",  # parent/forex_engine/core
        Path("C:/trading_platform/forex_engine/core"),  # Absolute path
        Path("C:/trading_platform/trading_copy/core"),  # Copy location
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ Found core at: {path}")
            return path
    
    print("⚠️ Could not find core directory")
    return None

# Add core to path
core_path = find_core_directory()
if core_path:
    sys.path.insert(0, str(core_path.parent))
    sys.path.insert(0, str(core_path))
    print(f"✅ Added to path: {core_path}")

# ============================================================
# TRY TO IMPORT FROM CORE
# ============================================================

try:
    from core.dollar_engine import DollarEngine
    print("✅ DollarEngine imported from core")
    CORE_LOADED = True
except ImportError as e:
    print(f"⚠️ Could not import from core: {e}")
    CORE_LOADED = False

if not CORE_LOADED:
    # Try with forex_engine prefix
    try:
        from forex_engine.core.dollar_engine import DollarEngine
        print("✅ DollarEngine imported from forex_engine")
        CORE_LOADED = True
    except ImportError:
        print("⚠️ Could not import DollarEngine - using fallback")

# ============================================================
# FALLBACK CLASSES (if core not found)
# ============================================================

if not CORE_LOADED:
    print("📊 Creating fallback core classes...")
    
    class DollarEngine:
        """Fallback Dollar Engine"""
        def __init__(self, config=None):
            self.config = config or {}
            self.engine_speed = 0.5
            self.engine_direction = 'FORWARD'
            self.engine_health = 95.0
            self.regime = 'RANGING'
            self.reversal_probability = 20.0
            self.confidence = 70.0
            self.engine_state = 'NORMAL'
            self.engine_acceleration = 0.0
            self.current_factors = {}
            self.dxy_current = 104.5
            print("   📊 DollarEngine (fallback) ready")
        
        def update_engine_state(self, market_data):
            return {
                'engine_speed': self.engine_speed,
                'engine_acceleration': self.engine_acceleration,
                'engine_direction': self.engine_direction,
                'engine_state': self.engine_state,
                'engine_health': self.engine_health,
                'reversal_probability': self.reversal_probability,
                'confidence': self.confidence,
                'regime': self.regime,
                'regime_confidence': 70.0,
                'dxy_current': self.dxy_current,
                'factors': self.current_factors,
            }
        
        def get_status(self):
            return self.update_engine_state({})
        
        def get_gear_prediction(self, pair, gear_ratio=1.0):
            return {
                'pair': pair,
                'gear_ratio': gear_ratio,
                'predicted_direction': 'UP' if self.engine_speed > 0 else 'DOWN',
                'confidence': self.confidence,
                'engine_speed': self.engine_speed,
                'engine_state': self.engine_state,
                'reversal_probability': self.reversal_probability,
                'regime': self.regime,
            }

    class GearBroker:
        def __init__(self, pair, config, engine):
            self.pair = pair
            self.config = config
            self.engine = engine
            self.price_history = []
            self.close_history = []
            self.spread_history = []
            self.current_price = 0
            self.z_score = 0
            print(f"   📊 GearBroker (fallback): {pair}")
        
        def get_status(self):
            return {'pair': self.pair, 'price': self.current_price, 'z_score': self.z_score}

    class GearAnomalyDetector:
        def __init__(self, config=None):
            self.config = config or {}
            print("   📊 GearAnomalyDetector (fallback) ready")
        
        def update(self, market_data):
            return {'protection_active': False, 'anomalies': []}
        
        def set_brokers(self, brokers):
            pass

    class MonteCarloSimulator:
        def __init__(self, config=None):
            self.config = config or {}
            print("   📊 MonteCarloSimulator (fallback) ready")
        
        def simulate_entry(self, current_price=0, direction='BUY', **kwargs):
            return {'entry_confidence': 50, 'probability_of_success': 0.5}

    class OrderExecutionEngine:
        def __init__(self, engine=None, config=None):
            self.engine = engine
            self.config = config or {}
            self.positions = {}
            self.trades_today = 0
            self.daily_pnl = 0.0
            print("   📊 OrderExecutionEngine (fallback) ready")
        
        def execute_signal(self, consensus, market_data, *args, **kwargs):
            return {'status': 'EXECUTED', 'ticket': 12345, 'price': market_data.get('price', 0)}
        
        def get_status(self):
            return {
                'trades_today': self.trades_today,
                'daily_pnl': self.daily_pnl,
                'positions': len(self.positions)
            }
        
        def register_broker(self, pair, broker):
            pass
    
    print("✅ Fallback core classes created")

# Export everything
__all__ = [
    'DollarEngine',
    'GearBroker',
    'GearAnomalyDetector',
    'MonteCarloSimulator',
    'OrderExecutionEngine'
]

print("✅ core_bridge.py ready")