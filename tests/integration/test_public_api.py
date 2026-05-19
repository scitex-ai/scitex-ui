#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/integration/test_public_api.py

"""Cross-module integration: package initialization, public API surface,
and the aggregate registration contract (every shipped component lands
in `_registry`)."""

import pytest

import scitex_ui


class TestPublicAPI:
    def test_version_hasattr_scitex_ui_version(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "__version__")

    def test_version_re_match_d_d_d_scitex_ui_version(self):
        # Arrange
        # Arrange
        # Act
        import re

        # Act
        # Assert
        # Assert
        assert re.match(r"^\d+\.\d+\.\d+", scitex_ui.__version__)

    def test_exports_hasattr_scitex_ui_get_component(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "get_component")

    def test_exports_hasattr_scitex_ui_list_components(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "list_components")

    def test_register_component_accessible(self):
        # Available but not in __all__ (advanced use)
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "register_component")

    def test_all_contains_expected(self):
        # Arrange
        # Act
        expected = {
            "__version__",
            "get_component",
            "list_components",
            "get_static_dir",
            "get_docs_path",
        }
        # Assert
        assert expected == set(scitex_ui.__all__)

    def test_get_static_dir_static_dir_is_dir(self):
        # Arrange
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
        # Act
        # Assert
        # Assert
        assert static_dir.is_dir()

    def test_get_static_dir_static_dir_ts_is_dir(self):
        # Arrange
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
        # Act
        # Assert
        # Assert
        assert (static_dir / "ts").is_dir()

    def test_get_static_dir_static_dir_css_is_dir(self):
        # Arrange
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
        # Act
        # Assert
        # Assert
        assert (static_dir / "css").is_dir()

    def test_css_primitives_dir_exists(self):
        # Arrange
        # Act
        css_dir = scitex_ui.get_static_dir() / "css" / "primitives"
        # Assert
        assert css_dir.is_dir()

    @pytest.mark.parametrize("name", ["spacing.css", "z-index.css", "typography.css"])
    def test_css_primitive_file_exists(self, name):
        # Arrange
        css_dir = scitex_ui.get_static_dir() / "css" / "primitives"
        # Act
        target = css_dir / name
        # Assert
        assert target.is_file(), f"Missing {name}"

    def test_list_components_includes_sidebar(self):
        # Arrange
        # Act
        components = scitex_ui.list_components()
        # Assert
        assert "package-docs-sidebar" in components


class TestAllComponentsRegistered:
    """Importing scitex_ui must trigger registration of every component.

    Lives in tests/integration/ because it spans every component module
    in src/scitex_ui/_components/ — there is no single src counterpart.
    """

    def test_all_components_registered(self):
        # Arrange
        names = scitex_ui.list_components()
        # Act
        expected = {
            "app-shell",
            "confirm-modal",
            "data-table",
            "dropdown",
            "file-browser",
            "file-tabs",
            "media-viewer",
            "monaco-editor",
            "package-docs-sidebar",
            "resizer",
            "status-bar",
            "theme-provider",
            "tooltip",
        }
        # Assert
        assert expected.issubset(set(names)), f"missing: {expected - set(names)}"


# EOF
