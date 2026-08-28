"""V3 motoru — formasyon + confluence katmani, kanitlanmis V2 cekirdeginin ustunde.

Akis:
  1. 1s kapali mumlarda 8 detektor calisir
  2. Formasyon adaylari + (formasyon yoksa) V2 yapisal yol
  3. Aday varsa baglam cekilir (funding, OI, taker, L/S, spread, basis, 1G)
  4. Agirlikli confluence skoru + zorunlu vetolar
  5. ACTIVE >= 9/13 ve 15d tetik sart; EARLY/WATCH >= 7/13
"""
from . import config as C
from .engine import (_fmt_side, _risk_pct, _targets, _planned_levels,
                     _funding_bias, evaluate as evaluate_v2)
from .patterns import scan_patterns, DETECTORS_TR
from .confluence import confluence, SCORE_MAX, SCORE_ACTIVE_MIN, SCORE_WATCH_MIN


def _pattern_levels(side, pattern, a15, a1h, a4h):
    """Formasyonun kendi invalid seviyesinden SL; yapisal pivotlardan TP."""
    atr1 = a1h["atr"]
    trigger = pattern["trigger"]
    if side == "short" and pattern.get("trigger_short"):
        trigger = pattern["trigger_short"]
    inv = pattern["invalid"]
    sl = inv - 0.15 * atr1 if side == "long" else inv + 0.15 * atr1
    entry = trigger
    rp = _risk_pct(entry, sl)
    if not (C.MIN_RISK_PCT <= rp <= C.MAX_RISK_PCT):
        # formasyon invalid'i cok genis/dar -> V2 swing yontemine dus
        plan = _planned_levels(side, trigger, a15, a1h, a4h)
        return plan, trigger
    risk = abs(entry - sl)
    tp1, tp2, tp3 = _targets(
        side, entry, risk,
        a15["pivot_highs" if side == "long" else "pivot_lows"],
        a1h["pivot_highs" if side == "long" else "pivot_lows"],
        a4h["pivot_highs" if side == "long" else "pivot_lows"])
    if tp2 is None:
        return None, trigger
    rr2 = abs(tp2 - entry) / risk
    if rr2 < C.MIN_RR_TP2:
        return None, trigger
    return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "risk_pct": rp, "rr2": rr2, "rr3": abs(tp3 - entry) / risk}, trigger


def _fresh_1h(side, trigger, a1h, pattern_type):
    """Tetik son 2 kapali 1s mumda mi gecildi? (sweep/retest yapisal olarak taze)"""
    if pattern_type in ("liquidity_sweep", "breakout_retest"):
        return True
    c1 = a1h["closed"]
    recent = c1.iloc[-C.FRESH_BREAK_BARS_1H:]
    older = c1.iloc[-(C.FRESH_BREAK_BARS_1H + 6):-C.FRESH_BREAK_BARS_1H]
    if side == "long":
        return (recent["close"] > trigger).any() and (older["close"] <= trigger).all()
    return (recent["close"] < trigger).any() and (older["close"] >= trigger).all()


def _candidate_from_pattern(pattern, a15, a1h, a4h):
    """Formasyondan asama adayi uret (skor/veto haric)."""
    side = pattern["dir"]
    if side is None:                       # simetrik ucgen: yon 4s'ten
        if a4h["tscore"] >= 1:
            side = "long"
        elif a4h["tscore"] <= -1:
            side = "short"
        else:
            return None
    # 4s kapisi
    if side == "long" and a4h["tscore"] < 1:
        return None
    if side == "short" and a4h["tscore"] > -1:
        return None
    # dikey harekete atlama
    if a1h["stretch"] is not None and a1h["stretch"] > C.ATR_STRETCH_MAX:
        return None

    plan, trigger = _pattern_levels(side, pattern, a15, a1h, a4h)
    if not plan:
        return None
    price = a15["price"]

    if pattern["state"] == "triggered":
        if not _fresh_1h(side, trigger, a1h, pattern["type"]):
            return None                    # bayat kirilim
        run = ((price - trigger) / trigger * 100 if side == "long"
               else (trigger - price) / trigger * 100)
        if run > C.ACTIVE_MAX_RUN_PCT:
            return None                    # kacti -> sessizlik
        risk_live = abs(price - plan["sl"])
        rr2_live = abs(plan["tp2"] - price) / risk_live if risk_live else 0
        if rr2_live < C.MIN_RR_TP2:
            return None
        return {"stage": "ACTIVE", "side": side, "pattern": pattern,
                "trigger": trigger, "plan": plan, "rr2_live": rr2_live}

    dist = abs(trigger - price) / price * 100
    if dist > C.EARLY_PROXIMITY_PCT:
        return None
    stage = "WATCH" if dist <= C.WATCH_PROXIMITY_PCT else "EARLY"
    return {"stage": stage, "side": side, "pattern": pattern,
            "trigger": trigger, "plan": plan, "dist": dist}


def evaluate_v3(sym, a15, a1h, a4h, regime, ctx_fn):
    """Ana giris. ctx_fn(sym, a1h): baglam sozlugu doner (lazy API cagrilari).
    Donus: sinyal sozlugu | None. Veto durumunda ("__veto__", sebep) doner.
    """
    if not a1h["atr"] or len(a1h["closed"]) < 60 or len(a15["closed"]) < 80:
        return None

    patterns, struct1 = scan_patterns(a1h["closed"], a1h["atr"], a1h["price"],
                                      a1h["high24"], a1h["low24"])
    cands = []
    for p in patterns:
        c = _candidate_from_pattern(p, a15, a1h, a4h)
        if c:
            cands.append(c)
    order = {"ACTIVE": 2, "WATCH": 1, "EARLY": 0}
    cands.sort(key=lambda c: (order[c["stage"]], c["pattern"]["quality"]), reverse=True)

    if not cands:
        # formasyon yok -> V2 yapisal yol (dusuk oncelik, "structural" etiketi)
        v2 = evaluate_v2(sym, a15, a1h, a4h, None, None)
        if not v2:
            return None
        fake_pat = {"type": "structural", "trigger": v2["trigger"],
                    "invalid": v2["sl"], "quality": 0.5,
                    "state": "triggered" if v2["status"] == "ACTIVE" else "forming",
                    "note": "yapisal seviye (formasyonsuz)", "dir": v2["side"].lower()}
        ctx = ctx_fn(sym, a1h)
        score, parts, veto = confluence(v2["side"].lower(), fake_pat,
                                        a15, a1h, a4h, ctx.get("a1d"), ctx, regime)
        need = SCORE_ACTIVE_MIN if v2["status"] == "ACTIVE" else SCORE_WATCH_MIN
        if veto:
            return ("__veto__", veto)
        if score < need:
            return None
        v2.update({"setup_type": "structural", "setup_note": "yapisal kirilim/retest",
                   "score": score, "score_max": SCORE_MAX, "score_parts": parts,
                   "structure_1h": struct1, "regime_note": regime.get("note", "")})
        _merge_ctx(v2, v2["side"].lower(), ctx)
        return v2

    best = cands[0]
    side, pat, plan = best["side"], best["pattern"], best["plan"]
    ctx = ctx_fn(sym, a1h)
    score, parts, veto = confluence(side, pat, a15, a1h, a4h,
                                    ctx.get("a1d"), ctx, regime)
    if veto:
        return ("__veto__", veto)
    need = SCORE_ACTIVE_MIN if best["stage"] == "ACTIVE" else SCORE_WATCH_MIN
    if score < need:
        return None
    if best["stage"] == "ACTIVE" and not any(p.startswith("15d tetik") for p in parts):
        # ACTIVE icin 15d teyidi zorunlu; yoksa tetik yakinindaysa WATCH'a dusur
        dist = abs(best["trigger"] - a15["price"]) / a15["price"] * 100
        if dist <= C.WATCH_PROXIMITY_PCT:
            best["stage"] = "WATCH"
        else:
            return None

    price = a15["price"]
    trigger = best["trigger"]
    if side == "long":
        alarm = trigger * (1 - C.EARLY_ALERT_PRICE_BUFFER_PCT / 100)
        e_lo, e_hi = trigger * 0.998, trigger * 1.004
    else:
        alarm = trigger * (1 + C.EARLY_ALERT_PRICE_BUFFER_PCT / 100)
        e_lo, e_hi = trigger * 1.000, trigger * 1.002
    if best["stage"] == "ACTIVE":
        e_lo, e_hi = min(price, trigger), max(price, trigger)

    sig = {
        "status": best["stage"], "side": _fmt_side(side), "price": price,
        "trigger": trigger, "alarm": alarm,
        "dist_pct": best.get("dist", 0.0),
        "invalidation": plan["sl"], "sl": plan["sl"],
        "entry_lo": e_lo, "entry_hi": e_hi,
        "tp1": plan["tp1"], "tp2": plan["tp2"], "tp3": plan["tp3"],
        "rr2": best.get("rr2_live", plan["rr2"]), "rr3": plan["rr3"],
        "risk_pct": plan["risk_pct"],
        "rsi15": a15["rsi"], "rsi1h": a1h["rsi"],
        "trend1h": a1h["tlabel"], "trend4h": a4h["tlabel"],
        "vol15_ratio": a15["vol_ratio"], "vol1h_ratio": a1h["vol_ratio"],
        "setup_type": pat["type"],
        "setup_note": pat["note"],
        "score": score, "score_max": SCORE_MAX, "score_parts": parts,
        "structure_1h": struct1, "regime_note": regime.get("note", ""),
    }
    _merge_ctx(sig, side, ctx)
    return sig


def _merge_ctx(sig, side, ctx):
    sig["funding"] = ctx.get("funding_rate")
    sig["funding_bias"] = _funding_bias(side, ctx.get("funding_rate"))
    sig["oi"] = ctx.get("oi") or {}
    sig["taker"] = ctx.get("taker")
    sig["ls_ratios"] = ctx.get("ls_ratios") or {}
    sig["basis_pct"] = ctx.get("basis_pct")
    sig["spread_pct"] = ctx.get("spread_pct")
    sig["trend1d"] = ctx["a1d"]["tlabel"] if ctx.get("a1d") else None
