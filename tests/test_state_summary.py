import json

from scanner import state as ST
from scanner import config as C


def test_build_summary_is_compact_and_excludes_known_symbols_payload(monkeypatch):
    monkeypatch.setattr(ST, "now", lambda: 1_800_000_000)
    st = {
        "engine_version": C.ENGINE_VERSION,
        "known_symbols": {f"COIN{i}USDT": i for i in range(1200)},
        "signals": {
            "AAAUSDT": {"status": "WATCH", "side": "LONG", "trigger": 1.0, "sl": 0.9,
                        "tp1": 1.2, "score": 8, "created": 1_799_999_000},
            "BBBUSDT": {"status": "CANCELLED", "side": "SHORT"},
        },
        "scan_log": [{"ts": 1_799_999_900, "ok": True}],
        "log": [{"t": 1_799_999_800, "sym": "AAAUSDT", "event": "WATCH", "detail": "x"}],
        "trades": [{"symbol": "X", "pnl_r": -1.0}, {"symbol": "Y", "pnl_r": 2.0}],
        "fail_count": 0,
        "last_ok_run": 1_799_999_900,
    }
    summary = ST.build_summary(st)
    text = json.dumps(summary)
    assert "known_symbols" not in summary
    assert summary["known_symbols_count"] == 1200
    assert summary["open_signal_count"] == 1
    assert summary["open_signals"][0]["symbol"] == "AAAUSDT"
    assert summary["trades_stats"]["count"] == 2
    assert summary["trades_stats"]["wins"] == 1
    assert len(text) < 10_000


def test_prune_known_symbols_removes_only_stale_when_universe_is_healthy(monkeypatch):
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE", 3)
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_RATIO", 0.5)
    st = {"known_symbols": {"A": 0, "B": 0, "OLD": 0}, "log": []}
    n = ST.prune_known_symbols(st, ["A", "B", "C"])
    assert n == 1
    assert set(st["known_symbols"]) == {"A", "B"}


def test_prune_skips_suspiciously_small_exchange_universe(monkeypatch):
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE", 300)
    st = {"known_symbols": {f"S{i}": 0 for i in range(500)}, "log": []}
    n = ST.prune_known_symbols(st, [f"S{i}" for i in range(20)])
    assert n == 0
    assert len(st["known_symbols"]) == 500
