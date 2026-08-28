"""V3.2 motoru — confluence skoru + bagimsiz ACTIVE execution veto katmani.

Akis:
  1. 1s kapali mumlarda 8 detektor calisir
  2. Formasyon adaylari + (formasyon yoksa) V2 yapisal yol
  3. Aday varsa baglam cekilir (funding, OI, taker, L/S, spread, basis, 1G)
  4. Agirlikli confluence skoru + zorunlu vetolar
  5. ACTIVE >= 9/13, 15d tetik ve execution kapilari; EARLY/WATCH >= 7/13
"""
from . import config as C
from .engine import (_fmt_side, _risk_pct, _targets, _planned_levels,
                     _funding_bias, evaluate as evaluate_v2)
from .patterns import scan_patterns, DETECTORS_TR
from .confluence import (confluence, trigger_hold_count, SCORE_MAX,
                         SCORE_ACTIVE_MIN, SCORE_WATCH_MIN)


REVERSAL_SETUPS = {
    "liquidity_sweep", "breakout_retest", "double_top", "double_bottom",
    "trendline_break", "rising_wedge", "falling_wedge",
}
CONTINUATION_SETUPS = {"flag", "asc_triangle", "desc_triangle", "sym_triangle"}


def _rr_set(ref, sl, tp1, tp2, tp3):
    """Tum R:R degerlerini AYNI referans fiyattan hesapla (tutarlilik)."""
    risk = abs(ref - sl)
    if not risk:
        return None
    f = lambda tp: (abs(tp - ref) / risk) if tp else None
    return f(tp1), f(tp2), f(tp3)


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


def _trend_flags(side, pattern_type, a4h):
    aligned = ((side == "long" and a4h["tscore"] >= 1) or
               (side == "short" and a4h["tscore"] <= -1))
    opposed = ((side == "long" and a4h["tscore"] <= -1) or
               (side == "short" and a4h["tscore"] >= 1))
    reversal = opposed and pattern_type in REVERSAL_SETUPS
    if pattern_type in CONTINUATION_SETUPS:
        return aligned, False
    return aligned or reversal or a4h["tscore"] == 0, reversal


def _first_obstacle_r(side, price, risk, a15, a1h, a4h):
    levels = []
    key = "pivot_highs" if side == "long" else "pivot_lows"
    for analysis in (a15, a1h, a4h):
        levels.extend(analysis.get(key) or [])
    if side == "long":
        ahead = [x for x in levels if x > price]
        obstacle = min(ahead) if ahead else None
        reward = obstacle - price if obstacle is not None else None
    else:
        ahead = [x for x in levels if x < price]
        obstacle = max(ahead) if ahead else None
        reward = price - obstacle if obstacle is not None else None
    return ((reward / risk) if obstacle is not None and risk > 0 else None,
            obstacle)


def _execution_veto(side, pattern, plan, a15, a1h, a4h, ctx):
    """ACTIVE'e ozel, skordan bagimsiz execution kapilari.

    Donus: (veto_sebebi|None, quality, checks). Quality yalnizca butun zorunlu
    kapilar gecildiginde aday siralamasi icin kullanilir.
    """
    trigger = (pattern.get("trigger_short") if side == "short" and
               pattern.get("trigger_short") is not None else pattern["trigger"])
    price = float(a15["price"])
    closed = a15["closed"]
    last = closed.iloc[-1]
    hold_needed = (C.RETEST_MIN_HOLD_CLOSES if pattern["type"] in
                   ("liquidity_sweep", "breakout_retest") else
                   C.ACTIVE_MIN_HOLD_CLOSES)
    holds = trigger_hold_count(side, trigger, a15)
    if holds < hold_needed:
        return f"15d failed reclaim/hold ({holds}/{hold_needed} kapanis)", 0, []
    if (side == "long" and price <= trigger) or (side == "short" and price >= trigger):
        return "canli fiyat reclaim/breakdown seviyesini kaybetti", 0, []

    ema20 = float(last["ema20"])
    ma7 = float(last["ma7"] if "ma7" in closed else closed["close"].rolling(7).mean().iloc[-1])
    ema_prev = float(closed["ema20"].iloc[-4]) if len(closed) >= 4 else ema20
    close = float(last["close"])
    trend15_ok = ((close > ema20 and close > ma7 and ma7 >= ema20 and ema20 > ema_prev)
                  if side == "long" else
                  (close < ema20 and close < ma7 and ma7 <= ema20 and ema20 < ema_prev))
    if not trend15_ok:
        return "15d EMA20/MA7 yonu veya EMA20 egimi uyumsuz", 0, []

    vol1h = a1h.get("vol_ratio")
    if vol1h is None or vol1h != vol1h or vol1h < C.ACTIVE_MIN_VOL_RATIO_1H:
        return f"1s hacim yetersiz ({vol1h if vol1h is not None else '-'}x)", 0, []

    allowed, reversal = _trend_flags(side, pattern["type"], a4h)
    if not allowed:
        return "continuation setup 4s trendiyle uyumsuz", 0, []
    taker15 = ctx.get("taker_15m")
    taker1h = ctx.get("taker_1h")
    if reversal:
        taker_ok = (taker15 is not None and
                    (taker15 >= C.REVERSAL_TAKER_LONG_15M if side == "long"
                     else taker15 <= C.REVERSAL_TAKER_SHORT_15M))
        if not taker_ok:
            return "reversal icin 15d taker teyidi yok", 0, []

    move24 = ctx.get("change_24h")
    hard_against = (move24 is not None and
                    ((side == "long" and move24 <= -C.HARD_MOVE_24H_PCT) or
                     (side == "short" and move24 >= C.HARD_MOVE_24H_PCT)))
    if reversal and hard_against:
        panic_taker_ok = (taker15 is not None and
                          (taker15 >= C.PANIC_TAKER_LONG_15M if side == "long"
                           else taker15 <= C.PANIC_TAKER_SHORT_15M))
        if vol1h < C.REVERSAL_HARD_MOVE_MIN_VOL_1H or not panic_taker_ok:
            return "sert 24s harekete ters reversal hacim/taker teyitsiz", 0, []

    oi = ctx.get("oi") or {}
    oi_collapse = (oi.get("4h") is not None and oi.get("24h") is not None and
                   oi["4h"] <= C.OI_COLLAPSE_4H_PCT and
                   oi["24h"] <= C.OI_COLLAPSE_24H_PCT)
    if reversal and side == "long" and oi_collapse and (
            taker15 is None or taker15 < C.PANIC_TAKER_LONG_15M):
        return "OI 4s/24s cokusu guclu 15d taker donusu olmadan reversal LONG'u veto etti", 0, []

    risk = abs(price - float(plan["sl"]))
    risk_pct = risk / price * 100 if price else float("inf")
    if risk_pct > C.ACTIVE_MAX_LIVE_RISK_PCT:
        return f"canli stop riski %{risk_pct:.2f} > %{C.ACTIVE_MAX_LIVE_RISK_PCT:.1f}", 0, []
    obstacle_r, obstacle = _first_obstacle_r(side, price, risk, a15, a1h, a4h)
    if obstacle_r is not None and obstacle_r < C.ACTIVE_MIN_OBSTACLE_R:
        return f"ilk yapisal engel {obstacle_r:.2f}R (<{C.ACTIVE_MIN_OBSTACLE_R:.1f}R)", 0, []

    taker_aligned = (taker15 is not None and
                     (taker15 >= 0.50 if side == "long" else taker15 <= 0.50))
    quality = min(2, holds) + min(1.5, float(vol1h)) + (1 if taker_aligned else 0)
    quality += max(0, 1 - risk_pct / C.ACTIVE_MAX_LIVE_RISK_PCT)
    checks = [f"hold={holds}", f"vol1h={vol1h:.2f}",
              f"taker15={taker15:.3f}" if taker15 is not None else "taker15=-",
              f"taker1h={taker1h:.3f}" if taker1h is not None else "taker1h=-",
              f"risk={risk_pct:.2f}%"]
    if obstacle is not None:
        checks.append(f"obstacle={obstacle:.6g}/{obstacle_r:.2f}R")
    return None, round(quality, 3), checks


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
    # Reversal setup'lar karsi 4s etiketinde otomatik elenmez; continuation
    # setup'larinda trend uyumu zorunlu kalir.
    allowed, _ = _trend_flags(side, pattern["type"], a4h)
    if not allowed:
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
    """Ana giris. ctx_fn(sym, a15, a1h): baglam sozlugu doner (lazy API cagrilari).
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
    if not cands:
        # formasyon yok -> V2 yapisal yol (dusuk oncelik, "structural" etiketi)
        v2 = evaluate_v2(sym, a15, a1h, a4h, None, None)
        if not v2:
            return None
        fake_pat = {"type": "structural", "trigger": v2["trigger"],
                    "invalid": v2["sl"], "quality": 0.5,
                    "state": "triggered" if v2["status"] == "ACTIVE" else "forming",
                    "note": "yapisal seviye (formasyonsuz)", "dir": v2["side"].lower()}
        ctx = ctx_fn(sym, a15, a1h)
        score, parts, veto = confluence(v2["side"].lower(), fake_pat,
                                        a15, a1h, a4h, ctx.get("a1d"), ctx, regime)
        need = SCORE_ACTIVE_MIN if v2["status"] == "ACTIVE" else SCORE_WATCH_MIN
        if veto:
            return ("__veto__", veto)
        if score < need:
            return None
        execution_quality, execution_checks = 0, []
        if v2["status"] == "ACTIVE":
            plan = {"sl": v2["sl"]}
            veto, execution_quality, execution_checks = _execution_veto(
                v2["side"].lower(), fake_pat, plan, a15, a1h, a4h, ctx)
            if veto:
                return ("__veto__", veto)
            if not any(p.startswith("15d tetik") for p in parts):
                return ("__veto__", "15d trigger hacmi teyitsiz")
        ref = v2["price"] if v2["status"] == "ACTIVE" else v2["trigger"]
        rrs = _rr_set(ref, v2["sl"], v2.get("tp1"), v2.get("tp2"), v2.get("tp3"))
        if rrs:
            v2["rr1"], v2["rr2"], v2["rr3"] = rrs
            v2["rr_ref"] = ref
        v2.update({"setup_type": "structural", "setup_note": "yapisal kirilim/retest",
                   "score": score, "score_max": SCORE_MAX, "score_parts": parts,
                   "execution_quality": execution_quality,
                   "execution_checks": execution_checks,
                   "engine_version": C.ENGINE_VERSION,
                   "structure_1h": struct1, "regime_note": regime.get("note", "")})
        _merge_ctx(v2, v2["side"].lower(), ctx)
        return v2

    # Tum adaylar ayni turev baglamiyla ayri ayri skorlanir. Stage, confluence
    # ve execution quality birlikte siralanir; pattern kalitesi son tie-break'tir.
    ctx = ctx_fn(sym, a15, a1h)
    eligible, vetoes = [], []
    for cand in cands:
        side, pat, plan = cand["side"], cand["pattern"], cand["plan"]
        score, parts, veto = confluence(side, pat, a15, a1h, a4h,
                                        ctx.get("a1d"), ctx, regime)
        if veto:
            vetoes.append(veto)
            continue
        need = SCORE_ACTIVE_MIN if cand["stage"] == "ACTIVE" else SCORE_WATCH_MIN
        if score < need:
            continue
        execution_quality, execution_checks = 0, []
        if cand["stage"] == "ACTIVE":
            veto, execution_quality, execution_checks = _execution_veto(
                side, pat, plan, a15, a1h, a4h, ctx)
            if veto:
                vetoes.append(veto)
                continue
            if not any(p.startswith("15d tetik") for p in parts):
                vetoes.append("15d trigger hacmi teyitsiz")
                continue
        cand.update({"score": score, "parts": parts,
                     "execution_quality": execution_quality,
                     "execution_checks": execution_checks})
        eligible.append(cand)

    if not eligible:
        return ("__veto__", vetoes[0]) if vetoes else None

    order = {"ACTIVE": 2, "WATCH": 1, "EARLY": 0}
    eligible.sort(key=lambda c: (order[c["stage"]], c["score"],
                                 c["execution_quality"], c["pattern"]["quality"]),
                  reverse=True)
    active = [c for c in eligible if c["stage"] == "ACTIVE"]
    if active:
        leader = active[0]
        opposed = [c for c in active if c["side"] != leader["side"] and
                   c["score"] >= leader["score"] - C.ACTIVE_CONFLICT_SCORE_GAP]
        if opposed:
            return ("__veto__", "zit yonlu ACTIVE adaylar yakin skorda")

    best = eligible[0]
    side, pat, plan = best["side"], best["pattern"], best["plan"]
    score, parts = best["score"], best["parts"]
    if best["stage"] == "ACTIVE" and not any(p.startswith("15d tetik") for p in parts):
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
        "rr1": None, "rr2": None, "rr3": None, "rr_ref": None,
        "risk_pct": (abs(price - plan["sl"]) / price * 100
                     if best["stage"] == "ACTIVE" else plan["risk_pct"]),
        "rsi15": a15["rsi"], "rsi1h": a1h["rsi"],
        "trend1h": a1h["tlabel"], "trend4h": a4h["tlabel"],
        "vol15_ratio": a15["vol_ratio"], "vol1h_ratio": a1h["vol_ratio"],
        "setup_type": pat["type"],
        "setup_note": pat["note"],
        "score": score, "score_max": SCORE_MAX, "score_parts": parts,
        "execution_quality": best["execution_quality"],
        "execution_checks": best["execution_checks"],
        "engine_version": C.ENGINE_VERSION,
        "structure_1h": struct1, "regime_note": regime.get("note", ""),
    }
    ref = price if best["stage"] == "ACTIVE" else trigger
    rrs = _rr_set(ref, plan["sl"], plan["tp1"], plan["tp2"], plan["tp3"])
    if not rrs or (rrs[1] is not None and rrs[1] < C.MIN_RR_TP2 and best["stage"] == "ACTIVE"):
        return None
    sig["rr1"], sig["rr2"], sig["rr3"] = rrs
    sig["rr_ref"] = ref
    _merge_ctx(sig, side, ctx)
    return sig


def _merge_ctx(sig, side, ctx):
    sig["funding"] = ctx.get("funding_rate")
    sig["funding_bias"] = _funding_bias(side, ctx.get("funding_rate"))
    sig["oi"] = ctx.get("oi") or {}
    sig["taker_15m"] = ctx.get("taker_15m")
    sig["taker_1h"] = ctx.get("taker_1h", ctx.get("taker"))
    sig["taker"] = sig["taker_1h"]  # V3.1 state okuyuculari icin uyumluluk
    sig["change_24h"] = ctx.get("change_24h")
    sig["ls_ratios"] = ctx.get("ls_ratios") or {}
    sig["basis_pct"] = ctx.get("basis_pct")
    sig["spread_pct"] = ctx.get("spread_pct")
    sig["trend1d"] = ctx["a1d"]["tlabel"] if ctx.get("a1d") else None
