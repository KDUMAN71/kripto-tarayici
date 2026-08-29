"""Gostergeler: EMA, RSI(Wilder), ATR, pivot, Fibonacci ve RSI uyumsuzlugu."""
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


def _pivot_points(df: pd.DataFrame, order: int = 3, lookback: int = 100):
    """RSI uyumsuzlugu icin indeksli pivotlar; son kapanmis mumlar uzerinde."""
    sub = df.iloc[-lookback:].copy().reset_index(drop=True)
    hs, ls = [], []
    for i in range(order, len(sub) - order):
        if sub["high"].iloc[i] >= sub["high"].iloc[i-order:i+order+1].max():
            hs.append(i)
        if sub["low"].iloc[i] <= sub["low"].iloc[i-order:i+order+1].min():
            ls.append(i)
    return sub, hs, ls


def rsi_divergence(df: pd.DataFrame):
    """Son iki anlamli pivot arasinda klasik RSI divergence ara.

    Donus: bullish|bearish|None. Tek basina sinyal degildir; location/setup confluence'tur.
    """
    if len(df) < 35:
        return None
    sub, hs, ls = _pivot_points(df, order=3, lookback=min(120, len(df)))
    if "rsi" not in sub:
        sub["rsi"] = rsi(sub["close"])
    if len(ls) >= 2:
        a, b = ls[-2], ls[-1]
        if sub["low"].iloc[b] < sub["low"].iloc[a] and sub["rsi"].iloc[b] > sub["rsi"].iloc[a] + 2:
            return "bullish"
    if len(hs) >= 2:
        a, b = hs[-2], hs[-1]
        if sub["high"].iloc[b] > sub["high"].iloc[a] and sub["rsi"].iloc[b] < sub["rsi"].iloc[a] - 2:
            return "bearish"
    return None


def fibonacci_context(df: pd.DataFrame, lookback: int = 120):
    """Son anlamli swing icin retracement/extension haritasi.

    Low once, high sonra ise upswing; high once, low sonra ise downswing kabul edilir.
    Fibonacci tek basina sinyal degil, S/R cluster confluence'udur.
    """
    if len(df) < 20:
        return {"direction": None, "levels": {}, "swing_low": None, "swing_high": None}
    sub = df.iloc[-lookback:]
    # Son TEYITLI swing bacagi: pivot bazli anchor (pencere ekstremi eski bir
    # spike olabilir ve sahte confluence uretir). Pivot yoksa ekstreme dus.
    psub, hs, ls = _pivot_points(df, order=3, lookback=lookback)
    hi_idx = sub["high"].idxmax(); lo_idx = sub["low"].idxmin()
    hi = float(sub.loc[hi_idx, "high"]); lo = float(sub.loc[lo_idx, "low"])
    if hs and ls:
        h_i, l_i = hs[-1], ls[-1]
        ph = float(psub["high"].iloc[h_i]); pl = float(psub["low"].iloc[l_i])
        if ph > pl and (ph - pl) / max(pl, 1e-12) >= 0.01:
            hi, lo = ph, pl
            lo_idx, hi_idx = (0, 1) if l_i < h_i else (1, 0)  # yalniz sira bilgisi
    span = hi - lo
    if span <= 0:
        return {"direction": None, "levels": {}, "swing_low": lo, "swing_high": hi}
    ratios = (0.382, 0.50, 0.618, 0.786)
    if lo_idx < hi_idx:
        direction = "up"
        levels = {str(r): hi - r * span for r in ratios}
        levels.update({"1.272": hi + 0.272 * span, "1.618": hi + 0.618 * span})
    else:
        direction = "down"
        levels = {str(r): lo + r * span for r in ratios}
        levels.update({"1.272": lo - 0.272 * span, "1.618": lo - 0.618 * span})
    return {"direction": direction, "levels": levels, "swing_low": lo, "swing_high": hi}


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
    d["ema100"] = ema(d["close"], min(100, max(50, len(d) - 2)))
    d["ema200"] = ema(d["close"], min(200, max(50, len(d) - 2)))
    d["rsi"] = rsi(d["close"])
    d["atr"] = atr(d)
    d["vol_sma20"] = d["volume"].rolling(20).mean()

    closed = d.iloc[:-1]
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
    fib = fibonacci_context(closed, lookback=min(120, len(closed)))
    div = rsi_divergence(closed)

    def slope(col, bars=4):
        if len(closed) <= bars:
            return 0.0
        return float(closed[col].iloc[-1] - closed[col].iloc[-1-bars])

    return {
        "df": d, "closed": closed, "price": live_price,
        "ema20": float(last_closed["ema20"]), "ema50": float(last_closed["ema50"]),
        "ema100": float(last_closed["ema100"]), "ema200": float(last_closed["ema200"]),
        "ema20_slope": slope("ema20"), "ema50_slope": slope("ema50"),
        "ema100_slope": slope("ema100"), "ema200_slope": slope("ema200"),
        "ma7": float(last_closed["ma7"]), "rsi": float(last_closed["rsi"]),
        "rsi_divergence": div, "fib": fib,
        "atr": a, "vol_ratio": vol_ratio, "stretch": stretch,
        "tscore": ts, "tlabel": tlabel,
        "pivot_highs": ph, "pivot_lows": pl,
        "high72": float(closed["high"].iloc[-72:].max()) if len(closed) >= 20 else None,
        "low72": float(closed["low"].iloc[-72:].min()) if len(closed) >= 20 else None,
        "high24": float(closed["high"].iloc[-24:].max()) if len(closed) >= 20 else None,
        "low24": float(closed["low"].iloc[-24:].min()) if len(closed) >= 20 else None,
    }
