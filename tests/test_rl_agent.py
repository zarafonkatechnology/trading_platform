import numpy as np

from forex_engine.rl_agent import RLAgent


class DummyEnv:
    def __init__(self):
        self.pairs = ["EURUSD", "GBPUSD"]
        self.controller = type("Controller", (), {})()
        self.controller.engine = type("Engine", (), {"get_status": lambda self: {"engine_direction": "FORWARD", "engine_speed": 1.0, "engine_health": 100.0, "reversal_probability": 0.0}})
        self.controller.execution_engine = type("Exec", (), {"positions": {}, "daily_pnl": 0.0, "trades_today": 0})
        self.controller.get_all_prices = lambda: {"EURUSD": 1.1000, "GBPUSD": 1.2800}


def test_rl_agent_predict_returns_valid_action_without_model():
    agent = RLAgent.__new__(RLAgent)
    agent.env = DummyEnv()
    agent.model = None
    action = agent.predict(np.zeros(50, dtype=np.float32), deterministic=True)

    assert action.shape == (3,)
    assert 0 <= action[0] < len(agent.env.pairs)
    assert 0 <= action[1] <= 2
    assert 0.0 <= action[2] <= 2.0
