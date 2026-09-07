# C:\trading_platform\forex_engine\brokers\test.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
import random

# Import brokers - using simplified versions
from eurusd_broker import EURUSDBroker
from eurgbp_broker import EURGBPBroker
from gbpusd_broker import GBPUSDBroker
from usdjpy_broker import USDJPYBroker
from core.broker_manager import BrokerManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockEngine:
    def __init__(self):
        self.engine_speed = 0.3
        self.engine_direction = 'FORWARD'
    
    def get_status(self):
        return {'engine_speed': 0.3, 'engine_direction': 'FORWARD', 'engine_health': 95.0}
    
    def get_gear_prediction(self, pair, gear_ratio=1.0):
        return {'predicted_direction': 'UP', 'confidence': 70.0}


class MockMonteCarlo:
    def simulate_entry(self, current_price, direction, volatility=0.005):
        return {'entry_confidence': random.uniform(55, 85)}


def create_test_data():
    """Create test data with candles."""
    base_price = 1.14350
    candles = []
    
    for i in range(60):
        if i < 30:
            change = 0.0001 + (i * 0.000005)
        else:
            change = -0.0001 - ((i - 30) * 0.000005)
        
        price = base_price + change
        price = max(1.0, price)
        
        candles.append({
            'high': price + 0.0005,
            'low': price - 0.0005,
            'open': price - 0.0002,
            'close': price,
            'volume': 1000 + i * 10,
            'time': datetime.now().timestamp() - (60 - i) * 900
        })
    
    return {
        'EURUSD': base_price + 0.0015,
        'GBPUSD': 1.34180,
        'USDJPY': 161.350,
        'EURGBP': 0.85200,
        'current_price': base_price + 0.0015,
        'price': base_price + 0.0015,
        'pair': 'EURUSD',
        'candles': candles,
        'engine_state': {'engine_speed': 0.3, 'engine_direction': 'FORWARD'},
        'ecb_policy': 'HAWKISH',
        'fed_policy': 'DOVISH',
        'eurusd_rate_diff': 0.75,
        'us_10y_yield': 4.52,
        'jp_10y_yield': 0.02,
        'brexit_sentiment': -0.2,
        'gbpusd_volatility': 0.012,
        'timestamp': datetime.now().isoformat()
    }


def build_broker_history(broker, market_data, iterations=20):
    """Build history for a broker by calling analyze multiple times."""
    for i in range(iterations):
        variation = (i - iterations/2) * 0.0005
        market_data['price'] = market_data['EURUSD'] + variation
        market_data['current_price'] = market_data['price']
        
        # Update candles
        candles = []
        base_price = market_data['price']
        for j in range(20):
            price = base_price + (j - 10) * 0.0002 + (i % 5) * 0.0001
            candles.append({
                'high': price + 0.0005,
                'low': price - 0.0005,
                'open': price - 0.0002,
                'close': price,
                'volume': 1000 + j * 10,
                'time': datetime.now().timestamp() - (20 - j) * 900
            })
        market_data['candles'] = candles
        
        broker.analyze(market_data)
    
    return broker


def main():
    print("\n" + "="*60)
    print("📊 BROKER SYSTEM TEST")
    print("="*60)
    
    # Create test data
    market_data = create_test_data()
    
    # Test EURUSD Broker
    print("\n🔍 Testing EURUSD Broker:")
    eurusd = EURUSDBroker()
    build_broker_history(eurusd, market_data, iterations=30)
    
    result = eurusd.analyze(market_data)
    print(f"   Signal: {result.get('vote', 'HOLD')}")
    print(f"   Confidence: {result.get('confidence', 0):.1f}%")
    print(f"   Z-Score: {eurusd.z_score:.3f}")
    print(f"   Persistence: {eurusd.persistence}")
    print(f"   Samples: {eurusd.samples}")
    
    # Test all brokers
    print("\n🔍 Testing All Brokers:")
    brokers = {
        'EURUSD': EURUSDBroker(),
        'GBPUSD': GBPUSDBroker(),
        'USDJPY': USDJPYBroker(),
        'EURGBP': EURGBPBroker(),
    }
    
    for pair, broker in brokers.items():
        build_broker_history(broker, market_data, iterations=20)
        result = broker.analyze(market_data)
        signal = result.get('vote', 'HOLD')
        confidence = result.get('confidence', 0)
        z_score = broker.z_score
        print(f"   {pair}: {signal} ({confidence:.1f}%) | Z={z_score:.3f}")
    
    # Test Broker Manager
    print("\n🔍 Testing Broker Manager:")
    engine = MockEngine()
    mc = MockMonteCarlo()
    manager = BrokerManager(engine, mc)
    
    for pair, broker in brokers.items():
        manager.brokers[pair] = broker
    
    decisions = manager.get_decision(market_data)
    
    print("\n📈 Final Decisions:")
    for pair, decision in decisions.items():
        if decision.get('signal') != 'HOLD':
            print(f"   ✅ {pair}: {decision['signal']} ({decision['confidence']:.1f}%)")
            if 'sl' in decision and 'tp' in decision:
                print(f"      SL: {decision['sl']:.5f} | TP: {decision['tp']:.5f}")
            print(f"      Position Size: {decision.get('position_size', 0)}")
        else:
            print(f"   ⏸️ {pair}: HOLD (Z={manager.brokers[pair].z_score:.3f})")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()