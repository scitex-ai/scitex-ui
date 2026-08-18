#!/usr/bin/env python3
"""Guards that every shell TypeScript module a consumer can reach is reachable.

`ts/shell/mobile-swipe.ts` and `ts/shell/sidebar-drawer-gesture.ts` shipped for
months while being reachable from nothing: absent from the `ts/shell/index.ts`
barrel, imported by no module here, referenced by no template, and with no
compiled counterpart under `js/`. They had been written, debugged and given
`export function init()` — but a caller was never added, so no browser ever ran
them. See ADR 0002.

("imported by no consumer" used to appear in that list. It was removed on
2026-08-05 because this test never checked it and cannot — see the scope
warning below. Claiming it here is what made the allow-list read as a
deletion license.)

That is the same defect class as the unregistered components 0.9.0 fixed, the
unimported stylesheets `test_css_bundle_index.py` guards, and the orphaned
element inspector of ADR 0001: the artifact ships, the wiring that gives it
force does not, and nothing fails on either side.

So this recomputes the module set from the filesystem and requires each one to
be reachable by one of the two mechanisms this package actually uses, which
catches the NEXT orphan too, not just the two that were found by hand.

A module is REACHABLE when either:
  - the barrel `ts/shell/index.ts` names it in an `export ... from "./name"`, or
  - a committed IIFE bundle `js/shell/<name>.js` exists AND a template loads it.

Known orphans are listed in `_ALLOWED_ORPHANS` with the reason. They are named
rather than hidden: `test_allowlist_has_no_stale_entries` fails once one is
fixed or removed, so the allowlist cannot quietly outlive the problem.

SCOPE — WHAT "ORPHAN" MEANS HERE, AND WHAT IT DOES NOT
======================================================
Orphan means UNREACHABLE WITHIN THIS REPOSITORY. Both mechanisms above —
the barrel and the template-loaded bundle — are local. This test does not
look at any consumer, and it cannot: a component library's consumers live in
other repositories by definition, so the one search that would establish
"nobody imports this" is the one search this file never runs.

**DO NOT TREAT AN ENTRY IN `_ALLOWED_ORPHANS` AS A LICENCE TO DELETE.**

The warning exists because of a 2026-08-05 near-miss whose value is in how it
resolved, not in the damage — there was none. A consumer (figrecipe) reported
a broken frontend build and attributed it to this repo removing modules. Two
of the modules named here HAD been removed by 15f37d2 (#119), both allow-listed
in this file, so the story fit and was briefly accepted on both sides.

It was wrong. Measured afterwards: figrecipe imports NEITHER removed module —
zero occurrences of `standalone-terminal` or `workspace-shell` in their repo,
against a positive control that returns hits. Their build broke for an
unrelated reason of their own, and their initial report rested on a probe that
listed files while hiding directories.

The lesson survives the retraction, which is why this warning stays: for the
half-hour that story was believed, NOTHING IN THIS FILE COULD HAVE SETTLED IT
EITHER WAY. The guard was green throughout — correctly, since green was all it
ever claimed. A removal here can be safe or catastrophic for a consumer and
this test returns the same answer to both.

Before removing an exported module, run the check this file cannot:
  - grep the fleet for the export name, or
  - ask the known consumers (figrecipe, scitex-writer, scitex-cards,
    scitex-cloud, scitex-storage)
A published-package dependency would turn such a removal into a version bump;
consumers that symlink into this working checkout get it with no signal at all.

This is the same defect class the module list above describes, pointed
outward: there, an artifact shipped that reached nobody; here, a deletion
COULD reach somebody nobody looked for. Both are "I checked the layer I could
see", and they are the same query run in opposite directions — the reach audit
and the deletion audit differ only in which way you point it.
"""

from __future__ import annotations

import re

import pytest

from tests._checkout import static_dir, templates_dir

_STATIC = static_dir()
_SHELL_TS = _STATIC / "ts" / "shell"
_JS_SHELL = _STATIC / "js" / "shell"
_TEMPLATES = templates_dir()

# Structural, not orphans: the barrel itself and its type-only companion.
_NOT_MODULES = {"index.ts", "types.ts"}

# Orphans that need their own decision, each with the reason it is deferred.
# See ADR 0002 "Consequences".
#: Empty, and that is the point: both entries were REMOVED in 0.14.2 rather
#: than fixed, because measuring them answered the question the card called a
#: design decision.
#:
#: workspace-shell.ts — scitex-cloud already owns
#:   static/workspace_app/ts/workspace-shell.ts, serves /workspace/content/
#:   from workspace_app/views.py, and ships module-tab-switcher.ts for the
#:   .module-tab-btn this needed. Its copy is also FURTHER EVOLVED (198 lines
#:   vs 139): it reads module names from a DOM attribute set by a registry
#:   context processor where ours hardcoded KNOWN_MODULES. So ours was a stale
#:   fork of a consumer-owned file, not a base component awaiting a home.
#:
#: standalone-terminal.ts — superseded by terminal/, and its successor says so:
#:   terminal/_TerminalFactory.ts:4 reads "Merges standalone-terminal.ts (local
#:   vendor, port+1 WebSocket) with …", and terminal/index.ts already exports
#:   the same loadXtermModules / loadXtermCSS helpers. The merge had happened;
#:   this was the leftover original.
#:
#: Deleted rather than archived to .old/: these files ship inside the wheel, so
#: an in-tree archive would be published to every consumer. Git history is the
#: archive here.
_ALLOWED_ORPHANS: dict[str, str] = {}


def _shell_modules() -> set[str]:
    """Top-level shell modules a consumer could import, as file names."""
    return {
        p.name
        for p in _SHELL_TS.glob("*.ts")
        if not p.name.startswith("_") and p.name not in _NOT_MODULES
    }


def _barrel_exports() -> set[str]:
    """Module stems the barrel re-exports, from `export ... from "./stem"`."""
    text = (_SHELL_TS / "index.ts").read_text()
    return set(re.findall(r'from\s+"\./([A-Za-z0-9._-]+)"', text))


def _template_text() -> str:
    return "\n".join(p.read_text() for p in _TEMPLATES.rglob("*.html"))


def _is_reachable(module: str) -> bool:
    stem = module[: -len(".ts")]
    if stem in _barrel_exports():
        return True
    bundle = _JS_SHELL / f"{stem}.js"
    return bundle.is_file() and f"js/shell/{stem}.js" in _template_text()


class TestShellModulesAreReachable:
    @pytest.mark.parametrize("module", sorted(_shell_modules()))
    def test_module_is_reachable_or_a_known_orphan(self, module):
        # Arrange
        reason = _ALLOWED_ORPHANS.get(module)
        # Act
        reachable = _is_reachable(module)
        # Assert
        assert reachable or reason, (
            f"ts/shell/{module} ships in the package but reaches no browser and "
            f"no consumer: it is not re-exported by ts/shell/index.ts and has no "
            f"js/shell/ bundle loaded by a template. Export it from the barrel, "
            f"or bundle it (see ADR 0002), or delete it."
        )

    @pytest.mark.parametrize("module", sorted(_ALLOWED_ORPHANS))
    def test_allowlist_has_no_stale_entries(self, module):
        # Arrange
        exists = (_SHELL_TS / module).is_file()
        # Act
        still_orphaned = exists and not _is_reachable(module)
        # Assert
        assert still_orphaned, (
            f"ts/shell/{module} is allow-listed as a known orphan but is now "
            f"{'reachable' if exists else 'gone'}; drop it from _ALLOWED_ORPHANS"
        )

    def test_guard_covers_something(self):
        # Arrange
        # Act
        modules = _shell_modules()
        # Assert
        assert modules, "no shell modules discovered; the guard would be vacuous"


class TestMobileSwipeReachesTheShell:
    def test_bundle_is_committed(self):
        # Arrange
        bundle = _JS_SHELL / "mobile-swipe.js"
        # Act
        exists = bundle.is_file()
        # Assert
        assert exists, (
            "js/shell/mobile-swipe.js is missing; rebuild it per ADR 0002 or the "
            "shell template loads a 404"
        )

    def test_standalone_shell_loads_the_bundle(self):
        # Arrange
        shell = _TEMPLATES / "scitex_ui" / "standalone_shell.html"
        # Act
        text = shell.read_text()
        # Assert
        assert "js/shell/mobile-swipe.js" in text, (
            "standalone_shell.html no longer loads mobile-swipe.js; the gestures "
            "reach no page again"
        )

    def test_bundle_carries_the_gesture_code(self):
        # Arrange
        bundle = (_JS_SHELL / "mobile-swipe.js").read_text()
        # Act
        has_guard = "workspace-three-col" in bundle
        # Assert
        assert has_guard, (
            "js/shell/mobile-swipe.js does not reference #workspace-three-col; "
            "the committed bundle is stale or was built from the wrong entry"
        )
