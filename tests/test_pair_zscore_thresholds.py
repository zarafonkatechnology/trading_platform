import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "forex_engine"))

from trading_controller2 import ForexTradingController


def make_controller(config=None):
    controller = ForexTradingController.__new__(ForexTradingController)
    controller.config = config or {}
    return controller


def test_pair_specific_default_thresholds_are_used():
    controller = make_controller()

    assert controller._get_pair_z_threshold("AUDUSD") == 1.5
    assert controller._get_pair_z_threshold("GBPUSD") == 2.0
    assert controller._get_pair_z_threshold("USDCHF") == 1.6


def test_pair_config_overrides_symbol_default():
    controller = make_controller({
        "pairs_config": {"AUDUSD": {"z_score_threshold": 1.9}}
    })

    assert controller._get_pair_z_threshold("AUDUSD") == 1.9


def test_unknown_pair_uses_global_fallback():
    controller = make_controller({"entry_confirmation_z_threshold": 1.7})

    assert controller._get_pair_z_threshold("UNKNOWN") == 1.7
