"""V3 Formasyon Motoru — 8 onaylanmis detektor.

Tasarim ilkeleri:
- Yuksek precision: emin olunmayan geometri sinyal uretmez (None doner)
- Her detektor ayni sozlesmeyle doner:
    {"type": str, "dir": "long"|"short", "trigger": float, "invalid": float,
     "quality": 0..1, "state": "forming"|"triggered", "note": str}
- Toleranslar ATR ile normalize edilir (coin fiyat olceginden bagimsiz)
- Kapali mumlar uzerinde calisir; olusmakta olan mum asla geometriye girmez
"""
import numpy as np
import logging


# ---------- pivot cikarimi (indeksli) ----------
def find_pivots(df, order=3, lookback=120):
    sub = df.iloc[-lookback:].reset_index(drop=True)
    h, l = sub["high"].values, sub["low"].values
    n = len(sub)
    piv = []
    for i in range(order, n - order):
        if h[i] >= h[i - order:i + order + 1].max():
            piv.append((i, float(h[i]), "H"))
        if l[i] <= l[i - order:i + order + 1].min():
            piv.append((i, float(l[i]), "L"))
    piv.sort(key=lambda x: x[0])
    # ardisik ayni tur pivotlarda ekstremi tut (alternating dizi)
    out = []
    for p in piv:
        if out and out[-1][2] == p[2]:
            if (p[2] == "H" and p[1] >= out[-1][1]) or (p[2] == "L" and p[1] <= out[-1][1]):
                out[-1] = p
        else:
            out.append(p)
    return out, sub


def _fit_line(points):
    """points: [(idx, price)] -> (slope, intercept, max_resid)"""
    if len(points) < 2:
        return None
    x = np.array([p[0] for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    slope, inter = np.polyfit(x, y, 1)
    resid = np.abs(y - (slope * x + inter))
    return slope, inter, float(resid.max())


def _line_at(fit, x):
    return fit[0] * x + fit[1]


def market_structure(piv):
    """HH-HL / LH-LL yapisi: son 4 anlamli pivottan."""
    hs = [p for p in piv if p[2] == "H"][-3:]
    ls = [p for p in piv if p[2] == "L"][-3:]
    if len(hs) < 2 or len(ls) < 2:
        return "belirsiz"
    hh = hs[-1][1] > hs[-2][1]
    hl = ls[-1][1] > ls[-2][1]
    if hh and hl:
        return "HH-HL"
    if (not hh) and (not hl):
        return "LH-LL"
    return "karisik"


# ---------- 1. Range / Dikdortgen ----------
def detect_range(piv, sub, atr, price):
    hs = [p for p in piv if p[2] == "H"][-4:]
    ls = [p for p in piv if p[2] == "L"][-4:]
    if len(hs) < 2 or len(ls) < 2:
        return None
    top = np.mean([p[1] for p in hs[-2:]])
    bot = np.mean([p[1] for p in ls[-2:]])
    tol = 0.6 * atr
    if max(abs(p[1] - top) for p in hs[-2:]) > tol:
        return None
    if max(abs(p[1] - bot) for p in ls[-2:]) > tol:
        return None
    height = top - bot
    if height < 2.0 * atr:
        return None
    pos = (price - bot) / height
    last_close = float(sub["close"].iloc[-1])
    if last_close > top + 0.25 * atr:
        return {"type": "range", "dir": "long", "trigger": top,
                "invalid": top - 0.5 * height, "quality": 0.7,
                "state": "triggered", "note": f"range kirilimi yukari (bant {bot:.6g}-{top:.6g})"}
    if last_close < bot - 0.25 * atr:
        return {"type": "range", "dir": "short", "trigger": bot,
                "invalid": bot + 0.5 * height, "quality": 0.7,
                "state": "triggered", "note": f"range kirilimi asagi (bant {bot:.6g}-{top:.6g})"}
    if pos > 0.75:
        return {"type": "range", "dir": "long", "trigger": top,
                "invalid": bot, "quality": 0.6, "state": "forming",
                "note": f"range tavani test ediliyor ({top:.6g})"}
    if pos < 0.25:
        return {"type": "range", "dir": "short", "trigger": bot,
                "invalid": top, "quality": 0.6, "state": "forming",
                "note": f"range tabani test ediliyor ({bot:.6g})"}
    return None


# ---------- 2. Cift tepe / Cift dip ----------
def detect_double(piv, sub, atr, price):
    """Son anlamli pivotlarda gercekci cift tepe/dip geometrisi ara.

    Eski surum yalnizca son 3 pivotu ve 0.5 ATR esitlik toleransini kabul
    ediyordu. Burada son 10 pivot icindeki aday ciftler taranir; benzerlik
    ATR + yuzde bazli dinamik toleransla, neckline ise minimum derinlik ve
    bar mesafesiyle dogrulanir. Hacim/momentum kaliteyi artirir ama tespit
    icin zorunlu degildir.
    """
    if len(piv) < 3 or not atr or atr <= 0 or len(sub) < 2:
        return None

    recent = piv[-10:]
    last_close = float(sub["close"].iloc[-1])
    prev_close = float(sub["close"].iloc[-2])
    n = len(sub)
    candidates = []

    # Kapanis hacmi / son 20 ortalama: sadece kalite bonusu.
    vol_ratio = None
    if "volume" in sub.columns and len(sub) >= 6:
        base = float(sub["volume"].iloc[-21:-1].mean()) if len(sub) >= 21 else float(sub["volume"].iloc[:-1].mean())
        if base > 0:
            vol_ratio = float(sub["volume"].iloc[-1]) / base

    def similarity_tol(level):
        # Normal kosulda en az %1.8 tolerans; volatil coinlerde ATR ile genisler,
        # fakat %3.5 ustune cikarak trend devamini "cift" diye etiketlemez.
        return min(max(0.80 * atr, 0.018 * level), 0.035 * level)

    def add_candidates(kind):
        same = [p for p in recent if p[2] == kind]
        opposite = "L" if kind == "H" else "H"
        for i in range(len(same) - 1):
            for j in range(i + 1, len(same)):
                a, c = same[i], same[j]
                sep = c[0] - a[0]
                if sep < 5 or sep > 60:
                    continue
                # Ikinci tepe/dip cok eskiyse forming sinyali bayatlar; triggered
                # tarafinda motorun ayrica tazelik filtresi vardir.
                if n - 1 - c[0] > 36:
                    continue
                mids = [p for p in recent if a[0] < p[0] < c[0] and p[2] == opposite]
                if not mids:
                    continue

                level = (a[1] + c[1]) / 2.0
                tol = similarity_tol(level)
                diff = abs(a[1] - c[1])
                if diff > tol:
                    continue

                if kind == "H":
                    neck = min(p[1] for p in mids)
                    depth = min(a[1], c[1]) - neck
                    min_depth = max(1.20 * atr, 0.035 * level)
                    if depth < min_depth:
                        continue
                    triggered = last_close < neck
                    # Neckline kirilmadiysa ikinci tepeden en az %25 geri cekilme
                    # olmadan forming deme; yakin gürültüyü eler.
                    if not triggered and last_close > min(a[1], c[1]) - 0.25 * depth:
                        continue
                    side, ptype = "short", "double_top"
                    invalid = max(a[1], c[1]) + 0.30 * atr
                    directional_momentum = last_close < prev_close
                else:
                    neck = max(p[1] for p in mids)
                    depth = neck - max(a[1], c[1])
                    min_depth = max(1.20 * atr, 0.035 * level)
                    if depth < min_depth:
                        continue
                    triggered = last_close > neck
                    if not triggered and last_close < max(a[1], c[1]) + 0.25 * depth:
                        continue
                    side, ptype = "long", "double_bottom"
                    invalid = min(a[1], c[1]) - 0.30 * atr
                    directional_momentum = last_close > prev_close

                q = 0.78 if triggered else 0.64
                q += 0.04 * max(0.0, 1.0 - diff / max(tol, 1e-12))
                if depth >= 2.0 * min_depth:
                    q += 0.03
                confirmations = []
                if triggered and vol_ratio is not None and vol_ratio >= 1.30:
                    q += 0.05
                    confirmations.append(f"hacim {vol_ratio:.1f}x")
                if triggered and directional_momentum and abs(last_close - prev_close) >= 0.60 * atr:
                    q += 0.04
                    confirmations.append("momentum")
                if triggered and abs(last_close - neck) >= 0.15 * atr:
                    q += 0.02
                q = min(q, 0.95)
                state = "triggered" if triggered else "forming"
                conf_note = f", teyit: {', '.join(confirmations)}" if confirmations else ""
                note_name = "cift tepe" if kind == "H" else "cift dip"
                note = (f"{note_name} {a[1]:.6g}/{c[1]:.6g}, boyun {neck:.6g}, "
                        f"aralik {sep} bar{conf_note}")
                # Triggered adaylar, sonra kalite, sonra daha yeni ikinci pivot,
                # sonra daha derin neckline tercih edilir.
                candidates.append(((1 if triggered else 0, q, c[0], depth),
                                   {"type": ptype, "dir": side, "trigger": neck,
                                    "invalid": invalid, "quality": q,
                                    "state": state, "note": note}))

    add_candidates("H")
    add_candidates("L")
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


# ---------- 3-4. Ucgen ve Kama/Takoz ----------
def detect_triangle_wedge(piv, sub, atr, price):
    hs = [(p[0], p[1]) for p in piv if p[2] == "H"][-4:]
    ls = [(p[0], p[1]) for p in piv if p[2] == "L"][-4:]
    if len(hs) < 3 or len(ls) < 3:
        return None
    fh, fl = _fit_line(hs), _fit_line(ls)
    if not fh or not fl:
        return None
    if fh[2] > 0.7 * atr or fl[2] > 0.7 * atr:
        return None
    x_now = len(sub) - 1
    top_now, bot_now = _line_at(fh, x_now), _line_at(fl, x_now)
    if top_now <= bot_now:
        return None
    sh, sl_ = fh[0] / atr, fl[0] / atr
    width_start = _line_at(fh, hs[0][0]) - _line_at(fl, ls[0][0])
    width_now = top_now - bot_now
    converging = width_now < width_start * 0.75
    last_close = float(sub["close"].iloc[-1])

    def result(t, d, trig, inval, note, q):
        st = "triggered" if ((d == "long" and last_close > trig + 0.2 * atr) or
                             (d == "short" and last_close < trig - 0.2 * atr)) else "forming"
        return {"type": t, "dir": d, "trigger": trig, "invalid": inval,
                "quality": q, "state": st, "note": note}

    flat_h, flat_l = abs(sh) < 0.05, abs(sl_) < 0.05
    if converging:
        if sh < -0.05 and sl_ < -0.05:
            return result("falling_wedge", "long", top_now, bot_now - 0.4 * atr,
                          "dusen takoz (falling wedge)", 0.7)
        if sh > 0.05 and sl_ > 0.05:
            return result("rising_wedge", "short", bot_now, top_now + 0.4 * atr,
                          "yukselen kama (rising wedge)", 0.7)
        if flat_h and sl_ > 0.05:
            return result("asc_triangle", "long", top_now, bot_now - 0.4 * atr,
                          "yukselen ucgen", 0.75)
        if flat_l and sh < -0.05:
            return result("desc_triangle", "short", bot_now, top_now + 0.4 * atr,
                          "alcalan ucgen", 0.75)
        if sh < -0.05 and sl_ > 0.05:
            return {"type": "sym_triangle", "dir": None, "trigger": top_now,
                    "invalid": bot_now, "quality": 0.6, "state": "forming",
                    "note": "simetrik ucgen (yon üst TF trendiyle)",
                    "trigger_short": bot_now}
    return None


# ---------- 5. Bayrak / Flama ----------
def detect_flag(sub, atr, price):
    closes = sub["close"].values
    if len(closes) < 30:
        return None
    for start in range(len(closes) - 25, len(closes) - 10):
        move = closes[start + 8] - closes[start]
        if abs(move) < 3.5 * atr:
            continue
        pole_dir = "long" if move > 0 else "short"
        cons = sub.iloc[start + 8:]
        if len(cons) < 4 or len(cons) > 15:
            continue
        c_hi, c_lo = cons["high"].max(), cons["low"].min()
        if (c_hi - c_lo) > abs(move) * 0.5:
            continue
        last_close = float(cons["close"].iloc[-1])
        if pole_dir == "long":
            trig, inval = float(c_hi), float(c_lo) - 0.3 * atr
            st = "triggered" if last_close > trig + 0.15 * atr else "forming"
        else:
            trig, inval = float(c_lo), float(c_hi) + 0.3 * atr
            st = "triggered" if last_close < trig - 0.15 * atr else "forming"
        return {"type": "flag", "dir": pole_dir, "trigger": trig, "invalid": inval,
                "quality": 0.65, "state": st,
                "note": f"bayrak/flama (direk {abs(move)/atr:.1f} ATR)"}
    return None


# ---------- 6. Trend cizgisi / kanal kirilimi ----------
def detect_trendline_break(piv, sub, atr, price):
    hs = [(p[0], p[1]) for p in piv if p[2] == "H"][-4:]
    ls = [(p[0], p[1]) for p in piv if p[2] == "L"][-4:]
    x_now = len(sub) - 1
    last_close = float(sub["close"].iloc[-1])
    prev_close = float(sub["close"].iloc[-2])
    if len(ls) >= 3:
        fl = _fit_line(ls)
        if fl and fl[2] <= 0.6 * atr and fl[0] / atr > 0.08:
            line_now = _line_at(fl, x_now)
            if last_close < line_now - 0.25 * atr and prev_close >= _line_at(fl, x_now - 1) - 0.1 * atr:
                return {"type": "trendline_break", "dir": "short", "trigger": line_now,
                        "invalid": line_now + 1.2 * atr, "quality": 0.7,
                        "state": "triggered", "note": "yukselen trend cizgisi asagi kirildi"}
    if len(hs) >= 3:
        fh = _fit_line(hs)
        if fh and fh[2] <= 0.6 * atr and fh[0] / atr < -0.08:
            line_now = _line_at(fh, x_now)
            if last_close > line_now + 0.25 * atr and prev_close <= _line_at(fh, x_now - 1) + 0.1 * atr:
                return {"type": "trendline_break", "dir": "long", "trigger": line_now,
                        "invalid": line_now - 1.2 * atr, "quality": 0.7,
                        "state": "triggered", "note": "alcalan trend cizgisi yukari kirildi"}
    return None


# ---------- 7. Liquidity sweep / false breakout ----------
def detect_sweep(piv, sub, atr, price):
    if len(piv) < 2 or len(sub) < 6:
        return None
    last3 = sub.iloc[-3:]
    hs = [p[1] for p in piv[:-1] if p[2] == "H"]
    ls = [p[1] for p in piv[:-1] if p[2] == "L"]
    if hs:
        ref = max(hs[-2:]) if len(hs) >= 2 else hs[-1]
        swept = (last3["high"] > ref + 0.1 * atr) & (last3["close"] < ref - 0.05 * atr)
        if swept.any():
            wick_hi = float(last3["high"].max())
            return {"type": "liquidity_sweep", "dir": "short", "trigger": ref,
                    "invalid": wick_hi + 0.3 * atr, "quality": 0.75,
                    "state": "triggered",
                    "note": f"tepe süpürme: {ref:.6g} ustu fitil, geri kapanis (tahmini likidite bolgesi)"}
    if ls:
        ref = min(ls[-2:]) if len(ls) >= 2 else ls[-1]
        swept = (last3["low"] < ref - 0.1 * atr) & (last3["close"] > ref + 0.05 * atr)
        if swept.any():
            wick_lo = float(last3["low"].min())
            return {"type": "liquidity_sweep", "dir": "long", "trigger": ref,
                    "invalid": wick_lo - 0.3 * atr, "quality": 0.75,
                    "state": "triggered",
                    "note": f"dip süpürme: {ref:.6g} alti fitil, geri kapanis (tahmini likidite bolgesi)"}
    return None


# ---------- 8. Breakout-retest (recent pivot break -> retest -> hold) ----------
def detect_breakout_retest(piv, sub, atr, price, hi24, lo24):
    if len(sub) < 10:
        return None

    n = len(sub)
    candidates = []
    for p_idx, lvl, kind in piv[-12:]:
        side = "long" if kind == "H" else "short"
        if side == "long" and not (lvl <= price and price - lvl <= 1.5 * atr):
            continue
        if side == "short" and not (lvl >= price and lvl - price <= 1.5 * atr):
            continue

        break_idx = None
        start = max(p_idx + 1, n - 12, 1)
        for i in range(start, n - 2):
            prev = float(sub["close"].iloc[i - 1])
            close = float(sub["close"].iloc[i])
            if side == "long" and prev <= lvl + 0.05 * atr and close > lvl + 0.10 * atr:
                break_idx = i
            elif side == "short" and prev >= lvl - 0.05 * atr and close < lvl - 0.10 * atr:
                break_idx = i
        if break_idx is None:
            continue

        after = sub.iloc[break_idx + 1:]
        if len(after) < 2:
            continue
        if side == "long":
            touched = (after["low"] <= lvl + 0.35 * atr).any()
            held = (sub["close"].iloc[-2:] > lvl).all()
        else:
            touched = (after["high"] >= lvl - 0.35 * atr).any()
            held = (sub["close"].iloc[-2:] < lvl).all()
        if not (touched and held):
            continue

        recency = break_idx / max(n, 1)
        distance = abs(price - lvl) / max(atr, 1e-12)
        candidates.append((recency - 0.05 * distance, side, lvl))

    if candidates:
        _, side, lvl = max(candidates, key=lambda x: x[0])
        if side == "long":
            return {"type": "breakout_retest", "dir": "long", "trigger": lvl,
                    "invalid": lvl - 0.8 * atr, "quality": 0.78,
                    "state": "triggered", "note": f"recent pivot {lvl:.6g} kirildi, retest sonrasi 2 kapanis tuttu"}
        return {"type": "breakout_retest", "dir": "short", "trigger": lvl,
                "invalid": lvl + 0.8 * atr, "quality": 0.78,
                "state": "triggered", "note": f"recent pivot {lvl:.6g} kirildi, retest sonrasi 2 kapanis asagida tuttu"}
    return None


DETECTORS_TR = {
    "range": "Range/Dikdortgen", "double_top": "Cift Tepe", "double_bottom": "Cift Dip",
    "falling_wedge": "Dusen Takoz", "rising_wedge": "Yukselen Kama",
    "asc_triangle": "Yukselen Ucgen", "desc_triangle": "Alcalan Ucgen",
    "sym_triangle": "Simetrik Ucgen", "flag": "Bayrak/Flama",
    "trendline_break": "Trend Cizgisi Kirilimi", "liquidity_sweep": "Likidite Süpürme",
    "breakout_retest": "Kirilim+Retest",
}


def scan_patterns(df, atr, price, hi24=None, lo24=None):
    """Tum detektorleri calistir, kaliteye gore sirali liste don."""
    piv, sub = find_pivots(df)
    if len(piv) < 3 or not atr:
        return [], "belirsiz"
    struct = market_structure(piv)
    found = []
    for fn in (detect_range, detect_double, detect_triangle_wedge,
               detect_trendline_break, detect_sweep):
        try:
            r = fn(piv, sub, atr, price)
            if r:
                found.append(r)
        except Exception as e:
            logging.warning("pattern detector %s failed: %s", fn.__name__, e)
    try:
        r = detect_flag(sub, atr, price)
        if r:
            found.append(r)
    except Exception as e:
        logging.warning("pattern detector detect_flag failed: %s", e)
    try:
        r = detect_breakout_retest(piv, sub, atr, price, hi24, lo24)
        if r:
            found.append(r)
    except Exception as e:
        logging.warning("pattern detector detect_breakout_retest failed: %s", e)
    found.sort(key=lambda x: (x["state"] == "triggered", x["quality"]), reverse=True)
    return found, struct
