#!/usr/bin/env python3
"""Write one generator task file per page, so every agent gets an identical, short instruction.

    python3 bench/make_tasks.py <workdir> --skill <skill dir> --python <python exe> [--briefs-file briefs.json] [--briefs r,m] [--reps 2] [--rounds 2]

Creates <workdir>/tasks/{skill,noskill}-<mood>-<brief>-<rep>.txt and <workdir>/raw/{skill,noskill}/.
Agent prompt: "Read <task file> and do exactly what it says."
Pages are saved as <workdir>/raw/<arm>/<mood>-<brief>-<rep>.html (the layout build_pairs.py expects).
"""
import argparse, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
MOOD_FILE = {'playful': 'expressive', 'bold': 'expressive', 'trust': 'trust', 'technical': 'technical', 'editorial': 'editorial'}
COMMON = ("Build one web page.\nBrief: {brief}\n\nOutput: single-file HTML, Tailwind via the CDN script, Google Fonts links allowed, "
          "vanilla JS only if needed, no web images (inline SVG/CSS shapes), roughly 150-300 lines. "
          "Save it to {out} and reply with that path only.\n\nDo NOT use the Skill tool.\n")
SKILL = ("First read {skill_md} and the files it tells you to read (mood {mood}: {mood_md}, {vq_md}; "
         "{rules_md} when fixing findings). Follow it. Do not read anything else in the skill folder (bench/ is off limits).\n"
         "When the page is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
         "  \"{py}\" \"{uitools}\" audit <file> --mood {mood}\n"
         "  \"{py}\" \"{render_py}\" <file> --out \"{png}\" --check\n"
         "Open the PNG with the Read tool. Fix every WARN and anything empty, clipped, overlapping or broken with the smallest edits. "
         "Repeat audit and render after fixes. At most {rounds} fix rounds.\n")
NOSKILL = ("Do NOT read anything under {skill} or any skills folder.\n"
           "When the page is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
           "  \"{py}\" \"{render_py}\" <file> --out \"{png}\"\n"
           "(no --check; use it only to render a screenshot). Open the PNG with the Read tool. "
           "Fix anything empty, clipped, overlapping, broken or ugly with the smallest edits. At most {rounds} fix rounds.\n")


def resolve_briefs_file(spec):
    """Resolve --briefs-file against CWD first, then bench/ directory."""
    p = pathlib.Path(spec)
    return p if p.is_file() else HERE / spec


def redact_task_text(text, skill_dir, work_dir, python_exe):
    """Replace local machine paths in task text with portable placeholders for archiving."""
    for old, token in ((str(skill_dir), '<SKILL_DIR>'), (str(work_dir), '<WORKDIR>'), (str(python_exe), '<PYTHON>')):
        if old:
            text = text.replace(old, token)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work'); ap.add_argument('--skill', required=True); ap.add_argument('--python', required=True)
    ap.add_argument('--briefs', default=''); ap.add_argument('--moods', default='')
    ap.add_argument('--briefs-file', default='briefs.json'); ap.add_argument('--reps', type=int, default=2); ap.add_argument('--rounds', type=int, default=2)
    a = ap.parse_args(argv)
    W = pathlib.Path(a.work)
    skill_path = pathlib.Path(a.skill)
    with open(resolve_briefs_file(a.briefs_file), encoding='utf-8') as fh:
        briefs = json.load(fh)
    want_moods = {m.strip() for m in a.moods.split(',') if m.strip()}
    want_briefs = [k.strip() for k in a.briefs.split(',') if k.strip()] if a.briefs else None
    (W / 'tasks').mkdir(parents=True, exist_ok=True); (W / 'shots_gen').mkdir(exist_ok=True)
    index = []
    for arm in ('skill', 'noskill'):
        (W / 'raw' / arm).mkdir(parents=True, exist_ok=True)
        for mood, b in briefs.items():
            if want_moods and mood not in want_moods:
                continue
            keys = want_briefs if want_briefs is not None else list(b.keys())
            for key in keys:
                if key not in b:
                    continue
                for rep in range(1, a.reps + 1):
                    name = f'{mood}-{key}-{rep}'
                    out = W / 'raw' / arm / f'{name}.html'; png = W / 'shots_gen' / f'{arm}-{name}.png'
                    text = COMMON.format(brief=b[key], out=out)
                    fmt = dict(
                        skill=str(skill_path),
                        skill_md=str(skill_path / 'SKILL.md'),
                        mood_md=str(pathlib.Path('moods') / f'{MOOD_FILE[mood]}.md'),
                        vq_md=str(pathlib.Path('reference') / 'visual-quality.md'),
                        rules_md=str(pathlib.Path('reference') / 'rules.md'),
                        uitools=str(skill_path / 'scripts' / 'uitools.py'),
                        render_py=str(skill_path / 'scripts' / 'render.py'),
                        py=a.python,
                        mood=mood,
                        png=png,
                        rounds=a.rounds,
                    )
                    text += (SKILL if arm == 'skill' else NOSKILL).format(**fmt)
                    task = W / 'tasks' / f'{arm}-{name}.txt'; task.write_text(text, encoding='utf-8')
                    index.append({'arm': arm, 'page': name, 'task': str(task)})
    with open(W / 'tasks' / 'index.json', 'w', encoding='utf-8') as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)
    print(f'{len(index)} task files in {W / "tasks"}')


if __name__ == '__main__':
    main()
