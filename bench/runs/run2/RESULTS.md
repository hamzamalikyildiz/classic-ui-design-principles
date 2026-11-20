# Run 2 results (blind A/B, 10 pairs)

Generator: Haiku, both arms, 1 fix round. Judge: one Sonnet pass over 1000px crops. Skill version: with visual-quality.md and the updated Trust mood.

| Pair | Mood | Brief | Winner | Confidence | Reason |
|---|---|---|---|---|---|
| cift1 | technical | r | skill | 4 | B reads like a real observability tool with SLO banner, annotated chart, service table and dense log table, while A is a competent but plainer dashboard. |
| cift2 | playful | m | skill | 3 | B has a bolder, more distinctive playful identity with tilted polaroid cards, bento features and stats, whereas A is tidy but closer to a standard kids template. |
| cift3 | editorial | m | skill | 4 | A has a stronger editorial layout with sidebar facts, pull quote, ingredients table and richly illustrated related items, while B is simpler and its related cards are plain gradients. |
| cift4 | trust | r | skill | 4 | A feels more crafted with serif numerals, a contextual overdue alert, an annotated cash flow chart and a coherent green palette, while B is a generic fintech dashboard. |
| cift5 | editorial | r | noskill | 2 | A is the more elegant and consistent editorial page with a nicer map illustration, while B has more furniture (sidebar, stat) but overlapping map labels and a long empty right column. |
| cift6 | bold | r | skill | 4 | B has a bold condensed typographic identity, marquee, bento features and a strong closing CTA, while A is a safe dark headphone template with filler icons. |
| cift7 | playful | r | skill | 4 | A has a bold, coherent chunky palette with a lively robot hero, bento features, a code-based mini-game teaser and rich pricing, whereas B is cleaner but more generic. |
| cift8 | technical | m | skill | 2 | A has a distinctive monospace ops-console feel with annotated SLO chart and dense, believable data, while B is a nicer-coloured but more standard dashboard. |
| cift9 | bold | m | skill | 3 | A has a striking oversized hero with a reel card, ticker, varied work grid with a bold CTA, while B has awkward stray hero shapes and a more repetitive grid. |
| cift10 | trust | m | skill | 5 | B is a much richer, thoughtful clinic dashboard with next-patient banner, alert, target-lined chart and full schedule, while A is sparse and generic. |

Skill wins 9/10.

- skill: axe serious pages 0/10, mean --check WARNs 0.1
- noskill: axe serious pages 9/10, mean --check WARNs 1.5

Caveats: one judge, one repetition, 10 pairs; indicative, not conclusive. `brief` r = detailed brief, m = second brief.
HTML files are in `skill/` and `noskill/` next to this file.