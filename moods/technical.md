# Technical mood notes

- Dark-first neutral layers (zinc/slate 950 → 900 → 800), 1px borders, 4–8px radius, mono for labels, numbers and IDs, dense `h-8` controls.
- Fill every panel: a log or table shows 12+ rows at load, charts have continuous lines, labelled axes and a legend, text and code never overflow their box. A half-empty panel is the most common failure; fix `empty-panel` by adding real rows or data, not by shrinking the panel.
- On a dark page, dark neutral buttons (`bg-zinc-800`) are secondary surfaces, not primary CTAs; the primary action is the one accent-colored button.

Content floor: top bar or page header with actions, 4+ KPIs with deltas, a multi-series chart with legend, a ranked or status list, a table or log stream, one alert/empty/error state shown, a code or detail panel where relevant.

Distinctive, not generic (lost 4/6 blind pairs for looking like a default SaaS template):
- Pick one identity: an ops console (dark, mono, live status dots, color-coded severity) or a light data-dense product. Do not mix; a light page with grey cards and a blue button reads as a template.
- Give it a signature element: a live multi-series chart with a threshold line and annotation, a host/service detail side panel, or a severity-coded alert strip. Show the selected row highlighted and its detail panel open at load.
- Use real names, IDs, timestamps and units in the data (service names, regions, p95 ms, SLO %), never lorem or round placeholder numbers.
- Keep it dense: tables 12+ rows, text 12-13px mono for IDs, tabular-nums for every number column.
