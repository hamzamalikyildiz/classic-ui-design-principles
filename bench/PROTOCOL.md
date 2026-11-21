# Benchmark protocol (v2)

Question: does an agent that follows this skill produce better-looking, more accessible pages than the same agent without it?

## Design

- **Arms:** `skill` (reads SKILL.md, mood file, `reference/visual-quality.md`, and `reference/rules.md` when fixing findings; runs `audit` and `render.py --check`) vs `noskill` (renders and looks at a screenshot only). Same model, same brief, same fix-round budget (2).
- **Briefs:** 5 moods x 2 briefs (`--briefs r,m` default: `r` detailed, `m` second; an optional `v` vague brief is also available in `briefs.json`), 2 repetitions each = 20 pairs, 40 pages. Pages are independent generations.
- **Models:** generators and judges use cheap models (Haiku by default) so the run stays affordable; both arms always use the same one.
- **Judges:** 5 independent blind personas (`judges.json`: age 16 student, 34 senior designer, 63 retired teacher with low vision, 45 small-business owner, 27 skeptical front-end developer). Each sees all 20 pairs in its own random order with its own random A/B placement, never sees which arm is which, and scores four criteria 1-10 plus a forced choice with confidence 1-5.
- **Scoring (`score.py`):** vote-level win rate with a pair-cluster bootstrap 95% CI, per-pair majority with an exact sign test, per-judge and per-mood tables, mean score difference per criterion, plus automatic metrics (axe violations, `--check` warnings) that involve no model.

## Run it

```powershell
$py = "python"            # Python 3.10+ with: pip install playwright pillow ; python -m playwright install chromium
$work = "$env:TEMP\benchrun"
python bench/make_tasks.py $work --skill "<path to this repo>" --python $py       # writes tasks/*.txt
# for every file in $work/tasks run one agent: "Read <task file> and do exactly what it says."
python bench/build_pairs.py $work --checks --width 1000                            # pairs (1000px default) + automatic metrics
python bench/make_judge_sets.py $work                                              # 5 blind judge sets + prompts
# for every file in $work/judge_tasks run one agent: "Read <task file> and do exactly what it says."
python bench/score.py $work --md RESULTS.md
```

## Known limits

- Judges are language models role-playing personas, not people; they share biases (for example liking richer pages). Use the result to compare skill versions, not as proof of human preference.
- Cheap generators follow the skill less faithfully than stronger ones; the real gap may be larger or smaller.
- Fix-round budget is small on purpose; pages are not polished to a final state.
- 20 pairs detect a large effect, not a small one. Read the confidence interval, not just the win rate.
- Report skill version (git commit) with every result; `runs/<name>/` holds the HTML pages, task prompts, judge verdicts and maps for that run.
