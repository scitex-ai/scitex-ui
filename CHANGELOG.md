# Changelog

All notable changes to `scitex-ui` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
