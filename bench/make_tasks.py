#!/usr/bin/env python3
"""Write one generator task file per page or app, so every agent gets an identical, short instruction.

    python3 bench/make_tasks.py <workdir> --skill <skill dir> --python <python exe> [--mode page|app] [--ablation] [--briefs-file briefs.json] [--briefs r,m] [--reps 2] [--rounds 2]

Creates <workdir>/tasks/{skill,noskill[,noskill_check]}-<mood>-<brief>-<rep>.txt and <workdir>/raw/{skill,noskill[,noskill_check]}/.
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
NOSKILL_CHECK = (
    "Do NOT read anything under {skill} or any skills folder.\n"
    "When the page is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
    "  \"{py}\" \"{render_py}\" <file> --out \"{png}\" --check\n"
    "Open the PNG with the Read tool. Fix every WARN and anything empty, clipped, overlapping or broken with the smallest edits. "
    "Repeat render after fixes. At most {rounds} fix rounds.\n"
)

COMMON_APP = (
    "Build one multi-screen web application as a single HTML file.\n"
    "Brief: {brief}\n\n"
    "Technical contract (required for automated multi-route rendering):\n"
    "- Single-file HTML, Tailwind via the CDN script, Google Fonts links allowed, vanilla JS.\n"
    "- Hash router supporting exactly these 4 routes on load and on hashchange: #/login, #/list, #/detail/1, #/settings.\n"
    "- State switcher supporting both `?state=default|empty|loading|long-loading|error|partial|locked` in the URL query string "
    "and `window.__RENDER_STATE__` (if defined) across routes.\n"
    "- On #/detail/1, include an interactive element with attribute `data-motion-trigger` that triggers the primary result micro-moment, "
    "and implement the >3s long-running operation with staged progress feedback and a cancel control.\n"
    "- No external web images (use inline SVG / CSS shapes).\n"
    "Save it to {out} and reply with that path only.\n\nDo NOT use the Skill tool.\n"
)
SKILL_APP = (
    "First read {skill_md} (App mode) and these reference files before coding:\n"
    "  - {app_flow_md}\n"
    "  - {states_md}\n"
    "  - {motion_md}\n"
    "  - {typography_locale_md}\n"
    "  - {sample_data_md}\n"
    "  - mood {mood}: {mood_md}, {vq_md} (and {rules_md} when fixing findings)\n"
    "Follow them carefully. Do not read anything else in the skill folder (bench/ is off limits).\n"
    "When the app is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
    "  \"{py}\" \"{uitools}\" audit \"{out}\" --mood {mood}\n"
    "  \"{py}\" \"{render_py}\" --routes \"{routes_json}\" --motion --check --out-dir \"{shots_dir}\"\n"
    "Open \"{shots_dir}/contact-sheet.png\" and any filmstrip PNGs (e.g. \"{shots_dir}/detail/filmstrip.png\") with the Read tool. "
    "Fix every WARN/FAIL and anything empty, clipped, overlapping, broken, or missing in states/motion with the smallest edits. "
    "Repeat audit and render after fixes. At most {rounds} fix rounds.\n"
)
NOSKILL_APP = (
    "Do NOT read anything under {skill} or any skills folder.\n"
    "When the app is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
    "  \"{py}\" \"{render_py}\" \"{out}\" --out \"{png}\"\n"
    "(no --check; use it only to render a screenshot). Open the PNG with the Read tool. "
    "Fix anything empty, clipped, overlapping, broken or ugly with the smallest edits. At most {rounds} fix rounds.\n"
)
NOSKILL_CHECK_APP = (
    "Do NOT read anything under {skill} or any skills folder.\n"
    "When the app is done run (set the environment variable PYTHONIOENCODING=utf-8 first; the command starts with the python.exe path in quotes):\n"
    "  \"{py}\" \"{render_py}\" --check --routes \"{routes_json}\" --out-dir \"{shots_dir}\"\n"
    "Open \"{shots_dir}/contact-sheet.png\" with the Read tool. "
    "Fix every WARN/FAIL and anything empty, clipped, overlapping, or broken with the smallest edits. "
    "Repeat render --check --routes after fixes. At most {rounds} fix rounds.\n"
)


def resolve_briefs_file(spec):
    """Resolve --briefs-file against CWD first, then bench/ directory."""
    p = pathlib.Path(spec)
    return p if p.is_file() else HERE / spec


def default_routes_template(brief_key):
    """Load bench/routes_app/<brief_key>.json or return a default 4-route app template."""
    tpl = HERE / 'routes_app' / f'{brief_key}.json'
    if tpl.is_file():
        return json.loads(tpl.read_text(encoding='utf-8'))
    return {
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


def write_task_routes_config(brief_key, html_path, dest_path):
    """Write a routes.json config bound to html_path's file:/// URI for app-mode checks."""
    cfg = default_routes_template(brief_key)
    cfg['base_url'] = pathlib.Path(html_path).resolve().as_uri()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
    return dest_path


def redact_task_text(text, skill_dir, work_dir, python_exe):
    """Replace local machine paths in task text with portable placeholders for archiving."""
    for old, token in ((str(skill_dir), '<SKILL_DIR>'), (str(work_dir), '<WORKDIR>'), (str(python_exe), '<PYTHON>')):
        if old:
            text = text.replace(old, token)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work'); ap.add_argument('--skill', required=True); ap.add_argument('--python', required=True)
    ap.add_argument('--mode', choices=('page', 'app'), default='page',
                    help='benchmark mode: page (default single-page) or app (multi-screen hash-routed app)')
    ap.add_argument('--ablation', action='store_true',
                    help='include noskill_check ablation arm (runs render.py --check without reading skill docs)')
    ap.add_argument('--briefs', default=''); ap.add_argument('--moods', default='')
    ap.add_argument('--briefs-file', default=None)
    ap.add_argument('--reps', type=int, default=2); ap.add_argument('--rounds', type=int, default=2)
    a = ap.parse_args(argv)
    W = pathlib.Path(a.work)
    skill_path = pathlib.Path(a.skill)
    briefs_spec = a.briefs_file or ('briefs_app.json' if a.mode == 'app' else 'briefs.json')
    with open(resolve_briefs_file(briefs_spec), encoding='utf-8') as fh:
        briefs = json.load(fh)
    want_moods = {m.strip() for m in a.moods.split(',') if m.strip()}
    want_briefs = [k.strip() for k in a.briefs.split(',') if k.strip()] if a.briefs else None
    (W / 'tasks').mkdir(parents=True, exist_ok=True); (W / 'shots_gen').mkdir(exist_ok=True)
    arms = ('skill', 'noskill', 'noskill_check') if a.ablation else ('skill', 'noskill')
    index = []
    for arm in arms:
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
                    shots_dir = W / 'shots_gen' / f'{arm}-{name}'
                    routes_json = W / 'routes' / f'{arm}-{name}.json'
                    fmt = dict(
                        skill=str(skill_path),
                        skill_md=str(skill_path / 'SKILL.md'),
                        mood_md=str(pathlib.Path('moods') / f'{MOOD_FILE[mood]}.md'),
                        vq_md=str(pathlib.Path('reference') / 'visual-quality.md'),
                        rules_md=str(pathlib.Path('reference') / 'rules.md'),
                        app_flow_md=str(pathlib.Path('reference') / 'app-flow.md'),
                        states_md=str(pathlib.Path('reference') / 'states.md'),
                        motion_md=str(pathlib.Path('reference') / 'motion.md'),
                        typography_locale_md=str(pathlib.Path('reference') / 'typography-locale.md'),
                        sample_data_md=str(pathlib.Path('reference') / 'sample-data.md'),
                        uitools=str(skill_path / 'scripts' / 'uitools.py'),
                        render_py=str(skill_path / 'scripts' / 'render.py'),
                        py=a.python,
                        mood=mood,
                        out=str(out),
                        png=str(png),
                        shots_dir=str(shots_dir),
                        routes_json=str(routes_json),
                        rounds=a.rounds,
                    )
                    if a.mode == 'app':
                        text = COMMON_APP.format(brief=b[key], out=out)
                        if arm == 'skill':
                            write_task_routes_config(key, out, routes_json)
                            text += SKILL_APP.format(**fmt)
                        elif arm == 'noskill_check':
                            write_task_routes_config(key, out, routes_json)
                            text += NOSKILL_CHECK_APP.format(**fmt)
                        else:
                            text += NOSKILL_APP.format(**fmt)
                    else:
                        text = COMMON.format(brief=b[key], out=out)
                        if arm == 'skill':
                            text += SKILL.format(**fmt)
                        elif arm == 'noskill_check':
                            text += NOSKILL_CHECK.format(**fmt)
                        else:
                            text += NOSKILL.format(**fmt)
                    task = W / 'tasks' / f'{arm}-{name}.txt'; task.write_text(text, encoding='utf-8')
                    entry = {'arm': arm, 'page': name, 'task': str(task)}
                    if a.mode == 'app':
                        entry['mode'] = 'app'
                    index.append(entry)
    with open(W / 'tasks' / 'index.json', 'w', encoding='utf-8') as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)
    print(f'{len(index)} task files in {W / "tasks"}')


if __name__ == '__main__':
    main()
