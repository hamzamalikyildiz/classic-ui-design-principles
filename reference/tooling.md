# Tooling details

**Severity levels.** By default `audit` and `render.py --check` keep only the floor at FAIL/WARN (contrast, landmark, hidden-until-JS content, line length, Turkish casing; clipped or overflowing content, focus rings, reduced motion, layout-property animation, axe serious/critical). Style and taste findings (grid, CTA count, hero surface, Miller 7, card sameness, grey charts, editorial layout hints, empty panels/columns, hollow text, theme toggle, slow feedback) are reported as INFO with the note `[style suggestion; --strict keeps WARN]`. Primary CTAs under 24px stay WARN; 24-44px is INFO. Pass `--strict` to `uitools.py audit` and `render.py` to keep every finding at its old WARN level (useful in CI).

`uitools.py` runs with Python 3 stdlib only (`uicolor.py`, `uiparse.py`, `uiroute.py`, `uiignore.py`). `render.py` uses Playwright + headless Chromium and `scripts/checks/*.js` (`check.js`, `mobile.js`, `interact.js`, `motion.js`, `sweep.js`).

## `uitools.py` commands & flags

```bash
python scripts/uitools.py --help
python scripts/uitools.py audit --help
python scripts/uitools.py contrast "oklch(0.70 0.18 250)" white
python scripts/uitools.py scale --base 16 --ratio major-third
python scripts/uitools.py radius 24 8
python scripts/uitools.py snap 13 22 --grid 8
```

### Audit flags

- `--route PATH [PATH ...]`: route entry file(s) with cross-file component inlining (`--root DIR`, `--tsconfig PATH` for `@/` and `tsconfig.json` path aliases).
- `--routes-glob GLOB`: glob pattern for route entry files (e.g. `"app/**/page.tsx"`).
- `--grid GRID`: soft grid (default `8`); values off the 4px grid are always `WARN`.
- `--css [CSS ...]`: CSS files with `:root` / `.dark` tokens (e.g. `app/globals.css`).
- `--mood {playful,trust,bold,editorial,technical}`: enable mood checks.
- `--baseline PATH` / `--write-baseline`: filter known issues against `.uitools-baseline.json` (or custom path), or write current issues to the baseline file.
- `--show-suppressed`: list suppressed issues with their ignore reasons.

### Color & Tailwind v4 support

`uicolor.py` resolves hex, named CSS colors, `rgb()`/`rgba()`, `hsl()`/`hsla()`, `oklch()`, `oklab()`, `color-mix()` (including `in oklab|oklch|srgb|srgb-linear`), `var(--token)` references, inline `tailwind.config`, Tailwind v3 palette, Tailwind v4 `TW4` OKLCH palette, and `@theme { --color-*: ... }` blocks. Translucent layers (`bg-white/10`) are composited over ancestors; gradients (`bg-gradient-*`, `bg-linear-to-*`) are checked against every color stop; contrast fixes suggest the nearest passing shade of the **same hue**.

### Static rules

- **Core:** spacing (`grid`), text/background contrast (`wcag-aa`), single solid primary button per section/card (`single-primary-cta`), primary CTAs `< 40px` (`fitts-primary`), `nested-radius`, `frame-wrapper`, `miller-7`, `line-length`, `max-2-fonts`, `skeleton-empty`, `reveal-needs-js`, `landmark-main`.
- **Sterility & mood:** `stock-look`, `grey-chart`, `border-heavy`, `flat-hierarchy`; `playful|bold|trust` (`low-color`, `no-hero-surface`); `playful` (`no-drawn-mascot`, `card-sameness`); `bold` (`bold-headline-size`, `bold-font-default`); `editorial` (`headline-measure`, `left-stacked-column`, `edge-align`, `width-funnel`, `editorial-leading`, `no-serif`); `technical` (`radius-too-soft`, `no-mono`, `shadow-heavy`). In `playful`/`bold` (`EXPRESSIVE`), style rules downgrade to `INFO`; accessibility, `line-length`, and `reveal-needs-js` stay at full severity.
- **Locale, typography, shadcn & complexity rules:**
  - `tr-uppercase` (`WARN`): uppercase transform with Turkish characters (`ğüşiöçİĞÜŞÖÇ`) without `lang="tr"` on root/ancestor.
  - `numeric-columns` (`INFO`): numeric table cells or KPI values without `tabular-nums`.
  - `heading-wrap` (`INFO`): headings without `text-balance` or long paragraphs without `text-pretty`.
  - `theme-toggle-missing` (`INFO`, `WARN` in `--route` mode): `.dark` tokens or `dark:` classes without a visible theme toggle (`ThemeToggle` / `setTheme` / `useTheme`).
  - `hardcoded-locale-format` (`INFO`): hardcoded currency/percent `.toFixed()` or manual date concatenation instead of `Intl.NumberFormat` / `Intl.DateTimeFormat`.
  - `shadcn-defaults` (`INFO`): uncustomized shadcn/ui default styling signals.
  - `branch-explosion` (`INFO`): >8 conditional class combinations (`cva` / ternary branches); audits first 8 branches.

### Inline suppression (`uitools-ignore`)

Suppress intentional exceptions with a mandatory reason of at least **8 characters** (`<rule> — <reason>`):

- `uitools-ignore: <rule> — <reason>` (inline on the flagged line)
- `uitools-ignore-next-line: <rule> — <reason>` (applies to the following line)
- `uitools-ignore-start: <rule> — <reason>` ... `uitools-ignore-end` (block range)
- `uitools-ignore-file: <rule> — <reason>` (entire file)

Missing/short reasons or unknown rule names emit meta-issues instead of suppressing.

## `render.py` commands, flags & checks

```bash
python scripts/render.py --help
```

### Flags

- `html` / `--url URL`: local HTML file or live HTTP(S) URL.
- `--out OUT` / `--out-dir DIR`: single PNG output (`--out`) or multi-route output directory (`--out-dir`, default `shots`).
- `--routes PATH`: multi-route `routes.json` matrix (`route x state x viewport`).
- `--viewports VP [VP ...]`: presets (`desktop`, `laptop`, `tablet`, `mobile`, `mobile-375`) or `WxH` (space or comma separated).
- `--states ST [ST ...]`: built-in states (`loading`, `long-loading`, `error`, `empty`, `partial`, `offline`, `locked`) plus `default` and custom `state_mocks` (space or comma separated).
- `--dark`, `--width`, `--height`: theme and viewport overrides for single-target renders.
- `--storage-state PATH`, `--save-storage-state PATH`, `--login-script PATH` (`def login(page, base_url): ...`): session auth support. Never commit `auth.json` / storage state files.
- `--wait-for SELECTOR`: wait for selector visibility after hydration/DOM stability.
- `--check`: run DOM, layout, accessibility (`axe-core`), console, focus, interaction, and 375px mobile checks.
- `--motion` / `--motion-trigger SELECTOR`: run motion & animation audit (including `prefers-reduced-motion: reduce` pass) and capture filmstrip frames.
- `--format text|json`: output format (default `text`).
- `--fail-on none|fail|warn`: exit code `1` when findings reach threshold (default `none`).

### DOM & mobile checks (`--check`)

- **Existing:** `page-overflow-x` (`WARN`), `clipped-content` (`WARN`), `invisible-content` (`WARN`), `blank-band` (`WARN`), `empty-panel` (`WARN`), `empty-column` (`WARN`), `overlapping-labels` (`WARN`), `hollow-text` (`WARN`), `desktop-tiny-text` (`WARN`), `empty-control` (`WARN`), `edge-clipped-art` (`INFO`), `axe-core` serious/critical (`WARN`), `js-errors` (`WARN`), `no-focus-ring` (`WARN`), `dead-buttons` (`INFO`), and 375px mobile (`mobile-overflow-x`, `mobile-tiny-text` = `WARN`; `mobile-tap-targets` = `INFO`).
- **New DOM checks:**
  - `tr-uppercase-render` (`WARN`): uppercase Turkish text without `lang="tr"`.
  - `theme-toggle-missing` (`WARN`): dark theme styles defined without a visible theme toggle control.
  - `numeric-alignment` (`INFO`): numeric table columns lacking `font-variant-numeric: tabular-nums`.
  - `long-wait-unexplained` (`WARN`): `long-loading` state showing only a bare spinner/short text without progress, stage/step, or cancel/notify control.

### Motion checks (`--motion`)

- `motion-layout-property` (`WARN`): animating/transitioning layout properties (`width`, `height`, `top`, `left`, etc.) instead of `transform`/`opacity`.
- `reduced-motion-ignored` (`WARN`): spatial motion transitions/animations exceeding `150ms` under `prefers-reduced-motion: reduce`.
- `layout-shift` (`WARN`): Cumulative Layout Shift (`CLS > 0.1`).
- `slow-feedback` (`WARN`): interactive trigger taking `> 100ms` for DOM/visual feedback or `> 200ms` next animation frame (INP).
- `long-ui-transition` (`INFO`): UI feedback transition/animation exceeding `500ms`.
- `infinite-motion` (`INFO`): infinite non-loading animation lacking a pause control.

## `routes.json` schema summary

Top-level keys:
- `base_url` (required string): HTTP(S) URL, `file://` URI, or local HTML/directory path.
- `auth` (optional object): `{ "storage_state": "...", "login_script": "...", "save_storage_state": "..." }`.
- `viewports` (optional list): viewport presets or `WxH`.
- `states` (optional list): state names (e.g. `["default", "empty", "loading", "long-loading", "error"]`).
- `api_pattern` (optional string/list): Playwright route pattern for state mocking (e.g. `"**/api/**"`).
- `state_mocks` (optional object): custom mock specs keyed by state name.
- `long_loading_frames_ms` (optional list of ints): filmstrip capture timestamps in ms.
- `routes` (required non-empty list): each item has `name` (unique, no `/` or `\`), `path` (or `url`), and optional `wait_for`, `states`, `viewports`, `actions`, `api_pattern`, `state_mocks`, `long_loading_frames_ms`.
