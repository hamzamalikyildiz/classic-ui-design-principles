# Blind A/B results

Pairs: 6, judges: 5, votes: 30.

**Skill win rate (all votes): 20/30 = 67%**, pair-cluster bootstrap 95% CI 40% to 87%.

Per-pair majority: skill wins 5, no-skill wins 1, ties 0; exact sign test p = 0.2188.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 5/6 = 83% | 6 of 6 |
| Murat (34) | 3/6 = 50% | 6 of 6 |
| Nermin (63) | 2/6 = 33% | 6 of 6 |
| Kaan (45) | 5/6 = 83% | 6 of 6 |
| Selin (27) | 5/6 = 83% | 6 of 6 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| editorial | 6 | 5/6 |

## Per brief type (majority per pair)

| Brief | Pairs | Skill majority wins | Vote win rate |
|---|---|---|---|
| m | 2 | 2/2 | 7/10 = 70% |
| r | 2 | 2/2 | 8/10 = 80% |
| v | 2 | 1/2 | 5/10 = 50% |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +0.40 |
| professional look | +0.57 |
| hierarchy and readability | -0.27 |
| content richness | +0.33 |

High-confidence votes only (conf >= 4): skill wins 6/7.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean --check WARNs |
|---|---|---|---|
| skill | 6 | 0 | 0.2 |
| noskill | 6 | 3 | 0.7 |

## Run setup and caveats

- Editorial only: re-generated the 6 skill pages after reversing the editorial rule (every page gets one clean hero SVG; recipes use two columns by default; essays center headline and column together). The 6 no-skill pages are the same files as run5 (that arm does not depend on the skill). Same Haiku generator, same 5 Sonnet persona judges.
- Result: skill won 5 of 6 pairs by majority (run5 editorial: 3/6); vote win rate 20/30 = 67%, CI 40% to 87%, p = 0.22. **Not independent evidence:** the rule change was made after reading these judges' reasons on the same briefs and the same no-skill pages, so some of the gain is tuning to this test. A fresh set of briefs would be needed to confirm it.
- The only lost pair (`editorial-v-2`, an essay on map projections) lost 0/5: judges wanted a contents sidebar, a chart and a question list, which the no-skill page had.
- Nermin (63) won only 2 of 6 for the skill; hierarchy and readability scored slightly below the no-skill pages (-0.27), the one criterion where the skill is not ahead.
