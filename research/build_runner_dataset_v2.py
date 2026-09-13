"""V3.5 episode-first replay dataset (schema v2)."""
from __future__ import annotations
import argparse, json, math
from collections import defaultdict
from pathlib import Path
import pandas as pd
from scanner import config as C, data
from research.reverse_engineering import snapshot_features, excursion_from_entry

def pct(a,b):
    return (float(b)/float(a)-1)*100 if a else None

def klines(symbol, interval, start_ms, end_ms):
    rows=[]; cur=int(start_ms)
    while cur < end_ms:
        raw=data.get("/klines",{"symbol":symbol,"interval":interval,"startTime":cur,"endTime":int(end_ms),"limit":1500})
        if not raw: break
        rows += raw
        last=int(raw[-1][0])
        if last < cur: break
        cur=last+1
        if len(raw)<1500: break
    if not rows: return pd.DataFrame()
    d=pd.DataFrame(rows,columns=["openTime","open","high","low","close","volume","closeTime","quoteVolume","trades","tbBase","tbQuote","ignore"])
    for c in ["open","high","low","close","volume","quoteVolume","tbQuote"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d["trades"]=pd.to_numeric(d["trades"],errors="coerce")
    d["openTime"]=pd.to_datetime(d["openTime"],unit="ms",utc=True)
    d["closeTime"]=pd.to_datetime(d["closeTime"],unit="ms",utc=True)
    return d.drop_duplicates("openTime").sort_values("openTime").reset_index(drop=True)

def runner_episodes(symbol,d,min_run=10,baseline_h=24,future_h=24,cooldown_h=6):
    if d.empty or len(d)<baseline_h+future_h+2: return []
    out=[]; next_allowed=baseline_h
    for i in range(baseline_h,len(d)-future_h-1):
        if i < next_allowed: continue
        prior=d.iloc[i-baseline_h:i]
        low_idx=i-baseline_h+int(prior.low.to_numpy().argmin())
        base=float(d.iloc[low_idx].low); hi=float(d.iloc[i].high)
        cross=pct(base,hi)
        if cross is None or cross < min_run: continue
        fut=d.iloc[i+1:i+1+future_h]
        peak_idx=i+1+int(fut.high.to_numpy().argmax())
        peak=max(hi,float(fut.high.max()))
        if hi>=peak: peak_idx=i
        out.append({
            "kind":"runner","symbol":symbol,
            "baseline_ts":d.iloc[low_idx].closeTime.isoformat(),"baseline_price":base,
            "cross_ts":d.iloc[i].closeTime.isoformat(),"cross_price":float(d.iloc[i].close),
            "cross_run_pct":cross,"peak_ts":d.iloc[peak_idx].closeTime.isoformat(),
            "peak_price":peak,"episode_total_pct":pct(base,peak),
            "future_extension_pct":pct(float(d.iloc[i].close),peak),
            "quote_volume_1h":float(d.iloc[i].quoteVolume or 0),"_idx":i})
        next_allowed=max(i+cooldown_h,peak_idx+cooldown_h)
    return out

def balance(events,per_day,max_events):
    by=defaultdict(list)
    for e in events: by[pd.Timestamp(e["cross_ts"]).strftime("%Y-%m-%d")].append(e)
    buckets={k:sorted(v,key=lambda x:x["episode_total_pct"],reverse=True)[:per_day] for k,v in by.items()}
    out=[]; depth=0
    while True:
        added=False
        for day in sorted(buckets):
            if depth<len(buckets[day]):
                out.append(buckets[day][depth]); added=True
                if max_events and len(out)>=max_events: return sorted(out,key=lambda x:x["cross_ts"])
        if not added: break
        depth+=1
    return sorted(out,key=lambda x:x["cross_ts"])

def hkey(ts): return int(pd.Timestamp(ts).timestamp()//3600)
def maps(frames): return {s:{hkey(t):i for i,t in enumerate(d.closeTime)} for s,d in frames.items()}
def past_ret(d,i,b): return pct(float(d.iloc[i-b].close),float(d.iloc[i].close)) if i>=b else None
def fwd_max(d,i,b=24):
    f=d.iloc[i+1:min(len(d),i+1+b)]
    return pct(float(d.iloc[i].close),float(f.high.max())) if not f.empty else None

def controls(e,frames,hm,min_run,count=1):
    key=hkey(e["cross_ts"]); rq=max(float(e["quote_volume_1h"]),1); rd=frames[e["symbol"]]; ri=e["_idx"]; rr=past_ret(rd,ri,24) or 0
    cand=[]
    for s,d in frames.items():
        if s==e["symbol"]: continue
        i=hm.get(s,{}).get(key)
        if i is None or i<24 or i+24>=len(d): continue
        q=max(float(d.iloc[i].quoteVolume or 0),1); ratio=q/rq
        if not .2<=ratio<=5: continue
        fm=fwd_max(d,i,24)
        if fm is None or fm>=min_run: continue
        r24=past_ret(d,i,24)
        if r24 is None: continue
        dist=abs(math.log(ratio))+.04*abs(r24-rr)
        cand.append((dist,s,i,q,r24,fm))
    out=[]
    for rank,(_,s,i,q,r24,fm) in enumerate(sorted(cand)[:count],1):
        d=frames[s]
        out.append({"kind":"control","symbol":s,"matched_runner":e["symbol"],"control_rank":rank,
                    "cross_ts":d.iloc[i].closeTime.isoformat(),"cross_price":float(d.iloc[i].close),
                    "quote_volume_1h":q,"ret_24h_at_match":r24,"future_max_24h_pct":fm,"_idx":i})
    return out

def idx_at(d,ts):
    if d.empty: return None
    x=d.index[d.closeTime<=pd.Timestamp(ts)]
    return int(x[-1]) if len(x) else None

def attach_btc(snap,btc):
    out=dict(snap); i=idx_at(btc,snap["ts"])
    if i is None: return out
    b=snapshot_features(btc,i)
    for tf in ["1h","3h","6h","24h"]:
        cv,bv=snap.get("ret_"+tf),b.get("ret_"+tf)
        out["btc_ret_"+tf]=bv
        out["rel_btc_"+tf]=(cv-bv) if cv is not None and bv is not None else None
    return out

def oi(symbol,ts):
    at=pd.Timestamp(ts); raw=data.get_futures_data("/openInterestHist",{
        "symbol":symbol,"period":"1h","startTime":int((at-pd.Timedelta(hours=30)).timestamp()*1000),
        "endTime":int(at.timestamp()*1000),"limit":100})
    if not raw: return {"available":False}
    vals=[]
    for x in raw:
        try:
            t=pd.to_datetime(int(x["timestamp"]),unit="ms",utc=True)
            if t<=at: vals.append((t,float(x["sumOpenInterest"])))
        except Exception: pass
    vals.sort()
    if len(vals)<2: return {"available":False}
    def ch(h): return pct(vals[-1-h][1],vals[-1][1]) if len(vals)>h else None
    return {"available":True,"oi_change_1h_pct":ch(1),"oi_change_4h_pct":ch(4),"oi_change_24h_pct":ch(24),"last_ts":vals[-1][0].isoformat()}

def funding(symbol,ts):
    at=pd.Timestamp(ts); raw=data.get("/fundingRate",{
        "symbol":symbol,"startTime":int((at-pd.Timedelta(hours=80)).timestamp()*1000),
        "endTime":int(at.timestamp()*1000),"limit":100})
    if not raw: return {"available":False}
    vals=[]
    for x in raw:
        try:
            t=pd.to_datetime(int(x["fundingTime"]),unit="ms",utc=True)
            if t<=at: vals.append((t,float(x["fundingRate"])))
        except Exception: pass
    vals.sort()
    if not vals: return {"available":False}
    last24=[v for t,v in vals if t>=at-pd.Timedelta(hours=24)]
    prev=vals[-2][1] if len(vals)>1 else None; latest=vals[-1][1]
    return {"available":True,"funding_latest":latest,"funding_prev":prev,
            "funding_delta":latest-prev if prev is not None else None,
            "funding_mean_24h":sum(last24)/len(last24) if last24 else None,
            "last_ts":vals[-1][0].isoformat()}

def legacy_proxy(s):
    q,r,v,m=s.get("quote_volume_24h"),s.get("ret_24h"),s.get("vol_ratio_20"),s.get("ret_3h")
    return {"scope":"proxy_only_not_full_engine_replay",
            "min_quote_volume_ok":q>=C.MIN_QUOTE_VOLUME_24H if q is not None else None,
            "max_abs_24h_ok":abs(r)<=C.MAX_ABS_24H_CHANGE_TECH if r is not None else None,
            "momentum_3h_long_ok":m>=C.MOMENTUM_PRE_3H_PCT if m is not None else None,
            "momentum_vol_ok":v>=C.MOMENTUM_PRE_VOL_MULT if v is not None else None}

def enrich(e,btc,warmup_h=72):
    cross=pd.Timestamp(e["cross_ts"])
    d=klines(e["symbol"],"15m",int((cross-pd.Timedelta(hours=warmup_h)).timestamp()*1000),
             int((cross+pd.Timedelta(hours=24)).timestamp()*1000))
    out={k:v for k,v in e.items() if not k.startswith("_")}
    if d.empty: out["enrichment_error"]="no_15m_data"; return out
    i=idx_at(d,cross)
    if i is None: out["enrichment_error"]="no_closed_15m_at_cross"; return out
    out["alignment_delta_ms"]=int(abs((cross-d.iloc[i].closeTime).total_seconds())*1000)
    out["features_t0"]=attach_btc(snapshot_features(d,i),btc)
    out["execution_24h"]=excursion_from_entry(d,i,horizon_bars=96)
    out["legacy_prefilter_proxy_t0"]=legacy_proxy(out["features_t0"])
    path=[]
    for h in [24,12,6,3,1,0]:
        target=cross-pd.Timedelta(hours=h); j=idx_at(d,target)
        if j is not None:
            s=attach_btc(snapshot_features(d,j),btc); s["hours_before_cross"]=h; s["target_ts"]=target.isoformat(); path.append(s)
    out["feature_path"]=path; out["open_interest"]=oi(e["symbol"],cross); out["funding"]=funding(e["symbol"],cross)
    return out

def build(days,min_run,max_events,max_symbols,events_per_day=8,controls_per_runner=1):
    now=pd.Timestamp.now(tz="UTC").floor("h"); start=now-pd.Timedelta(days=days+4)
    syms=data.exchange_perp_symbols() or []
    if max_symbols: syms=syms[:max_symbols]
    frames={}; failures=[]; raw=[]
    for n,s in enumerate(syms,1):
        d=klines(s,"1h",int(start.timestamp()*1000),int(now.timestamp()*1000))
        if d.empty: failures.append(s)
        else: frames[s]=d; raw += runner_episodes(s,d,min_run=min_run)
        if n%25==0: print(f"episode scan {n}/{len(syms)} | raw={len(raw)}")
    cutoff=now-pd.Timedelta(days=days); raw=[e for e in raw if pd.Timestamp(e["cross_ts"])>=cutoff]
    runners=balance(raw,events_per_day,max_events); hm=maps(frames)
    rows=[]; missing=0
    for e in runners:
        rows.append(e); c=controls(e,frames,hm,min_run,controls_per_runner); rows += c; missing += controls_per_runner-len(c)
    btc=klines("BTCUSDT","15m",int((cutoff-pd.Timedelta(hours=80)).timestamp()*1000),int(now.timestamp()*1000))
    enriched=[]
    for i,e in enumerate(rows,1):
        enriched.append(enrich(e,btc))
        if i%10==0: print(f"15m enrich {i}/{len(rows)}")
    availability={"runner_count":sum(e.get("kind")=="runner" for e in enriched),
                  "control_count":sum(e.get("kind")=="control" for e in enriched),
                  "oi_available_runners":sum(e.get("kind")=="runner" and e.get("open_interest",{}).get("available",False) for e in enriched),
                  "funding_available_runners":sum(e.get("kind")=="runner" and e.get("funding",{}).get("available",False) for e in enriched),
                  "aligned_within_1s":sum("alignment_delta_ms" in e and e["alignment_delta_ms"]<=1000 for e in enriched)}
    return {"meta":{"schema_version":2,"generated_at":pd.Timestamp.now(tz="UTC").isoformat(),
                    "lookback_days":days,"min_run_pct":min_run,"symbols_scanned":len(syms),"failures":failures,
                    "raw_episode_count":len(raw),"selected_runner_count":len(runners),"events_per_day_cap":events_per_day,
                    "controls_per_runner":controls_per_runner,"missing_controls":missing,
                    "event_definition":"first 1h threshold-cross above trailing 24h low; candle-close timestamp",
                    "feature_rule":"closed candles only; 72h warmup; BTC-relative + point-in-time OI/funding",
                    "label_warning":"future data only labels peak/extension, dedupes episode, and verifies negative controls",
                    "survivorship_bias_warning":"current exchangeInfo omits delisted contracts","availability":availability},
            "events":enriched}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--days",type=int,default=30); p.add_argument("--min-run-pct",type=float,default=10)
    p.add_argument("--max-events",type=int,default=240); p.add_argument("--events-per-day",type=int,default=8)
    p.add_argument("--controls-per-runner",type=int,default=1); p.add_argument("--max-symbols",type=int)
    p.add_argument("--output",default="artifacts/v35_episode_replay_v2.json"); a=p.parse_args()
    payload=build(a.days,a.min_run_pct,a.max_events,a.max_symbols,a.events_per_day,a.controls_per_runner)
    path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"wrote {path} | runners={payload['meta']['selected_runner_count']} controls={payload['meta']['availability']['control_count']}")
if __name__=="__main__": main()
