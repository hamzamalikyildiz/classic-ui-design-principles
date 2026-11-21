# Kovan CV — Skill v2 (App Modu) İyileştirme Raporu (`examples/app-demo` → `examples/app-demo-polished`)

> **Plan Beyanı:** `Mode: App | Mood: Trust | Stack: Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui (oklch) + MSW | Hedef: examples/app-demo-polished/`
>
> **Not:** `examples/app-demo/src/**` dosyalarına dokunulmamıştır (`tests/test_app_demo_audit.py` CI'da 6 bilinçli hatayı doğrulamaya devam eder). Tüm Skill v2 App modu iyileştirmeleri `examples/app-demo-polished/` altında uygulanmıştır.

---

## 1. Ekran Envanteri (Adım 1 — `reference/app-flow.md` §1)

| Screen | Route | Primary user job | Data dependency | Critical states | Priority |
|---|---|---|---|---|---|
| Başvuru Listesi | `/cv` | Adayları skora/duruma göre tarayıp incelemeye açmak | `GET /api/cv` | Empty (ilk kullanım + filtre), Loading, Long (>3s), Error, Partial, Locked, Success, Offline, Stale | **P0** |
| Aday CV Detayı | `/cv/:id` | Uyumluluk skorunu görmek, AI önerilerini onaylamak/reddetmek, 30s AI analizi çalıştırmak | `GET /api/cv/:id`, `POST /api/cv/:id/analyze` | Empty, Loading, Long (>3s), Error, Partial, Locked, Success, Offline, Stale | **P0** |
| Oturum Açma | `/login` | Kurumsal hesapla platforma giriş yapmak | `localStorage` / cookie oturumu | Empty, Loading, Long (>3s), Error, Success | **P1** |
| Hesap ve Tercihler | `/settings` | Profil bilgilerini ve haftalık bildirim tercihini güncellemek | `getSession()` | Empty, Long (>3s), Error, Success | **P2** |

---

## 2. Zorunlu Kapsam Raporu (`reference/app-flow.md` §5)

| Screen | Priority | Done | States covered | Motion | Open gaps |
|---|---|---|---|---|---|
| `/cv` | P0 | Redesigned | 9/9 | GPU `scaleX` bar + `80ms` tactile press | – |
| `/cv/:id` | P0 | Redesigned | 9/9 | `500ms` SVG score ring + count-up (`tabular-nums`), `1.2s` `.row-ok` flash, `4s` Undo toast, `reduced-motion` fallback | – |
| `/login` | P1 | Styled to match | 5/5 | `80ms` tactile press, `LongOperationPanel` | – |
| `/settings` | P2 | Styled to match | 4/4 | `80ms` tactile press, `LongOperationPanel` | Çevrimdışı/kilitli durumları kapsam dışı (P2) |

---

## 3. 9-Durum Kapsam Matrisi (`reference/states.md` §4)

| Screen | Empty | Loading | Long (>3s) | Error | Partial | Locked | Success | Offline | Stale |
|---|---|---|---|---|---|---|---|---|---|
| `/cv` | yes (ilk kullanım + filtre) | yes (`aria-busy`, skeleton) | yes (`LongOperationPanel`) | yes (`role="alert"`, filtre korunur) | yes (`—` + `aria-label="Metric pending"`) | yes (kilit bandı + `disabled`) | yes (ekleme `role="status"`) | yes (çevrimdışı banner + önbellek) | yes (`Intl.RelativeTimeFormat` + Yenile) |
| `/cv/:id` | yes (boş kayıt + filtre) | yes (`aria-busy`, skeleton) | yes (`LongOperationPanel`) | yes (`role="alert"`, not korunur) | yes (`—` + `Yanıt Kaydet`) | yes (kilit bandı + `aria-describedby`) | yes (skor artışı + `1.2s` flash + Undo toast) | yes (yerel not düzenlenebilir) | yes (`Intl.RelativeTimeFormat` + Yenile) |
| `/login` | yes | yes | yes (`LongOperationPanel`) | yes (`role="alert"`) | n/a | n/a | yes (`/cv` yönlendirmesi) | - | n/a |
| `/settings` | yes | n/a | yes (`LongOperationPanel`) | yes (`role="alert"`) | n/a | n/a | yes (`role="status"` kaydedildi) | - | n/a |

---

## 4. 6 Gerçek Hatanın Önce → Sonra Özeti

| # | Kural / Hata | Önce (`examples/app-demo`) | Sonra (`examples/app-demo-polished`) |
|---|---|---|---|
| **#1** | `wcag-aa` (Düşük kontrast) | `CvDetailPage.tsx`: `bg-slate-100 text-slate-300` (**1.36:1** — FAIL) | Semantik `bg-muted text-muted-foreground` tokenlarına geçildi (**FAIL=0**) |
| **#2** | `single-primary-cta` (2 dolu CTA) | `CvDetailPage.tsx`: Hero'da 2 adet dolu `<Button size="lg">` (**WARN**) | Yalnızca `"30s AI Analizi Başlat"` dolu birincil; `"Raporu Dışa Aktar"` `variant="outline"` yapıldı |
| **#3** | `shadcn-defaults` (`10px` rozet) | `badge.tsx` `micro` varyantı + `text-[10px]` | `micro` kaldırıldı; tüm rozetler `text-xs` (`12px`) minimumunda |
| **#4** | `tr-uppercase` (`lang="tr"` eksik) | `index.html`: `<html lang="en">` ve JSX'te `lang` yok (**WARN**) | `<html lang="tr">` + uppercase Türkçe başlıklarda `lang="tr"` ve `tracking-wider` |
| **#5** | `long-wait-unexplained` (>3s yalnız spinner) | `animate-spin` + `"Hazırlanıyor..."` (aşama/ilerleme/iptal yok) | `LongOperationPanel`: 3 isimli aşama, `role="progressbar"`, `Geçen X sn · Genellikle 30–60 sn` (`tabular-nums`), yetkinlik önizlemesi, `"İptal Et"` + `"Hazır Olunca Bildir"` |
| **#6** | `motion-layout-property` (`width/height` animasyonu) | `transition: width 350ms, height 350ms` + `panel-expand-width` | GPU-composited `transform: scaleX(...)` + `opacity`, `:root` `80–500ms` tokenları, SVG score ring (`stroke-dashoffset`), count-up, `1.2s` `.row-ok` flash, `4s` Undo toast ve `prefers-reduced-motion: reduce` fallback |
| **Ek** | Karanlık mod tema anahtarı | Yalnızca ikon butonu (`Sistem` modu ve `localStorage` kalıcılığı yok) | `ThemeToggle` (`Sistem / Aydınlık / Karanlık`, `data-theme-toggle="true"`, `localStorage` + FOUC önleyici `<head>` betiği) |

---

## 5. Gerçek Ölçüm Çıktıları (Önce vs Sonra)

### 5.1. Statik Denetim (`python scripts/uitools.py audit --route ... --mood trust`)

| Rota | Önce (`examples/app-demo`) | Sonra (`examples/app-demo-polished`) |
|---|---|---|
| `CvListPage.tsx` (`/cv`) | `FAIL=0 WARN=0 INFO=1` | **`FAIL=0 WARN=0 INFO=1`** |
| `CvDetailPage.tsx` (`/cv/:id`) | **`FAIL=1 WARN=2 INFO=1`** (`wcag-aa`, `single-primary-cta`, `tr-uppercase`) | **`FAIL=0 WARN=0 INFO=1`** |
| `LoginPage.tsx` (`/login`) | `FAIL=0 WARN=0 INFO=1` | **`FAIL=0 WARN=0 INFO=1`** |
| `SettingsPage.tsx` (`/settings`) | `FAIL=0 WARN=0 INFO=1` | **`FAIL=0 WARN=0 INFO=1`** |

### 5.2. Gerçek Tarayıcı + Hareket Denetimi (`python scripts/render.py --routes ... --motion`)

4 rota × 5 durum (`default`, `empty`, `loading`, `long-loading`, `error`) × 2 görünüm (`desktop 1440×900`, `mobile 390×844`) = **40 yakalama** üzerinden:

| Metrik | Önce (`examples/app-demo`) | Sonra (`examples/app-demo-polished`) | Değişim |
|---|---|---|---|
| **FAIL** | `0` | **`0`** | `0` |
| **WARN** | `57` | **`17`** | **`-40` (%70 azalma)** |
| **INFO** | `40` | `63` | `+23` (`ThemeToggle` + ek etkileşimli kontroller) |
| `cv-detail / default` (desktop & mobile) | `WARN: 5 / 6` | **`WARN: 0 / 0`** | Tüm `axe-color-contrast`, `reduced-motion-ignored` ve `theme-toggle-missing` uyarıları kapandı |
| `cv-list / long-loading` (desktop & mobile) | `WARN: 2 / 2` | **`WARN: 0 / 0`** | `long-wait-unexplained` + `reduced-motion-ignored` kapandı |
| `cv-detail / long-loading` (desktop & mobile) | `WARN: 4 / 4` | **`WARN: 0 / 0`** | `long-wait-unexplained` + `reduced-motion-ignored` kapandı |
| `settings / long-loading` (desktop & mobile) | `WARN: 3 / 3` | **`WARN: 0 / 0`** | `long-wait-unexplained` + `reduced-motion-ignored` kapandı |

> **Kalan 17 `WARN` hakkında:** 10 tanesi `?state=error` mock rotasındaki kasıtlı HTTP 500 yanıtının ürettiği `js-errors`/`network-errors` uyarılarıdır; 6 tanesi boş/yükleme durumlarındaki kısa içerik alanının `empty-column` uyarısıdır; 1 tanesi `login/long-loading` üzerindeki `slow-feedback` ölçümüdür.

### 5.3. Derleme Doğrulaması

`examples/app-demo-polished` içinde `npm install && npm run build` (`tsc -b && vite build`) hatasız tamamlandı (`dist/` ve `node_modules/` `.gitignore` kapsamındadır, commit edilmemiştir).
