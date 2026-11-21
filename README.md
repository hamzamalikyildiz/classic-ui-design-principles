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
├── SKILL.md              # core: flow, mood table, hard rules, tooling (~7 KB)
├── moods/                # per-mood notes: expressive (Playful/Bold), editorial, technical, trust
├── reference/
│   ├── page-types.md     # page-type matrix and mood mapping
│   ├── rules.md          # rule values, anti-patterns, conflict resolution
│   ├── tooling.md        # audit and render.py check details
│   └── visual-quality.md # palette recipe, typography voice, product UI, rhythm
├── bench/                # blind A/B benchmark: briefs, pair builder, scorer
│   └── runs/             # archived benchmark runs (pilot run2 + protocol v2 run3)
├── scripts/
│   ├── uitools.py        # contrast, scale, radius, snap, audit (Python 3 stdlib only)
│   └── render.py         # offline full-page screenshot + --check (Playwright + Chromium)
└── tests/
    └── test_uitools.py   # regression tests (unittest, stdlib only)
```

## Install

**Claude Code**

```bash
git clone https://github.com/hamzamalikyildiz/classic-ui-design-principles ~/.claude/skills/classic-ui-design-principles
```

**claude.ai:** zip the `classic-ui-design-principles` folder and upload it in the Skills section of Settings.

`uitools.py` runs standalone with zero dependencies (Python 3 stdlib only). For screenshots and `--check`, `render.py` needs Playwright and a Chromium/Chrome binary:

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
| FAIL | Breaks a hard rule, e.g. unreadable contrast or more than 2 fonts | Always fixed |
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
- **Line length:** long paragraphs without `max-w-prose` / ≤80ch on themselves or an ancestor
- **Fonts:** more than 2 families (up to 3 in expressive moods) across CSS, Google Fonts and `next/font`
- **Miller / states:** navs with more than 7 links, lists without skeleton or empty states
- **Fitts:** solid primary buttons shorter than 40px
- **Sterility:** frame wrappers (a box whose only child is another rounded box), borders on most cards with no shadows (skipped for technical/editorial), flat type hierarchy (mostly one size and bold), grey-only charts
- **Mood (`--mood`):** with `playful`/`bold`, fewer than 3 hues; with `playful`/`bold`/`trust`, no saturated or gradient hero surface; with `editorial`, display headlines trapped in the reading measure, 3+ container widths, tight leading on long text; with `technical`, soft radii, no mono face, heavy shadows

Contrast fixes suggest the nearest passing shade of the **same hue** (`text-pink-700`), never grey. Tailwind v4 `oklch` colors and runtime CSS variables are not resolved; check those with `contrast`.

`render.py` works offline: if the Tailwind CDN or Google Fonts are unreachable, it compiles Tailwind locally with `npx tailwindcss@3` (using the page's inline `tailwind.config`) and inlines the fonts from `@fontsource` packages.

The audit exits with code 1 when any FAIL is found, so it can run in CI.

## Benchmark

Blind A/B evaluation across 20 pairs (5 moods × 2 briefs × 2 repetitions; 40 pages generated by Haiku with 2 fix rounds each) scored by 5 LLM persona judges (100 votes total):

- **90/100 (90%)** skill win rate across all votes (95% CI 83%–96%)
- **20/20** per-pair majorities (`p = 0.0000`, 4/4 in every mood)
- **0/20 vs 18/20** pages with serious axe-core accessibility issues (mean `--check` WARNs: `0.1` vs `1.6`)

Caveats: judges are LLM personas from the same model family as the generators rather than human raters, and skill pages were longer on average (mean 235 vs 188 lines, 16.1 vs 10.5 KB), creating a length/content-richness confound. See [bench/runs/run3/RESULTS.md](bench/runs/run3/RESULTS.md) for the full breakdown and setup notes.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the suite on Python 3.10 and 3.13 for every push and pull request.

## License

MIT
