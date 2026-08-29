"""Live, read-only DOTUSDT QA harness for V3.3.

No Telegram, no state writes, no orders. Reads Binance Futures public data and
prints the raw decision context plus the engine result.
"""
import json

from scanner import data
from scanner.confluence import btc_regime
from scanner.decision import decision_summary, build_flip_plan
from scanner.main import _market_data, _build_ctx
import scanner.main as main
from scanner.engine_v3 import evaluate_v3
from scanner.patterns import scan_patterns


def slim_zone(z):
    if not z:
        return None
    return {"level": round(float(z["level"]), 8), "evidence": z.get("evidence"),
            "members": [round(float(x), 8) for x in z.get("members", [])]}


def main_run():
    sym = "DOTUSDT"
    tickers = data.ticker_24h()
    if tickers is None:
        raise SystemExit("ticker_24h unavailable")
    row = tickers[tickers["symbol"] == sym]
    if row.empty:
        raise SystemExit("DOTUSDT ticker missing")
    main.CHANGE_24H = {sym: float(row.iloc[0]["priceChangePercent"])}

    md = _market_data(sym, need_4h=True)
    if not md:
        raise SystemExit("market data unavailable")
    a15, a1h, a4h = md
    regime = btc_regime()
    ctx = _build_ctx(sym, a15, a1h)
    dec = decision_summary(a15, a1h, a4h, ctx.get("a1d"), regime, ctx)
    patterns, structure = scan_patterns(a1h["closed"], a1h["atr"], a1h["price"],
                                        a1h["high24"], a1h["low24"])
    result = evaluate_v3(sym, a15, a1h, a4h, regime, _build_ctx)

    primary_side = None
    if isinstance(result, dict):
        primary_side = result.get("side", "").lower()
    elif dec.get("bias") in ("LONG", "SHORT"):
        primary_side = dec["bias"].lower()
    flip = build_flip_plan(primary_side, a15["price"], a15, a1h, a4h, dec) if primary_side else None

    out = {
        "symbol": sym,
        "price": a15["price"],
        "change_24h": main.CHANGE_24H[sym],
        "timeframes": {
            "15m": {"rsi": a15["rsi"], "vol_ratio": a15["vol_ratio"], "trend": a15["tlabel"],
                    "rsi_divergence": a15.get("rsi_divergence")},
            "1h": {"rsi": a1h["rsi"], "vol_ratio": a1h["vol_ratio"], "trend": a1h["tlabel"],
                   "ema50": a1h.get("ema50"), "ema100": a1h.get("ema100"), "ema200": a1h.get("ema200"),
                   "rsi_divergence": a1h.get("rsi_divergence")},
            "4h": {"rsi": a4h["rsi"], "vol_ratio": a4h["vol_ratio"], "trend": a4h["tlabel"],
                   "ema50": a4h.get("ema50"), "ema100": a4h.get("ema100"), "ema200": a4h.get("ema200"),
                   "rsi_divergence": a4h.get("rsi_divergence"), "fib": a4h.get("fib")},
            "1d": ({"rsi": ctx["a1d"]["rsi"], "trend": ctx["a1d"]["tlabel"],
                    "ema50": ctx["a1d"].get("ema50"), "ema100": ctx["a1d"].get("ema100"),
                    "ema200": ctx["a1d"].get("ema200"), "fib": ctx["a1d"].get("fib")}
                   if ctx.get("a1d") else None),
        },
        "btc_regime": regime,
        "derivatives": {k: ctx.get(k) for k in ("funding_rate", "oi", "taker_15m", "taker_1h",
                                                  "ls_ratios", "basis_pct", "spread_pct")},
        "structure_1h": structure,
        "patterns_1h": [{k: p.get(k) for k in ("type", "dir", "state", "trigger", "trigger_short", "invalid", "quality", "note")}
                        for p in patterns],
        "decision": {
            "bias": dec["bias"], "strength": dec["strength"],
            "long_advantage": dec["long_advantage"], "short_advantage": dec["short_advantage"],
            "long_edge": dec["long_edge"], "short_edge": dec["short_edge"],
            "long_reasons": dec["long_reasons"], "short_reasons": dec["short_reasons"],
            "support": slim_zone(dec["zones"].get("support")),
            "resistance": slim_zone(dec["zones"].get("resistance")),
            "tolerance": dec["zones"].get("tolerance"),
        },
        "engine_result": result,
        "alternate_flip_plan": flip,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main_run()
