"""Spot Radar V1.1 — TUM esikler tek dosyada. scanner/ ile iliskisi YOKTUR."""
# Evren
CEX_PAGES = 3                # CoinGecko volume_desc sayfa (250/sayfa)
CEX_MIN_MC = 50_000_000
CEX_MIN_VOLMC = 0.03
DEX_NETWORKS = ["solana", "eth", "base", "bsc"]
DEX_MIN_LIQ = 150_000
DEX_MIN_VOL24 = 200_000
DEX_MC_MIN, DEX_MC_MAX = 1_000_000, 150_000_000
AGE_MIN_H = 24
FRESH_MAX_D, EMERGING_MAX_D = 14, 90
# Kapilar
LIQ_DROP_RATIO = 0.85
TOP10_MAX_PCT = 45.0
CREATOR_MAX_PCT = 10.0
MAX_TAX_PCT = 5.0
EXT_24H_PCT = 150.0
EXT_7D_MULT = 4.0
MIN_FACTORS = 5          # DEX: 7 faktorun 5'i
MIN_FACTORS_CEX = 3      # CEX'te yalnizca volp/volmc/struct/diff uretilebilir
WASH_BS_LO, WASH_BS_HI = 0.98, 1.02
MANIP_FLAGS_VETO = 2
# Siralama
BREADTH_PCTL = 0.70
# Yayilim
TIER1 = ("binance.com","coinbase.com","okx.com","bybit.com","kraken.com","github.com")
TIER2 = ("reuters.com","bloomberg.com","coindesk.com","theblock.co","decrypt.co","cointelegraph.com","dlnews.com")
TIER_BLACKLIST = ("coinpedia","analyticsinsight","cryptonewsz","coingape","price-prediction","ambcrypto","tradingnews")
GENERIC_TICKERS = {"AI","ONE","MOVE","T","S","OP","GAS","ACT","NOW","JUP","RAY","BOME","PEOPLE","TIME","HOT","SUN","WIN","KEY","DATA","BLZ"}
ATTENTION_VEL = 2.0
PRICED_IN_24H = 80.0
CALM_24H = 30.0
# Guvenilir CEX (tickers dogrulamasi)
TRUSTED_CEX = {"binance","okex","okx","bybit_spot","bybit","gdax","coinbase","kraken","gate","mexc","kucoin"}
# Rapor / state
TOP_N = 10
MAX_SNAPSHOTS = 30
MAX_REPORTS = 60
OUTCOME_TRACK_DAYS = 10
SHADOW_UNTIL = "2026-09-27"   # 28 gun golge
FINALIST_SECURITY = 40
FINALIST_NEWS = 15
FINALIST_OHLCV = 20
HTTP_PACE_GOPLUS = 2.0
HTTP_PACE_GT = 2.1
