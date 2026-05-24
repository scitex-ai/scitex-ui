#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_mcp/test_inspect.py

"""Tests for scitex_ui._mcp.inspect — element-inspection handlers.

The handlers shell out to ``playwright-cli`` via ``subprocess.run``.  Tests
inject a hand-rolled fake runner so the suite exercises the real subprocess
codepath without requiring a real browser.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from scitex_ui._mcp.inspect import (
    inspect_element_handler,
    inspect_elements_handler,
)


# ---------------------------------------------------------------------------
# Hand-rolled fake subprocess runner
# ---------------------------------------------------------------------------


def _fake_runner(
    *,
    stdout: str = "",
    returncode: int = 0,
    side_effect: Exception | None = None,
):
    """Build a callable that mimics ``subprocess.run`` for testing.

    Parameters
    ----------
    stdout : str
        Standard output the fake process returns.
    returncode : int
        Exit code.
    side_effect : Exception or None
        If set, the callable raises this instead of returning.
    """

    def _run(_cmd: list[str], **_kw: Any) -> subprocess.CompletedProcess:
        if side_effect is not None:
            raise side_effect
        return subprocess.CompletedProcess(
            args=_cmd,
            returncode=returncode,
            stdout=stdout,
            stderr="",
        )

    return _run


def _wrap_eval_result(payload: dict | str) -> str:
    """Mirror playwright-cli's eval output framing: '### Result\\n<value>\\n###...'.

    The handler unquotes JSON-string-encoded payloads, so we encode dicts
    twice (json.dumps then json.dumps again to produce a quoted string).
    """
    inner = json.dumps(payload) if isinstance(payload, dict) else payload
    quoted = json.dumps(inner)  # turns it into "{\"key\":...}"
    return f"### Result\n{quoted}\n### Ran Playwright code\n"


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_SUCCESS_PAYLOAD = {
    "url": "http://example.com",
    "element": {"tag": "div", "id": "foo", "classes": []},
    "attributes": {},
    "computed": {"display": "block"},
    "inline": "",
    "dimensions": {"width": 100, "height": 50, "top": 0, "left": 0},
    "parentChain": [],
    "matchingRules": [],
}

_ELEMENTS_PAYLOAD = {
    "total": 2,
    "elements": [
        {"index": 0, "tag": "div", "id": None, "classes": "a"},
        {"index": 1, "tag": "div", "id": None, "classes": "a"},
    ],
}


# ---------------------------------------------------------------------------
# inspect_element_handler
# ---------------------------------------------------------------------------


def test_inspect_element_returns_success_true_on_valid_result():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_SUCCESS_PAYLOAD))
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert result["success"] is True


def test_inspect_element_returns_element_tag_from_data():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_SUCCESS_PAYLOAD))
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert result["data"]["element"]["tag"] == "div"


def test_inspect_element_reports_success_false_when_browser_returns_error():
    # Arrange
    err_payload = {"error": "Element not found: #missing"}
    runner = _fake_runner(stdout=_wrap_eval_result(err_payload))
    # Act
    result = inspect_element_handler("#missing", _run=runner)
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_error_message_when_element_not_found():
    # Arrange
    err_payload = {"error": "Element not found: #missing"}
    runner = _fake_runner(stdout=_wrap_eval_result(err_payload))
    # Act
    result = inspect_element_handler("#missing", _run=runner)
    # Assert
    assert "Element not found" in result["error"]


def test_inspect_element_reports_success_false_when_cli_missing():
    # Arrange
    runner = _fake_runner(side_effect=FileNotFoundError())
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_playwright_cli_in_error_when_cli_missing():
    # Arrange
    runner = _fake_runner(side_effect=FileNotFoundError())
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert "playwright-cli" in result["error"]


def test_inspect_element_reports_success_false_on_timeout():
    # Arrange
    runner = _fake_runner(
        side_effect=subprocess.TimeoutExpired(cmd="playwright-cli", timeout=10)
    )
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_timed_out_in_error_on_timeout():
    # Arrange
    runner = _fake_runner(
        side_effect=subprocess.TimeoutExpired(cmd="playwright-cli", timeout=10)
    )
    # Act
    result = inspect_element_handler("#foo", _run=runner)
    # Assert
    assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# inspect_elements_handler
# ---------------------------------------------------------------------------


def test_inspect_elements_returns_success_true_on_valid_result():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_ELEMENTS_PAYLOAD))
    # Act
    result = inspect_elements_handler(".a", limit=5, _run=runner)
    # Assert
    assert result["success"] is True


def test_inspect_elements_returns_selector_from_input():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_ELEMENTS_PAYLOAD))
    # Act
    result = inspect_elements_handler(".a", limit=5, _run=runner)
    # Assert
    assert result["selector"] == ".a"


def test_inspect_elements_returns_total_count():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_ELEMENTS_PAYLOAD))
    # Act
    result = inspect_elements_handler(".a", limit=5, _run=runner)
    # Assert
    assert result["total"] == 2


def test_inspect_elements_returns_correct_elements_length():
    # Arrange
    runner = _fake_runner(stdout=_wrap_eval_result(_ELEMENTS_PAYLOAD))
    # Act
    result = inspect_elements_handler(".a", limit=5, _run=runner)
    # Assert
    assert len(result["elements"]) == 2


def test_inspect_elements_reports_success_false_when_cli_missing():
    # Arrange
    runner = _fake_runner(side_effect=FileNotFoundError())
    # Act
    result = inspect_elements_handler(".a", _run=runner)
    # Assert
    assert result["success"] is False


def test_inspect_elements_reports_playwright_cli_in_error_when_cli_missing():
    # Arrange
    runner = _fake_runner(side_effect=FileNotFoundError())
    # Act
    result = inspect_elements_handler(".a", _run=runner)
    # Assert
    assert "playwright-cli" in result["error"]


# EOF
