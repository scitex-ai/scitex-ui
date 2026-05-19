#!/usr/bin/env python3
"""Tests for component registry."""

from scitex_ui._registry import get_component, list_components, register_component


class TestRegisterComponent:
    def test_register_and_get(self):
        # Arrange
        register_component("test-widget", {"version": "0.1.0"})
        # Act
        result = get_component("test-widget")
        # Assert
        assert result == {"version": "0.1.0"}

    def test_get_nonexistent_returns_none(self):
        # Arrange
        # Act
        result = get_component("nonexistent-component")
        # Assert
        assert result is None

    def test_list_components_sorted_names_is_list(self):
        # Arrange
        # Arrange
        register_component("z-widget", {})
        register_component("a-widget", {})
        # Act
        names = list_components()
        # Act
        # Assert
        # Assert
        assert isinstance(names, list)

    def test_list_components_sorted_names_equals_sorted_names(self):
        # Arrange
        # Arrange
        register_component("z-widget", {})
        register_component("a-widget", {})
        # Act
        names = list_components()
        # Act
        # Assert
        # Assert
        assert names == sorted(names)


    def test_list_components_includes_registered(self):
        # Arrange
        register_component("list-test-widget", {})
        # Act
        names = list_components()
        # Assert
        assert "list-test-widget" in names
