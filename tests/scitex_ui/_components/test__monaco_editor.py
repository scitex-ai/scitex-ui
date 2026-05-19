#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_components/test__monaco_editor.py

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
    def test_metadata_fields_monacoeditor_name_equals_monaco_editor(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.name == "monaco-editor"

    def test_metadata_fields_monacoeditor_version_equals_n_0_1_0(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.version == "0.1.0"

    def test_metadata_fields_monacoeditor_description(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.description

    def test_metadata_fields_monacoeditor_ts_entry(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.ts_entry

    def test_metadata_fields_monacoeditor_css_file_is_none(self):
        # Arrange
        # Act
        # Assert
        # Arrange
        # Act
        # Assert
        assert MonacoEditor.css_file is None


    def test_registered_get_component_monaco_editor_is_monacoeditor(self):
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
