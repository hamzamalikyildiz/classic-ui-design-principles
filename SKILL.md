---
name: classic-ui-design-principles
description: Use when designing, building, or refactoring UI (components, pages, dashboards, forms, apps). Picks mode (Component/Page/App) & mood, applies classic rules (60-30-10, WCAG AA, 8pt grid, type scale, depth, Fitts/Hick/Jakob/Miller, single primary CTA), 9-state coverage, motion, and typography/locale, then verifies with audit & render checks.
---

# Classic UI Design Principles

Turn vague adjectives ("modern", "clean", "fun") into measurable decisions. Rules prevent errors, not character: a zero-finding page that looks grey, flat, or generic has failed.

`Flow: detect context -> pick MODE (Component / Page / App) -> pick mood -> plan -> (App: screen inventory + foundation) -> build -> states -> motion -> audit -> render & check -> fix -> report.`

| Mode | Scope | Read & Apply | Output |
|---|---|---|---|
| **Component** | Single component or small tweak (button, modal, field, card) | Fast path: skip mood/`reference/visual-quality.md`/signature; apply `reference/rules.md` + `uitools.py audit` | Audited component + fix summary |
| **Page** | Single screen, landing, article, standalone dashboard | Mood file + `reference/visual-quality.md` + `reference/page-types.md` + `reference/states.md` + 1–2 `reference/motion.md` moments | Screenshot + `--check` + mini state table + motion note |
| **App** | Multi-screen (≥2 routes, auth, CRUD, dashboard + detail) | `reference/app-flow.md` first: P0/P1/P2 inventory -> foundation (`reference/shadcn-baseline.md` if shadcn) + realistic seed (`reference/sample-data.md`) -> screen loop (`reference/states.md`, `reference/motion.md`, `reference/typography-locale.md`) | Mandatory Coverage Report + 9-state matrix per P0 screen |

## 1. Detect context

- **Stack:** Tailwind (`package.json`/config/CDN), shadcn/ui (`components.json`; semantic tokens `bg-background`, `text-muted-foreground`, `border-border`), React/Vue/Svelte, or CSS (`:root`). Keep existing tokens/fonts.
- **shadcn/ui baseline:** Before screens, apply `reference/shadcn-baseline.md` once in `components/ui/` and `globals.css` (`oklch` tokens supported).
- **Existing vs new:** On existing UI, run `audit` + `render.py --check` first (brownfield apps: `reference/app-flow.md` §6); keep what works (colors, illustrations, personality).
- **Audience & page type:** Pick mood below; `reference/page-types.md` maps unusual briefs onto the 5 moods.
- **Plan statement** before code, one line: `Mode: Page | Type: Dashboard | Mood: Trust | Stack: Next + shadcn | Concept: ... | Signature: ...`

## 2. Mood profiles (read `moods/expressive.md` for Playful/Bold, `moods/<mood>.md` for Trust/Editorial/Technical)

| | Playful | Trust | Bold | Editorial | Technical |
|---|---|---|---|---|---|
| For | kids, games, consumer | finance, health, B2B, admin | marketing, launches | blogs, docs, news | dev tools, data |
| Palette | accent + 2-3 hues, tinted surfaces | 1 accent + neutrals, semantic | accent family + 1 contrast hue | neutrals + 1 accent | neutrals + 1 accent, dark-first |
| Hero surface | saturated stage | one accent card/band | full-bleed gradient or dark band | large type, optional diagram | dark panel, code block |
| Depth | `shadow-md/lg`, colored shadows ok | `shadow-sm`, bg shift | `shadow-lg`, layered | hairlines | 1px borders |
| Card / control radius | 24px / full | 12-16 / 8 | 16-24 / 12 | 4-8 / 4 | 6-8 / 6 |
| Type | rounded display + sans, 1.25-1.333 | serif display + sans (or clean sans), 1.2 | display + sans, 1.333-1.5 | serif display + body, 1.25 | sans + mono, 1.2 |
| Landing section spacing | `py-16 lg:py-20` | `py-20` | `py-24 lg:py-32` | `py-16` | `py-16` |

Playful and Bold are **expressive**: `audit` enforces only the accessibility floor and downgrades style rules to INFO, so invest in character (`moods/expressive.md`). Dark mode is a theme, not a mood; every mood respects `prefers-reduced-motion`.

## 3. Make it memorable (Page & App modes)

1. **One signature element per primary screen**: custom inline-SVG illustration (product, scene, mascot—never geometric placeholders/emoji) or working interaction (mini demo, configurator, sortable table, pausable log). Dashboards favor interaction, landings illustration/live preview, articles strong type (diagrams/interactions only if helpful, never clip-art).
2. **Palette from the subject**, not defaults (audio: ember on near-black; kids learning: sun yellow + sky + coral; observability: cyan on ink). Supporting hue 60–150° away. Violet-to-fuchsia gradient only when requested.
3. **Icons are inline SVG**, one stroke style. Emoji as icons only in Playful.
4. **Realistic copy & seeded data** (`reference/sample-data.md`): real names, numbers, units; no `"Lorem"` or `"Feature one"`. Seed realistic data before `render.py` — never judge screenshots against an empty database.
5. **Visual polish** (`reference/visual-quality.md`): subject-derived palette, display/serif voice, one hero entrance + dealt moment, real product UI over boxes, one atmosphere treatment, varied section rhythm. `audit` flags stock blue/violet accents without custom palette as `stock-look`.
6. **No half-empty stubs or filler widgets:** fill panels with real rows/copy; never invent extra panels/sidebars to fill space; keep content visible without JS (no static `opacity-0`).

## 4. Hard rules, states, motion & typography

Details in `reference/rules.md`, `reference/states.md`, `reference/motion.md`, `reference/typography-locale.md`:

- **Color & depth:** 60-30-10 by area; one hero surface per screen (except pure typographic Editorial); AA contrast (4.5:1 body, 3:1 large/UI) incl. gradients & `oklch`; fix failing colored pairs by shade in the same hue, never grey. Depth over borders (except Technical/Editorial hairlines); no frame wrappers; nested radius = outer - padding.
- **Layout:** 8pt grid (4px fine-tuning), proximity inside groups < between groups, Z-pattern for landings, F-pattern for dashboards/content, bento with one featured card when fitting.
- **Type & locale** (`reference/typography-locale.md`): modular scale, `xs` ≥ 12px for short kickers/tags only, ≥ 14px (`sm`) for table/caption/sidebar text, body 16px, leading 1.5–1.6, paragraphs ≤ 65ch, ≤ 2 families (3 in expressive). Use `text-balance` on headings, `text-pretty` on paragraphs, `opsz`, `tabular-nums`, `Intl` formatting, `lang="tr"` with `uppercase` (no `İ/I` corruption), reachable dark-mode toggle if `.dark` tokens exist.
- **UX & 9-State Matrix** (`reference/states.md`): single solid primary CTA per screen/card/form (≥ 44px; `audit` warns < 40px), Hick/Miller as starting sizes (~5–7 per group, grouped by task and clarity), hover/focus-visible/active/disabled, `aria-hidden` on decoration, `<main>`/`<header>`/`<nav>` landmarks. 9-state coverage: **Empty** (first-use vs filtered), **Loading** (`<1s` none / `1–3s` matching skeleton), **Long-loading (>3s)** (named stages, elapsed + honest estimate, productive fill, Cancel + Notify), **Error** (preserve user input + specific recovery), **Partial**, **Locked**, **Success** (micro-moment), **Offline**, **Stale**.
- **Motion & Micro-Moments** (`reference/motion.md`): tokens (`80–500ms`), `transform`/`opacity`-led (short paint-only exceptions allowed; avoid layout `width`/`height`/`top`/`left` — policy table in `reference/motion.md`), `exit <= 0.7 * enter`. Add 1–2 result micro-moments (score ring count-up, `1.2s` row highlight flash, Undo toast, sliding tab indicator) with zero-travel `prefers-reduced-motion: reduce` fallback.
- **Anti-patterns:** rainbow buttons, multiple solid CTAs, `<14px` body/table text, faint grey walls, hollow outlined display text, all-card borders outside Technical/Editorial, bare `"Loading..."` on `>3s` jobs, wiping input on error.

Explicit user requests win; resolve colliding rules via presentation (grouping, "More" menus, ghost variants) and note in the report.

## 5. Tooling (`reference/tooling.md` lists every check)

Resolve `scripts/` relative to this `SKILL.md` folder (`<skill_dir>/scripts/...`), not the app's CWD; use one-shot `python <skill_dir>/scripts/verify.py` (`audit` + `render --check` in one pass) or run `uitools.py` / `render.py` directly:

```bash
python <skill_dir>/scripts/verify.py page.html --mood playful --out shot.png
python <skill_dir>/scripts/uitools.py contrast pink-400 pink-100 # ratio, AA, same-hue fix
python <skill_dir>/scripts/uitools.py scale --base 16 --ratio major-third
python <skill_dir>/scripts/uitools.py radius 24 8 # inner radius
python <skill_dir>/scripts/uitools.py audit app/cv/page.tsx --css app/globals.css --mood trust --baseline .uitools-baseline.json
python <skill_dir>/scripts/render.py page.html --out shot.png --check # screenshot + DOM checks
python <skill_dir>/scripts/render.py --url http://localhost:3000/cv --storage-state auth.json --out cv.png --check
python <skill_dir>/scripts/render.py --routes routes.json --out-dir shots/ --check
```

Suppress intentional exceptions inline: `uitools-ignore: <rule> — <reason>`. `--check` runs headless Chrome for clipped/overflowing content, blank/half-empty panels, `opacity: 0` text, empty/dead buttons, axe violations, JS errors, 375px mobile overflow/tiny text, and missing focus rings. Fix every WARN.

## 6. Build and verify

1. **Mode, mood, concept & plan statement** (App mode: run `reference/app-flow.md` screen inventory P0/P1/P2 first).
2. **Tokens & foundation:** Palette from subject (`contrast` incl. `oklch`), type `scale`, motion/radius tokens in one place (apply `reference/shadcn-baseline.md` once for shadcn).
3. **Seed & build:** Seed realistic data (`reference/sample-data.md`) before rendering. Build hero + signature element first, then supporting modules per mood focus rule.
4. **States, motion & locale pass:** Wire the 9-state matrix (`reference/states.md`), 1–2 micro-moments (`reference/motion.md`), and typography/locale/theme toggle (`reference/typography-locale.md`).
5. **Audit & render:** Run `verify.py` (or `uitools.py audit --mood <mood>` + `render.py --check` if Playwright + Chrome exist), fix FAIL/WARN without deleting signature art, inspect screenshots (eye landing, mood, empty/stretched areas, squint hierarchy), up to 3 rounds (note if browser unavailable).

## 7. Report

- **Component mode:** modified file(s), applied rule values, `audit` result.
- **Page mode:** type, mood, stack, concept & signature; palette/scale/radius/spacing; `audit` & `--check` results; screenshot path + first-glance verdict; **mini state table + motion note**.
- **App mode:** **Mandatory Coverage Report** (`reference/app-flow.md`) — `Screen | Priority | Done [Redesigned / Styled to match / Untouched] | States covered [n/9] | Motion | Open gaps` — plus **9-state matrix per P0 screen** (`reference/states.md`), cross-screen consistency verdict, `audit`/`--check` summary, screenshot paths.
