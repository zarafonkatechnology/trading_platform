import importlib


def test_trade_open_keeps_balance_unchanged():
    module = importlib.import_module('src.api.routes.client_trades')
    balance, equity = module.calculate_balance_after_open(1000.0, 1000.0)
    assert balance == 1000.0
    assert equity == 1000.0


def test_close_balance_uses_only_realized_pnl():
    module = importlib.import_module('src.api.routes.client_trades')
    balance, equity = module.calculate_balance_after_close(1000.0, 1000.0, 25.0)
    assert balance == 1025.0
    assert equity == 1025.0
