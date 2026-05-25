#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_ui._components._monaco_editor.

MonacoEditor is special-cased: it has no CSS file (Monaco styles are
imported via JS), so we skip the standard `check_metadata` helper and
verify the remaining contract by hand.
"""

from pathlib import Path

import scitex_ui
from scitex_ui._components._monaco_editor import MonacoEditor
from scitex_ui._registry import get_component

PKG_DIR = Path(scitex_ui.__file__).parent


class TestMonacoEditor:
    def test_name_is_monaco_editor(self):
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.name == "monaco-editor"

    def test_version_is_0_1_0(self):
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.version == "0.1.0"

    def test_description_is_set(self):
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.description

    def test_ts_entry_is_set(self):
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.ts_entry

    def test_css_file_is_none(self):
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.css_file is None

    def test_registered_get_component_returns_monacoeditor(self):
        # Arrange
        # Act
        # Assert
        assert get_component("monaco-editor") is MonacoEditor

    def test_ts_entry_exists(self):
        # Arrange
        # Act
        ts_path = PKG_DIR / "static" / (MonacoEditor.ts_entry + ".ts")
        # Assert
        assert ts_path.exists(), f"TS entry not found: {ts_path}"


# EOF
