# Changelog

## Unreleased
- Tried a looser rule set (floor / defaults / ideas, style findings as INFO). The run10 trial did not keep quality against the strict rules and saved no tokens, so `main` keeps the strict rules; the experiment lives on branch `loose-rules` (see `bench/runs/run10`).
- Pinned npm tool versions, Chromium keeps its sandbox by default (`UITOOLS_NO_SANDBOX=1` or root opts out), `requirements.txt`, light install bundle (`package_skill.py`).

## v1.0.0
- Component, Page and App modes; five moods; static audit (`uitools.py`) and rendered checks (`render.py`); blind A/B benchmark with runs 2-9.
