# İnsan Değerlendirme Kiti (Kör A/B)

Bu klasör, UI çıktılarının gerçek insanlar tarafından **kör A/B** olarak değerlendirilmesi ve sonuçların otomatik olarak puanlanıp LLM jüri sonuçlarıyla karşılaştırılması için kullanılır. Tüm araçlar yalnızca Python standart kütüphanesini kullanır.

## 1. Kitin Üretilmesi (`make_human_kit.py`)

Bir benchmark koşusundan (`<run_dir>` içinde `pairs.json` ve `pairs/` medyaları bulunur) tamamen çevrimdışı, tek klasörlük bir statik galeri oluşturun:

```bash
python bench/human/make_human_kit.py \
  --run-dir bench/runs/run1 \
  --out-dir dist/human_kit_run1 \
  --seed 42
```

Çıktı klasöründe yalnızca şunlar yer alır:
- `index.html` (harici ağ isteği, CDN veya izleyici içermez)
- `media/<pair_id>/<A|B>/...` (kopyalanmış `contact-sheet.png`, varsa `filmstrip.png` / `.mp4` / `.gif`)

`key.json` veya hangi tarafın `skill` / `noskill` olduğunu belirten hiçbir alan kite **kesinlikle kopyalanmaz**. Çiftlerin sırası `--seed` ile karıştırılır.

## 2. En Az 5 Gerçek Kullanıcıya Dağıtım

1. Üretilen `dist/human_kit_run1/` klasörünü `.zip` olarak paketleyin veya herhangi bir statik sunucuda barındırın.
   - Katılımcılar `.zip` dosyasını açıp `index.html` dosyasını tarayıcılarında doğrudan (`file://` üzerinden bile) açabilir.
2. En az **5 gerçek kullanıcıya** (ör. Tasarımcı, Geliştirici ve Son kullanıcı rollerinden karma) gönderin.
3. Her katılımcı:
   - İsteğe bağlı olarak **Rol** ve **Göz/okuma durumu** seçer.
   - Her çiftte **A** ve **B** seçeneklerini yan yana (`Contact Sheet` ve varsa `Filmstrip / Hareket` sekmesiyle, tıklayıp büyüterek) inceler.
   - **6 kriteri** (1–5) puanlar, **Genel Tercih (A / B)** seçer ve isterse kısa gerekçe yazar.
   - İlerleme tarayıcının `localStorage` alanında otomatik saklanır.
   - Tüm çiftler bitince sağ üstteki **"CSV İndir"** butonuna basar ve oluşan `.csv` dosyasını size iletir.
4. Dönen tüm `.csv` dosyalarını tek bir klasörün içine (ör. `bench/runs/run1/csvs/`) toplayın.

## 3. Puanlama ve LLM Karşılaştırması (`score_human.py`)

Toplanan CSV'leri gizli `key.json` ile eşleştirerek puanlayın:

```bash
python bench/human/score_human.py \
  --csv-dir bench/runs/run1/csvs \
  --key bench/runs/run1/key.json \
  --llm-summary bench/runs/run1/llm_results.json \
  --out-md bench/runs/run1/HUMAN_RESULTS.md
```

Rapor şunları üretir:
- Skill vs No-Skill kazanma oranı ve **Wilson %95 güven aralığı**
- 6 kriter için **Skill − No-Skill** ortalama puan farkları
- **Rol bazlı** kırılım
- Opsiyonel `--llm-summary` (JSON dosyası veya `verdicts/` klasörü) verildiğinde yan yana karşılaştırma tablosu ve **Cohen's κ (kappa)** uyum katsayısı

## 4. Gizlilik Garantisi

- **Kişisel veri toplanmaz:** İsim, e-posta, IP adresi veya hesap bilgisi istenmez ve kaydedilmez.
- **Anonim oturum kodu:** Yalnızca aynı oylayıcının satırlarını gruplamak için tarayıcıda rastgele üretilen `rater_id_anon` (ör. `r_a1b2c3d4`) kullanılır.
- **Körlük koruması:** `key.json` yalnızca `score_human.py` çalıştırılırken analiz aşamasında okunur; dağıtılan kitte bulunmaz.
