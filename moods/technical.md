# Technical mood notes

- Dark-first neutral layers (zinc/slate 950 → 900 → 800), 1px borders, 4–8px radius, mono for labels, numbers and IDs, dense `h-8` controls.
- **Single ops identity + 1 focal telemetry/workflow surface** (e.g. an SLO latency chart, live log/trace stream, or interactive service/build inspector) + only 1-2 brief-driven companion panels. Do not force every technical screen into a 7-panel Datadog clone.
- **Panel craft (when included):** populate any table or log stream densely enough to avoid half-empty boxes (typically 8-12 real rows with real IDs, timestamps, and units); wrap code snippets in `overflow-x-auto` with dark-themed scrollbars (`scrollbar-color` / sleek dark track), and ensure header status pills do not overlap nav links at intermediate desktop widths (`850-1024px`). Charts have continuous lines, labelled axes and a legend.
- **Every chart carries axes:** x-axis ticks with time or category labels, y-axis ticks with units (ms, %, req/s), a legend for more than one series, and at most one threshold line with a label. A chart without axis labels is a decoration; draw them as SVG `<text>` with 8px clearance from lines and bars.
- **Code and log blocks never overflow:** `overflow-x-auto`, `max-w-full`, `min-w-0` on the grid column that holds them, and `whitespace-pre` only inside that scroll box; check the render for text running out of its box (`--check` reports `clipped-content`).
- Floor for a dashboard (use what the brief names): a KPI strip (3+ numbers with units and deltas), one focal chart with labelled axes, one dense table or log (8+ real rows), and a code snippet when the brief asks for one. Fill the panel instead of leaving it half empty.
- On a dark page, dark neutral buttons (`bg-zinc-800`) are secondary surfaces, not primary CTAs; the primary action is the one accent-colored button.

Distinctive, not generic:
- Pick one identity: an ops console (dark, mono, live status dots, color-coded severity) or a light data-dense product. Do not mix; a light page with grey cards and a blue button reads as a template.
- Give it a signature element: a live multi-series chart with a threshold line and annotation, a host/service detail side panel, or a severity-coded alert strip. Show the selected row highlighted and its detail panel open at load.
- Use real names, IDs, timestamps and units in the data (service names, regions, p95 ms, SLO %), never lorem or round placeholder numbers.
- Keep it dense: text 12-13px mono for IDs, tabular-nums for every number column.
