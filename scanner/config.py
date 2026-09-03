"""Kripto Tarayici merkezi ayarlari."""

ENGINE_VERSION = "3.3"

# ---- Evren / likidite ----
MIN_QUOTE_VOLUME_24H = 8_000_000   # V3.4: ATOM gibi orta hacimli majorler evrene girsin
MAX_ABS_24H_CHANGE_TECH = 25.0
YOUNG_COIN_DAYS = 5
CORE_SCAN_CAP = 130
MOMENTUM_SCAN_POOL = 200
DEEP_SCAN_CAP = 150
MOMENTUM_PRE_VOL_MULT = 1.8
MOMENTUM_PRE_3H_PCT = 3.0

# ---- Uyari katmanlari ----
EARLY_PROXIMITY_PCT = 3.0
WATCH_PROXIMITY_PCT = 1.2
EARLY_ALERT_PRICE_BUFFER_PCT = 0.35
WATCH_EXPIRY_H = 36

# ---- Teknik sinyal kurallari ----
RSI_LONG_MIN, RSI_LONG_MAX = 48, 74
RSI_SHORT_MIN, RSI_SHORT_MAX = 26, 52
BREAKOUT_VOL_MULT_15M = 1.30
BREAKOUT_VOL_MULT_1H = 1.05
ACTIVE_MAX_RUN_PCT = 1.25
ATR_STRETCH_MAX = 2.3
EXTREME_PROX_PCT = 1.5
MIN_RISK_PCT, MAX_RISK_PCT = 0.35, 5.0
MIN_RR_TP1 = 1.50
MIN_RR_TP2 = 2.0
TARGET_RR_TP3 = 3.0
SL_ATR_BUFFER = 0.35
# V3.4 kirilim duzeltmeleri
STRUCT_SL_BARS_15M = 12      # kirilim oncesi son salinim penceresi (~3 saat)
TP_MIN_SEPARATION_R = 0.5    # TP2, TP1'den en az bu kadar R uzakta olmali
FRESH_BREAK_BARS_15M = 2

MIN_1H_TREND_SCORE_LONG = 0
MAX_1H_TREND_SCORE_SHORT = 0

OI_WINDOWS = {
    "1h": ("5m", 13),
    "4h": ("15m", 17),
    "24h": ("1h", 25),
}
CROWDED_FUNDING_ABS = 0.0010

TP1_CLOSE_PCT = 25
TP2_CLOSE_PCT = 35
TP3_CLOSE_PCT = 40
MOVE_SL_TO_BE_AFTER_TP1 = True

PUMP_MIN_24H, PUMP_MAX_24H = 8.0, 45.0
PUMP_VOL_MULT = 5.0
PUMP_OI_MIN_CHANGE = 8.0
PUMP_ALERT_COOLDOWN_H = 24
PUMP_MAX_PER_RUN = 6

# ---- Erken pump izi (V3.4) ----
# Mevcut pump radari "kostu mu?" diye sorar ve dogasi geregi gec kalir.
# Bu katman tersini sorar: para giriyor ama fiyat henuz tepki vermemis mi?
EARLY_PUMP_MAX_24H = 12.0          # bundan cok kosmus coin artik "erken" degil
EARLY_PUMP_MIN_QUOTE_VOL = 5_000_000
EARLY_PUMP_POOL = 40               # API butcesi: kac aday yoklanir
# Esikler tahminle degil olcumle konuldu (01.09.2026, 40+25 sembollu ornek):
#   hareket edenler (24s>=%12): 1s OI medyan +1.44%, ust ceyrek +2.42%, maks +5.64%
#   sakinler (|24s|<=%5)      : 1s OI medyan +0.01%, ust ceyrek +0.27%, maks +0.80%
# 1.0 esigi ikisini temiz ayirir. Taker gercekte %43-54 bandinda seyrediyor,
# guclu ayirt edici degil; hafif teyit olarak kullanilir.
EARLY_PUMP_OI_MIN_1H = 1.0         # ~1 saatte OI artisi (5d cozunurluk)
EARLY_PUMP_MAX_PRICE_RUN_1H = 3.0  # ayni pencerede fiyat bu kadardan az kosmus olmali
EARLY_PUMP_VOL_MULT_15M = 1.5      # son kapali 15d hacim / ortalama
EARLY_PUMP_TAKER_MIN = 0.52        # hafif alici baskisi (bkz. olcum notu)
EARLY_PUMP_RSI_MAX = 70.0          # giris hala mumkun olsun
EARLY_PUMP_COOLDOWN_H = 12
EARLY_PUMP_MAX_PER_RUN = 4

NEWS_VETO_KEYWORDS = ["delist", "delisting", "hack", "exploit", "lawsuit",
                      "sec sues", "halt", "suspend", "rug"]
NEWS_LOOKBACK_H = 12

KLINE_LIMITS = {"15m": 240, "1h": 240, "4h": 220}
STATE_PATH = "state/state.json"
SUMMARY_PATH = "state/summary.json"
LOG_KEEP = 800
TRADE_HISTORY_KEEP = 300
SCAN_LOG_KEEP = 96
SUMMARY_LOG_MAX = 120
SUMMARY_RECENT_TRADES = 30
KNOWN_SYMBOLS_PRUNE_MIN_UNIVERSE = 300
KNOWN_SYMBOLS_PRUNE_MIN_RATIO = 0.85

FUNDING_VETO = 0.0012
SPREAD_VETO_PCT = 0.15
FRESH_BREAK_BARS_1H = 2

ACTIVE_MIN_VOL_RATIO_1H = 0.70
ACTIVE_MAX_LIVE_RISK_PCT = 3.0
ACTIVE_MIN_OBSTACLE_R = 1.50
ACTIVE_MIN_HOLD_CLOSES = 1
RETEST_MIN_HOLD_CLOSES = 2
REVERSAL_TAKER_LONG_15M = 0.51
REVERSAL_TAKER_SHORT_15M = 0.49
PANIC_TAKER_LONG_15M = 0.53
PANIC_TAKER_SHORT_15M = 0.47
HARD_MOVE_24H_PCT = 8.0
REVERSAL_HARD_MOVE_MIN_VOL_1H = 1.20
OI_COLLAPSE_4H_PCT = -3.0
OI_COLLAPSE_24H_PCT = -8.0
ACTIVE_CONFLICT_SCORE_GAP = 1

HTF_ZONE_ATR_MULT = 0.55
HTF_ZONE_MAX_PCT = 1.25
HTF_LOCATION_PROX_PCT = 1.75
HTF_CLUSTER_MIN_TOUCHES = 2
PREFILTER_MIN_TSCORE = None
FIB_RETRACE_LEVELS = (0.382, 0.50, 0.618, 0.786)
PRIORITY_SETUPS = {
    "flag", "breakout_retest", "double_top", "double_bottom",
    "liquidity_sweep", "trendline_break",
}
DECISION_EDGE_STRONG = 3.0
DECISION_EDGE_MODERATE = 1.5
# Liquidation map verisi bu repoda yok: V3.3 bunu varmis gibi kullanmaz.
