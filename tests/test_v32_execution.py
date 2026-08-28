import pandas as pd

from scanner.confluence import confluence
from scanner.engine_v3 import _execution_veto, _trend_flags
from scanner.main import active_msg
from scanner.patterns import detect_breakout_retest
from scanner.state import migrate_engine


def _frame(closes, *, side="long", trigger=100.0, volume=100.0):
    n = len(closes)
    if side == "long":
        ema20 = [c - 0.30 - (n - i) * 0.01 for i, c in enumerate(closes)]
        ma7 = [e + 0.10 for e in ema20]
    else:
        ema20 = [c + 0.30 + (n - i) * 0.01 for i, c in enumerate(closes)]
        ma7 = [e - 0.10 for e in ema20]
    return pd.DataFrame({
        "close": closes,
        "high": [c + 0.20 for c in closes],
        "low": [c - 0.20 for c in closes],
        "volume": [volume] * n,
        "tbBase": [volume * (0.55 if side == "long" else 0.45)] * n,
        "ema20": ema20,
        "ma7": ma7,
    })


def _analysis(closes, *, side="long", price=None, vol_ratio=1.4,
              tscore=0, pivot_highs=None, pivot_lows=None):
    closed = _frame(closes, side=side)
    return {
        "closed": closed,
        "price": float(price if price is not None else closes[-1]),
        "atr": 1.0,
        "vol_ratio": vol_ratio,
        "tscore": tscore,
        "tlabel": "test",
        "rsi": 50.0,
        "pivot_highs": pivot_highs or [],
        "pivot_lows": pivot_lows or [],
    }


def _ctx(**overrides):
    ctx = {
        "funding_rate": 0.0,
        "spread_pct": 0.01,
        "basis_pct": 0.0,
        "oi": {"1h": 1.0, "4h": 0.0, "24h": 0.0},
        "taker_15m": 0.55,
        "taker_1h": 0.54,
        "ls_ratios": {},
        "change_24h": 0.0,
        "a1d": None,
    }
    ctx.update(overrides)
    return ctx


def test_bico_like_failed_reclaim_long_is_vetoed():
    a15 = _analysis([99.5, 100.4, 100.2, 99.8], side="long", price=99.7)
    a1h = _analysis([100.0] * 12, vol_ratio=1.2)
    a4h = _analysis([100.0] * 12, tscore=-2)
    pattern = {"type": "liquidity_sweep", "trigger": 100.0}

    veto, quality, _ = _execution_veto(
        "long", pattern, {"sl": 98.0}, a15, a1h, a4h, _ctx())

    assert "failed reclaim/hold" in veto
    assert quality == 0


def test_confirmed_breakdown_retest_short_can_pass_in_bullish_4h_context():
    closes = [101.2, 101.0, 100.8, 100.5, 100.2, 99.8, 99.6, 99.4, 99.2, 99.0]
    a15 = _analysis(closes, side="short", price=99.0)
    a1h = _analysis([100.0] * 12, vol_ratio=1.3)
    a4h = _analysis([100.0] * 12, tscore=2)
    pattern = {"type": "breakout_retest", "trigger": 100.0}

    allowed, reversal = _trend_flags("short", pattern["type"], a4h)
    veto, quality, checks = _execution_veto(
        "short", pattern, {"sl": 101.0}, a15, a1h, a4h,
        _ctx(taker_15m=0.46, change_24h=4.0))

    assert allowed and reversal
    assert veto is None
    assert quality > 0
    assert any(c.startswith("hold=") for c in checks)


def test_failed_reclaim_gets_no_15m_trigger_confluence_points():
    a15 = _analysis([99.7, 100.4, 100.2, 99.8], side="long", price=99.8,
                    vol_ratio=2.0)
    a1h = _analysis([100.0] * 12, vol_ratio=1.4)
    a4h = _analysis([100.0] * 12, tscore=0)
    pattern = {"type": "liquidity_sweep", "trigger": 100.0}

    _, parts, veto = confluence(
        "long", pattern, a15, a1h, a4h, None, _ctx(),
        {"hard_break": None, "trend": 0, "sweep_dir": None, "note": "test"})

    assert veto is None
    assert not any(p.startswith("15d tetik") for p in parts)


def test_mid_range_pivot_breakdown_retest_is_detected():
    closes = [101.0, 100.8, 100.5, 100.4, 100.3, 100.2,
              100.2, 99.7, 99.8, 99.6, 99.2, 98.8]
    sub = pd.DataFrame({
        "close": closes,
        "high": [c + (0.45 if i == 8 else 0.20) for i, c in enumerate(closes)],
        "low": [c - 0.20 for c in closes],
    })
    piv = [(2, 100.0, "L"), (4, 104.0, "H")]

    pattern = detect_breakout_retest(
        piv, sub, atr=1.0, price=98.8, hi24=110.0, lo24=90.0)

    assert pattern is not None
    assert pattern["type"] == "breakout_retest"
    assert pattern["dir"] == "short"
    assert pattern["trigger"] == 100.0


def test_active_telegram_message_is_decision_only():
    sig = {
        "side": "SHORT", "entry_lo": 0.0246, "entry_hi": 0.0248,
        "sl": 0.0254, "tp1": 0.0240, "tp2": 0.0234, "tp3": 0.0228,
        "rr2": 2.1, "setup_type": "breakout_retest",
        "funding": 0.001, "oi": {"24h": -9}, "score_parts": ["debug"],
    }

    msg = active_msg("BICOUSDT", sig, "debug-news")

    assert "İŞLEM BÖLGESİ AKTİF — BICOUSDT SHORT" in msg
    assert "Neden:" in msg and "İptal:" in msg
    for debug_field in ("Funding", "OI:", "Taker", "RSI", "Skor", "debug-news"):
        assert debug_field not in msg


def test_v31_state_migration_preserves_history_and_cancels_open_plans():
    state = {
        "signals": {
            "OPENUSDT": {"status": "ACTIVE", "last_update": 1},
            "DONEUSDT": {"status": "STOPPED", "last_update": 2},
        },
        "log": [{"t": 1, "sym": "OLD", "event": "ACTIVE", "detail": "kept"}],
        "trades": [{"symbol": "DONEUSDT", "outcome": "STOPPED"}],
    }
    old_log = list(state["log"])
    old_trades = list(state["trades"])

    migrated = migrate_engine(state)

    assert migrated == 1
    assert state["engine_version"] == "3.2.2"
    assert state["signals"]["OPENUSDT"]["status"] == "CANCELLED"
    assert state["signals"]["DONEUSDT"]["status"] == "STOPPED"
    assert state["log"][:1] == old_log
    assert state["trades"] == old_trades
    assert state["log"][-1]["event"] == "ENGINE_MIGRATION"
