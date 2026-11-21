#!/usr/bin/env python3
"""Build blind A/B pairs from raw/{skill,noskill[,noskill_check]}/<mood>-<brief>-<rep>.html.

    python3 bench/build_pairs.py <workdir> [--seed N] [--checks] [--app]

Single-page mode (default): writes <workdir>/judge/ciftN-{A,B}-K.png (1000px wide crops),
pairs/*.html, PAIR_MAP_DO_NOT_OPEN.json, KEY_DO_NOT_OPEN.json, and metrics.json.

App mode (--app): binds bench/routes_app/<brief>.json to each HTML file's file:/// URI,
runs scripts/render.py --routes <tmp_routes.json> --motion --check --out-dir <pair_dir>/<side>,
produces contact-sheet.png + filmstrip.png per side in pairs/ and judge/, and writes
blind pairs.json + key.json alongside PAIR_MAP_DO_NOT_OPEN.json / KEY_DO_NOT_OPEN.json.
"""
import argparse, json, pathlib, random, re, shutil, subprocess, sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import render as R

MOTION_RULES = {
    'motion-layout-property',
    'reduced-motion-ignored',
    'layout-shift',
    'slow-feedback',
    'long-ui-transition',
    'infinite-motion',
}
COMPARISON_ORDER = (
    ('skill', 'noskill'),
    ('skill', 'noskill_check'),
    ('noskill_check', 'noskill'),
)


def parse_page_stem(stem):
    """Parse '<mood>-<brief>-<rep>' even when <brief> contains hyphens (e.g. 'trust-cv-opt-1')."""
    if '-' not in stem:
        raise ValueError(f'expected <mood>-<brief>-<rep>, got {stem!r}')
    mood, rest = stem.split('-', 1)
    if '-' not in rest:
        raise ValueError(f'expected <mood>-<brief>-<rep>, got {stem!r}')
    brief, rep = rest.rsplit('-', 1)
    return mood, brief, rep


def prepare_routes_config(brief_id, html_path, routes_dir=None):
    """Load bench/routes_app/<brief_id>.json (or fallback) and bind base_url to html_path's file:/// URI."""
    rdir = pathlib.Path(routes_dir) if routes_dir is not None else (HERE / 'routes_app')
    tpl = rdir / f'{brief_id}.json'
    if tpl.is_file():
        cfg = json.loads(tpl.read_text(encoding='utf-8'))
    else:
        cfg = {
            'base_url': 'index.html',
            'viewports': ['desktop', 'mobile'],
            'long_loading_frames_ms': [500, 4000, 12000],
            'routes': [
                {'name': 'login', 'path': '#/login', 'states': ['default', 'loading', 'error', 'locked']},
                {'name': 'list', 'path': '#/list', 'states': ['default', 'empty', 'loading', 'error', 'partial']},
                {
                    'name': 'detail',
                    'path': '#/detail/1',
                    'states': ['default', 'loading', 'long-loading', 'error', 'partial'],
                    'motion_trigger': '[data-motion-trigger]',
                    'state_overrides': {
                        'default': {'actions': [{'click': '[data-motion-trigger]'}, {'wait': 400}]},
                    },
                },
                {'name': 'settings', 'path': '#/settings', 'states': ['default', 'loading', 'error']},
            ],
        }
    cfg['base_url'] = pathlib.Path(html_path).resolve().as_uri()
    return cfg


def find_filmstrip(shot_dir):
    """Locate filmstrip.png produced by render.py --routes --motion (root or route subdir)."""
    d = pathlib.Path(shot_dir)
    for cand in (d / 'filmstrip.png', d / 'detail' / 'filmstrip.png'):
        if cand.is_file():
            return cand
    for cand in sorted(d.glob('*/filmstrip.png')):
        if cand.is_file():
            return cand
    return None


def extract_route_metrics(report_data):
    """Summarize axe, layout, and motion WARN/FAIL counts from render.py --format json output."""
    findings = report_data.get('findings') or []
    summary = report_data.get('summary') or {}
    axe_missing = any(
        f.get('rule') == 'axe' and 'unavailable' in (f.get('message') or '')
        for f in findings
    )
    axe_serious = None if axe_missing else sum(
        1 for f in findings
        if f.get('severity') in ('WARN', 'FAIL') and str(f.get('rule', '')).startswith('axe-')
    )
    non_axe = sum(
        1 for f in findings
        if f.get('severity') in ('WARN', 'FAIL') and not str(f.get('rule', '')).startswith('axe-')
    )
    motion_warns = sum(
        1 for f in findings
        if f.get('severity') in ('WARN', 'FAIL') and f.get('rule') in MOTION_RULES
    )
    return {
        'axe_serious': axe_serious,
        'layout_warns': non_axe,
        'check_warns': non_axe,
        'motion_warns': motion_warns,
        'fail_count': int(summary.get('FAIL', 0)),
        'warn_count': int(summary.get('WARN', 0)),
        'capture_count': len(report_data.get('captures') or []),
    }


def _strip_comments(html_path):
    return re.sub(r'<!--.*?-->', '', pathlib.Path(html_path).read_text(encoding='utf-8'), flags=re.S)


def _render_single_page_mode(files, ids, W, args):
    from playwright.sync_api import sync_playwright

    key, metrics = {}, {}
    tw_offline = args.offline or not R.reachable('https://cdn.tailwindcss.com')
    gf_offline = args.offline or not R.reachable('https://fonts.googleapis.com/css2?family=Inter')
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=R.chrome_path() or None, args=['--no-sandbox'])
        for f, i in zip(files, ids):
            arm = f.parent.name
            mood, brief, rep = parse_page_stem(f.stem)
            html = _strip_comments(f)
            pid = f'p{i}'
            (W / 'anon' / f'{pid}.html').write_text(html, encoding='utf-8')
            if R.CDN.search(html) and tw_offline:
                html = R.compile_tailwind(html)
            if R.GFONTS.search(html) and gf_offline:
                html = R.inline_fonts(html)
            tmp = W / 'anon' / f'.{pid}.render.html'
            tmp.write_text(html, encoding='utf-8')
            pg = br.new_page(viewport={'width': 1440, 'height': 900})
            try:
                pg.goto(tmp.as_uri())
                pg.wait_for_timeout(500)
                pg.evaluate(
                    "async()=>{const h=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight);"
                    "for(let y=0;y<h;y+=600){scrollTo({top:y,behavior:'instant'});await new Promise(r=>setTimeout(r,60))}"
                    "scrollTo({top:0,behavior:'instant'})}"
                )
                pg.wait_for_timeout(600)
                pg.screenshot(path=str(W / 'shots' / f'{pid}.png'), full_page=True)
                ax = R.run_axe(pg)
            finally:
                pg.close()
                tmp.unlink(missing_ok=True)
            key[pid] = {'arm': arm, 'mood': mood, 'brief': brief, 'rep': rep}
            axe_missing = any(r == 'axe' and 'unavailable' in m for _, r, m in ax)
            metrics[pid] = {'axe_serious': None if axe_missing else sum(1 for s, r, m in ax if s == 'WARN')}
            if args.checks:
                tmp_png = W / 'anon' / '_b.png'
                try:
                    res = subprocess.run(
                        [sys.executable, str(HERE.parent / 'scripts/render.py'),
                         str(W / 'anon' / f'{pid}.html'), '--out', str(tmp_png), '--check'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace',
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
    return key, metrics


def _render_app_mode(files, ids, W, args):
    key, metrics = {}, {}
    render_py = HERE.parent / 'scripts' / 'render.py'
    routes_dir = HERE / 'routes_app'
    for f, i in zip(files, ids):
        arm = f.parent.name
        mood, brief, rep = parse_page_stem(f.stem)
        html = _strip_comments(f)
        pid = f'p{i}'
        anon_html = W / 'anon' / f'{pid}.html'
        anon_html.write_text(html, encoding='utf-8')
        shot_dir = W / 'shots' / pid
        if shot_dir.exists():
            shutil.rmtree(shot_dir)
        shot_dir.mkdir(parents=True, exist_ok=True)

        routes_cfg = prepare_routes_config(brief, anon_html, routes_dir=routes_dir)
        tmp_routes = W / 'anon' / f'.{pid}.routes.json'
        tmp_routes.write_text(json.dumps(routes_cfg, indent=2, ensure_ascii=False), encoding='utf-8')
        try:
            cmd = [
                sys.executable, str(render_py),
                '--routes', str(tmp_routes),
                '--motion',
                '--check',
                '--format', 'json',
                '--out-dir', str(shot_dir),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        finally:
            tmp_routes.unlink(missing_ok=True)

        key[pid] = {'arm': arm, 'mood': mood, 'brief': brief, 'rep': rep}
        report_file = shot_dir / 'report.json'
        report_data = None
        if report_file.is_file():
            report_data = json.loads(report_file.read_text(encoding='utf-8'))
        elif res.returncode == 0 and res.stdout.strip():
            try:
                report_data = json.loads(res.stdout)
            except json.JSONDecodeError:
                report_data = None
        if res.returncode != 0:
            print(f'warning: render.py --routes failed for {pid}: {res.stderr.strip()}', file=sys.stderr)
        metrics[pid] = extract_route_metrics(report_data) if report_data else {
            'axe_serious': None, 'layout_warns': 0, 'check_warns': 0, 'motion_warns': 0,
        }
        film = find_filmstrip(shot_dir)
        if film is not None and film != shot_dir / 'filmstrip.png':
            shutil.copy2(film, shot_dir / 'filmstrip.png')
    return key, metrics


def _collect_pair_specs(inv):
    """Build pair specs [(comparison, focal_arm, other_arm, mood, brief, rep), ...] from inventory."""
    by_slot = {}
    for (arm, mood, brief, rep), pid in inv.items():
        by_slot.setdefault((mood, brief, rep), {})[arm] = pid
    specs = []
    paired_keys = set()
    for (mood, brief, rep), arm_map in sorted(by_slot.items()):
        for focal, other in COMPARISON_ORDER:
            if focal in arm_map and other in arm_map:
                specs.append((f'{focal}_vs_{other}', focal, other, mood, brief, rep))
                paired_keys.add((focal, mood, brief, rep))
                paired_keys.add((other, mood, brief, rep))
    for k in sorted(inv):
        if k not in paired_keys:
            arm, mood, brief, rep = k
            print(f'warning: unpaired page dropped: {arm}/{mood}-{brief}-{rep}', file=sys.stderr)
    return specs


def _save_judge_image(src_path, dst_path, max_width=None):
    im = Image.open(src_path).convert('RGB')
    if max_width and im.width > max_width:
        im = im.resize((max_width, max(1, int(im.height * max_width / im.width))), Image.Resampling.LANCZOS)
    im.save(dst_path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--checks', action='store_true')
    ap.add_argument('--app', action='store_true',
                    help='multi-screen app mode using bench/routes_app/<brief>.json and render.py --routes --motion')
    ap.add_argument('--width', type=int, default=1000)
    ap.add_argument('--offline', action='store_true', help='force local Tailwind compilation and font inlining')
    args = ap.parse_args(argv)

    W = pathlib.Path(args.work)
    random.seed(args.seed)
    files = sorted(f for f in (W / 'raw').glob('*/*.html') if not f.name.startswith('.'))
    ids = random.sample(range(1000, 9999), len(files))

    if (W / 'judge').exists():
        shutil.rmtree(W / 'judge')
    for d in ('anon', 'shots', 'pairs', 'judge'):
        (W / d).mkdir(exist_ok=True)

    if args.app:
        key, metrics = _render_app_mode(files, ids, W, args)
    else:
        key, metrics = _render_single_page_mode(files, ids, W, args)

    inv = {(v['arm'], v['mood'], v['brief'], v['rep']): k for k, v in key.items()}
    pair_specs = _collect_pair_specs(inv)

    # Balance A/B placement within each (comparison, mood) bucket
    buckets = {}
    for spec in pair_specs:
        comp, _, _, mood, _, _ = spec
        buckets.setdefault((comp, mood), []).append(spec)

    placement = {}
    for bucket_specs in buckets.values():
        flags = ([True, False] * len(bucket_specs))[:len(bucket_specs)]
        random.shuffle(flags)
        for spec, fl in zip(bucket_specs, flags):
            placement[spec] = fl

    order = list(pair_specs)
    random.shuffle(order)

    pm = {}
    blind_pairs = []
    for n, spec in enumerate(order, 1):
        comp, focal, other, m, b, r = spec
        pid_focal = inv[(focal, m, b, r)]
        pid_other = inv[(other, m, b, r)]
        focal_is_a = placement[spec]
        A, B = (pid_focal, pid_other) if focal_is_a else (pid_other, pid_focal)
        arm_a, arm_b = (focal, other) if focal_is_a else (other, focal)
        skill_side = 'A' if arm_a == 'skill' else ('B' if arm_b == 'skill' else None)

        pair_id = f'cift{n}'
        pm_entry = {
            'A': A,
            'B': B,
            'skill': skill_side,
            'mood': m,
            'brief': b,
            'rep': r,
        }
        if args.app or focal != 'skill' or other != 'noskill':
            pm_entry['arm_a'] = arm_a
            pm_entry['arm_b'] = arm_b
            pm_entry['focal'] = 'A' if focal_is_a else 'B'
            pm_entry['comparison'] = comp
        pm[pair_id] = pm_entry

        if args.app:
            blind_side_meta = {}
            for side, pid in (('A', A), ('B', B)):
                shutil.copy(W / 'anon' / f'{pid}.html', W / 'pairs' / f'{pair_id}-{side}.html')
                side_dir = W / 'pairs' / pair_id / side
                if side_dir.exists():
                    shutil.rmtree(side_dir)
                shot_dir = W / 'shots' / pid
                if shot_dir.exists():
                    shutil.copytree(shot_dir, side_dir)
                else:
                    side_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(W / 'anon' / f'{pid}.html', side_dir / 'index.html')

                cs_src = side_dir / 'contact-sheet.png'
                fs_src = find_filmstrip(side_dir)
                if fs_src is not None and fs_src != side_dir / 'filmstrip.png':
                    shutil.copy2(fs_src, side_dir / 'filmstrip.png')
                    fs_src = side_dir / 'filmstrip.png'

                side_info = {'html': f'pairs/{pair_id}/{side}/index.html'}
                if cs_src.is_file():
                    _save_judge_image(cs_src, W / 'judge' / f'{pair_id}-{side}-contact-sheet.png', max_width=args.width)
                    side_info['contact_sheet'] = f'pairs/{pair_id}/{side}/contact-sheet.png'
                if fs_src is not None and fs_src.is_file():
                    _save_judge_image(fs_src, W / 'judge' / f'{pair_id}-{side}-filmstrip.png', max_width=args.width)
                    side_info['filmstrip'] = f'pairs/{pair_id}/{side}/filmstrip.png'
                blind_side_meta[side] = side_info

            blind_pairs.append({
                'id': pair_id,
                'mood': m,
                'brief': b,
                'rep': r,
                'A': blind_side_meta['A'],
                'B': blind_side_meta['B'],
            })
        else:
            for side, pid in (('A', A), ('B', B)):
                shutil.copy(W / 'anon' / f'{pid}.html', W / 'pairs' / f'{pair_id}-{side}.html')
                im = Image.open(W / 'shots' / f'{pid}.png').convert('RGB')
                w, h = im.size
                im = im.resize((args.width, int(h * args.width / w)), Image.Resampling.LANCZOS)
                h = im.size[1]
                k = 2 if h * 1000 / args.width < 3400 else 3
                half_ov = 40 if k >= 2 else 0
                for j in range(k):
                    y0 = max(0, j * h // k - (half_ov if j > 0 else 0))
                    y1 = min(h, (j + 1) * h // k + (half_ov if j < k - 1 else 0))
                    im.crop((0, y0, args.width, y1)).save(W / 'judge' / f'{pair_id}-{side}-{j + 1}.png')

    for name, obj in (('PAIR_MAP_DO_NOT_OPEN.json', pm), ('KEY_DO_NOT_OPEN.json', key), ('metrics.json', metrics)):
        with open(W / name, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, ensure_ascii=False)

    if args.app:
        with open(W / 'pairs.json', 'w', encoding='utf-8') as fh:
            json.dump({'mode': 'app', 'pairs': blind_pairs}, fh, indent=2, ensure_ascii=False)
        with open(W / 'key.json', 'w', encoding='utf-8') as fh:
            json.dump({'mode': 'app', 'pairs': pm, 'pages': key}, fh, indent=2, ensure_ascii=False)

    print(f'{len(pm)} pairs built')


if __name__ == '__main__':
    main()
