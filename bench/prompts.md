# Generator prompts (equal effort: both arms render, look and fix up to 3 rounds)

Common tail for both arms: single-file HTML, Tailwind via the CDN script, Google Fonts links allowed, vanilla JS only if needed, no web images (inline SVG/CSS shapes), roughly 150-300 lines, save to the given path, reply with the path only.

**Skill arm:** First read <skill>/SKILL.md and the files it tells you to read (moods/<mood>.md). Follow it. When done run `uitools.py audit <file> --mood <mood>` and `render.py <file> --out /tmp/x.png --check`, open the PNG with Read, fix every WARN and anything empty, clipped or broken with the smallest edits (max 3 rounds).

**No-skill arm:** Do not read the skill folder. When done run `render.py <file> --out /tmp/x.png` (no --check), open the PNG with Read, fix anything empty, clipped, broken or ugly with the smallest edits (max 3 rounds).

Judge prompt: see JUDGE_PROMPT.md (blind, A/B balanced, one line per pair).
