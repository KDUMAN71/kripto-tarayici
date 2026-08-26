"""Kripto Tarayici V2 ana akisi — 15 dakikada bir.

V2 yenilikleri:
- 4s yon / 1s setup / 15d entry
- ERKEN UYARI -> YAKIN TAKIP -> AKTIF
- 1s / 4s / 24s OI pencereleri
- hacim anomalisi ile genisletilmis momentum evreni
- kacmis girislerde sessizlik
- paper-performance (MFE/MAE/R) kaydi
"""
import time
from . import config as C
from . import data, radars, state as ST
from .engine import evaluate
from .indicators import analyze
from .state import fmtp
from .telegram import Telegram


def fmt_funding(fr):
    try:
        return f"%{float(fr) * 100:.4f}/8s"
    except (TypeError, ValueError):
        return "-"


def fmt_oi(oi):
    oi = oi or {}
    def f(k):
        v = oi.get(k)
        return f"%{v:+.1f}" if v is not None else "-"
    return f"1s {f('1h')} | 4s {f('4h')} | 24s {f('24h')}"


def pretrade_msg(sym, sig, news_note):
    is_early = sig["status"] == "EARLY"
    icon = "🔵" if is_early else "🟡"
    title = "ERKEN UYARI — EMİR HAZIRLIĞI" if is_early else "YAKIN TAKİP"
    direction = "ÜZERİ" if sig["side"] == "LONG" else "ALTI"
    return (f"{icon} <b>{title} — {sym} {sig['side']}</b>\n"
            f"Referans fiyat: {fmtp(sig['price'])} | Tetiğe uzaklık: %{sig['dist_pct']:.2f}\n"
            f"Kritik tetik: {fmtp(sig['trigger'])} {direction}\n"
            f"🔔 Binance fiyat alarmı: {fmtp(sig['alarm'])}\n"
            f"Teyit gelirse planlı giriş: {fmtp(sig['entry_lo'])} – {fmtp(sig['entry_hi'])}\n"
            f"SL: {fmtp(sig['sl'])} | TP1: {fmtp(sig['tp1'])} | TP2: {fmtp(sig['tp2'])} | TP3: {fmtp(sig['tp3'])}\n"
            f"R:R TP2 ~1:{sig['rr2']:.1f} | TP3 ~1:{sig['rr3']:.1f}\n"
            f"4s: {sig['trend4h']} | 1s: {sig['trend1h']} | RSI 15d/1s: {sig['rsi15']:.0f}/{sig['rsi1h']:.0f}\n"
            f"Hacim 15d/1s: {sig['vol15_ratio']:.1f}x/{sig['vol1h_ratio']:.1f}x | "
            f"Funding: {fmt_funding(sig['funding'])} | OI: {fmt_oi(sig.get('oi'))}\n"
            f"Haber: {news_note}\n"
            f"<i>Bu aşama giriş emri değildir; Binance alarmını kurup teyidi bekle.</i>")


def active_msg(sym, sig, news_note):
    extra = " (taze ekstrem kırılımı)" if sig.get("fresh_extreme_break") else ""
    return (f"🟢 <b>İŞLEM BÖLGESİ AKTİF — {sym} {sig['side']}</b>{extra}\n"
            f"Referans fiyat: {fmtp(sig['price'])}\n"
            f"Giriş: {fmtp(sig['entry_lo'])} – {fmtp(sig['entry_hi'])}\n"
            f"SL: {fmtp(sig['sl'])} (fiyat riski ≈ %{sig['risk_pct']:.1f})\n"
            f"TP1: {fmtp(sig['tp1'])} | TP2: {fmtp(sig['tp2'])} | TP3: {fmtp(sig['tp3'])}\n"
            f"R:R TP2 ~1:{sig['rr2']:.1f} | TP3 ~1:{sig['rr3']:.1f}\n"
            f"15d kırılım hacmi: {sig['vol15_ratio']:.1f}x | 1s hacim: {sig['vol1h_ratio']:.1f}x\n"
            f"4s: {sig['trend4h']} | 1s: {sig['trend1h']} | RSI 15d/1s: {sig['rsi15']:.0f}/{sig['rsi1h']:.0f}\n"
            f"Funding: {fmt_funding(sig['funding'])} ({sig['funding_bias']}) | OI: {fmt_oi(sig.get('oi'))}\n"
            f"Haber: {news_note}\n"
            f"Planlı yönetim: TP1 %{C.TP1_CLOSE_PCT}, TP2 %{C.TP2_CLOSE_PCT}, TP3 %{C.TP3_CLOSE_PCT}; "
            f"TP1 sonrası kalan için SL girişe taşınabilir.\n"
            f"⚠️ Kaldıraç likidasyon riskini büyütür; SL olmadan işlem yok.")


def _market_data(sym, need_4h=True, min_tscore=None):
    """4h once cekilir; min_tscore verilirse gecmeyen sembolde 15m/1h cekilmez."""
    a4 = None
    if need_4h:
        k4 = data.klines(sym, "4h", C.KLINE_LIMITS["4h"])
        if k4 is None or len(k4) < 60:
            return None
        a4 = analyze(k4)
        if min_tscore is not None and abs(a4["tscore"]) < min_tscore:
            return None
    k15 = data.klines(sym, "15m", C.KLINE_LIMITS["15m"])
    k1 = data.klines(sym, "1h", C.KLINE_LIMITS["1h"])
    if k15 is None or k1 is None or len(k15) < 100 or len(k1) < 80:
        return None
    return analyze(k15), analyze(k1), a4


def _attach_context(sym, sig):
    """Funding + OI yalnizca sinyal uretilince cekilir (API tasarrufu)."""
    fr = data.funding(sym)
    frate = fr.get("lastFundingRate") if fr else None
    sig["funding"] = frate
    from .engine import _funding_bias
    sig["funding_bias"] = _funding_bias("long" if sig["side"] == "LONG" else "short", frate)
    sig["oi"] = data.oi_changes(sym) or {}
    return sig


def run():
    tg = Telegram()
    st = ST.load()
    t0 = time.time()

    symbols = data.exchange_perp_symbols()
    tickers = data.ticker_24h()
    if symbols is None or tickers is None:
        st["fail_count"] = st.get("fail_count", 0) + 1
        if st["fail_count"] == 1 or st["fail_count"] % 12 == 0:
            tg.send("🚨 <b>VERİ KAYNAĞI SORUNU</b>\nBinance Futures verisine ulaşılamıyor; analiz üretilmedi.")
        ST.log_scan(st, ok=False, reason="binance_unreachable", fails=st["fail_count"])
        ST.save(st); return
    if st.get("fail_count", 0) >= 1:
        tg.send(f"✅ Binance veri kaynağı geri geldi (önceki hata: {st['fail_count']}).")
    st["fail_count"] = 0
    st["last_ok_run"] = ST.now()

    first_run = not st["known_symbols"]
    for s in radars.detect_new_listings(symbols, st["known_symbols"]):
        st["known_symbols"][s] = 0 if first_run else ST.now()
        if not first_run:
            tg.send(f"🆕 <b>YENİ LİSTELEME — {s}</b>\nİlk {C.YOUNG_COIN_DAYS} gün teknik sinyal yok; yapı otursun.")
    if first_run:
        tg.send(f"🚀 Kripto Tarayıcı V2 aktif. {len(symbols)} perpetual kayıtlı; 15 dakikalık tarama başladı.")

    tdf = tickers[tickers["symbol"].isin(symbols)].copy()
    tdf = tdf[tdf["quoteVolume"] >= C.MIN_QUOTE_VOLUME_24H].sort_values("quoteVolume", ascending=False)
    young_cut = ST.now() - C.YOUNG_COIN_DAYS * 86400
    liquid = [s for s in tdf["symbol"] if st["known_symbols"].get(s, 0) <= young_cut or first_run]
    chg = dict(zip(tdf["symbol"], tdf["priceChangePercent"]))

    # Mevcut sinyaller
    ST.cleanup_terminal(st)
    open_syms = [s for s, v in st["signals"].items() if v["status"] in ("EARLY", "WATCH", "ACTIVE")]
    for sym in open_syms:
        md = _market_data(sym, need_4h=True)
        if not md: continue
        a15, a1, a4 = md
        sig = st["signals"][sym]
        if sig["status"] in ("EARLY", "WATCH"):
            res = evaluate(sym, a15, a1, a4, None, None)
            if res:
                _attach_context(sym, res)
            if res and res["status"] == "ACTIVE" and res["side"] == sig["side"]:
                news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
                if news and news["veto"]:
                    sig["status"], sig["last_update"] = "CANCELLED", ST.now()
                    tg.send(f"🛑 <b>İPTAL (HABER VETOSU) — {sym}</b>\n{news['note']}")
                    continue
                ST.activate(st, sym, sig, res)
                ST.log_event(st, sym, "ACTIVATED", f"{res['side']} @ {res['price']:.6g}")
                tg.send(active_msg(sym, res, nn)); continue
            # EARLY -> WATCH'e yaklastiysa tek sefer yakin takip mesaji
            if res and res["status"] == "WATCH" and sig["status"] == "EARLY" and res["side"] == sig["side"]:
                res["created"] = sig.get("created", ST.now()); res["last_update"] = ST.now()
                st["signals"][sym] = res
                news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
                ST.log_event(st, sym, "WATCH", f"{res['side']} @ {res['price']:.6g}")
                tg.send(pretrade_msg(sym, res, nn)); continue
            ST.update_pretrade(st, sym, a15, a1, tg)
        else:
            ST.update_active(st, sym, a15, tg)

    # Genisletilmis aday havuzu: hacim liderleri + 1s momentum anomalisi
    core = list(liquid[:C.CORE_SCAN_CAP])
    momentum = []
    for sym in liquid[:C.MOMENTUM_SCAN_POOL]:
        if sym in core or abs(chg.get(sym, 0)) > C.MAX_ABS_24H_CHANGE_TECH:
            continue
        k1 = data.klines(sym, "1h", 80)
        if k1 is None or len(k1) < 30: continue
        a1 = analyze(k1, piv_lookback=50)
        c = a1["closed"]
        chg3h = abs((c["close"].iloc[-1] / c["close"].iloc[-4] - 1) * 100) if len(c) > 4 else 0
        if (a1["vol_ratio"] == a1["vol_ratio"] and a1["vol_ratio"] >= C.MOMENTUM_PRE_VOL_MULT) or chg3h >= C.MOMENTUM_PRE_3H_PCT:
            momentum.append(sym)
    candidates = (core + [s for s in momentum if s not in core])[:C.DEEP_SCAN_CAP]

    new_sent = 0
    for sym in candidates:
        if new_sent >= 8:
            break
        if sym in st["signals"] and st["signals"][sym]["status"] in ("EARLY", "WATCH", "ACTIVE"):
            continue
        if abs(chg.get(sym, 0)) > C.MAX_ABS_24H_CHANGE_TECH:
            continue
        md = _market_data(sym, need_4h=True, min_tscore=1)
        if not md: continue
        a15, a1, a4 = md
        sig = evaluate(sym, a15, a1, a4, None, None)
        if not sig: continue
        _attach_context(sym, sig)
        news = radars.news_check(sym); nn = news["note"] if news else "haber modülü kapalı"
        if news and news["veto"]:
            ST.log_event(st, sym, "NEWS_VETO", news["note"]); continue
        sig["created"] = ST.now(); sig["last_update"] = ST.now()
        if sig["status"] == "ACTIVE":
            sig["entry_ref"] = (sig["entry_lo"] + sig["entry_hi"]) / 2
            sig["activated_at"] = ST.now(); sig["mfe_pct"] = 0; sig["mae_pct"] = 0
        st["signals"][sym] = sig
        ST.log_event(st, sym, sig["status"], f"{sig['side']} @ {sig['price']:.6g}")
        tg.send(active_msg(sym, sig, nn) if sig["status"] == "ACTIVE" else pretrade_msg(sym, sig, nn))
        new_sent += 1

    # Pump radari aynen korunur
    pcands = radars.pump_candidates(tdf)
    sent = 0
    for _, row in pcands.iterrows():
        if sent >= C.PUMP_MAX_PER_RUN: break
        sym = row["symbol"]
        p = radars.check_pump(sym, ST.now(), st.get("pump_alerts", {}))
        if not p: continue
        st.setdefault("pump_alerts", {})[sym] = ST.now()
        ST.log_event(st, sym, "PUMP_ALERT", f"vol {p['vol_ratio']:.1f}x, 3h %{p['chg3h']:.1f}")
        tg.send(f"⚡ <b>PUMP RADARI — {sym}</b> (SPEKÜLATİF)\n"
                f"Fiyat: {fmtp(p['price'])} | 24s: %{row['priceChangePercent']:.1f} | 3s: %{p['chg3h']:.1f}\n"
                f"1s hacim: {p['vol_ratio']:.1f}x | OI(~6s): %{p['oi_chg']:+.1f} | RSI(1s): {p['rsi1h']:.0f}\n"
                f"Teknik giriş sinyali değildir; manipülasyon riski yüksek.")
        sent += 1

    active_count = len([1 for v in st["signals"].values() if v["status"] in ("EARLY", "WATCH", "ACTIVE")])
    ST.log_scan(st, ok=True, symbols=len(symbols), liquid=len(liquid),
                candidates=len(candidates), new_signals=new_sent, pumps=sent,
                open=active_count, secs=round(time.time() - t0))
    ST.save(st)
    print(f"V2 tamamlandi: {time.time()-t0:.0f}s | likit {len(liquid)} | aday {len(candidates)} | takip {active_count}")


if __name__ == "__main__":
    run()
