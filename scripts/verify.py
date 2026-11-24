#!/usr/bin/env python3
"""Unified single-turn UI verification: static uitools.py audit + rendered render.py checks (stdlib only).

    python scripts/verify.py [files ...] [--route PATH ...] [--routes-glob GLOB ...]
        [--root DIR] [--tsconfig PATH] [--css CSS ...]
        [--mood {playful,trust,bold,editorial,technical}] [--baseline PATH]
        [--url URL] [--routes PATH] [--out OUT] [--out-dir DIR]
        [--motion] [--motion-trigger SELECTOR] [--require-axe] [--no-render]
        [--format {text,json}] [--fail-on {none,fail,warn}]
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

_SCRIPTS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import render as R  # noqa: E402
import uitools  # noqa: E402

NOT_RUN_RULES = {'axe-not-run', 'axe-error'}
DEFAULT_GRID = 8


def is_playwright_available():
    """Return True when Python Playwright is importable in the current environment."""
    try:
        return importlib.util.find_spec('playwright') is not None
    except (ImportError, ValueError):
        return False


def build_parser():
    """Construct the CLI argument parser for verify.py."""
    ap = argparse.ArgumentParser(
        description='Unified single-turn static audit (uitools.py) and rendered browser verification (render.py)',
    )
    ap.add_argument('files', nargs='*', help='files to audit statically (and render if local .html/.htm)')
    ap.add_argument('--route', nargs='+', action='extend', default=[], metavar='PATH',
                    help='route entry file(s) to audit statically with cross-file component inlining')
    ap.add_argument('--routes-glob', nargs='+', action='extend', default=[], metavar='GLOB',
                    help='glob pattern(s) for route entry files (e.g. "app/**/page.tsx")')
    ap.add_argument('--root', metavar='DIR',
                    help='project root directory for @/ and tsconfig path resolution')
    ap.add_argument('--tsconfig', metavar='PATH',
                    help='path to tsconfig.json for alias path resolution')
    ap.add_argument('--css', nargs='+', action='extend', default=[], metavar='CSS',
                    help='CSS file(s) with :root tokens (e.g. app/globals.css)')
    ap.add_argument('--mood', choices=('playful', 'trust', 'bold', 'editorial', 'technical'),
                    help='mood profile for static character and palette checks')
    ap.add_argument('--baseline', metavar='PATH',
                    help='baseline JSON file to filter known static audit issues')
    ap.add_argument('--url', metavar='URL',
                    help='live HTTP(S) URL for rendered verification')
    ap.add_argument('--routes', metavar='PATH',
                    help='multi-route JSON configuration file for rendered verification')
    ap.add_argument('--out', metavar='OUT',
                    help='output PNG path for single-target rendered capture')
    ap.add_argument('--out-dir', metavar='DIR', default=None,
                    help='output directory for rendered screenshots and reports (default: shots)')
    ap.add_argument('--motion', action='store_true',
                    help='run motion & animation audit and capture filmstrip frames during rendered check')
    ap.add_argument('--motion-trigger', metavar='SELECTOR',
                    help='CSS selector of interactive element to trigger during --motion audit')
    ap.add_argument('--require-axe', action='store_true',
                    help='fail if axe-core accessibility check does not run or errors')
    ap.add_argument('--no-render', action='store_true',
                    help='skip browser rendering and run static audit only')
    ap.add_argument('--format', choices=('text', 'json'), default='text',
                    help='output format for unified report (default: text)')
    ap.add_argument('--fail-on', choices=('none', 'fail', 'warn'), default='fail',
                    help='exit with code 1 when findings reach this severity (default: fail)')
    return ap


def _resolve_routes_local_html(routes_cfg, routes_base_dir=None):
    """If routes_cfg['base_url'] points to an existing local .html/.htm file, return its path string."""
    raw = str(routes_cfg.get('base_url') or '').strip()
    if not raw or raw.lower().startswith(('http://', 'https://')):
        return None
    if raw.lower().startswith('file://'):
        parsed = urllib.parse.urlsplit(raw)
        local_path = pathlib.Path(urllib.request.url2pathname(parsed.path))
        if local_path.is_file() and local_path.suffix.lower() in ('.html', '.htm'):
            return str(local_path)
        return None

    file_part = re.split(r'[?#]', raw, maxsplit=1)[0]
    if not file_part:
        return None
    p = pathlib.Path(file_part)
    if not p.is_absolute() and routes_base_dir is not None and (routes_base_dir / p).is_file():
        cand = (routes_base_dir / p).resolve()
    else:
        cand = p
    if cand.is_file() and cand.suffix.lower() in ('.html', '.htm'):
        return str(cand)
    return None


def _run_static_phase(static_files, all_routes, args):
    """Execute static uitools.py audit across files and route entrypoints; return structured dict."""
    if not static_files and not all_routes:
        return {
            'ran': False,
            'summary': {'FAIL': 0, 'WARN': 0, 'INFO': 0},
            'targets': [],
            'findings': [],
        }

    css_texts = [pathlib.Path(p).read_text(encoding='utf-8', errors='ignore') for p in (args.css or [])]
    shared_tokens = uitools.css_tokens(css_texts)
    shared_dark = uitools.css_tokens(css_texts, r'\.dark')
    baseline_entries = uitools.load_baseline(args.baseline) if args.baseline else None

    total = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
    total_suppressed = 0
    total_baseline_skipped = 0
    targets_out = []
    findings_out = []

    targets = [(p, False) for p in static_files] + [(p, True) for p in all_routes]
    for p, is_route in targets:
        p_txt = pathlib.Path(p).read_text(encoding='utf-8', errors='ignore')
        inlined_rel = []
        if is_route:
            eff_root = pathlib.Path(args.root).resolve() if args.root else uitools.find_project_root(p)
            composed = uitools.compose_route(p, txt=p_txt, root_dir=eff_root, tsconfig_path=args.tsconfig)
            extra_texts = [p_txt] + [
                pathlib.Path(fp).read_text(encoding='utf-8', errors='ignore')
                for fp in composed.inlined_files
                if pathlib.Path(fp).is_file()
            ]
            tokens = {**shared_tokens, **uitools.css_tokens(extra_texts)}
            dark_tokens = {**shared_dark, **uitools.css_tokens(extra_texts, r'\.dark')}
            iss, suppressed = uitools.audit(
                p,
                DEFAULT_GRID,
                tokens,
                dark_tokens,
                args.mood,
                txt=composed,
                return_suppressed=True,
                route_mode=True,
                root_dir=eff_root,
                tsconfig_path=args.tsconfig,
            )
            for fp in composed.inlined_files:
                try:
                    inlined_rel.append(pathlib.Path(fp).resolve().relative_to(eff_root).as_posix())
                except ValueError:
                    inlined_rel.append(str(fp))
        else:
            tokens = {**shared_tokens, **uitools.css_tokens([p_txt])}
            dark_tokens = {**shared_dark, **uitools.css_tokens([p_txt], r'\.dark')}
            iss, suppressed = uitools.audit(
                p,
                DEFAULT_GRID,
                tokens,
                dark_tokens,
                args.mood,
                txt=p_txt,
                return_suppressed=True,
                root_dir=args.root,
                tsconfig_path=args.tsconfig,
            )
            composed = None

        total_suppressed += len(suppressed)
        if baseline_entries is not None:
            filtered, skipped = uitools.filter_baseline(
                [(p, sev, rule, msg, p_txt) for sev, rule, msg in iss],
                baseline_entries,
            )
            iss = [(sev, rule, msg) for _p, sev, rule, msg, _txt in filtered]
            total_baseline_skipped += skipped

        target_findings = []
        for sev, rule, msg in iss:
            total[sev] += 1
            target_findings.append({'severity': sev, 'rule': rule, 'message': msg})
            findings_out.append({'file': str(p), 'severity': sev, 'rule': rule, 'message': msg})

        t_entry = {
            'file': str(p),
            'route_mode': is_route,
            'findings': target_findings,
        }
        if is_route and composed is not None:
            t_entry['inlined_count'] = composed.inlined_count
            t_entry['inlined_files'] = inlined_rel
        targets_out.append(t_entry)

    out = {
        'ran': True,
        'summary': total,
        'targets': targets_out,
        'findings': findings_out,
    }
    if total_suppressed > 0:
        out['suppressed'] = total_suppressed
    if args.baseline is not None:
        out['baseline_skipped'] = total_baseline_skipped
    return out


def _skipped_render_report(sev, rule, msg):
    summary = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
    summary[sev] += 1
    return {
        'ran': False,
        'skipped': True,
        'summary': summary,
        'captures': [],
        'findings': [{
            'route': None,
            'viewport': None,
            'state': None,
            'rule': rule,
            'severity': sev,
            'message': msg,
            'selector': None,
        }],
    }


def _run_render_phase(html_files, args):
    """Execute rendered render.py checks when enabled and a renderable target is present."""
    has_target = bool(args.routes or args.url or html_files)
    if args.no_render or not has_target:
        if args.require_axe and args.no_render and has_target:
            return _skipped_render_report(
                'FAIL',
                'axe-not-run',
                'rendering skipped via --no-render while --require-axe was requested',
            )
        return {
            'ran': False,
            'summary': {'FAIL': 0, 'WARN': 0, 'INFO': 0},
            'captures': [],
            'findings': [],
        }

    if not is_playwright_available():
        if args.require_axe:
            return _skipped_render_report(
                'FAIL',
                'axe-not-run',
                'Playwright not installed; Accessibility was NOT checked (--require-axe)',
            )
        return _skipped_render_report(
            'INFO',
            'render-skipped',
            'Playwright not installed; static audit only',
        )

    eff_out_dir = args.out_dir or 'shots'
    prev_require_axe = R.REQUIRE_AXE
    R.REQUIRE_AXE = bool(args.require_axe)
    try:
        if args.routes:
            opts = R.RenderOptions(
                routes=args.routes,
                out_dir=eff_out_dir,
                check=True,
                motion=bool(args.motion),
                motion_trigger=args.motion_trigger,
                format=args.format,
                require_axe=bool(args.require_axe),
            )
            res = R.render_routes(opts)
            jr = dict(res.get('json_report') or R._build_json_report(res.get('results') or []))
            jr['ran'] = True
            jr['out_dir'] = res.get('out_dir')
            if res.get('report'):
                jr['report'] = res['report']
            if res.get('contact_sheet'):
                jr['contact_sheet'] = res['contact_sheet']
            return jr

        if args.url:
            out_path = args.out or (str(pathlib.Path(args.out_dir) / 'page.png') if args.out_dir else None)
            if out_path:
                pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            opts = R.RenderOptions(
                url=args.url,
                out=out_path,
                out_dir=eff_out_dir,
                check=True,
                motion=bool(args.motion),
                motion_trigger=args.motion_trigger,
                format=args.format,
                require_axe=bool(args.require_axe),
                online=True,
            )
            res = R.render(opts)
            jr = dict(R._build_json_report([], single_target={'route': args.url, 'height': opts.height, **res}))
            jr['ran'] = True
            return jr

        items = []
        for idx, hf in enumerate(html_files):
            if args.out:
                if len(html_files) == 1:
                    out_path = args.out
                else:
                    p_out = pathlib.Path(args.out)
                    suffix = p_out.suffix or '.png'
                    out_path = str(p_out.with_name(f'{p_out.stem}-{idx + 1}{suffix}'))
            elif args.out_dir:
                out_path = str(pathlib.Path(args.out_dir) / f'{pathlib.Path(hf).stem}.png')
            else:
                out_path = None
            if out_path:
                pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)

            opts = R.RenderOptions(
                html=hf,
                out=out_path,
                out_dir=eff_out_dir,
                check=True,
                motion=bool(args.motion),
                motion_trigger=args.motion_trigger,
                format=args.format,
                require_axe=bool(args.require_axe),
                online=False,
            )
            res = R.render(opts)
            items.append({
                'route': str(hf),
                'viewport': f"{res.get('width', opts.width)}x{opts.height}",
                'state': 'default',
                'width': res.get('width', opts.width),
                'height': opts.height,
                'scroll_height': res.get('scroll_height', 0),
                'out': res.get('out'),
                'findings': res.get('findings') or [],
            })

        jr = dict(R._build_json_report(items))
        jr['ran'] = True
        return jr
    finally:
        R.REQUIRE_AXE = prev_require_axe


def _format_text_report(unified):
    lines = []
    static_rep = unified['static']
    render_rep = unified['render']
    total = unified['summary']

    if static_rep.get('ran'):
        for tgt in static_rep.get('targets', []):
            iss = tgt.get('findings', [])
            if tgt.get('route_mode'):
                inl_n = tgt.get('inlined_count', 0)
                lines.append(f"== {tgt['file']} [inlined {inl_n} component(s)]: {len(iss)} issue(s)")
                if tgt.get('inlined_files'):
                    lines.append(f"  inlined files: {', '.join(tgt['inlined_files'])}")
            else:
                lines.append(f"== {tgt['file']}: {len(iss)} issue(s)")
            for f in iss:
                lines.append(f"  [{f['severity']}] {f['rule']}: {f['message']}")

    if render_rep.get('ran'):
        captures = render_rep.get('captures', [])
        lines.append(f"== render: {len(captures)} capture(s)")
        for f in render_rep.get('findings', []):
            ctx_parts = [str(f[k]) for k in ('route', 'state', 'viewport') if f.get(k)]
            ctx = f" ({'/'.join(ctx_parts)})" if len(ctx_parts) > 1 else (f" ({ctx_parts[0]})" if ctx_parts else '')
            lines.append(f"  [{f['severity']}] {f['rule']}{ctx}: {f['message']}")
        for cap in captures:
            if cap.get('out'):
                lines.append(f"  {cap['out']} ({cap.get('width', 0)}x{cap.get('scroll_height', 0)})")
        if render_rep.get('report'):
            lines.append(f"REPORT: {render_rep['report']}")
        if render_rep.get('contact_sheet'):
            lines.append(f"CONTACT_SHEET: {render_rep['contact_sheet']}")
    elif render_rep.get('skipped'):
        for f in render_rep.get('findings', []):
            lines.append(f"[{f['severity']}] {f['rule']}: {f['message']}")

    summary_line = f"\nSUMMARY FAIL={total['FAIL']} WARN={total['WARN']} INFO={total['INFO']}"
    if static_rep.get('suppressed'):
        summary_line += f" SUPPRESSED={static_rep['suppressed']}"
    if 'baseline_skipped' in static_rep:
        summary_line += f" BASELINE_SKIPPED={static_rep['baseline_skipped']}"
    lines.append(summary_line)
    return '\n'.join(lines)


def verify(argv=None):
    """Parse CLI args, run static + rendered verification, and return (exit_code, unified_report)."""
    ap = build_parser()
    a = ap.parse_args(argv)

    if not a.files and not a.route and not a.routes_glob and not a.url and not a.routes:
        ap.error('provide at least one target: files, --route, --routes-glob, --url, or --routes')
    if a.routes and a.url:
        ap.error('cannot combine --routes with --url')
    if a.url:
        parsed = urllib.parse.urlparse(a.url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            ap.error(f'invalid --url {a.url!r}: expected http:// or https:// URL')

    routes_cfg = None
    routes_base_dir = None
    if a.routes:
        try:
            routes_cfg, routes_base_dir = R.load_routes_config(a.routes)
        except (OSError, ValueError) as exc:
            ap.error(str(exc))

    if a.tsconfig and not pathlib.Path(a.tsconfig).is_file():
        ap.error(f'tsconfig not found: {a.tsconfig}')
    if a.baseline and not pathlib.Path(a.baseline).is_file():
        ap.error(f'baseline file not found: {a.baseline}')

    glob_routes = uitools._expand_routes_glob(a.routes_glob, root_dir=a.root) if a.routes_glob else []
    if a.routes_glob and not glob_routes:
        ap.error(f"no files matched --routes-glob: {', '.join(a.routes_glob)}")

    all_routes = list(dict.fromkeys(list(a.route or []) + glob_routes))
    static_files = list(a.files or [])

    if not static_files and not all_routes and routes_cfg is not None:
        local_html = _resolve_routes_local_html(routes_cfg, routes_base_dir)
        if local_html:
            static_files = [local_html]

    missing = [p for p in static_files + all_routes + list(a.css or []) if not pathlib.Path(p).is_file()]
    if missing:
        ap.error(f"file not found: {', '.join(missing)}")

    html_files = [f for f in (a.files or []) if pathlib.Path(f).suffix.lower() in ('.html', '.htm')]

    static_rep = _run_static_phase(static_files, all_routes, a)
    render_rep = _run_render_phase(html_files, a)

    total_summary = {
        'FAIL': static_rep['summary']['FAIL'] + render_rep['summary']['FAIL'],
        'WARN': static_rep['summary']['WARN'] + render_rep['summary']['WARN'],
        'INFO': static_rep['summary']['INFO'] + render_rep['summary']['INFO'],
    }
    axe_failed = bool(a.require_axe and any(
        f.get('rule') in NOT_RUN_RULES
        for f in render_rep.get('findings', [])
    ))
    failed = axe_failed or R._should_fail(total_summary, a.fail_on)
    unified = {
        'static': static_rep,
        'render': render_rep,
        'summary': total_summary,
        'passed': not failed,
    }
    return (1 if failed else 0), unified, a.format


def main(argv=None):
    code, unified, fmt = verify(argv)
    if fmt == 'json':
        print(json.dumps(unified, indent=2))
    else:
        print(_format_text_report(unified))
    return code


if __name__ == '__main__':
    sys.exit(main())
