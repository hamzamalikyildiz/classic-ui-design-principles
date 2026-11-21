#!/usr/bin/env python3
"""Build blind A/B pairs from raw/{skill,noskill}/<mood>-<brief>-<rep>.html.

    python3 bench/build_pairs.py <workdir> [--seed N] [--checks]

Writes <workdir>/judge/ciftN-{A,B}-K.png (1000px wide crops), pairs/*.html, PAIR_MAP_DO_NOT_OPEN.json
(placement; skill is A in half of each mood's pairs) and metrics.json (axe serious violations; --checks adds
non-axe layout WARN counts). Judges see only the judge/ crops.
"""
import argparse, json, pathlib, random, re, shutil, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import render as R
from playwright.sync_api import sync_playwright
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--checks', action='store_true'); ap.add_argument('--width', type=int, default=1000)
ap.add_argument('--offline', action='store_true', help='force local Tailwind compilation and font inlining'); a = ap.parse_args()
W = pathlib.Path(a.work); random.seed(a.seed)
files = sorted(f for f in (W / 'raw').glob('*/*.html') if not f.name.startswith('.'))
ids = random.sample(range(1000, 9999), len(files))
key, metrics = {}, {}
if (W / 'judge').exists():
    shutil.rmtree(W / 'judge')
for d in ('anon', 'shots', 'pairs', 'judge'):
    (W / d).mkdir(exist_ok=True)
tw_offline = a.offline or not R.reachable('https://cdn.tailwindcss.com')
gf_offline = a.offline or not R.reachable('https://fonts.googleapis.com/css2?family=Inter')
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=R.chrome_path() or None, args=['--no-sandbox'])
    for f, i in zip(files, ids):
        arm = f.parent.name; mood, brief, rep = f.stem.rsplit('-', 2)
        html = re.sub(r'<!--.*?-->', '', f.read_text(encoding='utf-8'), flags=re.S)
        pid = f'p{i}'; (W / 'anon' / f'{pid}.html').write_text(html, encoding='utf-8')
        if R.CDN.search(html) and tw_offline: html = R.compile_tailwind(html)
        if R.GFONTS.search(html) and gf_offline: html = R.inline_fonts(html)
        tmp = W / 'anon' / f'.{pid}.render.html'; tmp.write_text(html, encoding='utf-8')
        pg = br.new_page(viewport={'width': 1440, 'height': 900})
        try:
            pg.goto(tmp.as_uri()); pg.wait_for_timeout(500)
            pg.evaluate("async()=>{const h=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight);for(let y=0;y<h;y+=600){scrollTo({top:y,behavior:'instant'});await new Promise(r=>setTimeout(r,60))}scrollTo({top:0,behavior:'instant'})}")
            pg.wait_for_timeout(600); pg.screenshot(path=str(W / 'shots' / f'{pid}.png'), full_page=True)
            ax = R.run_axe(pg)
        finally:
            pg.close(); tmp.unlink(missing_ok=True)
        key[pid] = {'arm': arm, 'mood': mood, 'brief': brief, 'rep': rep}
        axe_missing = any(r == 'axe' and 'unavailable' in m for _, r, m in ax)
        metrics[pid] = {'axe_serious': None if axe_missing else sum(1 for s, r, m in ax if s == 'WARN')}
        if a.checks:
            tmp_png = W / 'anon' / '_b.png'
            try:
                res = subprocess.run(
                    [sys.executable, str(HERE.parent / 'scripts/render.py'), str(W / 'anon' / f'{pid}.html'), '--out', str(tmp_png), '--check'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace'
                )
            finally:
                tmp_png.unlink(missing_ok=True)
            if res.returncode != 0:
                print(f'warning: render.py --check failed for {pid}: {res.stderr.strip()}', file=sys.stderr)
            else:
                non_axe = len(re.findall(r'^\s*\[WARN\]\s+(?!axe-)', res.stdout, re.M))
                metrics[pid]['layout_warns'] = non_axe
                metrics[pid]['check_warns'] = non_axe
    br.close()
inv = {(v['arm'], v['mood'], v['brief'], v['rep']): k for k, v in key.items()}
groups = {}
for (arm, mood, brief, rep) in sorted(inv):
    other = 'noskill' if arm == 'skill' else 'skill'
    if (other, mood, brief, rep) not in inv:
        print(f'warning: unpaired page dropped: {arm}/{mood}-{brief}-{rep}', file=sys.stderr)
        continue
    if arm == 'skill':
        groups.setdefault(mood, []).append((brief, rep))
pm, n = {}, 0
order = [(m, b, r) for m, lst in groups.items() for b, r in lst]; random.shuffle(order)
placement = {}
for m, lst in groups.items():
    flags = ([True, False] * len(lst))[:len(lst)]; random.shuffle(flags)
    for (b, r), fl in zip(lst, flags): placement[(m, b, r)] = fl
for m, b, r in order:
    n += 1; sk, ns = inv[('skill', m, b, r)], inv[('noskill', m, b, r)]
    A, B = (sk, ns) if placement[(m, b, r)] else (ns, sk)
    pm[f'cift{n}'] = {'A': A, 'B': B, 'skill': 'A' if placement[(m, b, r)] else 'B', 'mood': m, 'brief': b, 'rep': r}
    for side, pid in (('A', A), ('B', B)):
        shutil.copy(W / 'anon' / f'{pid}.html', W / 'pairs' / f'cift{n}-{side}.html')
        im = Image.open(W / 'shots' / f'{pid}.png').convert('RGB'); w, h = im.size
        im = im.resize((a.width, int(h * a.width / w)), Image.Resampling.LANCZOS); h = im.size[1]; k = 2 if h * 1000 / a.width < 3400 else 3
        half_ov = 40 if k >= 2 else 0
        for j in range(k):
            y0 = max(0, j * h // k - (half_ov if j > 0 else 0))
            y1 = min(h, (j + 1) * h // k + (half_ov if j < k - 1 else 0))
            im.crop((0, y0, a.width, y1)).save(W / 'judge' / f'cift{n}-{side}-{j + 1}.png')
for name, obj in (('PAIR_MAP_DO_NOT_OPEN.json', pm), ('KEY_DO_NOT_OPEN.json', key), ('metrics.json', metrics)):
    with open(W / name, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False)
print(f'{n} pairs built')
