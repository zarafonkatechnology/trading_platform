# backend/env/trading_env.py
class TradingEnvironment:
    """
    Simulated environment using Monte Carlo world model.
    """
    def __init__(self, world_model, initial_price=1.0950):
        self.world_model = world_model
        self.price = initial_price
        self.step_count = 0
        self.max_steps = 20
        self.position = 0   # 0=flat, 1=long, -1=short
    
    def reset(self):
        self.price = 1.0950
        self.step_count = 0
        self.position = 0
        return self._get_state()
    
    def _get_state(self):
        # Return the state vector used by the policy
        return np.array([self.price / 1000, 0.5, 0.01, 0.01, 0.5, 0.005, 0.7, 0.3, 0.0])
    
    def step(self, action):
        # action: 0=BUY, 1=SELL, 2=HOLD
        self.step_count += 1
        # Simulate next price using world model
        next_price = self.price * (1 + np.random.normal(0, 0.005))
        
        # Calculate reward
        reward = 0
        done = False
        if action == 0 and self.position == 0:
            self.position = 1
            reward = -0.1   # small cost for opening
        elif action == 1 and self.position == 0:
            self.position = -1
            reward = -0.1
        elif action == 0 and self.position == -1:
            # cover short
            pnl = (self.price - next_price) / self.price
            reward = pnl * 100
            self.position = 0
        elif action == 1 and self.position == 1:
            pnl = (next_price - self.price) / self.price
            reward = pnl * 100
            self.position = 0
        
        self.price = next_price
        
        if self.step_count >= self.max_steps:
            done = True
        
        return self._get_state(), reward, done, {}
