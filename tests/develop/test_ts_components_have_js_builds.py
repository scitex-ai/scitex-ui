#!/usr/bin/env python3
"""Guards that a component shipping TypeScript also ships something a browser runs.

INSTALLED IS NOT CONSUMABLE. scitex-cards upgraded to 0.12.0, confirmed
`ts/app/context-menu/` was present with all three files, and still could not
use it: the package ships TypeScript, their chat page has no bundler, and a
browser will not execute a `.ts` file. The module was installed and unusable.

That is the fourth rung of a chain every one of whose steps looked like the
finish line from the step above:

    merged     is not published        (their gate caught that too)
    published  is not installed        (their host sat on 0.11.1)
    installed  is not consumable       (this)
    consumable is not correctly styled (the token-layer fix)

The mechanism to fix it already existed and was already documented — ADR 0001
established the esbuild-bundle-under-`js/` path, ADR 0002 reused it for
mobile-swipe on the same day these four primitives were written, and
`js/app/combobox.js` had been sitting there as a worked example the whole time.
Knowing the mechanism did not cause it to be applied. So this is a check rather
than a note.

SCOPE, deliberately narrow: only components under `ts/app/`, which are the
library-style ones an adopter imports. Shell modules are wired by the shell
itself and are a different consumption story.
"""

from __future__ import annotations

import pathlib

import pytest

import scitex_ui

_STATIC = pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui"
_JS_APP = _STATIC / "js" / "app"

# Components whose ts_entry lives under ts/app/ but which are consumed only
# through a bundler today, with the reason. Named rather than hidden: a
# companion test fails once one gains a build, so the list cannot outlive it.
_BUNDLER_ONLY = {
    "data-table": "large; React-side consumers bundle it and no plain-page adopter has asked",
    "file-browser": "same — no plain-page adopter yet",
    "monaco-editor": "wraps monaco-editor, a peer dependency the adopter loads anyway",
    "pdf-viewer": "wraps pdfjs-dist, a peer dependency",
    "package-docs-sidebar": "no plain-page adopter yet",
    # MEASURED, not assumed: bundling this produced a 7.0 MB file because it
    # inlines mermaid and pdfjs-dist, both declared peer/deps the adopter loads
    # separately. Every other bundle here is 1-12 KB. Shipping 7 MB of vendored
    # copy into the wheel would be a worse defect than the one this PR fixes.
    "media-viewer": "bundling inlines mermaid + pdfjs-dist -> 7.0 MB; peers load separately",
}


# No bundle may exceed this. media-viewer built to 7.0 MB before it was
# exempted; without a ceiling the next peer-wrapping component repeats it
# silently, because a too-large bundle still passes an exists() check.
_MAX_BUNDLE_KB = 64


def _app_components():
    """Registered components whose ts_entry is under ts/app/."""
    out = []
    for name in scitex_ui.list_components():
        cls = scitex_ui.get_component(name)
        entry = getattr(cls, "ts_entry", None)
        if entry and "/ts/app/" in f"/{entry}":
            out.append((name, entry))
    return sorted(out)


def _module_dir(ts_entry: str) -> str:
    # "scitex_ui/ts/app/context-menu/index" -> "context-menu"
    return ts_entry.split("/ts/app/", 1)[1].rsplit("/", 1)[0]


def test_discovery_is_not_vacuous():
    # Arrange
    # Act
    found = _app_components()
    # Assert
    assert len(found) >= 5, (
        f"only {len(found)} app components with a ts_entry discovered; the "
        f"registry lookup drifted and the guard would prove nothing"
    )


@pytest.mark.parametrize("name,entry", _app_components(), ids=lambda v: str(v))
def test_app_component_has_a_browser_loadable_build(name, entry):
    # Arrange
    mod = _module_dir(entry)
    # Act
    built = (_JS_APP / f"{mod}.js").is_file()
    # Assert
    assert built or mod in _BUNDLER_ONLY, (
        f"component '{name}' ships ts/app/{mod}/ but no js/app/{mod}.js. An "
        f"adopter without a bundler cannot run it — a browser does not execute "
        f".ts. Build it (esbuild --format=esm, see the banner in any existing "
        f"bundle) or add it to _BUNDLER_ONLY with the reason."
    )


@pytest.mark.parametrize(
    "bundle", sorted(_JS_APP.glob("*.js")), ids=lambda p: p.name
)
def test_no_bundle_inlines_a_peer_dependency(bundle):
    """A bundle that exists but is 7 MB is not a fix, it is a new defect.

    `media-viewer` built to 7.0 MB because esbuild inlined mermaid and
    pdfjs-dist — both declared peers the adopter already loads. An exists()
    check passes on that file happily, which is why this size ceiling is a
    separate assertion rather than a comment.
    """
    # Arrange
    size_kb = bundle.stat().st_size / 1024
    # Act
    oversized = size_kb > _MAX_BUNDLE_KB
    # Assert
    assert not oversized, (
        f"{bundle.name} is {size_kb:.0f} KB, over the {_MAX_BUNDLE_KB} KB "
        f"ceiling — it has almost certainly inlined a peer dependency. Mark the "
        f"peer external, or add the component to _BUNDLER_ONLY with the reason."
    )


@pytest.mark.parametrize("mod", sorted(_BUNDLER_ONLY))
def test_bundler_only_list_has_no_stale_entries(mod):
    # Arrange
    built = (_JS_APP / f"{mod}.js").is_file()
    ts_dir = (_STATIC / "ts" / "app" / mod).is_dir()
    # Act
    still_exempt = ts_dir and not built
    # Assert
    assert still_exempt, (
        f"'{mod}' is listed as bundler-only but now {'has a build' if built else 'is gone'}; "
        f"drop it from _BUNDLER_ONLY so the list cannot outlive the exemption"
    )


# EOF
