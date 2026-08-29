"""V3.3: Turev istihbarati + BTC rejim filtresi + yonlu confluence skoru."""
import numpy as np
from . import data
from . import config as C
from .indicators import analyze
from .patterns import scan_patterns, market_structure, find_pivots


def taker_pressure(df, bars=6):
    sub = df.iloc[-bars:]
    tb = sub["tbBase"].astype(float).sum() if "tbBase" in sub else None
    vol = sub["volume"].sum()
    if tb is None or not vol:
        return None
    return float(tb / vol)


def trigger_hold_count(side, trigger, a15, limit=3):
    closes = a15["closed"]["close"].iloc[-limit:]
    count = 0
    for close in reversed(closes.tolist()):
        held = close > trigger if side == "long" else close < trigger
        if not held:
            break
        count += 1
    return count


def long_short_ratios(symbol):
    out = {}
    for key, path in (("top_pos", "/topLongShortPositionRatio"),
                      ("global_acc", "/globalLongShortAccountRatio")):
        d = data.get_futures_data(path, {"symbol": symbol, "period": "1h", "limit": 2})
        try:
            out[key] = float(d[-1]["longShortRatio"])
        except (TypeError, KeyError, IndexError, ValueError):
            out[key] = None
    return out


def basis_pct(funding_obj):
    try:
        mark = float(funding_obj["markPrice"]); idx = float(funding_obj["indexPrice"])
        return (mark - idx) / idx * 100
    except (TypeError, KeyError, ValueError, ZeroDivisionError):
        return None


def spread_pct(symbol):
    d = data.get("/ticker/bookTicker", {"symbol": symbol})
    try:
        bid, ask = float(d["bidPrice"]), float(d["askPrice"])
        return (ask - bid) / bid * 100
    except (TypeError, KeyError, ValueError, ZeroDivisionError):
        return None


def btc_regime():
    k4 = data.klines("BTCUSDT", "4h", 220)
    k1 = data.klines("BTCUSDT", "1h", 240)
    if k4 is None or k1 is None:
        return {"trend": 0, "hard_break": None, "note": "BTC verisi alinamadi"}
    a4, a1 = analyze(k4), analyze(k1)
    piv1, _ = find_pivots(a1["closed"])
    struct1 = market_structure(piv1)
    hard = None
    closed = a1["closed"]; last2 = closed.iloc[-2:]
    piv4, _ = find_pivots(a4["closed"], lookback=90)
    hs4 = [p[1] for p in piv4 if p[2] == "H"][-3:]
    ls4 = [p[1] for p in piv4 if p[2] == "L"][-3:]
    atr1 = a1["atr"] or 0
    if ls4 and (last2["close"] < min(ls4) - 0.3 * atr1).any(): hard = "down"
    if hs4 and (last2["close"] > max(hs4) + 0.3 * atr1).any(): hard = "up"
    pats, _ = scan_patterns(a1["closed"], a1["atr"], a1["price"], a1["high24"], a1["low24"])
    sweep = next((p for p in pats if p["type"] == "liquidity_sweep"), None)
    note = f"BTC 4s: {a4['tlabel']}, 1s yapi: {struct1}"
    if hard: note += f", SERT {'yukari' if hard == 'up' else 'asagi'} kirilim"
    if sweep: note += f", taze {'tepe' if sweep['dir'] == 'short' else 'dip'} süpürme"
    return {"trend": a4["tscore"], "hard_break": hard,
            "sweep_dir": sweep["dir"] if sweep else None,
            "price": a1["price"], "note": note}


W = {
    "structure_4h": 2, "setup_1h": 2, "sr_confluence": 2, "trigger_15m": 2,
    "volume": 1, "derivatives": 1, "btc_regime": 1, "context_1d": 1, "secondary": 1,
}
SCORE_MAX = sum(W.values())
SCORE_ACTIVE_MIN = 9
SCORE_WATCH_MIN = 7


def confluence(side, pattern, a15, a1, a4, a1d, deriv, regime):
    parts, score = [], 0
    is_long = side == "long"

    if regime.get("hard_break") == ("down" if is_long else "up"):
        return 0, [], f"BTC ters yonde sert rejim kirilimi ({regime['note']})"
    fr = deriv.get("funding_rate")
    if fr is not None:
        try:
            f = float(fr)
            if is_long and f >= C.FUNDING_VETO or (not is_long) and f <= -C.FUNDING_VETO:
                return 0, [], f"funding asiri kalabalik ({f*100:.3f}%/8s)"
        except ValueError:
            pass
    sp = deriv.get("spread_pct")
    if sp is not None and sp > C.SPREAD_VETO_PCT:
        return 0, [], f"spread cok genis (%{sp:.3f}) — likidite sorunu"

    if (is_long and a4["tscore"] >= 1) or ((not is_long) and a4["tscore"] <= -1):
        pts, lbl = W["structure_4h"], f"4s yapı+{W['structure_4h']}"
        try:
            e20 = float(a4["closed"]["ema20"].iloc[-1])
            pullback = (is_long and a4["price"] < e20) or ((not is_long) and a4["price"] > e20)
            if pullback:
                pts, lbl = 1, "4s yapı+1 (ana trend uyumlu, düzeltme fazı)"
        except Exception:
            pass
        score += pts; parts.append(lbl)

    # V3.3: formasyonsuz structural fallback gercek setup ile ayni +2'yi alamaz.
    if pattern and pattern.get("type") != "structural":
        score += W["setup_1h"]; parts.append(f"{pattern['type']}+{W['setup_1h']}")

    trig = None
    if pattern:
        trig = pattern.get("trigger_short") if (not is_long and pattern.get("trigger_short") is not None) else pattern.get("trigger")
    if trig:
        atr4 = a4["atr"] or (trig * 0.01)
        # Yonlu S/R: LONG icin kirilan direnc/pivot-high, SHORT icin kirilan destek/pivot-low.
        directional = list(a4["pivot_highs"] if is_long else a4["pivot_lows"])
        if a1d:
            directional += list(a1d["pivot_highs"] if is_long else a1d["pivot_lows"])
        if any(abs(trig - l) <= 0.8 * atr4 for l in directional):
            score += W["sr_confluence"]; parts.append(f"yonlu S/R+{W['sr_confluence']}")

    trig15 = False
    if trig and a15["atr"]:
        needed = (C.RETEST_MIN_HOLD_CLOSES if pattern and pattern.get("type") in ("liquidity_sweep", "breakout_retest") else C.ACTIVE_MIN_HOLD_CLOSES)
        trig15 = (trigger_hold_count(side, trig, a15) >= needed and
                  a15["vol_ratio"] and a15["vol_ratio"] >= C.BREAKOUT_VOL_MULT_15M)
    if trig15:
        score += W["trigger_15m"]; parts.append(f"15d tetik+{W['trigger_15m']}")

    vol_ok = (a1["vol_ratio"] and a1["vol_ratio"] >= 1.2) or (a15["vol_ratio"] and a15["vol_ratio"] >= 1.5)
    if vol_ok:
        score += W["volume"]; parts.append(f"hacim+{W['volume']}")

    d_pts = 0
    oi1h = (deriv.get("oi") or {}).get("1h")
    if oi1h is not None and oi1h > 0.5: d_pts += 1
    tp = deriv.get("taker_1h", deriv.get("taker"))
    if tp is not None and ((is_long and tp > 0.54) or ((not is_long) and tp < 0.46)): d_pts += 1
    ratios = deriv.get("ls_ratios") or {}
    top_pos = ratios.get("top_pos"); global_acc = ratios.get("global_acc")
    if top_pos is not None and ((is_long and top_pos >= 1.05) or ((not is_long) and top_pos <= 0.95)): d_pts += 1
    crowded_accounts = (global_acc is not None and ((is_long and global_acc >= 2.2) or ((not is_long) and global_acc <= 0.45)))
    if d_pts >= 2 and not crowded_accounts:
        score += W["derivatives"]; parts.append(f"türev+{W['derivatives']}")

    bt = regime.get("trend", 0)
    if (is_long and bt >= 1) or ((not is_long) and bt <= -1):
        score += W["btc_regime"]; parts.append(f"BTC+{W['btc_regime']}")
    elif regime.get("sweep_dir") == side:
        score += W["btc_regime"]; parts.append(f"BTC süpürme uyumu+{W['btc_regime']}")

    if a1d and ((is_long and a1d["tscore"] >= 1) or ((not is_long) and a1d["tscore"] <= -1)):
        score += W["context_1d"]; parts.append(f"1G+{W['context_1d']}")

    sec = 0
    r1 = a1["rsi"]
    div = a1.get("rsi_divergence") or a15.get("rsi_divergence")
    if (is_long and 45 <= r1 <= 70) or ((not is_long) and 30 <= r1 <= 55): sec = 1
    if (is_long and div == "bullish") or ((not is_long) and div == "bearish"):
        sec = 1; parts.append("RSI divergence")
    b = deriv.get("basis_pct")
    if b is not None and abs(b) > 0.6: sec = 0
    if sec:
        score += W["secondary"]; parts.append(f"RSI+{W['secondary']}")

    return score, parts, None
