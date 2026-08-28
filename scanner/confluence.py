"""V3: Turev istihbarati + BTC rejim filtresi + agirlikli confluence skoru."""
import numpy as np
from . import data
from . import config as C
from .indicators import analyze
from .patterns import scan_patterns, market_structure, find_pivots


# ================= TUREV KATMANI =================
def taker_pressure(df, bars=6):
    """Son N mumda taker alis orani. >0.55 alici baskisi, <0.45 satici baskisi."""
    sub = df.iloc[-bars:]
    tb = sub["tbBase"].astype(float).sum() if "tbBase" in sub else None
    vol = sub["volume"].sum()
    if tb is None or not vol:
        return None
    return float(tb / vol)


def long_short_ratios(symbol):
    """Top trader pozisyon orani + global hesap orani (period=1h, son deger)."""
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
    """Mark vs index premium (%)."""
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


# ================= BTC REJIM FILTRESI =================
def btc_regime():
    """Tur basina 1 kez: BTC 4h trend + 1h taze sert kirilim var mi?
    Donus: {"trend": -2..2, "hard_break": "up"|"down"|None, "note": str}
    """
    k4 = data.klines("BTCUSDT", "4h", 220)
    k1 = data.klines("BTCUSDT", "1h", 240)
    if k4 is None or k1 is None:
        return {"trend": 0, "hard_break": None, "note": "BTC verisi alinamadi"}
    a4, a1 = analyze(k4), analyze(k1)
    piv1, _ = find_pivots(a1["closed"])
    struct1 = market_structure(piv1)

    hard = None
    closed = a1["closed"]
    last2 = closed.iloc[-2:]
    # 4h onemli pivotlarin taze 1h kirilimi
    piv4, _ = find_pivots(a4["closed"], lookback=90)
    hs4 = [p[1] for p in piv4 if p[2] == "H"][-3:]
    ls4 = [p[1] for p in piv4 if p[2] == "L"][-3:]
    atr1 = a1["atr"] or 0
    if ls4 and (last2["close"] < min(ls4) - 0.3 * atr1).any():
        hard = "down"
    if hs4 and (last2["close"] > max(hs4) + 0.3 * atr1).any():
        hard = "up"

    # taze sweep tespiti (piyasa geneli sahte kirilim uyarisi)
    pats, _ = scan_patterns(a1["closed"], a1["atr"], a1["price"], a1["high24"], a1["low24"])
    sweep = next((p for p in pats if p["type"] == "liquidity_sweep"), None)

    note = f"BTC 4s: {a4['tlabel']}, 1s yapi: {struct1}"
    if hard:
        note += f", SERT {'yukari' if hard == 'up' else 'asagi'} kirilim"
    if sweep:
        note += f", taze {'tepe' if sweep['dir'] == 'short' else 'dip'} süpürme"
    return {"trend": a4["tscore"], "hard_break": hard,
            "sweep_dir": sweep["dir"] if sweep else None,
            "price": a1["price"], "note": note}


# ================= CONFLUENCE SKORU =================
# Agirliklar (kullanici onayli): yapi/tetik/SR/RR yuksek, RSI-MACD dusuk
W = {
    "structure_4h": 2, "setup_1h": 2, "sr_confluence": 2, "trigger_15m": 2,
    "volume": 1, "derivatives": 1, "btc_regime": 1, "context_1d": 1, "secondary": 1,
}
SCORE_MAX = sum(W.values())          # 13
SCORE_ACTIVE_MIN = 9
SCORE_WATCH_MIN = 7


def confluence(side, pattern, a15, a1, a4, a1d, deriv, regime):
    """(skor, dokum_listesi, veto_sebebi|None) doner. Vetolar skor ustudur."""
    parts, score = [], 0
    is_long = side == "long"

    # --- ZORUNLU VETOLAR ---
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

    # --- PUANLAR ---
    if (is_long and a4["tscore"] >= 1) or ((not is_long) and a4["tscore"] <= -1):
        score += W["structure_4h"]; parts.append(f"4s yapı+{W['structure_4h']}")
    if pattern:
        score += W["setup_1h"]; parts.append(f"{pattern['type']}+{W['setup_1h']}")

    # S/R confluence: tetik seviyesi 4h veya 1D pivot kumesine yakin mi
    trig = None
    if pattern:
        trig = pattern.get("trigger_short") if (not is_long and pattern.get("trigger_short") is not None) else pattern.get("trigger")
    if trig:
        lvls = a4["pivot_highs"] + a4["pivot_lows"]
        if a1d:
            lvls += a1d["pivot_highs"] + a1d["pivot_lows"]
        atr4 = a4["atr"] or (trig * 0.01)
        if any(abs(trig - l) <= 0.8 * atr4 for l in lvls):
            score += W["sr_confluence"]; parts.append(f"S/R+{W['sr_confluence']}")

    # 15m tetik: taze kirilim + hacim
    trig15 = False
    if trig and a15["atr"]:
        c15 = a15["closed"].iloc[-3:]
        if is_long:
            trig15 = (c15["close"] > trig).any() and a15["vol_ratio"] and a15["vol_ratio"] >= C.BREAKOUT_VOL_MULT_15M
        else:
            trig15 = (c15["close"] < trig).any() and a15["vol_ratio"] and a15["vol_ratio"] >= C.BREAKOUT_VOL_MULT_15M
    if trig15:
        score += W["trigger_15m"]; parts.append(f"15d tetik+{W['trigger_15m']}")

    vol_ok = (a1["vol_ratio"] and a1["vol_ratio"] >= 1.2) or \
             (a15["vol_ratio"] and a15["vol_ratio"] >= 1.5)
    if vol_ok:
        score += W["volume"]; parts.append(f"hacim+{W['volume']}")

    # turev destegi: OI artisi + taker baskisi + top trader pozisyon uyumu.
    # Global hesap orani asiri kalabaliksa turev puani verilmez (veto degil).
    d_pts = 0
    oi1h = (deriv.get("oi") or {}).get("1h")
    if oi1h is not None and oi1h > 0.5:
        d_pts += 1
    tp = deriv.get("taker")
    if tp is not None and ((is_long and tp > 0.54) or ((not is_long) and tp < 0.46)):
        d_pts += 1
    ratios = deriv.get("ls_ratios") or {}
    top_pos = ratios.get("top_pos")
    global_acc = ratios.get("global_acc")
    if top_pos is not None and ((is_long and top_pos >= 1.05) or ((not is_long) and top_pos <= 0.95)):
        d_pts += 1
    crowded_accounts = (global_acc is not None and
                        ((is_long and global_acc >= 2.2) or ((not is_long) and global_acc <= 0.45)))
    if d_pts >= 2 and not crowded_accounts:
        score += W["derivatives"]; parts.append(f"türev+{W['derivatives']}")

    # BTC rejimi uyumu (veto degilse)
    bt = regime.get("trend", 0)
    if (is_long and bt >= 1) or ((not is_long) and bt <= -1):
        score += W["btc_regime"]; parts.append(f"BTC+{W['btc_regime']}")
    elif regime.get("sweep_dir") == side:
        score += W["btc_regime"]; parts.append(f"BTC süpürme uyumu+{W['btc_regime']}")

    # 1D baglam
    if a1d and ((is_long and a1d["tscore"] >= 1) or ((not is_long) and a1d["tscore"] <= -1)):
        score += W["context_1d"]; parts.append(f"1G+{W['context_1d']}")

    # ikincil: RSI bolgesi + basis asiri degil
    sec = 0
    r1 = a1["rsi"]
    if (is_long and 45 <= r1 <= 70) or ((not is_long) and 30 <= r1 <= 55):
        sec = 1
    b = deriv.get("basis_pct")
    if b is not None and abs(b) > 0.6:
        sec = 0    # asiri premium/discount ikincil puani goturur
    if sec:
        score += W["secondary"]; parts.append(f"RSI+{W['secondary']}")

    return score, parts, None
