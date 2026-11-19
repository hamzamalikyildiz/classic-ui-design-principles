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
├── SKILL.md            # rule matrix, rule reference, workflow
└── scripts/
    └── uitools.py      # contrast, scale, radius, snap, audit
```

## Install

**Claude Code**

```bash
git clone https://github.com/hamzamalikyildiz/classic-ui-design-principles ~/.claude/skills/classic-ui-design-principles
```

**claude.ai:** zip the `classic-ui-design-principles` folder and upload it in the Skills section of Settings.

## Script

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
- **Contrast:** text/background pairs with the background inherited from the nearest ancestor; resolves Tailwind v3 palette names, arbitrary hex, `dark:` variants and shadcn HSL tokens passed with `--css`
- **Single primary CTA:** solid buttons per section/card, including `bg-primary` and shadcn `<Button>` default/destructive variants
- **Line length:** long paragraphs without `max-w-prose` / ≤80ch on themselves or an ancestor
- **Fonts:** more than two families across CSS, Google Fonts and `next/font`
- **Miller / states:** navs with more than 7 links, lists without skeleton or empty states

Tailwind v4 `oklch` colors and runtime CSS variables are not resolved; check those with `contrast`.

The audit exits with code 1 when any FAIL is found, so it can run in CI.

## License

MIT
