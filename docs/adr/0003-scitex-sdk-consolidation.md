<!-- ---
!-- Timestamp: 2026-09-14
!-- Author: scitex-ui (agent)
!-- File: /home/ywatanabe/proj/scitex-ui/docs/adr/0003-scitex-sdk-consolidation.md
!-- --- -->

# ADR 0003 — Consolidate scitex-app + scitex-ui into scitex-sdk

- **Status**: Accepted
- **Date**: 2026-09-14
- **Deciders**: operator (Telegram 5319/5322/5325/5333, 2026-09-14), recorded by scitex-hub
  (app-fleet leader) on `sdk-consolidate-scitex-app-and-scitex-ui-into-scitex-sdk-20260914`
- **Affects**: this package's public surface (Python + npm/static), the
  `scitex_ui` distribution name, every consumer that imports `scitex_ui` or
  installs `@scitex/ui`; scitex-app records the mirror ADR for the `app` half
- **Sibling ADR**: scitex-app's ADR on the same decision (its package is the
  `scitex_sdk.app` half); the two ADRs are the shared record, one per package

## Context

scitex-app and scitex-ui are consumed together as "the SDK": scitex-hub is a
hard dependency of both, every GUI leaf installs both, and this repo's
compass L18 principle ("keep common UI rules in the SDK rather than fixing
each app independently") has been doing work for **two** distributions with
one name. The operator's framing (2026-09-14): saying "SDK (scitex-app,
scitex-ui)" every time is tiring; having to restate it shows they should be
one unit. The decision:

- **One repo, one distribution: `scitex-sdk`**, split as
  `scitex_sdk.app` (from scitex-app) and `scitex_sdk.ui` (from scitex-ui).
- **Facade first**: `scitex_sdk` starts by re-exporting today's two packages
  without moving code. The operator (15:07Z): "scitex-sdk is a thin facade
  that re-exports today's scitex-app and scitex-ui — `scitex_sdk.app =
  scitex_app`, `scitex_sdk.ui = scitex_ui`."
- **Prompt mechanical migration**: once the facade releases, consumers move
  `scitex_app → scitex_sdk.app`, `scitex_ui → scitex_sdk.ui` in one PR per
  repo; "don't let consumers linger on the old imports" (15:08Z). Small API
  adjustments are acceptable now and must be recorded in a CHANGELOG.
- **The app/ui boundary is preserved inside the SDK.** Consolidation is a
  packaging decision, not a code decision: `scitex_sdk.ui` must never import
  `scitex_sdk.app` and vice versa, and the existing dependency direction
  (neither package imports the other today; they meet only in consumers'
  settings) stays true inside the combined package.

## Decision (the `scitex_sdk.ui` half — this package)

### 1. What moves

The `scitex_ui` package (Python: `src/scitex_ui/`, including
`templates/`, `locale/`, `static/`) moves into the scitex-sdk repo as the
`ui` subpackage. The static asset tree (`static/scitex_ui/{css,ts,react,
js,img}` — 18 MB, measured 2026-09-14) moves with it, because it is
addressed by the Django app label: `AppDirectoriesFinder` resolves
`scitex_ui/...` static paths by the installed app name, so the app label
`scitex_ui` must survive the move (it does, as `scitex_sdk.ui`'s inner
module name — see step 3). Nothing in the asset layout changes; no CSS/TS
file path changes at the move step.

### 2. The re-export surface (scitex-sdk repo, this package's content)

The facade `scitex_sdk.ui` must re-export **this package's documented public
surface**, identity-verified (`scitex_sdk.ui.X is scitex_ui.X`), exactly as
scitex-app has done for its half (23/23 identity check,
`tests/test_facade_identity.py`, reported 2026-09-14 15:15Z). The surface,
measured from this repo (2026-09-14, develop `a02e0ea`):

- **Python `__all__`** (`test_public_api.py::test_all_contains_expected`
  pins it): `__version__`, `get_component`, `list_components`,
  `get_static_dir`, `get_docs_path`.
- **Documented modules** (`docs/sphinx/api/scitex_ui.rst` automodule list —
  the "every public module is documented" contract enforced by
  `test_api_docs_list_every_public_module.py`): `scitex_ui`, `apps`
  (`ScitexUiConfig`), `branding` (`shell_context`, `shell_title`,
  `launcher_context`), `context_processors`, `middleware`
  (`ElementInspectorMiddleware`), `mount` (`mount_context`, `api_url`,
  `mount_prefix`), `testing` (`assert_has_route_away`, ...), plus the
  documented private components.
- **npm**: `@scitex/ui` — 52 `exports` entries (48 exact + 4 wildcard),
  `main`/`types` at `.../ts/react/index.ts` (see §4 for the naming decision).

**DISCREPANCY RECORDED (15:15Z scitex-app report vs this repo's pinned
surface):** the scitex-app facade report lists `scitex_sdk.ui` re-exporting
5 names — `get_component`, `list_components`, `get_static_dir`,
`get_docs_path`, **`register_component`** — which omits `__version__` (pinned
by `test_all_contains_expected`) and includes `register_component` (used by
every component module, but not in `__all__`). The facade surface must be
**at least** the pinned `__all__`; whether `register_component` (and the
documented modules) belong in `scitex_sdk.ui`'s top level is decided at the
facade-review step (scitex-app prepares, scitex-ui reviews per the card).
The identity check, not the name count, is the correctness bar.

### 3. Versioning

The facade has its **own independent version** (scitex-app reports
`scitex-sdk 0.1.0` as of 2026-09-14), with declared floors on the wrapped
packages (`scitex-app>=0.24.0`, `scitex-ui>=0.20.3` — published floors, not
dev-only: the initial `>=0.20.4` pin was caught and corrected, 15:15Z).
`scitex_sdk.ui.__version__` is **not** this package's version — this package
keeps shipping its own `__version__` (0.20.x) during and after the facade
step; consumers who need "the SDK" pin the umbrella, consumers who need "the
ui" keep pinning `scitex-ui`. Both are valid during the migration window.

### 4. JS/CSS assets and npm naming (my part of the contract)

- **Step 1 (facade): no npm name is registered or needed.** `@scitex/ui` is
  `private: true` in this repo's `package.json` — it has never been a public
  npm publication; every consumer today takes it via `file:` (scitex-hub) or
  vendored copy. There is nothing to rename, nothing to deprecate.
- **Step 2+ (implementation move): the npm name follows the app/ui
  boundary.** The JS/CSS asset surface (52 `exports` entries, `main`/`types`
  path) moves into the scitex-sdk repo **unchanged in layout** — consumers
  import by **content** (`@<name>/ts/shell`, `@<name>/ts/app/app-launcher`,
  css paths via Django static, not npm). The name is the one open question
  for the move step, with the constraint that **the 48 exact export keys
  must not change** (they are the consumer contract; `figrecipe`'s vite
  config, hub's `file:` imports, and every leaf's `@scitex/ui/...` specifiers
  reference them). Two options, owner decides at the move step:
  - **`@scitex/sdk` with `./ui/*` subpaths** — matches the umbrella name,
    but changes every existing specifier (a consumer rewrite on top of the
    Python rewrite, i.e. TWO mechanical rewrites per repo);
  - **keep `@scitex/ui`** — zero specifier change, the name is slightly
    narrower than the repo it ships in.
  Recommendation (recorded, not decided): **keep `@scitex/ui`** at the move.
  The Python rename is the consolidation; the npm specifier is a consumer
  contract that would gain nothing and cost every leaf a second rewrite for
  the rename itself. Revisit only if the umbrella's other assets (an
  `app`-side JS surface, of which there is none today) make the name lie.

### 5. The compat shims (both packages, after the facade)

Per the hub proposal (card note, step 2), `scitex-app` and `scitex-ui`
become **thin compat shims that re-export `scitex_sdk.*` with a
`DeprecationWarning`** — no consumer breaks on day one, and every import of
the old name announces itself so the migration can be measured. Removal
happens only after every consumer (hub, figrecipe, writer, scholar, cards,
sac GUI) has migrated and released — "the shims are removed last" (card
step 4). The deprecation window and each shim's removal are CHANGELOG
entries in both repos.

### 6. What is explicitly NOT in this decision

- **No code change at the facade step.** `scitex_sdk.ui` is re-exports only;
  this package's tests, guards, and versioning run unchanged.
- **No merging of the two codebases.** The app/ui boundary stays; what
  changes is the packaging and the umbrella name.
- **No consumer rewrites by this repo's agents.** Each consumer repo's
  rewrite is that repo's PR (hub said it will do its own immediately after
  release; the rest follow per owner).
- **The mobile-layout card is independent**
  (`ui-mobile-layout-primitives-extract-from-apps-20260914`): its
  scitex-sdk side (pane helpers) lands in whichever repo owns the `ui`
  subpackage at that time; the consolidation does not gate it or vice versa
  (hub, 15:0xZ: "don't block either on the other").

## Consequences

- **For consumers:** a two-step mechanical migration (Python import
  rewrite; npm specifier unchanged per §4) behind a DeprecationWarning shim;
  no behavior change at any step (identity-verified re-exports).
- **For this repo:** the `scitex_ui` app label, static layout, npm `exports`
  keys, and Python `__all__` are the three contracts that must survive the
  move byte-for-byte; §2's measured surface is the baseline they are checked
  against.
- **For the fleet:** one umbrella pin (`scitex-sdk`) for "the SDK" and
  per-half pins (`scitex-app`, `scitex-ui`) where a consumer needs one half —
  both valid during the migration window.

## Status log

- 2026-09-14: operator decision + facade-first path (Telegram 5319/5322/5325/
  5333); card opened by scitex-hub; scitex-app built the thin facade (0.1.0,
  23/23 identity-verified, PyPI `scitex-sdk` registration pending operator)
  and reported names; this ADR records the `ui` half.
