# rl_agent.py - COMPLETE FIXED VERSION
"""
Reinforcement Learning Agent wrapper
Supports PPO and SAC with Gymnasium
"""

import os
import numpy as np
import logging
from typing import Optional, Dict, Any, Type, Union
import torch.nn as nn

from stable_baselines3 import PPO, SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env

logger = logging.getLogger(__name__)

class RLAgent:
    """
    Wrapper for Reinforcement Learning agent.
    Supports PPO and SAC algorithms.
    """
    
    # Supported algorithms
    ALGORITHMS = {
        'PPO': PPO,
        'SAC': SAC,
    }
    
    def __init__(
        self,
        env,
        algorithm: str = 'PPO',
        model_path: Optional[str] = None,
        learning_rate: float = 3e-4,
        tensorboard_log: Optional[str] = None,
        load_existing: bool = False,
        buffer_size: int = 50000,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        policy_kwargs: Optional[Dict] = None,
    ):
        """
        Initialize RL Agent.
        
        Args:
            env: Gymnasium environment
            algorithm: 'PPO' or 'SAC'
            model_path: Path to save/load model
            learning_rate: Learning rate for optimizer
            tensorboard_log: TensorBoard log directory
            load_existing: If True, load existing model
            buffer_size: Replay buffer size (SAC only)
            n_steps: Steps per update (PPO only)
            batch_size: Batch size for training
            n_epochs: Number of epochs per update (PPO only)
            gamma: Discount factor
            policy_kwargs: Additional policy arguments
        """
        self.env = env
        self.algorithm = algorithm
        self.model_path = model_path
        self.tensorboard_log = tensorboard_log
        self.training = False
        
        # Default policy kwargs - FIXED: use nn.Tanh, not 'tanh'
        if policy_kwargs is None:
            policy_kwargs = {
                'net_arch': [128, 128, 64],
                'activation_fn': nn.Tanh,  # ← FIXED: use nn.Tanh
            }
        
        # Check if algorithm is supported
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported. Use: {list(self.ALGORITHMS.keys())}")
        
        # Load existing model if requested
        if load_existing and model_path and os.path.exists(model_path):
            logger.info(f"Loading RL model from {model_path}")
            self.model = self.ALGORITHMS[algorithm].load(
                model_path, 
                env=env, 
                tensorboard_log=tensorboard_log
            )
            self.model.set_env(env)
            logger.info("✅ Model loaded successfully")
        else:
            logger.info(f"Creating new RL model with {algorithm}")
            self.model = self._create_model(
                algorithm,
                env,
                learning_rate,
                tensorboard_log,
                buffer_size,
                n_steps,
                batch_size,
                n_epochs,
                gamma,
                policy_kwargs
            )
            logger.info("✅ New model created")
    
    def _create_model(
        self,
        algorithm: str,
        env,
        learning_rate: float,
        tensorboard_log: Optional[str],
        buffer_size: int,
        n_steps: int,
        batch_size: int,
        n_epochs: int,
        gamma: float,
        policy_kwargs: Dict,
    ) -> Union[PPO, SAC]:
        """Create a new model based on algorithm."""
        
        if algorithm == 'PPO':
            return PPO(
                'MlpPolicy',
                env,
                verbose=1,
                learning_rate=learning_rate,
                tensorboard_log=tensorboard_log,
                n_steps=n_steps,
                batch_size=batch_size,
                n_epochs=n_epochs,
                gamma=gamma,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                policy_kwargs=policy_kwargs,
            )
        
        elif algorithm == 'SAC':
            return SAC(
                'MlpPolicy',
                env,
                verbose=1,
                learning_rate=learning_rate,
                tensorboard_log=tensorboard_log,
                buffer_size=buffer_size,
                batch_size=batch_size,
                gamma=gamma,
                tau=0.005,
                policy_kwargs=policy_kwargs,
            )
        
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def predict(self, observation: np.ndarray, deterministic: bool = True) -> np.ndarray:
        """Get action from model or a deterministic fallback action when no model is ready."""
        if self.model is None:
            logger.warning("Model not initialized, returning deterministic fallback action")
            pair_count = max(1, len(getattr(self.env, 'pairs', ['EURUSD'])))
            action = np.array([0.0, 0.0, 0.0], dtype=np.float32)

            if observation is not None:
                try:
                    obs_array = np.asarray(observation, dtype=np.float32)
                    if obs_array.size > 0:
                        pair_idx = int(np.clip(abs(int(obs_array[0] * 1000)) % pair_count, 0, pair_count - 1))
                        trade_type = 0
                        if obs_array.size > 1:
                            trade_type = int(np.clip(int(abs(obs_array[1]) * 1000) % 3, 0, 2))
                        size_mult = float(np.clip(abs(obs_array[-1]) if obs_array.size > 0 else 0.0, 0.0, 2.0))
                        action = np.array([float(pair_idx), float(trade_type), size_mult], dtype=np.float32)
                except Exception:
                    action = np.array([0.0, 0.0, 0.0], dtype=np.float32)

            return action

        try:
            action, _ = self.model.predict(observation, deterministic=deterministic)
            if action is None:
                raise ValueError("Model returned None")
            return np.asarray(action, dtype=np.float32)
        except Exception as e:
            logger.warning(f"RL model prediction failed: {e}. Using fallback action")
            pair_count = max(1, len(getattr(self.env, 'pairs', ['EURUSD'])))
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)
    
    def train(self, total_timesteps: int = 100000, callback: Optional[BaseCallback] = None) -> None:
        """Train the model."""
        if self.model is None:
            logger.error("Model not initialized, cannot train")
            return
        
        self.training = True
        logger.info(f"Training RL model for {total_timesteps} timesteps")
        
        try:
            self.model.learn(
                total_timesteps=total_timesteps,
                callback=callback,
                reset_num_timesteps=False
            )
            logger.info("✅ Training complete")
        except Exception as e:
            logger.error(f"Training error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.training = False
    
    def save(self, path: Optional[str] = None) -> None:
        """Save model to disk."""
        if path is None:
            path = self.model_path
        
        if path is None:
            logger.warning("No path provided for saving model")
            return
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
        logger.info(f"💾 Model saved to {path}")
    
    def load(self, path: Optional[str] = None) -> None:
        """Load model from disk."""
        if path is None:
            path = self.model_path
        
        if path is None:
            logger.warning("No path provided for loading model")
            return
        
        if not os.path.exists(path):
            logger.warning(f"Model path does not exist: {path}")
            return
        
        self.model = self.ALGORITHMS[self.algorithm].load(path, env=self.env)
        self.model.set_env(self.env)
        logger.info(f"📂 Model loaded from {path}")
    
    def evaluate(self, env, n_episodes: int = 10) -> float:
        """Evaluate the current policy."""
        rewards = []
        
        for episode in range(n_episodes):
            try:
                result = env.reset()
                if isinstance(result, tuple) and len(result) == 2:
                    obs, _ = result
                else:
                    obs = result
                
                done = False
                total_reward = 0
                step_count = 0
                
                while not done and step_count < 1000:
                    action = self.predict(obs, deterministic=True)
                    
                    result = env.step(action)
                    if len(result) == 5:
                        obs, reward, terminated, truncated, _ = result
                        done = terminated or truncated
                    else:
                        obs, reward, done, _ = result
                    
                    total_reward += reward
                    step_count += 1
                
                rewards.append(total_reward)
                logger.info(f"Episode {episode+1}/{n_episodes}: reward = {total_reward:.2f}")
                
            except Exception as e:
                logger.warning(f"Evaluation episode {episode+1} failed: {e}")
                rewards.append(0.0)
        
        mean_reward = np.mean(rewards) if rewards else 0.0
        logger.info(f"📊 Evaluation: mean reward = {mean_reward:.2f} over {len(rewards)} episodes")
        return mean_reward
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            'algorithm': self.algorithm,
            'model_path': self.model_path,
            'training': self.training,
            'model_loaded': self.model is not None,
            'tensorboard_log': self.tensorboard_log,
        }


class TensorboardCallback(BaseCallback):
    """Custom callback for logging to TensorBoard."""
    
    def __init__(self, verbose: int = 0):
        super(TensorboardCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
    
    def _on_step(self) -> bool:
        if self.locals.get('dones', [False])[0]:
            ep_info = self.locals.get('infos', [{}])[0]
            if 'episode' in ep_info:
                reward = ep_info['episode']['r']
                length = ep_info['episode']['l']
                self.episode_rewards.append(reward)
                self.episode_lengths.append(length)
                
                self.logger.record('train/episode_reward', reward)
                self.logger.record('train/episode_length', length)
                self.logger.dump(self.num_timesteps)
                
                if self.verbose > 0:
                    print(f"Episode {len(self.episode_rewards)}: reward={reward:.2f}, length={length}")
        
        return True


class SaveModelCallback(BaseCallback):
    """Callback to save model periodically during training."""
    
    def __init__(self, agent: RLAgent, save_freq: int = 10000, save_path: str = 'models/rl_model'):
        super(SaveModelCallback, self).__init__()
        self.agent = agent
        self.save_freq = save_freq
        self.save_path = save_path
        self.last_save = 0
    
    def _on_step(self) -> bool:
        if self.n_calls - self.last_save >= self.save_freq:
            self.last_save = self.n_calls
            save_file = f"{self.save_path}_step{self.n_calls}.zip"
            self.agent.save(save_file)
            if self.verbose > 0:
                print(f"💾 Model saved at step {self.n_calls}")
        return True