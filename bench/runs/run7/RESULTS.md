# Blind A/B results

Pairs: 10, judges: 5, votes: 50.

**Skill win rate (all votes): 38/50 = 76%**, pair-cluster bootstrap 95% CI 60% to 88%.

Per-pair majority: skill wins 9, no-skill wins 1, ties 0; exact sign test p = 0.0215.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 8/10 = 80% | 10 of 10 |
| Murat (34) | 10/10 = 100% | 10 of 10 |
| Nermin (63) | 4/10 = 40% | 10 of 10 |
| Kaan (45) | 7/10 = 70% | 10 of 10 |
| Selin (27) | 9/10 = 90% | 10 of 10 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| bold | 2 | 2/2 |
| editorial | 2 | 1/2 |
| playful | 2 | 2/2 |
| technical | 2 | 2/2 |
| trust | 2 | 2/2 |

## Per brief type (majority per pair)

| Brief | Pairs | Skill majority wins | Vote win rate |
|---|---|---|---|
| a | 5 | 4/5 | 16/25 = 64% |
| b | 5 | 5/5 | 22/25 = 88% |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +0.66 |
| professional look | +0.96 |
| hierarchy and readability | +0.12 |
| content richness | +1.60 |

High-confidence votes only (conf >= 4): skill wins 23/26.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean --check WARNs |
|---|---|---|---|
| skill | 10 | 0 | 0.0 |
| noskill | 10 | 9 | 1.2 |

## Run setup and caveats (held-out validation)

- **Pre-registered:** skill frozen at commit `13ef373` and the 10 briefs in `bench/briefs_holdout.json` were written before any page was generated; nothing was tuned after seeing these results. The briefs were not used in runs 2-6.
- 5 moods x 2 new briefs (`a`, `b`) x 1 repetition = 10 pairs, 20 pages, 50 votes. Generators: Claude Haiku (2 fix rounds, both arms). Judges: 5 persona judges on Claude Sonnet; A/B placement was 25/25 and pair order was randomized per judge.
- **Result:** skill won 38/50 votes (76%), 9 of 10 pairs by majority; exact sign test p = 0.0215 (the first run in this repo with p < 0.05), bootstrap CI 60% to 88%.
- **Only lost pair:** `editorial-a-1` (ceramics profile): 1/5. Judges called the skill page's bowl-and-flame illustration odd and the body text stuck in a left column. The same weakness as in runs 5-6 (left-stacked column, odd hero SVG).
- Judges are language models from one family, not people. Nermin (63, low vision) preferred the skill pages in only 4 of 10 pairs; hierarchy and readability is the one criterion with almost no gap (+0.12).
- **Length confound remains:** skill pages are larger (mean 225 vs 180 lines, 14.4 vs 10.4 KB) and content richness shows the biggest score gap (+1.60). The judges are told not to reward length, but a longer, fuller page likely helps.
- Small sample (10 pairs): read the confidence interval, not just the win rate.
