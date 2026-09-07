import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "forex_engine"))
from forex_engine.trading_controller2 import ForexTradingController


class FixedRLAgent:
    def __init__(self, action):
        self.action = np.asarray(action, dtype=np.float32)

    def predict(self, observation, deterministic=True):
        return self.action


def make_controller(z_score, action):
    controller = ForexTradingController.__new__(ForexTradingController)
    controller.rl_enabled = True
    controller.rl_agent = FixedRLAgent(action)
    controller.rl_env = None
    controller.pairs = ["EURUSD"]
    controller.config = {"entry_confirmation_z_threshold": 1.8}
    controller._get_pair_z_score = lambda pair: z_score
    return controller


def test_rl_sell_is_blocked_below_positive_z_threshold():
    controller = make_controller(1.52, [0, 2, 1])

    decision = controller._get_rl_decision_for_pair("EURUSD", {"EURUSD": 1.14})

    assert decision["used"] is False
    assert decision["signal"] == "HOLD"
    assert "SELL blocked" in decision["reason"]


def test_rl_sell_requires_positive_z_threshold():
    controller = make_controller(1.8, [0, 2, 1])

    decision = controller._get_rl_decision_for_pair("EURUSD", {"EURUSD": 1.14})

    assert decision["used"] is True
    assert decision["signal"] == "SELL"


def test_rl_buy_requires_negative_z_threshold():
    controller = make_controller(-1.8, [0, 1, 1])

    decision = controller._get_rl_decision_for_pair("EURUSD", {"EURUSD": 1.14})

    assert decision["used"] is True
    assert decision["signal"] == "BUY"
