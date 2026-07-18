#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_ui._components._selector_nav."""

from scitex_ui._components._selector_nav import SelectorNav


class TestSelectorNav:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(SelectorNav) is SelectorNav

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert SelectorNav.ts_entry is None


# EOF
