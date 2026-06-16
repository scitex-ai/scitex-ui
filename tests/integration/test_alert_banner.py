#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural guards for the AlertBanner React component.

scitex-ui has no JS test runner, so React behaviour is not unit-tested here;
these assert the component ships and stays wired (file present, exported, CSS
bundled) so it cannot silently disappear from the SDK surface.
"""

import scitex_ui


class TestAlertBannerComponent:
    def test_component_file_exists(self):
        # Arrange
        static = scitex_ui.get_static_dir()
        # Act
        target = static / "react" / "app" / "alert-banner" / "AlertBanner.tsx"
        # Assert
        assert target.is_file()

    def test_exported_from_react_app_index(self):
        # Arrange
        static = scitex_ui.get_static_dir()
        index = static / "react" / "app" / "index.ts"
        # Act
        source = index.read_text(encoding="utf-8")
        # Assert
        assert "AlertBanner" in source

    def test_css_present_and_bundled(self):
        # Arrange
        static = scitex_ui.get_static_dir()
        css = static / "css" / "app" / "alert-banner.css"
        all_css = (static / "css" / "all.css").read_text(encoding="utf-8")
        # Act
        bundled = css.is_file() and "app/alert-banner.css" in all_css
        # Assert
        assert bundled
