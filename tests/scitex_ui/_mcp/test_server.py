#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_mcp/test_server.py

"""Tests for scitex_ui._mcp.server — MCP smoke + tool invocation."""

import asyncio
import json

import pytest

# fastmcp is an optional dep (scitex-ui[mcp]); skip the whole module if
# it isn't installed so pytest collection stays green (PA-303).
pytest.importorskip("fastmcp")

from scitex_ui._mcp.server import mcp, ui_skills_get, ui_skills_list  # noqa: E402


# ---------------------------------------------------------------------------
# Server / list_tools smoke
# ---------------------------------------------------------------------------


def test_server_name_mcp_name_equals_scitex_ui():
    # Arrange
    # Act
    # Assert
    assert mcp.name == "scitex-ui"


def test_list_tools_async_returns_expected_tools_ui_skills_list_in_names():
    # Arrange
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Act
    # Assert
    # Assert
    assert "ui_skills_list" in names, f"missing ui_skills_list, got {names}"


def test_list_tools_async_returns_expected_tools_ui_skills_get_in_names():
    # Arrange
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Act
    # Assert
    # Assert
    assert "ui_skills_get" in names, f"missing ui_skills_get, got {names}"




def test_list_tools_have_descriptions():
    # Arrange
    # Act
    # Assert
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        assert t.description, f"tool {t.name} has empty description"


# ---------------------------------------------------------------------------
# Direct function invocation (sync) — exercises the JSON envelope contract
# ---------------------------------------------------------------------------


def test_ui_skills_list_returns_known_skills_payload_success_is_true():
    # Arrange
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["success"] is True


def test_ui_skills_list_returns_known_skills_payload_package_scitex_ui():
    # Arrange
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["package"] == "scitex-ui"


def test_ui_skills_list_returns_known_skills_isinstance_payload_skills_list():
    # Arrange
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert isinstance(payload["skills"], list)


def test_ui_skills_list_returns_known_skills_n_03_python_api_in_payload_skills():
    # Arrange
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert "03_python-api" in payload["skills"]




def test_ui_skills_get_known_page_payload_success_is_true():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["success"] is True


def test_ui_skills_get_known_page_payload_name_03_python_api():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["name"] == "03_python-api"


def test_ui_skills_get_known_page_isinstance_payload_content_str():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert isinstance(payload["content"], str)


def test_ui_skills_get_known_page_payload_content_strip():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["content"].strip(), "skill content must be non-empty"




def test_ui_skills_get_unknown_page_reports_available_payload_success_is_false():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="this-skill-does-not-exist")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert payload["success"] is False


def test_ui_skills_get_unknown_page_reports_available_available_in_payload_error():
    # Arrange
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="this-skill-does-not-exist")
    # Act
    payload = json.loads(raw)
    # Act
    # Assert
    # Assert
    assert "available" in payload["error"]




# ---------------------------------------------------------------------------
# End-to-end async tool invocation through the registered MCP machinery
# ---------------------------------------------------------------------------


def test_call_tool_ui_skills_list_via_mcp_payload_success_is_true():
    # Arrange
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_list", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Act
    # Assert
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_skills_list_via_mcp_skills_in_payload():
    # Arrange
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_list", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Act
    # Assert
    # Assert
    assert "skills" in payload




def test_call_tool_ui_skills_get_via_mcp_payload_success_is_true():
    # Arrange
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_get", {"name": "03_python-api"}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Act
    # Assert
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_skills_get_via_mcp_payload_name_03_python_api():
    # Arrange
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_get", {"name": "03_python-api"}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Act
    # Assert
    # Assert
    assert payload["name"] == "03_python-api"




# EOF
