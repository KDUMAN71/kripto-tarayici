# Kripto Tarayıcı V3 — Binance Futures + Telegram

Binance USDT-M perpetual piyasasını **15 dakikada bir** tarayan karar-destek radarı. Emir vermez; Binance hesabına bağlanmaz. Ama amaç, giriş olduktan sonra haber vermek değil, **giriş oluşmadan önce hazırlanman için yeterince erken uyarmaktır.**

## V3 mimarisi

**4 saat = ana yön → 1 saat = setup/yapı → 15 dakika = giriş zamanlaması ve hacim teyidi**

| Aşama | Bildirim | Ne yapmalısın? |
|---|---|---|
| 🔵 | **ERKEN UYARI — EMİR HAZIRLIĞI** | Tetiğe ≤%3. Binance fiyat alarmını kur; giriş/SL/TP planını hazırla. |
| 🟡 | **YAKIN TAKİP** | Tetiğe ≤%1,2. Binance ekranını yakından izle. |
| 🟢 | **İŞLEM BÖLGESİ AKTİF** | 15d taze kırılım + hacim teyidi + 1s/4s uyumu var. Giriş, SL, TP1/2/3 ve R:R verilir. |
| 🛑 | **İPTAL** | Daha önce bildirilen kurulum bozuldu. |
| 🔴 / 🎯 | **STOP / TP** | Aktif paper-planın hedef/stop takibi. |

**İdeal giriş kaçtıysa mesaj GELMEZ.** Sistem `MISSED_SILENT` olarak kayda geçirir ve yeni yapı bekler.

## V3 çekirdeği

- **15 dakikalık entry motoru:** 1 saatlik mum kapanışını bekleyip geç kalmak yerine, 4s/1s bağlamı içinde 15d taze breakout ve hacim teyidi kullanılır.
- **Erken uyarı:** tetiğe %3 kala plan + Binance alarm seviyesi + SL + TP1/2/3 önceden gelir.
- **Çoklu OI:** yaklaşık **1s / 4s / 24s** açık pozisyon değişimi birlikte gösterilir.
- **Funding crowding:** aşırı pozitif funding long, aşırı negatif funding short için `crowded` etiketi üretir.
- **Genişletilmiş evren:** sadece en yüksek hacimli coinler değil, 1s hacim anomalisi / 3s momentum gösteren daha alt sıralardaki coinler de derin taramaya alınır.
- **Kaçan sinyal sessizliği:** kötü R:R ile geç işlem bildirimi yok.
- **Paper performance:** ACTIVE sinyaller `state/state.json -> trades` altında MFE, MAE ve R sonucu ile tutulur. 50–100 sinyal sonra gerçek expectancy ölçülebilir. Özet için repo kökünde: `python -m scanner.report` → win rate, expectancy (R), profit factor, MFE/MAE. Hesap, pozisyon yönetimini dikkate alır (TP1 sonrası stop tam -1R sayılmaz).
- **Pozisyon yönetimi planı:** varsayılan TP1 %25, TP2 %35, TP3 %40; TP1 sonrası kalan SL'nin breakeven'a alınması mesajda hatırlatılır.

## Temel kalite filtreleri

- Minimum 24s hacim: **20M USDT**
- 4s trend yönü zorunlu
- 1s setup ana yönün tersine güçlü olmamalı
- 15d kırılım hacmi ≥ **1.30x** 20-mum ortalaması
- 1s son kapalı mum hacmi ≥ **1.05x** ortalama
- TP2 için minimum **1:2 R:R**
- ATR stretch ve 72s ekstrem-kovalama filtresi
- Breakout sonrası fiyat tetikten >%1,25 uzaklaştıysa sinyal sessizce reddedilir
- Yeni perpetual ilk 5 gün teknik sinyal almaz
- Haber modülü açıksa delist/hack/exploit gibi kritik haberler veto eder

## Kurulum

### 1) Telegram
1. Telegram'da `@BotFather` → `/newbot` → token al.
2. Bota bir mesaj gönder.
3. `@userinfobot` üzerinden chat ID'ni al.

### 2) GitHub
Dosyaları bir GitHub reposuna yükle. `.github/workflows/scan.yml` yolu korunmalı.

### 3) Actions Secrets
`Settings → Secrets and variables → Actions`:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `CRYPTOPANIC_TOKEN` (opsiyonel)

### 4) Test
Actions → `crypto-scan-v3` → **Run workflow**.

Yerelde Telegram göndermeden:
```bash
TELEGRAM_DRY_RUN=1 python -m scanner.main
```

## GitHub Actions zamanlama gerçeği
Workflow cron'u `*/15` olsa da GitHub Actions kesin gerçek-zaman garantisi vermez; yoğunlukta gecikebilir. Eğer bu radar ciddi futures giriş zamanlaması için kullanılacaksa en sağlam kurulum Avrupa lokasyonlu küçük bir VPS'tir:

```cron
*/15 * * * * cd /opt/kripto-tarayici-v3 && /usr/bin/python3 -m scanner.main
```

İstersen 5 dakikalık VPS cron'u da teknik olarak mümkündür; Binance API rate limitlerine göre ayrıca test edilmelidir.

## Dosyalar

```text
scanner/config.py      eşikler
scanner/data.py        Binance Futures public API + OI pencereleri
scanner/indicators.py  EMA / RSI / ATR / pivot
scanner/engine.py      EARLY / WATCH / ACTIVE motoru
scanner/radars.py      pump / listing / haber
scanner/state.py       yaşam döngüsü + paper performance
scanner/main.py        tarama akışı
scanner/telegram.py    Telegram
scanner/report.py      performans raporu (python -m scanner.report)
state/state.json       kalıcı durum (otomatik oluşur)
```

## Risk notu
Bu yazılım sinyal doğruluğunu garanti etmez. Özellikle yüksek kaldıraç, küçük fiyat hareketini büyük PnL ve likidasyon riskine dönüştürür. V3'ün amacı daha erken ve daha seçici teknik kurulum üretmek; **ilk aşamada paper tracking ile en az 50–100 sinyal istatistiği görmek** mantıklıdır.


## V3 QA notları
- 1G bağlam gerçek EMA200 için 240 günlük mumla hesaplanır.
- Taker buy/sell baskısı en son kapalı mumları içerir.
- Simetrik üçgende short confluence alt kırılım tetik seviyesini kullanır.
- Top-trader pozisyon ve global hesap long/short oranları türev puanına/crowding kontrolüne dahildir.
- Paper SL/TP takibi yalnızca tarama anındaki fiyata değil, aktivasyondan beri görülen 15d high/low seviyelerine bakar. Hard SL dokunuşu kapanış beklemez.
- Haber API'si veri vermezse mesaj "haber teyidi yok" der; veri yokken "haber temiz" iddiası üretmez.
