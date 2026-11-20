# Expressive moods: Playful and Bold

Hero archetypes: Bold = dark stage with one accent glow and a large drawn product; Playful = flat saturated color blocks, chunky shapes and a drawn mascot or toy, optional soft gradient; Trust = one accent card with a real chart; Technical = layered ink panels with live data; Editorial = large serif type with a drawn illustration.

**Expressive moods (Playful, Bold): concept first, rules second.**
These two are judged on memorability, so the audit only enforces a floor and turns style rules (grid, CTA count, card radius, fonts, depth) into INFO. You may break a style rule on purpose when the concept needs it; you may not break the floor.
1. Write the concept in one line before any code: "visual idea + 3 personality words", e.g. "a toy workshop: chunky, tilted, warm" or "stage lighting: huge type, one lime glow, sharp".
2. Spend the effort on 2-3 signature moves, not on balance. Pick from: a drawn mascot/toy/product that is half the hero; type at 96px+ with a trick (outline, crop, vertical, overlap); rotated or overlapping blocks; a marquee or live visual (spectrum, ticker, drag-and-drop demo); a section that changes background color and shape; art bleeding off an edge (a third of it still visible, subject whole).
3. Make the page lopsided on purpose: vary section rhythm, alternate full-color bands with plain ones, repeat no card style more than 3 times in a row.
4. Pick the type pair from the concept (display examples: Baloo 2, Lilita One, Bricolage Grotesque, Chewy for Playful; Archivo Black, Anton, Space Grotesk 700, Sora 800, Bebas Neue for Bold); Inter is for body only. Up to 3 families.
5. Inline-SVG illustrations are drawn, not geometric placeholders; emoji decorate and never replace the mascot.

Floor, never broken: AA contrast (including on gradients), 44px primary tap targets, visible focus, reduced-motion respected, all content visible without JavaScript, nothing clipped, empty or overlapping. Run `render.py --check` and fix every WARN it prints.

**Content must show without JavaScript.** No `opacity-0`/`.reveal` start state that only a script clears; use a CSS animation with `animation-fill-mode: both` or leave content visible. A page that renders blank in a screenshot has failed.

Content floor (landing): hero with a focal illustration or product visual, 3+ feature blocks of different sizes, proof (numbers or quotes), pricing or specs, FAQ or secondary section, closing CTA band.

