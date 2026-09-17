#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Smoke test for examples/04_mobile_panes_demo.py.

Two layers, deliberately:

1. The house smoke (compiles, exercises the template tag) — cheap, runs
   everywhere, and cannot see whether the page actually WORKS.
2. A build-level check that the page does not reference assets it inlines.

WHY THE SECOND LAYER EXISTS. The demo inlines panes.css and panes.js and then
removes the tags that would load them from a server — because the page is meant
to open from disk, where there is no server to answer. Django's {% static %}
appends a cache-busting query to those URLs, so a pattern anchored on the
closing quote right after ".css" matched NOTHING, and the page shipped two dead
references on every load. Measured 2026-09-17 in a browser at 1440x900 and
390x844: both 404 — invisible, because the inlined copies still styled and drove
the panes. Nothing looked wrong; only the network log said so.

A source-level assertion cannot catch that class of defect: it can see the
pattern, not whether it matches. So this builds the page and reads the output.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "04_mobile_panes_demo.py"

#: Any same-origin asset the page asks a server for. The page is standalone, so
#: the correct number of these is zero.
_ABSOLUTE_ASSET = re.compile(r'(?:href|src)="(/static/[^"]+)"')


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


def _build_page() -> str:
    """The demo's own ``build()``, with the session framework stood in for.

    ``build()`` is the only place the asset-stripping is observable, and the
    stand-in is narrow on purpose: ``@stx.session`` wraps ``main``, which writes
    to a session directory. ``main`` is never called here, and if
    ``scitex_session`` is genuinely installed it is left alone.
    """
    if EXAMPLE.parent.parent.joinpath("src").is_dir():  # a source checkout
        sys.path.insert(0, str(EXAMPLE.parent.parent / "src"))

    installed = "scitex_session" in sys.modules
    if not installed:
        stub = ModuleType("scitex_session")
        # setattr, not attribute assignment: a module has no such attributes
        # declared, and the static checkers read `stub.INJECTED = ...` on a
        # ModuleType as an error rather than as the stand-in it is.
        setattr(stub, "INJECTED", object())
        setattr(stub, "session", lambda fn=None, *a, **k: fn if fn is not None else (lambda f: f))
        sys.modules["scitex_session"] = stub

    try:
        spec = importlib.util.spec_from_file_location("_example_04_mobile_panes_demo", EXAMPLE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build()
    except (ImportError, ModuleNotFoundError) as exc:  # no django in this env
        pytest.skip(f"cannot build the demo page here: {exc}")
    finally:
        if not installed:
            sys.modules.pop("scitex_session", None)


def test_the_page_never_asks_a_server_for_an_asset_it_inlines() -> None:
    """Zero same-origin asset requests: this page is opened from disk."""
    # Arrange
    page = _build_page()
    # Act
    referenced = _ABSOLUTE_ASSET.findall(page)
    # Assert
    assert referenced == [], (
        "the demo inlines panes.css/panes.js, so the page must not also reference "
        f"them at /static/ — found {referenced}. Django's {{% static %}} appends "
        '"?v=<hash>", so a strip pattern anchored on the quoting silently matches '
        "nothing and the page 404s on every load."
    )


def test_the_inlined_assets_are_the_shipped_stylesheet_and_module() -> None:
    """Removing the dead references must not remove the working copies."""
    # Arrange
    page = _build_page()
    # Act
    has_stylesheet = ".stx-panes__tab" in page and ".stx-panes--single" in page
    has_module = "mountPanes" in page and "stx-panes--single" in page
    # Assert
    assert has_stylesheet, "the inlined css/app/panes.css must reach the page"
    assert has_module, "the inlined js/app/panes.js must reach the page"
