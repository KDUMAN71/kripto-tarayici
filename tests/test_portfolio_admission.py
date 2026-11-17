from scanner.portfolio_admission import can_activate,active_count,rank_active


def test_cap_blocks_eleventh_active():
    s={str(i):{"status":"ACTIVE"} for i in range(10)}
    assert active_count(s)==10
    assert not can_activate(s)
    s["0"]["status"]="STOPPED"
    assert can_activate(s)


def test_watch_states_do_not_consume_slots():
    assert can_activate({"x":{"status":"WATCH"}},limit=1)


def test_priority_prefers_higher_rr_with_stable_ties():
    x=[("B",{"rr2":2,"score":8}),("A",{"rr2":3,"score":1}),("C",{"rr2":2,"score":8})]
    assert [k for k,_ in rank_active(x)]==["A","B","C"]
