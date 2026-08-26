"""Binance Futures public veri katmanı.

Birden fazla host dener: fapi.binance.com bazi bolgelerden (ABD dahil)
engellidir; www.binance.com uzerindeki ayni public endpoint cogu zaman
calisir. Hicbiri calismazsa saglik alarmi icin None doner.
"""
import time
import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

HOSTS = [
    "https://www.binance.com/fapi/v1",
    "https://fapi.binance.com/fapi/v1",
    "https://fapi1.binance.com/fapi/v1",
    "https://fapi2.binance.com/fapi/v1",
]
FUTURES_DATA_HOSTS = [
    "https://www.binance.com/futures/data",
    "https://fapi.binance.com/futures/data",
]

_working_host = None


def _try_hosts(hosts, path, params):
    global _working_host
    ordered = hosts[:]
    if _working_host in ordered:
        ordered.remove(_working_host)
        ordered.insert(0, _working_host)
    for host in ordered:
        for attempt in range(2):
            try:
                r = requests.get(host + path, params=params, headers=HEADERS, timeout=15)
                if r.status_code == 200:
                    _working_host = host
                    return r.json()
                if r.status_code in (418, 429):  # rate limit
                    time.sleep(3)
                    continue
                break  # 451/403 vb -> siradaki host
            except requests.RequestException:
                time.sleep(0.5)
    return None


def get(path, params=None):
    data = _try_hosts(HOSTS, path, params)
    if data is not None:
        time.sleep(0.12)  # nazik rate-limit
    return data


def get_futures_data(path, params=None):
    data = _try_hosts(FUTURES_DATA_HOSTS, path, params)
    if data is not None:
        time.sleep(0.12)
    return data


def exchange_perp_symbols():
    ex = get("/exchangeInfo")
    if not ex:
        return None
    return sorted(
        s["symbol"] for s in ex.get("symbols", [])
        if s.get("contractType") == "PERPETUAL"
        and s.get("quoteAsset") == "USDT"
        and s.get("status") == "TRADING"
    )


def ticker_24h():
    t = get("/ticker/24hr")
    if not t:
        return None
    df = pd.DataFrame(t)
    for c in ["lastPrice", "priceChangePercent", "quoteVolume", "highPrice", "lowPrice"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def klines(symbol, interval, limit):
    data = get("/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    if not data:
        return None
    df = pd.DataFrame(data, columns=[
        "openTime", "open", "high", "low", "close", "volume", "closeTime",
        "quoteVolume", "trades", "tbBase", "tbQuote", "ignore"])
    for c in ["open", "high", "low", "close", "volume", "quoteVolume"]:
        df[c] = df[c].astype(float)
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    return df


def funding(symbol):
    return get("/premiumIndex", {"symbol": symbol})


def open_interest_hist(symbol, period="1h", limit=25):
    return get_futures_data("/openInterestHist",
                            {"symbol": symbol, "period": period, "limit": limit})


def oi_change_pct(symbol, period="1h", limit=25):
    h = open_interest_hist(symbol, period, limit)
    if not h or len(h) < 2:
        return None
    try:
        a = float(h[0]["sumOpenInterest"]); b = float(h[-1]["sumOpenInterest"])
        return (b - a) / a * 100 if a else None
    except (KeyError, ValueError, ZeroDivisionError):
        return None


def oi_changes(symbol):
    """V2: OI degisimini 1s / 4s / 24s pencerelerinde birlikte dondurur."""
    from . import config as C
    out = {}
    for label, (period, limit) in C.OI_WINDOWS.items():
        out[label] = oi_change_pct(symbol, period=period, limit=limit)
    return out
