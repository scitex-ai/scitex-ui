#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_ui/_components/conftest.py

"""Shared fixtures and helpers for per-component metadata tests."""

from __future__ import annotations

from pathlib import Path

import pytest

import scitex_ui
from scitex_ui._registry import get_component

PKG_DIR = Path(scitex_ui.__file__).parent


def _check_metadata(cls):
    """Verify common metadata fields and on-disk asset existence.

    Returns the class on success so callers can `assert check_metadata(Cls)`.
    """
    assert cls.name
    assert cls.version == "0.1.0"
    assert cls.description
    assert cls.ts_entry
    assert cls.css_file

    # Registered in registry under its canonical name.
    assert get_component(cls.name) is cls

    css_path = PKG_DIR / "static" / cls.css_file
    assert css_path.exists(), f"CSS not found: {css_path}"

    ts_path = PKG_DIR / "static" / (cls.ts_entry + ".ts")
    assert ts_path.exists(), f"TS entry not found: {ts_path}"

    return cls


@pytest.fixture
def check_metadata():
    """Fixture exposing the metadata sanity checker to per-component tests."""
    return _check_metadata


# EOF
