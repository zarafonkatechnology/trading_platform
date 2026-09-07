from forex_engine.core.order_execution import OrderExecutionEngine


class AcceptedProvider:
    def place_order(self, **kwargs):
        assert kwargs['symbol'] == 'AUDUSD'
        assert kwargs['order_type'] == 'BUY'
        assert kwargs['stop_loss'] > 0
        assert kwargs['take_profit'] > 0
        return {'status': 'ACCEPTED', 'ticket': 12345}


def test_accepted_mt4_response_is_normalized_to_success():
    engine = OrderExecutionEngine.__new__(OrderExecutionEngine)

    result = engine._send_mt4_order(
        AcceptedProvider(), 'AUDUSD', 'BUY', 0.01, 0.69635, 0.70005
    )

    assert result['success'] is True
    assert result['ticket'] == 12345
