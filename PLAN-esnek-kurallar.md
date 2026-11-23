# Plan: Kalıpları azaltmak, zorunlulukları tabana indirmek

Durum: taslak, uygulanmadı. Hedef sürüm: `v1.0.0` öncesi.

## 1. Neden

Skill büyüdükçe "zorunlu" kural sayısı arttı ve ajanlar bu kuralları eksiksiz karşılamaya çalışırken sayfaların kendisi zayıfladı. Repo'daki ölçümler bu yönde işaret ediyor:

- **Zorla konan figür kaybettirdi.** run7'de skill "her ana ekranda bir imza çizimi" kuralına uyup bir kase ve alev çizdi; hakemlerin beşte dördü bu çizimi "garip" bulup karşı sayfayı seçti. Aynı türde run5'te ise "saf tipografi" kuralına uyan çizimsiz tarif sayfaları 0/5 kaybetti. Her iki kayıp da bir kalıbın brief'e bakılmadan uygulanmasından geliyor.
- **Temiz kontrol, kötü sonuç.** run9'da skill'li uygulamalar hareket kontrollerinden neredeyse sıfır uyarıyla geçti (0,83'e karşı 8,0), ama hakemler hareket ve akıcılıkta skill'li sayfaları daha kötü buldu (-1,37). Ajan uyarıyı kapatmayı öğrendi, iyi hareket tasarlamayı değil.
- **Kural arttıkça kazanma oranı düştü.** run8 (6 çift, %83) ile aynı brief'lerde koşan reg_v2 %53'te kaldı. Örnek küçük, kesin gerileme sayılmaz, ama yön uyarı veriyor.
- **Zorunlu dil yoğun.** `must / never / always / mandatory / every / exactly` gibi ifadeler: `reference/rules.md` 17, `reference/app-flow.md` 15, `SKILL.md` 13, `moods/editorial.md` 11 kez geçiyor. Statik denetimde 17 kural WARN seviyesinde ve `SKILL.md` ile `app-flow.md` "her WARN'ı düzelt" diyor.

Sonuç: kuralların çoğu kalite tavanı değil, uyulması gereken bir form gibi işliyor. Ajanın zamanı ve dikkati formu doldurmaya gidiyor.

## 2. İlke: üç katman

| Katman | Ne demek | Ajan ne yapar | Denetim seviyesi |
|---|---|---|---|
| **Taban** | Ölçülebilir, tartışmasız: erişilebilirlik ve kırık düzen | Her zaman uyar | FAIL veya WARN |
| **Varsayılan** | İyi bir başlangıç noktası | Brief başka bir şey istemiyorsa uygular, sapınca raporda bir cümleyle söyler | INFO |
| **Fikir menüsü** | İlham listesi | Uygun olanı seçer, hiçbirini zorunlu saymaz | Denetlenmez |

Kural yazım dili buna göre değişir: tabanda "must", varsayılanda "default / start with", menüde "ideas / consider". Sayılar (satır adedi, piksel, yarıçap) varsayılan katmanında "örnek değer" olarak kalır.

## 3. Taban listesi (tamamı bu kadar)

1. Metin ve UI kontrastı WCAG AA (4,5:1 gövde, 3:1 büyük metin ve UI), gradyanlar ve iki tema dahil.
2. Görünür klavye odağı, klavyeyle ulaşılabilir kontroller, düğme ve bağlantıların erişilebilir adı.
3. `prefers-reduced-motion` desteği; düzen özelliklerini (width, height, top, left, margin, padding) animasyonla oynatmamak.
4. İçerik JavaScript olmadan görünür (`opacity-0` başlangıç durumu yok).
5. Kesilen, taşan veya üst üste binen içerik yok; 375px'te yatay kaydırma yok.
6. Gövde metni 12px altına inmez; ana dokunma hedefi en az 24×24px (WCAG 2.5.8).
7. `<main>` ve temel landmark'lar.
8. Dil doğruluğu: `lang` özniteliği, Türkçe büyük harf (`tr-TR`), yerel sayı ve tarih biçimi.
9. Lorem ipsum ve "Feature one" gibi yer tutucu metin yok.

Bu listenin dışındaki her şey varsayılan ya da fikir menüsü olur.

## 4. Belge değişiklikleri

| Yer | Şu an | Olacak |
|---|---|---|
| `SKILL.md:42` | "Her ana ekranda bir imza öğesi" (çizim veya etkileşim) | Varsayılan: "Akılda kalan tek bir öğe düşün; büyük tipografi, gerçek veri veya küçük bir etkileşim de olur. Brief'e zorla eklenmiş hissettirecekse ekleme." Editorial çelişkisi böylece kendiliğinden kalkar. |
| `SKILL.md:47` | "Her paneli doldur" | Taban dışı: "Yarı boş panel bırakma; daha küçük panel veya tek sütun da çözüm." |
| `SKILL.md:53` | 60-30-10, ekran başına tek hero yüzeyi | Varsayılan olarak etiketle. |
| `SKILL.md:84` | "FAIL ve WARN'ları düzelt" | "FAIL ve taban uyarılarını düzelt. Stil önerilerinde (INFO) karar ver, uymadıysan raporda bir cümleyle söyle." |
| `SKILL.md:90`, `reference/app-flow.md` §5 | "Mandatory Coverage Report" ve tam tablo | Kısa kapsam notu: hangi ekranlar yapıldı, hangisi eksik. Tablo isteğe bağlı. |
| `reference/app-flow.md:35` | "Envanterdeki her durumu uygula" | "Ekranın gerçekten sahip olduğu durumları uygula (çoğu ekranda yükleniyor, boş ve hata yeterli)." |
| `reference/app-flow.md:37` | "Her WARN'ı düzelt" | `SKILL.md:84` ile aynı dil. |
| `reference/states.md` §4 | "Mandatory State Coverage Table" | 9 durumlu matris kontrol listesi olarak kalır; zorunlu tablo kalkar. |
| `reference/rules.md:10` | Grafik paleti için sabit renk listesi | Örnek olarak kalır, zorunlu değil. |
| `reference/rules.md:40-41` | Her listeye iskelet ve boş durum, her etkileşimli öğeye 4 durum | Odak görünürlüğü tabanda kalır; iskelet, boş durum ve hover gibi durumlar varsayılan olur. |
| `reference/typography-locale.md:26, 39` | `opsz` ve her tabloda `tabular-nums` "must" | Varsayılan. |
| `reference/typography-locale.md:70` | Koyu tema token'ı varsa tema düğmesi "must" | Sistem tercihini izleyen koyu tema yeterli; düğme varsayılan. |
| `moods/*.md` | Satır adetleri (6-10, 8-12), yarıçap ve boşluk pikselleri | "Başlangıç değerleri" başlığı altında toplanır. |
| `moods/editorial.md` | 11 zorunlu ifade | Taban ögeleri dışında "default" diline çevrilir. |

Genel kural: `SKILL.md` 10 KB altında kalır, toplam zorunlu ifade sayısı yarıdan aza iner (ölçüm: aynı `grep` sayımı).

## 5. Denetim araçlarındaki değişiklikler

**`uitools.py audit`: WARN'dan INFO'ya inecekler (stil ve zevk):**
`grid`, `single-primary-cta`, `miller-7`, `no-hero-surface`, `card-sameness`, `bold-headline-size`, `no-drawn-mascot`, `grey-chart`, `edge-align`, `headline-measure`, `left-stacked-column`, `editorial-leading`.

`fitts-primary` ikiye bölünür: 24px altı WARN (taban), 24-44px arası INFO.

**WARN olarak kalacaklar (taban):** `wcag-aa` (FAIL), `landmark-main`, `reveal-needs-js`, `tr-uppercase`, `line-length`.

**`render.py --check`: INFO'ya inecekler:**
`theme-toggle-missing`, `long-wait-unexplained`, `empty-panel`, `empty-column`, `hollow-text`, `slow-feedback`.

**WARN olarak kalacaklar:** `clipped-content`, `page-overflow-x`, `mobile-overflow-x`, `overlapping-labels`, `invisible-content`, `empty-control`, `no-focus-ring`, `reduced-motion-ignored`, `motion-layout-property`, `layout-shift`, `blank-band`, `desktop-tiny-text`, `mobile-tiny-text`, `tr-uppercase-render`, axe'in ciddi ve kritik ihlalleri.

**Eski davranış korunur:** iki araca `--strict` bayrağı eklenir; açıkken bugünkü seviyeler geçerli olur. Böylece katı kontrol isteyen ekipler ve aşağıdaki kıyas için eski sürüm hazır kalır.

**Rapor biçimi:** çıktıda önce taban sonuçları ("must fix"), sonra öneriler ("consider") ayrı başlıklarla yazılır. Testler yeni seviyelere göre güncellenir.

## 6. Ölçüm (önceden kayıtlı)

Değişiklikler gerçekten verimi artırıyor mu, tahminle değil ölçümle karar verilecek.

- **Kollar:** `strict` (bugünkü sürüm, `aac46ae`), `loose` (bu plan uygulanmış hali), `noskill`.
- **Brief'ler:** yeni bir `bench/briefs_holdout_v3.json`, kodlamadan önce commit edilir: beş mood'dan 2'şer sayfa (10) ve 2 çok ekranlı uygulama akışı. Daha önce hiçbir koşuda kullanılmamış konular.
- **Üretici ve hakem:** üretici Haiku, hakemler farklı aileden 5 kişilik hakem (Sonnet); mümkünse ikinci tekrar Gemini ile. Ek olarak `bench/human` kitiyle en az 5 gerçek kişi.
- **Ölçülecekler:**
  - Hakem kazanma oranı: `loose` - `strict` ve her ikisi - `noskill`.
  - Taban metrikleri: ciddi axe ihlali, taban WARN sayısı.
  - Verim: sayfa başına token, araç çağrısı ve süre; kullanılan düzeltme turu.
  - Sayfa uzunluğu (uzunluk etkisini ayırmak için).
- **Karar kuralı (önceden yazılı):** `loose` kabul edilir eğer
  1. hakemlerde `strict`'e karşı en az eşit kalırsa (oy oranı ≥ %45 ve güven aralığı %50'yi kapsıyorsa),
  2. taban metrikleri kötüleşmezse (ciddi axe ihlali skill kolunda 0 kalırsa),
  3. sayfa başına token veya süre en az %20 düşerse.
  Biri tutmazsa, hangi değişikliğin sorun çıkardığı ayrı ayrı geri alınıp yeniden denenir. Sonuç ne çıkarsa çıksın README'ye yazılır.

## 7. Paralel küçük işler (bağımsız, hemen yapılabilir)

- **Hafif paket:** yalnızca `SKILL.md`, `moods/`, `reference/`, `scripts/`, `LICENSE` içeren zip üreten bir betik (`bench`, `examples`, `tests` hariç); README'de claude.ai yüklemesi için bu zip gösterilir.
- **`requirements.txt`:** Playwright, Pillow; node/npm notu.
- **npm sürümleri sabitlenir:** `tailwindcss`, `axe-core`, `@fontsource/*`.
- **Sandbox:** Chromium varsayılanda sandbox'lı açılır, `--no-sandbox` bir bayrağa bağlanır (`scripts/render.py:644`, `bench/build_pairs.py:132`).
- **`/tmp/axe` araması kalkar** (`scripts/render.py:178`).
- **README'de `python3` yerine `python`** (Windows uyumu).
- **İlk sürüm:** `v1.0.0` etiketi ve kısa `CHANGELOG.md`.
- **Temizlik:** commit edilmemiş `bench/runs/bold_quick/` silinir veya arşivlenir.

## 8. Sıra

1. Bölüm 7 (küçük işler), çünkü ölçümü etkilemez.
2. `bench/briefs_holdout_v3.json` yazılıp commit edilir (ölçümden önce dondurulur).
3. `strict` sürümü etiketlenir (`v1.0.0-strict` veya commit hash'i not edilir).
4. Bölüm 4 ve 5 uygulanır, testler güncellenir, CI yeşil.
5. Bölüm 6 ölçümü koşulur, karar kuralına göre ilerlenir.
6. README ve `bench/runs/README.md` güncellenir, `v1.1.0` olarak yayımlanır.

## 9. Riskler

- **Taban dışı kurallar gevşeyince sayfalar sadeleşebilir.** Önceki run'larda daha dolu sayfalar hakemlerde avantaj sağlamıştı. Ölçüm bunu yakalar; uzunluk ayrı raporlanır.
- **Model hakemlere göre ayar yapma tuzağı.** Kural değişiklikleri hakem gerekçelerine bakılarak değil, bu plandaki ilkeye göre yapılır; ölçümden sonra tek tur düzeltme hakkı var.
- **Katı denetim isteyen kullanıcılar.** `--strict` bayrağı bu ihtiyacı karşılar.

## 10. Bitti sayılma ölçütü

- Zorunlu ifade sayısı belgelerde yarıdan aza indi; taban listesi tek bir yerde (`SKILL.md`) duruyor.
- Statik denetimde WARN seviyesinde yalnızca taban kuralları var; `--strict` eski davranışı veriyor.
- CI Windows ve Ubuntu'da yeşil.
- Bölüm 6'daki ölçüm koşuldu, sonucu ve kararı `bench/runs/` altında yazılı.
