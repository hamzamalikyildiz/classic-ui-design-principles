# Visual quality: what lifts a correct page into a designed one

Rules remove errors; these moves create character. Pick the ones that fit the mood, do not stack all of them.

## 1. Palette from the subject, with a recipe
1. Name the subject's real-world material or light (ledger paper and ink, stage lighting, a paper map, a toy box).
2. Take the accent from that (forest green + brass for finance, ember on ink for audio, sun yellow + sky for kids).
3. Neutrals are tinted toward the accent hue (slate with a green cast), never pure `gray-*` next to a saturated accent.
4. One supporting hue 60-150 degrees away, used for state or highlights only.
5. Stock blue/indigo/violet-to-fuchsia accents are allowed only when the brief names them. `audit` reports `stock-look` otherwise.
6. Define the palette once (`tailwind.config` colors or `:root` variables) so the page reads as one system.

## 2. Type with a voice
- Pair a display face with a body face: a serif display (Fraunces, Newsreader, Playfair, Source Serif) lifts Trust and Editorial pages out of the SaaS look; a grotesque or condensed display suits Bold; a rounded display suits Playful; mono for numbers and labels in Technical and Trust.
- Large type is the cheapest hierarchy: one headline or one key number at 2-3x the next size.
- Numbers in tables and KPIs use tabular figures (`tabular-nums`).

## 3. One hero entrance and one moment
- Hero entrance: staggered CSS fade-up of headline, support text and visual (animation-fill-mode both, 400-700ms, `prefers-reduced-motion` turns it off). Content stays visible without JavaScript.
- One dealt moment per page: a count-up, a drawing line chart, a marquee, a hover that lifts a card. Not five.

## 4. Real product UI instead of boxes
- Show the product as it looks in use: a browser frame with a believable screen, a phone with a real list, a chart with an annotated event. Inline SVG or HTML, with specific labels and numbers.
- Charts carry a story: a threshold line, an event marker, a one-line annotation, a legend.

## 5. Atmosphere, lightly
- One surface treatment per page: a faint grain, a soft radial glow behind the hero, a hairline grid, or a paper tint. Never a purple-pink mesh by default.
- Layered depth: a hero surface, cards one step lighter or darker, shadows tinted with the page hue.

## 6. Rhythm
- Alternate section treatments (plain, tinted band, dark band, split); never more than three identical cards in a row.
- Vary card sizes inside a grid (one featured card spanning two columns).
- Equal outer margins and one container width per section type.

## 7. Template tells to remove
Three identical feature cards with a circled icon; centered hero with two buttons and a gradient blob; stock blue SaaS dashboard with grey sidebar; emoji as feature icons (outside Playful); "Lorem" or "Feature one" copy; pure grey body text on white with no tint.

Check before reporting: cover the logo. Could this page be for any company? If yes, add one specific detail (palette, drawing, data story, copy) until it could not.
