# Blind A/B results

Pairs: 5, judges: 5, votes: 25.

**Skill win rate (all votes): 16/25 = 64%**, pair-cluster bootstrap 95% CI 28% to 88%.

Per-pair majority: skill wins 4, no-skill wins 1, ties 0; exact sign test p = 0.3750.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 4/5 = 80% | 5 of 5 |
| Murat (34) | 4/5 = 80% | 5 of 5 |
| Nermin (63) | 1/5 = 20% | 5 of 5 |
| Kaan (45) | 3/5 = 60% | 5 of 5 |
| Selin (27) | 4/5 = 80% | 5 of 5 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| bold | 1 | 1/1 |
| editorial | 1 | 0/1 |
| playful | 1 | 1/1 |
| technical | 1 | 1/1 |
| trust | 1 | 1/1 |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +0.44 |
| professional look | +0.56 |
| hierarchy and readability | +0.08 |
| content richness | +1.16 |

High-confidence votes only (conf >= 4): skill wins 9/12.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean layout WARNs (non-axe) |
|---|---|---|---|
| skill | 5 | 0 | 0.0 |
| noskill | 5 | 4 | 0.4 |
