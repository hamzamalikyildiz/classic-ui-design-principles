# shadcn/ui & Base UI Baseline Patch (`reference/shadcn-baseline.md`)

## 1. Why a Baseline Patch is Required

Stock `shadcn/ui` and Base UI primitives ship with compact defaults that collide with classic Fitts, readability, and depth rules (`reference/rules.md`):
- **Undersized targets:** Default `h-9` (36px) buttons/inputs and `h-8` (32px) `sm` buttons fall below the 40px control floor and 44px (`h-11`) primary CTA / touch floor.
- **Illegible micro-badges:** Custom `10px`/`11px` badge overrides break the `12px` (`text-xs`) tag minimum.
- **Border-only flat cards:** Stock `<Card>` uses `border bg-card` with zero elevation or surface shift, triggering `border-heavy` sterility in `Trust`, `Playful`, and `Bold` moods.
- **Generic radius & unverified tokens:** Fixed `--radius: 0.625rem` (10px) ignores mood geometry, and tinted `oklch`/`hsl` `--muted-foreground` or `--ring` tokens can fail WCAG AA (4.5:1 text, 3:1 UI/focus).

Apply this baseline **once** in `components/ui/*.tsx` and `globals.css` before building screens (`reference/app-flow.md` Step 2). Never patch screen instances ad hoc while leaving `components/ui/` at stock defaults.

## 2. Baseline Value Table

| Component | shadcn default | Skill baseline |
|---|---|---|
| Button `default` | `h-9` (36px) | `h-10` (40px); primary page CTA `size="lg"` = `h-11` (44px) |
| Button `sm` | `h-8` (32px) | `h-9` (36px); reserve `h-8` strictly for dense desktop toolbars |
| Button `icon` | `size-9` | `size-10` (`size-11` on touch/mobile primary actions) |
| Input / Select | `h-9` | `h-10` (`h-11` on form-heavy/auth screens) |
| Badge | `text-xs` / `10px` variants | `text-xs` (12px) minimum, `px-2.5 py-0.5`, `font-medium` |
| Card | `border` + no shadow | Trust/Playful/Bold: `border-transparent shadow-sm` (+ interactive hover `shadow-md`); Technical/Editorial: `border border-border/70`, no shadow |
| Table row | `h-10` | `h-12`, numeric cells `tabular-nums text-right` |
| Focus ring | `ring-[3px] ring-ring/50` | keep; verify `--ring` passes ≥ 3:1 contrast against surface |
| Radius (`--radius`) | `.625rem` (10px) | set from mood profile (`Playful 1.5rem`, `Bold 1rem–1.5rem`, `Trust 0.75rem–1rem`, `Technical 0.375rem–0.5rem`, `Editorial 0.25rem–0.5rem`) |
| Toast (`sonner`) | default | `richColors`, `bottom-center`, `4000ms` duration, actionable Undo button for mutations |

## 3. Copy-Paste `cva` & Component Diff Patches

### `components/ui/button.tsx` (`buttonVariants`)
Raise all size tiers by 4px and add a `toolbar` size for dense desktop chrome:
```diff
       size: {
-        default: "h-9 px-4 py-2 has-[>svg]:px-3",
-        sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
-        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
-        icon: "size-9",
+        default: "h-10 px-4 py-2 has-[>svg]:px-3",
+        sm: "h-9 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
+        lg: "h-11 rounded-md px-6 has-[>svg]:px-4",
+        icon: "size-10",
+        toolbar: "h-8 rounded-md gap-1 px-2.5 text-xs",
       },
```

### `components/ui/badge.tsx` (`badgeVariants`)
Lock badge text at `text-xs` (12px) with `px-2.5 py-0.5 font-medium` (never `text-[10px]`):
```diff
 const badgeVariants = cva(
-  "inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium ...",
+  "inline-flex items-center justify-center rounded-md border px-2.5 py-0.5 text-xs font-medium ...",
```

### `components/ui/input.tsx` (and `select.tsx` trigger)
Raise height to `h-10` (`h-11` on auth/form screens) with `text-base md:text-sm`:
```diff
-  className={cn("... flex h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs ... md:text-sm", className)}
+  className={cn("... flex h-10 w-full min-w-0 rounded-md border bg-transparent px-3 py-2 text-base shadow-xs ... md:text-sm", className)}
```

### `components/ui/card.tsx` (Mood-Aware Surface)
Match surface elevation to the active mood (in dark mode, step `--card` above `--background` + `dark:border-white/10`):
```diff
-// Stock: "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm"
+// Trust / Playful / Bold (depth + hover elevation):
+className={cn("bg-card text-card-foreground flex flex-col gap-6 rounded-xl border border-transparent py-6 shadow-sm transition-shadow hover:shadow-md dark:border-white/10", className)}
+// Technical / Editorial (crisp 1px hairline, no shadow):
+className={cn("bg-card text-card-foreground flex flex-col gap-6 rounded-lg border border-border/70 py-6 shadow-none", className)}
```

### `components/ui/table.tsx`
Set `TableRow` to `h-12` (48px), cells `text-sm` (≥14px), and numeric columns `tabular-nums text-right`:
```diff
-  className={cn("hover:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors", className)}
+  className={cn("hover:bg-muted/50 data-[state=selected]:bg-muted h-12 border-b transition-colors", className)}
```

### `app/globals.css` (`--radius` & `oklch` Contrast Check)
```css
:root {
  /* Playful: 1.5rem | Bold: 1rem–1.5rem | Trust: 0.75rem–1rem | Technical: 0.375rem–0.5rem | Editorial: 0.25rem–0.5rem */
  --radius: 0.75rem;
}
```
Verify `:root` and `.dark` `oklch(...)`/`hsl(...)` tokens with `python3 scripts/uitools.py contrast <fg> <bg>` (and `audit --css app/globals.css`) so `--foreground`/`--muted-foreground` pass ≥ 4.5:1 and `--ring`/`--border` pass ≥ 3:1 against `--background` and `--card`. Mount `<Toaster richColors position="bottom-center" duration={4000} />` with an Undo action on mutations.

## 4. Static Audit Rule (`shadcn-defaults`)

`python3 scripts/uitools.py audit <file> --mood <mood>` scans component definitions and JSX for unpatched stock classes and reports `INFO shadcn-defaults` on:
- **`cva` button height:** `cva` or button classes with `h-8` on `default` or `sm` variants.
- **Micro-badge text:** Badge classes using `text-[10px]` or `text-[11px]` below the 12px (`text-xs`) floor.
- **Bordered shadowless cards:** Card surfaces in `trust`, `playful`, or `bold` moods with `border` and no shadow (`shadow-sm`/`md`/`lg`) or `border-transparent`.
