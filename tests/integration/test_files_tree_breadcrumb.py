#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural guards for the WorkspaceFilesTree breadcrumb.

No JS test runner here, so behaviour isn't unit-tested; these assert the
breadcrumb ships and stays wired (handler present, CSS bundled, adapter
interface advertises the rootPath argument) so it can't silently regress.
"""

import scitex_ui


class TestFilesTreeBreadcrumb:
    def test_breadcrumb_handler_present(self):
        # Arrange
        wft = scitex_ui.get_static_dir() / "ts" / "shell" / "workspace-files-tree"
        # Act
        handler = wft / "_handlers" / "BreadcrumbHandler.ts"
        # Assert
        assert handler.is_file()

    def test_breadcrumb_css_bundled(self):
        # Arrange
        static = scitex_ui.get_static_dir()
        css = static / "css" / "shell" / "workspace-files-tree" / "breadcrumb.css"
        all_css = (static / "css" / "all.css").read_text(encoding="utf-8")
        # Act
        bundled = css.is_file() and "workspace-files-tree/breadcrumb.css" in all_css
        # Assert
        assert bundled

    def test_adapter_interface_advertises_rootpath(self):
        # Arrange -- the FileTreeAdapter contract must document the rootPath arg
        # so consumers know to honour it for breadcrumb re-rooting.
        types_ts = (
            scitex_ui.get_static_dir()
            / "ts"
            / "shell"
            / "workspace-files-tree"
            / "types.ts"
        ).read_text(encoding="utf-8")
        # Act
        advertises = "fetchTree(rootPath" in types_ts and "showBreadcrumb" in types_ts
        # Assert
        assert advertises
