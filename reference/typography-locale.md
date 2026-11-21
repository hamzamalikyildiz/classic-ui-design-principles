# Typography, Locale, Turkish `İ/I` & Theme Toggle (`reference/typography-locale.md`)

## 1. Text Wrapping (`text-wrap: balance` & `pretty`)

- **Headings (`h1–h3`, `<= 4` lines) & centered hero subheads:** Use `text-balance` (`text-wrap: balance`).
- **Long body paragraphs (`p`, `max-w-prose`):** Use `text-pretty` (`text-wrap: pretty`) to eliminate orphan words on the last line.

```css
@layer base {
  h1, h2, h3, [data-hero-subhead] { text-wrap: balance; }
  p, dd, li { text-wrap: pretty; }
}
```

```tsx
<header className="mx-auto max-w-2xl text-center">
  <h1 className="text-4xl font-semibold tracking-tight text-balance">Aday Uyum Skoru Raporu</h1>
  <p className="mt-3 max-w-prose text-base text-muted-foreground text-pretty">
    Özgeçmişinizdeki yetkinlikleri ilanlarla karşılaştırır ve etki cümlelerini sıralar.
  </p>
</header>
```

## 2. Optical Sizing (`opsz`) & Display Tracking

- **Optical-size axis (`opsz`):** Variable fonts (`Fraunces` `opsz 9..144`, `Newsreader` `opsz 6..72`, `Inter Display` vs `Inter Text`) must enable `font-optical-sizing: auto` and load the `opsz` axis in Google Fonts / `@fontsource` (e.g. `Fraunces:ital,opsz,wght@0,9..144,400..700`).
- **Display & label tracking:** Tighten tracking at display sizes (`>= 36px`: `tracking-tight` / `-0.02em` to `-0.03em`); never apply negative tracking to body copy (`14–16px`) or `uppercase` labels (which need `tracking-wider` `0.05em–0.08em`).

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700&display=swap" />
<style>
  .font-display { font-family: "Fraunces", serif; font-optical-sizing: auto; letter-spacing: -0.025em; }
  .kicker { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
</style>
```

## 3. Numeric Discipline & `Intl` Formatting

- **Tabular numerals & alignment:** All table columns, KPI cards, counters, timers, and score rings must set `tabular-nums` (`font-variant-numeric: tabular-nums lining-nums`) and right-align numeric table columns (`tabular-nums text-right`).
- **Native `Intl` formatters:** Format currencies, percentages, dates, and relative times with native `Intl` (`Intl.NumberFormat('tr-TR', ...)`, `Intl.DateTimeFormat('tr-TR', ...)`, `Intl.RelativeTimeFormat('tr-TR', { numeric: 'auto' })` -> `"2 gün önce"`), never hardcoded `toFixed()` + string concatenation or manual `${d.getDate()}/${d.getMonth()+1}`.

```ts
const fmtTRY = new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 });
const fmtPct = new Intl.NumberFormat("tr-TR", { style: "percent", maximumFractionDigits: 1 });
const fmtDate = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short", year: "numeric" });
const fmtRel = new Intl.RelativeTimeFormat("tr-TR", { numeric: "auto" }); // (-2, "day") -> "2 gün önce"
```

```tsx
<th scope="col" className="px-4 py-3 text-right text-sm font-medium">Skor</th>
<td className="px-4 py-3 text-right text-sm font-semibold tabular-nums">{fmtPct.format(0.73)}</td>
```

## 4. Turkish Uppercase (`İ/I`, `i/ı`) & Locale Attributes

- **Document `lang="tr"`:** CSS `text-transform: uppercase` (`uppercase` in Tailwind) maps `i -> I` instead of `i -> İ` unless the document or ancestor sets `lang="tr"` (`<html lang="tr">`).
- **JS locale casing:** Always use `str.toLocaleUpperCase('tr-TR')` / `toLocaleLowerCase('tr-TR')` instead of `.toUpperCase()`.
- **Hyphenation & punctuation:** Enable `hyphens: auto` only when `lang` is set; use typographic quotes (`“...”` / `‘...’`) and en-dashes (`–`) for ranges (`30–60 sn`).

```html
<html lang="tr" class="antialiased">
<script>
  const badge = "ilan".toLocaleUpperCase("tr-TR"); // "İLAN"
  const query = input.toLocaleLowerCase("tr-TR");  // "İSTANBUL" -> "istanbul"
</script>
```

## 5. Dark Mode & Reachable Theme Toggle

- **Reachable theme control:** Whenever `.dark` / `[data-theme="dark"]` tokens or `dark:` classes exist, the UI **must** expose a user-reachable theme control (`System / Light / Dark` segmented control or toggle button in the top bar, user menu, or settings header, persisted via `next-themes` or `localStorage` + inline `<head>` script to prevent FOUC).
- Shipping dark-mode tokens with no way for the user to switch is flagged by `theme-toggle-missing`.

```html
<script>
  const t = localStorage.getItem("theme") ?? "system";
  document.documentElement.classList.toggle("dark", t === "dark" || (t === "system" && matchMedia("(prefers-color-scheme: dark)").matches));
</script>
```

```tsx
<div role="group" aria-label="Tema" data-theme-toggle className="inline-flex rounded-lg bg-muted p-1">
  {(["system", "light", "dark"] as const).map((m) => (
    <button key={m} type="button" aria-pressed={theme === m} onClick={() => setTheme(m)}
      className="h-8 rounded-md px-2 text-xs font-medium aria-pressed:bg-background">{m}</button>
  ))}
</div>
```

## 6. Linked Static & Runtime Audit Checks (İP-A8 & İP-B7)

| Engine | Rule ID | Trigger & Fix |
|---|---|---|
| Static (`uitools.py`) | `WARN tr-uppercase` | `uppercase` or `.toUpperCase()` without `lang="tr"` / `.toLocaleUpperCase('tr-TR')`. |
| Static (`uitools.py`) | `INFO numeric-columns` | Table columns, KPIs, counters, timers, or score rings missing `tabular-nums`. |
| Static (`uitools.py`) | `INFO heading-wrap` | Headings (`h1–h3`) missing `text-balance` or paragraphs (`p`) missing `text-pretty`. |
| Static (`uitools.py`) | `INFO/WARN theme-toggle-missing` | `.dark` / `[data-theme="dark"]` / `dark:` tokens exist with no theme toggle. |
| Static (`uitools.py`) | `INFO hardcoded-locale-format` | Hardcoded `.toFixed()` or `${d.getDate()}/${d.getMonth()+1}` instead of `Intl`. |
| Rendered (`render.py`) | `WARN tr-uppercase-render` | Computed `uppercase` on Turkish DOM without `lang="tr"` or broken `I/İ`. |
| Rendered (`render.py`) | `WARN theme-toggle-missing` | Dark CSS rules exist, but DOM has no visible theme toggle. |
| Rendered (`render.py`) | `INFO numeric-alignment` | Rendered `<table>` numeric columns lack `tabular-nums` or `text-right`. |
