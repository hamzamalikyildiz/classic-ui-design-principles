# Blind A/B results

Pairs: 20, judges: 5, votes: 100.

**Skill win rate (all votes): 90/100 = 90%**, pair-cluster bootstrap 95% CI 83% to 96%.

Per-pair majority: skill wins 20, no-skill wins 0, ties 0; exact sign test p = 0.0000.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 17/20 = 85% | 20 of 20 |
| Murat (34) | 20/20 = 100% | 20 of 20 |
| Nermin (63) | 14/20 = 70% | 20 of 20 |
| Kaan (45) | 19/20 = 95% | 20 of 20 |
| Selin (27) | 20/20 = 100% | 20 of 20 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| bold | 4 | 4/4 |
| editorial | 4 | 4/4 |
| playful | 4 | 4/4 |
| technical | 4 | 4/4 |
| trust | 4 | 4/4 |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +1.19 |
| professional look | +1.30 |
| hierarchy and readability | +0.87 |
| content richness | +2.35 |

High-confidence votes only (conf >= 4): skill wins 56/58.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean --check WARNs |
|---|---|---|---|
| skill | 20 | 0 | 0.1 |
| noskill | 20 | 18 | 1.6 |

## Run setup and caveats

- Protocol v2 (`bench/PROTOCOL.md`): 5 moods x 2 briefs x 2 repetitions = 20 pairs, 40 pages. Generators and judges are Haiku; both arms had the same 2 fix rounds. Skill commit: see the git log entry that added this folder.
- Judges are language models role-playing five personas, not people. Judges and generators are from the same model family, which may favor similar-looking pages.
- **Length confound:** skill pages are larger (mean 235 vs 188 lines, 16.1 vs 10.5 KB) and the skill explicitly asks for fuller pages ("content floor"). The judge prompt tells judges not to reward length alone, but richer pages likely help the skill arm; the content-richness gap (+2.35) is the largest of the four criteria.
- Position: judges picked A in 58 of 100 verdicts (an earlier count reported 57 of 99 because a leading UTF-8 BOM on line 1 of `judge_murat.txt` broke line-start matching; both `score.py` and `judge_murat.txt` are now BOM-safe), and `skill=A` occurred in 56/100 placements due to the unweighted per-judge coin flip used in run3 (since fixed to exact 50/50 per judge in `make_judge_sets.py`). Pair order and A/B placement were randomized per judge, so position effects cancel out in the totals.
- Tool issues seen while generating: the static `audit` assumes a white page when the dark background is set in CSS instead of on `body`, producing false `wcag-aa` FAILs on dark pages (agents worked around it by adding a `bg-*` class to `body`).
- A 20/20 pair-majority result is unusually strong. Treat it as evidence that the skill helps cheap models under this rubric, and confirm with human raters before making stronger claims.
