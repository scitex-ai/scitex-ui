<!-- ---
!-- Timestamp: 2026-07-28
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-ui/docs/adr/0002-shell-gesture-wiring.md
!-- --- -->

# ADR 0002 — Ship mobile-swipe with the shell; delete sidebar-drawer-gesture

- **Status**: Accepted
- **Date**: 2026-07-28
- **Deciders**: scitex-ui (agent)
- **Affects**: `static/scitex_ui/ts/shell/mobile-swipe.ts`,
  `static/scitex_ui/ts/shell/sidebar-drawer-gesture.ts` (removed),
  `static/scitex_ui/js/shell/mobile-swipe.js` (new bundle),
  `templates/scitex_ui/standalone_shell.html`,
  `static/scitex_ui/ts/shell/index.ts`,
  `tests/develop/test_shell_ts_reachability.py` (new guard)

## Context

Two touch-gesture modules shipped in `ts/shell/` and were reachable from
nothing: absent from the `ts/shell/index.ts` barrel, imported by no module
in this package, imported by no consumer, referenced by no template, and
with no compiled counterpart under `js/`. They had been written, debugged
and exported (`export function init()`, PR #86) — but a caller was never
added, so no browser ever ran them.

This is the same defect class ADR 0001 found for the element inspector,
and the same class as the 0.9.0 unregistered components and the 0.11.1
unlinked stylesheet: **the artifact ships, the wiring that gives it force
does not, and nothing fails on either side.**

The two modules look alike but the evidence separates them, so they get
different answers.

### What each module actually targets

`mobile-swipe.ts` operates on `#workspace-three-col`, `.stx-shell-sidebar`,
`.stx-shell-sidebar__header` and `.panel-toggle-btn`. **`standalone_shell.html`
renders all of them** (`#workspace-three-col` at line 63; 18 `.stx-shell-sidebar`
occurrences). This is shell-owned DOM: a consumer of the shell cannot
meaningfully decline the shell's own mobile behaviour.

`sidebar-drawer-gesture.ts` operates on `#workspace-sidebar`, `#sidebar-inner`
and the `.drawer-open` class. **scitex-ui renders none of them, and defines
`.drawer-open` nowhere.** They belong to scitex-cloud, which renders the
markup (`templates/global_base_partials/workspace_sidebar.html`), owns the
CSS (`static/shared/css/components/workspace-sidebar-responsive.css`), and
**already implements the same gesture** — `static/shared/ts/components/sidebar/index.ts`
attaches `touchstart`/`touchend` to `sidebarInner` and toggles `drawer-open`,
documented as "Mobile drawer with backdrop + swipe-to-close".

So one module is shell behaviour with no caller, and the other is a
duplicate of a working consumer implementation, written against DOM this
package does not own.

## Decision

**1. `mobile-swipe.ts` — the shell wires it itself, via the ADR 0001
mechanism.**

Bundle it to a self-contained IIFE at `static/scitex_ui/js/shell/mobile-swipe.js`
and load it from `standalone_shell.html` with `defer`, next to
`standalone-shell-init.js`. Rebuild with:

```
cd src/scitex_ui/static/scitex_ui
npx esbuild ts/shell/mobile-swipe.ts --bundle --format=iife \
  --outfile=js/shell/mobile-swipe.js
```

Not gated behind DEBUG/staff as the inspector is — this is user-facing
product behaviour, not a developer tool. It is unconditional because it
self-guards twice over: `init()` returns early when `#workspace-three-col`
is absent, and the listeners only attach while `(max-width: 768px)` matches.

It is loaded rather than left to `initShell()` because **`initShell` reaches
nothing today** — no template in this package loads a `type="module"` script,
and no consumer calls it. Wiring a dead module into an unreached entry point
would have looked like a fix and changed nothing. `init` is also re-exported
from the barrel as `initMobileSwipe`, for consumers that bundle the
TypeScript themselves and want to control init order.

**2. `sidebar-drawer-gesture.ts` — deleted.**

Keeping it has no good outcome. Left unwired it stays dead source. Wired
up it would attach a second, competing swipe handler to the element
scitex-cloud's own sidebar controller already manages, on markup scitex-ui
never renders. Barrel-exporting it without wiring would publish that hazard
as an API. The working implementation lives in scitex-cloud, and git history
retains this one.

**3. A guard test, so the class cannot recur silently.**

`tests/develop/test_shell_ts_reachability.py` enumerates every top-level
`.ts` under `ts/shell/` and requires each to be reachable — named in a
barrel `export … from`, or built into a `js/` bundle that a template loads.
Recomputed from the filesystem, so it catches the *next* orphan too, in the
idiom of `test_css_bundle_index.py`.

## Consequences

- Apps extending `standalone_shell.html` get mobile pane-collapse gestures
  with no template edit and no config, on any viewport ≤768px.
- The committed `.js` is a generated artifact, as in ADR 0001. scitex-ui
  still has no JS build pipeline; the banner carries the rebuild command
  and the guard test fails if the bundle disappears.
- Two known orphans remain and are **allow-listed by name** in the guard
  rather than hidden by it, because each needs its own decision:
  - `workspace-shell.ts` — a page controller with no exports at all, which
    fetches `/workspace/content/<module>/`, a scitex-cloud URL. Either it
    belongs in the consumer or it needs a shell page to live on.
  - `standalone-terminal.ts` — its own docstring claims it is "Used by
    standalone apps (figrecipe, etc.) via the Django standalone_shell.html",
    which is false: that template loads no such script.
