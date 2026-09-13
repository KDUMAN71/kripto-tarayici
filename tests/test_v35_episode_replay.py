import pandas as pd

from research.build_runner_dataset_v2 import balance, controls, maps, runner_episodes
from research.reverse_engineering import snapshot_features


def _frame_1h(n=80, base=100.0, qv=1_000_000.0):
    opens = pd.date_range("2026-08-01", periods=n, freq="1h", tz="UTC")
    close_times = opens + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)
    return pd.DataFrame({
        "openTime": opens, "closeTime": close_times, "open": [base]*n,
        "high": [base*1.01]*n, "low": [base*0.99]*n, "close": [base]*n,
        "volume": [1000.0]*n, "quoteVolume": [qv]*n, "trades": [1000]*n,
        "tbBase": [500.0]*n, "tbQuote": [qv*0.5]*n, "ignore": [0]*n,
    })


def _frame_15m(n=120):
    opens = pd.date_range("2026-08-01", periods=n, freq="15min", tz="UTC")
    closes = opens + pd.Timedelta(minutes=15) - pd.Timedelta(milliseconds=1)
    vals = [100.0 + i*0.01 for i in range(n)]
    return pd.DataFrame({
        "openTime": opens, "closeTime": closes, "open": vals,
        "high": [v+0.2 for v in vals], "low": [v-0.2 for v in vals], "close": vals,
        "volume": [100.0]*n, "quoteVolume": [10_000.0]*n,
        "trades": [100]*n, "tbQuote": [5_000.0]*n,
    })


def test_episode_uses_close_timestamp_and_dedupes_one_pump():
    d = _frame_1h()
    d.loc[30, ["high", "close"]] = [111.0, 109.0]
    d.loc[31:33, ["high", "close"]] = [112.0, 110.0]
    d.loc[34, ["high", "close"]] = [125.0, 121.0]
    d.loc[35:, ["high", "low", "close"]] = [106.0, 104.0, 105.0]
    ev = runner_episodes("TESTUSDT", d, min_run=10.0)
    assert len(ev) == 1
    assert pd.Timestamp(ev[0]["cross_ts"]) == pd.Timestamp(d.loc[30, "closeTime"])
    assert pd.Timestamp(ev[0]["peak_ts"]) == pd.Timestamp(d.loc[34, "closeTime"])


def test_snapshot_is_past_only_and_uses_close_time():
    d = _frame_15m()
    a = snapshot_features(d, 100)
    d.loc[101:, "quoteVolume"] = 9_999_999_999.0
    d.loc[101:, "close"] = 999.0
    b = snapshot_features(d, 100)
    assert a == b
    assert pd.Timestamp(a["ts"]) == pd.Timestamp(d.loc[100, "closeTime"])
    assert a["quote_volume_24h"] == 96*10_000.0


def test_daily_cap_balances_dates():
    events=[]
    for day, strengths in [("2026-08-01", [100,90,80]), ("2026-08-02", [20,19,18])]:
        for hour, strength in enumerate(strengths):
            events.append({"cross_ts": pd.Timestamp(f"{day} {hour:02d}:59:59", tz="UTC").isoformat(), "episode_total_pct": strength})
    picked=balance(events,2,4)
    days=[pd.Timestamp(x["cross_ts"]).strftime("%Y-%m-%d") for x in picked]
    assert days.count("2026-08-01")==2 and days.count("2026-08-02")==2


def test_matched_control_rejects_future_runner():
    runner=_frame_1h(qv=2_000_000.0); runner.loc[30,["high","close"]]=[112.0,110.0]
    good=_frame_1h(qv=2_100_000.0); good.loc[31:54,"high"]=104.0
    bad=_frame_1h(qv=2_050_000.0); bad.loc[35,"high"]=120.0
    frames={"RUNUSDT":runner,"GOODUSDT":good,"BADUSDT":bad}; hm=maps(frames)
    event={"symbol":"RUNUSDT","cross_ts":runner.loc[30,"closeTime"].isoformat(),"quote_volume_1h":float(runner.loc[30,"quoteVolume"]),"_idx":30}
    c=controls(event,frames,hm,10.0,1)
    assert len(c)==1 and c[0]["symbol"]=="GOODUSDT" and c[0]["future_max_24h_pct"]<10.0
