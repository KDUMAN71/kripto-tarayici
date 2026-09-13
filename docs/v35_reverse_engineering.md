# V3.5 Runner Reverse Engineering Lab

## Amaç

Mevcut Futures motorunu eşiklerle yamamak yerine, son 30 günlük gerçek runner olaylarını geriye dönük inceleyip **hangi verilerin hareketten önce gerçekten öncü sinyal verdiğini** bulmak. Bu çalışma üretim sinyal mantığını değiştirmez; önce ölçer, karşılaştırır, replay eder ve ancak doğrulanmış kuralları V3.5 production motoruna taşır.

## Temel ilke: label ile feature ayrımı

- **Label** geleceğe bakabilir: örneğin T anından sonraki 24 saatte fiyatın maksimum +%18 yapması.
- **Feature** kesinlikle geleceğe bakamaz: T anındaki hesap sadece T ve öncesindeki mum/OI/hacim/taker/funding/haber verisini kullanır.
- Replay sırasında ileride oluşmuş pivot, haber, mum kapanışı veya gün sonu verisi T anına sızdırılmaz.

Bu kural bozulursa backtest gerçek olmayan şekilde mükemmel görünür ve çalışma geçersiz sayılır.

## Veri seti

İki pozitif örneklem tutulur:

1. Her UTC/TR işlem gününün en güçlü 10-20 USDT perpetual yükseleni.
2. Gün sınırından bağımsız rolling 6s / 12s / 24s pencerelerde +%10 / +%15 / +%20 maksimum hareket yapan runner olayları.

Her pozitif örnek için aynı saat ve benzer likidite/hacim bandından **koşmayan kontrol coinleri** seçilir. Böylece "runnerlarda sık" görünen bir özelliğin aslında tüm piyasada yaygın olup olmadığı ölçülür.

## Dondurulacak zaman noktaları

Her runner başlangıcı için feature snapshot:

- T-24s
- T-12s
- T-6s
- T-3s
- T-1s
- T-30d
- T-15d
- T0 / breakout başlangıcı

Execution analizi için ayrıca:

- +%3
- +%5
- +%10
- ilk pullback / flag / retest

Pozitif offset'ler tahmin modeli için değil, yalnız giriş/stop kalibrasyonu için kullanılır.

## İncelenecek feature aileleri

### Fiyat / yapı
- 15d, 1s, 3s, 6s, 24s getiri
- relative strength (BTC ve Futures evrenine göre)
- range compression / ATR compression
- higher-low / breakout / flag / retest
- EMA/VWAP/pivot konumu
- ilk gerçek HTF obstacle mesafesi

### Hacim / akış
- 15d ve 1s hacim oranı / z-score
- quote volume ivmesi
- trade-count ivmesi
- taker buy share ve değişimi
- OI 15d / 1s / 4s / 24s
- özellikle OI artarken fiyatın henüz koşmadığı durumlar
- funding seviyesi ve funding değişimi

### Piyasa bağlamı
- BTC trend/rejim
- sektör/tema rotasyonu
- coin likidite bandı
- yeni listing / coin yaşı
- spread ve işlem derinliği

### Haber / katalizör
Runner olayları ayrıca şu sınıflara ayrılır:
- TECHNICAL_LED
- FLOW_LED
- NEWS_LED
- LISTING_LED
- MIXED
- UNEXPLAINED

Haberler zaman damgasıyla replay'e dahil edilir. Sonradan yayınlanan haber geriye taşınmaz.

## Çıktılar

Her event için:
- runner başlangıç zamanı
- hareket eşiğine ilk ulaşma zamanı
- pre-runner feature path
- mevcut V3.x pipeline'ın o coin için stage/veto geçmişi
- hipotez motorunun ilk uyarı zamanı
- varsayımsal entry
- MAE / MFE
- stop mesafesi
- 1R/2R/3R sonuçları
- ana hareketin yüzde kaçında yakalandığı

## Runner DNA kümeleri

Tek bir universal formül varsayılmayacak. Veriden aşağıdaki gibi ayrı setup aileleri çıkabilir:

1. Accumulation -> breakout
2. Momentum continuation / flag
3. OI-led expansion
4. News impulse
5. Listing / low-float
6. Rotation / relative-strength runner

Her aile kendi feature seti, giriş mantığı ve risk profiliyle ayrı değerlendirilir.

## Kalibrasyon ve doğrulama

- Son 30 gün: discovery / calibration seti.
- Öncesindeki dokunulmamış 30-60 gün: out-of-sample doğrulama.
- Bir kural yalnız calibration döneminde iyi çalışıyorsa production'a alınmaz.
- Threshold optimizasyonunda mümkün olduğunca geniş stabil bölgeler tercih edilir; tek bir ideal sayıya overfit edilmez.

## Başarı metrikleri

Sinyal sayısı başarı metriği değildir. Ölçülecekler:

- yakalanabilir runner recall
- hareketin ilk üçte birlik bölümünde detection oranı
- median detection lead time
- false-positive oranı
- ACTIVE expectancy (R)
- profit factor
- MAE / MFE dağılımı
- stop-out sonrası MFE
- runner türüne göre ayrı performans

İlk hedef: yakalanabilir Top-10 runnerların en az %50'sini ana hareketin ilk üçte birlik bölümünde EARLY/WATCH seviyesinde görmek. Production ACTIVE için ayrıca out-of-sample pozitif expectancy şarttır.

## Güvenlik / production sınırı

Bu branch altındaki `research/` kodu canlı scanner tarafından import edilmez. İlk replay sonuçları tamamlanana kadar mevcut Futures eşikleri araştırma sonucuna göre değiştirilmeyecek. LITUSDT'de görülen HTF-obstacle geometri hatası ayrı bir safety fix olarak ele alınabilir.
