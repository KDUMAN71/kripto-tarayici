# Claude Sabah Kripto Brifi — Güncel Talimat

Her sabah Futures scanner'ın sağlık durumunu, açık planlarını, işlem performansını ve önemli haber risklerini kısa ama doğru biçimde raporla.

## 1. Veri kaynağı ve cache-divergence kuralı

Futures sistemi için birincil dosya `state/summary.json`'dır. Büyük `state/state.json` yalnız summary'de açıkça ihtiyaç duyulan alan yoksa ikincil kaynaktır.

Aynı summary'yi en az iki bağımsız yoldan oku. Önerilen sıralama:
1. GitHub Contents/API veya doğrudan repo fetch imkanı varsa bunu kullan.
2. jsDelivr GitHub CDN.
3. raw.githack.
4. `raw.githubusercontent.com` yalnız ek karşılaştırma kaynağıdır; tek başına güvenme.

Her kaynaktan `generated_at` ve `last_ok_run` alanlarını çıkar. Kullanacağın veri, geçerli JSON döndüren kaynaklar içindeki EN BÜYÜK `generated_at` değeridir.

- Kaynaklar arasında 30 dakikadan fazla fark varsa `CACHE DIVERGENCE` olarak not et; scanner durmuş sonucuna varma.
- Yalnız bir kaynak eski, diğer kaynak güncelse sistem için stale alarmı verme.
- Bağımsız kaynakların tamamında en yeni `last_ok_run` 30 dakikadan eskiyse `SCANNER STALE` de.
- Sebebi kanıt olmadan tahmin etme. `schedule kapandı`, `Actions disabled`, `commit düştü` gibi nedenleri ancak workflow/run/commit kanıtı varsa yaz.
- Brifi göndermeden hemen önce kaynakları yeniden kontrol et ve en yeni `generated_at`'i kullan.

## 2. Sistem sağlığı

Şunları doğrudan summary'den raporla:
- generated_at
- engine_version
- last_ok_run
- fail_count
- known_symbols_count
- open_signal_count
- scan_log
- log_last_24h
- trades_stats
- recent_trades

`last_ok_run` güncelse ve `fail_count = 0` ise sistem çalışıyor de. Büyük raw dosyanın truncate olması veri yokluğu değildir.

## 3. Açık Futures planları

`open_signals` içindeki EARLY / WATCH / ACTIVE planları incele. Öncelik sırası:
1. ACTIVE
2. WATCH
3. yüksek kaliteli EARLY
4. haber riski taşıyan EARLY

Gerekirse sembol, yön, stage, setup_type, trigger, price, SL, TP1/TP2, RR, score, decision_bias, decision_strength, HTF support/resistance ver.

Yeni mantıkta formasyon kırılımı için retest zorunlu değildir. EMA/MA, RSI, hacim, HTF konum, derivatives, risk ve R:R kapıları geçiyorsa breakout anında ACTIVE giriş üretilebilir. Retest daha güvenli ikinci giriş fırsatıdır ve ayrıca güçlü retest uyarısı doğurabilir.

EARLY/WATCH planı ACTIVE işlem önerisi gibi sunma.

## 4. Haber kontrolü

Açık sinyal sembollerinde yalnız anlamlı olayları kontrol et: chain halt/restart, exploit/hack, delist/suspend, token unlock, regulatory action, major listing, protocol failure, transfer suspension, doğrulanmış önemli katalizör.

Geçmiş olayın mevcut durumunu ayrıca doğrula. Geçmişte olmuş ama çözülmüş olay yalnız risk notudur; güncel veto değildir.

NEWS VETO yalnız devam eden güçlü risk için verilebilir: chain halen durmuş, transferler halen kapalı, exploit çözülmemiş, delist/trading suspension aktif vb.

## 5. İşlem istatistiği

`trades_stats` alanını kullan. Trade count, scored_count, wins, losses, win_rate, avg_r değerlerini state'ten doğrula. Örneklem küçükse kesin performans yorumu yapma.

## 6. Spot Radar

Spot Radar Futures'tan ayrıdır. DEX coinlerinde isim/ticker tek başına kimlik değildir. Mutlaka ağ + TAM kontrat + DEX + pair adresi göster. CEX coinlerinde borsa + parite + varsa network/contract göster. Aynı ticker ile sahte token riski nedeniyle kontratsız DEX varlığını satın alma adayı gibi sunma.

## 7. Brif formatı

SABAH KRİPTO BRİFİ — [tarih/saat]

SİSTEM
- Son tarama:
- Durum:
- Fail:
- Açık plan:
- ACTIVE:
- İşlem karnesi:
- Veri kaynakları: [en güncel kaynak + varsa CACHE DIVERGENCE]

ÖNE ÇIKAN FUTURES PLANLARI
- [sembol] — [yön/stage]
  Kısa teknik durum
  Haber riski varsa bir satır

KRİTİK HABER / RİSK
- yalnız gerçekten önemli olanlar

SONUÇ
- `Şu an işlem alınabilir ACTIVE yok` veya `X ve Y işlem alınabilir durumda` gibi net sonuç.

## 8. Yapmaman gerekenler

- raw.githubusercontent çıktısını tek başına kesin gerçek kabul etme.
- cache farkını scanner kesintisi sanma.
- state.json truncation'ını veri yokluğu sanma.
- geçmiş haber durumunu güncelmiş gibi yazma.
- generic web fiyatını Binance Futures kesin fiyatı gibi verme.
- EARLY/WATCH sinyalini ACTIVE gibi sunma.
- retesti zorunlu giriş koşulu sanma.
- kanıtsız kök neden uydurma.
- spekülatif `whale`, `kesin pump`, `100x` gibi ifadeler kullanma.
