import pandas as pd

from scanner import state as ST


class DummyTelegram:
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)
        return True


def _analysis(price, close):
    return {
        "price": price,
        "closed": pd.DataFrame({"close": [close, close, close]}),
    }


def _signal(note="", created=None):
    return {
        "status": "WATCH",
        "side": "LONG",
        "trigger": 100.0,
        "invalidation": 95.0,
        "setup_note": note,
        "created": ST.now() if created is None else created,
        "last_update": ST.now(),
    }


def test_retest_watch_is_not_marked_missed_when_price_is_extended():
    st = {"signals": {"XUSDT": _signal("kirilim yapildi, retest bekleniyor")}, "log": []}
    ST.update_pretrade(st, "XUSDT", _analysis(103.0, 101.0), _analysis(103.0, 101.0), DummyTelegram())
    sig = st["signals"]["XUSDT"]
    assert sig["status"] == "WATCH"
    assert sig["retest_wait"] is True
    assert not any(x["event"] == "MISSED_SILENT" for x in st["log"])


def test_non_retest_pretrade_can_still_be_marked_missed():
    st = {"signals": {"XUSDT": _signal("normal forming setup")}, "log": []}
    ST.update_pretrade(st, "XUSDT", _analysis(103.0, 101.0), _analysis(103.0, 101.0), DummyTelegram())
    assert st["signals"]["XUSDT"]["status"] == "MISSED"
    assert any(x["event"] == "MISSED_SILENT" for x in st["log"])


def test_retest_watch_still_cancels_on_structural_invalidation():
    st = {"signals": {"XUSDT": _signal("kirilim yapildi, retest bekleniyor")}, "log": []}
    ST.update_pretrade(st, "XUSDT", _analysis(94.0, 94.0), _analysis(94.0, 94.0), DummyTelegram())
    assert st["signals"]["XUSDT"]["status"] == "CANCELLED"


def test_retest_watch_still_expires():
    old = ST.now() - 40 * 3600
    st = {"signals": {"XUSDT": _signal("kirilim yapildi, retest bekleniyor", created=old)}, "log": []}
    ST.update_pretrade(st, "XUSDT", _analysis(103.0, 101.0), _analysis(103.0, 101.0), DummyTelegram())
    assert st["signals"]["XUSDT"]["status"] == "EXPIRED"
