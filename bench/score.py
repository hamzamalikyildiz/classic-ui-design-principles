#!/usr/bin/env python3
"""Tally blind multi-judge results.

    python3 bench/score.py <workdir> [--md RESULTS.md]

Reads <workdir>/judge_<id>.txt (or verdicts/judge_<id>.txt) per persona in judges.json and <workdir>/maps/MAP_<id>.json.
Judge lines look like: `cift3: A | 4 | reason | A 8/8/7/9 B 7/6/8/7`.
Reports: per-judge skill win rate, vote-level win rate with a pair-cluster bootstrap 95% CI, per-pair
majority wins with an exact two-sided sign test, per-mood rates, mean score differences per criterion,
and the automatic axe / --check metrics (metrics.json, KEY_DO_NOT_OPEN.json or page_key.json) when present.
"""
import argparse, json, math, pathlib, random, re, statistics

CRIT = ['visual appeal', 'professional look', 'hierarchy and readability', 'content richness']
LINE = re.compile(r'(cift\d+)\s*:\s*([AB])\b\s*\|\s*([1-5])\b\s*\|(.*)', re.I)
SCORES = re.compile(r'A\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*B\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', re.I)


def load_json(path):
    """Load JSON from a UTF-8 file."""
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def first_existing(*paths):
    """Return the first existing Path among candidates, or None."""
    return next((p for p in paths if p.exists()), None)


ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--md'); a = ap.parse_args()
W = pathlib.Path(a.work); H = pathlib.Path(__file__).resolve().parent
judges = load_json(H / 'judges.json')
votes = {}       # orig pair -> list of dict(judge, win, conf, diff)
per_judge = {}
moods = {}
for j in judges:
    f = first_existing(W / f'judge_{j["id"]}.txt', W / 'verdicts' / f'judge_{j["id"]}.txt')
    mf = W / 'maps' / f'MAP_{j["id"]}.json'
    if f is None or not mf.exists(): continue
    mp = load_json(mf); seen = set(); w = n = 0
    for m in LINE.finditer(f.read_text(encoding='utf-8-sig')):
        k = m.group(1).lower()
        if k not in mp or k in seen: continue
        seen.add(k); v = mp[k]; win = m.group(2).upper() == v['skill']
        diff = None
        s = SCORES.search(m.group(4))
        if s:
            x = [int(t) for t in s.groups()]; a_, b_ = x[:4], x[4:]
            sk, ns = (a_, b_) if v['skill'] == 'A' else (b_, a_)
            diff = [p - q for p, q in zip(sk, ns)]
        votes.setdefault(v['orig'], []).append({'judge': j['id'], 'win': win, 'conf': int(m.group(3)), 'diff': diff})
        moods[v['orig']] = v['mood']; w += win; n += 1
    per_judge[j['id']] = (w, n, len(mp))

allv = [x for vs in votes.values() for x in vs]
if not allv: raise SystemExit('no judge verdicts found')
N, WIN = len(allv), sum(x['win'] for x in allv)


def boot(votes, reps=4000, seed=1):
    rnd = random.Random(seed); keys = list(votes); res = []
    for _ in range(reps):
        w = n = 0
        for k in (rnd.choice(keys) for _ in keys):
            w += sum(x['win'] for x in votes[k]); n += len(votes[k])
        res.append(w / n)
    res.sort(); return res[int(.025 * reps)], res[int(.975 * reps)]


def sign_p(w, n):
    if n == 0: return 1.0
    k = max(w, n - w); p = math.ldexp(sum(math.comb(n, i) for i in range(k, n + 1)), -n)
    return min(1.0, 2 * p)


lo, hi = boot(votes)
maj = {k: sum(x['win'] for x in vs) / len(vs) for k, vs in votes.items()}
mw = sum(1 for v in maj.values() if v > .5); ml = sum(1 for v in maj.values() if v < .5); mt = len(maj) - mw - ml
out = ['# Blind A/B results', '',
       f'Pairs: {len(votes)}, judges: {len(per_judge)}, votes: {N}.', '',
       f'**Skill win rate (all votes): {WIN}/{N} = {100 * WIN / N:.0f}%**, pair-cluster bootstrap 95% CI {100 * lo:.0f}% to {100 * hi:.0f}%.', '',
       f'Per-pair majority: skill wins {mw}, no-skill wins {ml}, ties {mt}; exact sign test p = {sign_p(mw, mw + ml):.4f}.', '',
       '## Per judge', '', '| Judge | Skill wins | Votes |', '|---|---|---|']
names = {j['id']: f'{j["name"]} ({j["age"]})' for j in judges}
for jid, (w, n, tot) in per_judge.items():
    out.append(f'| {names[jid]} | {w}/{n} = {100 * w / max(n, 1):.0f}% | {n} of {tot} |')
out += ['', '## Per mood (majority per pair)', '', '| Mood | Pairs | Skill majority wins |', '|---|---|---|']
bymood = {}
for k, v in maj.items(): bymood.setdefault(moods[k], []).append(v)
for m, vs in sorted(bymood.items()):
    out.append(f'| {m} | {len(vs)} | {sum(1 for v in vs if v > .5)}/{len(vs)} |')
ds = [x['diff'] for x in allv if x['diff']]
if ds:
    out += ['', '## Mean score difference, skill minus no-skill (1-10 scale)', '', '| Criterion | Mean diff |', '|---|---|']
    for i, c in enumerate(CRIT): out.append(f'| {c} | {statistics.mean(d[i] for d in ds):+.2f} |')
hi_conf = [x for x in allv if x['conf'] >= 4]
if hi_conf: out += ['', f'High-confidence votes only (conf >= 4): skill wins {sum(x["win"] for x in hi_conf)}/{len(hi_conf)}.']
kp = first_existing(W / 'KEY_DO_NOT_OPEN.json', W / 'page_key.json')
mpth = W / 'metrics.json'
if kp is not None and mpth.exists():
    key, met = load_json(kp), load_json(mpth)
    out += ['', '## Automatic metrics (no model involved)', '', '| Arm | Pages | Pages with serious axe issue | Mean --check WARNs |', '|---|---|---|---|']
    for arm in ('skill', 'noskill'):
        ks = [k for k, v in key.items() if v['arm'] == arm]
        cw = [met[k]['check_warns'] for k in ks if k in met and 'check_warns' in met[k]]
        serious = sum(1 for k in ks if met.get(k, {}).get('axe_serious', 0))
        out.append(f'| {arm} | {len(ks)} | {serious} | {statistics.mean(cw):.1f} |' if cw else
                   f'| {arm} | {len(ks)} | {serious} | n/a |')
text = '\n'.join(out); print(text)
if a.md: pathlib.Path(a.md).write_text(text + '\n', encoding='utf-8')
