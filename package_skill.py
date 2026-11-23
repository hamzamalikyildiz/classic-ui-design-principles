#!/usr/bin/env python3
"""Build a light install bundle: only what an agent needs (SKILL.md, moods/, reference/, scripts/, LICENSE).

    python package_skill.py [--out dist/classic-ui-design-principles.zip]

Benchmarks (bench/), tests/ and examples/ are left out, so the upload to claude.ai stays small.
"""
import argparse, pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
NAME = 'classic-ui-design-principles'
INCLUDE = ['SKILL.md', 'LICENSE', 'moods', 'reference', 'scripts']


def files():
    for item in INCLUDE:
        p = ROOT / item
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc', '.pyo'):
                    yield f


def build(out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files():
            z.write(f, f'{NAME}/{f.relative_to(ROOT).as_posix()}')
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'dist' / f'{NAME}.zip'))
    out = build(pathlib.Path(a.out)) if (a := ap.parse_args()) else None
    print(f'{out} ({out.stat().st_size // 1024} KB)')
