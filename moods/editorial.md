# Editorial mood notes

- Left edges line up: the reading column shares the frame's left edge (no `mx-auto` on the column inside a left-aligned frame), or the headline and column are both centered.
- Two measures only: a wide frame (`max-w-4xl`/`5xl`) for header, display headline, figures and pull quotes, and a reading column (`max-w-prose`, 65ch) for body text. Align both to the same left edge or center both. Do not stack three or more container widths.
- The 65ch rule is for paragraphs. A 40–60px serif headline inside the reading column gets squeezed into 3–4 lines; let it span the wide frame.
- Long-form leading 1.65–1.8 (`leading-relaxed`/`loose`), quotes ≥1.4, never `leading-tight` on running text.
- Serif is allowed for body (Merriweather, Source Serif, Lora) and often warmer than a sans; still max 2 families.
- Depth comes from hairline rules and whitespace, so `border-heavy` does not apply.

Content floor: masthead with date/section nav, kicker + headline + standfirst + byline with avatar, illustration with caption, drop cap, pull quote, related stories, newsletter.

Fill the page (lost 5/6 blind pairs for looking thin):
- A 65ch column alone leaves the right half empty at 1280px. Use a two-column article: reading column plus a sticky aside (`lg:grid-cols-[minmax(0,65ch)_280px] gap-12`) with contents list, one big statistic, key facts or related reading.
- Include at least one custom inline-SVG figure (map, diagram, timeline) with a caption, not a gradient box or stock placeholder. Related stories get small illustrated cards (SVG shape per card), not text-only links.
- Give the piece a signature: a distinctive serif display face at 56px+ for the headline, one spot accent color from the subject, and a dark newsletter/closing band for contrast.
- Verify with the screenshot: no region of the page wider than 300px x 400px is blank. A sticky aside that is short still looks like an empty right column in a full-page screenshot: keep the aside as long as the article (stats, key facts, contents, related reading, a second figure) or use one centered column instead. `render.py --check` reports this as `empty-column`.
- Labels inside SVG figures (map pins, chart annotations) need 8px clearance from each other and from lines; place them on a grid, shorten them, or move them into a legend. `--check` reports `overlapping-labels`.
