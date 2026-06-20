# Changelog

All notable changes to `scitex-ui` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
