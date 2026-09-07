import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "forex_engine"))

from brokers.broker_manager import BrokerManager
from brokers.usdchf_broker import USDCHFBroker


class DummyBroker:
    def __init__(self):
        self.persistence = 2
        self.z_score = 2.2
        self.entry_threshold = 1.5
        self.min_persistence = 2
        self.signal = "HOLD"
        self.confidence = 0
        self.current_price = 1.0
        self.close_history = []

    def analyze(self, market_data):
        return {
            "vote": "SELL",
            "confidence": 80,
            "z_score": self.z_score,
            "volatility": 0.01,
        }


def test_broker_manager_uses_broker_persistence_for_z_signal():
    manager = BrokerManager(engine=None, monte_carlo=None)
    broker = DummyBroker()
    manager.brokers = {"USDCHF": broker}

    result = manager._get_pair_decision(
        "USDCHF",
        broker,
        {"USDCHF": 1.0},
        {"direction": "MIXED", "confidence": 100},
    )

    assert result["signal"] == "SELL"


def test_usdchf_broker_analyzes_without_candles():
    broker = USDCHFBroker()
    result = broker.analyze(
        {
            "price": 0.8980,
            "VIX": 30.0,
            "safe_haven_flow": 0.8,
            "risk_sentiment": -0.2,
            "geopolitical_risk": 0.6,
        }
    )

    assert result["vote"] != "HOLD"
