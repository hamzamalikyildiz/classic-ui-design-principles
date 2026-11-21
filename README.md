# classic-ui-design-principles

[![test](https://github.com/hamzamalikyildiz/classic-ui-design-principles/actions/workflows/test.yml/badge.svg)](https://github.com/hamzamalikyildiz/classic-ui-design-principles/actions/workflows/test.yml)

An agent skill built on classic, time-tested UI design principles. It turns vague UI requests ("make it modern") into measurable design rules. It detects the page type, stack and audience, picks a mood profile and the matching rules, applies them as concrete Tailwind/CSS values, then verifies the output with an audit script and a rendered screenshot.

The rules are guardrails, not the design: the goal is to remove errors without removing character.

Works with Claude (claude.ai, Claude Code) and any agent that reads `SKILL.md` files.

## What it covers

- **Color:** 60-30-10, WCAG AA contrast, semantic status colors
- **Layout:** 8pt grid, law of proximity, nested border radius, Z/F patterns, bento grid
- **Typography:** modular type scale, 45–75 character line length, max 2 fonts (up to 3 in expressive moods)
- **UX laws:** Fitts, Hick, Jakob, Miller, single primary CTA, skeleton and empty states
- **Character:** mood profiles (Playful, Trust, Bold, Editorial, Technical), one hero surface per screen, depth over borders, same-hue contrast fixes, categorical chart colors

Rules are selected per page type: landing, dashboard, form, content, mobile, e-commerce, settings, nav and card/modal components.

## Structure

```
classic-ui-design-principles/
├── SKILL.md              # core: flow, mood table, hard rules, tooling (~8.5 KB)
├── moods/                # per-mood notes: expressive (Playful/Bold), editorial, technical, trust
├── reference/
│   ├── page-types.md     # page-type matrix and mood mapping
│   ├── rules.md          # rule values, anti-patterns, conflict resolution
│   ├── tooling.md        # audit and render.py check details
│   └── visual-quality.md # palette recipe, typography voice, product UI, rhythm
├── bench/                # blind A/B benchmark: briefs, pair builder, scorer
│   └── runs/             # archived benchmark runs (run2–run8; see bench/runs/README.md)
├── scripts/
│   ├── uitools.py        # contrast, scale, radius, snap, audit (Python 3 stdlib only)
│   └── render.py         # offline full-page screenshot + --check (Playwright + Chromium)
└── tests/
    ├── test_uitools.py   # audit & rule regression tests (unittest, stdlib only)
    └── test_render.py    # render.py & JS payload tests (unittest)
```

## Install

**Claude Code**

```bash
git clone https://github.com/hamzamalikyildiz/classic-ui-design-principles ~/.claude/skills/classic-ui-design-principles
```

**claude.ai:** zip the `classic-ui-design-principles` folder and upload it in the Skills section of Settings.

`uitools.py` runs standalone with zero dependencies (Python 3 stdlib only). For screenshots and `--check`, `render.py` needs Playwright, Chromium/Chrome, and `node`/`npm` (for `axe-core` and offline Tailwind/font fallback):

```bash
pip install playwright && python -m playwright install chromium
```

## How to use

### 1. Ask for UI as usual

Once the skill is installed you don't need to mention it. Any request to build or improve UI triggers it:

```
Build a pricing page with three plans for my SaaS
Make this dashboard look more modern
Review src/components/PricingCard.tsx and fix the design issues
```

Vague words like "modern" or "clean" are fine. The skill turns them into measurable rules.

### 2. The agent picks a mood and the rules

Before writing code, the agent detects your stack, the page type and the audience, then states its plan in one line:

```
Type: Landing | Mood: Playful | Stack: Tailwind CDN | Concept: toy workshop — chunky, tilted, warm | Signature: custom SVG robot mascot + interactive block builder
```

The **mood** sets how much color, depth, radius and decoration the page gets. A kids' coding site (Playful) keeps its gradients, mascot and supporting colors. A finance dashboard (Trust) gets one accent, soft shadows and a single highlighted card. The **page type** decides the layout rules: a dashboard gets F-pattern, bento metrics and skeleton states; a form gets steps; a blog gets a 65ch reading column. Accessibility, the 8pt grid and the single primary button apply everywhere. If the plan isn't what you want, say so before it builds.

### 3. The agent builds, audits, renders and fixes

After writing the UI, the agent runs the audit on the files it touched:

```
$ python3 scripts/uitools.py audit src/components/PricingCard.tsx
== src/components/PricingCard.tsx: 3 issue(s)
  [FAIL] wcag-aa: L5 text-slate-400 on bg-white = 2.56:1 (need 4.5, fix -> text-slate-500, keep the hue)
  [WARN] single-primary-cta: 2 solid buttons in one block (lines [6, 7]); keep 1 solid, rest outline/ghost
  [INFO] nested-radius: L4 inner radius 24px inside 24px with 8px padding; use 16px (rounded-2xl)

SUMMARY FAIL=1 WARN=1 INFO=1
```

It fixes every FAIL, fixes or justifies each WARN, and repeats until FAIL is 0. Then it renders the page and checks the screenshot: where the eye lands first, whether it matches the mood, whether anything looks empty, stretched or boxed-in. A page can pass every rule and still look grey and flat; the screenshot catches that.

```
$ python3 scripts/render.py index.html --out shot.png --check --dark
```

| Level | Meaning | What happens |
|---|---|---|
| FAIL | Breaks a hard rule, e.g. unreadable contrast or more than 2 fonts (relaxed to INFO in Playful/Bold) | Always fixed |
| WARN | Likely mistake, e.g. two solid buttons or 10px spacing | Fixed or explained |
| INFO | Refinement, e.g. 12px instead of 8/16px, frame wrappers, borders on every card | Reviewed |

### 4. Read the report

The agent ends with a short summary: page type, mood and stack, the rules it applied with concrete values, the audit result with any deliberate exceptions, and the screenshot with its first-glance verdict.

### Using the script without an agent

The script works on its own:

```bash
# Is this color pair readable?
python3 scripts/uitools.py contrast slate-400 white

# Audit a shadcn project, including dark-theme tokens
python3 scripts/uitools.py audit src/app/page.tsx src/components/*.tsx --css src/app/globals.css
```

To run the audit on every pull request, add a step to your project's workflow. The job fails on any FAIL:

```yaml
- run: python3 path/to/classic-ui-design-principles/scripts/uitools.py audit $(git ls-files '*.tsx') --css src/app/globals.css
```

## Script reference

`uitools.py` runs standalone with zero dependencies (Python 3 stdlib only); `render.py` needs Playwright + Chromium.

```bash
python3 scripts/uitools.py contrast pink-400 pink-100
# #f472b6 on #fce7f3: 2.25:1 | AA text(4.5): FAIL | AA large/UI(3.0): FAIL
#   fix -> pink-700 / #cc1072 (>= 4.5:1, same hue)

python3 scripts/uitools.py scale --base 16 --ratio perfect-fourth
python3 scripts/uitools.py radius 24 8
python3 scripts/uitools.py snap 13 22 --grid 8
python3 scripts/uitools.py audit index.html src/App.tsx --css app/globals.css --mood trust
python3 scripts/render.py index.html --out shot.png --check [--dark] [--width 1440]
```

The audit works per element, not per file:

- **Spacing:** values off the 4px grid are WARN; Tailwind half-steps (6, 10, 14px) and 4px fine-tunes off the 8px grid are INFO
- **Contrast:** text/background pairs against the composited background (translucent layers like `bg-white/10` are blended over their ancestors); resolves Tailwind v3 palette names, arbitrary hex, `dark:` variants and shadcn HSL tokens from both `:root` and `.dark` passed with `--css`. Background utilities like `bg-cover` are ignored, `bg-transparent` falls through to the parent, images and unknown custom colors are skipped rather than guessed; text on a gradient is checked against each color stop
- **Single primary CTA:** solid buttons per section/card, including `bg-primary` and shadcn `<Button>` default/destructive variants
- **Nested radius:** child radius vs. parent radius minus parent padding
- **Line length:** long paragraphs without `max-w-prose` / `<= 65ch` on themselves or an ancestor (skipping multi-column grids)
- **Fonts:** more than 2 families across CSS, Google Fonts and `next/font` (relaxed to INFO in Playful/Bold, up to 3 recommended)
- **Miller / states:** navs with more than 7 links, dynamic lists without skeleton or empty states, `opacity-0` start states (`reveal-needs-js`)
- **Fitts:** solid primary buttons shorter than 40px (guide target >= 44px)
- **Sterility:** frame wrappers (a box whose only child is another rounded box), borders on most cards with no shadows (skipped for technical/editorial), flat type hierarchy (mostly one size and bold), grey-only charts
- **Mood (`--mood`):** `stock-look` on default Tailwind accents with neutral fonts; with `playful`/`bold`, fewer than 3 hues, mascot (`no-drawn-mascot`), `card-sameness`, `bold-headline-size`; with `trust`, `low-color`; with `playful`/`bold`/`trust`, `no-hero-surface`; with `editorial`, `headline-measure`, `left-stacked-column`, `edge-align`, `width-funnel`, `editorial-leading`, `no-serif`; with `technical`, soft radii, no mono face, heavy shadows

Contrast fixes suggest the nearest passing shade of the **same hue** (`text-pink-700`), never grey. Tailwind v4 `oklch` colors and runtime CSS variables are not resolved; check those with `contrast`.

`render.py` works offline (with `node`/`npm`): if the Tailwind CDN or Google Fonts are unreachable, it installs/caches `tailwindcss@3` locally (using inline `tailwind.config`) and inlines fonts from `@fontsource` packages.

The audit exits with code 1 when any FAIL is found, so it can run in CI.

## Benchmark

Blind A/B runs using 5 persona judges (`bench/judges.json`), 2 fix rounds each, rendered with Playwright + Chromium (see [bench/runs/README.md](bench/runs/README.md) for the trust hierarchy across runs `run2`–`run8`):

- **`run8/` (pre-registered held-out validation v2, unseen briefs, frozen skill `fc3a31b`):** 6 pairs (12 pages generated by Gemini 4 Hydrogen Low, 30 blind votes by 5 Gemini 4 Neon Medium judges):
  - **25/30 (83%)** skill win rate (95% CI 73%–93%; pair majority **6/6**, exact sign test **p = 0.0312**, Nermin low-vision **5/6 = 83%**, `hierarchy and readability` **+0.93**, near-matched **260.8 vs 246.5** lines)
  - Mood split: `editorial` 2/2, `technical` 1/1, `bold` 1/1, `playful` 1/1, `trust` 1/1
  - **0/6 vs 3/6** pages with serious axe-core issues (mean non-axe layout WARNs: `0.0` vs `0.3`; see [bench/runs/run8/RESULTS.md](bench/runs/run8/RESULTS.md))
- **`run7/` (pre-registered held-out validation, unseen briefs, frozen skill `13ef373`):** 10 pairs (20 pages generated by Claude Haiku, 50 blind votes by 5 Claude Sonnet judges):
  - **38/50 (76%)** skill win rate (95% CI 60%–88%; pair majority **9/10**, exact sign test **p = 0.0215**)
  - Mood split: `bold` 2/2, `playful` 2/2, `technical` 2/2, `trust` 2/2, `editorial` 1/2
  - **0/10 vs 9/10** pages with serious axe-core issues (mean `--check` WARNs: `0.0` vs `1.2`; see [bench/runs/run7/RESULTS.md](bench/runs/run7/RESULTS.md))
- **`run4/` (cross-model v6 run, all brief tiers `v,r,m`):** 15 pairs (30 pages generated by Gemini 4 Hydrogen Low, 75 blind votes by 5 Gemini 4 Neon Medium judges):
  - **52/75 (69%)** skill win rate (95% CI 49%–87%; pair majority **10/15**, `p = 0.30`; vague prompts `v`: **21/25 = 84%**)
  - **0/15 vs 11/15** pages with serious axe-core issues (`--check` WARNs: `0.0` vs `0.9`; see [bench/runs/run4/RESULTS.md](bench/runs/run4/RESULTS.md))
- **`run3/` (`r,m` briefs, Haiku/Haiku):** 20 pairs (40 pages, 100 votes):
  - **90/100 (90%)** skill win rate (95% CI 83%–96%, **20/20** pair majorities, `0/20 vs 18/20` serious axe issues; see [bench/runs/run3/RESULTS.md](bench/runs/run3/RESULTS.md))

## Tests

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the suite on Python 3.10 and 3.13 for every push and pull request.

## License

MIT
