"""Gostergeler: EMA, RSI(Wilder), ATR, pivot noktalar."""
import numpy as np
import pandas as pd


def ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def rsi(s: pd.Series, period: int = 14) -> pd.Series:
    d = s.diff()
    gain = d.clip(lower=0)
    loss = -d.clip(upper=0)
    ag = gain.ewm(alpha=1 / period, min_periods=period).mean()
    al = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = ag / al.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def pivot_levels(df: pd.DataFrame, order: int = 3, lookback: int = 90):
    """Kapali mumlar uzerinden pivot tepe/dip seviyeleri (deger listesi, yeni->eski)."""
    sub = df.iloc[-(lookback + order):].reset_index(drop=True)
    highs = sub["high"].values
    lows = sub["low"].values
    n = len(sub)
    ph, pl = [], []
    for i in range(order, n - order):
        win_h = highs[i - order:i + order + 1]
        win_l = lows[i - order:i + order + 1]
        if highs[i] >= win_h.max():
            ph.append((i, float(highs[i])))
        if lows[i] <= win_l.min():
            pl.append((i, float(lows[i])))
    ph_vals = [v for _, v in sorted(ph, key=lambda x: -x[0])]
    pl_vals = [v for _, v in sorted(pl, key=lambda x: -x[0])]
    return ph_vals, pl_vals


def trend_score(price, e20, e50, e200):
    if e20 > e50 > e200 and price > e20:
        return 2, "guclu yukselis"
    if e20 > e50 and price > e50:
        return 1, "yukselis"
    if e20 < e50 < e200 and price < e20:
        return -2, "guclu dusus"
    if e20 < e50 and price < e50:
        return -1, "dusus"
    return 0, "kararsiz"


def analyze(df: pd.DataFrame, piv_lookback: int = 90):
    """Tek zaman dilimi ozeti. Teyit mantigi icin SON KAPALI mum kullanilir."""
    d = df.copy()
    d["ema20"] = ema(d["close"], 20)
    d["ma7"] = d["close"].rolling(7).mean()
    d["ema50"] = ema(d["close"], 50)
    d["ema200"] = ema(d["close"], min(200, max(50, len(d) - 2)))
    d["rsi"] = rsi(d["close"])
    d["atr"] = atr(d)
    d["vol_sma20"] = d["volume"].rolling(20).mean()

    closed = d.iloc[:-1]           # son satir olusmakta olan mum olabilir
    last_closed = closed.iloc[-1]
    live_price = float(d["close"].iloc[-1])

    ph, pl = pivot_levels(closed, order=3, lookback=piv_lookback)
    ts, tlabel = trend_score(live_price, last_closed["ema20"],
                             last_closed["ema50"], last_closed["ema200"])
    vol_ratio = (float(last_closed["volume"] / last_closed["vol_sma20"])
                 if last_closed["vol_sma20"] and not np.isnan(last_closed["vol_sma20"])
                 and last_closed["vol_sma20"] > 0 else float("nan"))
    a = float(last_closed["atr"]) if not np.isnan(last_closed["atr"]) else None
    stretch = (abs(live_price - float(last_closed["ema20"])) / a) if a else None

    return {
        "df": d, "closed": closed, "price": live_price,
        "ema20": float(last_closed["ema20"]), "ema50": float(last_closed["ema50"]),
        "ema200": float(last_closed["ema200"]), "ma7": float(last_closed["ma7"]),
        "rsi": float(last_closed["rsi"]),
        "atr": a, "vol_ratio": vol_ratio, "stretch": stretch,
        "tscore": ts, "tlabel": tlabel,
        "pivot_highs": ph, "pivot_lows": pl,
        "high72": float(closed["high"].iloc[-72:].max()) if len(closed) >= 20 else None,
        "low72": float(closed["low"].iloc[-72:].min()) if len(closed) >= 20 else None,
        "high24": float(closed["high"].iloc[-24:].max()) if len(closed) >= 20 else None,
        "low24": float(closed["low"].iloc[-24:].min()) if len(closed) >= 20 else None,
    }
