"""Kripto Tarayici V3.3 ana akisi — 15 dakikada bir.

V3.3:
- 4s/1G location + 1s setup + 15d entry
- LONG/SHORT paralel karar ozeti
- gercek TP1 >= 1.5R hard gate
- priority breakout/retest setup etiketi
- alternatif flip plani (otomatik giris degil, teyit kosullu)
"""
import time
REGIME = {}
CHANGE_24H = {}
from . import config as C
from . import data, radars, state as ST
from .engine_v3 import evaluate_v3
from .confluence import (btc_regime, taker_pressure, long_short_ratios,
                          basis_pct, spread_pct)
from .indicators import analyze
from .state import fmtp
from .telegram import Telegram


def fmt_funding(fr):
    try: return f"%{float(fr) * 100:.4f}/8s"
    except (TypeError, ValueError): return "-"


def fmt_oi(oi):
    oi = oi or {}
    def f(k):
        v = oi.get(k); return f"%{v:+.1f}" if v is not None else "-"
    return f"1s {f('1h')} | 4s {f('4h')} | 24s {f('24h')}"


def fmt_taker(v):
    try: return f"%{float(v) * 100:.0f} alıcı"
    except (TypeError, ValueError): return "-"


def fmt_ls(r):
    r = r or {}
    def f(k):
        try: return f"{float(r.get(k)):.2f}"
        except (TypeError, ValueError): return "-"
    return f"{f('top_pos')}/{f('global_acc')}"


def fmt_basis(v):
    try: return f"%{float(v):+.3f}"
    except (TypeError, ValueError): return "-"


def fmt_spread(v):
    try: return f"%{float(v):.3f}"
    except (TypeError, ValueError): return "-"


def fmt_optional_price(value):
    return "—" if value is None else fmtp(value)


def fmt_rr(value):
    return "—" if value is None else f"{value:.1f}"


def build_warnings(sig):
    w, side = [], sig.get("side")
    is_long = side == "LONG"
    oi24 = (sig.get("oi") or {}).get("24h")
    if oi24 is not None and oi24 <= -8: w.append(f"OI 24s %{oi24:.0f} boşalıyor")
    try:
        fr = float(sig.get("funding"))
        if fr <= -0.0006: w.append("funding aşırı negatif (short tarafı kalabalık)")
        elif fr >= 0.0006: w.append("funding aşırı pozitif (long tarafı kalabalık)")
    except (TypeError, ValueError): pass
    tk = sig.get("taker_1h") or sig.get("taker")
    if tk is not None:
        if is_long and tk < 0.47: w.append(f"taker satıcı ağırlıklı (%{tk*100:.0f})")
        if (not is_long) and tk > 0.53: w.append(f"taker alıcı ağırlıklı (%{tk*100:.0f})")
    v1 = sig.get("vol1h_ratio")
    if v1 == v1 and v1 is not None and v1 < 0.8: w.append(f"1s hacim zayıf ({v1:.1f}x)")
    r15 = sig.get("rsi15")
    if r15 is not None:
        if is_long and r15 < 30: w.append("15d aşırı satım — bıçak riski")
        if (not is_long) and r15 > 70: w.append("15d aşırı alım — squeeze riski")
    c24 = sig.get("change_24h")
    if c24 is not None:
        if is_long and c24 <= -10: w.append(f"24s %{c24:.0f} düşüşte long")
        if (not is_long) and c24 >= 10: w.append(f"24s %+{c24:.0f} yükselişte short")
    if any("düzeltme" in s for s in sig.get("score_parts", [])): w.append("4s düzeltme fazında")
    sp = sig.get("spread_pct")
    if sp is not None and sp > 0.08: w.append(f"spread geniş (%{sp:.2f})")
    return w[:4]


def _decision_line(sig):
    la, sa = sig.get("long_advantage"), sig.get("short_advantage")
    if la is None or sa is None: return ""
    return (f"Karar: {sig.get('decision_bias','WAIT')} ({sig.get('decision_strength','-')}) · "
            f"model avantajı LONG %{la} / SHORT %{sa}\n")


def _location_line(sig):
    s, r = sig.get("htf_support"), sig.get("htf_resistance")
    bits = []
    if s: bits.append(f"HTF destek {fmtp(s)}")
    if r: bits.append(f"HTF direnç {fmtp(r)}")
    if sig.get("rsi_divergence"): bits.append(f"RSI div {sig['rsi_divergence']}")
    return ("Konum: " + " · ".join(bits) + "\n") if bits else ""


def _flip_line(sig):
    p = sig.get("flip_plan")
    if not p: return ""
    return (f"↔️ Alternatif {p['side']}: yalnız {p['condition']} sonrası · "
            f"tetik {fmtp(p['trigger'])} · giriş ~{fmtp(p['entry'])} · "
            f"SL {fmtp(p['sl'])} · TP1 {fmtp(p['tp1'])} ({p['rr1']:.1f}R)\n")


def pretrade_msg(sym, sig, news_note):
    is_early = sig["status"] == "EARLY"
    icon = "🔵" if is_early else "🟡"
    title = "ERKEN UYARI" if is_early else "YAKIN TAKİP"
    direction = "ÜZERİ" if sig["side"] == "LONG" else "ALTI"
    setup = sig.get("setup_type", "yapisal").replace("_", "-")
    priority = " · ⭐ PRIORITY" if sig.get("priority_setup") else ""
    warns = build_warnings(sig)
    warn_line = ("⚠️ " + " · ".join(warns) + "\n") if warns else ""
    return (f"{icon} <b>{title} — {sym} {sig['side']}</b> · {setup}{priority} · Skor {sig.get('score','-')}/{sig.get('score_max','-')}\n"
            f"{_decision_line(sig)}{_location_line(sig)}"
            f"Tetik: {fmtp(sig['trigger'])} {direction} (uzaklık %{sig['dist_pct']:.2f}) · 🔔 Alarm: {fmtp(sig['alarm'])}\n"
            f"Plan: Giriş {fmtp(sig['entry_lo'])}–{fmtp(sig['entry_hi'])} | SL {fmtp(sig['sl'])} (risk %{sig['risk_pct']:.1f})\n"
            f"TP1: {fmtp(sig['tp1'])} | TP2: {fmtp(sig['tp2'])} | TP3: {fmt_optional_price(sig.get('tp3'))}\n"
            f"R:R: {fmt_rr(sig.get('rr1'))} / {fmt_rr(sig.get('rr2'))} / {fmt_rr(sig.get('rr3'))}\n"
            f"{_flip_line(sig)}{warn_line}"
            f"<i>Birincil plan teyit gelmeden emir değildir; alternatif plan otomatik flip değildir.</i>")


def active_msg(sym, sig, news_note):
    direction = "bullish" if sig["side"] == "LONG" else "bearish"
    setup = sig.get("setup_type", "yapisal").replace("_", "-")
    priority = " · ⭐ PRIORITY" if sig.get("priority_setup") else ""
    return (f"🟢 <b>İŞLEM BÖLGESİ AKTİF — {sym} {sig['side']}</b> · {setup}{priority}\n"
            f"{_decision_line(sig)}{_location_line(sig)}"
            f"Giriş: {fmtp(sig['entry_lo'])}–{fmtp(sig['entry_hi'])} | SL: {fmtp(sig['sl'])} — HARD STOP\n"
            f"TP1: {fmtp(sig['tp1'])} | TP2: {fmtp(sig['tp2'])} | TP3: {fmt_optional_price(sig.get('tp3'))}\n"
            f"R:R: {fmt_rr(sig.get('rr1'))} / {fmt_rr(sig.get('rr2'))} / {fmt_rr(sig.get('rr3'))}\n"
            f"Neden: 15d/1s {direction}, {setup}, hacim/taker + HTF location teyidi\n"
            + _flip_line(sig)
            + (("⚠️ " + " · ".join(build_warnings(sig)) + "\n") if build_warnings(sig) else "")
            + f"İptal: Hard SL {fmtp(sig['sl'])} seviyesine temas")


def _market_data(sym, need_4h=True, min_tscore=None):
    a4 = None
    if need_4h:
        k4 = data.klines(sym, "4h", C.KLINE_LIMITS["4h"])
        if k4 is None or len(k4) < 60: return None
        a4 = analyze(k4)
        if min_tscore is not None and abs(a4["tscore"]) < min_tscore: return None
    k15 = data.klines(sym, "15m", C.KLINE_LIMITS["15m"])
    k1 = data.klines(sym, "1h", C.KLINE_LIMITS["1h"])
    if k15 is None or k1 is None or len(k15) < 100 or len(k1) < 80: return None
    return analyze(k15), analyze(k1), a4


CTX_BUDGET = {"n": 0}
def _build_ctx(sym, a15, a1h):
    CTX_BUDGET["n"] += 1
    fr = data.funding(sym) or {}
    a1d = None
    k1d = data.klines(sym, "1d", 240)
    if k1d is not None and len(k1d) >= 40: a1d = analyze(k1d, piv_lookback=100)
    return {
        "funding_rate": fr.get("lastFundingRate"), "basis_pct": basis_pct(fr),
        "oi": data.oi_changes(sym) or {}, "taker_15m": taker_pressure(a15["closed"], bars=4),
        "taker_1h": taker_pressure(a1h["closed"], bars=6), "change_24h": CHANGE_24H.get(sym),
        "ls_ratios": long_short_ratios(sym), "spread_pct": spread_pct(sym), "a1d": a1d,
    }


def _legacy_attach(sym, sig):
    fr = data.funding(sym); frate = fr.get("lastFundingRate") if fr else None
    sig["funding"] = frate
    from .engine import _funding_bias
    sig["funding_bias"] = _funding_bias("long" if sig["side"] == "LONG" else "short", frate)
    sig["oi"] = data.oi_changes(sym) or {}
    return sig


def run():
    CTX_BUDGET["n"] = 0
    tg = Telegram(); st = ST.load(); t0 = time.time()
    symbols = data.exchange_perp_symbols(); tickers = data.ticker_24h()
    if symbols is None or tickers is None:
        st["fail_count"] = st.get("fail_count", 0) + 1
        if st["fail_count"] == 1 or st["fail_count"] % 12 == 0:
            tg.send("🚨 <b>VERİ KAYNAĞI SORUNU</b>\nBinance Futures verisine ulaşılamıyor; analiz üretilmedi.")
        ST.append_scan(st, {"ts": ST.now(), "ok": False, "reason": "veri kaynağı", "duration_s": round(time.time() - t0)})
        ST.save(st); return
    if st.get("fail_count", 0) >= 1: tg.send(f"✅ Binance veri kaynağı geri geldi (önceki hata: {st['fail_count']}).")
    st["fail_count"] = 0; st["last_ok_run"] = ST.now()

    first_run = not st["known_symbols"]
    for s in radars.detect_new_listings(symbols, st["known_symbols"]):
        st["known_symbols"][s] = 0 if first_run else ST.now()
        if not first_run: tg.send(f"🆕 <b>YENİ LİSTELEME — {s}</b>\nİlk {C.YOUNG_COIN_DAYS} gün teknik sinyal yok; yapı otursun.")
    if first_run: tg.send(f"🚀 Kripto Tarayıcı V3.3 aktif. {len(symbols)} perpetual kayıtlı; 15 dakikalık tarama başladı.")

    tdf = tickers[tickers["symbol"].isin(symbols)].copy()
    tdf = tdf[tdf["quoteVolume"] >= C.MIN_QUOTE_VOLUME_24H].sort_values("quoteVolume", ascending=False)
    young_cut = ST.now() - C.YOUNG_COIN_DAYS * 86400
    liquid = [s for s in tdf["symbol"] if st["known_symbols"].get(s, 0) <= young_cut or first_run]
    chg = dict(zip(tdf["symbol"], tdf["priceChangePercent"]))
    global REGIME, CHANGE_24H
    REGIME = btc_regime(); CHANGE_24H = chg
    print("REJIM:", REGIME.get("note"))

    ST.cleanup_terminal(st)
    open_syms = [s for s, v in st["signals"].items() if v["status"] in ("EARLY", "WATCH", "ACTIVE")]
    for sym in open_syms:
        md = _market_data(sym, need_4h=True)
        if not md: continue
        a15, a1, a4 = md; sig = st["signals"][sym]
        if sig["status"] in ("EARLY", "WATCH"):
            res = evaluate_v3(sym, a15, a1, a4, REGIME, _build_ctx)
            if isinstance(res, tuple): ST.log_event(st, sym, "VETO", res[1]); res = None
            if res and res["status"] == "ACTIVE" and res["side"] == sig["side"]:
                news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
                if news and news["veto"]:
                    sig["status"], sig["last_update"] = "CANCELLED", ST.now(); tg.send(f"🛑 <b>İPTAL (HABER VETOSU) — {sym}</b>\n{news['note']}"); continue
                ST.activate(st, sym, sig, res); ST.log_event(st, sym, "ACTIVATED", f"{res['side']} @ {res['price']:.6g}")
                tg.send(active_msg(sym, res, nn)); continue
            if res and res["status"] == "WATCH" and sig["status"] == "EARLY" and res["side"] == sig["side"]:
                res["created"] = sig.get("created", ST.now()); res["last_update"] = ST.now(); st["signals"][sym] = res
                news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
                ST.log_event(st, sym, "WATCH", f"{res['side']} @ {res['price']:.6g}"); tg.send(pretrade_msg(sym, res, nn)); continue
            ST.update_pretrade(st, sym, a15, a1, tg)
        else:
            ST.update_active(st, sym, a15, tg)

    core = list(liquid[:C.CORE_SCAN_CAP]); momentum = []
    for sym in liquid[:C.MOMENTUM_SCAN_POOL]:
        if sym in core or abs(chg.get(sym, 0)) > C.MAX_ABS_24H_CHANGE_TECH: continue
        k1 = data.klines(sym, "1h", 80)
        if k1 is None or len(k1) < 30: continue
        a1 = analyze(k1, piv_lookback=50); c = a1["closed"]
        chg3h = abs((c["close"].iloc[-1] / c["close"].iloc[-4] - 1) * 100) if len(c) > 4 else 0
        if (a1["vol_ratio"] == a1["vol_ratio"] and a1["vol_ratio"] >= C.MOMENTUM_PRE_VOL_MULT) or chg3h >= C.MOMENTUM_PRE_3H_PCT:
            momentum.append(sym)
    candidates = (core + [s for s in momentum if s not in core])[:C.DEEP_SCAN_CAP]

    new_sent = 0
    for sym in candidates:
        if new_sent >= 8 or CTX_BUDGET["n"] >= 18: break
        if sym in st["signals"] and st["signals"][sym]["status"] in ("EARLY", "WATCH", "ACTIVE"): continue
        if abs(chg.get(sym, 0)) > C.MAX_ABS_24H_CHANGE_TECH: continue
        md = _market_data(sym, need_4h=True, min_tscore=1)
        if not md: continue
        a15, a1, a4 = md; sig = evaluate_v3(sym, a15, a1, a4, REGIME, _build_ctx)
        if isinstance(sig, tuple): ST.log_event(st, sym, "VETO", sig[1]); continue
        if not sig: continue
        news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
        if news and news["veto"]: ST.log_event(st, sym, "NEWS_VETO", news["note"]); continue
        sig["created"] = ST.now(); sig["last_update"] = ST.now()
        if sig["status"] == "ACTIVE":
            sig["entry_ref"] = (sig["entry_lo"] + sig["entry_hi"]) / 2; sig["activated_at"] = ST.now(); sig["mfe_pct"] = 0; sig["mae_pct"] = 0
        st["signals"][sym] = sig; ST.log_event(st, sym, sig["status"], f"{sig['side']} @ {sig['price']:.6g}")
        tg.send(active_msg(sym, sig, nn) if sig["status"] == "ACTIVE" else pretrade_msg(sym, sig, nn)); new_sent += 1

    pcands = radars.pump_candidates(tdf); sent = 0
    for _, row in pcands.iterrows():
        if sent >= C.PUMP_MAX_PER_RUN: break
        sym = row["symbol"]; p = radars.check_pump(sym, ST.now(), st.get("pump_alerts", {}))
        if not p: continue
        st.setdefault("pump_alerts", {})[sym] = ST.now(); ST.log_event(st, sym, "PUMP_ALERT", f"vol {p['vol_ratio']:.1f}x, 3h %{p['chg3h']:.1f}")
        tg.send(f"⚡ <b>PUMP RADARI — {sym}</b> (SPEKÜLATİF)\nFiyat: {fmtp(p['price'])} | 24s: %{row['priceChangePercent']:.1f} | 3s: %{p['chg3h']:.1f}\n1s hacim: {p['vol_ratio']:.1f}x | OI(~6s): %{p['oi_chg']:+.1f} | RSI(1s): {p['rsi1h']:.0f}\nTeknik giriş sinyali değildir; manipülasyon riski yüksek.")
        sent += 1

    active_count = len([1 for v in st["signals"].values() if v["status"] in ("EARLY", "WATCH", "ACTIVE")])
    ST.append_scan(st, {"ts": ST.now(), "ok": True, "symbols": len(symbols), "liquid": len(liquid), "candidates": len(candidates), "open_signals": active_count, "duration_s": round(time.time() - t0)})
    ST.save(st)
    print(f"V3.3 tamamlandi: {time.time()-t0:.0f}s | likit {len(liquid)} | aday {len(candidates)} | takip {active_count}")


if __name__ == "__main__":
    run()
