"""V3.4 kirilim duzeltmeleri: yapisal stop, hedef ayrimi, retest'e donusum.

Uc davranis test edilir:
  A) Formasyonun geçersizlik ucu risk bandina sigmadiginda, TETIKLENMIS
     kirilimlarda yapisal stop (son salinim ucu) devreye girer.
  B) TP2, TP1'e yapismaz; min_sep_r kadar ilerideki pivota gider.
  C) Kirilim kacirildiginda aday silinmez, retest beklentisine cevrilir.
"""
import pandas as pd

from scanner import config as C
from scanner.engine import _targets
from scanner.engine_v3 import (_candidate_from_pattern, _pattern_levels,
                               _structural_sl)


def _bars(low, high, n=30):
    return pd.DataFrame({"open": [low] * n, "high": [high] * n,
                         "low": [low] * n, "close": [(low + high) / 2] * n})


def _a15(price, low=99.0, high=101.0, atr=0.5, highs=None, lows=None):
    return {"price": price, "atr": atr, "closed": _bars(low, high),
            "pivot_highs": highs or [102.0, 105.0, 110.0],
            "pivot_lows": lows or [98.0, 95.0, 90.0]}


def _a1h(atr=1.0, stretch=0.5):
    return {"atr": atr, "stretch": stretch, "closed": _bars(99.0, 101.0),
            "pivot_highs": [], "pivot_lows": []}


def _a4h(tscore=1):
    return {"tscore": tscore, "pivot_highs": [], "pivot_lows": []}


def _pattern(state="triggered", invalid=99.0, trigger=100.0):
    return {"dir": "long", "type": "breakout_retest", "state": state,
            "trigger": trigger, "invalid": invalid, "quality": 0.8,
            "note": "pivot kirildi"}


# --- A) yapisal stop ---------------------------------------------------------

def test_structural_sl_sits_below_trigger_for_long():
    sl = _structural_sl("long", 100.0, _a15(100.0, low=99.0), _a1h())
    assert sl is not None and sl < 100.0


def test_far_invalid_is_rescued_by_structural_sl_when_triggered():
    """Gecersizlik ucu %10 uzakta; eskiden plan hic kurulamiyordu."""
    plan, trigger = _pattern_levels("long", _pattern(invalid=90.0),
                                    _a15(100.0), _a1h(), _a4h())
    assert trigger == 100.0
    assert plan is not None
    # Yapisal stop kullanildi: risk formasyon ucundan degil son salinimdan.
    assert plan["sl"] > 98.0
    assert C.MIN_RISK_PCT <= plan["risk_pct"] <= C.ACTIVE_MAX_LIVE_RISK_PCT


def test_far_invalid_still_rejected_when_pattern_only_forming():
    """Yedek yalnizca tetiklenmis kirilimlar icin; formasyon asamasinda degil."""
    plan, _ = _pattern_levels("long", _pattern(state="forming", invalid=90.0),
                              _a15(100.0), _a1h(), _a4h())
    assert plan is None


# --- B) hedef ayrimi ---------------------------------------------------------

BUNCHED = [101.6, 102.05, 106.0]


def test_targets_default_keeps_legacy_behaviour():
    """min_sep_r verilmezse V2 davranisi birebir korunur."""
    tp1, tp2, _ = _targets("long", 100.0, 1.0, BUNCHED, [], [])
    assert (tp1, tp2) == (101.6, 102.05)


def test_targets_separation_skips_pivot_glued_to_tp1():
    tp1, tp2, _ = _targets("long", 100.0, 1.0, BUNCHED, [], [], min_sep_r=0.5)
    assert tp1 == 101.6
    assert tp2 == 106.0
    assert (tp2 - tp1) / tp1 * 100 > 0.5


# --- C) kacirilan kirilim -> retest ------------------------------------------

def test_missed_breakout_becomes_retest_watch_instead_of_being_dropped():
    price = 102.0  # tetigin %2 ustunde -> kovalama filtresi eskiden silerdi
    cand = _candidate_from_pattern(_pattern(), _a15(price), _a1h(), _a4h())
    assert cand is not None
    assert cand["retest"] is True
    assert cand["stage"] in ("WATCH", "EARLY")
    assert cand["trigger"] == 100.0          # tetik artik retest seviyesi
    assert "retest bekleniyor" in cand["pattern"]["note"]


def test_retest_candidate_dropped_when_price_ran_too_far():
    price = 100.0 * (1 + (C.EARLY_PROXIMITY_PCT + 2) / 100)
    assert _candidate_from_pattern(_pattern(), _a15(price), _a1h(), _a4h()) is None


def test_fresh_breakout_still_becomes_active():
    """Fiyat tetige yakinken davranis degismemeli."""
    cand = _candidate_from_pattern(_pattern(), _a15(100.1), _a1h(), _a4h())
    assert cand is not None
    assert cand["stage"] == "ACTIVE"
    assert not cand.get("retest")
