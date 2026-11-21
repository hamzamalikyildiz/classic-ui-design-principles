Her çiftte aynı brief'ten üretilmiş iki web sayfasının (A ve B) ekran görüntülerini inceleyeceksin. Hangi aracın ya da kuralın ürettiğini bilmiyorsun, bilmen de gerekmiyor.

Değerlendirme kriterleri (her biri 1-10 puan):
1. Görsel çekicilik
2. Profesyonel görünüm ("yapay zeka şablonu" hissi yok mu)
3. Hiyerarşi ve okunabilirlik
4. İçerik zenginliği

<!-- APP_MODE -->
Uygulama akışı ek kriterleri (`--app` modu, toplam 6 kriter):
5. Durumlar ve geri bildirim (States & feedback): boş (`empty`), yükleniyor (`loading`), >3s uzun bekleme (`long-loading`: adım/ilerleme/geçen süre/iptal), hata (`error`), kısmi veri (`partial`), kilitli (`locked`) ve sonuç mikro anları.
6. Hareket ve akıcılık (Motion & fluidity): filmstrip üzerinden geçiş akıcılığı, tepki hızı, görsel geri bildirim kalitesi.

Çıktı formatı (her çift için tek satır, başka açıklama ekleme):
- Tek sayfa modu (4 kriter): `ciftN: A | 4 | tek cümle gerekçe | A 8/8/7/9 B 7/6/8/7`
- Uygulama modu (`--app`, 6 kriter): `ciftN: A | 4 | tek cümle gerekçe | A 8/8/7/9/8/7 B 7/6/8/7/5/6`
- `A` veya `B`: tercih (beraberlik yok, zorunlu seçim)
- `1-5`: güven (5 = çok emin)
- `tek cümle gerekçe`: bu tercihi açıklayan kısa tek cümle
- `A x/... B y/...`: yukarıdaki 4 (tek sayfa) veya 6 (uygulama) kriter için 1-10 puanlar

Kurallar:
- Sayfaları kendi zevkine göre değerlendir, "kurallara uyuyor mu" diye değil.
- Uzunluk ya da süs tek başına puan getirmesin, işe yarayan ve tutarlı olan kazansın.
- Pozisyona göre (hep A ya da hep B) cevap verme.
