#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Cross-module integration: package initialization, public API surface,
and the aggregate registration contract (every shipped component lands
in `_registry`)."""

import pytest

import scitex_ui


class TestPublicAPI:
    def test_version_attribute_exists(self):
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "__version__")

    def test_version_semver_format(self):
        # Arrange
        import re

        # Act
        # Assert
        assert re.match(r"^\d+\.\d+\.\d+", scitex_ui.__version__)

    def test_exports_get_component(self):
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "get_component")

    def test_exports_list_components(self):
        # Arrange
        # Act
        # Assert
        assert hasattr(scitex_ui, "list_components")

    def test_register_component_accessible(self):
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

    def test_get_static_dir_is_dir(self):
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
        # Assert
        assert static_dir.is_dir()

    def test_get_static_dir_has_ts_subdir(self):
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
        # Assert
        assert (static_dir / "ts").is_dir()

    def test_get_static_dir_has_css_subdir(self):
        # Arrange
        # Act
        static_dir = scitex_ui.get_static_dir()
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
