"""Runtime policy for two-stage breakout entries.

1) A formasyon breakout may become ACTIVE on the first confirmed 15m close when
   the existing EMA/volume/RSI/context/risk/RR gates pass.
2) The ACTIVE alert tells the user that waiting for a retest is the safer option.
3) If price later returns to the broken trigger and reclaims/holds it with basic
   15m confirmation, emit one second STRONG RETEST ENTRY alert.

This module intentionally does not relax HTF location, decision, risk or RR gates.
"""
from . import config as C


_FORMATION_SETUPS = {
    "range", "double_top", "double_bottom", "asc_triangle", "desc_triangle",
    "sym_triangle", "rising_wedge", "falling_wedge", "flag",
    "trendline_break", "liquidity_sweep", "breakout_retest",
}


def _fmtp(x):
    if x is None:
        return "-"
    ax = abs(float(x))
    if ax >= 1000:
        return f"{x:,.1f}"
    if ax >= 10:
        return f"{x:.2f}"
    if ax >= 0.1:
        return f"{x:.4f}"
    return f"{x:.6f}"


def _retest_confirmed(s, a15):
    if s.get("setup_type") not in _FORMATION_SETUPS:
        return False, None, None
    if s.get("retest_alerted") or s.get("tp1_hit"):
        return False, None, None
    trigger = s.get("trigger")
    activated = s.get("activated_at")
    if not trigger or not activated:
        return False, None, None

    from . import state as ST
    # Aynı breakout mumunu retest sanma; en az bir sonraki tarama/candle beklensin.
    if ST.now() - activated < 12 * 60:
        return False, None, None

    price = float(a15.get("price") or 0)
    atr = float(a15.get("atr") or 0)
    if price <= 0:
        return False, None, None
    is_long = s.get("side") == "LONG"

    # Önce breakout seviyesinden anlamlı biçimde uzaklaşsın; sonra dönüş retest sayılır.
    away_pct = ((price - trigger) / trigger * 100) if is_long else ((trigger - price) / trigger * 100)
    arm_pct = max(0.30, (0.30 * atr / trigger * 100) if atr else 0.30)
    if not s.get("retest_armed"):
        if away_pct >= arm_pct:
            s["retest_armed"] = True
        return False, None, None

    closed = a15.get("closed")
    if closed is None or len(closed) < 2:
        return False, None, None
    recent = closed.iloc[-2:]
    last = closed.iloc[-1]
    tol = max(trigger * 0.0012, 0.20 * atr)
    if is_long:
        touched = float(recent["low"].min()) <= trigger + tol
        reclaimed = float(last["close"]) > trigger
    else:
        touched = float(recent["high"].max()) >= trigger - tol
        reclaimed = float(last["close"]) < trigger
    if not (touched and reclaimed):
        return False, None, None

    close = float(last["close"])
    ema20 = float(last["ema20"]) if "ema20" in closed else close
    ma7 = float(last["ma7"]) if "ma7" in closed else float(closed["close"].rolling(7).mean().iloc[-1])
    trend_ok = (close >= ema20 and close >= ma7) if is_long else (close <= ema20 and close <= ma7)
    vol = a15.get("vol_ratio")
    vol_ok = vol is not None and vol == vol and float(vol) >= 0.80
    rsi = a15.get("rsi")
    rsi_ok = True if rsi is None else ((38 <= rsi <= 75) if is_long else (25 <= rsi <= 62))
    if not (trend_ok and vol_ok and rsi_ok):
        return False, None, None

    lo = trigger if is_long else trigger - 1.5 * tol
    hi = trigger + 1.5 * tol if is_long else trigger
    return True, min(lo, hi), max(lo, hi)


def install_runtime_policy():
    from . import state as ST
    from . import telegram as TG

    if getattr(ST, "_two_stage_retest_installed", False):
        return

    original_update_active = ST.update_active

    def update_active_with_retest(st, sym, a15, tg):
        original_update_active(st, sym, a15, tg)
        s = st.get("signals", {}).get(sym)
        if not s or s.get("status") != "ACTIVE":
            return
        ok, entry_lo, entry_hi = _retest_confirmed(s, a15)
        if not ok:
            return
        s["retest_alerted"] = True
        s["retest_at"] = ST.now()
        ST.log_event(st, sym, "RETEST_ENTRY", f"{s.get('side')} retest @ {a15.get('price')}")
        tg.send(
            f"🔥 <b>GÜÇLÜ RETEST GİRİŞİ — {sym} {s.get('side')}</b>\n"
            f"Kırılan seviye retest edildi ve 15d yeniden teyit geldi.\n"
            f"Giriş bölgesi: {_fmtp(entry_lo)}–{_fmtp(entry_hi)} | "
            f"SL: {_fmtp(s.get('sl'))} — HARD STOP\n"
            f"TP1: {_fmtp(s.get('tp1'))} | TP2: {_fmtp(s.get('tp2'))} | TP3: {_fmtp(s.get('tp3'))}\n"
            f"Teyit: seviye teması + yönlü kapanış + EMA/MA + hacim/RSI uyumu"
        )

    ST.update_active = update_active_with_retest
    ST._two_stage_retest_installed = True

    original_send = TG.Telegram.send

    def send_with_breakout_note(self, text):
        if text.startswith("🟢 <b>İŞLEM BÖLGESİ AKTİF") and "Daha güvenli alternatif" not in text:
            text += ("\nℹ️ <i>Daha güvenli alternatif: kırılan seviyenin retesti beklenebilir; "
                     "sağlıklı retest oluşursa sistem ikinci kez güçlü giriş uyarısı verir.</i>")
        return original_send(self, text)

    TG.Telegram.send = send_with_breakout_note
