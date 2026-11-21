# Editorial mood notes

- Left edges line up: the reading column shares the frame's left edge (no `mx-auto` on the column inside a left-aligned frame), or the headline and column are both centered.
- Two measures only: a wide frame (`max-w-4xl`/`5xl`) for header, display headline, figures and pull quotes, and a reading column (`max-w-prose`, 65ch) for body text. Align both to the same left edge or center both. Do not stack three or more container widths.
- The 65ch rule is for paragraphs. A 40–60px serif headline inside the reading column gets squeezed into 3–4 lines; let it span the wide frame.
- Long-form leading 1.65–1.8 (`leading-relaxed`/`loose`), quotes ≥1.4, never `leading-tight` on running text.
- Serif is allowed for body (Merriweather, Source Serif, Lora) and often warmer than a sans; still max 2 families.
- Depth comes from hairline rules and whitespace, so `border-heavy` does not apply.

Layout and figures:
- **Essay default: one centered reading column** (`max-w-prose` / `65ch`) under a wide `max-w-4xl`/`5xl` headline, with the figure, pull quotes and the closing band spanning the wide frame so the page uses its width. Center the headline block and the column together (the left-edges rule above), or use two columns; a left-stacked column with a blank right half on a wide page reads as unfinished.
- **Recipe and reference pages use two columns by default**: an ingredient and at-a-glance rail beside the numbered method (`lg:grid-cols-[minmax(0,65ch)_280px] gap-12`, or ingredients left and method right). Keep the rail as long as its content needs; a facts or contents sidebar is also fine for long essays. Never stack 6-7 unrelated widgets just to match article height.
- **Every editorial page needs one hero figure** (blind tests: text-only editorial pages lost 5 of 5 judges on a recipe brief). Draw one inline SVG that illustrates the actual subject, composed with care and captioned: a recipe gets a drawn dish or ingredient still life, an essay gets a map, diagram, timeline or chart that carries information. Keep it clean and flat (3-6 shapes in the page palette, no cartoon blobs, no generic icons, no gradient box pretending to be an image), and keep captions and labels clear of the artwork (`>= 8px`). Support it with typography: oversized serif headline, drop cap, pull quote, ruled section breaks.
- Floor for an article or recipe page (use only what the brief names): masthead and section nav, kicker, headline, standfirst, byline, body with drop cap, a pull quote, related stories, a newsletter or closing band.
- Give the piece a signature: a distinctive serif display face at 56px+ for the headline, one spot accent color from the subject, and a dark newsletter/closing band for contrast when the brief calls for one.
- **SVG figure craft:** keep every SVG label clear of axis lines, dashed threshold lines, and callout borders (`>= 8px` clearance; never run a vertical threshold line across bar value labels). `--check` reports `overlapping-labels`.
