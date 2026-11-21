# Motion Language

Motion shows state transitions, cause-and-effect, and spatial continuity—never decoration. Keep content visible without JS and collapse spatial travel under `prefers-reduced-motion: reduce`.

## 1. Motion tokens (single source)

- **Durations:** `instant 80ms` (press) · `fast 150ms` (hover/fade) · `base 220ms` (tabs/toasts) · `slow 320ms` (modals/drawers) · `deliberate 500ms` (hero/ring/chart; UI cap).
- **Easings:** `standard cubic-bezier(.2,0,0,1)` · `enter cubic-bezier(0,0,.2,1)` · `exit cubic-bezier(.4,0,1,1)` · `spring` (Motion/Framer: `stiffness: 400, damping: 30`).

```css
:root, @theme {
  --dur-instant: 80ms; --dur-fast: 150ms; --dur-base: 220ms;
  --dur-slow: 320ms;   --dur-deliberate: 500ms;
  --ease-standard: cubic-bezier(.2,0,0,1);
  --ease-enter: cubic-bezier(0,0,.2,1);
  --ease-exit: cubic-bezier(.4,0,1,1);
}
```

## 2. What moves

- **Composite-only:** ONLY GPU-composited `transform` and `opacity` (+ restrained `filter`, `clip-path`).
- **Never animate layout properties:** `width`, `height`, `top`, `left`, `margin`, `padding`.
- **Layout changes:** Use FLIP (`getBoundingClientRect` delta via `transform`), `grid-template-rows: 0fr -> 1fr`, or View Transitions (`document.startViewTransition`).

## 3. Choreography

- **1 hero entrance + staggered reveal:** `30–50ms` stagger, **max 6 items** (`animation-fill-mode: both`, no static `opacity: 0`).
- **Exits faster than enters:** `exit <= 0.7 * enter` (enter `220ms`, exit `150ms`).
- **Single visual focus:** One primary motion at a time.

## 4. 12-Pattern Catalog

1. **Skeleton -> content crossfade** (*async resolve; locked height, CLS = 0; `150–220ms --ease-standard`*):
```css
.slot { min-height: 7.5rem; position: relative; }
.pane { transition: opacity var(--dur-base) var(--ease-standard); }
.pane[aria-hidden="true"] { opacity: 0; pointer-events: none; position: absolute; inset: 0; }
```
2. **Count-up + progress/score ring fill** (*KPI/score update; `tabular-nums`, `aria-live="polite"`; `500ms --ease-enter`*):
```css
.ring-fg { transition: stroke-dashoffset var(--dur-deliberate) var(--ease-enter); }
.metric  { font-variant-numeric: tabular-nums; }
```
3. **Accepted row highlight flash** (*row saved/accepted; `1.2s` fade; border fallback in `reduced-motion`*):
```css
.row-ok { position: relative; }
.row-ok::after { content: ""; position: absolute; inset: 0; background: rgb(16 185 129/.16);
  animation: flash 1.2s var(--ease-enter) forwards; pointer-events: none; }
@keyframes flash { from { opacity: 1; } to { opacity: 0; } }
```
4. **Optimistic list add/remove** (*insert/delete without reflow jitter; `220ms --ease-standard`*):
```css
.row-wrap { display: grid; grid-template-rows: 1fr; transition: grid-template-rows var(--dur-base) var(--ease-standard), opacity var(--dur-fast); }
.row-wrap.out { grid-template-rows: 0fr; opacity: 0; }
.row-wrap > div { overflow: hidden; }
```
5. **Long-operation stage transition** (*`>3s` job step; stage icon morphs to check; `220ms --ease-enter`*):
```css
.stage-icon { transition: transform var(--dur-base) var(--ease-enter), opacity var(--dur-fast); }
.stage[data-done] .stage-icon { transform: scale(1); opacity: 1; }
```
6. **Toast enter/exit + Undo affordance** (*`role="status"`, 4–6s Undo button; enter `220ms --ease-enter`, exit `150ms --ease-exit`*):
```css
.toast { transform: translateY(12px); opacity: 0; transition: transform var(--dur-base) var(--ease-enter), opacity var(--dur-base) var(--ease-enter); }
.toast.open { transform: translateY(0); opacity: 1; }
.toast.exit { opacity: 0; transition: opacity var(--dur-fast) var(--ease-exit); }
```
7. **Modal / drawer** (*`aria-modal="true"`, focus trap; backdrop fade + panel translate; enter `220–320ms`, exit `150–220ms`*):
```css
.backdrop { opacity: 0; transition: opacity var(--dur-base) var(--ease-enter); }
.panel    { transform: translateY(8px) scale(.98); opacity: 0; transition: transform var(--dur-base) var(--ease-enter), opacity var(--dur-base) var(--ease-enter); }
.open .backdrop, .open .panel { opacity: 1; transform: none; }
```
8. **Page transitions** (*route change / shared card->heading via `document.startViewTransition` or Next.js experimental `ViewTransition`; `220ms`*):
```css
.card-title { view-transition-name: hero-title; }
::view-transition-old(root), ::view-transition-new(root) { animation-duration: var(--dur-base); }
```
9. **Button tactile press & card hover lift** (*press `80ms scale(0.98)`; card hover `150ms translateY(-1px)` + shadow*):
```css
.btn { transition: transform var(--dur-instant) var(--ease-standard); }
.btn:active { transform: scale(0.98); }
.card-hit { transition: transform var(--dur-fast) var(--ease-standard), box-shadow var(--dur-fast); }
.card-hit:hover { transform: translateY(-1px); }
```
10. **Sliding active tab indicator** (*`role="tablist"` transform slider or Motion `layoutId="tab"`; `220ms --ease-standard`*):
```css
.tab-pill { transition: transform var(--dur-base) var(--ease-standard); transform: translateX(calc(var(--tab,0) * 100%)); }
```
11. **Line / chart stroke draw** (*hero chart mounts; runs once; `500ms --ease-enter` with `pathLength="1"`*):
```css
.chart-path { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw var(--dur-deliberate) var(--ease-enter) forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }
```
12. **Completion moment** (*check stroke draw `220ms --ease-enter`; restrained confetti strictly Playful-only*):
```css
.check-path { stroke-dasharray: 24; stroke-dashoffset: 24; animation: draw var(--dur-base) var(--ease-enter) 80ms forwards; }
```

## 5. Mood Motion Personality Table

| Mood | Personality | Timing & Easing | Boundaries |
|---|---|---|---|
| **Playful** | Springy, expressive | `220–320ms`, `spring(400,30)` | Tactile bounce, badge pop, restrained completion confetti |
| **Bold** | Cinematic, deliberate | `320–500ms`, `--ease-enter` | Hero stagger (`40–50ms`), view transitions, confident scale |
| **Trust** | Calm, crisp | `150–220ms`, `--ease-standard` | Zero bounce; count-up ring, row highlight flash, tab pill |
| **Editorial** | Minimal, opacity-led | `150–220ms`, `--ease-standard` | Crossfades (`opacity` or `2px` lift); no sliding cards/springs |
| **Technical** | Ultra-fast, functional | `80–150ms`, `--ease-standard` | Instant state swaps, `80ms` press, zero entrance motion |

## 6. Anti-patterns

- Sliding every block on scroll or heavy scroll-linked parallax.
- `> 500ms` button/UI feedback (`long-ui-transition`) or `> 100ms` click delay (`slow-feedback`).
- Unpausable infinite motion (`infinite-motion` outside loading spinners/skeletons).
- Ignoring `prefers-reduced-motion` (`reduced-motion-ignored`).
- Animating layout properties (`width/height/top/left/margin/padding`, or async shifts `CLS > 0.05`).

## 7. Reduced-motion rule

Map every pattern to `@media (prefers-reduced-motion: reduce)`: **zero spatial travel (`transform: none`), instant state swap or `<= 150ms` opacity dissolve**, and border fallback.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important; animation-iteration-count: 1 !important;
    transition-duration: 120ms !important; transition-property: opacity, color, background-color, border-color !important;
    transform: none !important;
  }
  .row-ok::after { animation: none !important; opacity: 0 !important; }
  .row-ok { border-left: 2px solid #10b981; }
}
```
