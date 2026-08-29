"""V3.3 karar katmani.

Amaç: tek yonlu skor yerine LONG ve SHORT hipotezlerini ayni anda tartmak,
HTF konumu (pivot + EMA + Fibonacci), RSI uyumsuzlugu, BTC ve turev baglamini
birlikte degerlendirmek. Buradaki yuzdeler kazanma olasiligi degil; normalize
edilmis model avantajidir. Gercek win probability ancak tarihsel kalibrasyonla
uretilebilir.
"""
from . import config as C


def _near(a, b, pct):
    return b and abs(a - b) / abs(b) * 100 <= pct


def _cluster_levels(values, tol):
    vals = sorted(v for v in values if v and v == v and v > 0)
    if not vals:
        return []
    clusters = [[vals[0]]]
    for v in vals[1:]:
        center = sum(clusters[-1]) / len(clusters[-1])
        if abs(v - center) <= tol:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [{"level": sum(c) / len(c), "evidence": len(c), "members": c}
            for c in clusters]


def htf_zones(price, a4h, a1d=None):
    """4H/1D pivot, EMA50/100/200 ve Fibonacci seviyelerini cluster'lar."""
    values = []
    for a in (a4h, a1d):
        if not a:
            continue
        values += (a.get("pivot_highs") or [])[:8]
        values += (a.get("pivot_lows") or [])[:8]
        for k in ("ema50", "ema100", "ema200"):
            v = a.get(k)
            if v:
                values.append(float(v))
        fib = (a.get("fib") or {}).get("levels") or {}
        for key in ("0.382", "0.5", "0.618", "0.786"):
            v = fib.get(key)
            if v:
                values.append(float(v))
    atr4 = a4h.get("atr") or price * 0.01
    tol = min(C.HTF_ZONE_ATR_MULT * atr4, price * C.HTF_ZONE_MAX_PCT / 100)
    clusters = _cluster_levels(values, tol)
    strong = [c for c in clusters if c["evidence"] >= C.HTF_CLUSTER_MIN_TOUCHES]
    support = [c for c in strong if c["level"] <= price * (1 + C.HTF_LOCATION_PROX_PCT / 100)]
    resistance = [c for c in strong if c["level"] >= price * (1 - C.HTF_LOCATION_PROX_PCT / 100)]
    sup = max(support, key=lambda c: c["level"], default=None)
    res = min(resistance, key=lambda c: c["level"], default=None)
    return {"support": sup, "resistance": res, "clusters": strong, "tolerance": tol}


def _zone_distance_pct(price, zone):
    if not zone:
        return None
    return abs(price - zone["level"]) / price * 100


def location_gate(side, stage, trigger, price, zones, hold_count=0):
    """HTF bolgesine karsi breakout teyidi olmadan continuation'i engelle."""
    if side == "short":
        z = zones.get("support")
        d = _zone_distance_pct(price, z)
        if z and d is not None and d <= C.HTF_LOCATION_PROX_PCT:
            broken = trigger < z["level"] - zones["tolerance"] * 0.25 and hold_count >= C.ACTIVE_MIN_HOLD_CLOSES
            if stage != "ACTIVE" or not broken:
                return f"guclu HTF destek bolgesinde ({z['level']:.6g}); kirilim/hold olmadan SHORT yok"
    else:
        z = zones.get("resistance")
        d = _zone_distance_pct(price, z)
        if z and d is not None and d <= C.HTF_LOCATION_PROX_PCT:
            broken = trigger > z["level"] + zones["tolerance"] * 0.25 and hold_count >= C.ACTIVE_MIN_HOLD_CLOSES
            if stage != "ACTIVE" or not broken:
                return f"guclu HTF direnc bolgesinde ({z['level']:.6g}); kirilim/hold olmadan LONG yok"
    return None


def geometry_gate(entry, sl, tp1):
    if entry is None or sl is None or tp1 is None:
        return False, None
    risk = abs(entry - sl)
    if risk <= 0:
        return False, None
    rr1 = abs(tp1 - entry) / risk
    return rr1 >= C.MIN_RR_TP1, rr1


def _side_evidence(side, a15, a1h, a4h, a1d, regime, ctx, zones):
    """Model avantajini hesaplar; probability degildir."""
    long = side == "long"
    edge = 0.0
    reasons = []

    # HTF trend
    for name, a, weight in (("4s", a4h, 1.5), ("1G", a1d, 1.0)):
        if not a:
            continue
        t = a.get("tscore", 0)
        if (long and t >= 1) or ((not long) and t <= -1):
            edge += weight; reasons.append(f"{name} trend uyumu")
        elif (long and t <= -1) or ((not long) and t >= 1):
            edge -= weight * 0.7

    # Location: destek LONG, direnc SHORT lehine
    if long and zones.get("support") and _zone_distance_pct(a15["price"], zones["support"]) <= C.HTF_LOCATION_PROX_PCT:
        edge += 2.0; reasons.append("HTF destek cluster")
    if (not long) and zones.get("resistance") and _zone_distance_pct(a15["price"], zones["resistance"]) <= C.HTF_LOCATION_PROX_PCT:
        edge += 2.0; reasons.append("HTF direnc cluster")
    if long and zones.get("resistance") and _zone_distance_pct(a15["price"], zones["resistance"]) <= 0.7:
        edge -= 1.5
    if (not long) and zones.get("support") and _zone_distance_pct(a15["price"], zones["support"]) <= 0.7:
        edge -= 1.5

    # RSI divergence + RSI konumu
    divs = {a15.get("rsi_divergence"), a1h.get("rsi_divergence"), a4h.get("rsi_divergence")}
    if long and "bullish" in divs:
        edge += 1.25; reasons.append("bullish RSI divergence")
    if (not long) and "bearish" in divs:
        edge += 1.25; reasons.append("bearish RSI divergence")
    r1 = a1h.get("rsi")
    if r1 is not None:
        if long and 35 <= r1 <= 55:
            edge += 0.4
        if (not long) and 45 <= r1 <= 65:
            edge += 0.4

    # EMA50/100/200 dinamik konum/eğim
    for k, w in (("ema50", 0.35), ("ema100", 0.5), ("ema200", 0.6)):
        v = a4h.get(k)
        slope = a4h.get(k + "_slope", 0)
        if not v:
            continue
        if long and a15["price"] >= v and slope >= 0:
            edge += w
        elif (not long) and a15["price"] <= v and slope <= 0:
            edge += w

    # BTC rejimi
    bt = regime.get("trend", 0)
    if (long and bt >= 1) or ((not long) and bt <= -1):
        edge += 0.8; reasons.append("BTC uyumu")
    if regime.get("hard_break") == ("down" if long else "up"):
        edge -= 2.5

    # Taker/OI
    taker = ctx.get("taker_15m")
    if taker is not None:
        if (long and taker >= 0.52) or ((not long) and taker <= 0.48):
            edge += 0.8; reasons.append("15d taker uyumu")
        elif (long and taker <= 0.47) or ((not long) and taker >= 0.53):
            edge -= 0.6
    oi1 = (ctx.get("oi") or {}).get("1h")
    if oi1 is not None and oi1 > 0.5:
        edge += 0.25

    # 1H hacim teyidi
    v1 = a1h.get("vol_ratio")
    if v1 is not None and v1 == v1:
        if v1 >= 1.2:
            edge += 0.5; reasons.append("1s hacim")
        elif v1 < 0.7:
            edge -= 0.4

    return edge, reasons


def decision_summary(a15, a1h, a4h, a1d, regime, ctx):
    """LONG/SHORT paralel avantaj ozeti."""
    zones = htf_zones(a15["price"], a4h, a1d)
    le, lr = _side_evidence("long", a15, a1h, a4h, a1d, regime, ctx, zones)
    se, sr = _side_evidence("short", a15, a1h, a4h, a1d, regime, ctx, zones)
    # Softmax yerine basit normalize: sadece goreli model advantage; probability degil.
    diff = le - se
    if diff >= C.DECISION_EDGE_STRONG:
        bias, strength = "LONG", "guclu"
    elif diff >= C.DECISION_EDGE_MODERATE:
        bias, strength = "LONG", "orta"
    elif diff <= -C.DECISION_EDGE_STRONG:
        bias, strength = "SHORT", "guclu"
    elif diff <= -C.DECISION_EDGE_MODERATE:
        bias, strength = "SHORT", "orta"
    else:
        bias, strength = "WAIT", "zayif/karisik"
    # 50/50 etrafinda okunabilir goreli avantaj; win-rate olarak etiketlenmez.
    long_adv = max(5, min(95, round(50 + diff * 7)))
    short_adv = 100 - long_adv
    return {"bias": bias, "strength": strength,
            "long_advantage": long_adv, "short_advantage": short_adv,
            "long_edge": round(le, 2), "short_edge": round(se, 2),
            "long_reasons": lr[:4], "short_reasons": sr[:4], "zones": zones}


def build_flip_plan(primary_side, price, a15, a1h, a4h, decision):
    """Primary stop sonrasi otomatik giris degil; teyit edilirse alternatif senaryo."""
    alt = "short" if primary_side == "long" else "long"
    zones = decision.get("zones") or {}
    zone = zones.get("support") if alt == "short" else zones.get("resistance")
    if not zone:
        return None
    trigger = zone["level"]
    atr1 = a1h.get("atr") or price * 0.01
    if alt == "short":
        entry = trigger * 0.998
        sl = trigger + 0.8 * atr1
        lows = sorted({p for a in (a15, a1h, a4h) for p in (a.get("pivot_lows") or []) if p < entry}, reverse=True)
        tp1 = next((p for p in lows if (entry - p) >= C.MIN_RR_TP1 * abs(entry - sl)), None)
    else:
        entry = trigger * 1.002
        sl = trigger - 0.8 * atr1
        highs = sorted({p for a in (a15, a1h, a4h) for p in (a.get("pivot_highs") or []) if p > entry})
        tp1 = next((p for p in highs if (p - entry) >= C.MIN_RR_TP1 * abs(entry - sl)), None)
    ok, rr1 = geometry_gate(entry, sl, tp1)
    if not ok:
        return None
    return {"side": alt.upper(), "trigger": trigger, "entry": entry, "sl": sl,
            "tp1": tp1, "rr1": rr1,
            "condition": "breakdown+hold+retest failure" if alt == "short" else "breakout+hold+retest"}
