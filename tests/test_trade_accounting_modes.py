import pytest
from scanner.trade_accounting import *


def test_touch_is_not_a_fill():
    t=target_touch("ICPUSDT","SHORT","TP1",2.9,100)
    assert t["realized_r"] is None and not t["executed"]


def test_signal_only_never_claims_realized_profit():
    assert account_trade(SIGNAL_ONLY,100,99,"LONG")["realized_r"] is None


def test_paper_partial_tp_then_stop():
    x=account_trade(PAPER_FILL,100,99,"LONG",
                    [{"price":102,"fraction":.25},{"price":99,"fraction":.75}])
    assert x["realized_r"]==pytest.approx(-.25)


def test_short_partial_tp_then_stop():
    x=account_trade(PAPER_FILL,100,101,"SHORT",
                    [{"price":98,"fraction":.5},{"price":101,"fraction":.5}])
    assert x["realized_r"]==pytest.approx(.5)


def test_live_requires_exchange_fill_identifiers():
    with pytest.raises(ValueError):
        account_trade(VERIFIED_LIVE_FILL,100,99,"LONG",[{"price":101,"fraction":1}])


def test_full_close_required():
    with pytest.raises(ValueError):
        realized_r_from_fills(100,99,"LONG",[{"price":101,"fraction":.5}])
