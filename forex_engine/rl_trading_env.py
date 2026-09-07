# rl_trading_env.py - COMPLETE FIXED VERSION

import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

# Try importing gymnasium, fallback to gym
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYMNASIUM_AVAILABLE = True
    print("✅ Using Gymnasium")
except ImportError:
    try:
        import gym
        from gym import spaces
        GYMNASIUM_AVAILABLE = False
        print("⚠️ Using old Gym (consider upgrading to Gymnasium)")
    except ImportError:
        print("❌ No gym/gymnasium found - install: pip install gymnasium")
        raise ImportError("Please install gymnasium: pip install gymnasium")

logger = logging.getLogger(__name__)

class ForexTradingEnv(gym.Env):
    """
    Gymnasium/Gym environment for Forex trading with multi-agent consensus.
    Uses Box action space for compatibility with PPO.
    """
    
    def __init__(self, controller, config: Optional[Dict] = None):
        super(ForexTradingEnv, self).__init__()
        
        self.controller = controller
        self.config = config or {}
        self.pairs = self.config.get('pairs', ['EURUSD'])
        self.max_steps = self.config.get('max_steps', 1000)
        self.step_counter = 0
        
        # ===== ACTION SPACE =====
        # Box space: [pair_idx (0 to n-1), trade_type (0=HOLD,1=BUY,2=SELL), size_mult (0.0 to 2.0)]
        num_pairs = len(self.pairs)
        self.action_space = spaces.Box(
            low=np.array([0, 0, 0.0], dtype=np.float32),
            high=np.array([num_pairs - 1, 2, 2.0], dtype=np.float32),
            dtype=np.float32
        )
        
        # ===== OBSERVATION SPACE =====
        # 50 features with proper bounds
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(50,), 
            dtype=np.float32
        )
        
        # ===== STATE =====
        self.external_market_data: Optional[Dict] = None
        self.episode_trades = []
        self.episode_pnl = 0.0
        self.max_drawdown_episode = 0.0
        self.peak_equity_episode = 0.0
        self.last_price = 0.0
        self.last_pnl = 0.0
        
        # ===== PENALTIES =====
        self.penalty_inactivity = 0.05
        self.penalty_high_trades = 1.0
        self.penalty_loss = 5.0
        self.penalty_holding = 0.01
        
        logger.info("✅ ForexTradingEnv initialized")
        logger.info(f"   Pairs: {num_pairs}")
        logger.info(f"   Max Steps: {self.max_steps}")
        logger.info(f"   Action Space: Box(3,)")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Union[np.ndarray, Tuple[np.ndarray, Dict]]:
        """Reset environment state."""
        self.step_counter = 0
        self.episode_trades = []
        self.episode_pnl = 0.0
        self.max_drawdown_episode = 0.0
        self.peak_equity_episode = self._get_current_equity()
        self.last_price = 0.0
        self.last_pnl = 0.0
        
        obs = self._get_observation()
        
        if GYMNASIUM_AVAILABLE:
            return obs, {}
        else:
            return obs
    
    def set_external_data(self, market_data: Dict):
        """Set external market data for training episodes."""
        self.external_market_data = market_data
    
    def step(self, action: np.ndarray) -> Union[Tuple, Tuple[np.ndarray, float, bool, bool, Dict]]:
        """
        Execute action and return next state, reward, done, info.
        action: [pair_idx, trade_type, size_multiplier]
        """
        self.step_counter += 1
        
        # Clip action to valid ranges
        pair_idx = int(np.clip(action[0], 0, len(self.pairs) - 1))
        trade_type = int(np.clip(action[1], 0, 2))
        size_mult = np.clip(action[2], 0.0, 2.0)
        
        pair = self.pairs[pair_idx]
        
        # Get market data
        if self.external_market_data is not None:
            market_data = self.external_market_data
        else:
            market_data = self.controller.build_market_data()
        
        price = market_data.get(pair, 0)
        self.last_price = price
        
        # ===== CALCULATE REWARD =====
        reward = 0.0
        done = False
        info = {'pair': pair, 'action': action.tolist()}
        
        # Get current equity
        current_equity = self._get_current_equity()
        
        # Update peak equity and drawdown
        if current_equity > self.peak_equity_episode:
            self.peak_equity_episode = current_equity
        drawdown = (self.peak_equity_episode - current_equity) if self.peak_equity_episode > 0 else 0
        if drawdown > self.max_drawdown_episode:
            self.max_drawdown_episode = drawdown
        
        # ===== EXECUTE TRADE =====
        if trade_type != 0 and price > 0:
            # Check risk limits
            if self._check_trade_allowed(trade_type, pair, market_data):
                # Get PnL before trade
                before_pnl = self._get_current_pnl()
                
                # Create consensus from RL action
                confidence = int(70 + np.random.randint(0, 30))
                consensus = {
                    'signal': 'BUY' if trade_type == 1 else 'SELL',
                    'confidence': confidence,
                    'reason': f'RL action: {trade_type}',
                    'pair': pair
                }
                
                # Execute trade
                try:
                    if self.controller.execution_engine:
                        result = self.controller.execution_engine.execute_signal(
                            consensus, market_data, position_size=size_mult
                        )
                        
                        if result and result.get('status') == 'EXECUTED':
                            self.episode_trades.append({
                                'pair': pair,
                                'type': 'BUY' if trade_type == 1 else 'SELL',
                                'size': size_mult,
                                'price': price,
                                'confidence': confidence
                            })
                except Exception as e:
                    logger.debug(f"RL trade execution error: {e}")
                
                # Update PnL
                if self.controller.execution_engine:
                    self.controller.execution_engine.update_pnl(market_data)
                    after_pnl = self._get_current_pnl()
                    
                    # Calculate reward
                    reward = after_pnl - before_pnl
                    self.episode_pnl += reward
                    
                    # Add bonus for profitable trades
                    if reward > 0:
                        reward += min(0.5, reward * 0.1)
                    
                    # Add penalty for too many trades
                    if len(self.episode_trades) > 10:
                        reward -= self.penalty_high_trades * (len(self.episode_trades) - 10) / 10
                    
                    # Add penalty for daily loss limit
                    if self.controller.execution_engine.daily_pnl < -100:
                        reward -= self.penalty_loss
                
            else:
                # Trade blocked
                reward = -0.5
                info['blocked'] = True
        
        elif trade_type == 0:
            # HOLD action
            reward = -self.penalty_inactivity
            
            # Small penalty for holding losing positions
            if self._has_open_positions():
                current_pnl = self._get_current_pnl()
                if current_pnl < 0:
                    reward -= 0.1 * abs(current_pnl) / 100
        
        # ===== CHECK TERMINATION =====
        if self.step_counter >= self.max_steps:
            done = True
        
        # Terminal reward adjustment
        if done:
            if self.episode_pnl > 0:
                reward += min(5.0, self.episode_pnl / 20)
            if self.max_drawdown_episode > 50:
                reward -= self.max_drawdown_episode / 10
        
        # Get next observation
        obs = self._get_observation()
        
        # Update info
        info.update({
            'reward': reward,
            'step': self.step_counter,
            'episode_pnl': self.episode_pnl,
            'drawdown': self.max_drawdown_episode,
            'trades': len(self.episode_trades),
        })
        
        self.last_pnl = reward
        
        if GYMNASIUM_AVAILABLE:
            return obs, reward, done, False, info
        else:
            return obs, reward, done, info
    
    def _check_trade_allowed(self, trade_type: int, pair: str, market_data: Dict) -> bool:
        """Check if trade is allowed based on risk rules."""
        # Daily trade limit
        if len(self.episode_trades) >= 10:
            return False
        
        # Check if already in position for this pair
        if self.controller.execution_engine:
            positions = self.controller.execution_engine.positions
            if pair in positions and positions[pair].get('size', 0) != 0:
                return False
        
        # Check daily loss limit
        if self.controller.execution_engine and self.controller.execution_engine.daily_pnl < -100:
            return False
        
        return True
    
    def _has_open_positions(self) -> bool:
        """Check if there are any open positions."""
        if not self.controller.execution_engine:
            return False
        for pair, pos in self.controller.execution_engine.positions.items():
            if pos.get('size', 0) != 0:
                return True
        return False
    
    def _get_current_pnl(self) -> float:
        """Get current PnL."""
        if self.controller.execution_engine:
            return self.controller.execution_engine.daily_pnl
        return 0.0
    
    def _get_current_equity(self) -> float:
        """Get current equity."""
        if self.controller.execution_engine:
            return 10000 + self.controller.execution_engine.daily_pnl
        return 10000.0
    
    def _get_observation(self) -> np.ndarray:
        """Build observation vector from controller state."""
        features = []
        
        # Get engine state
        engine = self.controller.engine.get_status() if self.controller.engine else {}
        
        # 1. Engine features (3)
        features.append(engine.get('engine_speed', 0.0))
        features.append(engine.get('engine_health', 100.0) / 100.0)
        features.append(engine.get('reversal_probability', 0.0) / 100.0)
        
        # 2. Engine direction one-hot (3)
        dirs = ['FORWARD', 'BACKWARD', 'NEUTRAL']
        d = engine.get('engine_direction', 'NEUTRAL')
        features += [1.0 if d == x else 0.0 for x in dirs]
        
        # 3. Prices for each pair (n)
        prices = self.controller.get_all_prices()
        for pair in self.pairs:
            price = prices.get(pair, 0.0)
            if pair.endswith('JPY'):
                features.append(price / 200.0)  # Normalize JPY pairs
            else:
                features.append(price)  # Normalize other pairs
        
        # 4. Positions (size, pnl) per pair (2n)
        positions = self.controller.execution_engine.positions if self.controller.execution_engine else {}
        for pair in self.pairs:
            pos = positions.get(pair, {})
            features.append(pos.get('size', 0.0) / 100.0)
            features.append(pos.get('pnl', 0.0) / 100.0)
        
        # 5. Agent signals (up to 6 agents, each vote + confidence = 12 features)
        agent_features = self._get_agent_votes()
        features.extend(agent_features)
        
        # 6. Time features (2)
        now = datetime.now()
        features.append(now.hour / 24.0)
        features.append(now.weekday() / 7.0)
        
        # 7. Market regime (1)
        regime = engine.get('regime', 'RANGING')
        regime_map = {'RANGING': 0, 'TRENDING': 1, 'VOLATILE': 2}
        features.append(regime_map.get(regime, 0) / 2.0)
        
        # 8. Daily PnL (1)
        daily_pnl = self._get_current_pnl()
        features.append(daily_pnl / 100.0)
        
        # 9. Recent reward (1)
        features.append(self.last_pnl / 100.0)
        
        # Pad to 50 features
        while len(features) < 50:
            features.append(0.0)
        features = features[:50]
        
        return np.array(features, dtype=np.float32)
    
    def _get_agent_votes(self) -> List[float]:
        """Get agent votes as features."""
        votes = []
        # Try to get agent results from controller
        if hasattr(self.controller, 'last_results'):
            agent_results = self.controller.last_results.get('agents', {})
            for agent_name, result in agent_results.items():
                vote = result.get('vote', 'HOLD')
                confidence = result.get('confidence', 50) / 100.0
                # Encode vote: BUY=1, SELL=-1, HOLD=0
                vote_val = 1.0 if vote == 'BUY' else -1.0 if vote == 'SELL' else 0.0
                votes.append(vote_val)
                votes.append(confidence)
        # Pad to 12 features (6 agents)
        while len(votes) < 12:
            votes.append(0.0)
        return votes[:12]
    
    def close_positions(self):
        """Close all open positions at end of episode."""
        if self.controller.execution_engine:
            self.controller.execution_engine.close_all_positions()
    
    def get_status(self) -> Dict:
        """Get current environment status."""
        return {
            'step': self.step_counter,
            'max_steps': self.max_steps,
            'episode_trades': len(self.episode_trades),
            'episode_pnl': self.episode_pnl,
            'max_drawdown': self.max_drawdown_episode,
            'peak_equity': self.peak_equity_episode,
            'current_equity': self._get_current_equity(),
        }