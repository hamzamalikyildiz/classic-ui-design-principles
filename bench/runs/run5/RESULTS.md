# Blind A/B results

Pairs: 12, judges: 5, votes: 60.

**Skill win rate (all votes): 40/60 = 67%**, pair-cluster bootstrap 95% CI 45% to 85%.

Per-pair majority: skill wins 9, no-skill wins 3, ties 0; exact sign test p = 0.1460.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 9/12 = 75% | 12 of 12 |
| Murat (34) | 9/12 = 75% | 12 of 12 |
| Nermin (63) | 3/12 = 25% | 12 of 12 |
| Kaan (45) | 10/12 = 83% | 12 of 12 |
| Selin (27) | 9/12 = 75% | 12 of 12 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| editorial | 6 | 3/6 |
| technical | 6 | 6/6 |

## Per brief type (majority per pair)

| Brief | Pairs | Skill majority wins | Vote win rate |
|---|---|---|---|
| m | 4 | 2/4 | 8/20 = 40% |
| r | 4 | 4/4 | 19/20 = 95% |
| v | 4 | 3/4 | 13/20 = 65% |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +0.45 |
| professional look | +0.88 |
| hierarchy and readability | -0.13 |
| content richness | +1.38 |

High-confidence votes only (conf >= 4): skill wins 25/33.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean --check WARNs |
|---|---|---|---|
| skill | 12 | 0 | 0.0 |
| noskill | 12 | 9 | 1.3 |

## Run setup and caveats

- Targeted run on the two weakest moods from run4 (technical, editorial): 2 moods x 3 brief types (`v`, `r`, `m`) x 2 repetitions = 12 pairs, 24 pages, 60 votes. Generators: Claude Haiku (2 fix rounds, both arms). Judges: 5 persona judges on Claude Sonnet (stronger than the generator, as in run4). Skill commit: the commit that added this folder.
- Skill changes under test: technical mood now requires labelled chart axes, non-overflowing code blocks and a small dashboard floor; editorial mood got figures-optional / pure-typography guidance (later reversed, see run6); `stock-look` audit rule widened.
- Result vs run4 (different models, not directly comparable): technical 6/6 pairs (run4: 0/3), editorial 3/6 (run4: 1/3).
- All five judges rejected the editorial `m` (recipe) pages that had no illustration (0/5 and 0/5), and one essay page for a half-empty right column. This is why the editorial figure rule was reversed for run6.
- Judges are language models; Nermin (63, low vision) preferred the no-skill pages in 9 of 12 pairs. Sample is small (12 pairs).
