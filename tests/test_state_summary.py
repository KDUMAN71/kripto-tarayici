from scanner import config as C
from scanner import state as ST


def test_summary_excludes_known_symbols_payload():
    st = {
        "engine_version": C.ENGINE_VERSION,
        "known_symbols": {f"COIN{i}USDT": 0 for i in range(1000)},
        "signals": {
            "AAAUSDT": {"status": "WATCH", "side": "LONG", "trigger": 1.0, "sl": 0.9, "tp1": 1.2},
            "BBBUSDT": {"status": "CLOSED", "side": "SHORT"},
        },
        "log": [], "trades": [], "scan_log": [], "last_ok_run": 123, "fail_count": 0,
    }
    summary = ST.build_summary(st)
    assert "known_symbols" not in summary
    assert summary["known_symbols_count"] == 1000
    assert summary["open_signal_count"] == 1
    assert summary["open_signals"][0]["symbol"] == "AAAUSDT"


def test_prune_removes_only_stale_when_universe_is_healthy(monkeypatch):
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE", 2)
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_RATIO", 0.5)
    st = {"known_symbols": {"A": 0, "B": 0, "OLD": 0}, "log": []}
    removed = ST.prune_known_symbols(st, ["A", "B"])
    assert removed == 1
    assert set(st["known_symbols"]) == {"A", "B"}


def test_prune_skips_suspiciously_small_universe(monkeypatch):
    monkeypatch.setattr(C, "KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE", 3)
    st = {"known_symbols": {"A": 0, "B": 0, "C": 0}, "log": []}
    removed = ST.prune_known_symbols(st, ["A"])
    assert removed == 0
    assert set(st["known_symbols"]) == {"A", "B", "C"}


def test_trade_stats_are_compact_and_calculated():
    st = {
        "known_symbols": {}, "signals": {}, "log": [], "scan_log": [],
        "last_ok_run": 0, "fail_count": 0,
        "trades": [{"pnl_r": 2.0}, {"pnl_r": -1.0}, {"pnl_r": None}],
    }
    stats = ST.build_summary(st)["trades_stats"]
    assert stats["count"] == 3
    assert stats["scored_count"] == 2
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["win_rate"] == 0.5
    assert stats["avg_r"] == 0.5
