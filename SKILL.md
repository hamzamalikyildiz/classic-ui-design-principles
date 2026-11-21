---
name: classic-ui-design-principles
description: Use when designing, building or refactoring any UI (components, pages, dashboards, landing pages, forms, mobile screens). Picks a mood profile for the audience, applies classic rules (60-30-10, WCAG AA, 8pt grid, type scale, depth, Fitts/Hick/Jakob/Miller, single primary CTA, skeleton/empty states) as concrete CSS/Tailwind values, adds a signature element so the page is memorable, then verifies with an audit script and a rendered check.
---

# Classic UI Design Principles

Turn vague adjectives ("modern", "clean", "fun") into measurable decisions. Rules remove errors, they do not create character: a page with zero findings that looks grey, flat and generic has failed.

Flow: detect context, pick mood, read the mood file, plan, build, audit, render and check, fix, report.

**Fast path (single component or small tweak):**
- For a single component (button, modal, form field, card tweak), skip the mood file, `reference/visual-quality.md`, and the signature element.
- Apply AA contrast, 8pt grid, nested radius, and focus/CTA rules (`reference/rules.md`), then run `audit`.

## 1. Detect context

- **Stack:** Tailwind in `package.json`/config or CDN, shadcn/ui (`components.json`; use semantic tokens `bg-background`, `text-muted-foreground`, `border-border`), React/Vue/Svelte, or plain CSS (custom properties on `:root`). Build on existing tokens and fonts, never break them.
- **Mode:** new UI, or improving existing? When improving, run audit and render first, then fix; keep what already works (colors, illustrations, personality).
- **Audience and brand** pick the mood. **Page type** picks layout rules (`reference/page-types.md`, which also maps unusual briefs onto the five moods).
- **Plan statement** before code, one line: `Type: Dashboard | Mood: Trust | Stack: Tailwind CDN | Concept: ... | Signature: ...`

## 2. Mood profiles (read `moods/expressive.md` for Playful/Bold, or `moods/<mood>.md` for Trust/Editorial/Technical before building)

| | Playful | Trust | Bold | Editorial | Technical |
|---|---|---|---|---|---|
| For | kids, games, consumer | finance, health, B2B, admin | marketing, launches | blogs, docs, news | dev tools, data |
| Palette | accent + 2-3 hues, tinted surfaces | 1 accent + neutrals, semantic | accent family + 1 contrast hue | neutrals + 1 accent | neutrals + 1 accent, dark-first |
| Hero surface | saturated stage | one accent card/band | full-bleed gradient or dark band | large type, optional diagram | dark panel, code block |
| Depth | `shadow-md/lg`, colored shadows ok | `shadow-sm`, bg shift | `shadow-lg`, layered | hairlines | 1px borders |
| Card / control radius | 24px / full | 12-16 / 8 | 16-24 / 12 | 4-8 / 4 | 6-8 / 6 |
| Type | rounded display + sans, 1.25-1.333 | serif display + sans (or clean sans), 1.2 | display + sans, 1.333-1.5 | serif display + body, 1.25 | sans + mono, 1.2 |
| Landing section spacing | `py-16 lg:py-20` | `py-20` | `py-24 lg:py-32` | `py-16` | `py-16` |

Playful and Bold are **expressive**: the audit enforces only the accessibility floor and turns style rules into INFO, so spend the effort on character (`moods/expressive.md`). Dark mode is a theme, not a mood. Every mood respects `prefers-reduced-motion`.

## 3. Make it memorable (all moods)

1. **One signature element per page**, built for this brief: a custom inline-SVG illustration (a drawn product, scene or mascot, not geometric placeholders or emoji), or one working interaction in vanilla JS (mini demo, configurator, sortable table, pausable live log). Dashboards favor the interaction, landings an illustration or live preview, and articles strong typography — adding a diagram or interaction only when it genuinely helps the reader (never forced clip-art).
2. **Palette from the subject**, not the default (audio: ember on near-black; kids learning: sun yellow + sky + coral; observability: cyan on ink). Supporting hue 60-150 degrees away. A violet-to-fuchsia gradient only if the brief calls for it.
3. **Icons are inline SVG**, one stroke style. Emoji as icons only in Playful.
4. **Specific copy and data**: real-sounding names, numbers, units; no "Lorem", no "Feature one".
5. **Visual polish** (`reference/visual-quality.md`, read it before building): palette recipe from the subject, a display or serif face with a voice, one hero entrance and one dealt moment, real product UI instead of boxes, one atmosphere treatment, varied section rhythm. Cover the logo: if the page could belong to any company, add specifics. `audit` flags stock blue/violet accents with no custom palette as `stock-look`.
6. **No half-empty stubs, no filler widgets**: populate every panel you include with real rows and copy, and do NOT invent extra panels or sidebars just to fill space; intentional breathing room beats kitchen-sink crowding; keep all content visible without JavaScript (no `opacity-0` start states).

## 4. Hard rules (details and values in `reference/rules.md`; read it when fixing findings or building components)

- Color: 60-30-10 by area; one hero surface per screen (except pure typographic Editorial); AA contrast (4.5:1 body, 3:1 large/UI), measured on gradients too; fix a failing colored pair by shade within the hue, never by grey; charts use a categorical palette with labels.
- Depth over borders (except Technical/Editorial hairlines); no frame wrappers; nested radius = outer - padding.
- Layout: 8pt grid (4px for fine-tuning), proximity inside groups < between groups, Z-pattern for landings, F-pattern for dashboards and content, bento with one featured card (when the brief calls for bento).
- Type: modular scale, `xs` >= 12px for short kickers/tags only, >= 14px (`sm`) for readable table/caption/sidebar text, body 16px, leading 1.5-1.6, paragraphs <= 65ch, <= 2 families (up to 3 in expressive moods).
- UX: single solid primary CTA per screen/card/form (primary >= 44px; `audit` warns below 40px), Hick <= 7 options, Miller 5-7 nav items, skeleton + empty + error states for dynamic/async data, hover/focus-visible/active/disabled, `aria-hidden` on decoration, `<main>`/`<header>`/`<nav>` landmarks.
- Anti-patterns: rainbow buttons, several solid CTAs, tiny <14px body/table text, faint grey walls, hollow outlined display text, borders on every card outside Technical/Editorial, everything bold, stretched empty cards.

The user's explicit request wins; satisfy colliding rules through presentation (grouping, "More" menus, ghost variants) and say so in the report.

## 5. Tooling (`reference/tooling.md` lists every check)

```bash
python3 scripts/uitools.py contrast pink-400 pink-100      # ratio, AA verdict, same-hue fix
python3 scripts/uitools.py scale --base 16 --ratio major-third
python3 scripts/uitools.py radius 24 8                      # inner radius
python3 scripts/uitools.py snap 13 22 --grid 8
python3 scripts/uitools.py audit page.html --mood playful   # static rules; exit 1 on FAIL; reads inline tailwind.config colors
python3 scripts/uitools.py audit src/App.tsx --css app/globals.css --mood trust
python3 scripts/render.py page.html --out shot.png --check  # screenshot + rendered-page checks (add --dark, --width)
```

`--check` runs in headless Chrome and reports clipped text, overflowing code, blank and half-empty panels, hidden content, empty buttons, axe accessibility violations, console errors, 375px mobile overflow and tiny text, buttons that do nothing, missing focus rings. Fix every WARN.

## 6. Build and verify

1. Mood, concept (one line: visual idea + 3 personality words) and plan statement.
2. Palette from the subject; check every text/background pair with `contrast`. Type scale with `scale`. Tokens in one place.
3. Build the hero and signature element first (include a diagram or illustration only when it genuinely serves the brief), then add only the supporting modules the brief calls for (follow the mood file's focus rule, not a fixed widget quota).
4. `audit --mood <mood>` once on the finished file. Fix FAIL/WARN with the smallest edit (a shade, a size, a class); never delete the signature element or illustration to satisfy a check.
5. If Playwright + Chrome are available, run `render.py --check`, fix every WARN, then open the screenshot and ask: where does the eye land (hero surface or primary CTA)? does it feel like the mood? any empty, stretched or boxed-in area? does the squint test show hierarchy? did a requested element lose emphasis? If Playwright/rendering is unavailable and skipped, say so in the report.
6. Repeat 4-5 at most three times; the last round must be clean.

## 7. Report

Short list: page type, mood, stack, concept and signature element; applied values (palette, scale, radius, spacing); audit and `--check` results with deliberate exceptions; screenshot path and the first-glance verdict.
