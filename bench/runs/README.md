# Benchmark runs

- `run2/`: pilot, 10 pairs, one Sonnet judge, 1 fix round, Haiku generators. Indicative only.
- `run3/`: protocol v2 (see `../PROTOCOL.md`): 20 pairs, 5 persona judges, 2 fix rounds. `RESULTS.md` has the numbers and caveats; `skill/` and `noskill/` hold the generated pages; `verdicts/` and `maps/` let anyone re-score with `python bench/score.py`.
- `run4/`: cross-model v6 run (post-content-floor refactor, commit `577491a`): 15 pairs across all 3 brief types (`v,r,m`), Gemini 4 Hydrogen Low generators (2 fix rounds), 5 Gemini 4 Neon Medium persona judges (75 blind votes). See `run4/RESULTS.md`.
- `run5/`: targeted technical + editorial run, 12 pairs, Haiku generators, 5 Sonnet persona judges (technical 6/6, editorial 3/6).
- `run6/`: editorial re-run after reversing the figure rule, 6 pairs (editorial 5/6). Not independent of run5; see its caveats.
- `run7/`: **held-out validation**: 10 new briefs never used in runs 2-6, skill frozen before generation (`13ef373`), Haiku generators, 5 Sonnet persona judges: 76% of votes, 9/10 pairs, p = 0.0215.
- `run8/`: **held-out validation v2 (post-hardening)**: 6 brand-new unseen briefs (`briefs_holdout_v2.json`), skill frozen at `fc3a31b`, Gemini 4 Hydrogen Low generators, 5 Gemini 4 Neon Medium persona judges (uniform Turkish verdicts): **25/30 = 83%**, **6/6 pairs**, **p = 0.0312**, Nermin 5/6 (83%), Editorial 2/2, Technical 1/1.

## Which run to trust

| Run | Purpose | Trust |
|---|---|---|
| run2 | Pilot | Low (one judge) |
| run3 | First full run | Medium: strong result, but persona text was garbled by a Windows encoding bug and the skill was then changed |
| run4 | Cross-model run by a different tool | Medium: honest, not significant (p = 0.30) |
| run5, run6 | Targeted tuning of technical and editorial | Low as evidence: tuned on the judges' own reasons |
| run7 | Held-out validation (v1, n=10) | High: unseen briefs, frozen skill, significant (p = 0.0215) |
| run8 | Held-out validation (v2, n=6, post-hardening) | High (small sample): unseen briefs, frozen skill (`fc3a31b`), cross-family judges, near-matched line length (`260.8 vs 246.5`), p = 0.0312 |
