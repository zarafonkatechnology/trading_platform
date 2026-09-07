import importlib.util
import sys
from pathlib import Path


def load_controller_module():
    module_path = Path(__file__).resolve().parents[1] / "forex_engine" / "trading_controller2.py"
    sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location("trading_controller2", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMT4:
    def _send(self, payload):
        if payload.get("command") == "HISTORY":
            count = int(payload.get("count", 3))
            return {
                "candles": [
                    {"open": 1.1000 + i, "close": 1.1005 + i, "high": 1.1010 + i, "low": 1.0995 + i, "timeframe": payload.get("timeframe", "H1")}
                    for i in range(count)
                ]
            }
        return {}


def test_get_candles_supports_h1_timeframe(monkeypatch):
    module = load_controller_module()
    monkeypatch.setattr(module, "get_mt4_prices", lambda: None)

    controller = module.ForexTradingController({
        "pairs": ["EURUSD"],
        "rl_enabled": False,
        "use_hybrid": False,
        "pairs_config": {},
    })
    controller.mt4 = FakeMT4()

    candles = controller._get_candles("EURUSD", timeframe="H1", count=3)

    assert len(candles) == 3
    assert candles[0]["timeframe"] == "H1"
