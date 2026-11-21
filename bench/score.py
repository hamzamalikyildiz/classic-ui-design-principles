#!/usr/bin/env python3
"""Tally blind multi-judge results.

    python3 bench/score.py <workdir> [--md RESULTS.md]

Reads <workdir>/judge_<id>.txt (or verdicts/judge_<id>.txt) per persona in judges.json and <workdir>/maps/MAP_<id>.json.
Auto-detects both 4-criterion (page mode: `A 8/8/7/9 B 7/6/8/7`) and 6-criterion (app mode: `A 8/8/7/9/8/7 B 7/6/8/7/5/6`)
verdict lines, reports Δ states / Δ motion when 6 criteria are present, and reports noskill_check ablation pairs when present.
"""
import argparse, json, math, pathlib, random, re, statistics, sys

CRIT_4 = ['visual appeal', 'professional look', 'hierarchy and readability', 'content richness']
CRIT_6 = CRIT_4 + ['states and feedback', 'motion and fluidity']
CRIT = CRIT_4  # kept for backward-compatible imports

LINE = re.compile(r'(cift\d+)\s*:\s*([AB])\b\s*\|\s*([1-5])\b\s*\|(.*)', re.I)
SCORES_6 = re.compile(
    r'A\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*'
    r'B\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',
    re.I,
)
SCORES_4 = re.compile(
    r'A\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*'
    r'B\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',
    re.I,
)
SCORES = SCORES_4  # kept for backward-compatible imports


def load_json(path):
    """Load JSON from a UTF-8 file."""
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def first_existing(*paths):
    """Return the first existing Path among candidates, or None."""
    return next((p for p in paths if p.exists()), None)


def parse_score_pair(text):
    """Parse 6-criterion or 4-criterion A/B scores from verdict trailing text; return (a_scores, b_scores) or None."""
    s6 = SCORES_6.search(text)
    if s6:
        x = [int(t) for t in s6.groups()]
        return x[:6], x[6:]
    s4 = SCORES_4.search(text)
    if s4:
        x = [int(t) for t in s4.groups()]
        return x[:4], x[4:]
    return None


def boot(votes, reps=4000, seed=1):
    """Pair-cluster bootstrap 95% CI for vote-level win rate."""
    rnd = random.Random(seed)
    keys = sorted(votes)
    res = []
    for _ in range(reps):
        w = n = 0
        for k in (rnd.choice(keys) for _ in keys):
            w += sum(x['win'] for x in votes[k])
            n += len(votes[k])
        res.append(w / n)
    res.sort()
    return res[int(.025 * (reps - 1))], res[int(.975 * (reps - 1))]


def sign_p(w, n):
    """Exact two-sided binomial sign test p-value."""
    if n == 0:
        return 1.0
    k = max(w, n - w)
    p = math.ldexp(sum(math.comb(n, i) for i in range(k, n + 1)), -n)
    return min(1.0, 2 * p)


def _pair_arms(v):
    """Return (arm_a, arm_b, focal_arm, other_arm, focal_side, comparison) for a MAP entry."""
    if 'arm_a' in v and 'arm_b' in v:
        arm_a, arm_b = v['arm_a'], v['arm_b']
        if 'skill' in (arm_a, arm_b):
            focal_arm = 'skill'
            other_arm = arm_b if arm_a == 'skill' else arm_a
            focal_side = 'A' if arm_a == 'skill' else 'B'
        else:
            focal_side = v.get('focal') or 'A'
            focal_arm = arm_a if focal_side == 'A' else arm_b
            other_arm = arm_b if focal_side == 'A' else arm_a
        comp = v.get('comparison') or f'{focal_arm}_vs_{other_arm}'
        return arm_a, arm_b, focal_arm, other_arm, focal_side, comp

    sk_side = v['skill']
    arm_a = 'skill' if sk_side == 'A' else 'noskill'
    arm_b = 'noskill' if sk_side == 'A' else 'skill'
    return arm_a, arm_b, 'skill', 'noskill', sk_side, 'skill_vs_noskill'


def _load_page_key(workdir):
    """Load page key dict (pid -> {arm, ...}) from KEY_DO_NOT_OPEN.json, key.json, or page_key.json."""
    kp = first_existing(workdir / 'KEY_DO_NOT_OPEN.json', workdir / 'key.json', workdir / 'page_key.json')
    if kp is None:
        return None
    raw = load_json(kp)
    if isinstance(raw, dict) and 'pages' in raw and isinstance(raw['pages'], dict):
        return raw['pages']
    return raw


def _criteria_names(diffs):
    """Return CRIT_6 if any parsed score diff has 6 criteria, otherwise CRIT_4."""
    if any(len(d) >= 6 for d in diffs):
        return CRIT_6
    return CRIT_4


def score_run(workdir, md_path=None):
    """Score a benchmark workdir and return the formatted Markdown report string."""
    W = pathlib.Path(workdir)
    H = pathlib.Path(__file__).resolve().parent
    judges = load_json(H / 'judges.json')

    by_comp_votes = {}   # comparison -> {orig_pair: [vote_dict, ...]}
    by_comp_meta = {}    # comparison -> {'focal': ..., 'other': ...}
    per_judge_primary = {}
    per_judge_all = {}
    moods = {}
    briefs = {}

    for j in judges:
        f = first_existing(W / f'judge_{j["id"]}.txt', W / 'verdicts' / f'judge_{j["id"]}.txt')
        mf = W / 'maps' / f'MAP_{j["id"]}.json'
        if f is None or not mf.exists():
            continue
        mp = load_json(mf)
        seen = set()
        pw = pn = ptot = 0
        aw = an = atot = 0
        for v in mp.values():
            _, _, _, _, _, comp = _pair_arms(v)
            atot += 1
            if comp == 'skill_vs_noskill':
                ptot += 1

        for ln_no, raw_ln in enumerate(f.read_text(encoding='utf-8-sig').splitlines(), 1):
            line = raw_ln.strip()
            if not line:
                continue
            m = LINE.search(line)
            if not m:
                print(f'warning: unparsed line in {f.name}:{ln_no}: {line[:80]}', file=sys.stderr)
                continue
            k = m.group(1).lower()
            if k not in mp or k in seen:
                continue
            seen.add(k)
            v = mp[k]
            _, _, focal_arm, other_arm, focal_side, comp = _pair_arms(v)
            choice = m.group(2).upper()
            win = choice == focal_side
            diff = None
            parsed_scores = parse_score_pair(m.group(4))
            if parsed_scores is not None:
                a_, b_ = parsed_scores
                foc, oth = (a_, b_) if focal_side == 'A' else (b_, a_)
                diff = [p - q for p, q in zip(foc, oth)]

            vote = {'judge': j['id'], 'win': win, 'conf': int(m.group(3)), 'diff': diff}
            by_comp_votes.setdefault(comp, {}).setdefault(v['orig'], []).append(vote)
            by_comp_meta[comp] = (focal_arm, other_arm)
            moods[v['orig']] = v['mood']
            if 'brief' in v:
                briefs[v['orig']] = v['brief']
            aw += win
            an += 1
            if comp == 'skill_vs_noskill':
                pw += win
                pn += 1
        per_judge_primary[j['id']] = (pw, pn, ptot)
        per_judge_all[j['id']] = (aw, an, atot)

    if not by_comp_votes:
        raise SystemExit('no judge verdicts found')

    if 'skill_vs_noskill' in by_comp_votes:
        primary_comp = 'skill_vs_noskill'
        per_judge = per_judge_primary
    else:
        primary_comp = next(iter(by_comp_votes))
        per_judge = per_judge_all

    votes = by_comp_votes[primary_comp]
    focal_label, other_label = by_comp_meta[primary_comp]
    other_pretty = 'no-skill' if other_label == 'noskill' else other_label
    focal_title = 'Skill' if focal_label == 'skill' else focal_label

    allv = [x for vs in votes.values() for x in vs]
    if not allv:
        raise SystemExit('no judge verdicts found')
    N, WIN = len(allv), sum(x['win'] for x in allv)

    lo, hi = boot(votes)
    maj = {k: sum(x['win'] for x in vs) / len(vs) for k, vs in votes.items()}
    mw = sum(1 for v in maj.values() if v > .5)
    ml = sum(1 for v in maj.values() if v < .5)
    mt = len(maj) - mw - ml
    pval = sign_p(mw, mw + ml)
    pstr = '< 0.0001' if pval < 0.0001 else f'= {pval:.4f}'

    out = [
        '# Blind A/B results',
        '',
        f'Pairs: {len(votes)}, judges: {len(per_judge)}, votes: {N}.',
        '',
        f'**{focal_title} win rate (all votes): {WIN}/{N} = {100 * WIN / N:.0f}%**, pair-cluster bootstrap 95% CI {100 * lo:.0f}% to {100 * hi:.0f}%.',
        '',
        f'Per-pair majority: {focal_label} wins {mw}, {other_pretty} wins {ml}, ties {mt}; exact sign test p {pstr}.',
        '',
        '## Per judge',
        '',
        f'| Judge | {focal_title} wins | Votes |',
        '|---|---|---|',
    ]
    names = {j['id']: f'{j["name"]} ({j["age"]})' for j in judges}
    for jid, (w, n, tot) in per_judge.items():
        out.append(f'| {names[jid]} | {w}/{n} = {100 * w / max(n, 1):.0f}% | {n} of {tot} |')

    out += ['', '## Per mood (majority per pair)', '', f'| Mood | Pairs | {focal_title} majority wins |', '|---|---|---|']
    bymood = {}
    for k, v in maj.items():
        bymood.setdefault(moods[k], []).append(v)
    for m, vs in sorted(bymood.items()):
        out.append(f'| {m} | {len(vs)} | {sum(1 for v in vs if v > .5)}/{len(vs)} |')

    bybrief = {}
    for k in maj:
        if k in briefs:
            bybrief.setdefault(briefs[k], []).append(k)
    if len(bybrief) > 1:
        out += ['', '## Per brief type (majority per pair)', '', f'| Brief | Pairs | {focal_title} majority wins | Vote win rate |', '|---|---|---|---|']
        for b, ks in sorted(bybrief.items()):
            bw = sum(x['win'] for k in ks for x in votes[k])
            bn = sum(len(votes[k]) for k in ks)
            bm = sum(1 for k in ks if maj[k] > .5)
            out.append(f'| {b} | {len(ks)} | {bm}/{len(ks)} | {bw}/{bn} = {100 * bw / max(bn, 1):.0f}% |')

    ds = [x['diff'] for x in allv if x['diff']]
    if ds:
        crit_names = _criteria_names(ds)
        out += ['', f'## Mean score difference, {focal_label} minus {other_pretty} (1-10 scale)', '', '| Criterion | Mean diff |', '|---|---|']
        for i, c in enumerate(crit_names):
            vals = [d[i] for d in ds if len(d) > i]
            if vals:
                out.append(f'| {c} | {statistics.mean(vals):+.2f} |')
        if len(crit_names) >= 6:
            d_states = statistics.mean(d[4] for d in ds if len(d) > 4)
            d_motion = statistics.mean(d[5] for d in ds if len(d) > 5)
            out += ['', f'App criteria deltas: Δ states = {d_states:+.2f}, Δ motion = {d_motion:+.2f}.']

    hi_conf = [x for x in allv if x['conf'] >= 4]
    if hi_conf:
        out += ['', f'High-confidence votes only (conf >= 4): {focal_label} wins {sum(x["win"] for x in hi_conf)}/{len(hi_conf)}.']

    # Report any ablation comparisons (e.g. skill vs noskill_check, noskill_check vs noskill)
    ablation_comps = [c for c in by_comp_votes if c != primary_comp]
    if ablation_comps:
        out += ['', '## Ablation (noskill_check)', '']
        for comp in ablation_comps:
            cvotes = by_comp_votes[comp]
            f_arm, o_arm = by_comp_meta[comp]
            callv = [x for vs in cvotes.values() for x in vs]
            cn, cw = len(callv), sum(x['win'] for x in callv)
            clo, chi = boot(cvotes)
            cmaj = {k: sum(x['win'] for x in vs) / len(vs) for k, vs in cvotes.items()}
            cmw = sum(1 for v in cmaj.values() if v > .5)
            cml = sum(1 for v in cmaj.values() if v < .5)
            cmt = len(cmaj) - cmw - cml
            cpval = sign_p(cmw, cmw + cml)
            cpstr = '< 0.0001' if cpval < 0.0001 else f'= {cpval:.4f}'
            out.append(
                f'### {f_arm} vs {o_arm}: {cw}/{cn} = {100 * cw / max(cn, 1):.0f}% '
                f'(95% CI {100 * clo:.0f}%–{100 * chi:.0f}%, majority {cmw}/{cml}/{cmt}, p {cpstr})'
            )
            cds = [x['diff'] for x in callv if x['diff']]
            if cds:
                ccrit = _criteria_names(cds)
                parts = []
                for i, c in enumerate(ccrit):
                    vals = [d[i] for d in cds if len(d) > i]
                    if vals:
                        parts.append(f'{c}: {statistics.mean(vals):+.2f}')
                out.append('Mean diffs: ' + ', '.join(parts))
                if len(ccrit) >= 6:
                    ds_val = statistics.mean(d[4] for d in cds if len(d) > 4)
                    dm_val = statistics.mean(d[5] for d in cds if len(d) > 5)
                    out.append(f'Ablation deltas: Δ states = {ds_val:+.2f}, Δ motion = {dm_val:+.2f}.')
            out.append('')

    key = _load_page_key(W)
    mpth = W / 'metrics.json'
    if key is not None and mpth.exists():
        met = load_json(mpth)
        has_layout = any('layout_warns' in met.get(k, {}) for k in key)
        warn_hdr = 'Mean layout WARNs (non-axe)' if has_layout else 'Mean --check WARNs'
        out += ['', '## Automatic metrics (no model involved)', '', f'| Arm | Pages | Pages with serious axe issue | {warn_hdr} |', '|---|---|---|---|']
        arms_in_key = {v['arm'] for v in key.values() if isinstance(v, dict) and 'arm' in v}
        arms = ('skill', 'noskill_check', 'noskill') if 'noskill_check' in arms_in_key else ('skill', 'noskill')
        for arm in arms:
            ks = [k for k, v in key.items() if v['arm'] == arm]
            axe_vals = [met[k]['axe_serious'] for k in ks if k in met and met[k].get('axe_serious') is not None]
            serious_str = str(sum(1 for v in axe_vals if v)) if axe_vals else 'n/a'
            cw = [met[k]['layout_warns'] if 'layout_warns' in met[k] else met[k]['check_warns']
                  for k in ks if k in met and ('layout_warns' in met[k] or 'check_warns' in met[k])]
            out.append(f'| {arm} | {len(ks)} | {serious_str} | {statistics.mean(cw):.1f} |' if cw else
                       f'| {arm} | {len(ks)} | {serious_str} | n/a |')

    text = '\n'.join(out)
    if md_path:
        pathlib.Path(md_path).write_text(text + '\n', encoding='utf-8')
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--md')
    a = ap.parse_args(argv)
    text = score_run(a.work, md_path=a.md)
    print(text)


if __name__ == '__main__':
    main()
