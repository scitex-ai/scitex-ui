#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_components/test__file_tabs.py

"""Tests for scitex_ui._components._file_tabs."""

from scitex_ui._components._file_tabs import FileTabs


class TestFileTabs:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(FileTabs) is FileTabs


# EOF
