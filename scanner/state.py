"""Durum yonetimi ve paper-performance kaydi."""
import json
import os
import time
from . import config as C

OPEN_STATUSES = ("EARLY", "WATCH", "ACTIVE")


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
    migrate_engine(st)
    return st


def migrate_engine(st):
    if st.get("engine_version") == C.ENGINE_VERSION:
        return 0
    migrated = 0
    ts = now()
    previous = st.get("engine_version", "3.1")
    for signal in st.get("signals", {}).values():
        if signal.get("status") in OPEN_STATUSES:
            signal["status"] = "CANCELLED"
            signal["last_update"] = ts
            signal["migration_reason"] = f"engine {previous} -> {C.ENGINE_VERSION}"
            migrated += 1
    st["engine_version"] = C.ENGINE_VERSION
    log_event(st, "SYSTEM", "ENGINE_MIGRATION",
              f"{migrated} acik plan sessizce CANCELLED; tarihsel log/trades korundu")
    return migrated


def prune_known_symbols(st, current_symbols):
    """Delist edilmis perpetual sembollerini state'ten kontrollu temizle.

    exchangeInfo gecici/eksik gelirse toplu silme yapmamak icin iki emniyet var:
    minimum evren ve onceki known evrene gore makul oran.
    """
    cur = set(current_symbols or [])
    known = st.setdefault("known_symbols", {})
    if len(cur) < C.KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE:
        return 0
    prev = len(known)
    if prev and len(cur) < prev * C.KNOWN_SYMBOLS_PRUNE_MIN_RATIO:
        return 0
    stale = [s for s in known if s not in cur]
    for s in stale:
        del known[s]
    if stale:
        log_event(st, "SYSTEM", "KNOWN_SYMBOLS_PRUNED", f"{len(stale)} stale perpetual silindi")
    return len(stale)


def _compact_signal(sym, s):
    keys = ("status", "side", "price", "trigger", "sl", "tp1", "tp2", "tp3",
            "rr1", "rr2", "rr3", "risk_pct", "score", "score_max", "setup_type",
            "priority_setup", "decision_bias", "decision_strength", "htf_support",
            "htf_resistance", "created", "activated_at", "last_update")
    out = {"symbol": sym}
    for k in keys:
        if k in s:
            out[k] = s.get(k)
    return out


def _trade_stats(trades):
    vals = [t for t in trades if t.get("pnl_r") is not None]
    wins = [t for t in vals if t["pnl_r"] > 0]
    losses = [t for t in vals if t["pnl_r"] <= 0]
    avg_r = sum(t["pnl_r"] for t in vals) / len(vals) if vals else None
    return {
        "count": len(trades), "scored_count": len(vals), "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(vals) if vals else None),
        "avg_r": avg_r,
    }


def build_summary(st):
    ts = now()
    logs = [x for x in st.get("log", []) if x.get("t", 0) >= ts - 86400]
    trades = st.get("trades", [])
    open_signals = [_compact_signal(sym, s) for sym, s in st.get("signals", {}).items()
                    if s.get("status") in OPEN_STATUSES]
    scans = st.get("scan_log", [])
    if isinstance(scans, dict):
        scans = [scans]
    return {
        "generated_at": ts,
        "engine_version": st.get("engine_version", C.ENGINE_VERSION),
        "last_ok_run": st.get("last_ok_run", 0),
        "fail_count": st.get("fail_count", 0),
        "known_symbols_count": len(st.get("known_symbols", {})),
        "open_signal_count": len(open_signals),
        "open_signals": open_signals,
        "scan_log": scans[-C.SCAN_LOG_KEEP:],
        "log_last_24h": logs[-C.SUMMARY_LOG_MAX:],
        "trades_stats": _trade_stats(trades),
        "recent_trades": trades[-C.SUMMARY_RECENT_TRADES:],
    }


def save(st):
    os.makedirs(os.path.dirname(C.STATE_PATH), exist_ok=True)
    st["log"] = st.get("log", [])[-C.LOG_KEEP:]
    st["trades"] = st.get("trades", [])[-C.TRADE_HISTORY_KEEP:]
    sl = st.get("scan_log", [])
    st["scan_log"] = ([sl] if isinstance(sl, dict) else sl)[-C.SCAN_LOG_KEEP:]
    with open(C.STATE_PATH, "w") as f:
        json.dump(st, f, indent=1)
    with open(C.SUMMARY_PATH, "w") as f:
        json.dump(build_summary(st), f, indent=1)


def log_event(st, sym, event, detail):
    st.setdefault("log", []).append({"t": now(), "sym": sym, "event": event, "detail": detail})


def append_scan(st, rec):
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
    s = st["signals"][sym]
    price = a15["price"]
    c1 = a1h["closed"]
    last1 = float(c1["close"].iloc[-1])
    trig, inval = s["trigger"], s["invalidation"]
    is_long = s["side"] == "LONG"

    if (is_long and last1 < inval) or (not is_long and last1 > inval):
        s["status"], s["last_update"] = "CANCELLED", now()
        log_event(st, sym, "CANCELLED", f"1h close {last1:.6g} invalidation beyond")
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
    s = st["signals"][sym]
    price = a15["price"]
    is_long = s["side"] == "LONG"

    df = a15.get("df")
    if df is not None and len(df):
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

    targets = [(lvl, tag) for lvl, tag in
               (("tp1", "TP1"), ("tp2", "TP2"), ("tp3", "TP3"))
               if s.get(lvl) is not None]
    if not targets:
        return
    final_lvl = s.get("final_tp")
    if final_lvl not in {lvl for lvl, _ in targets}:
        final_lvl = targets[-1][0]

    for lvl, tag in targets:
        hit = hi >= s[lvl] if is_long else lo <= s[lvl]
        if hit and not s.get(f"{lvl}_hit"):
            s[f"{lvl}_hit"] = True
            s["last_update"] = now()
            is_final = lvl == final_lvl
            if is_final:
                outcome = f"{tag}_HIT"
                s["status"] = "TP3_HIT" if lvl == "tp3" else "CLOSED"
                _record_trade(st, sym, s, outcome, s[lvl])
            log_event(st, sym, f"{tag}_HIT", f"{s[lvl]:.6g}")
            tail = ""
            if tag == "TP1" and C.MOVE_SL_TO_BE_AFTER_TP1:
                tail = "\nPlan: kalan pozisyon için SL giriş/breakeven bölgesine taşınabilir."
            tg.send(f"🎯 <b>{tag} GÖRÜLDÜ — {sym} {s['side']}</b>\n"
                    f"15d mum aralığında {tag} {fmtp(s[lvl])} görüldü.{tail}")
            if is_final:
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
