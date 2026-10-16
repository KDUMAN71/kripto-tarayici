from scanner.state import _trade_stats, _record_trade

def test_proxy_is_not_realized_performance():
    summary = _trade_stats([{"pnl_r": -1, "realized_r": None, "tp1_hit": True}])
    assert summary["basis"] == "FULL_POSITION_PRICE_PATH_PROXY_NOT_REALIZED"
    assert summary["realized_trades"] == 0

def test_target_touch_does_not_imply_realized_profit(monkeypatch):
    import scanner.state as state
    monkeypatch.setattr(state, "now", lambda: 100)
    book = {"trades": []}
    signal = {"side": "SHORT", "sl": 110, "entry_ref": 100, "tp1_hit": True,
              "target_touches": [{"type": "TARGET_TOUCH", "executed": False}]}
    _record_trade(book, "ICPUSDT", signal, "STOPPED", 110)
    trade = book["trades"][0]
    assert trade["pnl_r"] == -1
    assert trade["realized_r"] is None
    assert trade["tp1_hit"]
    assert trade["pnl_r_basis"] == "FULL_POSITION_PRICE_PATH_PROXY_NOT_REALIZED"
