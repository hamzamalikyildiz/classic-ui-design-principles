#!/usr/bin/env python3
"""Tally blind judgments.  python3 bench/score.py <workdir> <judge1.txt> [<judge2.txt> ...]
Judge files contain lines like `cift3: A | 4 | reason`. Prints skill win rate overall and per mood, plus axe/check metrics."""
import json, pathlib, re, sys
W = pathlib.Path(sys.argv[1]); pm = json.load(open(W / 'PAIR_MAP_DO_NOT_OPEN.json'))
votes = {k: [] for k in pm}
for f in sys.argv[2:]:
    for m in re.finditer(r'(cift\d+)\W+([AB])\b', pathlib.Path(f).read_text(), re.I):
        if m.group(1).lower() in votes: votes[m.group(1).lower()].append(m.group(2).upper())
tot = win = 0; mood = {}
for k, v in pm.items():
    for x in votes[k]:
        tot += 1; w = int(x == v['skill']); win += w
        mood.setdefault(v['mood'], [0, 0]); mood[v['mood']][0] += w; mood[v['mood']][1] += 1
print(f"skill wins {win}/{tot} = {100 * win / max(tot, 1):.0f}%")
for m, (w, t) in sorted(mood.items()): print(f"  {m:10s} {w}/{t} = {100 * w / t:.0f}%")
mp = W / 'metrics.json'
if mp.exists():
    key = json.load(open(W / 'KEY_DO_NOT_OPEN.json')); met = json.load(open(mp))
    for arm in ('skill', 'noskill'):
        ks = [k for k, v in key.items() if v['arm'] == arm]
        print(f"{arm}: axe serious pages {sum(1 for k in ks if met[k]['axe_serious'])}/{len(ks)}" +
              (f", mean --check WARNs {sum(met[k].get('check_warns', 0) for k in ks) / len(ks):.1f}" if 'check_warns' in met[ks[0]] else ''))
