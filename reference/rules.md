# Rule reference

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
- Modular scale: `scale --ratio <ratio>` output. Do not shrink Tailwind's small sizes: `xs` ≥12px, `sm` ≥14px (the script enforces this). Body 16px. Line-height by size: body 1.5–1.6 (long-form 1.65–1.8), 20–24px text 1.4, headings 1.1–1.25. The `scale` output follows this.
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
