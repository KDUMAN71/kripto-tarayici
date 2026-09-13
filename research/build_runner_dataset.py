"""Build a 30-day Futures runner dataset for V3.5 reverse engineering.

Phase 1 intentionally uses 1h candles across the whole current USDT perpetual
universe (one request per symbol) to find strong rolling 24h events cheaply.
Phase 2 downloads 15m candles only for selected runner symbols/windows.

Caveat: current exchangeInfo introduces survivorship bias for contracts that were
delisted during the lookback. The generated metadata records this explicitly.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

from scanner import data
from research.reverse_engineering import snapshot_features, excursion_from_entry


def _klines_window(symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1500) -> pd.DataFrame:
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        raw = data.get("/klines", {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": limit,
        })
        if not raw:
            break
        rows.extend(raw)
        last_open = int(raw[-1][0])
        if last_open < cursor:
            break
        cursor = last_open + 1
        if len(raw) < limit:
            break
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "openTime", "open", "high", "low", "close", "volume", "closeTime",
        "quoteVolume", "trades", "tbBase", "tbQuote", "ignore",
    ])
    for c in ("open", "high", "low", "close", "volume", "quoteVolume", "tbQuote"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce")
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    return df.drop_duplicates("openTime").sort_values("openTime").reset_index(drop=True)


def _rolling_events_1h(symbol: str, df: pd.DataFrame, min_run_pct: float = 10.0,
                       horizon_h: int = 24, cooldown_h: int = 6) -> list[dict]:
    """Label starts whose next 24h maximum high reaches min_run_pct.

    The label may look forward; later features are reconstructed from data no
    later than each candidate timestamp.
    """
    if df.empty or len(df) < horizon_h + 2:
        return []
    events = []
    last = -10**9
    for i in range(len(df) - horizon_h - 1):
        if i - last < cooldown_h:
            continue
        entry = float(df.iloc[i].close)
        fut = df.iloc[i + 1:i + 1 + horizon_h]
        mx = float(fut.high.max())
        run = (mx / entry - 1) * 100 if entry else 0
        if run < min_run_pct:
            continue
        j = int(fut.high.to_numpy().argmax()) + i + 1
        events.append({
            "symbol": symbol,
            "start_ts": df.iloc[i].openTime.isoformat(),
            "peak_ts": df.iloc[j].openTime.isoformat(),
            "start_price": entry,
            "max_run_pct": run,
            "quote_volume_1h": float(df.iloc[i].quoteVolume or 0),
        })
        last = i
    return events


def _dedupe_events(events: list[dict], hours: int = 12) -> list[dict]:
    out = []
    by_sym = defaultdict(list)
    for e in sorted(events, key=lambda x: (x["symbol"], x["start_ts"])):
        ts = pd.Timestamp(e["start_ts"])
        if by_sym[e["symbol"]] and (ts - by_sym[e["symbol"]][-1]).total_seconds() < hours * 3600:
            # Keep the stronger label in the same episode.
            if e["max_run_pct"] > out[-1]["max_run_pct"] and out[-1]["symbol"] == e["symbol"]:
                out[-1] = e
            continue
        out.append(e)
        by_sym[e["symbol"]].append(ts)
    return out


def _enrich_15m(event: dict, before_h: int = 24, after_h: int = 24) -> dict:
    start = pd.Timestamp(event["start_ts"])
    begin = int((start - pd.Timedelta(hours=before_h)).timestamp() * 1000)
    end = int((start + pd.Timedelta(hours=after_h)).timestamp() * 1000)
    d = _klines_window(event["symbol"], "15m", begin, end)
    if d.empty:
        return event
    eligible = d.index[d.openTime <= start]
    if len(eligible) == 0:
        return event
    idx = int(eligible[-1])
    event = dict(event)
    event["features_t0"] = snapshot_features(d, idx)
    event["execution_24h"] = excursion_from_entry(d, idx, horizon_bars=96)
    # Fixed pre-run snapshots let analysis compare runner DNA without leakage.
    event["feature_path"] = []
    for hours in (24, 12, 6, 3, 1, 0):
        bars = hours * 4
        j = idx - bars
        if j >= 0:
            snap = snapshot_features(d, j)
            snap["hours_before_start"] = hours
            event["feature_path"].append(snap)
    return event


def build(days: int, min_run_pct: float, top_events: int | None, max_symbols: int | None) -> dict:
    now = pd.Timestamp.now(tz="UTC").floor("h")
    start = now - pd.Timedelta(days=days + 1)
    symbols = data.exchange_perp_symbols() or []
    if max_symbols:
        symbols = symbols[:max_symbols]

    all_events = []
    failures = []
    for n, sym in enumerate(symbols, 1):
        d = _klines_window(sym, "1h", int(start.timestamp() * 1000), int(now.timestamp() * 1000))
        if d.empty:
            failures.append(sym)
        else:
            all_events.extend(_rolling_events_1h(sym, d, min_run_pct=min_run_pct))
        if n % 25 == 0:
            print(f"coarse scan {n}/{len(symbols)} | events={len(all_events)}")

    events = _dedupe_events(all_events)
    events.sort(key=lambda x: x["max_run_pct"], reverse=True)
    if top_events:
        events = events[:top_events]

    enriched = []
    for i, e in enumerate(events, 1):
        enriched.append(_enrich_15m(e))
        if i % 10 == 0:
            print(f"15m enrich {i}/{len(events)}")

    return {
        "meta": {
            "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "lookback_days": days,
            "min_run_pct": min_run_pct,
            "symbols_scanned": len(symbols),
            "failures": failures,
            "event_count": len(enriched),
            "survivorship_bias_warning": "Universe uses current exchangeInfo; delisted contracts inside lookback may be absent.",
            "label_warning": "Runner labels look forward; features_t0/feature_path are past-only and may be used for replay research.",
        },
        "events": enriched,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-run-pct", type=float, default=10.0)
    ap.add_argument("--top-events", type=int, default=250)
    ap.add_argument("--max-symbols", type=int)
    ap.add_argument("--output", default="artifacts/v35_runner_dataset.json")
    args = ap.parse_args()
    payload = build(args.days, args.min_run_pct, args.top_events, args.max_symbols)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path} | events={payload['meta']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
