# training_env.py
"""
Specialized environment for RL training using historical/synthetic data.
"""
import numpy as np
from rl_trading_env import ForexTradingEnv

class TrainingEnv(ForexTradingEnv):
    def __init__(self, controller, config=None, price_history=None):
        super().__init__(controller, config)
        self.price_history = price_history  # dict of pair -> list of prices
        self.current_step = 0
        self.max_steps = config.get('max_steps', 500)
        self.episode_data = None  # list of market_data dicts

    def set_episode(self, episode_data):
        """Set the sequence of market data for this episode."""
        self.episode_data = episode_data
        self.current_step = 0

    def reset(self, seed=None, options=None):
        self.current_step = 0
        if self.episode_data is None:
            # Generate random episode on the fly
            self._generate_random_episode()
        if gymnasium:
            return self._get_observation(), {}
        else:
            return self._get_observation()

    def step(self, action):
        # Use the episode data for this step
        if self.episode_data is not None and self.current_step < len(self.episode_data):
            # Override controller's market data with episode data
            market_data = self.episode_data[self.current_step]
            # We need to tell the controller to use this market_data instead of building its own.
            # We'll patch the controller's build_market_data temporarily.
            original_build = self.controller.build_market_data
            self.controller.build_market_data = lambda: market_data
            # Now call parent step with the action
            result = super().step(action)
            # Restore original build method
            self.controller.build_market_data = original_build
            self.current_step += 1
            return result
        else:
            # Fallback to regular step (will use controller's own data)
            return super().step(action)

    def _generate_random_episode(self):
        """Generate a random episode using Monte Carlo."""
        episode = []
        base_price = 1.0
        for _ in range(self.max_steps):
            market_data = {}
            for pair in self.pairs:
                # Random walk
                if not episode:
                    price = base_price
                else:
                    prev = episode[-1].get(pair, base_price)
                    price = prev * (1 + np.random.normal(0, 0.01))
                market_data[pair] = max(0.0001, price)
            episode.append(market_data)
        self.episode_data = episode