"""Kripto Tarayici V2 sinyal motoru.

Hiyerarsi:
  4s = ana yon
  1s = setup / yapisal tetik
  15d = giris zamanlamasi ve hacim teyidi

Uretimler:
  EARLY  -> ERKEN UYARI / emir hazirligi
  WATCH  -> YAKIN TAKIP
  ACTIVE -> ISLEM BOLGESI AKTIF

Fiyat ideal girisi gecmisse motor None dondurur; kullaniciya "kacti" mesaji uretilmez.
"""
from . import config as C


def _fmt_side(side):
    return "LONG" if side == "long" else "SHORT"


def _risk_pct(entry, sl):
    return abs(entry - sl) / entry * 100


def _targets(side, entry, risk, piv_15m, piv_1h, piv_4h, min_sep_r=0.0):
    """Yapisal pivotlardan tekil ve yon boyunca ilerleyen TP zinciri sec.

    V3.3: TP1 sentetik uretilmez. Ilk gercek yapisal hedef en az MIN_RR_TP1
    uzakta degilse islem geometrisi riske degmez ve plan reddedilir.
    """
    pivots = piv_15m + piv_1h + piv_4h
    if side == "long":
        cands = sorted({p for p in pivots if p > entry * 1.001})
        need = lambda mult: entry + mult * risk
        progressive = lambda value, previous: previous is None or value > previous
        meets = lambda value, mult: value >= need(mult)
    else:
        cands = sorted({p for p in pivots if p < entry * 0.999}, reverse=True)
        need = lambda mult: entry - mult * risk
        progressive = lambda value, previous: previous is None or value < previous
        meets = lambda value, mult: value <= need(mult)

    def pick(mult, previous=None):
        return next((p for p in cands
                     if meets(p, mult) and progressive(p, previous)), None)

    tp1 = pick(C.MIN_RR_TP1)
    if tp1 is None:
        return None, None, None
    # min_sep_r: TP2/TP3 bir onceki hedefe yapismasin. Pivotlar sik oldugunda
    # TP1 ve TP2 ayni bolgeye dusup R:R esigini anlamsiz kiliyordu.
    rr1 = abs(tp1 - entry) / risk
    tp2 = pick(max(C.MIN_RR_TP2, rr1 + min_sep_r), tp1)
    if tp2 is None:
        return tp1, None, None
    rr2 = abs(tp2 - entry) / risk
    tp3 = pick(max(C.TARGET_RR_TP3, rr2 + min_sep_r), tp2)
    return tp1, tp2, tp3


def _planned_levels(side, trigger, a15, a1h, a4h):
    """Tetik daha gelmeden planli entry/SL/TP hesapla."""
    atr1 = a1h["atr"]
    c1 = a1h["closed"]
    if side == "long":
        swing = min(float(c1["low"].iloc[-12:].min()), trigger)
        sl = swing - C.SL_ATR_BUFFER * atr1
    else:
        swing = max(float(c1["high"].iloc[-12:].max()), trigger)
        sl = swing + C.SL_ATR_BUFFER * atr1
    entry = trigger
    risk = abs(entry - sl)
    rp = _risk_pct(entry, sl)
    if not (C.MIN_RISK_PCT <= rp <= C.ACTIVE_MAX_LIVE_RISK_PCT):
        return None
    tp1, tp2, tp3 = _targets(
        side, entry, risk,
        a15["pivot_highs" if side == "long" else "pivot_lows"],
        a1h["pivot_highs" if side == "long" else "pivot_lows"],
        a4h["pivot_highs" if side == "long" else "pivot_lows"],
    )
    if tp1 is None or tp2 is None:
        return None
    rr1 = abs(tp1 - entry) / risk
    rr2 = abs(tp2 - entry) / risk
    rr3 = abs(tp3 - entry) / risk if tp3 is not None else None
    if rr1 < C.MIN_RR_TP1 or rr2 < C.MIN_RR_TP2:
        return None
    return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "final_tp": "tp3" if tp3 is not None else "tp2",
            "risk_pct": rp, "rr1": rr1, "rr2": rr2, "rr3": rr3}


def _funding_bias(side, funding_rate):
    try:
        fr = float(funding_rate)
    except (TypeError, ValueError):
        return "neutral"
    if abs(fr) < 0.0003:
        return "nötr"
    if fr >= 0.0009:
        return "aşırı pozitif — long tarafı kalabalık"
    if fr <= -0.0009:
        return "aşırı negatif — short tarafı kalabalık"
    return "pozitif — long tarafı ödüyor" if fr > 0 else "negatif — short tarafı ödüyor"


def evaluate(sym, a15, a1h, a4h, funding_rate, oi):
    """Bir sembol icin EARLY/WATCH/ACTIVE dondurur; uygun degilse None."""
    price = a15["price"]
    atr1 = a1h["atr"]
    if not atr1 or atr1 <= 0 or len(a1h["closed"]) < 60 or len(a15["closed"]) < 80:
        return None

    for side in ("long", "short"):
        if side == "long" and a4h["tscore"] < 1:
            continue
        if side == "short" and a4h["tscore"] > -1:
            continue

        if side == "long" and a1h["tscore"] < C.MIN_1H_TREND_SCORE_LONG:
            continue
        if side == "short" and a1h["tscore"] > C.MAX_1H_TREND_SCORE_SHORT:
            continue

        r = a1h["rsi"]
        if side == "long" and not (C.RSI_LONG_MIN <= r <= C.RSI_LONG_MAX):
            continue
        if side == "short" and not (C.RSI_SHORT_MIN <= r <= C.RSI_SHORT_MAX):
            continue

        if a1h["stretch"] is not None and a1h["stretch"] > C.ATR_STRETCH_MAX:
            continue

        hi24, lo24 = a1h["high24"], a1h["low24"]
        if side == "long":
            ahead = [p for p in a1h["pivot_highs"] if p > price and hi24 and p >= hi24 * 0.997]
            trigger = min(ahead) if ahead else None
            behind = [p for p in a1h["pivot_highs"] if p <= price and hi24 and p >= hi24 * 0.985]
            broke = max(behind) if behind else None
        else:
            ahead = [p for p in a1h["pivot_lows"] if p < price and lo24 and p <= lo24 * 1.003]
            trigger = max(ahead) if ahead else None
            behind = [p for p in a1h["pivot_lows"] if p >= price and lo24 and p <= lo24 * 1.015]
            broke = min(behind) if behind else None

        lo72, hi72 = a1h["low72"], a1h["high72"]
        fresh_extreme_break = False
        if side == "short" and lo72:
            near_bottom = (price - lo72) / lo72 * 100 < C.EXTREME_PROX_PCT
            fresh_extreme_break = bool(broke) and broke <= lo72 * 1.002
            if near_bottom and not fresh_extreme_break:
                continue
        if side == "long" and hi72:
            near_top = (hi72 - price) / price * 100 < C.EXTREME_PROX_PCT
            fresh_extreme_break = bool(broke) and broke >= hi72 * 0.998
            if near_top and not fresh_extreme_break:
                continue

        if broke:
            c15 = a15["closed"]
            recent = c15.iloc[-C.FRESH_BREAK_BARS_15M:]
            older = c15.iloc[-(C.FRESH_BREAK_BARS_15M + 6):-C.FRESH_BREAK_BARS_15M]
            if side == "long":
                fresh = (recent["close"] > broke).any() and (older["close"] <= broke).all()
                run_pct = (price - broke) / broke * 100
            else:
                fresh = (recent["close"] < broke).any() and (older["close"] >= broke).all()
                run_pct = (broke - price) / broke * 100
            vol15_ok = bool(a15["vol_ratio"] == a15["vol_ratio"] and a15["vol_ratio"] >= C.BREAKOUT_VOL_MULT_15M)
            vol1_ok = bool(a1h["vol_ratio"] == a1h["vol_ratio"] and a1h["vol_ratio"] >= C.BREAKOUT_VOL_MULT_1H)
            if fresh and vol15_ok and vol1_ok and 0 <= run_pct <= C.ACTIVE_MAX_RUN_PCT:
                plan = _planned_levels(side, broke, a15, a1h, a4h)
                if not plan:
                    continue
                risk_live = abs(price - plan["sl"])
                risk_pct_live = _risk_pct(price, plan["sl"])
                rr1_live = abs(plan["tp1"] - price) / risk_live if risk_live else 0
                rr2_live = abs(plan["tp2"] - price) / risk_live if risk_live else 0
                if (not (C.MIN_RISK_PCT <= risk_pct_live <= C.ACTIVE_MAX_LIVE_RISK_PCT)
                        or rr1_live < C.MIN_RR_TP1 or rr2_live < C.MIN_RR_TP2):
                    continue
                return {
                    "status": "ACTIVE", "side": _fmt_side(side), "price": price,
                    "level": broke, "trigger": broke,
                    "entry_lo": min(price, broke), "entry_hi": max(price, broke),
                    "sl": plan["sl"], "tp1": plan["tp1"], "tp2": plan["tp2"], "tp3": plan["tp3"],
                    "final_tp": plan["final_tp"], "rr1": rr1_live, "rr2": rr2_live,
                    "rr3": (abs(plan["tp3"] - price) / risk_live if plan["tp3"] is not None else None),
                    "risk_pct": risk_pct_live,
                    "rsi15": a15["rsi"], "rsi1h": r,
                    "trend1h": a1h["tlabel"], "trend4h": a4h["tlabel"],
                    "vol15_ratio": a15["vol_ratio"], "vol1h_ratio": a1h["vol_ratio"],
                    "funding": funding_rate, "funding_bias": _funding_bias(side, funding_rate),
                    "oi": oi or {}, "fresh_extreme_break": fresh_extreme_break,
                }

        if trigger:
            dist = abs(trigger - price) / price * 100
            if dist <= C.EARLY_PROXIMITY_PCT:
                plan = _planned_levels(side, trigger, a15, a1h, a4h)
                if not plan:
                    continue
                status = "WATCH" if dist <= C.WATCH_PROXIMITY_PCT else "EARLY"
                alarm = trigger * (1 - C.EARLY_ALERT_PRICE_BUFFER_PCT / 100) if side == "long" else trigger * (1 + C.EARLY_ALERT_PRICE_BUFFER_PCT / 100)
                return {
                    "status": status, "side": _fmt_side(side), "price": price,
                    "trigger": trigger, "alarm": alarm, "dist_pct": dist,
                    "invalidation": plan["sl"], "sl": plan["sl"],
                    "entry_lo": trigger * (0.998 if side == "long" else 1.000),
                    "entry_hi": trigger * (1.004 if side == "long" else 1.002),
                    "tp1": plan["tp1"], "tp2": plan["tp2"], "tp3": plan["tp3"],
                    "final_tp": plan["final_tp"], "rr1": plan["rr1"],
                    "rr2": plan["rr2"], "rr3": plan["rr3"], "risk_pct": plan["risk_pct"],
                    "rsi15": a15["rsi"], "rsi1h": r,
                    "trend1h": a1h["tlabel"], "trend4h": a4h["tlabel"],
                    "vol15_ratio": a15["vol_ratio"], "vol1h_ratio": a1h["vol_ratio"],
                    "funding": funding_rate, "funding_bias": _funding_bias(side, funding_rate),
                    "oi": oi or {},
                }
    return None
