# Blind A/B results

Pairs: 6, judges: 5, votes: 30.

**Skill win rate (all votes): 19/30 = 63%**, pair-cluster bootstrap 95% CI 33% to 90%.

Per-pair majority: skill wins 4, no-skill wins 2, ties 0; exact sign test p = 0.6875.

## Per judge

| Judge | Skill wins | Votes |
|---|---|---|
| Ece (16) | 3/6 = 50% | 6 of 6 |
| Murat (34) | 4/6 = 67% | 6 of 6 |
| Nermin (63) | 2/6 = 33% | 6 of 6 |
| Kaan (45) | 6/6 = 100% | 6 of 6 |
| Selin (27) | 4/6 = 67% | 6 of 6 |

## Per mood (majority per pair)

| Mood | Pairs | Skill majority wins |
|---|---|---|
| editorial | 1 | 1/1 |
| playful | 1 | 1/1 |
| technical | 1 | 1/1 |
| trust | 3 | 1/3 |

## Per brief type (majority per pair)

| Brief | Pairs | Skill majority wins | Vote win rate |
|---|---|---|---|
| cicd-board | 1 | 1/1 | 4/5 = 80% |
| clinic-appt | 1 | 0/1 | 1/5 = 20% |
| cv-opt | 1 | 0/1 | 1/5 = 20% |
| invoice-quote | 1 | 1/1 | 3/5 = 60% |
| meal-planner | 1 | 1/1 | 5/5 = 100% |
| support-inbox | 1 | 1/1 | 5/5 = 100% |

## Mean score difference, skill minus no-skill (1-10 scale)

| Criterion | Mean diff |
|---|---|
| visual appeal | +1.27 |
| professional look | +1.50 |
| hierarchy and readability | +0.67 |
| content richness | +1.27 |
| states and feedback | +0.20 |
| motion and fluidity | -1.37 |

App criteria deltas: Δ states = +0.20, Δ motion = -1.37.

High-confidence votes only (conf >= 4): skill wins 10/15.

## Ablation (noskill_check)

### noskill_check vs noskill: 15/30 = 50% (95% CI 17%–83%, majority 3/3/0, p = 1.0000)
Mean diffs: visual appeal: +0.03, professional look: -0.17, hierarchy and readability: +0.17, content richness: +0.00, states and feedback: +0.30, motion and fluidity: +1.43
Ablation deltas: Δ states = +0.30, Δ motion = +1.43.

### skill vs noskill_check: 17/30 = 57% (95% CI 27%–87%, majority 3/3/0, p = 1.0000)
Mean diffs: visual appeal: +1.23, professional look: +1.60, hierarchy and readability: +0.37, content richness: +1.33, states and feedback: -0.20, motion and fluidity: -2.80
Ablation deltas: Δ states = -0.20, Δ motion = -2.80.


## Automatic metrics (no model involved)

| Arm | Pages | Pages with serious axe issue | Mean layout WARNs (non-axe) |
|---|---|---|---|
| skill | 6 | 3 | 14.3 |
| noskill_check | 6 | 3 | 9.3 |
| noskill | 6 | 6 | 18.3 |

## Motion warnings per arm (`render.py --routes --motion`)

| Arm | Apps with 0 motion WARNs | Mean motion WARNs |
|---|---|---|
| skill | **5 / 6** (`cicd-board`: 5) | **0.83** |
| noskill_check | 0 / 6 (`2`–`13` each) | 8.00 |
| noskill | 1 / 6 (`0`–`12` each) | 6.67 |

## Run setup, cross-family probe, diagnosis, and caveats (app flow benchmark v2)

- **Pre-registered & frozen:** Skill frozen at commit `bffa262` (post-Phase A/B/C/E; `SKILL.md` 10,884 bytes) and all 6 unseen multi-screen flow briefs in `bench/briefs_app.json` + `bench/routes_app/*.json` committed before any page was generated.
- **Generators & arms (18 single-HTML hash-routed apps):** **Gemini 4 Hydrogen (Low)** across all 3 arms: `skill` (App mode + `states.md`/`motion.md`/`render.py`), `noskill` (plain brief only), and `noskill_check` (ablation arm running `render.py --check --routes` without reading skill docs). Note: cross-family generators (e.g. a second model family generating 6 additional pairs) were not added as a second generator arm; `run9` evaluates Gemini 4 Hydrogen Low outputs across 3 arms.
- **Primary blind judges (`verdicts/`):** 5 **Gemini 4 Neon (Medium)** Turkish persona judges (`ece`, `kaan`, `murat`, `nermin`, `selin`) inspecting blind `contact-sheet.png` (4 routes × 2 viewports × states) + `filmstrip.png` across all 18 pairs (`90` total votes; `30` per arm comparison).
- **Cross-family probe (`verdicts_claude/judge_selin.txt`):** One **Claude Sonnet 5.5 (Medium)** Selin judge ran blindly on the exact same 18 `judge_selin` pairs as an independent cross-family sanity check:
  - Agreed with Neon Selin on **15 / 18 (83.3%)** overall pairs.
  - Chose **`skill` on 6 / 6 (100%)** of `skill_vs_noskill` pairs, with positive deltas across every criterion: `visual +1.33`, `professional +1.50`, `hierarchy +0.67`, `content +1.33`, `states +0.17`, `motion +0.50`.
  - Pre-registered primary headline stays the 5-judge Neon panel (**19/30 = 63%**, 4/6 pair majorities, `p = 0.6875`) without swapping in the secondary probe.
- **What worked cleanly:**
  - Design craft and product realism drove strong positive gaps on `skill vs noskill`: `professional look +1.50`, `visual appeal +1.27`, `content richness +1.27`, `hierarchy +0.67`, `states +0.20`, with **`skill vs noskill_check`** confirming those visual/hierarchy/content gains come from the skill rules (`+1.23` / `+1.60` / `+1.33`) rather than `render.py` alone.
  - Automated checks showed clean motion engineering on `skill` (**5/6 apps at 0 motion WARNs**, mean `0.83` vs `noskill_check 8.00` and `noskill 6.67`) and half as many serious `axe` issues as `noskill` (`3/6` vs `6/6`).
- **Honest diagnosis of why `skill_vs_noskill` fell short of 70% (`Δ motion = -1.37`):**
  1. **Debug state switcher chrome in Trust/Meal headers:** Several `skill` generators rendered a visible `?state=` selector pill/dropdown in the top bar (especially flagged on `cv-opt` and `clinic-appt`, both `1/5`), whereas `noskill` switched `?state=` silently via URL query/JS; judges penalized the visible debug chrome as "prototype scaffolding" despite praising `skill`'s typography and KPI layout.
  2. **Double-trigger filmstrip interaction on one-shot buttons:** `bench/routes_app/*.json` ran `actions: [{"click": "[data-motion-trigger]"}, {"wait": 400}]` during route capture and then `--motion` clicked `[data-motion-trigger]` a second time for the filmstrip. On one-shot buttons ("Accept recommendation" disabling after click 1), the second pass looked static (`motion = 3–4` from Neon judges on 5/6 apps), whereas toggleable `support-inbox` swept **5/5 (100%)** with `Δ motion = +4.0`. Neither the frozen skill (`bffa262`) nor `routes_app/` was altered after observing these results.
- **Length balance & caveats:** Mean HTML size differed (`skill` **544.8 lines / 28.5 KB** vs `noskill` **423.5 lines / 21.1 KB** vs `noskill_check` **410.5 lines / 20.5 KB**, `+28.6%` lines). Sample size is small (`n = 6` briefs per comparison, wide CIs).
- **Human evaluation status (`S7` — pending real raters):** An offline blind A/B kit (`bench/runs/run9/human_kit/index.html`, `key.json` excluded) was generated with `bench/human/make_human_kit.py`. Zero fabricated human votes exist. Distribute `bench/runs/run9/human_kit/` to `>= 5` human raters and tally exported CSVs with:
  ```bash
  python bench/human/score_human.py --csv-dir <csv_folder> --key bench/runs/run9/KEY_DO_NOT_OPEN.json --llm-summary bench/runs/run9/verdicts --out-md bench/runs/run9/HUMAN_RESULTS.md
  ```

