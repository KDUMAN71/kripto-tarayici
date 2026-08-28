# V3 QA düzeltmeleri

- Taker pressure son kapalı 1H barı artık atlamıyor.
- Simetrik üçgen SHORT confluence yanlış üst tetik kullanımından düzeltildi.
- 1D trend bağlamı 240 günlük veriyle gerçek EMA200 kullanıyor.
- Top trader/global L/S oranları türev skoruna eklendi; global aşırı crowding türev puanını engelliyor.
- Telegram mesajlarına taker, L/S, basis ve spread görünürlüğü eklendi.
- Paper trade STOP/TP takibi intrabar high/low kullanıyor; hard SL kapanış beklemiyor.
- Haber yok/API başarısız durumları "haber teyidi yok" diye raporlanıyor.
- Pattern detector exception'ları GitHub loglarında görünür hale getirildi.
- Workflow ve runtime etiketleri V3 olarak düzeltildi.
