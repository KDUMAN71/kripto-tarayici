"""V3.4 Runner Autopsy — olcum katmani (sinyal kurallarina dokunmaz).

Amac: her taramada boru hattindan elenen sembollerin NEREDE ve NEDEN
oldugunu kaydetmek; haftada bir Top-10 yukselen x olum-asamasi raporu uretmek.

Tasarim kurallari (V3.4 sartnamesi):
- state/state.json'a yazmaz; ayri bounded state/runner_autopsy.json kullanir.
- Her tarama/sembol satiri degil, (stage, reason) DEGISIMLERI kaydedilir;
  ayni durum tekrarlarinda yalnizca 6 saatlik zaman kovasi degistiginde
  sayac/son-gorulme guncellenir (git commit gurultusunu sinirlar).
- Sembol basi 8, toplam 400 sembol siniri; sinyal gecmisi olanlar korunur.
- Terminal sinyal gecisleri (EXPIRED/MISSED/STOPPED/CANCELLED/TP3_HIT/CLOSED)
  yan/yas/setup ayrintisiyla saklanir.
- Haftalik rapor: koseli fiyat anlik goruntusu (baseline) yontemiyle 7g
  degisim TUM evren icin sifir ek API maliyetiyle hesaplanir; yalnizca
  Top-10 icin 1g klines cekilip yakalanabilirlik sinifi cikarilir.
"""
import json, os, time
from . import config as C

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "state", "runner_autopsy.json")
MAX_SYMBOLS = 400
MAX_ENTRIES_PER_SYMBOL = 8
TS_BUCKET_S = 6 * 3600
NEARMISS_MIN_QV = 2_000_000       # likidite kaydi yalniz 2M ustu yakin-kacirma bandinda
REPORT_PERIOD_S = 7 * 86400
TOP_N = 10
TERMINAL = ("CANCELLED", "MISSED", "EXPIRED", "STOPPED", "TP3_HIT", "CLOSED")

_A = None


def load():
    global _A
    try:
        with open(PATH, encoding="utf-8") as f:
            _A = json.load(f)
    except Exception:
        _A = {}
    _A.setdefault("symbols", {})
    _A.setdefault("sig_seen", {})
    _A.setdefault("week_baseline", None)
    _A.setdefault("last_report_ts", 0)
    return _A


def save():
    if _A is None:
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_A, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, PATH)


def _bucket(ts):
    return int(ts // TS_BUCKET_S * TS_BUCKET_S)


def record(sym, stage, reason, extra=None, ts=None):
    """Dedupe'lu kayit: son satirla ayni (stage, reason) ise yeni satir acmaz."""
    if _A is None:
        return
    b = _bucket(ts if ts is not None else time.time())
    rows = _A["symbols"].setdefault(sym, [])
    if rows and rows[-1]["stage"] == stage and rows[-1]["reason"] == reason:
        r = rows[-1]
        if r.get("lt") != b:
            r["lt"] = b
            r["n"] = r.get("n", 1) + 1
        return
    row = {"ts": b, "lt": b, "stage": stage, "reason": reason, "n": 1}
    if extra:
        x = {k: v for k, v in extra.items() if v is not None}
        if x:
            row["x"] = x
    rows.append(row)
    if len(rows) > MAX_ENTRIES_PER_SYMBOL:
        del rows[0:len(rows) - MAX_ENTRIES_PER_SYMBOL]
    _prune()


def _prune():
    syms = _A["symbols"]
    if len(syms) <= MAX_SYMBOLS:
        return
    protected = set(_A.get("sig_seen", {}))
    order = sorted((s for s in syms if s not in protected),
                   key=lambda s: syms[s][-1].get("lt", 0))
    for s in order[:len(syms) - MAX_SYMBOLS]:
        del syms[s]


def record_universe(tickers, symbols, liquid, tdf):
    """Evren-girisi elemeleri: yakin-kacirma likidite bandi + genc coin."""
    if _A is None or tickers is None:
        return
    try:
        t = tickers[tickers["symbol"].isin(symbols)]
        near = t[(t["quoteVolume"] < C.MIN_QUOTE_VOLUME_24H) &
                 (t["quoteVolume"] >= NEARMISS_MIN_QV)]
        for _, r in near.iterrows():
            record(r["symbol"], "liquidity",
                   "24s hacim 8M$ tabaninin altinda (yakin-kacirma bandi)",
                   extra={"qv_musd": int(float(r["quoteVolume"]) / 1e6)})
        liq = set(liquid)
        for sym in tdf["symbol"]:
            if sym not in liq:
                record(sym, "young_coin", "yeni listeleme karantinasi")
    except Exception:
        pass


def observe_signals(st, ts=None):
    """Sinyal yasam dongusu gecislerini (EARLY/WATCH/ACTIVE/terminal) kaydeder."""
    if _A is None:
        return
    tnow = ts if ts is not None else time.time()
    seen = _A.setdefault("sig_seen", {})
    sigs = st.get("signals") or {}
    for sym, v in sigs.items():
        stt = v.get("status")
        if seen.get(sym, {}).get("status") == stt:
            continue
        age_h = (tnow - v.get("created", tnow)) / 3600
        extra = {"side": v.get("side"), "age_h": round(age_h, 1),
                 "setup": v.get("setup") or v.get("pattern") or v.get("setup_note")}
        reason = stt if stt not in TERMINAL else \
            "%s (%s, %.0fs yasadi)" % (stt, v.get("side", "?"), age_h)
        record(sym, "signal", reason, extra=extra, ts=tnow)
        seen[sym] = {"status": stt, "ts": int(tnow)}
    for sym in [s for s in list(seen) if s not in sigs]:
        del seen[sym]


def note_baseline(tickers, ts=None):
    """Ilk kosuda tum evren icin fiyat anlik goruntusu alir (7g kiyas tabani)."""
    if _A is None or tickers is None or _A.get("week_baseline"):
        return
    col = "lastPrice" if "lastPrice" in tickers.columns else "weightedAvgPrice"
    try:
        px = {r["symbol"]: float(r[col]) for _, r in tickers.iterrows()
              if float(r[col]) > 0}
    except Exception:
        return
    _A["week_baseline"] = {"ts": _bucket(ts if ts is not None else time.time()), "px": px}


def _classify(data_mod, sym):
    """Yakalanabilirlik sinifi: gunluk dagilimdan."""
    kl = data_mod.klines(sym, "1d", 9)
    if kl is None or len(kl) < 4:
        return "VERI-YOK", None
    closes = [float(x) for x in kl["close"]]
    d = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
    tot = (closes[-1] / closes[0] - 1) * 100
    if tot <= 5:
        return "GERI-VERDI", d
    mx = max(d)
    mi = d.index(mx)
    pre_quiet = all(abs(x) < 8 for x in d[:mi])
    after = (closes[-1] / closes[mi + 1] - 1) * 100 if mi + 1 < len(closes) else 0.0
    if mx / max(tot, 1e-9) > 0.65 and pre_quiet and after < 10:
        return "ANI-ONCUSUZ", d
    if mx > 20 and after >= 10:
        return "DEVAM-KOSUCUSU", d
    if all(abs(x) <= C.MAX_ABS_24H_CHANGE_TECH for x in d):
        return "MERDIVEN", d
    return "KARISIK", d


_CLS_TXT = {
    "ANI-ONCUSUZ": "ani/oncusuz — yakalanamaz sinif",
    "DEVAM-KOSUCUSU": "devam koscusu — momentum motoru adayi",
    "MERDIVEN": "merdiven — ana motor profili",
    "KARISIK": "karisik profil",
    "GERI-VERDI": "kazanci geri verdi",
    "VERI-YOK": "gunluk veri yok",
}


def _death_line(st, sym):
    tags = []
    rows = _A["symbols"].get(sym) or []
    if rows:
        r = rows[-1]
        tags.append("%s: %s" % (r["stage"], r["reason"]))
    sig = (st.get("signals") or {}).get(sym)
    if sig:
        tags.append("defter: %s" % sig.get("status"))
    elif _A.get("sig_seen", {}).get(sym):
        tags.append("son sinyal: %s" % _A["sig_seen"][sym].get("status"))
    if sym in (st.get("pump_alerts") or {}):
        tags.append("pump-izi")
    if sym in (st.get("early_pump_alerts") or {}):
        tags.append("erken-pump-izi")
    return " | ".join(tags) if tags else "hic kayit yok (evren disi / radar gormedi)"


def maybe_weekly_report(st, tickers, data_mod, ts=None):
    """7 gun dolduysa Top-10 runner x olum-asamasi raporu dondurur; yoksa None."""
    if _A is None or tickers is None:
        return None
    tnow = ts if ts is not None else time.time()
    wb = _A.get("week_baseline")
    if not wb:
        note_baseline(tickers, ts=tnow)
        return None
    if tnow - wb["ts"] < REPORT_PERIOD_S:
        return None
    col = "lastPrice" if "lastPrice" in tickers.columns else "weightedAvgPrice"
    try:
        px_now = {r["symbol"]: float(r[col]) for _, r in tickers.iterrows()}
    except Exception:
        return None
    perf = [(s, (px_now[s] / p - 1) * 100) for s, p in wb["px"].items()
            if s in px_now and p > 0 and px_now[s] > 0]
    top = sorted(perf, key=lambda x: -x[1])[:TOP_N]
    days = (tnow - wb["ts"]) / 86400
    lines = ["🧬 <b>RUNNER OTOPSİSİ — haftalık rapor</b> (son %.1f gün)" % days]
    stage_count = {}
    for s, ch in top:
        cls, _d = _classify(data_mod, s)
        death = _death_line(st, s)
        stage = (_A["symbols"].get(s) or [{}])[-1].get("stage", "kayitsiz")
        stage_count[stage] = stage_count.get(stage, 0) + 1
        lines.append("• <b>%s</b> +%%%.0f — %s\n   ↳ %s" % (s, ch, _CLS_TXT.get(cls, cls), death))
    lines.append("\nÖlüm dağılımı: " + ", ".join("%s×%d" % (k, v) for k, v in
                 sorted(stage_count.items(), key=lambda x: -x[1])))
    lines.append("<i>Ölçüm katmanıdır; sinyal kuralları değişmedi.</i>")
    _A["last_report_ts"] = int(tnow)
    _A["week_baseline"] = {"ts": _bucket(tnow), "px": px_now}
    return "\n".join(lines)
