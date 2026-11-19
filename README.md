# classic-ui-design-principles

An agent skill built on classic, time-tested UI design principles. It turns vague UI requests ("make it modern") into measurable design rules. It detects the page type and stack, picks the matching rules, applies them as concrete Tailwind/CSS values and verifies the output with an audit script.

Works with Claude (claude.ai, Claude Code) and any agent that reads `SKILL.md` files.

## What it covers

- **Color:** 60-30-10, WCAG AA contrast, semantic status colors
- **Layout:** 8pt grid, law of proximity, nested border radius, Z/F patterns, bento grid
- **Typography:** modular type scale, 45–75 character line length, max 2 fonts
- **UX laws:** Fitts, Hick, Jakob, Miller, single primary CTA, skeleton and empty states

Rules are selected per page type: landing, dashboard, form, content, mobile, e-commerce, settings, nav and card/modal components.

## Structure

```
classic-ui-design-principles/
├── SKILL.md              # rule matrix, rule reference, workflow
├── scripts/
│   └── uitools.py        # contrast, scale, radius, snap, audit
└── tests/
    └── test_uitools.py   # regression tests (unittest, stdlib only)
```

## Install

**Claude Code**

```bash
git clone https://github.com/hamzamalikyildiz/classic-ui-design-principles ~/.claude/skills/classic-ui-design-principles
```

**claude.ai:** zip the `classic-ui-design-principles` folder and upload it in the Skills section of Settings.

## How to use

### 1. Ask for UI as usual

Once the skill is installed you don't need to mention it. Any request to build or improve UI triggers it:

```
Build a pricing page with three plans for my SaaS
Make this dashboard look more modern
Review src/components/PricingCard.tsx and fix the design issues
```

Vague words like "modern" or "clean" are fine. The skill turns them into measurable rules.

### 2. The agent picks the rules

Before writing code, the agent detects your stack and the page type, then states its plan in one line:

```
Type: Landing | Stack: Next.js + Tailwind + shadcn | Rules: Z-pattern, bento, single CTA, perfect-fourth scale, accent indigo-600
```

The page type decides which rules apply. A dashboard gets F-pattern, bento metrics and skeleton states. A form gets steps and a full-width submit button. A blog gets a 65ch reading column. Accessibility, the 8pt grid and the single primary button apply everywhere. If the plan isn't what you want, say so before it builds.

### 3. The agent builds, audits and fixes

After writing the UI, the agent runs the audit on the files it touched:

```
$ python3 scripts/uitools.py audit src/components/PricingCard.tsx
== src/components/PricingCard.tsx: 3 issue(s)
  [FAIL] wcag-aa: L5 text-slate-400 on bg-white = 2.56:1 (need 4.5, fix -> #627793)
  [WARN] single-primary-cta: 2 solid buttons in one block (lines [6, 7]); keep 1 solid, rest outline/ghost
  [INFO] nested-radius: L4 inner radius 24px inside 24px with 8px padding; use 16px (rounded-2xl)

SUMMARY FAIL=1 WARN=1 INFO=1
```

It fixes every FAIL, fixes or justifies each WARN, and repeats until FAIL is 0.

| Level | Meaning | What happens |
|---|---|---|
| FAIL | Breaks a hard rule, e.g. unreadable contrast or more than 2 fonts | Always fixed |
| WARN | Likely mistake, e.g. two solid buttons or 10px spacing | Fixed or explained |
| INFO | Refinement, e.g. 12px instead of 8/16px or mismatched radius | Reviewed |

### 4. Read the report

The agent ends with a short summary: detected page type and stack, the rules it applied with concrete values, and the final audit result with any deliberate exceptions.

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

Python 3, no dependencies.

```bash
python3 scripts/uitools.py contrast slate-400 white
# #94a3b8 on #ffffff: 2.56:1 | AA text(4.5): FAIL | AA large/UI(3.0): FAIL
#   fix -> #627793 (>= 4.5:1)

python3 scripts/uitools.py scale --base 16 --ratio perfect-fourth
python3 scripts/uitools.py radius 24 8
python3 scripts/uitools.py snap 13 22 --grid 8
python3 scripts/uitools.py audit index.html src/App.tsx --css app/globals.css
```

The audit works per element, not per file:

- **Spacing:** values off the 4px grid are WARN, 4px fine-tunes off the 8px grid are INFO
- **Contrast:** text/background pairs with the background inherited from the nearest ancestor; resolves Tailwind v3 palette names, arbitrary hex, `dark:` variants and shadcn HSL tokens from both `:root` and `.dark` passed with `--css`. Background utilities like `bg-cover` are ignored, `bg-transparent` falls through to the parent, gradients and unknown custom colors are skipped rather than guessed
- **Single primary CTA:** solid buttons per section/card, including `bg-primary` and shadcn `<Button>` default/destructive variants
- **Nested radius:** child radius vs. parent radius minus parent padding
- **Line length:** long paragraphs without `max-w-prose` / ≤80ch on themselves or an ancestor
- **Fonts:** more than two families across CSS, Google Fonts and `next/font`
- **Miller / states:** navs with more than 7 links, lists without skeleton or empty states

Tailwind v4 `oklch` colors and runtime CSS variables are not resolved; check those with `contrast`.

The audit exits with code 1 when any FAIL is found, so it can run in CI.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the suite on Python 3.10 and 3.13 for every push and pull request.

## License

MIT
