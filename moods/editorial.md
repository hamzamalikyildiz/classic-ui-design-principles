# Editorial mood notes

## Layout (pick one clean structure — never leave a blank right half)
- **Single-column essay or profile (default):** keep one centered reading axis. Either a centered reading column (`mx-auto max-w-prose`) inside a wider centered frame (`max-w-4xl`/`5xl`) where the display headline, optional wide figure, pull quotes and closing band are centered together, OR one unified centered column (`mx-auto max-w-2xl`). **Never** left-align a lone `max-w-prose` reading column inside a wide `max-w-4xl`/`5xl` frame with dead empty space beside it.
- **Two-column layout (when a sidebar genuinely helps):** for recipes, itineraries, long references, or articles with real side material, place the reading column beside a purposeful rail (`lg:grid-cols-[minmax(0,65ch)_280px] gap-12`, or ingredients left and method right). Keep the rail strictly as tall as its content needs; never stack unrelated filler widgets to match article height.
- Use at most two container widths: one wide frame + one reading column (or one unified centered column).

## Typography & low-vision readability
- Pair an oversized serif display `h1` (56px+) with a serif body (`Newsreader`, `Source Serif 4`, `Merriweather`, `Lora`) or clean sans; max 2 families. Let an oversized `h1` span the wide frame instead of squeezing into 3–4 narrow lines; keep section `h2` headings inside the reading column with their paragraphs.
- Body copy `text-lg` (18px) with long-form leading `1.7–1.8` (`leading-relaxed`/`loose`); pull quotes `leading >= 1.4`; never `leading-tight` on running text.
- Keep sidebars, dark bands and captions comfortable for low-vision readers: body/list text inside rails and dark bands at `text-sm`–`text-base` (14–16px) with high contrast (never dense `text-xs` muted walls); reserve `text-xs` for short kickers/labels. Avoid hollow or outlined stroke display letters that weaken legibility.
- Depth comes from `1px` hairline rules and whitespace, so `border-heavy` does not apply.

## Visuals & scope (earned, never forced)
- **No graphic or illustration is mandatory.** Include a visual only when it genuinely clarifies the piece or the brief explicitly asks for one.
- When a figure *does* earn its space, prefer **information-bearing schematics** drawn from the subject: maps, route diagrams, timelines, process or temperature curves, comparison charts, or annotated diagrams. Keep every SVG label and caption `>= 8px` clear of lines and artwork (`--check` reports `overlapping-labels`).
- Avoid figurative object clip-art (generic bowls, plates, flames) and decorative abstract blobs — a weak inline SVG hurts an editorial page more than clean typography.
- When no graphic serves the topic (a quiet profile, interview, or literary essay), let editorial craft carry the page: oversized serif headline, crisp standfirst and byline, drop cap, ruled section breaks, a generous pull quote, and — where genuinely useful — a structured maker/index note or at-a-glance facts block.
- Related stories without photography should be **typographic** (kicker, headline, short deck, hairline divider) — never empty gradient or flat color-block placeholder boxes.
- Include only the elements the brief calls for (masthead/nav, kicker, headline, standfirst, byline, body, pull quote, related stories, newsletter/closing band); do not force a dark closing band or extra boxes unless they fit the piece.
