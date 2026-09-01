"""Pump radari + yeni listeleme radari + opsiyonel haber vetosu."""
import os
import time
import requests
from . import config as C
from . import data
from .indicators import analyze
from .confluence import taker_pressure


# ---------------- PUMP RADARI ----------------
def pump_candidates(tickers):
    df = tickers
    m = (df["priceChangePercent"] >= C.PUMP_MIN_24H) & \
        (df["priceChangePercent"] <= C.PUMP_MAX_24H) & \
        (df["quoteVolume"] >= C.MIN_QUOTE_VOLUME_24H / 4)  # pump'ta hacim hizla buyur, esik dusuk
    return df[m].sort_values("quoteVolume", ascending=False).head(20)


def check_pump(sym, now_ts, last_alerts):
    last = last_alerts.get(sym, 0)
    if now_ts - last < C.PUMP_ALERT_COOLDOWN_H * 3600:
        return None
    k1 = data.klines(sym, "1h", 60)
    if k1 is None or len(k1) < 30:
        return None
    a = analyze(k1, piv_lookback=40)
    if not a["vol_ratio"] or a["vol_ratio"] < C.PUMP_VOL_MULT:
        return None
    closed = a["closed"]
    chg3h = (closed["close"].iloc[-1] / closed["close"].iloc[-4] - 1) * 100 if len(closed) > 4 else 0
    if chg3h < 4:
        return None
    oi_chg = data.oi_change_pct(sym, period="1h", limit=6)
    if oi_chg is None or oi_chg < C.PUMP_OI_MIN_CHANGE:
        return None
    swing_lo = float(closed["low"].iloc[-6:].min())
    return {
        "price": a["price"], "vol_ratio": a["vol_ratio"], "chg3h": chg3h,
        "oi_chg": oi_chg, "suggested_stop": swing_lo - (a["atr"] or 0) * 0.8,
        "rsi1h": a["rsi"],
    }


# ---------------- ERKEN PUMP IZI ----------------
def early_pump_candidates(tickers):
    """Henuz kosmamis ama likit adaylar. Fiyat filtresi bilerek TERS:
    cok kosmus olanlari disarida birakir."""
    df = tickers
    m = (df["priceChangePercent"].abs() <= C.EARLY_PUMP_MAX_24H) &         (df["quoteVolume"] >= C.EARLY_PUMP_MIN_QUOTE_VOL)
    return df[m].sort_values("quoteVolume", ascending=False).head(C.EARLY_PUMP_POOL)


def check_early_pump(sym, now_ts, last_alerts):
    """OI fiyattan ONCE artiyor mu?

    Mevcut check_pump'in dogrulama mantiginin tersi: fiyat kostu mu diye degil,
    pozisyon ve alici baskisi birikirken fiyat hala sakin mi diye bakar.
    En eleyici ve en ucuz kontrol (tek istek) basa alinir ki API butcesi
    bosa harcanmasin.
    """
    if now_ts - last_alerts.get(sym, 0) < C.EARLY_PUMP_COOLDOWN_H * 3600:
        return None
    oi = data.oi_change_pct(sym, period="5m", limit=13)      # ~1 saat
    if oi is None or oi < C.EARLY_PUMP_OI_MIN_1H:
        return None
    k15 = data.klines(sym, "15m", 120)
    if k15 is None or len(k15) < 40:
        return None
    a = analyze(k15)
    closed = a["closed"]
    if len(closed) < 6:
        return None
    run1h = (closed["close"].iloc[-1] / closed["close"].iloc[-5] - 1) * 100
    if abs(run1h) > C.EARLY_PUMP_MAX_PRICE_RUN_1H:
        return None                                          # fiyat kosmus -> erken degil
    if not a["vol_ratio"] or a["vol_ratio"] < C.EARLY_PUMP_VOL_MULT_15M:
        return None
    taker = taker_pressure(closed, bars=8)
    if taker is None or taker < C.EARLY_PUMP_TAKER_MIN:
        return None
    k1 = data.klines(sym, "1h", 60)
    rsi1h = analyze(k1)["rsi"] if k1 is not None and len(k1) > 20 else None
    if rsi1h is not None and rsi1h > C.EARLY_PUMP_RSI_MAX:
        return None                                          # giris penceresi kapanmis
    return {"price": a["price"], "vol_ratio": a["vol_ratio"], "run1h": run1h,
            "oi_chg": oi, "taker": taker, "rsi1h": rsi1h}


# ---------------- YENI LISTELEME RADARI ----------------
def detect_new_listings(current_symbols, known):
    return [s for s in current_symbols if s not in known]


# ---------------- HABER VETOSU (opsiyonel) ----------------
def base_coin(sym):
    b = sym.replace("USDT", "")
    for pre in ("1000000", "1000"):
        if b.startswith(pre):
            b = b[len(pre):]
    return b


def news_check(sym):
    """CRYPTOPANIC_TOKEN secret'i varsa haber riski dondurur.
    Donus: None (veri yok) | {"veto": bool, "note": str}
    """
    token = os.environ.get("CRYPTOPANIC_TOKEN", "").strip()
    if not token:
        return {"veto": False, "note": "haber teyidi yok (haber modülü kapalı)"}
    try:
        r = requests.get(
            "https://cryptopanic.com/api/v1/posts/",
            params={"auth_token": token, "currencies": base_coin(sym),
                    "filter": "important", "public": "true"},
            timeout=12)
        if r.status_code != 200:
            return {"veto": False, "note": f"haber teyidi yok (API HTTP {r.status_code})"}
        posts = r.json().get("results", [])[:10]
        cutoff = time.time() - C.NEWS_LOOKBACK_H * 3600
        recent = []
        for p in posts:
            try:
                ts = time.mktime(time.strptime(p["published_at"][:19], "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                ts = time.time()
            if ts >= cutoff:
                recent.append(p.get("title", ""))
        veto = any(any(k in t.lower() for k in C.NEWS_VETO_KEYWORDS) for t in recent)
        note = f"{len(recent)} önemli haber teyit edildi (12s)" if recent else "teyit edilmiş kritik haber yok"
        if veto:
            note = "VETO: kritik haber (delist/hack vb.) — " + recent[0][:80]
        return {"veto": veto, "note": note}
    except requests.RequestException:
        return {"veto": False, "note": "haber teyidi yok (API erişimi başarısız)"}
