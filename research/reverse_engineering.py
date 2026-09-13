"""V3.5 runner reverse-engineering primitives.

The module deliberately separates LABELS (which may look into the future) from
FEATURES (which must only use rows available at or before timestamp T). This is
the core anti-lookahead rule for every replay experiment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RunnerLabel:
    symbol: str
    start_ts: pd.Timestamp
    horizon_bars: int
    forward_return_pct: float
    max_run_pct: float
    max_drawdown_pct: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_ts"] = self.start_ts.isoformat()
        return d


def _pct(a: float, b: float) -> float:
    return (b / a - 1.0) * 100.0 if a else np.nan


def label_forward_move(symbol: str, df: pd.DataFrame, idx: int, horizon_bars: int) -> RunnerLabel | None:
    """Create a future-looking label for research only.

    The label answers: starting at the close of row ``idx``, how far did price
    run up and draw down over the next ``horizon_bars`` bars? It must never be
    fed directly into the live signal model.
    """
    if idx < 0 or idx >= len(df) - 1:
        return None
    end = min(len(df), idx + 1 + horizon_bars)
    future = df.iloc[idx + 1:end]
    if future.empty:
        return None
    entry = float(df.iloc[idx]["close"])
    final = float(future.iloc[-1]["close"])
    max_high = float(future["high"].max())
    min_low = float(future["low"].min())
    ts = pd.Timestamp(df.iloc[idx]["openTime"])
    return RunnerLabel(
        symbol=symbol,
        start_ts=ts,
        horizon_bars=len(future),
        forward_return_pct=_pct(entry, final),
        max_run_pct=_pct(entry, max_high),
        max_drawdown_pct=_pct(entry, min_low),
    )


def find_runner_labels(symbol: str, df: pd.DataFrame, *, horizon_bars: int = 96,
                       min_run_pct: float = 10.0, cooldown_bars: int = 24) -> list[RunnerLabel]:
    """Find candidate runner starts using a future label, deduplicated by cooldown.

    Default assumes 15m bars: 96 bars = 24h, cooldown 24 bars = 6h.
    A label is positive when the future maximum reaches ``min_run_pct``.
    """
    out: list[RunnerLabel] = []
    last_idx = -10**9
    for idx in range(len(df) - 1):
        if idx - last_idx < cooldown_bars:
            continue
        lab = label_forward_move(symbol, df, idx, horizon_bars)
        if lab and lab.max_run_pct >= min_run_pct:
            out.append(lab)
            last_idx = idx
    return out


def _safe_ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0) or pd.isna(a) or pd.isna(b):
        return None
    return float(a) / float(b)


def snapshot_features(df: pd.DataFrame, idx: int) -> dict:
    """Build a strictly past-only feature snapshot at row ``idx``.

    Required columns: openTime/open/high/low/close/volume. Optional Binance
    kline columns quoteVolume, trades, tbQuote are used when present.
    """
    if idx < 0 or idx >= len(df):
        raise IndexError(idx)
    hist = df.iloc[:idx + 1].copy()
    row = hist.iloc[-1]
    close = float(row["close"])

    def ret(bars: int) -> float | None:
        if len(hist) <= bars:
            return None
        return _pct(float(hist.iloc[-1 - bars]["close"]), close)

    vol = pd.to_numeric(hist["volume"], errors="coerce")
    qv = pd.to_numeric(hist["quoteVolume"], errors="coerce") if "quoteVolume" in hist else None
    recent_vol = float(vol.iloc[-1]) if len(vol) else np.nan
    vol_med_20 = float(vol.tail(20).median()) if len(vol) >= 3 else np.nan

    # True-range / compression features use only closed historical bars.
    prev_close = pd.to_numeric(hist["close"], errors="coerce").shift(1)
    hi = pd.to_numeric(hist["high"], errors="coerce")
    lo = pd.to_numeric(hist["low"], errors="coerce")
    tr = pd.concat([(hi - lo).abs(), (hi - prev_close).abs(), (lo - prev_close).abs()], axis=1).max(axis=1)
    atr14 = float(tr.tail(14).mean()) if len(tr) >= 14 else None
    atr50 = float(tr.tail(50).mean()) if len(tr) >= 50 else None

    lookback = hist.tail(min(len(hist), 96))
    range_hi = float(lookback["high"].max())
    range_lo = float(lookback["low"].min())
    range_pos = ((close - range_lo) / (range_hi - range_lo)) if range_hi > range_lo else None

    taker_share = None
    if "tbQuote" in hist and qv is not None:
        taker_share = _safe_ratio(float(row.get("tbQuote") or 0), float(row.get("quoteVolume") or 0))

    return {
        "ts": pd.Timestamp(row["openTime"]).isoformat(),
        "close": close,
        "ret_15m": ret(1),
        "ret_1h": ret(4),
        "ret_3h": ret(12),
        "ret_6h": ret(24),
        "ret_24h": ret(96),
        "vol_ratio_20": _safe_ratio(recent_vol, vol_med_20),
        "quote_volume": float(row["quoteVolume"]) if "quoteVolume" in row and pd.notna(row["quoteVolume"]) else None,
        "trades": int(row["trades"]) if "trades" in row and pd.notna(row["trades"]) else None,
        "taker_buy_quote_share": taker_share,
        "atr14_pct": (atr14 / close * 100.0) if atr14 and close else None,
        "atr_compression": _safe_ratio(atr14, atr50),
        "range_pos_24h": range_pos,
    }


def excursion_from_entry(df: pd.DataFrame, idx: int, *, horizon_bars: int = 96) -> dict:
    """Return MAE/MFE after a hypothetical entry at row ``idx`` close."""
    if idx < 0 or idx >= len(df) - 1:
        return {"mfe_pct": None, "mae_pct": None, "final_pct": None}
    entry = float(df.iloc[idx]["close"])
    future = df.iloc[idx + 1:min(len(df), idx + 1 + horizon_bars)]
    if future.empty:
        return {"mfe_pct": None, "mae_pct": None, "final_pct": None}
    return {
        "mfe_pct": _pct(entry, float(future["high"].max())),
        "mae_pct": _pct(entry, float(future["low"].min())),
        "final_pct": _pct(entry, float(future.iloc[-1]["close"])),
    }


def earliest_threshold_cross(df: pd.DataFrame, start_idx: int, threshold_pct: float,
                             *, horizon_bars: int = 96) -> int | None:
    """First future bar whose high reaches ``threshold_pct`` above start close."""
    entry = float(df.iloc[start_idx]["close"])
    target = entry * (1.0 + threshold_pct / 100.0)
    end = min(len(df), start_idx + 1 + horizon_bars)
    for i in range(start_idx + 1, end):
        if float(df.iloc[i]["high"]) >= target:
            return i
    return None


def feature_path(df: pd.DataFrame, start_idx: int, offsets: Iterable[int]) -> list[dict]:
    """Past-only snapshots around an event start.

    Negative offsets inspect the hours/bars before the labelled runner start;
    zero is the label start. Positive offsets are allowed only for execution
    studies and are explicitly tagged so they cannot be mixed into pre-runner
    prediction training by accident.
    """
    out = []
    for off in offsets:
        i = start_idx + int(off)
        if i < 0 or i >= len(df):
            continue
        row = snapshot_features(df, i)
        row["offset_bars"] = int(off)
        row["phase"] = "pre_or_start" if off <= 0 else "post_start_execution"
        out.append(row)
    return out
