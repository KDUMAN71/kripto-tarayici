"""Spot Radar V2 — growth radar + independent microcap early discovery. scanner/ import ETMEZ."""
import json, os, re, time
from . import config as C
from . import identity, gates, structure, diffusion, ranking, outcomes, report, early
from .sources import coingecko, geckoterminal, dexscreener, goplus, news_rss, binance_futures

STATE_DIR = os.environ.get("SPOT_STATE_DIR", "state_spot")
STATE = os.path.join(STATE_DIR, "spot_state.json")

def _load():
    try: st = json.load(open(STATE))
    except Exception: st = {}
    st.setdefault("snapshots", {}); st.setdefault("reports", []); st.setdefault("outcomes", {})
    st.setdefault("health", {}); st.setdefault("early_seen", {})
    return st

def _save(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    for k, arr in st.get("snapshots", {}).items(): st["snapshots"][k] = arr[-C.MAX_SNAPSHOTS:]
    st["reports"] = st.get("reports", [])[-C.MAX_REPORTS:]
    # early_seen sonsuza kadar buyumesin: 30 gunden eski ve hic alarm vermemis kayitlari temizle.
    cutoff = time.time() - 30 * 86400
    st["early_seen"] = {k:v for k,v in st.get("early_seen", {}).items()
                        if (v.get("first_ts") or 0) >= cutoff or v.get("last_alert_stage")}
    json.dump(st, open(STATE, "w"), separators=(",", ":"))

def _today(): return time.strftime("%Y-%m-%d", time.gmtime())

def _snap(st, key, cand, n24=None):
    arr = st["snapshots"].setdefault(key, [])
    rec = {"d": _today(), "price": cand.get("price"), "mc": cand.get("mc"), "liq": cand.get("liq"),
           "vol24": cand.get("vol24"), "holders": cand.get("holders"), "news24": n24}
    if arr and arr[-1]["d"] == rec["d"]: arr[-1] = rec
    else: arr.append(rec)

def _prev(st, key):
    arr = st["snapshots"].get(key) or []
    for rec in reversed(arr):
        if rec["d"] != _today(): return rec
    return None

def build_universe():
    fut = binance_futures.futures_bases(); cex = []
    for m in coingecko.markets(C.CEX_PAGES):
        sym = (m.get("symbol") or "").upper(); mc, vol = m.get("market_cap"), m.get("total_volume")
        if not mc or mc < C.CEX_MIN_MC or not vol or vol / mc < C.CEX_MIN_VOLMC: continue
        if sym in C.EXCLUDE_SYMBOLS or sym in fut: continue
        cex.append({"layer":"CEX","key":f"cex:{m['id']}","symbol":sym,
                    "ident":identity.build(m.get("name"),sym,coin_id=m.get("id")),"price":m.get("current_price"),
                    "mc":mc,"fdv":m.get("fully_diluted_valuation"),"vol24":vol,"ch24":m.get("price_change_percentage_24h"),
                    "coin_id":m.get("id"),"low7":None})
    dex = []
    for p in geckoterminal.discover(C.DEX_NETWORKS):
        liq, vol, mc = p.get("liq"), p.get("vol24"), p.get("mc") or p.get("fdv")
        if not liq or liq < C.DEX_MIN_LIQ or not vol or vol < C.DEX_MIN_VOL24: continue
        if not mc or not (C.DEX_MC_MIN <= mc <= C.DEX_MC_MAX): continue
        name = (p.get("name") or "").split("/")[0].strip()
        dex.append({"layer":"DEX","key":f"{p['network']}:{p['token']}","symbol":name.upper() or "?",
                    "ident":identity.build(name,name,chain=p["network"],contract=p["token"]),"network":p["network"],
                    "token":p["token"],"pool":p.get("pool"),"price":p.get("price"),"mc":mc,"fdv":p.get("fdv"),
                    "liq":liq,"vol24":vol,"ch24":p.get("ch24"),"age_h":gates.age_hours(p.get("created_at")),"low7":None})
    return cex, dex

def enrich_dex(c):
    pair = dexscreener.token_pairs(c["network"], c["token"])
    if not pair: return
    tx = pair.get("txns") or {}; c["buys24"] = (tx.get("h24") or {}).get("buys"); c["sells24"] = (tx.get("h24") or {}).get("sells")
    c["buy_ratios"] = []
    for w in ("h1","h6","h24"):
        b = (tx.get(w) or {}).get("buys") or 0; s = (tx.get(w) or {}).get("sells") or 0
        c["buy_ratios"].append(b/(b+s) if (b+s) else None)
    c["tx_h1"] = ((tx.get("h1") or {}).get("buys") or 0) + ((tx.get("h1") or {}).get("sells") or 0)
    liq = (pair.get("liquidity") or {}).get("usd"); vol = pair.get("volume") or {}; ch = pair.get("priceChange") or {}
    if liq: c["liq"] = liq
    c["vol_h6"] = vol.get("h6"); c["ch1"] = ch.get("h1"); c["ch6"] = ch.get("h6")
    if pair.get("marketCap") or pair.get("fdv"): c["mc"] = pair.get("marketCap") or pair.get("fdv")
    if not c.get("age_h") and pair.get("pairCreatedAt"): c["age_h"] = (time.time()*1000-pair["pairCreatedAt"])/3.6e6
    c["dex_id"] = pair.get("dexId"); c["pair_address"] = pair.get("pairAddress") or c.get("pool"); c["trade_url"] = pair.get("url")
    info = pair.get("info") or {}; c["websites"] = info.get("websites") or []; c["socials"] = info.get("socials") or []
    base = pair.get("baseToken") or {}
    if base.get("address"):
        same = str(base["address"]) == str(c["token"]) if c["network"] == "solana" else str(base["address"]).lower() == str(c["token"]).lower()
        if same:
            c["symbol"] = (base.get("symbol") or c["symbol"]).upper()
            if base.get("name"): c["ident"]["project_name"] = base["name"]
            c["ident"]["ticker"] = c["symbol"]

def factors(c, st, sec):
    prev = _prev(st,c["key"])
    if prev and prev.get("vol24"): c["f_volp"]=(c.get("vol24") or 0)/max(prev["vol24"],1)
    elif c.get("vol_h6") and c.get("vol24"): c["f_volp"]=(c["vol_h6"]*4)/max(c["vol24"],1)
    else: c["f_volp"]=None
    c["f_volmc"]=(c["vol24"]/c["mc"]) if c.get("vol24") and c.get("mc") else None
    c["f_liqg"]=(c["liq"]/prev["liq"]-1) if prev and prev.get("liq") and c.get("liq") else None; c["liq_growth"]=c["f_liqg"]
    known=[b for b in (c.get("buy_ratios") or []) if b is not None]; c["f_buy"]=(sum(1 for b in known if b>0.55)/3) if known else None
    if sec is not None:
        try: c["holders"]=int(sec.get("holder_count") or 0) or None
        except (TypeError,ValueError): c["holders"]=None
    c["f_holder"]=(c["holders"]/prev["holders"]-1) if prev and prev.get("holders") and c.get("holders") else None

def _ann_match(sym, anns):
    if not sym or len(sym)<3 or sym in C.GENERIC_TICKERS or sym in C.EXCLUDE_SYMBOLS: return False
    pat=re.compile(r"(?<![A-Z0-9])"+re.escape(sym)+r"(?![A-Z0-9])"); return any(pat.search(a.upper()) for a in anns)

def _venue_rank(t):
    market=t.get("market") or ""; trusted=market in C.TRUSTED_CEX; green=t.get("trust_score")=="green"
    try: vol=float(t.get("volume") or 0)
    except (TypeError,ValueError): vol=0.0
    return (1 if trusted else 0,1 if green else 0,1 if t.get("target") in ("USDT","USDC","USD") else 0,vol)

def enrich_cex_identity(c):
    details=coingecko.ticker_details(c["coin_id"]); trusted=[t for t in details if t.get("market") in C.TRUSTED_CEX]
    c["trusted_cex"]=sorted({t["market"] for t in trusted}); best=max(trusted or details,key=_venue_rank,default=None)
    if best:
        c["buy_venue"]=best.get("market"); c["buy_pair"]=f"{best.get('base')}/{best.get('target')}" if best.get("base") and best.get("target") else None; c["trade_url"]=best.get("trade_url")
    c["no_trusted_cex"]=not bool(trusted); plats=coingecko.platforms(c["coin_id"]); c["platforms"]=plats
    if len(plats)==1:
        chain,contract=next(iter(plats.items())); c["network"]=chain; c["token"]=contract; c["ident"]["chain"]=chain; c["ident"]["contract"]=contract
    elif len(plats)>1: c["network"]=None; c["token"]=None

def scan_early(st, boosted=None):
    """$30K-$1M mikrocap taramasi. Guvenligi dogrulanmayan coin ASLA firsat olmaz."""
    boosted = boosted if boosted is not None else dexscreener.boosts()
    raw = geckoterminal.discover(C.DEX_NETWORKS, pages=C.EARLY_DISCOVERY_PAGES)
    candidates=[early.build_candidate(p) for p in raw if early.eligible_pool(p)]
    # API butcesini en umut verici adaylara ayir: hacim/deger + likidite/deger.
    candidates.sort(key=lambda c: ((c.get("vol24") or 0)/max(c.get("mc") or 1,1) + (c.get("liq") or 0)/max(c.get("mc") or 1,1)), reverse=True)
    accepted=[]
    for c in candidates[:C.FINALIST_SECURITY]:
        early.ensure_first_seen(st,c); enrich_dex(c); sec=goplus.security(c["network"],c["token"])
        if sec is None: continue
        bad,_=gates.security_gate(sec)
        if bad: continue
        bad,_=gates.concentration_gate(sec)
        if bad: continue
        try: c["holders"]=int(sec.get("holder_count") or 0) or None
        except (TypeError,ValueError): c["holders"]=None
        is_boost=(c.get("token") or "").lower() in boosted
        c["flags"]=gates.manipulation_flags(c,is_boost)
        if len(c["flags"])>=C.MANIP_FLAGS_VETO: continue
        early.classify(c,_prev(st,c["key"])); _snap(st,c["key"],c)
        if c["early_stage"]!="IGNORE": accepted.append(c)
    # Haber/katalizor daha sonra gelir; puani kurtaran tek unsur olamaz.
    accepted.sort(key=lambda c:c.get("early_score",0),reverse=True)
    for c in accepted[:C.EARLY_NEWS_FINALISTS]:
        q=identity.news_query(c["ident"])
        if not q: continue
        n24,doms,tier=news_rss.google_news(q); c["news24"]=n24; c["news_domains"]=doms; c["news_tier"]=tier
        early.classify(c,_prev(st,c["key"])); _snap(st,c["key"],c,n24=n24)
    accepted.sort(key=lambda c:(c.get("early_stage")!="EARLY_OPPORTUNITY",-c.get("early_score",0),c.get("mc") or 0))
    return accepted[:C.EARLY_TOP_N], len(raw), len(candidates)

def _run_growth(st, boosted, anns, ann_ok):
    cex,dex=build_universe(); passed=[]; sec_budget=C.FINALIST_SECURITY
    for c in dex:
        sec=goplus.security(c["network"],c["token"]) if sec_budget>0 else None; sec_budget-=1; enrich_dex(c)
        is_boost=(c.get("token") or "").lower() in boosted; factors(c,st,sec); ok,why,fl=gates.apply(c,_prev(st,c["key"]),sec,is_boost)
        c["flags"]=fl; c["gate_why"]=why; _snap(st,c["key"],c)
        if ok: passed.append(c)
    for c in cex:
        factors(c,st,None); ok,why,fl=gates.apply(c,_prev(st,c["key"]),None,False); c["flags"]=fl; c["gate_why"]=why; _snap(st,c["key"],c)
        if ok: passed.append(c)
    for group in ("DEX","CEX"):
        pool=[c for c in passed if c["layer"]==group]; ranking.percentiles(pool)
        pre=sorted(pool,key=lambda c:-sum(p or 0 for p in (c.get(f+"_p") for f in ranking.FACTORS)))
        for c in pre[:C.FINALIST_OHLCV]:
            if group=="DEX" and c.get("pool"):
                bars=geckoterminal.pool_ohlcv(c["network"],c["pool"],limit=168); c["f_struct"]=structure.score(bars)
                if bars: c["low7"]=min(x["l"] for x in bars)
            elif group=="CEX" and c.get("coin_id"): c["f_struct"]=structure.score(coingecko.ohlc(c["coin_id"]) or [])
        for c in pre[:C.FINALIST_NEWS]:
            q=identity.news_query(c["ident"])
            if not q: continue
            n24,doms,tier=news_rss.google_news(q); hist=[s.get("news24") for s in st["snapshots"].get(c["key"],[]) if s.get("news24") is not None]
            d=diffusion.evaluate(n24,doms,tier,hist,c.get("ch24"),"paid_promo" in (c.get("flags") or []),_ann_match(c["symbol"],anns)); c["diffusion"]=d; c["f_diff"]=d["raw"]; _snap(st,c["key"],c,n24=n24)
    top=[]
    for group in ("DEX","CEX"):
        pool=[c for c in passed if c["layer"]==group]; ranking.percentiles(pool); top+=ranking.rank(pool)
    top=[c for c in sorted(top,key=lambda c:(-c["breadth"],-c["median_p"])) if c["breadth"]>=C.MIN_BREADTH][:C.TOP_N]
    for c in top:
        if c["layer"]=="CEX" and c.get("coin_id"): enrich_cex_identity(c)
        outcomes.register(st,c["key"],c.get("price"),c.get("lifecycle",c["layer"]))
    def price_of(key):
        for c in cex+dex:
            if c["key"]==key:return c.get("price")
        return None
    outcomes.update(st,price_of)
    return top,cex,dex,passed

def run():
    t0=time.time(); st=_load(); boosted=dexscreener.boosts(); anns,ann_ok=news_rss.binance_announcements(); st["health"]["news_source_degraded"]=not ann_ok
    early_top,early_scanned,early_eligible=scan_early(st,boosted)
    alerts=[c for c in early_top if early.should_alert(st,c)]
    if alerts: report.send(report.build_early_alert(alerts))
    if os.environ.get("SPOT_EARLY_ONLY"):
        st["early_meta"]={"when":time.strftime("%d.%m %H:%M",time.gmtime(time.time()+10800)),"scanned":early_scanned,"eligible":early_eligible,"top":len(early_top),"duration_s":round(time.time()-t0)}
        _save(st); print(f"early radar tamam: {st['early_meta']}"); return
    top,cex,dex,passed=_run_growth(st,boosted,anns,ann_ok)
    meta={"when":time.strftime("%d.%m %H:%M",time.gmtime(time.time()+10800)),"n_cex":len(cex),"n_dex":len(dex),"n_pass":len(passed),"news_degraded":not ann_ok,"duration_s":None,
          "early_scanned":early_scanned,"early_eligible":early_eligible}
    report.send(report.build(top,meta,st,early_top=early_top))
    st["reports"].append({"ts":time.time(),"coins":[{"key":c["key"],"rank":i+1,"price":c.get("price"),"breadth":c["breadth"],"median_p":round(c["median_p"],3),"flags":c.get("flags"),"network":c.get("network"),"contract":c.get("token"),"venue":c.get("dex_id") or c.get("buy_venue")} for i,c in enumerate(top)],
                          "early":[{"key":c["key"],"stage":c.get("early_stage"),"score":c.get("early_score"),"mc":c.get("mc"),"first_mc":c.get("first_seen_mc")} for c in early_top]})
    meta["duration_s"]=round(time.time()-t0); st["meta"]=meta; _save(st)
    print(f"\nspot radar tamam: {meta['duration_s']}s | cex {len(cex)} dex {len(dex)} gecen {len(passed)} top {len(top)} | early {len(early_top)}")

if __name__=="__main__": run()
