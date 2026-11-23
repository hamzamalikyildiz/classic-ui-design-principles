# run10: loose-rules trial (one page per mood, three arms)

Question (from `PLAN-esnek-kurallar.md`): does loosening the rules (a 9-item floor, defaults and ideas, style audit findings as INFO) make an agent cheaper without lowering quality?

- **Arms:** `loose` (branch `loose-rules`, tag `loose-v1`), `strict` (tag `strict-baseline`, the rules before the change), `noskill`. Same Haiku generator, 2 fix rounds, 5 moods x 1 brief (`bench/briefs_holdout_v3.json`, frozen before generation), 5 persona judges on Claude Sonnet.
- **Layout:** `loose_vs_noskill/` and `loose_vs_strict/` are standard bench folders; in `loose_vs_strict/` the `skill` side is **loose** and the `noskill` side is **strict** (the scorer's column names are reused). `python bench/score.py bench/runs/run10/<folder>` re-scores them.

## Results

| Comparison | Pairs won by loose | Votes won by loose | 95% CI | Note |
|---|---|---|---|---|
| loose vs noskill | 4 of 5 | 16/25 = 64% | 28% to 88% | p = 0.375 |
| **loose vs strict** | **1 of 5** | **7/25 = 28%** | 12% to 48% | strict won 4 pairs; Murat chose strict in 5 of 5 |

Content richness difference loose minus strict: -0.64; professional look: -0.56.

## Efficiency and automatic metrics (mean per page, n = 5)

| Arm | Tokens | Tool calls | Time (s) | Serious axe pages | Mean --check WARNs | Lines |
|---|---|---|---|---|---|---|
| noskill | 89,580 | 6.0 | 56 | 4/5 | 0.4 | 173 |
| strict | 105,426 | 15.0 | 102 | 0/5 | 0.0 | 226 |
| loose | 106,050 | 15.6 | 115 | 0/5 | 0.0 | 211 |

## Decision (rule written before the run)

Loose was to be accepted only if (1) it kept at least 45% of votes against strict with a CI covering 50%, (2) the accessibility metrics did not get worse, and (3) tokens or time per page fell by at least 20%.

- (1) failed: 28% of votes, CI 12% to 48%.
- (2) held: 0 serious axe pages, 0 WARNs.
- (3) failed: tokens +0.6%, time +13%. Loosening the rules did not make the agent cheaper.

**Outcome:** `main` keeps the strict rules (the loose commit was reverted; it stays on branch `loose-rules` and tag `loose-v1`).

## Caveats

- n = 5 pairs per comparison and one repetition, so neither direction is statistically significant (p = 0.375). The pre-registered rule is what decided it, not the p-value.
- "Loose" changed documents and audit severities together; this run cannot tell which part cost quality.
- Judges are Claude Sonnet personas. They repeatedly preferred the fuller pages with drawn illustrations and more content (strict pages are longer: 226 vs 211 lines), the same pattern as in earlier runs.
- Token, tool-call and time figures come from the generator agents' completion reports and are not shown per page here.
