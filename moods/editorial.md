# Editorial mood notes

- Left edges line up: the reading column shares the frame's left edge (no `mx-auto` on the column inside a left-aligned frame), or the headline and column are both centered.
- Two measures only: a wide frame (`max-w-4xl`/`5xl`) for header, display headline, figures and pull quotes, and a reading column (`max-w-prose`, 65ch) for body text. Align both to the same left edge or center both. Do not stack three or more container widths.
- The 65ch rule is for paragraphs. A 40–60px serif headline inside the reading column gets squeezed into 3–4 lines; let it span the wide frame.
- Long-form leading 1.65–1.8 (`leading-relaxed`/`loose`), quotes ≥1.4, never `leading-tight` on running text.
- Serif is allowed for body (Merriweather, Source Serif, Lora) and often warmer than a sans; still max 2 families.
- Depth comes from hairline rules and whitespace, so `border-heavy` does not apply.

Layout and figures:
- **Default layout: centered single reading column** (`max-w-prose` / `65ch` under a wide `max-w-4xl`/`5xl` headline and wide figures — generous open margins around a 65ch column are intentional editorial breathing room, NOT empty space!).
- Use a two-column layout (`lg:grid-cols-[minmax(0,65ch)_280px] gap-12`) **only** when the brief genuinely benefits from parallel margin notes, a recipe ingredient rail, or a compact sticky TOC — never stack 6-7 unrelated widgets just to match article height.
- Include at least one custom inline-SVG figure (map, diagram, timeline) with a caption, not a gradient box or stock placeholder.
- Give the piece a signature: a distinctive serif display face at 56px+ for the headline, one spot accent color from the subject, and a dark newsletter/closing band for contrast when the brief calls for one.
- **SVG figure craft:** keep every SVG label clear of axis lines, dashed threshold lines, and callout borders (`>= 8px` clearance; never run a vertical threshold line across bar value labels). `--check` reports `overlapping-labels`.
