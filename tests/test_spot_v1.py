import ast, os, json, time
import pytest
from spot import gates, ranking, diffusion, structure, outcomes, identity
from spot import config as C


def _cand(layer="DEX", **kw):
    d = {"layer": layer, "key": "x", "symbol": "TST", "price": 1.0, "mc": 5e6,
         "liq": 3e5, "vol24": 5e5, "ch24": 10.0, "age_h": 72.0, "low7": 0.8}
    d.update(kw); return d


def test_t1_honeypot_eliminated():
    ok, why, _ = gates.apply(_cand(), None, {"is_honeypot": "1"}, False)
    assert not ok and "honeypot" in " ".join(why)


def test_t2_goplus_silent_dex_barred_cex_flagged():
    ok, why, fl = gates.apply(_cand(), None, None, False)
    assert not ok and "security_unverified" in fl
    ok2, _, fl2 = gates.apply(_cand(layer="CEX"), None, None, False)
    assert ok2 and "security_unverified" in fl2


def test_t3_liquidity_drop():
    ok, why, _ = gates.apply(_cand(liq=200_000), {"liq": 300_000}, {}, False)
    assert not ok and "likidite" in why[0]


def test_t4_two_manip_flags_veto_one_flag_pass():
    c = _cand(buys24=5000, sells24=5000)
    ok, _, fl = gates.apply(c, None, {}, True)      # wash + paid_promo
    assert not ok and len([f for f in fl if f in ("wash_suspect", "paid_promo")]) >= 2
    c2 = _cand(buys24=5000, sells24=5000)
    ok2, _, fl2 = gates.apply(c2, None, {}, False)  # tek bayrak
    assert ok2 and "wash_suspect" in fl2


def test_t5_extended():
    ok, why, _ = gates.apply(_cand(ch24=200.0), None, {}, False)
    assert not ok and "EXTENDED" in why[0]


def test_t6_completeness_gate():
    c = _cand(); c.update({f: None for f in ranking.FACTORS})
    c["f_volmc"] = 0.5; c["f_buy"] = 1.0
    ranking.percentiles([c]); ranked = ranking.rank([c])
    assert ranked == []


def test_t7_breadth_beats_median():
    a = _cand(key="a"); b = _cand(key="b")
    for i, f in enumerate(ranking.FACTORS):
        a[f] = 0.9 if i < 5 else None       # 5 guclu faktor
        b[f] = 0.95 if i < 3 else (0.1 if i < 5 else None)  # 3 cok guclu + 2 zayif
    pool = [a, b] + [_cand(key=f"n{j}", **{f: 0.2 for f in ranking.FACTORS}) for j in range(8)]
    ranking.percentiles(pool)
    r = ranking.rank(pool)
    assert r[0]["key"] == "a"


def test_t8_no_scanner_import():
    root = os.path.join(os.path.dirname(__file__), "..", "spot")
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".py"): continue
            tree = ast.parse(open(os.path.join(dirpath, fn)).read())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import): names = [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom): names = [node.module or ""]
                assert not any(n.split(".")[0] == "scanner" for n in names), f"{fn} scanner import ediyor"


def test_t9_state_fifo(tmp_path, monkeypatch):
    monkeypatch.setenv("SPOT_STATE_DIR", str(tmp_path))
    import importlib
    from spot import main as m
    importlib.reload(m)
    st = {"snapshots": {"k": [{"d": f"2026-01-{i:02d}"} for i in range(1, 33)]}, "reports": [], "outcomes": {}, "health": {}}
    m._save(st)
    st2 = m._load()
    assert len(st2["snapshots"]["k"]) == C.MAX_SNAPSHOTS


def test_t10_generic_ticker_news_skipped():
    q = identity.news_query(identity.build("", "AI"))
    assert q is None
    q2 = identity.news_query(identity.build("Snorter Bot", "SNORT"))
    assert "Snorter Bot" in q2


def test_t11_outcome_fill_and_cohort():
    st = {"outcomes": {}}
    outcomes.register(st, "k1", 1.0, "FRESH")
    st["outcomes"]["k1"]["entered_ts"] -= 25 * 3600
    outcomes.update(st, lambda k: 1.6)
    o = st["outcomes"]["k1"]
    assert o["t24"] is not None and o["hit50"] and o["mfe"] >= 0.6
    cs = outcomes.cohort_stats(st)
    assert cs["FRESH"]["n"] == 1


def test_t12_report_caps_and_health(monkeypatch):
    from spot import report
    tops = []
    for i in range(15):
        c = _cand(key=f"k{i}"); c.update({"breadth": 5, "median_p": 0.8, "lifecycle": "FRESH"})
        tops.append(c)
    txt = report.build(tops[:C.TOP_N], {"when": "x", "n_cex": 1, "n_dex": 1, "n_pass": 15, "news_degraded": True}, {"outcomes": {}})
    assert "10)" in txt and "11)" not in txt and "duyuru kaynagi bozuk" in txt


def test_structure_score_shape():
    up = [{"o": i, "h": i + 1.2, "l": i - 0.5 + i * 0.02, "c": i + 1, "v": 1} for i in range(1, 60)]
    s = structure.score(up)
    assert s is not None and 0 <= s <= 1


def test_diffusion_labels():
    d = diffusion.evaluate(8, ["a.com", "b.com", "c.com"], 12, [1, 1, 1], 10.0, False, False)
    assert d["label"] == "ilgi fiyatin onunde"
    d2 = diffusion.evaluate(8, ["a.com"], 8, [1], 120.0, False, False)
    assert d2["label"] == "fiyatlanmis"


def test_cex_layer_completeness_threshold():
    c = _cand(layer="CEX")
    c.update({f: None for f in ranking.FACTORS})
    c["f_volmc"] = 0.5; c["f_volp"] = 1.2; c["f_struct"] = 0.6
    pool = [c] + [_cand(key=f"z{i}", layer="CEX", f_volmc=0.1 * i, f_volp=1.0, f_struct=0.3) for i in range(4)]
    for x in pool[1:]:
        for f in ranking.FACTORS:
            x.setdefault(f, None)
    ranking.percentiles(pool)
    assert any(x["key"] == "x" for x in ranking.rank(pool))
