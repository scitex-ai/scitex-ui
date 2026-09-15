#!/usr/bin/env python3
"""Smoke test for examples/04_mobile_panes_demo.py."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "04_mobile_panes_demo.py"


def test_the_example_compiles_without_syntax_errors() -> None:
    # Arrange
    cmd = [sys.executable, "-m", "py_compile", str(EXAMPLE)]
    # Act
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Assert
    assert result.returncode == 0, result.stderr


def test_the_demo_renders_panes_through_the_template_tag() -> None:
    # Arrange
    source = EXAMPLE.read_text(encoding="utf-8")
    # Act
    uses_tag = "{% scitex_panes" in source
    # Assert
    assert uses_tag, "the demo must exercise {% scitex_panes %}, not hand-written markup"
