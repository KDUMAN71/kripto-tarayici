from scanner import state as ST
from scanner import config as C


def _st():
    return {"signals": {}, "pre_runners": {}, "log": []}


def test_pre_runner_is_separate_from_user_facing_signals():
    st = _st()
    ST.upsert_pre_runner(st, "METISUSDT", {"source": "momentum_pre"}, ts=100)
    assert "METISUSDT" in st["pre_runners"]
    assert "METISUSDT" not in st["signals"]
    assert st["pre_runners"]["METISUSDT"]["status"] == "PRE_RUNNER"


def test_pre_runner_preserves_created_and_refreshes_last_seen():
    st = _st()
    ST.upsert_pre_runner(st, "XUSDT", {"change_24h": 2}, ts=100)
    ST.upsert_pre_runner(st, "XUSDT", {"change_24h": 4}, ts=200)
    assert st["pre_runners"]["XUSDT"]["created"] == 100
    assert st["pre_runners"]["XUSDT"]["last_seen"] == 200
    assert st["pre_runners"]["XUSDT"]["change_24h"] == 4


def test_pre_runner_expires_deterministically():
    st = _st()
    ST.upsert_pre_runner(st, "OLDUSDT", {}, ts=100)
    ST.upsert_pre_runner(st, "FRESHUSDT", {}, ts=100 + C.PRE_RUNNER_EXPIRY_H * 3600)
    expired = ST.expire_pre_runners(st, ts=101 + C.PRE_RUNNER_EXPIRY_H * 3600)
    assert "OLDUSDT" in expired
    assert "OLDUSDT" not in st["pre_runners"]
    assert "FRESHUSDT" in st["pre_runners"]


def test_promotion_removes_hidden_candidate_and_logs_transition():
    st = _st()
    ST.upsert_pre_runner(st, "METISUSDT", {}, ts=100)
    row = ST.promote_pre_runner(st, "METISUSDT", "WATCH")
    assert row is not None
    assert "METISUSDT" not in st["pre_runners"]
    assert st["log"][-1]["event"] == "PRE_RUNNER_PROMOTED"


def test_pre_runner_book_is_bounded(monkeypatch):
    monkeypatch.setattr(C, "PRE_RUNNER_MAX", 2)
    st = _st()
    ST.upsert_pre_runner(st, "AUSDT", {}, ts=1)
    ST.upsert_pre_runner(st, "BUSDT", {}, ts=2)
    ST.upsert_pre_runner(st, "CUSDT", {}, ts=3)
    assert set(st["pre_runners"]) == {"BUSDT", "CUSDT"}
