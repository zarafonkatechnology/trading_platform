# rl_replay_env.py - COMPLETE FIXED VERSION

import numpy as np
import random
import logging
from typing import Dict, List, Optional, Tuple, Any

# Try Gymnasium first, fallback to Gym
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYMNASIUM_AVAILABLE = True
except ImportError:
    try:
        import gym
        from gym import spaces
        GYMNASIUM_AVAILABLE = False
        print("⚠️ Using old Gym (consider upgrading to Gymnasium)")
    except ImportError:
        raise ImportError("Please install gymnasium: pip install gymnasium")

logger = logging.getLogger(__name__)

class ReplayEnv(gym.Env):
    """
    A Gym environment that replays stored transitions.
    Used for offline training of RL agent.
    Supports both Gym and Gymnasium APIs.
    """
    
    def __init__(self, replay_buffer: List[Dict], 
                 observation_space: Optional[spaces.Space] = None,
                 action_space: Optional[spaces.Space] = None,
                 shuffle_buffer: bool = True,
                 max_steps: int = 1000):
        """
        Initialize Replay Environment.
        
        Args:
            replay_buffer: List of transitions
            observation_space: Optional observation space (auto-detected)
            action_space: Optional action space (auto-detected)
            shuffle_buffer: Whether to shuffle buffer on reset
            max_steps: Maximum steps per episode
        """
        super(ReplayEnv, self).__init__()
        
        self.buffer = replay_buffer
        self.shuffle_buffer = shuffle_buffer
        self.max_steps = max_steps
        self.index = 0
        self.step_count = 0
        self.episode_rewards = []
        
        # Validate buffer
        if not self.buffer:
            logger.warning("⚠️ Replay buffer is empty! Using dummy transitions.")
            self._create_dummy_buffer()
        
        # Detect observation space
        if observation_space is None:
            sample = self.buffer[0] if self.buffer else {'state': np.zeros(50)}
            obs_shape = sample['state'].shape if hasattr(sample['state'], 'shape') else (50,)
            self.observation_space = spaces.Box(
                low=-np.inf, 
                high=np.inf, 
                shape=obs_shape, 
                dtype=np.float32
            )
        else:
            self.observation_space = observation_space
        
        # Detect action space
        if action_space is None:
            sample = self.buffer[0] if self.buffer else {'action': np.array([0, 0, 0.5])}
            action = sample['action']
            if hasattr(action, 'shape'):
                action_shape = action.shape
            else:
                action_shape = (len(action),)
            
            # Try to detect bounds
            if hasattr(action, 'min') and hasattr(action, 'max'):
                low = np.full(action_shape, action.min())
                high = np.full(action_shape, action.max())
            else:
                low = np.full(action_shape, 0.0)
                high = np.full(action_shape, 2.0)
            
            self.action_space = spaces.Box(
                low=low.astype(np.float32),
                high=high.astype(np.float32),
                dtype=np.float32
            )
        else:
            self.action_space = action_space
        
        logger.info(f"✅ ReplayEnv initialized")
        logger.info(f"   Buffer size: {len(self.buffer)} transitions")
        logger.info(f"   Observation shape: {self.observation_space.shape}")
        logger.info(f"   Action shape: {self.action_space.shape}")
        logger.info(f"   Max steps: {self.max_steps}")
    
    def _create_dummy_buffer(self):
        """Create dummy transitions for testing."""
        self.buffer = []
        for i in range(100):
            self.buffer.append({
                'state': np.random.randn(50).astype(np.float32),
                'action': np.array([np.random.randint(0, 3), np.random.randint(0, 3), np.random.uniform(0, 2)],
                                   dtype=np.float32),
                'reward': np.random.uniform(-0.5, 0.5),
                'next_state': np.random.randn(50).astype(np.float32),
                'done': i == 99
            })
        logger.info(f"   Created {len(self.buffer)} dummy transitions for testing")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        """Reset environment to start of episode."""
        self.index = 0
        self.step_count = 0
        self.episode_rewards = []
        
        # Shuffle buffer if enabled
        if self.shuffle_buffer:
            random.shuffle(self.buffer)
        
        # Get initial observation
        if self.buffer:
            obs = self.buffer[0]['state'].copy() if hasattr(self.buffer[0]['state'], 'copy') else self.buffer[0]['state']
        else:
            obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        
        if GYMNASIUM_AVAILABLE:
            return obs.astype(np.float32), {}
        else:
            return obs.astype(np.float32)
    
    def step(self, action: np.ndarray) -> Tuple[Any, float, bool, bool, Dict]:
        """
        Step through replay buffer.
        
        Args:
            action: Action to take (ignored, uses stored action)
            
        Returns:
            obs, reward, terminated, truncated, info
        """
        self.step_count += 1
        
        # Check if episode should end
        if self.index >= len(self.buffer) or self.step_count >= self.max_steps:
            if GYMNASIUM_AVAILABLE:
                return np.zeros(self.observation_space.shape, dtype=np.float32), 0, True, False, {}
            else:
                return np.zeros(self.observation_space.shape, dtype=np.float32), 0, True, {}
        
        # Get transition
        transition = self.buffer[self.index]
        obs = transition['state'].copy() if hasattr(transition['state'], 'copy') else transition['state']
        stored_action = transition['action']
        reward = transition['reward']
        next_obs = transition['next_state'].copy() if hasattr(transition['next_state'], 'copy') else transition['next_state']
        done = transition.get('done', False)
        
        self.index += 1
        self.episode_rewards.append(reward)
        
        # Check if episode ends
        terminated = done or self.index >= len(self.buffer) or self.step_count >= self.max_steps
        
        info = {
            'step': self.step_count,
            'index': self.index,
            'buffer_size': len(self.buffer),
            'episode_reward': sum(self.episode_rewards)
        }
        
        if GYMNASIUM_AVAILABLE:
            return next_obs.astype(np.float32), float(reward), terminated, False, info
        else:
            return next_obs.astype(np.float32), float(reward), terminated, info
    
    def get_batch(self, batch_size: int = 64) -> Dict[str, np.ndarray]:
        """
        Get a batch of transitions from the buffer.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            Dict with 'state', 'action', 'reward', 'next_state', 'done'
        """
        if not self.buffer:
            return self._get_dummy_batch(batch_size)
        
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        states = np.array([t['state'] for t in batch], dtype=np.float32)
        actions = np.array([t['action'] for t in batch], dtype=np.float32)
        rewards = np.array([t['reward'] for t in batch], dtype=np.float32)
        next_states = np.array([t['next_state'] for t in batch], dtype=np.float32)
        dones = np.array([t.get('done', False) for t in batch], dtype=np.float32)
        
        return {
            'state': states,
            'action': actions,
            'reward': rewards.reshape(-1, 1),
            'next_state': next_states,
            'done': dones.reshape(-1, 1)
        }
    
    def _get_dummy_batch(self, batch_size: int) -> Dict[str, np.ndarray]:
        """Generate dummy batch for testing."""
        return {
            'state': np.random.randn(batch_size, 50).astype(np.float32),
            'action': np.random.randn(batch_size, 3).astype(np.float32),
            'reward': np.random.randn(batch_size, 1).astype(np.float32),
            'next_state': np.random.randn(batch_size, 50).astype(np.float32),
            'done': np.zeros((batch_size, 1), dtype=np.float32)
        }
    
    def get_status(self) -> Dict:
        """Get environment status."""
        return {
            'buffer_size': len(self.buffer),
            'index': self.index,
            'step_count': self.step_count,
            'max_steps': self.max_steps,
            'episode_reward': sum(self.episode_rewards) if self.episode_rewards else 0,
            'shuffle_buffer': self.shuffle_buffer
        }
    
    def add_transitions(self, transitions: List[Dict]):
        """Add new transitions to the buffer."""
        self.buffer.extend(transitions)
        logger.info(f"📊 Added {len(transitions)} transitions, buffer size: {len(self.buffer)}")
    
    def clear(self):
        """Clear the buffer."""
        self.buffer = []
        self.index = 0
        self.step_count = 0
        logger.info("🔄 Replay buffer cleared")
    
    def sample(self, batch_size: int = 64) -> List[Dict]:
        """Sample random transitions from buffer."""
        if not self.buffer:
            return []
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self) -> int:
        """Return buffer size."""
        return len(self.buffer)


# ============================================
# TEST
# ============================================

def test_replay_env():
    """Test the Replay Environment."""
    
    print("\n" + "="*60)
    print("🧪 TESTING REPLAY ENVIRONMENT")
    print("="*60 + "\n")
    
    # Create dummy buffer
    buffer = []
    for i in range(100):
        buffer.append({
            'state': np.random.randn(50).astype(np.float32),
            'action': np.array([np.random.randint(0, 3), np.random.randint(0, 3), np.random.uniform(0, 2)],
                               dtype=np.float32),
            'reward': np.random.uniform(-0.5, 0.5),
            'next_state': np.random.randn(50).astype(np.float32),
            'done': i == 99
        })
    
    # Create environment
    env = ReplayEnv(buffer)
    print("✅ Environment created")
    print(f"   Buffer size: {len(env)}")
    
    # Test reset
    print("\n📌 Testing reset...")
    result = env.reset()
    if isinstance(result, tuple) and len(result) == 2:
        obs, info = result
        print(f"   ✅ Reset returned (obs, info)")
    else:
        obs = result
        print(f"   ✅ Reset returned obs only")
    print(f"   Observation shape: {obs.shape}")
    
    # Test steps
    print("\n📌 Testing steps...")
    total_reward = 0
    for i in range(10):
        # Random action (ignored by replay env)
        action = np.array([np.random.randint(0, 3), np.random.randint(0, 3), np.random.uniform(0, 2)],
                          dtype=np.float32)
        
        result = env.step(action)
        if len(result) == 5:  # Gymnasium
            obs, reward, terminated, truncated, info = result
            done = terminated or truncated
        else:  # Old Gym
            obs, reward, done, info = result
        
        total_reward += reward
        print(f"   Step {i+1}: reward={reward:.3f}, done={done}")
    
    # Test batch sampling
    print("\n📌 Testing batch sampling...")
    batch = env.get_batch(batch_size=16)
    print(f"   States shape: {batch['state'].shape}")
    print(f"   Actions shape: {batch['action'].shape}")
    print(f"   Rewards shape: {batch['reward'].shape}")
    print(f"   Next states shape: {batch['next_state'].shape}")
    print(f"   Dones shape: {batch['done'].shape}")
    
    # Test status
    print("\n📌 Getting status...")
    status = env.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ Replay Environment Test Complete!")
    print("="*60)

if __name__ == "__main__":
    test_replay_env()