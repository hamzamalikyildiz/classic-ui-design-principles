# UI State Matrix, Time Budgets & Result Micro-Moments

Design dynamic screens and async flows for time and failure, not just the happy path. Never ship a bare spinner with `"Loading..."` or wipe user input on error.

## 1. The 9-State Matrix

| State | Trigger / rule | What to show & copy tone | Primary action | A11y (`aria-live`, `aria-busy`, focus) |
|---|---|---|---|---|
| **Empty** | **First-use**: 0 records created.<br>**Filtered/search**: query returns 0 matches | **First-use**: SVG spot + value pitch (`"Upload a CV to score role fit"`).<br>**Filtered**: active filter summary (`0 matches for "Rust"`). | **First-use**: single primary setup CTA (`"Upload CV"`).<br>**Filtered**: `"Clear filters"` | **First-use**: label landmark; focus CTA.<br>**Filtered**: `aria-live="polite"` `"0 results"`; keep focus in input |
| **Loading** | **< 1s**: show nothing (`150–200ms` delay avoids flash).<br>**1–3s**: matching-layout skeleton | **< 1s**: keep current view.<br>**1–3s**: `animate-pulse` skeleton matching exact row/card geometry. | Disable in-flight submit trigger only | Container `aria-busy="true"`; skeleton nodes `aria-hidden="true"` |
| **Long-loading (> 3s)** | Operation exceeds `3s` (AI pass, file parse, export, batch job) | Escalate to **> 3s Long-Running Operation Pattern** below (never just a bare spinner + `"Loading..."`). | `"Cancel"` + `"Notify when ready"` (run in background) | `role="progressbar"` or `role="status"`; `aria-live="polite"` on stage changes only |
| **Error** | Network error, 4xx/5xx, timeout, or validation fail | **Preserve user input.** Plain human explanation (`"Could not parse PDF — password-protected"`), never raw codes alone. | Specific recovery action: `"Retry"` or `"Edit input"` | `role="alert"`, `aria-invalid="true"` + `aria-describedby` on bad fields; focus first error or recovery CTA |
| **Partial data** | Optional metrics or secondary fields return `null` / time out | Render available fields cleanly; mark missing optional metrics as explicit neutral fallback (`—` / `"Pending"`). Never hide the whole screen for one null field. | Inline `"Retry section"` or `"Add detail"` | Fallback uses `aria-label="Metric pending"` so screen readers do not skip dashes |
| **Locked / unauthorized** | Gated by role, plan tier, or expired auth | Explain *why* locked (`"Requires Admin role"` / `"Pro feature"` / `"Session expired"`) and preview value behind lock badge. | Exact unlock path: `"Request access"`, `"Upgrade"`, or `"Re-auth"` | Disable mutated actions (`disabled` / `aria-disabled="true"`) linked via `aria-describedby` |
| **Success** | Mutation, save, or analysis finishes | Clear confirmation + subtle **Result Micro-Moment** in context (updated score, highlighted row). Never a dead-end flash that wipes context. | Next workflow step (`"Apply suggestion"`, `"Export"`) or `"Undo"` | `role="status"` (`aria-live="polite"`), `aria-busy="false"`, focus result heading |
| **Offline** | `navigator.onLine === false` or heartbeat lost | Honest banner (`"Offline — reading cached data from 2m ago"`). Read cached data and keep local drafts editable. | `"Retry"` or queued action (`"Queued — runs when back online"`) | `role="status"` (`aria-live="polite"`) on disconnect/reconnect; disable network actions |
| **Stale / revalidating** | Background refresh (SWR/polling) or tab refocus | Keep stale content readable + unobtrusive `"Updating..."` or timestamp indicator (`"Updated 4m ago"`) instead of blowing away the view with a skeleton. | Subtle `"Refresh"` trigger | `aria-busy="true"` on refreshing region; `aria-live="polite"` only if values change |

## 2. > 3 Second Long-Running Operation Pattern

For `3–60+ second` operations (e.g., a `30–60s` AI CV analysis), replace bare spinners with six steps:

1. **Named stages with live current-stage highlight:** Show a 3–5 step pipeline (`Parsing CV -> Matching experience -> Writing suggestions`). Check finished steps, highlight active stage, dim upcoming steps.
2. **Elapsed time + honest estimated range:** Show elapsed time + range (`Elapsed 18s · Usually 30–60s` in `tabular-nums`). Past the upper bound, switch copy honestly (`"Finalizing..."`) instead of freezing at `99%`.
3. **Productive waiting / fill:** Show a tentative preview, stream partial results inside skeletons as stages resolve (e.g., parsed header + skills at `8s`), or show contextual domain tips.
4. **Cancel AND run-in-background option:** Offer both `"Cancel"` and `"Notify when ready"` (run in background).
5. **Failure recovery:** Retry the failed step only (`"Retry step 3"`) while keeping all user inputs intact.
6. **Smooth handoff into result micro-moments:** Transition cleanly into the result workspace (`reference/motion.md`) and focus the result summary.

## 3. Result Micro-Moments

Micro-moments turn static templates into a live product:

- **Score count-up + progress ring fill:** Step metrics over `400–600ms` (e.g., score stepping `69 -> 73` using `tabular-nums` + SVG `stroke-dashoffset` fill) with an `aria-live="polite"` announcement (`prefers-reduced-motion`: instant `73`).
- **Brief `1.2s` highlight on accepted suggestion row:** Flash a semantic/brand tint (`bg-emerald-500/15`) for `1.2s` on the accepted suggestion row inside the live preview (`prefers-reduced-motion`: instant border accent).
- **Optimistic UI update + undo toast:** Update UI in-place and show a `4s` toast with an actionable `"Undo"` button, reverting cleanly on click or failure.
- **Smooth settled insertion of new list items:** Insert new rows with a `180–240ms` height/opacity settle and reserved dimensions without layout jump.

## 4. Mandatory State Coverage Table Template

Include per prioritized screen in App/Page reports (`yes` / `-` / `n/a`):

| Screen | Empty | Loading | Long (>3s) | Error | Partial | Locked | Success | Offline | Stale |
|---|---|---|---|---|---|---|---|---|---|
| `<Screen 1>` | yes | yes | yes | yes | yes | - | yes | - | yes |
| `<Screen 2>` | yes | yes | n/a | yes | yes | yes | yes | yes | yes |
