# test_rl_coldstart.py
"""
Test script to debug RL and Cold Start functionality.
This will simulate cold start and check RL training.
"""

import sys
import os
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import needed modules
from trading_controller2 import ForexTradingController, FOREX_PAIRS

# Mock classes for testing without MT4
class MockRLEnv:
    def __init__(self, controller=None):
        self.controller = controller
        self.pairs = FOREX_PAIRS
        self.observation_space = None
        self.action_space = None
    
    def _get_observation(self):
        # Return a mock observation
        return np.zeros(50, dtype=np.float32)

class MockRLAgent:
    def __init__(self, env=None, model_path=None, load_existing=False, learning_rate=0.001):
        self.env = env
        self.model_path = model_path
        self.training = False
        self.steps = 0
        logger.info("✅ Mock RL Agent initialized")
    
    def predict(self, observation, deterministic=True):
        # Return random action: [pair_idx, trade_type (0=HOLD,1=BUY,2=SELL), size_mult]
        import random
        return np.array([random.randint(0, 11), random.randint(0, 2), 1.0], dtype=np.float32)
    
    def train(self, total_timesteps=1000):
        self.training = True
        self.steps += total_timesteps
        logger.info(f"✅ RL Agent trained for {total_timesteps} steps")
        self.training = False
    
    def save(self, path):
        logger.info(f"✅ RL Model saved to {path}")

def create_test_config() -> Dict:
    """Create test configuration with RL enabled."""
    return {
        'pairs': FOREX_PAIRS[:4],  # Use first 4 pairs for faster testing
        'min_confidence': 60,
        'cycle_interval': 10,
        'rl_enabled': True,
        'load_rl_model': False,
        'rl_model_path': 'models/rl_model_test.zip',
        'cold_start_threshold': 10,  # Smaller for testing
        'cold_start_min_win_rate': 0.4,
        'cold_start_skip_real': True,
        'enable_entry_confirmation': False,  # Disable M5 check for testing
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

def create_mock_market_data(pair: str, price: float) -> Dict:
    """Create mock market data for testing."""
    return {
        pair: price,
        'current_price': price,
        'price': price,
        'pair': pair,
        'EURUSD': 1.14 if pair != 'EURUSD' else price,
        'GBPUSD': 1.34 if pair != 'GBPUSD' else price,
        'USDJPY': 162.0 if pair != 'USDJPY' else price,
        'AUDUSD': 0.69 if pair != 'AUDUSD' else price,
        'engine_state': {
            'engine_speed': 0.3,
            'engine_direction': 'FORWARD',
            'engine_health': 95.0
        },
        'candles': [
            {'high': price + 0.002, 'low': price - 0.002, 'close': price + 0.001},
            {'high': price + 0.003, 'low': price - 0.001, 'close': price + 0.002},
            {'high': price + 0.001, 'low': price - 0.003, 'close': price - 0.001},
            {'high': price + 0.002, 'low': price - 0.002, 'close': price + 0.0015},
        ] * 15,  # 60 candles
        'ecb_policy': 'HAWKISH',
        'fed_policy': 'DOVISH',
        'eurusd_rate_diff': 0.75,
        'timestamp': datetime.now().isoformat()
    }

def test_cold_start_state():
    """Test cold start state loading and saving."""
    print("\n" + "="*60)
    print("🧪 TEST 1: COLD START STATE")
    print("="*60)
    
    config = create_test_config()
    controller = ForexTradingController(config)
    
    # Check initial state
    print(f"\n📊 Initial Cold Start State:")
    print(f"   Active: {controller.cold_start_active}")
    print(f"   Samples: {len(controller.cold_start_samples)}")
    print(f"   Wins: {controller.cold_start_wins}")
    print(f"   Losses: {controller.cold_start_losses}")
    print(f"   Threshold: {controller.cold_start_threshold}")
    print(f"   Min Win Rate: {controller.cold_start_min_win_rate}")
    
    # Simulate some trades
    print(f"\n🧪 Simulating 5 cold start trades...")
    for i in range(5):
        signal = 'BUY' if i % 2 == 0 else 'SELL'
        pair = FOREX_PAIRS[i % len(FOREX_PAIRS)]
        price = 1.14 + (i * 0.001)
        confidence = 75 + (i * 5)
        
        controller._simulate_trade(pair, signal, confidence, price)
        print(f"   Trade {i+1}: {pair} {signal} @ {price:.5f} (conf: {confidence}%)")
    
    print(f"\n📊 After 5 simulations:")
    print(f"   Active: {controller.cold_start_active}")
    print(f"   Samples: {len(controller.cold_start_samples)}")
    print(f"   Wins: {controller.cold_start_wins}")
    print(f"   Losses: {controller.cold_start_losses}")
    
    # Save state
    controller._save_cold_start_state()
    print(f"\n💾 Cold start state saved")
    
    # Check if file exists
    if os.path.exists('cold_start_state.json'):
        print(f"   ✅ File exists")
        with open('cold_start_state.json', 'r') as f:
            data = json.load(f)
        print(f"   Samples in file: {len(data.get('samples', []))}")
    else:
        print(f"   ❌ File not found")
    
    return controller

def test_rl_data_collection():
    """Test RL data collection during cold start."""
    print("\n" + "="*60)
    print("🧪 TEST 2: RL DATA COLLECTION")
    print("="*60)
    
    config = create_test_config()
    controller = ForexTradingController(config)
    
    # Add mock RL agent
    controller.rl_enabled = True
    controller.rl_agent = MockRLAgent()
    controller.rl_env = MockRLEnv(controller)
    
    print(f"\n📊 RL Configuration:")
    print(f"   RL Enabled: {controller.rl_enabled}")
    print(f"   RL Agent: {controller.rl_agent is not None}")
    print(f"   RL Env: {controller.rl_env is not None}")
    print(f"   Replay Buffer Size: {len(controller.replay_buffer)}")
    print(f"   Train Batch Size: {controller.rl_train_batch_size}")
    print(f"   Train Every: {controller.rl_train_every} simulations")
    
    # Simulate trades to collect RL data
    print(f"\n🧪 Simulating 15 trades to collect RL data...")
    for i in range(15):
        signal = 'BUY' if i % 2 == 0 else 'SELL'
        pair = FOREX_PAIRS[i % len(FOREX_PAIRS)]
        price = 1.14 + (i * 0.001)
        confidence = 75 + (i * 5)
        
        controller._simulate_trade(pair, signal, confidence, price)
        
        if (i + 1) % 5 == 0:
            print(f"   After {i+1} simulations:")
            print(f"      Samples: {len(controller.cold_start_samples)}")
            print(f"      Replay Buffer: {len(controller.replay_buffer)}")
    
    print(f"\n📊 Final RL Data:")
    print(f"   Cold Start Samples: {len(controller.cold_start_samples)}")
    print(f"   Replay Buffer: {len(controller.replay_buffer)}")
    print(f"   RL Training Data: {len(controller.rl_training_data) if hasattr(controller, 'rl_training_data') else 0}")
    
    # Check if RL training was triggered
    if len(controller.replay_buffer) >= controller.rl_train_batch_size:
        print(f"\n✅ RL training triggered")
        print(f"   Training Buffer: {len(controller.rl_training_buffer) if hasattr(controller, 'rl_training_buffer') else 0}")
    else:
        print(f"\n⏸️ RL training not triggered (need {controller.rl_train_batch_size} transitions)")
    
    return controller

def test_rl_training():
    """Test actual RL training."""
    print("\n" + "="*60)
    print("🧪 TEST 3: RL TRAINING")
    print("="*60)
    
    config = create_test_config()
    controller = ForexTradingController(config)
    
    # Add mock RL agent
    controller.rl_enabled = True
    controller.rl_agent = MockRLAgent()
    controller.rl_env = MockRLEnv(controller)
    
    # Collect data
    print(f"\n🧪 Collecting 25 RL transitions...")
    for i in range(25):
        signal = 'BUY' if i % 2 == 0 else 'SELL'
        pair = FOREX_PAIRS[i % len(FOREX_PAIRS)]
        price = 1.14 + (i * 0.001)
        confidence = 75 + (i * 5)
        
        controller._simulate_trade(pair, signal, confidence, price)
    
    print(f"\n📊 Data collected:")
    print(f"   Replay Buffer: {len(controller.replay_buffer)}")
    print(f"   Cold Start Samples: {len(controller.cold_start_samples)}")
    
    # Try to train
    print(f"\n🧪 Attempting RL training...")
    controller._train_rl_from_replay()
    
    # Check training status
    print(f"\n📊 Training Status:")
    print(f"   RL Agent Training: {controller.rl_agent.training if hasattr(controller.rl_agent, 'training') else 'Unknown'}")
    print(f"   Training Buffer: {len(controller.rl_training_buffer) if hasattr(controller, 'rl_training_buffer') else 0}")
    print(f"   Training Data: {len(controller.rl_training_data) if hasattr(controller, 'rl_training_data') else 0}")
    
    # Try to train with collected data
    if hasattr(controller, 'rl_training_data') and controller.rl_training_data:
        print(f"\n🧪 Training RL with collected data...")
        controller._train_rl_with_collected_data()
        controller.rl_agent.save('models/rl_model_test_trained.zip')
        print(f"✅ RL model saved")
    
    return controller

def test_full_cycle():
    """Test full cold start cycle with RL."""
    print("\n" + "="*60)
    print("🧪 TEST 4: FULL COLD START CYCLE")
    print("="*60)
    
    config = create_test_config()
    config['cold_start_threshold'] = 15  # Smaller for testing
    
    controller = ForexTradingController(config)
    
    # Add mock RL agent
    controller.rl_enabled = True
    controller.rl_agent = MockRLAgent()
    controller.rl_env = MockRLEnv(controller)
    
    print(f"\n📊 Starting cold start (threshold: {controller.cold_start_threshold})")
    
    # Simulate trades until cold start completes
    max_cycles = 30
    for cycle in range(max_cycles):
        # Simulate trades for each pair
        for pair in FOREX_PAIRS[:4]:
            price = 1.14 + (cycle * 0.001) + (FOREX_PAIRS.index(pair) * 0.005)
            signal = 'BUY' if (cycle + FOREX_PAIRS.index(pair)) % 2 == 0 else 'SELL'
            confidence = 70 + (cycle % 20) + 10
            
            # Create market data
            market_data = create_mock_market_data(pair, price)
            
            # Process cycle
            result = controller.process_cycle(market_data)
            
            # Check if cold start complete
            if not controller.cold_start_active:
                print(f"\n✅ Cold start complete after {cycle + 1} cycles!")
                break
        
        if not controller.cold_start_active:
            break
        
        # Print progress
        if (cycle + 1) % 5 == 0:
            print(f"   Cycle {cycle + 1}: Samples {len(controller.cold_start_samples)}/{controller.cold_start_threshold}")
    
    # Final status
    print(f"\n📊 Final Status:")
    print(f"   Cold Start Active: {controller.cold_start_active}")
    print(f"   Total Samples: {len(controller.cold_start_samples)}")
    print(f"   Win Rate: {controller.cold_start_wins / len(controller.cold_start_samples) * 100:.1f}%")
    print(f"   Replay Buffer: {len(controller.replay_buffer)}")
    print(f"   RL Training Data: {len(controller.rl_training_data) if hasattr(controller, 'rl_training_data') else 0}")
    
    return controller

def check_rl_logs():
    """Check if RL logs are appearing."""
    print("\n" + "="*60)
    print("🧪 TEST 5: RL LOGS CHECK")
    print("="*60)
    
    print("\n📊 What to look for in logs:")
    print("   ✅ '🤖 RL: Collected X transitions' - Shows RL data collection")
    print("   ✅ '🤖 RL: Training on X transitions' - Shows RL training trigger")
    print("   ✅ '💾 RL: Saved X transitions' - Shows RL data saved")
    print("   ✅ '✅ RL: Training complete' - Shows RL training completed")
    print("\nIf you see these messages, RL is working correctly!")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🚀 STARTING RL & COLD START TESTS")
    print("="*60)
    
    # Clean up old test files
    for file in ['cold_start_state.json', 'rl_training_data.pkl', 'models/rl_model_test_trained.zip']:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ Removed: {file}")
    
    print()
    
    # Run tests
    test_cold_start_state()
    test_rl_data_collection()
    test_rl_training()
    test_full_cycle()
    check_rl_logs()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("="*60)
    print("\n📝 Summary:")
    print("   • Check the logs above for RL and Cold Start messages")
    print("   • The '🤖 RL:' messages show RL is working")
    print("   • The '❄️ Cold start:' messages show Cold Start is working")
    print("   • If you don't see RL messages, check rl_enabled=True")

if __name__ == "__main__":
    main()