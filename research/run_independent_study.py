"""Run Phase B5 matched winner/non-winner study from Phase B2 artifact."""
import argparse,json,math
from pathlib import Path
from collections import defaultdict
import pandas as pd
from research.build_runner_dataset_v2 import klines
from research.independent_controls import matched_controls,_index_at,_pre_features

def study(source,output,max_opportunities=0):
    ops=json.loads(Path(source).read_text())["opportunities"]
    ops=sorted(ops,key=lambda o:(-o["max_excursion_pct"],o["start_ts"]))
    if max_opportunities:ops=ops[:max_opportunities]
    symbols=sorted({o["symbol"] for o in ops})
    # Include the complete contemporaneous market, not just winning symbols.
    from scanner.data import exchange_perp_symbols
    universe=exchange_perp_symbols() or []
    t0=min(pd.Timestamp(o["start_ts"]) for o in ops)-pd.Timedelta(days=2)
    t1=max(pd.Timestamp(o["start_ts"]) for o in ops)+pd.Timedelta(days=9)
    frames={}; failures=[]
    for n,s in enumerate(universe,1):
        d=klines(s,"1h",int(t0.timestamp()*1000),int(t1.timestamp()*1000))
        if d.empty:failures.append(s)
        else:frames[s]=d
        if n%50==0:print("fetched",n,len(universe),flush=True)
    pairs=[]; missing=defaultdict(int)
    for n,o in enumerate(ops,1):
        # 7-day comparable fully matured directional outcome.
        if o["symbol"] not in frames:missing["winner_history"]+=1;continue
        matches=matched_controls(o,frames,horizon_hours=168,threshold_pct=25,count=3)
        if not matches:missing["no_matched_control"]+=1;continue
        wi=_index_at(frames[o["symbol"]],o["start_ts"])
        wf=_pre_features(frames[o["symbol"]],wi)
        if wf is None:missing["winner_warmup"]+=1;continue
        for m in matches:
            pairs.append({"opportunity_id":o["opportunity_id"],"symbol":o["symbol"],
              "side":o["side"],"anchor_ts":o["start_ts"],
              "max_excursion_pct_LABEL_ONLY":o["max_excursion_pct"],
              "winner":wf,"control_symbol":m["control_symbol"],
              "control":m["pre_anchor"],"control_outcome_LABEL_ONLY":m["future_excursion_pct_LABEL_ONLY"]})
        if n%50==0:print("matched",n,len(ops),"pairs",len(pairs),flush=True)
    def median(a):
        a=sorted(a);return a[len(a)//2] if a else None
    stats={}
    for k in ("quote_volume_24h","return_24h","history_bars"):
        w=[p["winner"][k] for p in pairs if p["winner"].get(k) is not None]
        c=[p["control"][k] for p in pairs if p["control"].get(k) is not None]
        stats[k]={"winner_median":median(w),"control_median":median(c),
                  "paired_winner_greater_rate":sum(a>b for a,b in zip(w,c))/len(w) if w and len(w)==len(c) else None}
    result={"meta":{"winner_episodes_requested":len(ops),"symbols_in_universe":len(universe),
       "symbols_loaded":len(frames),"fetch_failures":failures,"pairs":len(pairs),
       "unique_winners_matched":len({p["opportunity_id"] for p in pairs}),
       "missing":dict(missing),"scope":"exploratory; no ACTIVE profitability claims",
       "limitations":"current listed perpetuals only; episode anchor may not precede move; matched 7d negative controls"},
       "comparison":stats,"pairs":pairs}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,default=str))
    print("RESULT",json.dumps({k:v for k,v in result.items() if k!="pairs"},default=str),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    p.add_argument("--max-opportunities",type=int,default=0);a=p.parse_args()
    study(a.source,a.output,a.max_opportunities)
