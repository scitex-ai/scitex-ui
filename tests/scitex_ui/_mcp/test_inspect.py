#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_mcp/test_inspect.py

"""Tests for scitex_ui._mcp.inspect — element-inspection handlers.

The handlers shell out to `playwright-cli`; we patch the subprocess so the
suite runs in CI without a real browser.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from scitex_ui._mcp.inspect import (
    inspect_element_handler,
    inspect_elements_handler,
)


def _fake_completed(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(
        args=["playwright-cli", "eval", "..."],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def _wrap_eval_result(payload: dict | str) -> str:
    """Mirror playwright-cli's eval output framing: '### Result\\n<value>\\n###...'.

    The handler unquotes JSON-string-encoded payloads, so we encode dicts
    twice (json.dumps then json.dumps again to produce a quoted string).
    """
    inner = json.dumps(payload) if isinstance(payload, dict) else payload
    quoted = json.dumps(inner)  # turns it into "{\"key\":...}"
    return f"### Result\n{quoted}\n### Ran Playwright code\n"


# ---------------------------------------------------------------------------
# inspect_element_handler
# ---------------------------------------------------------------------------


def test_inspect_element_returns_data_on_success_result_success_is_true():
    # Arrange
    # Arrange
    payload = {
        "url": "http://example.com",
        "element": {"tag": "div", "id": "foo", "classes": []},
        "attributes": {},
        "computed": {"display": "block"},
        "inline": "",
        "dimensions": {"width": 100, "height": 50, "top": 0, "left": 0},
        "parentChain": [],
        "matchingRules": [],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert result["success"] is True


def test_inspect_element_returns_data_on_success_result_data_element_tag_div():
    # Arrange
    # Arrange
    payload = {
        "url": "http://example.com",
        "element": {"tag": "div", "id": "foo", "classes": []},
        "attributes": {},
        "computed": {"display": "block"},
        "inline": "",
        "dimensions": {"width": 100, "height": 50, "top": 0, "left": 0},
        "parentChain": [],
        "matchingRules": [],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert result["data"]["element"]["tag"] == "div"




def test_inspect_element_propagates_browser_error_result_success_is_false():
    # Arrange
    # Arrange
    err_payload = {"error": "Element not found: #missing"}
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(err_payload))
    ):
        result = inspect_element_handler("#missing")
    # Act
    # Assert
    # Assert
    assert result["success"] is False


def test_inspect_element_propagates_browser_error_element_not_found_in_result_error():
    # Arrange
    # Arrange
    err_payload = {"error": "Element not found: #missing"}
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(err_payload))
    ):
        result = inspect_element_handler("#missing")
    # Act
    # Assert
    # Assert
    assert "Element not found" in result["error"]




def test_inspect_element_when_playwright_cli_missing_result_success_is_false():
    # Arrange
    # Arrange
    # Act
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert result["success"] is False


def test_inspect_element_when_playwright_cli_missing_playwright_cli_in_result_error():
    # Arrange
    # Arrange
    # Act
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert "playwright-cli" in result["error"]




def test_inspect_element_on_subprocess_timeout_result_success_is_false():
    # Arrange
    # Arrange
    # Act
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="playwright-cli", timeout=10),
    ):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert result["success"] is False


def test_inspect_element_on_subprocess_timeout_timed_out_in_result_error():
    # Arrange
    # Arrange
    # Act
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="playwright-cli", timeout=10),
    ):
        result = inspect_element_handler("#foo")
    # Act
    # Assert
    # Assert
    assert "timed out" in result["error"]




# ---------------------------------------------------------------------------
# inspect_elements_handler
# ---------------------------------------------------------------------------


def test_inspect_elements_returns_total_and_elements_result_success_is_true():
    # Arrange
    # Arrange
    payload = {
        "total": 2,
        "elements": [
            {"index": 0, "tag": "div", "id": None, "classes": "a"},
            {"index": 1, "tag": "div", "id": None, "classes": "a"},
        ],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_elements_handler(".a", limit=5)
    # Act
    # Assert
    # Assert
    assert result["success"] is True


def test_inspect_elements_returns_total_and_elements_result_selector_a():
    # Arrange
    # Arrange
    payload = {
        "total": 2,
        "elements": [
            {"index": 0, "tag": "div", "id": None, "classes": "a"},
            {"index": 1, "tag": "div", "id": None, "classes": "a"},
        ],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_elements_handler(".a", limit=5)
    # Act
    # Assert
    # Assert
    assert result["selector"] == ".a"


def test_inspect_elements_returns_total_and_elements_result_total_2():
    # Arrange
    # Arrange
    payload = {
        "total": 2,
        "elements": [
            {"index": 0, "tag": "div", "id": None, "classes": "a"},
            {"index": 1, "tag": "div", "id": None, "classes": "a"},
        ],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_elements_handler(".a", limit=5)
    # Act
    # Assert
    # Assert
    assert result["total"] == 2


def test_inspect_elements_returns_total_and_elements_len_result_elements_is_2():
    # Arrange
    # Arrange
    payload = {
        "total": 2,
        "elements": [
            {"index": 0, "tag": "div", "id": None, "classes": "a"},
            {"index": 1, "tag": "div", "id": None, "classes": "a"},
        ],
    }
    # Act
    with patch(
        "subprocess.run", return_value=_fake_completed(_wrap_eval_result(payload))
    ):
        result = inspect_elements_handler(".a", limit=5)
    # Act
    # Assert
    # Assert
    assert len(result["elements"]) == 2




def test_inspect_elements_passes_selector_through_on_failure_result_success_is_false():
    # Arrange
    # Arrange
    # Act
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = inspect_elements_handler(".a")
    # Act
    # Assert
    # Assert
    assert result["success"] is False


def test_inspect_elements_passes_selector_through_on_failure_playwright_cli_in_result_error():
    # Arrange
    # Arrange
    # Act
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = inspect_elements_handler(".a")
    # Act
    # Assert
    # Assert
    assert "playwright-cli" in result["error"]




# EOF
