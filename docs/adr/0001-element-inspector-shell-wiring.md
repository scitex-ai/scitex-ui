<!-- ---
!-- Timestamp: 2026-05-27
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-ui/docs/adr/0001-element-inspector-shell-wiring.md
!-- --- -->

# ADR 0001 — Ship the Element Inspector shell-wide, DEBUG/staff-gated

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: ywatanabe (lead), head-ywata-note-win (agent)
- **Affects**: `static/scitex_ui/js/utils/element-inspector.js` (new
  bundle), `context_processors.py` (new), `templates/scitex_ui/_element_inspector.html`
  (new partial), `templates/scitex_ui/standalone_shell.html` (include),
  `_components/_element_inspector.py` (registry), and every Django app
  that renders through the scitex-ui shell.

## Context

A full visual DOM inspector already lived in scitex-ui as TypeScript —
`ts/utils/element-inspector.ts` plus 12 helper modules under
`ts/utils/_element-inspector/` and `css/utils/element-inspector.css`. It
implements Alt+I overlay toggling, rectangle selection (Ctrl+Alt+I),
batched scanning (Ctrl+I), and a debug snapshot (Ctrl+Shift+I).

However it was **orphaned dead code**:

- Nothing imported or instantiated the `ElementInspector` class — it is
  absent from the `utils/` barrel, the root `index.ts`, and `initShell()`.
- It was **never compiled** to a browser-loadable artifact. scitex-ui
  ships pre-built standalone JS under `static/scitex_ui/js/` (e.g.
  `js/shell/standalone-shell-init.js`, a self-contained IIFE), but no
  `js/utils/element-inspector.js` existed.
- No template referenced it, so **no Django app ever loaded Alt+I**.

The goal: make the inspector usable across the Django apps that consume
scitex-ui's shell, without shipping a developer tool to end users.

## Decision

Wire the existing inspector in, keeping scitex-ui as the single home.

1. **Bundle** `ts/utils/element-inspector.ts` → a single self-contained
   IIFE at `static/scitex_ui/js/utils/element-inspector.js` via esbuild,
   matching the existing standalone-JS convention. The TS already
   auto-initializes idempotently at module scope, so loading the bundle
   is enough; no entry/init wrapper is added. Rebuild with:

   ```
   npx esbuild src/scitex_ui/static/scitex_ui/ts/utils/element-inspector.ts \
     --bundle --format=iife \
     --outfile=src/scitex_ui/static/scitex_ui/js/utils/element-inspector.js
   ```

2. **Gate** it behind a context processor,
   `scitex_ui.context_processors.element_inspector`, which sets the
   template flag `stx_element_inspector_enabled` when **`settings.DEBUG`**
   is on, **or** the request user is authenticated **and** `is_staff`.
   `settings.SCITEX_UI_ELEMENT_INSPECTOR` (bool) overrides both.

3. **Emit conditionally** via a new partial
   `templates/scitex_ui/_element_inspector.html` that renders the
   `<script>`/`<link>` only when the flag is truthy.

4. **Include shell-wide**: add `{% include "scitex_ui/_element_inspector.html" %}`
   near the end of `<body>` in `standalone_shell.html`, so every app that
   extends the shell inherits Alt+I automatically.

5. **Register** an `ElementInspector` component metadata entry for
   discoverability via `_registry`.

### Gating policy

- Default-off and **safe by omission**: if an app never installs the
  context processor, the flag is absent (falsy) in templates and nothing
  is loaded. The inspector cannot accidentally ship to production.
- DEBUG drives it for local dev; `is_staff` extends it to trusted staff
  on a live site for diagnosing real layout bugs (chosen over
  DEBUG-only); `SCITEX_UI_ELEMENT_INSPECTOR` is the explicit override.

## Consequences

- **Consumers**: to enable Alt+I, an app installs scitex-ui and appends
  `"scitex_ui.context_processors.element_inspector"` to its
  `TEMPLATES[0]["OPTIONS"]["context_processors"]`. Shell-extending pages
  then get the inspector with no template edits. Non-shell pages can
  `{% include "scitex_ui/_element_inspector.html" %}` directly.
- **End users** never receive the ~74 KB bundle (it is not emitted when
  the flag is falsy).
- **Source of truth** stays the TypeScript; the committed `.js` is a
  generated artifact (banner notes the rebuild command). A future build
  step could regenerate it in CI, but hand-rebuild is acceptable for now
  given scitex-ui has no JS build pipeline yet.
