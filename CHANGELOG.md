# Changelog

## Unreleased
- Rules split into a short **floor** (accessibility and broken layout) and softer **defaults**; most style audit findings become INFO, `--strict` keeps the old severities. See `PLAN-esnek-kurallar.md`.
- Pinned npm tool versions, Chromium keeps its sandbox by default (`UITOOLS_NO_SANDBOX=1` or root opts out), `requirements.txt`, light install bundle (`package_skill.py`).

## v1.0.0
- Component, Page and App modes; five moods; static audit (`uitools.py`) and rendered checks (`render.py`); blind A/B benchmark with runs 2-9.
