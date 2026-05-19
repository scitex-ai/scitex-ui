#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_components/test__package_docs_sidebar.py

"""Tests for scitex_ui._components._package_docs_sidebar."""

from scitex_ui._components._package_docs_sidebar import PackageDocsSidebar


class TestPackageDocsSidebar:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        result = check_metadata(PackageDocsSidebar)
        # Assert
        assert result is PackageDocsSidebar

    def test_api_endpoint_is_set(self):
        # Arrange
        # Act
        endpoint = PackageDocsSidebar.api_endpoint
        # Assert
        assert endpoint


# EOF
