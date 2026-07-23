#!/usr/bin/env python3
"""Guards the npm exports map against the two ways it misleads consumers.

figrecipe spelled six shell imports `@scitex/ui/src/scitex_ui/static/...`
and reasonably believed it sanctioned: the `"./src/*"` catch-all really
does re-export the whole internal layout as public API, and there was no
`"./ts/*"`, so the catch-all was the ONLY way to reach `ts/` modules.
The result is a consumer coupled to our directory layout — we cannot move
a file without breaking them, and neither side finds out until it breaks.

So this asserts two things:
1. every published area has a CLEAN export (a consumer never needs the
   catch-all), and
2. every exports target resolves to something that actually ships —
   an export pointing at a missing path is the npm-side twin of the CSS
   bundle importing a stylesheet that was never packaged.
"""

from __future__ import annotations

import json
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[2]
_PKG_JSON = _REPO / "package.json"
_STATIC = "src/scitex_ui/static/scitex_ui"

# Areas a consumer imports from, and the clean subpath each must expose.
_REQUIRED_AREAS = {
    "./css/*": f"./{_STATIC}/css/*",
    "./react/*": f"./{_STATIC}/react/*",
    "./ts/*": f"./{_STATIC}/ts/*",
}


@pytest.fixture(scope="module")
def exports() -> dict:
    return json.loads(_PKG_JSON.read_text())["exports"]


class TestEveryAreaHasACleanExport:
    @pytest.mark.parametrize("subpath,target", sorted(_REQUIRED_AREAS.items()))
    def test_area_is_reachable_without_the_catch_all(self, exports, subpath, target):
        # Arrange
        declared = exports.get(subpath)
        # Act
        ok = declared == target
        # Assert
        assert ok, (
            f"exports is missing {subpath!r} -> {target!r} (found {declared!r}); "
            f"consumers can only reach that area through the './src/*' catch-all, "
            f"which couples them to our internal directory layout"
        )


class TestExportTargetsResolve:
    def test_every_export_target_exists(self, exports):
        # Arrange
        targets = [v for v in exports.values() if isinstance(v, str)]
        # Act
        dangling = sorted(
            t for t in targets
            if "*" not in t and not (_REPO / t.lstrip("./")).exists()
        )
        # Assert
        assert not dangling, f"exports point at paths that do not ship: {dangling}"

    def test_wildcard_export_roots_exist(self, exports):
        # Arrange
        roots = [v.split("*")[0] for v in exports.values()
                 if isinstance(v, str) and "*" in v]
        # Act
        missing = sorted(r for r in roots if not (_REPO / r.lstrip("./")).is_dir())
        # Assert
        assert not missing, f"wildcard exports rooted at missing dirs: {missing}"

    def test_guard_is_not_vacuous(self, exports):
        # Arrange
        # Act
        count = len(exports)
        # Assert
        assert count >= len(_REQUIRED_AREAS), "exports map too small to be meaningful"
