import scanner.outcomes as OUT


def _reset(monkeypatch):
    monkeypatch.setattr(OUT, "_L", {"episodes": []})


def test_episode_keeps_candidate_id_across_lifecycle(monkeypatch):
    _reset(monkeypatch)
    e = OUT.start("METISUSDT", "PRE_RUNNER", {"price": 3.0}, ts=100)
    cid = e["candidate_id"]
    OUT.transition("METISUSDT", "WATCH", ts=200)
    OUT.transition("METISUSDT", "ACTIVE", ts=300)
    assert OUT._L["episodes"][-1]["candidate_id"] == cid
    assert OUT._L["episodes"][-1]["status"] == "ACTIVE"


def test_rejected_episode_closes_and_new_episode_can_start(monkeypatch):
    _reset(monkeypatch)
    a = OUT.start("XUSDT", "PRE_RUNNER", {"price": 1.0}, ts=100)
    OUT.close("XUSDT", "REJECTED", "bad geometry", ts=200)
    b = OUT.start("XUSDT", "PRE_RUNNER", {"price": 1.1}, ts=300)
    assert a["candidate_id"] != b["candidate_id"]
    assert len(OUT._L["episodes"]) == 2


def test_excursions_track_both_favorable_and_adverse(monkeypatch):
    _reset(monkeypatch)
    OUT.start("XUSDT", "ACTIVE", {"price": 100}, ts=100)
    OUT.set_trade_geometry("XUSDT", {"status": "ACTIVE", "side": "LONG",
                                     "entry_ref": 100, "sl": 98, "tp1": 103, "tp2": 105}, ts=100)
    OUT.update_excursion("XUSDT", 104, ts=110)
    OUT.update_excursion("XUSDT", 97, ts=120)
    e = OUT._L["episodes"][-1]
    assert e["mfe_pct"] == 4.0
    assert e["mae_pct"] == 3.0


def test_initial_features_are_not_overwritten(monkeypatch):
    _reset(monkeypatch)
    OUT.start("XUSDT", "PRE_RUNNER", {"price": 1, "opportunity_score": 4}, ts=100)
    OUT.transition("XUSDT", "PRE_RUNNER", features={"price": 2, "opportunity_score": 6}, ts=200)
    e = OUT._L["episodes"][-1]
    assert e["initial_features"]["price"] == 1
    assert e["latest_features"]["price"] == 2


def test_ledger_is_bounded(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setattr(OUT, "MAX_EPISODES", 2)
    for i in range(3):
        s = f"X{i}USDT"
        OUT.start(s, "PRE_RUNNER", {"price": 1}, ts=100+i)
        OUT.close(s, "EXPIRED", ts=200+i)
    assert len(OUT._L["episodes"]) == 2
