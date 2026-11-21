# Trust mood notes

- One accent plus tinted neutrals, `shadow-sm`, 12-16px radius, one hero accent card/band per screen.
- Trust does not mean generic. Take the accent from the subject (forest green and brass for money, deep teal for health, ink navy for legal), not stock blue; tint the neutrals toward it; give headings a serif or distinctive display face and keep a clean sans for data (`reference/visual-quality.md`).
- **Concept + 1 primary data anchor:** start from the brief's core story (an annotated chart, OR a main ledger/schedule table, OR an action queue) and add only 1-2 supporting modules that the brief asks for. Calm breathing room is part of Trust; never invent extra sidebars, drawers, or filler widgets just to fill space.
- **Panel craft (when included):** if a table/list is present, populate it realistically (typically 6-10 real rows with `tabular-nums`, no stub placeholders); if a chart is present, include labelled axes, a legend, and one annotation; give KPI figures generous card width (`shrink-0` on top-right badges/icons, concise button copy) so large currency numbers never clip icons or crush buttons.
- Semantic colors carry state (red/amber/green) and always come with text or an icon.
- **Low-vision comfort:** keep KPI sublabels, table rows, chart legends and copy inside dark accent hero cards at `>= 14px` (`text-sm`) with strong contrast; avoid `text-xs` body lists or faint translucent white text (`text-white/60`) on dark accent cards.
- One signature detail so it is not a template: a ledger-paper tint, a real-looking statement preview, date chips, or a hand-drawn empty state.

## Motion & state tone (`reference/motion.md`, `reference/states.md`)
- **Motion personality:** calm, predictable (`150-220ms` `standard` cubic-bezier); subtle card elevation (`translateY(-1px)` + `shadow-md`), restrained count-up/ring fill (`tabular-nums`), zero playful bounce or confetti.
- **State & microcopy tone:** reassuring, precise, non-alarmist (errors state exactly what is safe and the direct recovery action; empty states explain the next workflow step; >3s operations show named verification stages and elapsed/estimated time).
