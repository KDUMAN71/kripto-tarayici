"""Spot Radar V1.1 — orkestrasyon. scanner/ import ETMEZ (test T8 dogrular)."""
import json, os, re, time
from . import config as C
from . import identity, gates, structure, diffusion, ranking, outcomes, report
from .sources import coingecko, geckoterminal, dexscreener, goplus, news_rss, binance_futures

STATE_DIR = os.environ.get("SPOT_STATE_DIR", "state_spot")
STATE = os.path.join(STATE_DIR, "spot_state.json")

def _load():
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    # Bootstrap state'i bos sozluk ({}) olarak yazilabiliyor; eksik anahtarlari
    # tamamla ki st["health"] / st["snapshots"] KeyError vermesin.
    st.setdefault("snapshots", {})
    st.setdefault("reports", [])
    st.setdefault("outcomes", {})
    st.setdefault("health", {})
    return st

def _save(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    for k, arr in st.get("snapshots", {}).items():
        st["snapshots"][k] = arr[-C.MAX_SNAPSHOTS:]
    st["reports"] = st.get("reports", [])[-C.MAX_REPORTS:]
    json.dump(st, open(STATE, "w"), separators=(",", ":"))

def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())

def _snap(st, key, cand, n24=None):
    arr = st["snapshots"].setdefault(key, [])
    rec = {"d": _today(), "price": cand.get("price"), "mc": cand.get("mc"),
           "liq": cand.get("liq"), "vol24": cand.get("vol24"),
           "holders": cand.get("holders"), "news24": n24}
    if arr and arr[-1]["d"] == rec["d"]: arr[-1] = rec
    else: arr.append(rec)

def _prev(st, key):
    arr = st["snapshots"].get(key) or []
    for rec in reversed(arr):
        if rec["d"] != _today(): return rec
    return None

def build_universe():
    fut = binance_futures.futures_bases()
    cex = []
    for m in coingecko.markets(C.CEX_PAGES):
        sym = (m.get("symbol") or "").upper()
        mc, vol = m.get("market_cap"), m.get("total_volume")
        if not mc or mc < C.CEX_MIN_MC: continue
        if not vol or vol / mc < C.CEX_MIN_VOLMC: continue
        if sym in C.EXCLUDE_SYMBOLS: continue
        if sym in fut: continue
        cex.append({"layer": "CEX", "key": f"cex:{m['id']}", "symbol": sym,
                    "ident": identity.build(m.get("name"), sym, coin_id=m.get("id")),
                    "price": m.get("current_price"), "mc": mc, "fdv": m.get("fully_diluted_valuation"),
                    "vol24": vol, "ch24": m.get("price_change_percentage_24h"),
                    "coin_id": m.get("id"), "low7": None})
    dex = []
    for p in geckoterminal.discover(C.DEX_NETWORKS):
        liq, vol = p.get("liq"), p.get("vol24")
        mc = p.get("mc") or p.get("fdv")
        if not liq or liq < C.DEX_MIN_LIQ: continue
        if not vol or vol < C.DEX_MIN_VOL24: continue
        if not mc or not (C.DEX_MC_MIN <= mc <= C.DEX_MC_MAX): continue
        name = (p.get("name") or "").split("/")[0].strip()
        dex.append({"layer": "DEX", "key": f"{p['network']}:{p['token']}", "symbol": name.upper() or "?",
                    "ident": identity.build(name, name, chain=p["network"], contract=p["token"]),
                    "network": p["network"], "token": p["token"], "pool": p.get("pool"),
                    "price": p.get("price"), "mc": mc, "fdv": p.get("fdv"), "liq": liq,
                    "vol24": vol, "ch24": p.get("ch24"),
                    "age_h": gates.age_hours(p.get("created_at")), "low7": None})
    return cex, dex

def enrich_dex(c):
    pair = dexscreener.token_pairs(c["network"], c["token"])
    if pair:
        tx = pair.get("txns") or {}
        c["buys24"] = (tx.get("h24") or {}).get("buys"); c["sells24"] = (tx.get("h24") or {}).get("sells")
        c["buy_ratios"] = []
        for w in ("h1", "h6", "h24"):
            b = (tx.get(w) or {}).get("buys") or 0; s = (tx.get(w) or {}).get("sells") or 0
            c["buy_ratios"].append(b / (b + s) if (b + s) else None)
        liq = (pair.get("liquidity") or {}).get("usd")
        if liq: c["liq"] = liq
        vol = (pair.get("volume") or {})
        c["vol_h6"] = vol.get("h6")
        if not c.get("age_h") and pair.get("pairCreatedAt"):
            c["age_h"] = (time.time() * 1000 - pair["pairCreatedAt"]) / 3.6e6

def factors(c, st, sec):
    prev = _prev(st, c["key"])
    if prev and prev.get("vol24"):
        c["f_volp"] = (c.get("vol24") or 0) / max(prev["vol24"], 1)
    elif c.get("vol_h6") and c.get("vol24"):
        c["f_volp"] = (c["vol_h6"] * 4) / max(c["vol24"], 1)
    else:
        c["f_volp"] = None
    c["f_volmc"] = (c["vol24"] / c["mc"]) if c.get("vol24") and c.get("mc") else None
    c["f_liqg"] = (c["liq"] / prev["liq"] - 1) if prev and prev.get("liq") and c.get("liq") else None
    c["liq_growth"] = c["f_liqg"]
    br = c.get("buy_ratios") or []
    known = [b for b in br if b is not None]
    c["f_buy"] = (sum(1 for b in known if b > 0.55) / 3) if known else None
    if sec is not None:
        try: c["holders"] = int(sec.get("holder_count") or 0) or None
        except (TypeError, ValueError): c["holders"] = None
    if prev and prev.get("holders") and c.get("holders"):
        c["f_holder"] = c["holders"] / prev["holders"] - 1
    else:
        c["f_holder"] = None

def _ann_match(sym, anns):
    """Kelime-siniri eslesmesi: 'USDT' artik 'BTCUSDT' basligini yakalayamaz."""
    if not sym or len(sym) < 3 or sym in C.GENERIC_TICKERS or sym in C.EXCLUDE_SYMBOLS:
        return False
    pat = re.compile(r"(?<![A-Z0-9])" + re.escape(sym) + r"(?![A-Z0-9])")
    return any(pat.search(a.upper()) for a in anns)

def run():
    t0 = time.time()
    st = _load()
    cex, dex = build_universe()
    boosted = dexscreener.boosts()
    anns, ann_ok = news_rss.binance_announcements()
    st["health"]["news_source_degraded"] = not ann_ok
    passed = []
    sec_budget = C.FINALIST_SECURITY
    for c in dex:
        sec = goplus.security(c["network"], c["token"]) if sec_budget > 0 else None
        sec_budget -= 1
        enrich_dex(c)
        is_boost = (c.get("token") or "").lower() in boosted
        factors(c, st, sec)
        ok, why, fl = gates.apply(c, _prev(st, c["key"]), sec, is_boost)
        c["flags"] = fl; c["gate_why"] = why
        _snap(st, c["key"], c)
        if ok: passed.append(c)
    for c in cex:
        factors(c, st, None)
        ok, why, fl = gates.apply(c, _prev(st, c["key"]), None, False)
        c["flags"] = fl; c["gate_why"] = why
        _snap(st, c["key"], c)
        if ok: passed.append(c)
    # finalist zenginlestirme: yapi + yayilim (butce sinirli)
    for group in ("DEX", "CEX"):
        pool = [c for c in passed if c["layer"] == group]
        ranking.percentiles(pool)
        pre = sorted(pool, key=lambda c: -sum(p or 0 for p in (c.get(f + "_p") for f in ranking.FACTORS)))
        for c in pre[:C.FINALIST_OHLCV]:
            if group == "DEX" and c.get("pool"):
                c["f_struct"] = structure.score(geckoterminal.pool_ohlcv(c["network"], c["pool"]))
            elif group == "CEX" and c.get("coin_id"):
                c["f_struct"] = structure.score(coingecko.ohlc(c["coin_id"]) or [])
        for c in pre[:C.FINALIST_NEWS]:
            q = identity.news_query(c["ident"])
            if not q: continue
            n24, doms, tier = news_rss.google_news(q)
            hist = [s.get("news24") for s in st["snapshots"].get(c["key"], []) if s.get("news24") is not None]
            ann_hit = _ann_match(c["symbol"], anns)
            d = diffusion.evaluate(n24, doms, tier, hist, c.get("ch24"), "paid_promo" in (c.get("flags") or []), ann_hit)
            c["diffusion"] = d; c["f_diff"] = d["raw"]
            _snap(st, c["key"], c, n24=n24)
    top = []
    for group in ("DEX", "CEX"):
        pool = [c for c in passed if c["layer"] == group]
        ranking.percentiles(pool)
        top += ranking.rank(pool)
    top = [c for c in sorted(top, key=lambda c: (-c["breadth"], -c["median_p"]))
           if c["breadth"] >= C.MIN_BREADTH][:C.TOP_N]
    for c in top:
        if c["layer"] == "CEX" and c.get("coin_id"):
            exs = {e.lower() for e in coingecko.tickers(c["coin_id"])}
            c["no_trusted_cex"] = not (exs & C.TRUSTED_CEX)
    for c in top:
        outcomes.register(st, c["key"], c.get("price"), c.get("lifecycle", c["layer"]))
    def price_of(key):
        for c in cex + dex:
            if c["key"] == key: return c.get("price")
        return None
    outcomes.update(st, price_of)
    meta = {"when": time.strftime("%d.%m %H:%M", time.gmtime(time.time() + 10800)),
            "n_cex": len(cex), "n_dex": len(dex), "n_pass": len(passed),
            "news_degraded": not ann_ok, "duration_s": None}
    txt = report.build(top, meta, st)
    report.send(txt)
    st["reports"].append({"ts": time.time(), "coins": [{"key": c["key"], "rank": i + 1,
                          "price": c.get("price"), "breadth": c["breadth"],
                          "median_p": round(c["median_p"], 3), "flags": c.get("flags")}
                         for i, c in enumerate(top)]})
    meta["duration_s"] = round(time.time() - t0)
    st["meta"] = meta
    _save(st)
    print(f"\nspot radar tamam: {meta['duration_s']}s | cex {len(cex)} dex {len(dex)} gecen {len(passed)} top {len(top)}")

if __name__ == "__main__":
    run()
