import pandas as pd

from research.reverse_engineering import (
    earliest_threshold_cross,
    excursion_from_entry,
    find_runner_labels,
    snapshot_features,
)


def _df(n=140, jump_at=None):
    rows = []
    px = 100.0
    for i in range(n):
        if jump_at is not None and i >= jump_at:
            px *= 1.015
        rows.append({
            "openTime": pd.Timestamp("2026-08-01", tz="UTC") + pd.Timedelta(minutes=15 * i),
            "open": px * 0.999,
            "high": px * 1.002,
            "low": px * 0.998,
            "close": px,
            "volume": 100 + i,
            "quoteVolume": (100 + i) * px,
            "trades": 1000 + i,
            "tbQuote": (100 + i) * px * 0.53,
        })
    return pd.DataFrame(rows)


def test_snapshot_features_never_reads_future_rows():
    a = _df()
    idx = 100
    f1 = snapshot_features(a, idx)
    b = a.copy()
    b.loc[idx + 1:, "close"] = 999999
    b.loc[idx + 1:, "high"] = 999999
    b.loc[idx + 1:, "volume"] = 999999
    f2 = snapshot_features(b, idx)
    assert f1 == f2


def test_runner_label_detects_future_move_but_features_do_not_use_it():
    d = _df(jump_at=105)
    labels = find_runner_labels("TESTUSDT", d, horizon_bars=32, min_run_pct=10, cooldown_bars=12)
    assert labels
    assert labels[0].max_run_pct >= 10
    f = snapshot_features(d, 100)
    assert (f["ret_1h"] or 0) < 3


def test_excursion_reports_mae_and_mfe():
    d = _df(jump_at=105)
    ex = excursion_from_entry(d, 100, horizon_bars=30)
    assert ex["mfe_pct"] > 10
    assert ex["mae_pct"] < 1


def test_threshold_cross_returns_first_bar_only():
    d = _df(jump_at=105)
    i = earliest_threshold_cross(d, 100, 5.0, horizon_bars=30)
    assert i is not None
    assert i >= 105
    entry = d.iloc[100].close
    assert d.iloc[i].high >= entry * 1.05
    assert not (d.iloc[100:i].high >= entry * 1.05).any()
