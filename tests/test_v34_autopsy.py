"""V3.4 Runner Autopsy testleri: dedupe, sinir, terminal ayrinti, siniflama, rapor."""
import copy
import pandas as pd
import pytest
from scanner import autopsy as AU


@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    monkeypatch.setattr(AU, "PATH", str(tmp_path / "ra.json"))
    AU.load()
    yield


def _series(chgs, base=100.0):
    cl = [base]
    for c in chgs:
        cl.append(cl[-1] * (1 + c / 100.0))
    return cl


class _FakeData:
    def __init__(self, closes):
        self.closes = closes
    def klines(self, sym, itv, lim):
        return pd.DataFrame({"close": self.closes})


def test_dedupe_ayni_kova_yeni_satir_acmaz():
    t0 = 1_700_000_000
    AU.record("AAAUSDT", "max_abs", "r1", ts=t0)
    AU.record("AAAUSDT", "max_abs", "r1", ts=t0 + 60)
    rows = AU._A["symbols"]["AAAUSDT"]
    assert len(rows) == 1 and rows[0]["n"] == 1
    AU.record("AAAUSDT", "max_abs", "r1", ts=t0 + AU.TS_BUCKET_S + 1)
    assert len(rows) == 1 and rows[0]["n"] == 2
    AU.record("AAAUSDT", "liquidity", "r2", ts=t0 + 2 * AU.TS_BUCKET_S)
    assert len(AU._A["symbols"]["AAAUSDT"]) == 2


def test_sinirlar_ve_sinyalli_sembol_korunur():
    for i in range(AU.MAX_ENTRIES_PER_SYMBOL + 5):
        AU.record("BBBUSDT", "s%d" % i, "r", ts=1_700_000_000 + i * AU.TS_BUCKET_S)
    assert len(AU._A["symbols"]["BBBUSDT"]) == AU.MAX_ENTRIES_PER_SYMBOL
    AU._A["sig_seen"]["KEEPUSDT"] = {"status": "EARLY", "ts": 0}
    AU.record("KEEPUSDT", "signal", "EARLY", ts=1)
    for i in range(AU.MAX_SYMBOLS + 20):
        AU.record("S%04dUSDT" % i, "liquidity", "r", ts=2_000_000_000 + i)
    assert len(AU._A["symbols"]) <= AU.MAX_SYMBOLS
    assert "KEEPUSDT" in AU._A["symbols"]


def test_terminal_gecis_ayrintili_ve_sig_seen_temizligi():
    st = {"signals": {"CCCUSDT": {"status": "EARLY", "side": "LONG", "created": 1000}}}
    AU.observe_signals(st, ts=1000 + 3600)
    st["signals"]["CCCUSDT"]["status"] = "EXPIRED"
    AU.observe_signals(st, ts=1000 + 36 * 3600)
    rows = AU._A["symbols"]["CCCUSDT"]
    assert rows[-1]["stage"] == "signal"
    assert "EXPIRED" in rows[-1]["reason"] and "LONG" in rows[-1]["reason"]
    assert rows[-1]["x"]["age_h"] == 36.0
    AU.observe_signals({"signals": {}}, ts=1000 + 40 * 3600)
    assert "CCCUSDT" not in AU._A["sig_seen"]


def test_siniflama_ani_merdiven_devam():
    sudden = _series([1, -2, 0.5, 1, 40, 0.5, -1, 0.3])
    assert AU._classify(_FakeData(sudden), "X")[0] == "ANI-ONCUSUZ"
    stair = _series([3, 5, 7, 9, 12, 8, 4, 2])
    assert AU._classify(_FakeData(stair), "X")[0] == "MERDIVEN"
    cont = _series([2, 1, 30, 5, 8, 6, 4, 3])
    assert AU._classify(_FakeData(cont), "X")[0] == "DEVAM-KOSUCUSU"


def test_haftalik_rapor_kapisi_ve_sifirlama():
    t0 = 1_700_000_000
    tick = pd.DataFrame({"symbol": ["AAAUSDT", "BBBUSDT"], "lastPrice": [1.0, 2.0]})
    assert AU.maybe_weekly_report({}, tick, None, ts=t0) is None
    assert AU._A["week_baseline"] is not None
    assert AU.maybe_weekly_report({}, tick, None, ts=t0 + 3600) is None
    tick2 = pd.DataFrame({"symbol": ["AAAUSDT", "BBBUSDT"], "lastPrice": [1.5, 2.0]})
    fk = _FakeData(_series([2, 1, 30, 5, 8, 6, 4, 3]))
    rep = AU.maybe_weekly_report({"pump_alerts": {"AAAUSDT": 1}}, tick2, fk, ts=t0 + 8 * 86400)
    assert rep is not None and "AAAUSDT" in rep and "+%50" in rep
    assert "pump-izi" in rep and "momentum motoru adayi" in rep
    assert AU._A["week_baseline"]["px"]["AAAUSDT"] == 1.5


def test_state_sozlugune_dokunulmaz():
    st = {"signals": {"DDDUSDT": {"status": "EARLY", "side": "LONG", "created": 0}},
          "pump_alerts": {}}
    snap = copy.deepcopy(st)
    AU.record("DDDUSDT", "veto", "x", ts=100)
    AU.observe_signals(st, ts=100)
    AU.maybe_weekly_report(st, pd.DataFrame({"symbol": ["DDDUSDT"], "lastPrice": [1.0]}), None, ts=100)
    assert st == snap
