#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/examples/test_03_self_explanatory_demo.py

"""Smoke test for examples/03_self_explanatory_demo.py.

Per scitex-dev audit-project PS303: every example must have a matching test
under tests/examples/. This validates the example parses cleanly, matching its
siblings; end-to-end execution is covered by tests/scitex_ui/test_examples.py.

IT ALSO ASSERTS THE ONE PROPERTY THAT MAKES THE DEMO WORTH HAVING, which the
sibling smoke tests have no equivalent of: the page must be GENERATED FROM THE
REGISTRY rather than hand-written. A gallery that hardcodes its component list
is a second source of truth, and this package spent 2026-08-18 removing exactly
that shape from its stylesheets -- a palette duplicated across two layers,
drifted, and nothing noticed because an undefined CSS custom property renders as
nothing instead of erroring.

So a demo listing components it hardcodes would be the same defect in a new
place: green tests, a page that looks right, and a claim about the library that
stopped being true at some point nobody can name.
"""

import subprocess
import sys
from pathlib import Path

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "examples" / "03_self_explanatory_demo.py"
)


def test_the_example_file_exists_on_disk() -> None:
    # Arrange
    path = EXAMPLE
    # Act
    found = path.exists()
    # Assert
    assert found, f"missing example: {path}"


def test_the_example_compiles_without_syntax_errors() -> None:
    # Arrange
    cmd = [sys.executable, "-m", "py_compile", str(EXAMPLE)]
    # Act
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Assert
    assert result.returncode == 0, result.stderr


def test_the_component_list_comes_from_the_registry() -> None:
    """No hardcoded component names — the catalogue must be derived.

    Asserting on the SOURCE rather than the OUTPUT is deliberate: a page with
    32 correct rows proves nothing about where they came from, and the failure
    this guards against only shows up later, when the registry changes and the
    page does not.
    """
    # Arrange
    source = EXAMPLE.read_text(encoding="utf-8")
    # Act
    derives = "scitex_ui.list_components()" in source
    # Assert
    assert derives, (
        "the example must build its catalogue from scitex_ui.list_components(); "
        "a hardcoded list is a second source of truth that goes stale silently"
    )


def test_the_palette_is_read_from_the_shipped_stylesheet() -> None:
    """No hardcoded hex palette — colours must come from shell/theme.css.

    Same argument as the component list, one layer over: a demo that hardcodes
    the palette shows colours the library may have stopped using, which is worse
    than showing none, because it looks authoritative.
    """
    # Arrange
    source = EXAMPLE.read_text(encoding="utf-8")
    # Act
    derives = "get_static_dir()" in source and "theme.css" in source
    # Assert
    assert derives, (
        "the example must read its palette from the shipped shell/theme.css "
        "via scitex_ui.get_static_dir(), not from literals in this file"
    )


def test_the_accent_is_offered_as_a_choice_not_asserted_as_the_brand() -> None:
    """The demo exists to let the operator COMPARE accents, not to defend one.

    From the request that produced this example (Telegram msg 3639,
    2026-08-18): 「製品が紫、どうですかね、なんかよくわかってなくて、、」 -- the
    product being purple, how about it, I don't really understand it. That is
    uncertainty, not a verdict, so a page presenting one colour as the answer
    would fail the brief no matter how good the colour is.
    """
    # Arrange
    source = EXAMPLE.read_text(encoding="utf-8")
    # Act
    n_alternatives = source.count('", "#')  # ("name", "#light", "#dark") rows
    # Assert
    assert n_alternatives >= 4, (
        "the demo must offer several accents for live comparison; found "
        f"{n_alternatives} candidate rows in _ALTERNATIVES"
    )
