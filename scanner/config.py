"""Kripto Tarayici V2 merkezi ayarlari."""

# ---- Evren / likidite ----
MIN_QUOTE_VOLUME_24H = 20_000_000
MAX_ABS_24H_CHANGE_TECH = 25.0
YOUNG_COIN_DAYS = 5
CORE_SCAN_CAP = 60                 # hacme gore ana evren
MOMENTUM_SCAN_POOL = 120           # hacim anomalisi icin incelenecek daha genis havuz
DEEP_SCAN_CAP = 75                 # 4s + 1s + 15d derin analiz tavanı
MOMENTUM_PRE_VOL_MULT = 1.8        # son kapali 1s hacim / 20 ortalama
MOMENTUM_PRE_3H_PCT = 3.0          # son 3 kapali 1s mumda mutlak hareket

# ---- Uyari katmanlari ----
EARLY_PROXIMITY_PCT = 3.0          # tetiğe <= %3: ERKEN UYARI
WATCH_PROXIMITY_PCT = 1.2          # tetiğe <= %1.2: YAKIN TAKIP
EARLY_ALERT_PRICE_BUFFER_PCT = 0.35 # Binance alarmi tetikten bu kadar once
WATCH_EXPIRY_H = 36

# ---- Teknik sinyal kurallari ----
RSI_LONG_MIN, RSI_LONG_MAX = 48, 74
RSI_SHORT_MIN, RSI_SHORT_MAX = 26, 52
BREAKOUT_VOL_MULT_15M = 1.30       # 15d teyit hacmi
BREAKOUT_VOL_MULT_1H = 1.05        # 1s momentum tamamen zayif olmasin
ACTIVE_MAX_RUN_PCT = 1.25          # 15d teyitten sonra kovalamama filtresi
ATR_STRETCH_MAX = 2.3
EXTREME_PROX_PCT = 1.5
MIN_RISK_PCT, MAX_RISK_PCT = 0.35, 5.0
MIN_RR_TP2 = 2.0
TARGET_RR_TP3 = 3.0
SL_ATR_BUFFER = 0.35
FRESH_BREAK_BARS_15M = 2           # son 2 kapali 15d mum

# 4s yon + 1s setup + 15d entry uyumu
MIN_1H_TREND_SCORE_LONG = 0
MAX_1H_TREND_SCORE_SHORT = 0

# ---- OI / funding ----
OI_WINDOWS = {
    "1h": ("5m", 13),             # ~60 dk
    "4h": ("15m", 17),            # ~4 saat
    "24h": ("1h", 25),            # ~24 saat
}
CROWDED_FUNDING_ABS = 0.0010        # %0.10 / 8s mutlak funding: kalabalik taraf uyarisi

# ---- Pozisyon yonetimi metni ----
TP1_CLOSE_PCT = 25
TP2_CLOSE_PCT = 35
TP3_CLOSE_PCT = 40
MOVE_SL_TO_BE_AFTER_TP1 = True

# ---- Pump radari ----
PUMP_MIN_24H, PUMP_MAX_24H = 8.0, 45.0
PUMP_VOL_MULT = 5.0
PUMP_OI_MIN_CHANGE = 8.0
PUMP_ALERT_COOLDOWN_H = 24
PUMP_MAX_PER_RUN = 6

# ---- Haber (opsiyonel) ----
NEWS_VETO_KEYWORDS = ["delist", "delisting", "hack", "exploit", "lawsuit",
                      "sec sues", "halt", "suspend", "rug"]
NEWS_LOOKBACK_H = 12

# ---- Veri / durum ----
KLINE_LIMITS = {"15m": 240, "1h": 240, "4h": 220}
STATE_PATH = "state/state.json"
LOG_KEEP = 800
TRADE_HISTORY_KEEP = 300
