# Claude Code Kurulum Görevi — Kripto Tarayıcı V2

Bu klasör, GitHub Actions üzerinde 15 dakikada bir çalışan bir Binance Futures
tarayıcısıdır. Görevin: bunu kullanıcının GitHub hesabında uçtan uca canlıya almak.

## Yapılacaklar (sırayla)

1. **Ön kontrol:** `gh auth status` çalıştır. `gh` yoksa işletim sistemine göre
   kurulumda yardım et (macOS: `brew install gh`, Windows: `winget install GitHub.cli`,
   Debian/Ubuntu: `sudo apt install gh`), sonra `gh auth login` akışını yürüt.

2. **Repo oluştur ve yükle:** Bu klasörden:
   - `git init` (gerekiyorsa), tüm dosyaları commit'le
   - `gh repo create kripto-tarayici --public --source=. --push`
   - Repo adı doluysa kullanıcıya alternatif ad sor.
   - NOT: Repo PUBLIC olmalı (Actions dakikası sınırsız olsun diye — kullanıcının
     bilinçli tercihi). `state/state.json` şu anki temiz haliyle commit'lenmeli.

3. **Secrets:** Kullanıcıdan Telegram bot token ve chat_id iste
   (daha önce BotFather'dan aldı). Şunlarla tanımla:
   - `gh secret set TELEGRAM_BOT_TOKEN`
   - `gh secret set TELEGRAM_CHAT_ID`
   Değerleri komut satırı geçmişine yazmamaya çalış (stdin ile ver).
   `CRYPTOPANIC_TOKEN` opsiyonel; kullanıcı istemezse atla.

4. **İlk çalıştırma:** `gh workflow run crypto-scan-v2` → `gh run watch` ile izle.
   Başarı ölçütü: kullanıcının Telegram'ına "🚀 Kripto Tarayıcı V2 aktif" mesajı
   düşmesi VE run sonunda `state/state.json`'ın bot tarafından commit'lenmesi.

5. **Cron doğrulama:** `.github/workflows/scan.yml` içindeki `*/15 * * * *`
   zamanlamasının aktif olduğunu `gh workflow list` ile göster.

6. **Bitiş çıktısı:** Kullanıcıya şunları ver:
   - Repo URL'si
   - Actions sayfası URL'si
   - `state.json` raw URL'si: `https://raw.githubusercontent.com/<KULLANICI>/<REPO>/main/state/state.json`
   - Bu raw URL'yi aşağıdaki "Cowork Sabah Brifi" şablonuna yerleştirip hazır
     prompt olarak sun.

## Sorun giderme bilgisi

- İlk run'da Telegram'a "🚨 VERİ KAYNAĞI SORUNU" gelirse: GitHub'ın ABD IP'leri
  Binance tarafından engellenmiş olabilir. `scanner/data.py` birden çok host
  dener (www.binance.com yolu genelde çalışır). Log'da hangi hostların denendiğini
  incele. Kalıcıysa kullanıcıya Avrupa lokasyonlu VPS alternatifini hatırlat —
  kod değişmeden cron ile çalışır.
- Workflow "Resource not accessible" hatası verirse: repo Settings → Actions →
  General → Workflow permissions → "Read and write permissions" seçili olmalı.
- 60+ gün commit olmazsa GitHub cron'u durdurur; her run state commit'lediği
  için normalde bu tetiklenmez.

## Cowork Sabah Brifi şablonu (adım 6'da doldur)

```
Şu dosyayı çek ve JSON olarak oku: <STATE_RAW_URL>
1. "signals" içinde EARLY/WATCH/ACTIVE durumundaki kayıtları listele: sembol,
   yön, tetik, SL, TP1/2/3, kaç saattir açık.
2. "log"daki son 24 saati özetle: kaç yeni sinyal, kaç iptal, kaç stop/TP.
3. "trades" doluysa win rate ve ortalama R hesapla; 30'dan az işlemde
   "istatistik henüz olgunlaşmadı" uyarısı ekle.
4. Açık sinyallerdeki coinler için web'de son 24 saatin haberlerini tara;
   delisting/hack/unlock gibi kritik olayları en üste yaz.
5. BTC ve genel piyasa için kısa rejim notu ver (trend mi range mi).
6. Çıktı: Türkçe "Sabah Brifi" — (a) açık sinyaller ve bugün izlenecek
   seviyeler, (b) haber riskleri, (c) piyasa rejimi, (d) varsa sistem ayar
   önerisi. Kendi sinyalini üretme; script seviyelerinin dışına çıkma. Bu bir
   yorum katmanıdır, işlem emri değildir.
```

## Yapmayacakların

- Kullanıcı adına işlem/emir sistemi kurma — bu proje yalnızca analiz + bildirim.
- Secret değerlerini dosyaya, log'a veya commit'e yazma.
- `scanner/` içindeki sinyal kurallarını kullanıcıya sormadan değiştirme.

## V3-QA DAĞITIM GÖREVİ (mevcut canlı repo: KDUMAN71/kripto-tarayici)

### ADIM 0 — TEŞHİS (önce bu; tarayıcı ~33 saattir koşmuyor)
1. `gh run list -R KDUMAN71/kripto-tarayici --limit 15` — 26 Ağustos 22:42 TR
   sonrasında run var mı?
   - Hiç run yoksa: `gh workflow list -R KDUMAN71/kripto-tarayici` ile workflow
     "disabled" mı bak; öyleyse `gh workflow enable scan.yml -R ...` ile aç.
   - Run var ama kırmızıysa: `gh run view <id> --log-failed` ile hatayı oku ve
     kullanıcıya raporla (muhtemel: veri kaynağı/commit adımı).
2. Sonucu kullanıcıya kısaca bildir (neden durmuştu).

### ADIM 1 — V3-QA KODUNU YAYINLA
1. `gh repo clone KDUMAN71/kripto-tarayici /tmp/kt`
2. Bu klasörden kopyala: `cp -r scanner /tmp/kt/ && cp README.md CLAUDE.md /tmp/kt/ && cp .github/workflows/scan.yml /tmp/kt/.github/workflows/scan.yml`
   (`state/` DOKUNMA — canlı sinyal geçmişi korunmalı.)
3. Commit + push: "V3-QA: formasyon motoru + confluence + intrabar SL takibi + scan_log"

### ADIM 2 — DOĞRULAMA
1. `gh workflow run scan.yml -R KDUMAN71/kripto-tarayici` (workflow adı artık
   crypto-scan-v3; dosya adıyla tetiklemek her durumda çalışır)
2. Log'da şu üçü görülmeli: "REJIM:" satırı, "V3 tamamlandi", state commit adımı.
3. state.json'da yeni `scan_log` alanı dolmalı (ts/ok/symbols/duration_s).
4. Sinyal koşulları oluşursa Telegram mesajında Formasyon + Skor satırları olmalı.
5. Cron dakikaları 7/22/37/52'ye kaydırıldı (GitHub :00/:15/:30/:45'te yoğun;
   tam çeyrek dakikalar en çok geciken/atlanan slotlardır). Bu 1. kademe çözümdür;
   1-2 gün gözlemlenecek. Hâlâ boşluk olursa 2. kademe: cron-job.org + PAT ile
   workflow_dispatch tetikleme (kullanıcı kararı).

