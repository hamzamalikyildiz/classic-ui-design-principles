# App Flow: Multi-Screen Apps

Use when the task covers an app (several routes, a shell, shared components), not one page. Page-level rules stay in `reference/rules.md` and `reference/visual-quality.md`; this file only adds ordering and coverage. Never polish two screens and leave their siblings raw.

## 1. Screen Inventory (extract from the codebase before writing UI)

Scan, do not guess: route files (`app/**/page.tsx`, `pages/**`, router configs such as `routes.tsx` or `App.vue`), navigation menus and tab bars, and every modal, drawer and sheet that holds a workflow. Write the table first and keep it as the work list:

| Screen | Route | Primary user job | Data dependency | Critical states | Priority (P0/P1/P2) |
|---|---|---|---|---|---|
| Dashboard | `/` | See what needs attention today | `GET /api/summary` | loading, empty, error, partial | P0 |

- **Primary user job:** one verb phrase ("compare plans", "review a CV"), not a page title.
- **Data dependency:** endpoint, store or mock the screen reads. No dependency means static, so skeleton and error states are N/A.
- **Critical states:** the subset of `reference/states.md` that can actually occur here.
- **P0:** the core value loop and the screen opened daily (home, main list/detail, primary create flow). **P1:** supporting workflows (search, profile, secondary lists, onboarding). **P2:** settings, billing, admin, legal, rare error pages. When unsure, ask "would the product still make sense without it?"; if yes, it is not P0.

## 2. Foundation Layer First (before individual screens)

1. **Tokens in one source:** `:root` / `.dark` / `@theme` holding color (semantic roles), type scale, 8pt spacing, radius, shadows (elevation levels) and motion tokens (duration, easing per `reference/motion.md`). Screens consume tokens; no per-screen hex or arbitrary values.
2. **Shared primitives:** `Button`, `Input`, `Card`, `Badge`, `Table`, `Dialog`, `Toast`, `Skeleton`, `EmptyState`, `ErrorState`, `ProgressSteps`. Build or restyle these once, with hover, focus-visible, disabled and loading variants. Reuse existing ones; extend, do not fork.
3. **shadcn/ui projects** (`components.json`): apply `reference/shadcn-baseline.md` first, so button height, badge size, card depth and input height already agree with `reference/rules.md` before any screen is designed.
4. **Realistic data:** seed from `reference/sample-data.md` (real-looking names, dates, amounts, long and short values). Screenshots never run against an empty database; empty states are rendered deliberately, not by accident.

## 3. Screen-by-Screen Loop by Priority (P0 → P2)

Work P0 screens first, then P1, then P2. Per screen (or per wave of near-identical screens):

```
plan -> all states (reference/states.md) -> motion moments (reference/motion.md)
     -> uitools.py audit --route <file> -> render.py --routes --motion -> fix
```

- **plan:** one-line plan statement per screen, reusing the app's mood; one signature element for the app's P0 hero, not one per screen.
- **states:** implement every state listed in the inventory row before moving on (default, loading, empty, error, partial, success, disabled, offline, long-content as applicable).
- **motion moments:** only meaningful ones (feedback, state change, entrance of the hero); respect `prefers-reduced-motion`.
- **audit / render:** fix every WARN, then look at the screenshots of each route and state, not only the happy path.
- Finish a priority wave fully before starting the next. If time runs out, P2 stays honestly unfinished (see section 5); never trade P0 depth for P2 breadth.

## 4. Cross-Screen Consistency Check

After the last wave, compare screens side by side:

- **Same role, same treatment:** buttons (one solid primary per screen), tables (row height, header style, zebra/hover), status badges (same color and label for the same status everywhere), cards, form fields and error messages.
- **Formats:** dates, numbers, currency and units follow `reference/typography-locale.md`, identically on every screen.
- **Shell:** navigation shows the active item on every route; back links or breadcrumbs behave predictably on detail pages; page transitions share one duration and easing; page titles sit at the same position and size.
- **Theme:** if `.dark` tokens exist, a theme toggle is reachable from the global shell and every screen passes AA in both themes.
- Fix drift at the primitive or token, not by patching the odd screen.

## 5. Mandatory Coverage Report (end of App-mode work)

End with this table, one row per inventory screen, in the same order:

```markdown
| Screen | Priority | Done | States covered | Motion | Open gaps |
|---|---|---|---|---|---|
| /cv | P0 | Redesigned | 9/9 | score ring, row highlight | – |
| /settings | P2 | Styled to match | 4/9 | – | missing error state |
| /billing | P2 | Untouched | – | – | out of scope |
```

- **Done** takes exactly one value: `Redesigned` (full loop run), `Styled to match` (tokens and primitives applied, loop not run), `Untouched`.
- **States covered** is `n/total` from the inventory row; **Open gaps** names what is missing, never blank when states < total.
- Report `Untouched` and `Styled to match` honestly. The user then knows what still needs work, and nothing surprises them in the next review. Never mark `Redesigned` for a screen whose states or audit are incomplete.
