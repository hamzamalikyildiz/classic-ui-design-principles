---
name: classic-ui-design-principles
description: Use when designing, building or refactoring any UI (components, pages, dashboards, landing pages, forms, mobile screens). Picks a mood profile for the audience, selects the matching design rules (60-30-10, WCAG AA, 8pt grid, modular type scale, depth, Fitts/Hick/Jakob/Miller, single primary CTA, skeleton/empty states), applies them as concrete CSS/Tailwind values, then verifies with an audit script and a rendered screenshot.
---

# Classic UI Design Principles

Turn vague adjectives ("modern", "clean", "fun") into measurable decisions. The rules are guardrails, not the design: remove errors without removing character. A page with zero audit findings that looks grey, flat and boxed-in has failed.

Flow: detect context, pick a mood, select rules, generate tokens, build, audit, render, review, fix.

## 1. Detect context

Inspect the files and the request before asking anything:

- **Stack:** `tailwindcss` in `package.json`/config → Tailwind classes. shadcn/ui present (`components.json`, `@/components/ui`) → semantic tokens instead of raw colors: `bg-background`, `bg-card`/`bg-muted`, `bg-primary`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-destructive`; button variants `default`/`outline`/`ghost`. React/Vue/Svelte → keep the component structure. None → CSS custom properties on `:root`. Never break existing tokens or fonts; build on them.
- **Mode:** New UI, or improving an existing one? When improving, run the audit and render it first (section 6), then fix. Keep what already works: its colors, illustrations, personality.
- **Audience and brand:** Who is it for and what should it feel like? This picks the mood (section 2).
- **Page type:** One row from the matrix (section 3); several for mixed pages; component rows for a single component.
- **Plan statement:** Before writing code, output one line:
  `Type: Dashboard | Mood: Trust | Stack: Tailwind CDN | Rules: F-pattern, bento, hero surface, skeleton/empty/error, minor-third, accent indigo-600, categorical chart palette`

## 2. Mood profiles

The mood sets the dose of color, depth, shape and decoration. The rules in section 4 apply to every mood; only the dose changes. If the brand or user names a style, follow it and pick the closest profile.

| | Playful | Trust | Bold | Editorial | Technical |
|---|---|---|---|---|---|
| For | kids, games, consumer, community | finance, health, B2B SaaS, admin | marketing, launches, portfolios | blogs, docs, news | dev tools, data, terminals |
| Palette | accent + 2–3 supporting hues, tinted surfaces | 1 accent + neutrals, semantic colors | accent family + 1 contrast hue | neutrals + 1 link/accent | neutrals + 1 accent, dark-first |
| Hero surface | gradient or saturated stage | one accent card/band per screen | full-bleed gradient or dark band | large type, image | dark panel, code block |
| Depth | `shadow-md`/`shadow-lg`, soft colored shadows ok | `shadow-sm`, bg shift | `shadow-lg`, layered | hairline rules, little shadow | 1px borders, no shadow |
| Card radius | 24px (`rounded-3xl`) | 12–16px (`rounded-xl`/`2xl`) | 16–24px | 4–8px | 6–8px |
| Control radius | full / 16px | 8px | 12px / full | 4px | 6px |
| Type | rounded display font + sans body, 1.25–1.333 | one sans, 1.2 | display + sans, 1.333–1.5 | serif display + sans/serif body, 1.25 | sans + mono details, 1.2 |
| Decoration | illustration, mascot, emoji as icons, playful motion | icons, small charts, restrained motion | big imagery, motion on scroll | photos, pull quotes | mono labels, grids |
| Section spacing (landing) | `py-16 lg:py-20` | `py-20` | `py-24 lg:py-32` | `py-16` | `py-16` |

Every mood respects `prefers-reduced-motion`.

## 3. Page-type matrix

Always-on baseline: WCAG AA, 8pt grid, semantic colors, max 2 fonts, modular scale, one hero surface per screen, single primary CTA, depth over borders, Jakob, proximity.

| Page type | Additional rules | Default mood | Layout |
|---|---|---|---|
| Landing / marketing | Z-pattern, Fitts (large hero CTA), bento features, focal visual in hero | Bold (Playful for kids/consumer) | Full-width sections, spacing from mood |
| Dashboard / admin | F-pattern, bento metrics with one featured card, Miller (sidebar ≤7), skeleton/empty/error, categorical chart colors | Trust | Left sidebar + 12-col grid, `gap-4`/`gap-6` |
| Form / onboarding / checkout | Hick (steps), progressive disclosure, Fitts (full-width submit on mobile), inline errors in semantic red | Trust | Single column, `max-w-md`/`max-w-lg` |
| Content / blog / docs | 45–75 chars (`max-w-prose`), F-pattern, accent for links only | Editorial | Single centered column |
| Mobile app screen | Fitts (44–48px targets, CTA in bottom zone), Miller (tab bar ≤5), skeleton | brand's | Single column, 16px side padding |
| E-commerce / catalog | Hick (grouped filters), skeleton grid, empty state, one CTA per card | Bold or Trust | Responsive card grid |
| Settings / profile | Proximity (grouped sections, whitespace over dividers), Jakob, Miller | Trust | Side menu + content |
| Component: nav / menu | Jakob, Miller (5–7 items), accent active state | page's | Top bar or left sidebar |
| Component: card / modal / dialog | Nested radius, proximity, single primary CTA (bottom-right, ghost cancel to its left) | page's | `p-4`/`p-6`, modal `max-w-md`–`max-w-lg` |

The user's explicit request wins over the matrix. Keep every requested item; when a request collides with a rule (10 menu items vs. Miller, three buttons vs. single CTA), satisfy the rule through presentation (grouping, "More" menus, outline/ghost variants) and say so in the report. Report any other deliberate deviation with its reason.

## 4. Rule reference

**Color**
- 60-30-10 is about **area**, not the number of hues: ~60% neutral background, ~30% surfaces, ~10% accent. In Playful/Bold the 10% can be an accent family or a gradient.
- **One hero surface per screen.** The most important element gets the strongest treatment: a saturated or gradient card, a colored stage behind the illustration, a CTA band. A featured metric that is only bigger, but the same color as its neighbors, is not featured.
- WCAG AA: body text ≥4.5:1; text ≥24px (or ≥18.66px bold), UI borders and icons ≥3:1. Measure with `contrast`.
- **Keep the hue, fix the shade.** When a colored pair fails, darken the text within the same hue (`bg-pink-100 text-pink-800`, `bg-amber-100 text-amber-900`); never fix contrast by switching to grey. `contrast` suggests a same-hue fix.
- Text on a gradient must pass against **both** end colors.
- Semantic: error=red-600, success=green-600, warning=amber-500 (dark text on it), info=blue-600. If the accent collides with one, pick another hue. Never convey state by color alone.
- **Charts use a categorical palette**: accent + 3–4 hues that differ in hue and lightness (e.g. indigo-500, emerald-500, amber-500, rose-500, sky-500), plus labels or a legend. Never encode categories in shades of grey.
- With dark mode, both themes must pass.

**Depth & surfaces**
- Elevation levels: page → surface (cards: background shift + `shadow-sm`) → raised (featured card, popover: `shadow-md`/`shadow-lg`) → overlay (modal).
- In dark mode shadows barely show: express elevation with lighter surfaces (`slate-950` page → `slate-900` card → `slate-800` raised) and a subtle `border-white/10` where needed.
- Borders are for inputs, table rows, dividers, outline buttons, and cards whose background equals the page background. Do not stack border + shadow + frame on the same card.
- **No frame wrappers.** Do not wrap content in an outer `rounded-3xl p-4` box just to hold an inner rounded box. One card, one surface.

**Layout & spacing**
- 8pt grid: margin, padding, gap and sizes in multiples of 8 (Tailwind 2, 4, 6, 8, 10, 12, 16, 20, 24…); 4px steps (1, 3, 5) for fine-tuning. No arbitrary values like `p-[13px]`; round with `snap`.
- Proximity: spacing within a group < half the spacing between groups (`gap-2` inside, `gap-8` between). Separate with whitespace first, background shift second, borders last.
- Section rhythm comes from the mood. Content-light pages get less vertical space, not more.
- Nested radius: where an element already sits inside a rounded container and the padding is smaller than the outer radius, `inner = outer - padding` (`radius` command). With padding ≥ outer radius the inner radius is free; use the mood's control radius. Never add nesting to satisfy the rule.
- Z-pattern: logo top-left, nav/CTA top-right, hero copy left, focal visual right, hero CTA under the copy.
- F-pattern: left-aligned, key info in the top row and left column, scannable headings.
- Bento: 12 or 4/6-col grid, cards 1x1/2x1/2x2, same radius, padding and gap. The featured item is the largest **and** the hero surface. If small cards would stretch to the featured card's height with empty space, stack them (`grid-rows-*`) or fill them (sparkline, progress bar).

**Typography**
- Modular scale: `scale --ratio <ratio>` output. Do not shrink Tailwind's small sizes: `xs` ≥12px, `sm` ≥14px (the script enforces this). Body 16px; heading line-height 1.1–1.25, body 1.5.
- Hierarchy uses three channels: **size, weight, color**. Body 400, labels 500, headings 600–700, muted text one shade lighter. If most text is the same size and bold, there is no hierarchy.
- Line length: paragraphs capped with `max-w-prose` or `max-width: 65ch`.
- Max 2 fonts (a display font for headings counts as one).

**UX laws**
- Fitts: primary CTAs and touch-first UI ≥44×44px (`h-11`+; hero CTA `h-12`–`h-14`). Desktop secondary controls, toolbars, segmented controls and tabs: 32–40px (`h-8`–`h-10`), never below 24px. Destructive actions away from the primary.
- Hick: ≤7 options per menu; long forms in steps; advanced options behind "More".
- Jakob: logo top-left, profile/actions top-right, left sidebar in apps, search at top, links in footer, standard icons.
- Miller: 5–7 items per nav, tab or card group; overflow into groups or a "More" menu.
- Single primary CTA: one solid button per screen/card/form; the rest outline or ghost.
- Skeleton & empty states: every async list/card gets an `animate-pulse` skeleton matching real content size, an empty state (icon + short text + one action) and an error state.
- Every interactive element has hover, focus-visible (accent ring), active and disabled states.
- Decorative emoji, illustrations and mascots get `aria-hidden="true"`; interactive ones get an `aria-label`.

**Anti-patterns**

Too sloppy: rainbow buttons, several solid CTAs side by side, light grey body text, more than 2 fonts, 8+ nav links, tiny 10–12px body copy, gradient text everywhere, emoji in every label.

Too sterile: contrast fixed by turning colored text grey, grey-only charts, a featured card without a hero surface, frame wrappers, borders on every card, everything `text-base font-bold`, every control 44px tall, huge section padding on light content, stretched empty cards, the illustration shrunk into a pale box.

## 5. Tooling

`scripts/uitools.py` and `scripts/render.py` (Python 3), run from the skill directory:

```bash
python3 scripts/uitools.py contrast pink-400 pink-100              # ratio, AA verdict, same-hue fix
python3 scripts/uitools.py scale --base 16 --ratio major-third      # CSS vars + Tailwind fontSize (xs>=12, sm>=14)
python3 scripts/uitools.py radius 24 8                              # inner radius
python3 scripts/uitools.py snap 13 22 --grid 8                      # round to grid
python3 scripts/uitools.py audit page.html --mood playful           # rule violations, exit 1 on FAIL
python3 scripts/uitools.py audit src/App.tsx --css app/globals.css --mood trust
python3 scripts/render.py page.html --out shot.png [--dark] [--width 1440]
```

`audit` checks per element: spacing off the 4px grid (WARN) or off the 8px grid (INFO); text/background contrast against the composited background (translucent layers like `bg-white/10` are blended over their ancestors; Tailwind v3 palette, arbitrary hex, `dark:` pairs, shadcn HSL tokens for `:root` and `.dark` via `--css`; gradients and unknown backgrounds are skipped) with same-hue fix suggestions; solid buttons per section/card; primary CTAs below 40px; nested radius; frame wrappers; nav link count; long paragraphs without a readable max-width; more than 2 fonts; lists without skeleton/empty states. Sterility checks: grey-only charts, borders on most cards with no shadows, flat type hierarchy; with `--mood playful|bold|trust` no hero surface, and with `playful|bold` fewer than 3 hues. The audit cannot see layout results (stretched cards, empty areas, what the eye lands on); the screenshot review covers those.

`render.py` takes a full-page screenshot with headless Chrome/Chromium (Playwright). If the page uses the Tailwind CDN and the network is blocked, it compiles Tailwind locally with `npx tailwindcss@3`, including the page's inline `tailwind.config`, and inlines Google Fonts from `@fontsource` packages.

## 6. Build & verify

1. Pick the mood and write the plan statement.
2. Define the palette for the mood (neutral + surface + accent + supporting hues + semantic + chart palette); check every text/background pair with `contrast`.
3. Generate the type scale with `scale`; choose radius and shadow levels from the mood.
4. Define tokens in one place (Tailwind `theme.extend` or `:root`); components use tokens only.
5. Build the UI. Give each screen its hero surface and focal visual first, then the supporting content.
6. Run `audit --mood <mood>` on every created or changed file. Fix until FAIL=0; fix WARNs or justify them; review INFOs, especially sterility checks.
7. Render with `render.py` (light and dark if both exist) and look at the screenshot. If rendering is impossible (no Playwright/Chrome), say so in the report instead of skipping silently. First-glance test:
   - Where does the eye land first? It should be the hero surface or primary CTA.
   - Does it feel like the mood? Would the audience recognize it as theirs?
   - Is any area empty, stretched, or boxed-in without reason?
   - Is the type hierarchy visible from across the room (squint test)?
   - Did any requested element lose its emphasis or color?
8. Pre-delivery checklist:
   - [ ] One hero surface per screen; the featured item is visually featured
   - [ ] Colored pairs fixed by shade, not by grey; charts use distinct hues
   - [ ] No frame wrappers; borders only where they separate same-colored surfaces
   - [ ] 4/8px grid; section spacing matches the mood
   - [ ] One solid primary button per screen/card/form; primary ≥44px, secondary controls 32–40px
   - [ ] Loading, empty and error states present
   - [ ] All text/background pairs pass AA (dark mode and gradient stops included)
   - [ ] ≤2 fonts; sizes from the scale; body regular, headings bold
   - [ ] Paragraphs 45–75 characters wide
   - [ ] Hover/focus-visible/disabled states; `prefers-reduced-motion` respected

## 7. Report

End with a short list:
- Page type, mood and stack
- Applied rules with concrete values (scale ratio, palette, radius, shadow, spacing)
- Audit result (FAIL/WARN/INFO counts) and deliberate exceptions
- Screenshot path and the first-glance verdict
