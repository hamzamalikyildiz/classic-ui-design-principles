# Expressive moods: Playful and Bold

Hero archetypes: Bold = dark stage (or saturated band) with oversized display type and a focal product/accent; Playful = flat saturated color blocks, chunky rounded shapes and a drawn mascot or toy, optional soft gradient.

**Expressive moods (Playful, Bold): concept first, rules second.**
These two are judged on memorability, so the audit only enforces a floor and turns style rules (`grid`, `miller-7`, `single-primary-cta`, `grey-chart`, `max-2-fonts`, `no-hero-surface`, `border-heavy`, `no-drawn-mascot`, `card-sameness`, `bold-headline-size`, `bold-font-default`) into INFO. You may break a style rule on purpose when the concept needs it; you may not break the floor.
1. Write the concept in one line before any code: "visual idea + 3 personality words", e.g. "a toy workshop: chunky, tilted, warm" or "stage lighting: huge type, one lime glow, sharp".
2. Spend the effort on 2-3 signature moves, not on balance. Pick from: a drawn mascot/toy/product that spans half the hero; solid high-contrast oversized display typography (`96px+` with scale contrast, tight tracking, or subtle bleed/crop — avoid hollow outlined stroke letters or overlapping text that degrades low-vision legibility); rotated or overlapping blocks; a marquee or live visual (spectrum, ticker, drag-and-drop demo, paused/reduced by `prefers-reduced-motion`); a section that changes background color and shape; art bleeding off an edge (a third of it still visible, subject whole).
3. Make the page lopsided on purpose: vary section rhythm, alternate full-color bands with plain ones, repeat no card style more than 3 times in a row.
4. Pick the type pair from the concept (display examples: Baloo 2, Lilita One, Bricolage Grotesque, Chewy for Playful; Archivo Black, Anton, Space Grotesk 700, Sora 800, Bebas Neue for Bold); Inter is for body only. Up to 3 families; keep body copy `>= 14px` with strong contrast on dark or saturated bands (reserve `12px` for short kickers/tags).
5. Inline-SVG illustrations are drawn, not geometric placeholders; emoji decorate and never replace the mascot.

Floor, never broken: AA contrast (including on gradients and inside dark/saturated cards), `>= 44px` primary tap targets, visible focus, `prefers-reduced-motion` respected, all content visible without JavaScript (no `opacity-0` start state without CSS `animation-fill-mode: both`), nothing clipped, empty or overlapping. Run `render.py --check` and fix every WARN it prints.

**Scope (no forced template quota):** build a strong hero plus only the supporting sections the brief calls for, rather than stacking a fixed 6-section quota or invented filler blocks.
