---
name: classic-ui-design-principles
description: Use when designing, building or refactoring any UI (components, pages, dashboards, landing pages, forms, mobile screens). Detects the page type and stack, selects the matching design rules (60-30-10, WCAG AA, 8pt grid, modular type scale, Fitts/Hick/Jakob/Miller, single primary CTA, skeleton/empty states), applies them as concrete CSS/Tailwind values and verifies the result with a bundled audit script.
---

# Classic UI Design Principles

Turn vague adjectives ("modern", "clean") into measurable rules. Flow: detect context, select rules, generate tokens, build, audit, fix.

## 1. Detect context

Inspect the files and the request before asking anything:

- **Stack:** `tailwindcss` in `package.json`/config → use Tailwind classes. shadcn/ui present (`components.json`, `@/components/ui`) → use semantic tokens instead of raw colors: `bg-background`, `bg-card`/`bg-muted`, `bg-primary`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-destructive`; button variants `default`/`outline`/`ghost`. React/Vue/Svelte → keep the existing component structure. None → CSS custom properties on `:root`. Never break existing design tokens or fonts; build on them.
- **Mode:** New UI, or improving an existing one? When improving, run the audit first (section 5), then fix.
- **Page type:** Pick one row from the matrix (several for mixed pages; component rows for a single component).
- **Plan statement:** Before writing code, output one line: `Type: Dashboard | Stack: Next.js + Tailwind + shadcn | Rules: F-pattern, bento, skeleton, empty state, minor-third scale, accent indigo-600`.

## 2. Rule selection matrix

Always-on baseline: WCAG AA, 8pt grid, semantic colors, max 2 fonts, modular scale, single primary CTA, Jakob's law, law of proximity.

| Page type | Additional rules | Scale ratio | Layout |
|---|---|---|---|
| Landing / marketing | Z-pattern, Fitts (large hero CTA), 60-30-10 with strong accent, bento (features) | 1.333 perfect-fourth | Full-width sections, `py-24`/`py-32` rhythm |
| Dashboard / admin | F-pattern, bento (metric cards), Miller (sidebar ≤7), skeleton, empty state, nested radius | 1.2 minor-third | Left sidebar + 12-col grid, dense `gap-4`/`gap-6` |
| Form / onboarding / checkout | Hick (split into steps), progressive disclosure, Fitts (full-width submit on mobile), inline errors in semantic red | 1.2 minor-third | Single column, `max-w-md`/`max-w-lg` |
| Content / blog / docs | 45–75 chars (`max-w-prose`), F-pattern, neutral-heavy 60-30-10 (accent for links only) | 1.25 major-third | Single centered column |
| Mobile app screen | Fitts (44–48px touch targets, CTA in bottom zone), Miller (tab bar ≤5), skeleton | 1.2 minor-third | Single column, 16px side padding |
| E-commerce / catalog / list | Hick (grouped filters), skeleton grid, empty state, one CTA per card | 1.25 major-third | Responsive card grid |
| Settings / profile | Proximity (grouped sections, whitespace over dividers), Jakob, Miller | 1.2 minor-third | Side menu + content |
| Component: nav / menu | Jakob, Miller (5–7 items), Fitts (≥44px targets), accent active state | page's | Top bar or left vertical sidebar |
| Component: card / modal / dialog | Nested radius, proximity, single primary CTA (bottom-right, ghost cancel to its left) | page's | `p-4`/`p-6`, modal `max-w-md`–`max-w-lg` |

The user's explicit request wins over the matrix. Report any deliberate deviation with its reason.

## 3. Rule reference

**Color**
- 60-30-10: 60% neutral background (`bg-white`/`bg-slate-950`), 30% surfaces/cards (`bg-slate-50`/`bg-slate-900`, borders `slate-200`/`slate-800`), 10% accent only for primary CTA, active state, links, focus ring. Never spread accent over large areas.
- WCAG AA: body text ≥4.5:1; text ≥24px (or ≥18.66px bold), UI borders and icons ≥3:1. Measure every text/background pair with `contrast`; replace failing colors with the suggested fix.
- Semantic: error=red-600, success=green-600, warning=amber-500 (dark text on it), info=blue-600. If the brand accent collides with one of these, pick another hue (indigo/violet/teal). Never convey state by color alone; add an icon or text.
- With dark mode, both themes must pass.

**Layout & spacing**
- 8pt grid: margin, padding, gap and sizes are multiples of 8 (Tailwind 2, 4, 6, 8, 10, 12, 16, 20, 24…); 4px steps (Tailwind 1, 3, 5) allowed for fine-tuning. No arbitrary values like `p-[13px]`; round with `snap`.
- Proximity: spacing within a group < half the spacing between groups (e.g. `gap-2` inside, `gap-8` between). Separate with whitespace first, background shift second, borders last.
- Nested radius: `inner = outer - padding` (`radius` command). E.g. `rounded-3xl` (24) + `p-2` (8) → inner `rounded-2xl` (16). If ≤0, inner is square or 2–4px.
- Z-pattern: logo top-left, nav/CTA top-right, hero copy left, hero CTA bottom-left/center; alternate sections left/right.
- F-pattern: left-aligned content, key info in the top row and left column, scannable headings.
- Bento: 12 or 4/6-col grid, cards sized 1x1, 2x1, 2x2 via `col-span-*`/`row-span-*`, identical radius, padding and gap on all cards; most important item in the largest card.

**Typography**
- Modular scale: use `scale --ratio <ratio>` output only; no off-scale font sizes. Body 16px (never smaller on mobile), heading line-height 1.1–1.25, body 1.5.
- Line length: paragraphs capped with `max-w-prose` or `max-width: 65ch`.
- Max 2 fonts: one display + one body, or one family with weights 400/500/600/700. Default to a single sans (Inter, Geist, system-ui).

**UX laws**
- Fitts: primary CTA is the largest clickable target, ≥44×44px (Tailwind `h-11`; `h-10` is only 40px), placed in the gaze/thumb zone. Destructive actions far from the primary one.
- Hick: ≤7 options per menu; long forms split into steps; advanced options behind "More".
- Jakob: logo top-left, profile/actions top-right, left vertical sidebar in apps, search at top, links in footer, standard icons.
- Miller: 5–7 items per nav, tab or card group; overflow goes into groups or a "More" menu.
- Single primary CTA: one solid button per screen/card/form; the rest outline or ghost.
- Skeleton & empty states: every async list/card gets an `animate-pulse` skeleton matching real content size, an empty state (icon + short text + one action) and an error state.
- Every interactive element has hover, focus-visible (accent ring), active and disabled states.

## 4. Tooling

`scripts/uitools.py` (Python 3, stdlib only), run from the skill directory:

```bash
python3 scripts/uitools.py contrast slate-500 white              # hex or Tailwind names; ratio, AA verdict, fixed color
python3 scripts/uitools.py scale --base 16 --ratio major-third    # CSS vars + Tailwind fontSize
python3 scripts/uitools.py radius 24 8                            # inner radius
python3 scripts/uitools.py snap 13 22 --grid 8                    # round to grid
python3 scripts/uitools.py audit src/App.tsx --css app/globals.css  # rule violations, exit 1 on FAIL
```

`audit` checks per element: spacing off the 4px grid (WARN) or off the 8px grid (INFO), text/background contrast with the background inherited from the nearest ancestor (Tailwind v3 palette, arbitrary hex, shadcn HSL tokens via `--css`, `dark:` pairs), solid buttons per section/card (raw buttons, `bg-primary`, shadcn `<Button>` default/destructive), nav link count, long paragraphs without a readable max-width on themselves or an ancestor, more than 2 fonts (CSS, Google Fonts, `next/font`) and lists without skeleton/empty states.

## 5. Build & verify

1. Define the palette (neutral + surface + accent + semantic) for the page type; check every text/background pair with `contrast`.
2. Generate the type scale with `scale` and nested radii with `radius`.
3. Define tokens in one place (Tailwind `theme.extend` or `:root`); components use tokens only.
4. Build the UI.
5. Run `audit` on every created or changed file. Fix until FAIL=0; fix WARNs or justify them; review INFOs.
6. Manually check what the audit can't measure: 60-30-10 balance, Z/F flow, focus states, responsive breakpoints, contrast of colors the audit can't resolve (Tailwind v4 oklch, custom theme colors, CSS variables set at runtime); measure those with `contrast`.
7. If a browser/preview is available, take a screenshot and review the hierarchy.
8. Pre-delivery checklist:
   - [ ] No arbitrary px values (`13px`, `19px`); 4/8px grid respected
   - [ ] One solid primary button per screen/card/form
   - [ ] Inner radii follow `outer - padding`
   - [ ] Loading (skeleton), empty and error states present
   - [ ] All text/background pairs pass AA (dark mode included)
   - [ ] ≤2 fonts; all font sizes from the scale
   - [ ] Paragraphs 45–75 characters wide
   - [ ] Hover/focus-visible/disabled states on interactive elements

## 6. Report

End with a short list:
- Detected page type and stack
- Applied rules with concrete values (scale ratio, accent color, grid)
- Audit result (FAIL/WARN counts) and deliberate exceptions
