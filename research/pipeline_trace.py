"""Point-in-time Phase B gate trace.

Replays only gates that can be reconstructed from historical candles/tickers.
Unavailable historical context is UNKNOWN, never substituted with current data.
"""
from __future__ import annotations
from scanner.opportunity import opportunity_score


def discovery_trace(features, quote_volume_24h, discovery_min=2_000_000):
    reasons=[]
    if quote_volume_24h is None:
        reasons.append("LIQUIDITY_UNKNOWN")
    elif quote_volume_24h < discovery_min:
        reasons.append("DISCOVERY_LIQUIDITY_REJECT")
    score=opportunity_score(features)
    return {"discovered":not any(x.endswith("_REJECT") for x in reasons),
            "opportunity_score":score,"reasons":reasons}


def pipeline_row(episode, snapshot):
    d=discovery_trace(snapshot.get("features") or {},snapshot.get("quote_volume_24h"))
    return {"episode_key":episode["episode_key"],"symbol":episode["symbol"],
            "side":episode["side"],"ts":snapshot["ts"],
            "label_max_excursion_pct":episode["max_excursion_pct"],
            "discovered":d["discovered"],"opportunity_score":d["opportunity_score"],
            "gate_reasons":d["reasons"],
            "historical_context_status":snapshot.get("historical_context_status","UNKNOWN")}
