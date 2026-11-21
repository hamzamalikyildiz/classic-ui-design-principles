# Blind A/B results

Pairs: 6, judges: 5, votes: 30.

**Skill win rate (all votes): 25/30 = 83%**, pair-cluster bootstrap 95% CI 73% to 93%.

Per-pair majority: skill wins 6, no-skill wins 0, ties 0; exact sign test p = 0.0312.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 3/6 = 50% | 6 of 6 |
| Murat (34) | 6/6 = 100% | 6 of 6 |
| Nermin (63) | 5/6 = 83% | 6 of 6 |
| Kaan (45) | 5/6 = 83% | 6 of 6 |
| Selin (27) | 6/6 = 100% | 6 of 6 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| bold | 1 | 1/1 |
| editorial | 2 | 2/2 |
| playful | 1 | 1/1 |
| technical | 1 | 1/1 |
| trust | 1 | 1/1 |

## Per brief type (majority per pair)

| Brief | Pairs | Skill majority wins | Vote win rate |
|---|---|---|---|
| a | 5 | 5/5 | 21/25 = 84% |
| b | 1 | 1/1 | 4/5 = 80% |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +0.73 |
| professional look | +1.13 |
| hierarchy and readability | +0.93 |
| content richness | +0.47 |

High-confidence votes only (conf >= 4): skill wins 21/25.

## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean layout WARNs (non-axe) |
|---|---|---|---|
| skill | 6 | 0 | 0.0 |
| noskill | 6 | 3 | 0.3 |
## Run setup and caveats (held-out validation v2)

- **Pre-registered & cross-family:** skill frozen at commit `fc3a31b` (post-Wave 1/2/3 hardening) and the 6 unseen briefs in `bench/briefs_holdout_v2.json` were committed before any page was generated. Generators: **Gemini 4 Hydrogen (Low)** (2 fix rounds, both arms). Judges: 5 **Gemini 4 Neon (Medium)** persona judges evaluating blindly in Turkish; A/B placement alternated across judges (`15/30` A vs B), pair order randomized per judge.
- **Result:** skill won **25/30 votes (83%)**, **6 of 6 pairs** by majority; exact sign test `p = 0.0312`, pair-cluster bootstrap 95% CI **73% to 93%**. High-confidence votes (`conf >= 4`): **21/25**.
- **Readability & Editorial validation:**
  - `editorial-a` (*Spruce and Varnish*, quiet profile): **4/5 wins** — skill omitted unrequested decorative SVGs and won Kaan, Murat, Nermin, and Selin on pure serif typography and centered alignment over `noskill`'s crude violin drawing.
  - `editorial-b` (*The Roasting Curve*): **4/5 wins** — clean schematic SVG without colliding labels (whereas `noskill`'s chart labels overlapped the curve, noted independently by Murat, Nermin, Kaan, Selin).
  - **Low-vision & Technical (`Nermin 5/6 = 83%`, `technical-a 4/5`):** `hierarchy and readability` jumped from `+0.12` (`run7`) / `-0.27` (`run6`) to **`+0.93`**, and Nermin explicitly praised the larger `technical` dashboard text, high-contrast status tags, and clean `editorial` typography.
- **Balanced page length:** mean HTML length was nearly matched (**260.8 vs 246.5 lines**, `+5.8%`; **14.9 vs 12.9 KB**), and `content richness` (`+0.47`) was no longer the main driver—`professional look` (`+1.13`) and `hierarchy and readability` (`+0.93`) led instead.
- **Automatic metrics (strictly non-axe separated):** serious axe violations `0/6` (`skill`) vs `3/6` (`noskill`); mean non-axe layout WARNs `0.0` vs `0.3`.
- **Caveats:** small sample (`n = 6` pairs, wide generalization error even though `6/6` reaches `p = 0.0312`), LLM persona judges rather than real users, and `skill` arm still runs `--check` while `noskill` runs plain screenshots (`render.py --out`).
