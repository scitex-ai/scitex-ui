#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_ui._components._context_menu."""

from scitex_ui._components._context_menu import ContextMenu


class TestContextMenu:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ContextMenu) is ContextMenu

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert ContextMenu.ts_entry is None


# EOF
