# ============================================================
# hyperlearning.py - Hyperlearning / Meta-Learning System
# ============================================================

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_trading.config import Config
from rl_trading.environment import SpreadArbitrageEnv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HyperLearner:
    """
    Meta-learning system that adapts agent parameters to changing market conditions.
    
    This implements the "hyperlearning" concept: training a model to adapt
    the parameters of another model.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.meta_model = None
        self.agent_params = {}
        self.performance_history = []
        
        logger.info("🧠 HyperLearner initialized")
    
    def adapt_parameters(self, agent_name: str, market_regime: str) -> Dict:
        """
        Adapt agent parameters based on current market regime.
        
        Market regimes: 'TRENDING', 'RANGING', 'VOLATILE', 'CRISIS'
        """
        # Base parameters
        base_params = {
            'entry_threshold': 2.5,
            'exit_threshold': 0.5,
            'confidence_boost': 0.0,
            'position_size_multiplier': 1.0
        }
        
        # Regime-specific adjustments
        regime_adjustments = {
            'TRENDING': {
                'entry_threshold': 2.0,
                'exit_threshold': 0.3,
                'confidence_boost': 0.1,
                'position_size_multiplier': 1.2
            },
            'RANGING': {
                'entry_threshold': 2.5,
                'exit_threshold': 0.5,
                'confidence_boost': 0.0,
                'position_size_multiplier': 1.0
            },
            'VOLATILE': {
                'entry_threshold': 3.0,
                'exit_threshold': 0.5,
                'confidence_boost': -0.1,
                'position_size_multiplier': 0.7
            },
            'CRISIS': {
                'entry_threshold': 3.5,
                'exit_threshold': 0.3,
                'confidence_boost': -0.2,
                'position_size_multiplier': 0.5
            }
        }
        
        # Merge parameters
        adapted_params = base_params.copy()
        if market_regime in regime_adjustments:
            for key, value in regime_adjustments[market_regime].items():
                adapted_params[key] = value
        
        # Store for this agent
        self.agent_params[agent_name] = adapted_params
        
        logger.info(f"   {agent_name} adapted to {market_regime}: {adapted_params}")
        
        return adapted_params
    
    def detect_market_regime(self, data: pd.DataFrame) -> str:
        """
        Detect current market regime using statistical metrics.
        """
        if len(data) < 100:
            return 'RANGING'
        
        # Calculate metrics
        volatility = np.std(data['spread'].values[-100:])
        trend_strength = abs(np.corrcoef(range(100), data['spread'].values[-100:])[0, 1])
        
        # Determine regime
        if volatility > 0.005:
            if trend_strength > 0.7:
                return 'TRENDING'
            else:
                return 'VOLATILE'
        elif volatility > 0.01:
            return 'CRISIS'
        else:
            return 'RANGING'
    
    def learn_from_episode(self, agent_name: str, episode_data: Dict):
        """
        Learn from a completed episode and update performance history.
        """
        performance = {
            'agent': agent_name,
            'timestamp': pd.Timestamp.now(),
            'pnl': episode_data.get('pnl', 0),
            'win_rate': episode_data.get('win_rate', 0),
            'z_entry': episode_data.get('z_entry', 0),
            'z_exit': episode_data.get('z_exit', 0),
            'hold_time': episode_data.get('hold_time', 0)
        }
        
        self.performance_history.append(performance)
        
        # Keep history manageable
        if len(self.performance_history) > 1000:
            self.performance_history.pop(0)
        
        logger.info(f"📊 HyperLearner recorded: {agent_name} PnL=${performance['pnl']:.2f}")
    
    def get_optimal_parameters(self, agent_name: str, data: pd.DataFrame) -> Dict:
        """
        Get optimal parameters based on learning history and current regime.
        """
        # Detect current regime
        regime = self.detect_market_regime(data)
        
        # Get base adapted parameters
        params = self.adapt_parameters(agent_name, regime)
        
        # Adjust based on historical performance
        agent_history = [p for p in self.performance_history if p['agent'] == agent_name]
        
        if len(agent_history) > 10:
            # Calculate average win rate for this agent
            avg_win_rate = np.mean([p['win_rate'] for p in agent_history[-50:]])
            
            # Adjust confidence based on historical performance
            if avg_win_rate > 0.8:
                params['confidence_boost'] += 0.1
                params['entry_threshold'] = max(2.0, params['entry_threshold'] - 0.2)
            elif avg_win_rate < 0.5:
                params['confidence_boost'] -= 0.1
                params['entry_threshold'] = min(3.5, params['entry_threshold'] + 0.2)
        
        return params


# ============================================================
# META-LEARNING ENVIRONMENT WRAPPER
# ============================================================

class MetaLearningWrapper:
    """
    Wraps the environment to include hyperlearning capabilities.
    """
    
    def __init__(self, env: SpreadArbitrageEnv, hyperlearner: HyperLearner):
        self.env = env
        self.hyperlearner = hyperlearner
        self.agent_name = None
        
    def set_agent(self, agent_name: str):
        """Set the current agent being trained."""
        self.agent_name = agent_name
        
    def step(self, action: int) -> Tuple:
        """Execute step with hyperlearning integration."""
        state, reward, done, info = self.env.step(action)
        
        # If episode is done, trigger hyperlearning
        if done and self.agent_name:
            episode_data = {
                'pnl': info.get('cumulative_pnl', 0),
                'win_rate': info.get('win_rate', 0),
                'z_entry': info.get('entry_z', 0),
                'z_exit': info.get('exit_z', 0),
                'hold_time': info.get('hold_time', 0)
            }
            self.hyperlearner.learn_from_episode(self.agent_name, episode_data)
        
        return state, reward, done, info