# SPOT OPPORTUNITY RADAR V1.1 — NİHAİ TEKNİK ŞARTNAME
Repo: KDUMAN71/kripto-tarayici · Uygulayıcı: Codex / Claude Code
Temel: V1 şartnamesi + 9 revizyon (29.08). Bu belge tek başına yeterlidir.
MUTLAK KURAL: scanner/ (Futures V3.2.x) değişmez; spot/ içinden `scanner` import YASAK
(test T8 bunu AST ile doğrular). Spot, Binance fapi exchangeInfo'yu KENDİ adaptöründen sorgular.

## 0. AMAÇ
Lansman yarışı yok. Hedef: sermaye çekmeye devam eden genç DEX coinleri (ilk pump'ını
atlatmış, günler-haftalar sürebilecek koşucular) + Binance Futures'ta olmayan CEX spot
fırsatları. Çıktı: günde 2 rapor, en fazla 10 aday, zorunlu karne. İlk 28 gün SHADOW MODE:
rapor Telegram'a "🧪 SHADOW — işlem sinyali değildir" başlığıyla gider; hiçbir katmandan
giriş/SL üretilmez. ACTIONABLE etiketi yaşam döngüsünde vardır ama infaz kalibrasyon sonrası.

## 1. DOSYA YAPISI
```
spot/
  config.py            # tüm eşikler + domain tier listeleri + kara liste
  identity.py          # varlık kimliği: coin_id, project_name, ticker, chain,
                       # contract, official_domain (haber eşleştirme bununla yapılır)
  sources/
    dexscreener.py     # keşif + pair metrikleri + token-boosts (paid promo)
    coingecko.py       # markets (750-1000 coin) + trending + finalist tickers
    geckoterminal.py   # finalist DEX OHLCV (pools/{addr}/ohlcv), 30/dk paced
    binance_futures.py # fapi/v1/exchangeInfo — futures üyelik seti (BAĞIMSIZ adaptör)
    goplus.py          # lazy güvenlik, 2 sn aralıklı
    news_rss.py        # Google News RSS + CryptoPanic(ops.)
    binance_ann.py     # duyuru adaptörü + health flag (bozulursa news_source_degraded,
                       # sistem ÇÖKMEZ, raporda tek satır uyarı)
  gates.py  ranking.py  diffusion.py  structure.py  outcomes.py  report.py  main.py
tests/test_spot_v1.py
.github/workflows/spot_radar.yml   # cron 0 6,18 * * * (+dispatch), concurrency: spot-radar
```
STATE: `spot-state` ADLI AYRI BRANCH'te yaşar (main'e state commit'i atılmaz; futures'ın
15dk'lık commit trafiğiyle yarışmaz). Workflow: main checkout (kod) → `git worktree add
.state origin/spot-state` (yoksa orphan oluştur) → koşu sonunda worktree'de commit
"spot state update" → push; reddedilirse 3× pull-rebase-retry.

## 2. EVREN VE YAŞ SINIFLARI
- **CEX katmanı:** CoinGecko volume_desc ilk 750-1000 (3-4 sayfa; günde 2 koşu × 30 gün
  = ~240 sayfa çağrısı/ay, kota sorunu yok). Filtre: MC ≥ $50M, 24s hacim/MC ≥ %3,
  Binance USDT-M futures listesinde YOK. Finalistlerde `/coins/{id}/tickers` ile en az
  bir güvenilir CEX marketi (binance, okx, bybit, coinbase, gate, mexc, kraken) doğrulanır.
- **DEX katmanı:** DexScreener keşif; liquidity ≥ $150K, 24s hacim ≥ $200K, MC $1M-$150M.
  Yaş sınıfları (hard eleme DEĞİL, etiket + davranış):
  <12s: sadece state'e kaydet, rapora giremez · 12-24s: DISCOVERY (rapora giremez)
  1-14g: FRESH RUNNER (ana asimetri bölgesi) · 15-90g: EMERGING · >90g: normal DEX spot.

## 3. KİMLİK ÇÖZÜMLEME (identity.py)
Her aday için: {coin_id, project_name, ticker, chain, contract, official_domain?}.
Haber sorgusu ASLA yalnız ticker ile yapılmaz: sorgu = "project_name" (+ "crypto");
ticker yalnızca ayırt ediciyse (config'te jenerik liste: AI, ONE, MOVE, T, S...) eklenir.
Jenerik ticker + project_name yoksa haber modülü o coin için sessiz atlanır (yanlış
eşleşme, eksik veriden kötüdür).

## 4. ELEME KAPILARI (gates.py — geçti/kaldı, sebep loglanır)
G1 rapor-uygunluk yaşı (DEX): ≥ 24s.
G2 güvenlik (DEX, GoPlus lazy): honeypot=1 · blacklist=1 · mintable=1&owner var ·
   tax>%5 · can_take_back_ownership=1 → ELE. GoPlus CEVAPSIZ → DEX adayı Top10'a
   GİREMEZ (security_unverified state'e yazılır). CEX adayı için GoPlus desteklemiyorsa
   elenmez; `security_unverified` etiketiyle devam eder (risk profilleri farklı).
G3 likidite yönü: bugünkü liq < dünkü snapshot × 0.85 → ELE; fiyat yükselirken likidite
   düşüyorsa ayrıca `exit_liquidity` bayrağı.
G4 yoğunlaşma (DEX): top10 (LP hariç) > %45 veya creator_percent > %10 → ELE.
G5 manipülasyon (BAYRAK + çoklu-veto): tekil göstergeler bayraktır → buys/sells 0.98-1.02
   & yüksek hacim = `wash_suspect`; DexScreener boost listesinde = `paid_promo`;
   likidite yatay + hacim patlaması = `vol_liq_divergence`. İKİ VE ÜZERİ bayrak → ELE.
G6 uzama: 24s > +%150 veya fiyat 7g dibinin > 4x → EXTENDED (rapora giremez; geri
   sakinleşirse dönebilir).
G7 veri tamlığı: 7 faktörden en az 5'i hesaplanabilir olmalı; değilse rapora giremez
   (eksik veri avantaja dönüşemez).

## 5. SIRALAMA (ranking.py) — İKİ AYRI PERCENTİLE EVRENİ
CEX kendi evreninde, DEX kendi evreninde yüzdelik alır ($500M coin ile $5M coin aynı
dağılımda sıralanmaz). Nihai Top ≤10 iki kategoriyi etiketiyle birlikte listeler.
S�ralama anahtarı (sırayla): (1) breadth = kaç faktörü ≥ 70. percentile (bağımsız güçlü
kanıt sayısı) → (2) eşitlikte faktörlerin MEDYAN percentile'ı. Ortalama KULLANILMAZ
(tek uç değer coin'i taşıyamaz). 7 faktör:
F1 hacim kalıcılığı: kendi geçmişine oran (7g taban; genç coinde 6h/24h/önceki-72h
   pencereleri, geçmiş uzadıkça kendi tabanı oluşur — snapshot zincirinden)
F2 24s hacim / MC
F3 likidite büyümesi (kendi snapshot farkımız; CEX'te opsiyonel)
F4 alım baskısı çok-pencere: h1/h6/h24 buys oranı >0.55 sayısı (0/⅓/⅔/1)
F5 holder büyümesi (DEX; GoPlus holder_count günlük Δ; CEX opsiyonel)
F6 teknik yapı — HER İKİ katmanda: finalistlere OHLCV (CEX: CoinGecko/Binance spot
   klines; DEX: GeckoTerminal 1h) → structure.py: higher-low serisi · konsolidasyon
   (ATR sıkışması) · ilk pump seviyesini koruma (ilk bacağın <%50 geri verilmemesi) ·
   breakout/retest · hacimli taban → kademeli 0/0.25/0.5/0.75/1
F7 yayılım (diffusion.py, §6)
Bağlam alanları (faktör DEĞİL, raporda gösterilir + shadow verisinde saklanır):
MC, FDV/MC, yaş, paid_promo, CEX erişimi, security bulguları, unlock_status(known|unknown
— tahmin YOK, "unlock yok" güveni ÜRETİLMEZ; ücretsiz güvenilir kaynak çıkarsa Faz-2).

## 6. YAYILIM + KATALİZÖR (diffusion.py) — iki AYRI çıktı
ATTENTION (mekanik): hız = 24s madde / (önceki 3g ort.+1) [12s/24s/72s/7g pencereleri
state'te] · genişlik = benzersiz güvenilir domain (aynı PR kopyaları tek olaya kümelenir:
başlık benzerliği >0.8 → tek sayım) · otorite = TierA(resmi/borsa) ×3, TierB(büyük medya)
×2, TierC ×1, TierD(SEO/tahmin çiftliği) ×0.
CATALYST (olay): Binance/OKX duyuru adaptöründen listing · mainnet · partnership ·
yatırım vb. gerçek olay yakalanırsa `catalyst` alanı dolu gelir + raporda ayrı satır.
HABER→FİYAT SIRASI (en değerli özellik): olay T0 için T-6h/T+1h/T+6h/T+24h getiri ve
hacim değişimi kaydedilir → etiket: "ilgi fiyatın önünde" (hız≥2x & 24s fiyat <+%30) /
"fiyatlanmış" (fiyat >+%80 sonra haber) / "piyasa inanmıyor" (yayılım var, hacim yok).
paid_promo varken F7 %50 kesilir + raporda ⚠️.

## 7. SNAPSHOT & OUTCOME STATE (spot-state branch'i, spot_state.json)
```json
{"identity": {...}, "snapshots": {"<key>":[{"d","price","mc","fdv","liq","vol24",
  "holders","news24","tier_hits"}]},              // coin başına MAX 30 kayıt FIFO
 "reports":[...],                                  // MAX 60
 "outcomes": {"<key>": {"entered":"2026-08-30","p0":..,
   "t24":..,"t72":..,"t7d":..,"mfe":..,"mae":..,
   "hit20":bool,"hit50":bool,"hit100":bool,"hit2x":bool,
   "extended_after":bool,"failed":bool,"cohort":"CEX|FRESH|EMERGING"}},
 "health": {"news_source_degraded":bool,...}}
```
outcomes.py her koşuda olgunlaşmamış adayların (rapora girmiş, <10 gün) fiyatını çekip
T+24/72/7g + MFE/MAE günceller (≤10 aday/gün → izleme yükü ~100 çağrı, 2 sn paced).
İSTATİSTİK ÜÇ KOHORTTA AYRI TUTULUR: CEX / FRESH(1-14g) / EMERGING(15-90g) — karışmaz.

## 8. RAPOR (report.py)
```
🧪 SPOT RADAR — SHADOW MODE · 30.08 09:00
Evren: CEX 812 / DEX 143 → kapılar → 11 → TOP 7   (10 doldurma ZORUNLU DEĞİL; 0 da rapor)
1) 🅳 FRESH · ABC — MC $18.2M · yaş 4.7g · breadth 5/7 · medyan p78
   Hacim 3.1x/taban · V/MC %38 · Liq +%22 · Alım ✓✓✓ · Holder +%9/g
   Yapı: ilk bacak korunuyor, HL serisi · Yayılım: 4.3x, 13 kaynak (2×TierA/B), ilgi önde
   Katalizör: — · 🎯 İzle: $0.0412 · ❌ Yapı bozulur: $0.0358 · ⚠️ paid_promo yok, top10 %38
...
— KARNE (zorunlu): dünkü liste T+24s ort/medyan · kohort kümülatifleri (CEX/FRESH/EMERGING
  ayrı): ort MFE, +20/+50/+100 isabet, 2x sayısı, fail oranı
⚠️ SHADOW: izleme listesi; işlem sinyali değildir.
```

## 9. TESTLER (CI'a eklenir)
T1 honeypot → G2 ele. T2 GoPlus cevapsız: DEX adayı Top10 dışı, CEX adayı unverified devam.
T3 likidite %20 düşüş → G3. T4 iki manipülasyon bayrağı → G5 ele; tek bayrak → sadece flag.
T5 +%200 → EXTENDED. T6 eksik 3 faktör → G7 ele. T7 sıralama: breadth > medyan determinizmi.
T8 spot/ içinden scanner import yok (AST). T9 state FIFO. T10 jenerik ticker (AI) +
project_name yok → haber atlanır. T11 outcome: T+24 doldurma ve kohort ayrımı.
T12 duyuru adaptörü bozuk → health flag, koşu tamamlanır.

## 10. TAKVİM
Gün 0: iskelet + testler + spot-state branch bootstrap. Gün 1-28: SHADOW (raporlar akar,
outcome birikir). Gün 28: kohort bazlı faktör analizi → ağırlıklar VERİDEN türetilir
(hangi faktör MFE/hit50 ile korele) → V1.2'de skor formülü ancak o zaman yazılır.
Faz-2 (ayrı issue): Moralis free key (experienced_net_buyers) / GMGN read-only API ·
CryptoRank/Tokenomist unlock · X/LunarCrush yayılım derinliği.

## 11. YASAKLAR
scanner/'a dokunma · giriş/SL/TP üretme (28 gün) · GoPlus sessizken DEX'e güven ·
listeyi doldurmak için eşik gevşetme · ticker-only haber eşleşmesi · main'e spot state
commit'i · LLM'siz çalışamayan hiçbir bileşen (tamamı deterministik).
