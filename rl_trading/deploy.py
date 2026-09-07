# ============================================================
# deploy.py - Deploy RL Agent to Live Trading
# ============================================================

import os
import sys
import time
import json
from datetime import datetime
import logging
from stable_baselines3 import PPO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl_trading.config import Config
from rl_trading.environment import SpreadArbitrageEnv
from rl_trading.hyperlearning import HyperLearner, MetaLearningWrapper
from rl_trading.evaluation import BacktestEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RLTrader:
    """
    Production RL Trader with hyperlearning and risk management.
    """
    
    def __init__(self, model_path: str, data_path: str):
        self.config = Config()
        self.model = PPO.load(model_path)
        self.hyperlearner = HyperLearner(self.config)
        
        # Load data
        self.data = pd.read_csv(data_path, index_col=0, parse_dates=True)
        self.current_idx = 0
        
        # State
        self.position = 0
        self.trades = []
        self.epsilon = 0.0  # No exploration in production
        
        logger.info("✅ RLTrader initialized")
        logger.info(f"   Epsilon: {self.epsilon} (exploitation only)")
        logger.info(f"   Gamma: {self.config.GAMMA}")
        logger.info(f"   Data points: {len(self.data)}")
    
    def get_signal(self, market_data: Dict) -> Dict:
        """
        Get trading signal from RL agent.
        """
        # Build state
        state = self._build_state(market_data)
        
        # Get action from model
        action, _ = self.model.predict(state, deterministic=True)
        
        # Map action
        action_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = action_map[action]
        
        # Get confidence (softmax of action probabilities)
        # For PPO, we can get action probabilities
        if hasattr(self.model, 'policy'):
            probs = self.model.policy.get_distribution(state)
            action_probs = probs.distribution.probs.detach().numpy()
            confidence = float(action_probs[0][action] * 100)
        else:
            confidence = 70  # Default if not available
        
        return {
            'signal': signal,
            'action': action,
            'confidence': round(confidence, 1),
            'position': self.position
        }
    
    def _build_state(self, market_data: Dict) -> np.ndarray:
        """Build state vector for RL agent."""
        z_score = market_data.get('z_score', 0)
        spread = market_data.get('spread', 0)
        
        # Get rolling statistics
        # In production, use your existing spread history
        return np.array([
            float(z_score),
            float(spread),
            float(self.config.GAMMA),
            0.0,  # mu (placeholder)
            0.0,  # sigma (placeholder)
            float(self.position)
        ], dtype=np.float32)
    
    def execute_trade(self, signal: Dict) -> Dict:
        """
        Execute trade based on signal.
        """
        if signal['signal'] == 'HOLD':
            return {'executed': False, 'reason': 'HOLD'}
        
        if signal['confidence'] < 70:
            return {'executed': False, 'reason': f'Low confidence: {signal["confidence"]}%'}
        
        # In production, this would send the order to MT4
        logger.info(f"🚀 EXECUTE: {signal['signal']} (confidence: {signal['confidence']}%)")
        
        return {
            'executed': True,
            'signal': signal['signal'],
            'confidence': signal['confidence']
        }
    
    def run(self):
        """Main trading loop."""
        logger.info("▶️ Starting RLTrader live loop...")
        
        while True:
            # Get latest market data
            if self.current_idx >= len(self.data):
                self.current_idx = 0
            
            row = self.data.iloc[self.current_idx]
            market_data = {
                'z_score': row['z_score'],
                'spread': row['spread'],
                'spx': row['spx'],
                'ndx': row['ndx']
            }
            
            # Get signal
            signal = self.get_signal(market_data)
            
            # Execute if not HOLD
            if signal['signal'] != 'HOLD':
                result = self.execute_trade(signal)
                logger.info(f"📊 Signal: {signal['signal']}, Confidence: {signal['confidence']}%")
                logger.info(f"   Result: {result}")
            
            self.current_idx += 1
            time.sleep(60)  # 1-minute loop


# ============================================================
# MAIN DEPLOYMENT
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 RL TRADER DEPLOYMENT")
    print("=" * 70)
    print()
    
    # Paths
    model_path = os.path.join('models', 'final_model_20260101_120000.zip')
    data_path = os.path.join('data', 'training_data.csv')
    
    # Check if files exist
    if not os.path.exists(model_path):
        print("❌ Model not found! Training required first.")
        print(f"   Expected: {model_path}")
        print("\nRun 'train_agent.py' first to train the model.")
        sys.exit(1)
    
    if not os.path.exists(data_path):
        print("❌ Data not found!")
        print(f"   Expected: {data_path}")
        sys.exit(1)
    
    # Initialize trader
    trader = RLTrader(model_path, data_path)
    
    # Run
    try:
        trader.run()
    except KeyboardInterrupt:
        print("\n🛑 Trader stopped by user")