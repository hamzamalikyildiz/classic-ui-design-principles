"""Capture and verify deterministic audit snapshots for bench/runs/run[3-8]/*/*.html."""
import argparse
import contextlib
import difflib
import gzip
import importlib.util
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SNAPSHOT = ROOT / 'tests' / 'fixtures' / 'audit_snapshot_run3_8.json.gz'
MOODS = ('bold', 'editorial', 'playful', 'technical', 'trust')


def _load_uitools():
    spec = importlib.util.spec_from_file_location('uitools', ROOT / 'scripts' / 'uitools.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _collect_files():
    files = sorted(
        (p for p in ROOT.glob('bench/runs/run[3-8]/*/*.html') if p.is_file()),
        key=lambda p: p.relative_to(ROOT).as_posix(),
    )
    if not files:
        raise RuntimeError('no HTML files found under bench/runs/run[3-8]/*/*.html')
    return files


def _mood_for(path):
    prefix = path.name.split('-', 1)[0]
    if prefix not in MOODS:
        raise ValueError(f'unexpected mood prefix {prefix!r} in {path}')
    return prefix


def build_snapshot():
    ut = _load_uitools()
    files = _collect_files()
    records = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        mood = _mood_for(f)
        issues = [list(item) for item in ut.audit(str(f), 8, {}, mood=mood)]
        buf = io.StringIO()
        exit_code = 0
        try:
            with contextlib.redirect_stdout(buf):
                ut.main(['audit', str(f), '--mood', mood])
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else 1
        cli_out = buf.getvalue().replace(str(f), rel)
        records.append({
            'path': rel,
            'mood': mood,
            'issues': issues,
            'cli_exit': exit_code,
            'cli_stdout': cli_out,
        })
    return {
        'count': len(records),
        'files': records,
    }


def _dump_deterministic(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def capture(snapshot_path):
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _dump_deterministic(build_snapshot()).encode('utf-8')
    with snapshot_path.open('wb') as raw_f:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_f, mtime=0) as gz:
            gz.write(payload)
    print(f'Captured snapshot to {snapshot_path} ({snapshot_path.stat().st_size} bytes)')


def verify(snapshot_path):
    if not snapshot_path.is_file():
        print(f'error: snapshot not found: {snapshot_path}', file=sys.stderr)
        return 1
    with gzip.open(snapshot_path, 'rt', encoding='utf-8') as gz:
        expected_text = gz.read()
    actual_text = _dump_deterministic(build_snapshot())
    if actual_text == expected_text:
        expected_data = json.loads(expected_text)
        print(f"OK: {expected_data['count']} files verified byte-for-byte identical")
        return 0
    diff = ''.join(difflib.unified_diff(
        expected_text.splitlines(keepends=True),
        actual_text.splitlines(keepends=True),
        fromfile='expected',
        tofile='actual',
        n=3,
    ))
    print(diff[:8000], file=sys.stderr)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description='Capture/verify pre-refactor audit snapshot')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true', help='write snapshot fixture')
    mode.add_argument('--verify', action='store_true', help='verify current output against snapshot')
    ap.add_argument('--snapshot', type=pathlib.Path, default=DEFAULT_SNAPSHOT)
    args = ap.parse_args(argv)
    if args.capture:
        capture(args.snapshot)
        return 0
    return verify(args.snapshot)


if __name__ == '__main__':
    raise SystemExit(main())
