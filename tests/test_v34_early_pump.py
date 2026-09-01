"""Erken pump izi: mevcut pump radarinin TERSI mantik.

check_pump "fiyat kostu mu?" diye sorar ve dogasi geregi gec kalir.
check_early_pump "para giriyor ama fiyat hala sakin mi?" diye sorar.
Buradaki testler o tersligi ve kalibre esikleri kilitler.
"""
import pandas as pd
import pytest

from scanner import config as C
from scanner import radars


def _k15(n=60, close=100.0, vol=100.0, taker_ratio=0.6, last_vol_mult=2.0):
    """Son bar hacmi ortalamanin last_vol_mult katı olan 15d serisi."""
    vols = [vol] * (n - 1) + [vol * last_vol_mult]
    return pd.DataFrame({
        "openTime": pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC"),
        "open": [close] * n, "high": [close * 1.002] * n,
        "low": [close * 0.998] * n, "close": [close] * n,
        "volume": vols, "quoteVolume": [v * close for v in vols],
        "tbBase": [v * taker_ratio for v in vols],
    })


@pytest.fixture
def patched(monkeypatch):
    """Ag cagrilarini kontrollu degerlerle degistir."""
    state = {"oi": 3.0, "k15": _k15(), "rsi": 55.0}

    def fake_oi(symbol, period="1h", limit=25):
        return state["oi"]

    def fake_klines(symbol, interval, limit):
        return state["k15"] if interval == "15m" else _k15(n=40)

    def fake_analyze(df, **kw):
        vols = df["volume"]
        return {"price": float(df["close"].iloc[-1]), "atr": 0.5,
                "vol_ratio": float(vols.iloc[-1] / vols.iloc[:-1].mean()),
                "rsi": state["rsi"], "closed": df}

    monkeypatch.setattr(radars.data, "oi_change_pct", fake_oi)
    monkeypatch.setattr(radars.data, "klines", fake_klines)
    monkeypatch.setattr(radars, "analyze", fake_analyze)
    return state


def test_fires_when_oi_builds_while_price_is_still_calm(patched):
    r = radars.check_early_pump("TESTUSDT", 10_000_000, {})
    assert r is not None
    assert r["oi_chg"] == 3.0
    assert abs(r["run1h"]) <= C.EARLY_PUMP_MAX_PRICE_RUN_1H


def test_silent_when_oi_is_flat(patched):
    patched["oi"] = 0.2                      # sakin piyasa medyani civari
    assert radars.check_early_pump("TESTUSDT", 10_000_000, {}) is None


def test_silent_when_price_already_ran(patched):
    """Fiyat kosmussa artik 'erken' degil - katmanin tum varlik sebebi bu."""
    n = 60
    closes = [100.0] * (n - 5) + [100.0, 103.0, 106.0, 109.0, 112.0]
    df = _k15(n=n)
    df["close"] = closes
    patched["k15"] = df
    assert radars.check_early_pump("TESTUSDT", 10_000_000, {}) is None


def test_silent_when_rsi_leaves_no_entry_room(patched):
    patched["rsi"] = C.EARLY_PUMP_RSI_MAX + 5
    assert radars.check_early_pump("TESTUSDT", 10_000_000, {}) is None


def test_silent_when_taker_pressure_is_absent(patched):
    patched["k15"] = _k15(taker_ratio=0.40)
    assert radars.check_early_pump("TESTUSDT", 10_000_000, {}) is None


def test_cooldown_blocks_repeat_alert(patched):
    now = 10_000_000
    last = {"TESTUSDT": now - 60}
    assert radars.check_early_pump("TESTUSDT", now, last) is None


def test_candidate_pool_excludes_already_pumped(patched):
    tickers = pd.DataFrame({
        "symbol": ["CALMUSDT", "PUMPEDUSDT", "THINUSDT"],
        "priceChangePercent": [3.0, C.EARLY_PUMP_MAX_24H + 10, 1.0],
        "quoteVolume": [50e6, 50e6, 1e6],
    })
    picked = set(radars.early_pump_candidates(tickers)["symbol"])
    assert "CALMUSDT" in picked
    assert "PUMPEDUSDT" not in picked   # cok kosmus
    assert "THINUSDT" not in picked     # likit degil


def test_thresholds_stay_in_measured_range():
    """Esikler olculen dagilimla tutarli kalsin (bkz. config'teki olcum notu)."""
    assert 0.8 <= C.EARLY_PUMP_OI_MIN_1H <= 2.0   # sakin maks 0.80, hareketli medyan 1.44
    assert 0.50 <= C.EARLY_PUMP_TAKER_MIN <= 0.56  # gercek band %43-54
