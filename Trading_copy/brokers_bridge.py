# brokers_bridge.py - Bridge for brokers module
"""
Bridge for brokers module with fallbacks
"""

import sys
from pathlib import Path

print("🔧 Loading brokers_bridge.py...")

# ============================================================
# FIND BROKERS DIRECTORY
# ============================================================

def find_brokers_directory():
    """Find the brokers directory in various locations"""
    possible_paths = [
        Path(__file__).parent / "brokers",
        Path(__file__).parent / "forex_engine" / "brokers",
        Path(__file__).parent.parent / "forex_engine" / "brokers",
        Path(__file__).parent / "backend" / "brokers",
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ Found brokers at: {path}")
            return path
    
    print("⚠️ Could not find brokers directory")
    return None

# Add brokers to path
brokers_path = find_brokers_directory()
if brokers_path:
    sys.path.insert(0, str(brokers_path.parent))
    sys.path.insert(0, str(brokers_path))

# ============================================================
# TRY TO IMPORT REAL BROKERS
# ============================================================

try:
    from brokers import BROKER_MAP, BaseBroker, BrokerManager
    print("✅ Brokers imported successfully")
    BROKERS_LOADED = True
except ImportError as e:
    print(f"⚠️ Could not import brokers: {e}")
    BROKERS_LOADED = False

if not BROKERS_LOADED:
    # ============================================================
    # FALLBACK BROKER CLASSES
    # ============================================================
    
    class BaseBroker:
        """Fallback Base Broker"""
        def __init__(self, pair, config=None, engine=None):
            self.pair = pair
            self.config = config or {}
            self.engine = engine
            self.current_price = 0
            self.z_score = 0
            self.price_history = []
            self.close_history = []
            self.spread_history = []
            print(f"   📊 BaseBroker (fallback): {pair}")
        
        def analyze(self, market_data):
            return {
                'signal': 'HOLD',
                'confidence': 50,
                'z_score': 0,
                'reasoning': 'Fallback broker'
            }
        
        def get_status(self):
            return {
                'pair': self.pair,
                'price': self.current_price,
                'z_score': self.z_score
            }
    
    class BrokerManager:
        """Fallback Broker Manager"""
        def __init__(self, engine=None, monte_carlo=None, rl_agent=None):
            self.engine = engine
            self.monte_carlo = monte_carlo
            self.rl_agent = rl_agent
            self.brokers = {}
            print("   📊 BrokerManager (fallback) ready")
        
        def register_brokers(self, pairs, broker_map):
            """Register brokers for all pairs"""
            for pair in pairs:
                config = {}
                if pair in broker_map:
                    config = broker_map[pair]
                self.brokers[pair] = BaseBroker(pair, config, self.engine)
                print(f"   ✅ Registered broker: {pair}")
        
        def get_decision(self, market_data):
            """Get decisions from all brokers"""
            decisions = {}
            for pair, broker in self.brokers.items():
                result = broker.analyze(market_data)
                decisions[pair] = {
                    'signal': result.get('signal', 'HOLD'),
                    'confidence': result.get('confidence', 50),
                    'z_score': result.get('z_score', 0),
                    'position_size': 1.0,
                    'sl': 0,
                    'tp': 0,
                    'broker_result': result
                }
            return decisions
        
        def get_status(self):
            return {
                'broker_count': len(self.brokers),
                'brokers': list(self.brokers.keys())
            }
    
    # Create empty BROKER_MAP
    BROKER_MAP = {}
    
    print("✅ Fallback brokers created")

# Export everything
__all__ = [
    'BROKER_MAP',
    'BaseBroker',
    'BrokerManager'
]

print("✅ brokers_bridge.py ready")