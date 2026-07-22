#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_components/conftest.py

"""Shared fixtures and helpers for per-component metadata tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import scitex_ui
from scitex_ui._registry import get_component

PKG_DIR = Path(scitex_ui.__file__).parent


def _check_metadata(cls):
    """Verify common metadata fields and on-disk asset existence.

    Either asset may be ``None``: a component can be CSS-only (the nine
    `stx-app-*` styles apps drive with their own handlers) or JS-only
    (monaco-editor, whose styles arrive through its bundle). Requiring both
    is what forced monaco-editor to bypass this helper with a hand-written
    test — so this checks each asset only when declared, and requires at
    least one, which is the property that actually matters: a component
    that ships nothing is a registry entry pointing at nothing.

    Returns the class on success so callers can `assert check_metadata(Cls)`.
    """
    assert cls.name
    # Shape, not value: pinning a literal version here froze every component
    # at 0.1.0 — the first real bump (context-menu 0.2.0) failed this line.
    assert re.fullmatch(r"\d+\.\d+\.\d+", cls.version), (
        f"{cls.name} version {cls.version!r} is not X.Y.Z"
    )
    assert cls.description
    assert cls.ts_entry or cls.css_file, f"{cls.name} declares no asset at all"

    # Registered in registry under its canonical name.
    assert get_component(cls.name) is cls

    if cls.css_file:
        css_path = PKG_DIR / "static" / cls.css_file
        assert css_path.exists(), f"CSS not found: {css_path}"

    if cls.ts_entry:
        ts_path = PKG_DIR / "static" / (cls.ts_entry + ".ts")
        assert ts_path.exists(), f"TS entry not found: {ts_path}"

    # Optional pre-built pure-JS sibling for Django-template consumers
    # (no vite). Verified only when the component declares ``js_file`` —
    # other components stay unchanged.
    js_file = getattr(cls, "js_file", None)
    if js_file:
        js_path = PKG_DIR / "static" / js_file
        assert js_path.exists(), f"JS bundle not found: {js_path}"

    return cls


@pytest.fixture
def check_metadata():
    """Fixture exposing the metadata sanity checker to per-component tests."""
    return _check_metadata


# EOF
