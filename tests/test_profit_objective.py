from research.profit_metrics import trade_metrics


def test_profit_metrics_use_realized_r_not_runner_count():
    trades = [{"pnl_r": 2.0}, {"pnl_r": -1.0}, {"pnl_r": 1.0}]
    m = trade_metrics(trades)
    assert round(m["expectancy_r"], 4) == round(2/3, 4)
    assert m["profit_factor"] == 3.0
    assert m["net_r"] == 2.0


def test_drawdown_is_measured_in_r():
    m = trade_metrics([{"pnl_r": 2}, {"pnl_r": -1}, {"pnl_r": -2}, {"pnl_r": 1}])
    assert m["max_drawdown_r"] == 3.0
