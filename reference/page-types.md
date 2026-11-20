# Page-type matrix

Always-on baseline: WCAG AA, 8pt grid, semantic colors, max 2 fonts, modular scale, one hero surface per screen, single primary CTA, depth over borders, Jakob, proximity.

| Page type | Additional rules | Default mood | Layout |
|---|---|---|---|
| Landing / marketing | Z-pattern, Fitts (large hero CTA), bento features, focal visual in hero | Bold (Playful for kids/consumer) | Full-width sections, spacing from mood |
| Dashboard / admin | F-pattern, bento metrics with one featured card, Miller (sidebar ≤7), skeleton/empty/error, categorical chart colors | Trust | Left sidebar + 12-col grid, `gap-4`/`gap-6` |
| Form / onboarding / checkout | Hick (steps), progressive disclosure, Fitts (full-width submit on mobile), inline errors in semantic red | Trust | Single column, `max-w-md`/`max-w-lg` |
| Content / blog / docs | 45–75 chars for body (`max-w-prose`), F-pattern, accent for links only, two measures (see Editorial notes) | Editorial | Wide frame + centered reading column |
| Mobile app screen | Fitts (44–48px targets, CTA in bottom zone), Miller (tab bar ≤5), skeleton | brand's | Single column, 16px side padding |
| E-commerce / catalog | Hick (grouped filters), skeleton grid, empty state, one CTA per card | Bold or Trust | Responsive card grid |
| Settings / profile | Proximity (grouped sections, whitespace over dividers), Jakob, Miller | Trust | Side menu + content |
| Component: nav / menu | Jakob, Miller (5–7 items), accent active state | page's | Top bar or left sidebar |
| Component: card / modal / dialog | Nested radius, proximity, single primary CTA (bottom-right, ghost cancel to its left) | page's | `p-4`/`p-6`, modal `max-w-md`–`max-w-lg` |

The user's explicit request wins over the matrix. Keep every requested item; when a request collides with a rule (10 menu items vs. Miller, three buttons vs. single CTA), satisfy the rule through presentation (grouping, "More" menus, outline/ghost variants) and say so in the report. Report any other deliberate deviation with its reason.

**No extra moods.** Map unusual briefs onto these five: luxury/fashion → Editorial with a Bold hero; e-commerce → Trust base with a Bold hero band; mobile app → the brand's mood; internal tools → Technical or Trust. Dark mode is a theme, not a mood.
