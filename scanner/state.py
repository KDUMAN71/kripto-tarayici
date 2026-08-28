"""V2 durum yonetimi ve paper-performance kaydi.

Akis: EARLY -> WATCH -> ACTIVE -> STOP/TP
Ideal giris kacarsa MISSED olur ama KULLANICIYA MESAJ GONDERILMEZ.
"""
import json
import os
import time
from . import config as C


def now():
    return int(time.time())


def load():
    if os.path.exists(C.STATE_PATH):
        with open(C.STATE_PATH) as f:
            st = json.load(f)
    else:
        st = {"known_symbols": {}, "signals": {}, "pump_alerts": {}, "log": [],
              "trades": [], "fail_count": 0, "last_ok_run": 0}
    st.setdefault("trades", [])
    st.setdefault("scan_log", [])
    return st


def save(st):
    os.makedirs(os.path.dirname(C.STATE_PATH), exist_ok=True)
    st["log"] = st.get("log", [])[-C.LOG_KEEP:]
    st["trades"] = st.get("trades", [])[-C.TRADE_HISTORY_KEEP:]
    sl = st.get("scan_log", [])
    st["scan_log"] = ([sl] if isinstance(sl, dict) else sl)[-C.SCAN_LOG_KEEP:]
    with open(C.STATE_PATH, "w") as f:
        json.dump(st, f, indent=1)


def log_event(st, sym, event, detail):
    st.setdefault("log", []).append({"t": now(), "sym": sym, "event": event, "detail": detail})


def append_scan(st, rec):
    """Kosu heartbeat'ini listeye ekler.

    Onceki surum tek bir sozluk yazip her kosuda uzerine yaziyordu; boylece
    kosular arasi boslugu olcmek mumkun olmuyordu. Eski tek kayit varsa
    kaybedilmeden listeye tasinir.
    """
    cur = st.get("scan_log")
    if isinstance(cur, dict):
        cur = [cur]
    elif not isinstance(cur, list):
        cur = []
    cur.append(rec)
    st["scan_log"] = cur


def cleanup_terminal(st):
    terminal = ("CANCELLED", "MISSED", "EXPIRED", "STOPPED", "TP3_HIT", "CLOSED")
    dead = []
    for sym, s in st["signals"].items():
        if s["status"] in terminal and now() - s.get("last_update", 0) > 24 * 3600:
            dead.append(sym)
    for sym in dead:
        del st["signals"][sym]


def _track_excursions(s, price):
    if s.get("status") != "ACTIVE" or not s.get("entry_ref"):
        return
    e = s["entry_ref"]
    if s["side"] == "LONG":
        fav = (price - e) / e * 100
        adv = (e - price) / e * 100
    else:
        fav = (e - price) / e * 100
        adv = (price - e) / e * 100
    s["mfe_pct"] = max(s.get("mfe_pct", 0), fav)
    s["mae_pct"] = max(s.get("mae_pct", 0), adv)


def activate(st, sym, old_sig, res):
    full = dict(old_sig)
    full.update(res)
    full["created"] = old_sig.get("created", now())
    full["activated_at"] = now()
    full["last_update"] = now()
    full["entry_ref"] = (res["entry_lo"] + res["entry_hi"]) / 2
    full["mfe_pct"] = 0
    full["mae_pct"] = 0
    st["signals"][sym] = full
    return full


def _record_trade(st, sym, s, outcome, exit_price):
    entry = s.get("entry_ref") or s.get("price")
    risk = abs(entry - s["sl"]) if entry and s.get("sl") else None
    if risk:
        pnl_r = ((exit_price - entry) / risk) if s["side"] == "LONG" else ((entry - exit_price) / risk)
    else:
        pnl_r = None
    st.setdefault("trades", []).append({
        "symbol": sym, "side": s["side"], "activated_at": s.get("activated_at"),
        "closed_at": now(), "entry": entry, "sl": s.get("sl"),
        "tp1": s.get("tp1"), "tp2": s.get("tp2"), "tp3": s.get("tp3"),
        "setup_type": s.get("setup_type", "v2"), "score": s.get("score"),
        "outcome": outcome, "exit": exit_price, "pnl_r": pnl_r,
        "tp1_hit": bool(s.get("tp1_hit")), "tp2_hit": bool(s.get("tp2_hit")),
        "tp3_hit": bool(s.get("tp3_hit")),
        "mfe_pct": s.get("mfe_pct", 0), "mae_pct": s.get("mae_pct", 0),
    })


def update_pretrade(st, sym, a15, a1h, tg):
    """EARLY/WATCH yasam dongusu. Kacmis ve suresi dolmus planlarda sessizlik."""
    s = st["signals"][sym]
    price = a15["price"]
    c1 = a1h["closed"]
    last1 = float(c1["close"].iloc[-1])
    trig, inval = s["trigger"], s["invalidation"]
    is_long = s["side"] == "LONG"

    if (is_long and last1 < inval) or (not is_long and last1 > inval):
        s["status"], s["last_update"] = "CANCELLED", now()
        log_event(st, sym, "CANCELLED", f"1h close {last1:.6g} invalidation beyond")
        tg.send(f"🛑 <b>İPTAL — {sym} {s['side']}</b>\n"
                f"Daha önce bildirilen kurulum bozuldu. 1s kapanış: {fmtp(last1)} | "
                f"geçersizlik: {fmtp(inval)}")
        return

    run = (price - trig) / trig * 100 if is_long else (trig - price) / trig * 100
    if run > C.ACTIVE_MAX_RUN_PCT:
        s["status"], s["last_update"] = "MISSED", now()
        log_event(st, sym, "MISSED_SILENT", f"trigger {trig:.6g}, price {price:.6g}")
        return

    if now() - s.get("created", now()) > C.WATCH_EXPIRY_H * 3600:
        s["status"], s["last_update"] = "EXPIRED", now()
        log_event(st, sym, "EXPIRED_SILENT", "pretrade expired")


def update_active(st, sym, a15, tg):
    """ACTIVE sinyali hard-SL mantigiyla izler.

    15 dakikalik taramalar arasinda fiyat seviyeye dokunup geri donebilir. Bu nedenle
    yalnizca son fiyata/kapanisa degil, aktivasyondan beri gorulen 15d mumlarin
    high/low degerlerine bakilir. Ayni mum hem SL hem TP'ye dokunmussa yol sirasi
    bilinmedigi icin muhafazakar olarak SL once kabul edilir.
    """
    s = st["signals"][sym]
    price = a15["price"]
    is_long = s["side"] == "LONG"

    df = a15.get("df")
    if df is not None and len(df):
        # Aktivasyon anindan onceki tek mumu da dahil et; aktivasyon mumundaki fitili kacirmayiz.
        try:
            import pandas as pd
            since = pd.to_datetime(s.get("activated_at", now()), unit="s", utc=True) - pd.Timedelta(minutes=15)
            seen = df[df["openTime"] >= since]
            if seen.empty:
                seen = df.iloc[-4:]
        except Exception:
            seen = df.iloc[-4:]
    else:
        seen = a15["closed"].iloc[-4:]

    hi = max(float(seen["high"].max()), price)
    lo = min(float(seen["low"].min()), price)
    _track_excursions(s, hi if is_long else lo)
    # adverse excursion da ayri ekstremle guncellensin
    e = s.get("entry_ref")
    if e:
        adv = ((e - lo) / e * 100) if is_long else ((hi - e) / e * 100)
        s["mae_pct"] = max(s.get("mae_pct", 0), adv)

    stop_hit = lo <= s["sl"] if is_long else hi >= s["sl"]
    if stop_hit:
        s["status"], s["last_update"] = "STOPPED", now()
        log_event(st, sym, "STOPPED", f"hard SL touched {s['sl']:.6g}")
        _record_trade(st, sym, s, "STOPPED", s["sl"])
        tg.send(f"🔴 <b>STOP — {sym} {s['side']}</b>\n"
                f"15d mum aralığında hard SL {fmtp(s['sl'])} görüldü. Kurulum sona erdi.")
        return

    for lvl, tag in (("tp1", "TP1"), ("tp2", "TP2"), ("tp3", "TP3")):
        hit = hi >= s[lvl] if is_long else lo <= s[lvl]
        if hit and not s.get(f"{lvl}_hit"):
            s[f"{lvl}_hit"] = True
            s["last_update"] = now()
            if tag == "TP3":
                s["status"] = "TP3_HIT"
                _record_trade(st, sym, s, "TP3_HIT", s[lvl])
            log_event(st, sym, f"{tag}_HIT", f"{s[lvl]:.6g}")
            tail = ""
            if tag == "TP1" and C.MOVE_SL_TO_BE_AFTER_TP1:
                tail = "\nPlan: kalan pozisyon için SL giriş/breakeven bölgesine taşınabilir."
            tg.send(f"🎯 <b>{tag} GÖRÜLDÜ — {sym} {s['side']}</b>\n"
                    f"15d mum aralığında {tag} {fmtp(s[lvl])} görüldü.{tail}")
            if tag == "TP3":
                break


def fmtp(x):
    if x is None:
        return "-"
    ax = abs(x)
    if ax >= 1000:
        return f"{x:,.1f}"
    if ax >= 10:
        return f"{x:.2f}"
    if ax >= 0.1:
        return f"{x:.4f}"
    return f"{x:.6f}"
