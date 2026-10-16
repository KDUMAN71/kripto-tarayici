from research.opportunity_identity import opportunity_identity, duplicate_diagnostics

def test_identity_is_stable_and_direction_sensitive():
    a = {"side": "LONG", "setup_type": "breakout_retest", "htf_support": 100}
    assert opportunity_identity("BTCUSDT", a) == opportunity_identity("BTCUSDT", dict(a))
    assert opportunity_identity("BTCUSDT", a) != opportunity_identity("BTCUSDT", {**a, "side": "SHORT"})

def test_shadow_only_diagnostic():
    a = {"status": "ACTIVE", "side": "LONG", "setup_type": "breakout_retest", "htf_support": 100}
    assert duplicate_diagnostics({"BTCUSDT": a, "ETHUSDT": a}) == {}
