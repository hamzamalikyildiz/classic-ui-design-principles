#!/usr/bin/env python3
"""Write one generator task file per page, so every agent gets an identical, short instruction.

    python3 bench/make_tasks.py <workdir> --skill <skill dir> --python <python exe> [--briefs r,m] [--reps 2] [--rounds 2]

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
SKILL = ("First read {skill}\\SKILL.md and the files it tells you to read (mood {mood}: moods\\{mf}.md, reference\\visual-quality.md; "
         "reference\\rules.md when fixing findings). Follow it. Do not read anything else in the skill folder (bench\\ is off limits).\n"
         "When the page is done run (set PYTHONIOENCODING=utf-8):\n"
         "  \"{py}\" \"{skill}\\scripts\\uitools.py\" audit <file> --mood {mood}\n"
         "  \"{py}\" \"{skill}\\scripts\\render.py\" <file> --out \"{png}\" --check\n"
         "Open the PNG with the Read tool. Fix every WARN and anything empty, clipped, overlapping or broken with the smallest edits. "
         "Repeat audit and render after fixes. At most {rounds} fix rounds.\n")
NOSKILL = ("Do NOT read anything under {skill} or any skills folder.\n"
           "When the page is done run (set PYTHONIOENCODING=utf-8):\n"
           "  \"{py}\" \"{skill}\\scripts\\render.py\" <file> --out \"{png}\"\n"
           "(no --check; use it only to render a screenshot). Open the PNG with the Read tool. "
           "Fix anything empty, clipped, overlapping, broken or ugly with the smallest edits. At most {rounds} fix rounds.\n")

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('--skill', required=True); ap.add_argument('--python', required=True)
ap.add_argument('--briefs', default='r,m'); ap.add_argument('--reps', type=int, default=2); ap.add_argument('--rounds', type=int, default=2)
a = ap.parse_args()
W = pathlib.Path(a.work); briefs = json.load(open(HERE / 'briefs.json'))
(W / 'tasks').mkdir(parents=True, exist_ok=True); (W / 'shots_gen').mkdir(exist_ok=True)
index = []
for arm in ('skill', 'noskill'):
    (W / 'raw' / arm).mkdir(parents=True, exist_ok=True)
    for mood, b in briefs.items():
        for key in a.briefs.split(','):
            for rep in range(1, a.reps + 1):
                name = f'{mood}-{key}-{rep}'
                out = W / 'raw' / arm / f'{name}.html'; png = W / 'shots_gen' / f'{arm}-{name}.png'
                text = COMMON.format(brief=b[key], out=out)
                fmt = dict(skill=a.skill, py=a.python, mood=mood, mf=MOOD_FILE[mood], png=png, rounds=a.rounds)
                text += (SKILL if arm == 'skill' else NOSKILL).format(**fmt)
                task = W / 'tasks' / f'{arm}-{name}.txt'; task.write_text(text, encoding='utf-8')
                index.append({'arm': arm, 'page': name, 'task': str(task)})
json.dump(index, open(W / 'tasks' / 'index.json', 'w'), indent=1)
print(f'{len(index)} task files in {W / "tasks"}')
