# Tooling details

When installed as an agent skill (`~/.claude/skills/...` or `~/.gemini/config/skills/...`), resolve `scripts/` relative to `SKILL.md` (`<skill_dir>/scripts/...`), not the target app's working directory. `uitools.py` and `verify.py` run with Python 3 stdlib only (`uicolor.py`, `uiparse.py`, `uiroute.py`, `uiignore.py`); `render.py` (and `verify.py`'s rendered pass) uses Playwright + headless Chromium and `scripts/checks/*.js` (`check.js`, `mobile.js`, `interact.js`, `motion.js`, `sweep.js`).

## `verify.py` (one-shot static + rendered verification)

`verify.py` runs static `uitools.py audit` and rendered `render.py --check` (plus optional `--motion`) in one pass and merges findings into a unified exit code and report:

```bash
python scripts/verify.py --help
python scripts/verify.py page.html --mood trust --out shot.png
python scripts/verify.py --routes routes.json --routes-glob "app/**/page.tsx" --css app/globals.css --motion --format json --fail-on fail
```

- Accepts single HTML/component/route targets or `--url` / `--routes`, forwarding static flags (`--mood`, `--css`, `--route`, `--routes-glob`, `--root`, `--tsconfig`, `--baseline`, `--grid`) to `uitools.py` and render flags (`--out`, `--out-dir`, `--viewports`, `--states`, `--storage-state`, `--wait-for`, `--dark`, `--motion`, `--motion-trigger`, `--require-axe`) to `render.py --check`.
- `--format text|json`: human-readable summary or structured JSON combining static and rendered findings.
- `--fail-on none|fail|warn`: exit `1` when combined findings reach the chosen severity threshold (default `fail`). If Playwright/Chromium is unavailable, `verify.py` still completes the static audit and reports the skipped render check explicitly.

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

## Packaging & CI usage

- `package_skill.py` builds a lightweight distribution zip (`SKILL.md`, `LICENSE`, `moods/`, `reference/`, `scripts/`, excluding `bench/`, `tests/`, `examples/`): `python package_skill.py` writes a `classic-ui-design-principles/`-wrapped archive for `claude.ai`, while `python package_skill.py --flat` writes a root-level `SKILL.md` archive for skill marketplaces such as Agensi.io.
- `render.py --require-axe`: exit 1 when axe-core is missing or errors. Without it a skipped accessibility check is reported as `axe-not-run` / `axe-error` (INFO, with the text "Accessibility was NOT checked") so it is never mistaken for "no findings"; with it the run fails. `--fail-on none|fail|warn` still sets the severity that fails the run; `--require-axe` implies at least `fail`.
- `scripts/e2e_gate.py` compares a `--routes ... --format json` report with a spec. `--expect FILE` (example with deliberate defects): every listed rule must still be caught. `--baseline FILE` (clean example): only the listed rules, up to the listed counts, may appear as WARN/FAIL; FAIL is never allowed. Both modes fail when axe did not run. `.github/workflows/app-e2e.yml` runs both against `examples/app-demo` and `examples/app-demo-polished`.
- Allowed motion properties are listed once, in the property policy table in `reference/motion.md`; `tests/fixtures/motion/pos_allowed_properties.html` checks that the allowed tier passes `--motion`.
