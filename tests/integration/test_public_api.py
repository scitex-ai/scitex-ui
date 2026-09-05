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


class TestCssImportsResolve:
    def test_all_css_imports_resolve(self):
        # Arrange -- collect every @import target across the shipped CSS and
        # check it points at a real file. A dangling @import (e.g. a primitive
        # referencing a never-migrated utilities/effects.css) passes scitex-ui's
        # own build but breaks any downstream bundler (vite/postcss) that
        # resolves @import, blocking consumer apps like the figrecipe editor.
        import re

        css_root = scitex_ui.get_static_dir() / "css"
        pattern = re.compile(r"""@import\s+(?:url\()?\s*["']([^"')]+)["']""")
        # Comments are stripped FIRST, because an @import inside /* */ is not an
        # import — CSS does not resolve it and no bundler tries. Without this,
        # the guard reported utils/effects.css as dangling for QUOTING hub's
        # spelling of the path (`../utilities/effects.css`) in the comment that
        # explains why this package does not use that spelling. The file
        # documenting why a path is wrong looked identical to a file still
        # using it — the same prose-vs-construct confusion recorded in
        # test_detectors_carry_controls, which has now bitten this repo three
        # times and scitex-app once.
        comments = re.compile(r"/\*.*?\*/", re.S)
        broken = []
        # Act
        for css_file in css_root.rglob("*.css"):
            text = comments.sub("", css_file.read_text(encoding="utf-8"))
            for raw in pattern.findall(text):
                target = raw.split("?")[0].split("#")[0]
                if target.startswith(("http://", "https://", "data:", "//")):
                    continue
                if not (css_file.parent / target).resolve().is_file():
                    broken.append(f"{css_file.relative_to(css_root)} -> {target}")
        # Assert
        assert not broken, f"dangling CSS @imports: {broken}"

    def test_the_import_scan_actually_finds_imports(self):
        """ANTI-VACUITY, added when the test above learned to strip comments.

        "No dangling imports" is what a correct tree reports AND what a scan
        that read nothing reports. Comment-stripping made that failure newly
        reachable: an over-greedy stripper would swallow whole stylesheets, the
        check above would find zero imports, and the suite would call the
        bundle healthy at the exact moment it stopped being inspected.
        """
        # Arrange
        import re

        css_root = scitex_ui.get_static_dir() / "css"
        pattern = re.compile(r"""@import\s+(?:url\()?\s*["']([^"')]+)["']""")
        comments = re.compile(r"/\*.*?\*/", re.S)
        # Act
        found = [
            raw
            for css_file in css_root.rglob("*.css")
            for raw in pattern.findall(
                comments.sub("", css_file.read_text(encoding="utf-8"))
            )
        ]
        # Assert
        assert len(found) > 50, (
            f"only {len(found)} @import targets found under {css_root}; this "
            "package's bundles alone carry far more, so the scan is not "
            "reading the tree and the dangling-import check above proves "
            "nothing"
        )


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
