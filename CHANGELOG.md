# Changelog

All notable changes to `scitex-ui` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.11.0] - 2026-07-22

- **`context-menu` grows `__shortcut`, `__label` and `:disabled` item styling** (component `0.1.0 → 0.2.0`). The harvest analysis found figrecipe's context-menu and base's are the same component under different names — except figrecipe's carried three affordances base lacked: a right-aligned keyboard-shortcut hint, an uppercase section label, and disabled-item styling. Until base had them, adopting the shared component meant losing affordances; now base is a strict superset and adoption is a pure deletion on the app side.

- **Test fixture: component versions may now evolve.** The shared `check_metadata` fixture asserted `version == "0.1.0"` literally — green only because no component had ever been bumped, and failing the moment the first one was (context-menu, this release). A guard that forbids all evolution is a freeze, not a check; it now asserts `X.Y.Z` shape instead of a pinned value.

- **Fix: standalone shell now links `css/shell/mobile.css` — standalone GUIs rendered completely blank on phones.** `standalone_shell.html` linked every desktop layout stylesheet (`workspace-three-col.css` and friends) but never `mobile.css`, whose `@media (max-width: 768px)` rules are the only thing that collapses the fixed-width side panes (`flex-shrink: 0`; 250px AI + 240px worktree) and gives `.ws-module-pane` full width. Without them the `overflow: hidden` flex row pushed the app content pane entirely off-screen, so **every** standalone-shell consumer showed a blank page on ≤768px viewports. Verified in production at scitex.ai `/apps/storage/` (2026-07-22): mobile and desktop received byte-identical HTML, every linked asset returned 200, and `/static/scitex_ui/css/shell/mobile.css` itself served 200 — shipped, collected, reachable, and referenced by nothing. Consumers that bundle the shell CSS themselves (the hub via `shell-css-imports.ts`) were unaffected; only the standalone template path was broken. Regression-guarded by rendering the shell and asserting the reference, plus a packaged-asset check mirroring the favicon guard.

## [0.10.0] - 2026-07-21

- **New component: `badge`** (`.stx-app-badge`) — a standalone tonal pill for short status/type labels. figrecipe, scitex-writer and scitex-cards had each rolled their own (`.badge` / `.badge` / `.activity-badge`) with convergent declarations: small inline pill, 600 weight, tonal background. Base already had eight badge selectors, but every one welded to a host component (`.stx-app-recent-pane__badge`, `.stx-app-sidebar-nav__badge`, …) — badges, but no badge an app could reuse. Neutral by default; `--info` / `--success` / `--warning` / `--error` map onto the existing `--status-{tone}-{bg,text,border}` variable triplets (light and dark both already ship them, so the component adds zero new color decisions); `--caps` covers uppercase type labels. CSS-only, registered, so `list_components()` now reports 25.

  Deliberately not covered: scitex-cards' five-step age gradation (`.age-pill--today/…/--rotten`) — a domain scale, not a tone; forcing it into the modifier set would bloat it for one consumer.

- **Packaging: the `all` extra is now closed over `dev` and `docs`** (PS-221 §3). scitex-dev's audit gate began enforcing that every public extra is a subset of `all`; `dev` and `docs` were missing, turning the gate red on every PR. Same shape as scitex-dev and scitex-cards: `all` self-references the public extras rather than renaming them internal, since both have in-repo consumers (the quality-audit workflow installs `.[dev]`, Read the Docs installs `.[docs]`) and both are published, making a rename a contract migration for no gain.

## [0.9.0] - 2026-07-19

- **Nine components were invisible to `list_components()`**. They shipped app-level CSS but were never registered, so the discovery API reported **15 of 24**. That API is how an app author answers "does scitex-ui already have a toggle-switch?" — the answer was silently NO, and the app rolled its own. The gap never surfaced as a bug; it surfaced as a duplicate implementation in someone else's repo months later.

  Now registered: `alert-banner`, `collapsible-panel`, `context-menu`, `miller-columns`, `recent-pane`, `selector-nav`, `settings-card`, `sidebar-layout`, `toggle-switch`. All are generic `stx-app-*` BEM components with usage documentation in their stylesheets. Two of them — `recent-pane` and `selector-nav` — carry the header comment "Ported from scitex-cloud", so for those the harvest had already happened and only the registration never did.

- **CSS-only and JS-only components are now both first-class.** The shared per-component test fixture required a component to declare *both* `ts_entry` and `css_file`, which is why `monaco-editor` (JS-only, `css_file = None`) had to be special-cased out of it with a hand-written test. Rather than add a second special case for the CSS-only nine, the fixture now checks each asset only when declared and requires at least one — the property that actually matters, since a component declaring no asset at all is a registry entry pointing at nothing.

- **Guard against silent recurrence** (`tests/develop/test_component_coverage.py`): every `css/app/*.css` must be claimed by a registered component; every declared `css_file` / `ts_entry` must actually ship; every component's `name` must match its registry key and carry a description. Scoped to `css/app/` deliberately — `css/shell/` also holds non-component stylesheets (theme, mobile, workspace\*), so "every file is a component" is false there and the rule would need a growing allowlist to stay green, which is how a guard rots into a rubber stamp. Verified non-vacuous by mutation: dropping the `ToggleSwitch` registration fails with `toggle-switch.css ships but no registered component declares it`.

  No behaviour change for existing consumers — the nine were already shipping their CSS; they were only undiscoverable. Minor bump because the discovery API's output changes.

## [0.8.1] - 2026-07-18

- **Docs correction (0.8.0 shipped a false justification)**: `shell_context`'s docstring claimed an emptiness check "would have collapsed [scitex-writer's] primary working surface on every page load." That is wrong, and scitex-writer caught it while wiring their declaration. Standalone writer already hides all four shell panes itself via `body:has(.writer-app) .workspace-three-col > .ws-ai-pane` and siblings (verified at `editor.css:1785-1797`, with `.writer-app` on both `editor.html:31` and `viewer.html:30`), so nothing of theirs would have been hidden that they were not already hiding.

  The design is unchanged and the reasoning is now stronger, because it no longer rests on any consumer's self-report. The load-bearing argument, which 0.8.0 missed: without a declared contract, apps reach into the shell's internals anyway. Writer's rule targets `.workspace-three-col > .ws-ai-pane` — private class names this package is free to rename, which would have broken them silently and invisibly to both sides. A declaration is an API the shell must not break; a stylesheet aimed at its DOM is not. That is verifiable from this repo and stays true whatever any consumer does.

  A second claim was dropped rather than shipped, having failed the same check. The corrected text initially cited writer's *cloud* deployment as the real false-positive case, on the strength of a comment in their CSS ("Cloud deployments override this — their own shell JS populates the panes"). Writer then established they do not implement that override, and a look at scitex-cloud and scitex-hub shows both render their **own** `workspace_ai_pane.html` / `workspace_worktree_pane.html` partials rather than this shell — hub has no reference to `standalone_shell.html` at all. So this contract does not operate in cloud mode, and citing it as evidence would have been a second unverified claim replacing the first. The general point — a client-populated pane is empty at render time — stands on its own without attribution.

- **Docs: adopting the shared favicon requires DELETING your workaround, not just upgrading**. 0.7.0 announced the shared mark as arriving "on upgrade." Measured at 0.7.1, it reached exactly **one of four** shell-extending GUIs: storage and figrecipe both set `favicon_href`, writer emits its own `<link rel="icon">` tags, and only cards supplied nothing and got the brand. The override is correct and unchanged — an app that wants its own mark must be able to keep it — but it means an upgrade alone changes nothing while still rendering *a* favicon, which is not the same as *the* mark, and nothing warns you. The module docstring now says so, along with two things consumers had to ask for individually: the shell emits exactly **one** `<link rel="icon">` (so setting `favicon_href` while keeping your existing tag moves the duplicate rather than removing it), and sized variants / `apple-touch-icon` belong in the app's own `extra_css` because the shell cannot express them.

  No behaviour change; documentation only.

## [0.8.0] - 2026-07-18

- **Declared pane contract (`shell_context(panes=...)`)**: an app states what each shell pane *is* — `{"ai": "unused", "files": "client-populated"}` — and a pane declared `unused` is hidden so the app's content reclaims the width. Fixes ~540px of dead space at 1440x900 on single-app standalone pages (scitex-hub's live audit of `/apps/storage/`: empty AI + files panes pushed content to x=539, 37% of the viewport).

  The obvious design — collapse a pane with no content — is wrong, and was rejected on evidence rather than taste. scitex-writer's file tree has **zero** server-rendered children (their templates never override `worktree_preseed`, empty by default) and fills from `data-working-dir` after mount. An emptiness check would have collapsed their primary working surface on *every* page load: a 100% false-positive rate, not an edge case. Emptiness at render time is uncorrelated with whether a pane matters — storage's panes are genuinely unused, writer's are genuinely used and merely late, and no inspection distinguishes those. So the app declares and the shell never guesses.

  Opt-in, chosen for the failure mode: forgetting to declare leaves the page exactly as it is today, whereas an opt-out default that guessed wrong would hide a working pane. When one direction's failure is invisible and the other's is destructive, take the invisible one.

  Unknown pane names or states raise `ValueError` — a typo that silently left a pane visible would look identical to never having declared it. Hidden via `display: none` rather than `width: 0`, because a zero-width pane keeps its resizer draggable and a user could drag open a pane the app declared it does not use.

  Design proposed by scitex-writer, agreed by scitex-storage.

## [0.7.1] - 2026-07-18

Consumer feedback on 0.7.0, same day. Two of these correct mistakes in 0.7.0 rather than adding scope.

- **Branding no longer requires the shell (new `_branding_head.html` partial)**: 0.7.0 put the favicon in `standalone_shell.html`'s `<head>`, which coupled *branding* to the *shell* when branding is the more general concern. Checking rather than assuming, only **4 of 6** consuming GUIs extend the shell (writer, figrecipe, cards, storage) — scholar and hub own their own layout, so 0.7.0 reached neither, and no version bump would have changed that. A GUI can now do `{% include "scitex_ui/_branding_head.html" %}` in its own `<head>` and get the shared mark with no layout migration. The shell includes the same partial instead of duplicating the markup. Raised by scitex-scholar, who verified their own wiring and disproved the "arrives on upgrade" claim.
- **Two render-blocking requests removed from every shell page**: 0.7.0 added a synchronous `<script src=theme-boot.js>` and a `<link>` for `typography-vars.css`. Both were small, but both blocked first paint, and scitex-cards flagged page latency as a live concern after an operator-visible slow-board incident. The theme boot is now an inline `_theme_boot.html` partial (it must run before paint, so an external file was the wrong shape), and the font tokens moved into `shell/theme.css`, which the shell already loads. `js/shell/theme-boot.js` is removed — the partial is the single source. A test asserts the duplicated font tokens stay identical to the primitives layer, so the copy fails CI if it drifts.
- **todo/cards accent uses scitex-cards' real values**: `#d99700` with `#fff7e6` as the tint (dark: `#e8ad2e`), replacing a warm brown invented here. Their board already renders that amber, so the operator sees continuity instead of a colour shift.
- **`logs/` is gitignored**: agent/session logs land in a top-level `logs/` in working checkouts, untracked *and* unignored, so a `git add -A` could sweep a session log into a commit. This does not by itself clear the PS-102 audit rule, which flags the directory's existence rather than its ignore status — that needs the dir relocated in each working checkout, which is local state this repo cannot fix from here.

## [0.7.0] - 2026-07-18

- **Shared GUI branding (new `scitex_ui.branding`)**: the four tool GUIs each hand-rolled their tab branding, so the fleet drifted — figrecipe and scholar showed the generic browser globe, and titles read "FigRecipe Editor" / "SciTeX Writer" / "default-project — SciTeX". 0.6.4 shipped the `favicon_href` *mechanism* but no asset and no convention, so nothing actually changed in a tab. This adds the missing half: the shared brand mark ships at `scitex_ui/img/scitex-favicon.svg` and the shell **falls back to it whenever a view supplies no `favicon_href`** — a tool is branded by doing nothing, rather than by opting in. `branding.shell_title()` normalises a tool name into the `"SciTeX <Tool>"` convention (idempotent), and `branding.shell_context()` builds the `app_label` / `app_accent` / `shell_theme_default` context in one call.
- **Fix (every standalone GUI rendered body text in Times New Roman)**: the shell loads only `shell/*.css`, and no file in that set sets `body { font-family }` — `primitives/typography.css` carries it but is the app-level stylesheet the shell deliberately does not load. The UA default therefore won on every SciTeX GUI. The shell now loads `primitives/typography-vars.css` (tokens only, no rule collisions) and `shell/app-shell.css` sets the base body typography from those tokens.
- **Fix (a stored light theme preference was silently overridden)**: `standalone_shell.html` hardcoded `data-theme="dark"` on `<html>`, so a user who had chosen light got dark anyway — proven live on the storage GUI. Theme resolution moved to `js/shell/theme-boot.js`, loaded synchronously in `<head>` so it applies before first paint (no flash). It reads the canonical `stx-theme` key, falls back to the legacy `scitex-theme-preference` key for hub/cloud-served pages until those converge, and defaults to dark — overridable per page via `shell_theme_default`.
- **Fix (accent line dead for storage/todo/comms)**: `--app-accent-*` tokens and the `[data-app-accent="..."]` mapping rows had drifted apart. Added tokens *and* rows for `storage`, `todo`/`cards` and `comms` in both light and dark, plus the missing row for `notebook` (its token had existed since 0.x with nothing to select it). Two tests now assert the two sets are equal in both directions, so this class of drift fails CI instead of shipping as an invisible no-op.
- **Shell**: `#main-content` renders `data-app-accent` from the new `app_accent` context var, so `shell_context(accent=...)` reaches the CSS.
- **Packaging (this class has now bitten three releases)**: the new favicon was silently absent from the first 0.7.0 wheel — the shared gitignore's blanket `**/*.svg` rule (intended for generated figures) matched it, so git never tracked it and hatchling never packaged it. Identical in shape to the `**/*old*` rule that broke 0.6.1/0.6.2. Fixed by force-tracking `src/scitex_ui/static/scitex_ui/img/**` and adding `*.svg`/`*.js` to `[tool.hatch.build] artifacts`. The durable part is `tests/scitex_ui/test_packaging.py`, which asserts **nothing under `static/` is gitignored** — the invariant behind all three incidents, checkable without building.

Reported by scitex-hub (PR #388 live audit of `/apps/storage/`) and scitex-dev (operator's browser-tab screenshot, 2026-07-12).

## [0.6.4] - 2026-07-12

- **Shell**: `standalone_shell.html` gains an optional `favicon_href` context var, rendered as `<link rel="icon">` right after `<title>`. Completes the tab-branding contract alongside `app_label` — consuming GUIs (scholar, storage, writer, todo, figrecipe) set both together through one shared key instead of five bespoke `extra_css` workarounds (PR #65).

## [0.6.3] - 2026-07-11

- **Fix (0.6.2 was still broken — sdist-stage drop)**: 0.6.2 moved `artifacts` under `[tool.hatch.build.targets.wheel]`, which fixed a *direct* `pip wheel` build but NOT the release. The release CI runs `python -m build`, which builds the **sdist first and then the wheel from that sdist** — so `_BinaryPlaceholder.ts` was already dropped at the sdist stage (which had no `artifacts` config) before the wheel step could recover it, and the published 0.6.2 wheel shipped without it just like 0.6.1. Moved `artifacts` to the shared `[tool.hatch.build]` level so it force-includes the frontend sources in **every** target (sdist + wheel). Verified via `python -m build`: both the 0.6.3 sdist and the wheel-from-sdist now carry `_BinaryPlaceholder.ts` (wheel: 366 frontend files vs 365). Supersedes the broken 0.6.2.

## [0.6.2] - 2026-07-11

- **Fix (wheel silently dropped a tracked frontend source)**: the built wheel omitted `src/scitex_ui/static/scitex_ui/ts/app/media-viewer/_BinaryPlaceholder.ts`. hatchling honors `.gitignore`, and the shared gitignore template's `**/*old*` rule (intended for `.old/` trash dirs) is a *substring* match that also hits any filename containing "old" — here `_BinaryPlaceh`**`old`**`er.ts`. git tracks the file, but every published wheel (0.6.1 and earlier) shipped without it, while editable/source installs still saw it. That skew is exactly what made scitex-hub's *baked* wheel partial and broke its boot-time Vite build (missing `_BinaryPlaceholder`), forcing the hub to editable-reinstall `develop` at boot as a workaround — the origin of the boot permission cascade. Fixed by pinning the frontend source extensions under `static/` into `[tool.hatch.build.targets.wheel] artifacts`, so they ship regardless of which filename a future generic ignore rule trips. Verified: the 0.6.2 wheel carries 366 frontend files (was 365) including the recovered `_BinaryPlaceholder.ts`.

## [0.6.1] - 2026-07-10

- **Fix (ASGI deadlock)**: `ElementInspectorMiddleware` is now a Django hybrid (async-capable) middleware. Previously it was sync-only, so under ASGI/daphne Django adapted it with `AsyncToSync` in a thread-sensitive executor. When daphne cancelled a slow request (`application_close_timeout`), the event loop — inside `executor.shutdown()` → `join()` — waited on the worker thread while that thread was blocked in `AsyncToSync` waiting on the loop: a hard deadlock that permanently wedged the daphne process so every later request, even `/healthz/`, hung forever. Declaring `async_capable`/`sync_capable` and awaiting the inner chain natively removes both the deadlock and the per-request sync↔async mode switch (which was also adding real latency). The deadlock was diagnosed with py-spy on a source/dev-install of scitex-ui on the scitex-hub staging box (which does carry `middleware.py`).
- **Fix (inspector silently off under ASGI)**: the staff-user gate reads `request.user`, a DB-backed lazy object whose evaluation raises `SynchronousOnlyOperation` on the event loop; that was being swallowed by the "never break a page" guard, so the inspector silently failed for staff users under ASGI. The async path now resolves the gate off the loop via `sync_to_async`, keeping `element_inspector_enabled` the single source of truth for the gating precedence.
- **Release note (0.6.0 shipped no middleware)**: `src/scitex_ui/middleware.py` landed on `develop` via PR #55 *after* 0.6.0 was cut, so the published 0.6.0 wheel contains only `context_processors.py` — every PyPI consumer (including scitex-hub production and staging) got the inspector *without* the universal middleware, so Alt+I only worked on pages that manually `{% include %}` the partial (the operator's "works in some GUI apps but not others"). 0.6.1 is therefore the first release that actually delivers the universal inspector — and it ships the deadlock-free async-capable middleware, so the release is mandatory, not cosmetic.

## [0.6.0] - 2026-06-20

- **Components**: Combobox (fuzzy-typeahead select primitive) with a pre-built pure-JS bundle for Django-template consumers; dismissible alert/error banner (React); element-inspector wired shell-wide (DEBUG/staff-gated).
- **Files tree**: breadcrumb path bar that re-roots from filesystem root.
- **Linter**: UI-101..105 component-usage rules + scitex-ui lint walker + linter plugin.
- **Deps**: `click` promoted to a hard core dependency (PS-213) — the `scitex_ui._cli:main` console-script imports it unguarded.
- **CI**: back-merged main; standardized on the canonical fleet workflow set (import-smoke, pytest-matrix with per-job codecov HOME isolation, rtd-sphinx, newb-docs, tag-driven pypi/release, auto-merge-to-develop, single-package quality-audit) and dropped the legacy `ci.yml`/`release.yml`.

## [0.4.9] - 2026-05-26

- **MCP-Python API parity**: Added 4 new MCP tools (`ui_get_component`, `ui_list_components`, `ui_get_static_dir`, `ui_get_docs_path`) to match Python API surface (PR #22).
- **Audit gate**: Removed `skip_rules=("§6",)` — full `audit-all` now runs with zero skips (PR #22).
- **Test quality**: Fixed TQ002 (AAA markers), TQ003 (descriptive names), TQ007 (single-assert) across all test files (PR #22).

## [0.4.8]

- Initial CHANGELOG entry — see git log for prior history.
