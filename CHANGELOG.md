# Changelog

## Unreleased
- v2.1 hardening & DX pass: plain-CSS `oklch`/`var()` contrast resolution, automatic Tailwind v4 palette fallback, App Router `layout.tsx` wrapping and `.vue`/`.svelte` route composition, child-component `uitools-ignore` propagation, safe isolated `interact.js` probing, full-width mobile tap-target check, offline Tailwind v4 shorthand normalization, one-shot `scripts/verify.py` (`audit` + `render --check [--motion]` with `--format text|json` and `--fail-on none|fail|warn`), `package_skill.py --flat` for root-level marketplace zips, `<skill_dir>/scripts/` path resolution guidance, and the brownfield refactor workflow (`reference/app-flow.md` §6).
- Issue #2 (omerkurt1): `render.py --require-axe` and explicit `axe-not-run`/`axe-error` findings (a skipped accessibility check can no longer look like a pass); `scripts/e2e_gate.py` with an expected-findings check for the flawed demo and a baseline regression check for the polished example, wired into `app-e2e.yml`; one motion property policy (preferred / allowed with conditions / avoid) with a fixture test; Hick and Miller treated as starting sizes (the `miller-7` audit finding is INFO); run8 wording corrected from cross-family to cross-model.
- Tried a looser rule set (floor / defaults / ideas, style findings as INFO). The run10 trial did not keep quality against the strict rules and saved no tokens, so `main` keeps the strict rules; the experiment lives on branch `loose-rules` (see `bench/runs/run10`).
- Pinned npm tool versions, Chromium keeps its sandbox by default (`UITOOLS_NO_SANDBOX=1` or root opts out), `requirements.txt`, light install bundle (`package_skill.py`).

## v1.0.0
- Component, Page and App modes; five moods; static audit (`uitools.py`) and rendered checks (`render.py`); blind A/B benchmark with runs 2-9.
