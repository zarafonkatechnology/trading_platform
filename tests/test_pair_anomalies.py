import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "forex_engine"))

from trading_controller2 import ForexTradingController


def test_correlation_break_is_assigned_to_both_pairs():
    controller = ForexTradingController.__new__(ForexTradingController)
    controller.pairs = ["EURUSD", "GBPUSD", "USDCHF"]

    result = controller._get_pair_anomaly_summary({
        "anomalies": [{
            "type": "CORRELATION_BREAK",
            "pair": "EURUSD_GBPUSD",
            "severity": "WARNING",
            "baseline": -0.73,
            "current": 0.77,
            "message": "Correlation break: EURUSD/GBPUSD (-0.73 -> 0.77)",
        }]
    })

    assert len(result["EURUSD"]) == 1
    assert len(result["GBPUSD"]) == 1
    assert result["USDCHF"] == []
