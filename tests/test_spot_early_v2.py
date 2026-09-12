import time
from spot import early, report, config as C


def _pool(**kw):
    d={"network":"solana","token":"So111","pool":"P1","name":"RAYCAT / SOL","created_at":"2026-09-01T00:00:00Z",
       "mc":80_000,"fdv":80_000,"liq":20_000,"vol24":100_000,"ch24":18.0,"price":0.00008}
    d.update(kw); return d


def _cand(**kw):
    c=early.build_candidate(_pool())
    c.update({"buy_ratios":[0.66,0.64,0.61],"tx_h1":75,"ch1":6.0,"ch6":22.0,"holders":900,"flags":[],
              "first_seen_mc":55_000,"news24":2,"dex_id":"raydium","pair_address":"PAIR"})
    c.update(kw); return c


def test_microcap_50_100k_is_eligible():
    assert C.EARLY_MC_MIN <= 50_000 < C.EARLY_MC_MAX
    assert early.eligible_pool(_pool(mc=70_000,liq=18_000,vol24=90_000))


def test_raycast_like_setup_becomes_early_opportunity():
    c=_cand()
    stage=early.classify(c,prev={"mc":60_000,"liq":16_000,"holders":800})
    assert stage=="EARLY_OPPORTUNITY"
    assert c["early_score"]>=C.EARLY_OPPORTUNITY_SCORE


def test_chase_after_4x_is_not_new_opportunity():
    c=_cand(mc=500_000,first_seen_mc=80_000,ch24=90.0)
    stage=early.classify(c,prev={"mc":350_000,"liq":50_000,"holders":800})
    assert stage!="EARLY_OPPORTUNITY"
    assert any("chase" in r for r in c["early_risks"])


def test_low_liquidity_microcap_is_rejected():
    assert not early.eligible_pool(_pool(mc=80_000,liq=3_000,vol24=100_000))


def test_alert_dedupes_for_six_hours():
    st={"early_seen":{"solana:So111":{"first_ts":time.time(),"first_mc":50_000,"last_alert_stage":None,"last_alert_ts":None}}}
    c=_cand(key="solana:So111",early_stage="EARLY_OPPORTUNITY")
    assert early.should_alert(st,c)
    assert not early.should_alert(st,c)


def test_telegram_chunking_never_truncates():
    text="\n\n".join(["X"*900 for _ in range(10)])
    parts=report._chunks(text,limit=3900)
    assert len(parts)>1
    assert all(len(p)<=3900 for p in parts)
    assert sum(p.count("X") for p in parts)==9000


def test_early_report_contains_contract_first_seen_and_stage():
    c=_cand(early_stage="EARLY_OPPORTUNITY",early_score=8.0)
    txt=report.build_early_alert([c])
    assert "EARLY OPPORTUNITY" in txt
    assert "ilk gorulen" in txt
    assert "So111" in txt
    assert "raydium" in txt
