#!/usr/bin/env python3
"""Build blind A/B pairs from raw/{skill,noskill}/<mood>-<brief>-<rep>.html.

    python3 bench/build_pairs.py <workdir> [--seed N] [--checks]

Writes <workdir>/judge/ciftN-{A,B}-K.png (1000px wide crops), pairs/*.html, PAIR_MAP_DO_NOT_OPEN.json
(placement; skill is A in exactly half of each mood's pairs) and metrics.json (axe violations; --checks adds
render.py --check WARN counts). Judges see only the judge/ crops.
"""
import argparse, json, pathlib, random, re, shutil, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import render as R
from playwright.sync_api import sync_playwright
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--checks', action='store_true'); ap.add_argument('--width', type=int, default=1000); a = ap.parse_args()
W = pathlib.Path(a.work); random.seed(a.seed)
AXE = R.find_axe()
files = sorted((W / 'raw').glob('*/*.html'))
ids = random.sample(range(1000, 9999), len(files))
key, metrics = {}, {}
for d in ('anon', 'shots', 'pairs', 'judge'): (W / d).mkdir(exist_ok=True)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=R.chrome_path() or None, args=['--no-sandbox'])
    for f, i in zip(files, ids):
        arm = f.parent.name; mood, brief, rep = f.stem.split('-')
        html = re.sub(r'<!--.*?-->', '', f.read_text(encoding='utf-8'), flags=re.S)
        pid = f'p{i}'; (W / 'anon' / f'{pid}.html').write_text(html, encoding='utf-8')
        if R.CDN.search(html): html = R.compile_tailwind(html)
        if R.GFONTS.search(html): html = R.inline_fonts(html)
        tmp = W / 'anon' / f'.{pid}.render.html'; tmp.write_text(html, encoding='utf-8')
        pg = br.new_page(viewport={'width': 1440, 'height': 900}); pg.goto(tmp.as_uri()); pg.wait_for_timeout(500)
        pg.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,60))}scrollTo(0,0)}")
        pg.wait_for_timeout(600); pg.screenshot(path=str(W / 'shots' / f'{pid}.png'), full_page=True)
        ax = R.run_axe(pg); pg.close(); tmp.unlink()
        key[pid] = {'arm': arm, 'mood': mood, 'brief': brief, 'rep': rep}
        metrics[pid] = {'axe_serious': sum(1 for s, r, m in ax if s == 'WARN')}
        if a.checks:
            out = subprocess.run([sys.executable, str(HERE.parent / 'scripts/render.py'), str(W / 'anon' / f'{pid}.html'), '--out', '/tmp/_b.png', '--check'],
                                 capture_output=True, text=True).stdout
            metrics[pid]['check_warns'] = len(re.findall(r'\[WARN\]', out))
    br.close()
inv = {(v['arm'], v['mood'], v['brief'], v['rep']): k for k, v in key.items()}
groups = {}
for (arm, mood, brief, rep) in inv:
    if arm == 'skill' and ('noskill', mood, brief, rep) in inv: groups.setdefault(mood, []).append((brief, rep))
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
        im = im.resize((a.width, int(h * a.width / w))); h = im.size[1]; k = 2 if h * 1000 / a.width < 3400 else 3
        for j in range(k): im.crop((0, j * h // k, a.width, (j + 1) * h // k)).save(W / 'judge' / f'cift{n}-{side}-{j + 1}.png')
json.dump(pm, open(W / 'PAIR_MAP_DO_NOT_OPEN.json', 'w')); json.dump(key, open(W / 'KEY_DO_NOT_OPEN.json', 'w'))
json.dump(metrics, open(W / 'metrics.json', 'w'))
print(f'{n} pairs built')
