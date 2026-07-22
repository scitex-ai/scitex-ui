#!/usr/bin/env python3
"""Guards that the component registry stays consistent with what ships.

`list_components()` is the discovery API: an app author asking "does
scitex-ui already have a toggle-switch?" gets their answer here. When a
component ships CSS but is never registered, the answer is silently NO and
the app rolls its own — so the gap does not surface as a bug, it surfaces
as a duplicate implementation in someone else's repo months later. Nine
components were in exactly that state before these tests existed.

Scoped to ``css/app/`` deliberately. ``css/shell/`` also holds non-component
stylesheets (theme.css, mobile.css, workspace*.css), so "every file is a
component" is false there and a blanket rule would have to carry a growing
allowlist to stay green — which is how a guard rots into a rubber stamp.
"""

from __future__ import annotations

import pathlib

import pytest

import scitex_ui  # noqa: F401  (import registers every component)
from scitex_ui._registry import _COMPONENTS

_STATIC = pathlib.Path(scitex_ui.__file__).parent / "static"
_APP_CSS_DIR = _STATIC / "scitex_ui" / "css" / "app"

_APP_CSS_FILES = sorted(p.name for p in _APP_CSS_DIR.glob("*.css"))
_DECLARED_CSS = {
    getattr(meta, "css_file", None) for meta in _COMPONENTS.values()
}
_CLAIMED_APP_CSS = {
    pathlib.PurePosixPath(css).name
    for css in _DECLARED_CSS
    if css and "/css/app/" in f"/{css}"
}


class TestAppCssIsDiscoverable:
    @pytest.mark.parametrize("css_name", _APP_CSS_FILES)
    def test_every_app_stylesheet_is_claimed_by_a_component(self, css_name):
        # Arrange
        claimed = _CLAIMED_APP_CSS
        # Act
        is_claimed = css_name in claimed
        # Assert
        assert is_claimed, (
            f"{css_name} ships but no registered component declares it; "
            f"list_components() will not reveal it to consumers"
        )

    def test_app_css_dir_is_not_empty(self):
        # Arrange
        # Act
        count = len(_APP_CSS_FILES)
        # Assert
        assert count > 0, "guard would be vacuous with no stylesheets to check"


class TestDeclaredAssetsResolve:
    @pytest.mark.parametrize(
        "name",
        sorted(n for n, m in _COMPONENTS.items() if getattr(m, "css_file", None)),
    )
    def test_declared_css_file_exists(self, name):
        # Arrange
        declared = _COMPONENTS[name].css_file
        # Act
        exists = (_STATIC / declared).is_file()
        # Assert
        assert exists, f"{name} declares css_file={declared!r}, which does not ship"

    @pytest.mark.parametrize(
        "name",
        sorted(n for n, m in _COMPONENTS.items() if getattr(m, "ts_entry", None)),
    )
    def test_declared_ts_entry_exists(self, name):
        # Arrange
        declared = _COMPONENTS[name].ts_entry
        # Act
        base = _STATIC / declared
        exists = base.with_suffix(".ts").is_file() or base.with_suffix(".tsx").is_file()
        # Assert
        assert exists, f"{name} declares ts_entry={declared!r}, which does not ship"


class TestComponentMetadataShape:
    @pytest.mark.parametrize("name", sorted(_COMPONENTS))
    def test_registered_name_matches_its_key(self, name):
        # Arrange
        meta = _COMPONENTS[name]
        # Act
        declared_name = getattr(meta, "name", None)
        # Assert
        assert declared_name == name

    @pytest.mark.parametrize("name", sorted(_COMPONENTS))
    def test_every_component_has_a_description(self, name):
        # Arrange
        meta = _COMPONENTS[name]
        # Act
        description = getattr(meta, "description", "")
        # Assert
        assert description, f"{name} has no description to show in discovery output"
