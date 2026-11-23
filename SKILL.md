---
name: classic-ui-design-principles
description: Use when designing, building, or refactoring UI (components, pages, dashboards, forms, apps). Picks mode (Component/Page/App) & mood, applies classic rules (60-30-10, WCAG AA, 8pt grid, type scale, depth, Fitts/Hick/Jakob/Miller, single primary CTA), 9-state coverage, motion, and typography/locale, then verifies with audit & render checks.
---

# Classic UI Design Principles

Turn vague adjectives ("modern", "clean", "fun") into measurable decisions. Rules prevent errors, not character: a zero-finding page that looks grey, flat, or generic has failed.

`Flow: detect context -> pick MODE (Component / Page / App) -> pick mood -> plan -> (App: screen inventory + foundation) -> build -> states -> motion -> audit -> render & check -> fix -> report.`

| Mode | Scope | Read & Apply | Output |
|---|---|---|---|
| **Component** | Single component or small tweak (button, modal, field, card) | Fast path: skip mood, `reference/visual-quality.md`, signature; apply `reference/rules.md` + `uitools.py audit` | Audited component + fix summary |
| **Page** | Single screen, landing, article, or standalone dashboard | Mood file + `reference/visual-quality.md` + `reference/page-types.md` + relevant `reference/states.md` + 1–2 `reference/motion.md` moments | Screenshot + `--check` + mini state table + motion note |
| **App** | Multi-screen (≥2 routes, auth, CRUD, dashboard + detail) | `reference/app-flow.md` first: P0/P1/P2 inventory -> foundation (`reference/shadcn-baseline.md` if shadcn) + realistic seed (`reference/sample-data.md`) -> screen loop (`reference/states.md`, `reference/motion.md`, `reference/typography-locale.md`) | Coverage note + states per P0 screen |

## 1. Detect context

- **Stack:** Tailwind (`package.json`/config/CDN), shadcn/ui (`components.json`; semantic tokens `bg-background`, `text-muted-foreground`, `border-border`), React/Vue/Svelte, or CSS (`:root`). Keep existing tokens/fonts.
- **shadcn/ui baseline:** Before building screens, apply `reference/shadcn-baseline.md` once in `components/ui/` and `globals.css` (`oklch` tokens supported by `uitools.py`).
- **Existing vs new:** When improving existing UI, run `audit` and `render.py --check` first, then fix; keep what already works (colors, illustrations, personality).
- **Audience & page type:** Pick the mood below; `reference/page-types.md` maps unusual briefs onto the five moods.
- **Plan statement** before code, one line: `Mode: Page | Type: Dashboard | Mood: Trust | Stack: Next + shadcn | Concept: ... | Signature: ...`

## 2. Mood profiles (read `moods/expressive.md` for Playful/Bold, or `moods/<mood>.md` for Trust/Editorial/Technical)

| | Playful | Trust | Bold | Editorial | Technical |
|---|---|---|---|---|---|
| For | kids, games, consumer | finance, health, B2B, admin | marketing, launches | blogs, docs, news | dev tools, data |
| Palette | accent + 2-3 hues, tinted surfaces | 1 accent + neutrals, semantic | accent family + 1 contrast hue | neutrals + 1 accent | neutrals + 1 accent, dark-first |
| Hero surface | saturated stage | one accent card/band | full-bleed gradient or dark band | large type, optional diagram | dark panel, code block |
| Depth | `shadow-md/lg`, colored shadows ok | `shadow-sm`, bg shift | `shadow-lg`, layered | hairlines | 1px borders |
| Card / control radius | 24px / full | 12-16 / 8 | 16-24 / 12 | 4-8 / 4 | 6-8 / 6 |
| Type | rounded display + sans, 1.25-1.333 | serif display + sans (or clean sans), 1.2 | display + sans, 1.333-1.5 | serif display + body, 1.25 | sans + mono, 1.2 |
| Landing section spacing | `py-16 lg:py-20` | `py-20` | `py-24 lg:py-32` | `py-16` | `py-16` |

Playful and Bold are **expressive**: the audit enforces only the accessibility floor and turns style rules into INFO, so spend effort on character (`moods/expressive.md`). Dark mode is a theme, not a mood; every mood respects `prefers-reduced-motion`.

## 3. Floor, defaults and ideas

Rules come in three strengths. Only the floor is non-negotiable; spending effort on a default that does not fit the brief usually makes the page worse.

**Floor (always; `audit` keeps these at FAIL/WARN):**
1. AA contrast (4.5:1 body, 3:1 large text/UI), including gradients, `oklch` tokens and both themes; fix a failing colored pair by shade within the hue, never grey.
2. Visible keyboard focus, reachable controls, accessible names for buttons and links.
3. `prefers-reduced-motion` honored; no animating layout properties (`width`, `height`, `top`, `left`, `margin`, `padding`).
4. Content visible without JavaScript (no static `opacity-0`).
5. Nothing clipped, overflowing or overlapping; no horizontal scroll at 375px.
6. Body text ≥ 12px (readable table/caption/sidebar text ≥ 14px), primary touch targets ≥ 24px.
7. `<main>` and basic landmarks; paragraphs capped around 65ch.
8. Language correctness: `lang`, Turkish casing (`tr-TR`), locale number/date formats (`reference/typography-locale.md`).
9. No placeholder copy (`"Lorem"`, `"Feature one"`).

**Defaults (start here; deviate when the brief or content calls for it, and say so in one line of the report; `audit` reports these as INFO):**
- Color and depth: 60-30-10 by area, one hero surface per screen, depth over borders, nested radius = outer - padding, categorical chart palette, same-hue contrast fixes.
- Layout: 8pt grid (4px fine-tuning), proximity inside groups < between groups, Z-pattern landings, F-pattern dashboards, a featured bento card when it helps.
- Type: modular scale, body 16px, leading 1.5-1.6, ≤ 2 families (3 in expressive), `text-balance` headings, `tabular-nums` for number columns, `Intl` formatting.
- UX: one solid primary CTA per block, primary CTAs ≈ 44px, Hick ≤ 7 options, Miller 5-7 nav items, hover/focus/active/disabled states, skeleton and empty states where data loads.
- States (`reference/states.md`): cover the states the screen really has; most need loading, empty and error, async jobs over 3s need named stages and a cancel.
- Motion (`reference/motion.md`): tokens `80-500ms`, `transform`/`opacity` only, `exit <= 0.7 * enter`.
- Content: realistic seeded data (`reference/sample-data.md`), panels filled with real rows rather than stubs, no filler widgets invented to fill space.
- Palette from the subject, not the default (ember on near-black for audio, sun yellow + sky for kids), supporting hue 60-150° away; inline-SVG icons in one stroke style.

**Ideas (pick what fits, none required; `reference/visual-quality.md`):** a signature element (a drawn product or scene, a small working interaction, or simply strong typography; skip it if it would feel bolted on), one hero entrance and one dealt moment, real product UI instead of boxes, one atmosphere treatment, varied section rhythm, 1-2 result micro-moments (count-up, row flash, Undo toast, sliding tab indicator) with a reduced-motion fallback. `stock-look` in the audit flags an untouched default blue/violet accent.

Anti-patterns: rainbow buttons, several solid CTAs side by side, faint grey text walls, hollow outlined display text, borders on every card, bare `"Loading..."` on long jobs, wiping input on error.

The user's explicit request wins; satisfy colliding rules through presentation (grouping, "More" menus, ghost variants) and note it in the report.

## 4. Tooling (`reference/tooling.md` lists every check)

```bash
python scripts/uitools.py contrast pink-400 pink-100      # ratio, AA verdict, same-hue fix
python scripts/uitools.py scale --base 16 --ratio major-third
python scripts/uitools.py radius 24 8                      # inner radius
python scripts/uitools.py audit page.html --mood playful   # static rules; exit 1 on FAIL
python scripts/uitools.py audit app/cv/page.tsx --css app/globals.css --mood trust
python scripts/uitools.py audit page.html --strict         # keep style suggestions at WARN (CI)
python scripts/render.py page.html --out shot.png --check  # screenshot + rendered checks
python scripts/render.py --url http://localhost:3000/cv --storage-state auth.json --out cv.png --check
python scripts/render.py --routes routes.json --out-dir shots/ --check
```

Suppress intentional exceptions inline: `uitools-ignore: <rule> — <reason>`. `--check` runs headless Chrome for clipped/overflowing content, hidden text, empty buttons, axe violations, JS errors, 375px overflow/tiny text and missing focus rings. Fix FAIL and WARN (the floor); INFO lines are suggestions: decide, and mention the ones you skip.

## 5. Build and verify

1. **Mode, mood, concept & plan statement** (App mode: `reference/app-flow.md` screen inventory first).
2. **Tokens & foundation:** palette (`contrast`, incl. `oklch`), type `scale`, radius/motion tokens in one place (`reference/shadcn-baseline.md` once for shadcn).
3. **Seed & build:** seed realistic data before rendering; build the hero and the main data surface first, then supporting modules per mood focus.
4. **States, motion & locale pass** for what the screens actually do.
5. **Audit & render:** `uitools.py audit --mood <mood>`; if Playwright + Chrome exist, `render.py --check` and look at the screenshot (where the eye lands, empty or stretched areas, squint hierarchy). Fix the floor findings, up to 3 rounds; if rendering is unavailable, say so.

## 6. Report

Keep it short: what was built (mode, mood, stack, concept), the audit and `--check` result, anything on the floor still open, defaults you deliberately skipped (one line each), and screenshot paths. App mode adds a coverage note: which screens were done, which states each has, and what is missing (`reference/app-flow.md`; a table is optional).
