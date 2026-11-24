#!/usr/bin/env python3
"""Build a light install bundle: only what an agent needs (SKILL.md, README.md, LICENSE, moods/, reference/, scripts/).

    python package_skill.py [--out dist/classic-ui-design-principles.zip] [--flat]

Benchmarks (bench/), tests/ and examples/ are left out, so the upload to claude.ai or marketplaces stays small.
Use --flat when packaging for marketplaces (e.g. Agensi.io) that require SKILL.md directly at the archive root.
"""
import argparse, pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
NAME = 'classic-ui-design-principles'
INCLUDE = ['SKILL.md', 'README.md', 'LICENSE', 'moods', 'reference', 'scripts']


def files():
    for item in INCLUDE:
        p = ROOT / item
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc', '.pyo'):
                    yield f


def build(out, flat=False):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files():
            rel = f.relative_to(ROOT).as_posix()
            arcname = rel if flat else f'{NAME}/{rel}'
            z.write(f, arcname)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(ROOT / 'dist' / f'{NAME}.zip'))
    ap.add_argument('--flat', action='store_true',
                    help='write files directly at the zip root (SKILL.md at root) instead of under classic-ui-design-principles/')
    a = ap.parse_args(argv)
    out = build(pathlib.Path(a.out), flat=a.flat)
    print(f'{out} ({out.stat().st_size // 1024} KB)')
    return out


if __name__ == '__main__':
    main()
