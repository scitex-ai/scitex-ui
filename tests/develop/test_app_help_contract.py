#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the in-app "How to use" primitive (app-help).

The `?` panel + first-open coach-mark tour share ONE per-app steps file
(JSON/YAML, EN/JA). These guards are STATIC on the shipped CSS + the
templatetag + the prebuilt bundle — the half that runs in CI on every change
(same deliberate shape as test_project_selector_contract.py and
test_responsive_shell_primitives.py). Behaviour (open/close/replay/first-
open-once) is covered by the vitest suite (tests/scitex_ui/vitest/
app-help.test.ts).
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CSS = _ROOT / "src/scitex_ui/static/scitex_ui/css/app/app-help.css"
_BUNDLE = _ROOT / "src/scitex_ui/static/scitex_ui/js/app/app-help.js"
_TAG = _ROOT / "src/scitex_ui/templatetags/scitex_help.py"
_COMPONENT = _ROOT / "src/scitex_ui/static/scitex_ui/ts/app/app-help/_AppHelp.ts"


def _css() -> str:
    return _CSS.read_text(errors="replace")


def test_the_question_button_is_a_44px_touch_target() -> None:
    """The `?` button is the only thing the user must reach by eye — 44px."""
    # Arrange
    css = _css()
    # Act
    match = re.search(r"\.stx-app-help__button\s*\{([^}]*)\}", css)
    body = match.group(1) if match else ""
    # Assert
    assert "min-width: 44px" in body and "min-height: 44px" in body, (
        "the app-help `?` button must be at least 44px on both axes"
    )


def test_the_panel_never_exceeds_the_viewport_width() -> None:
    """Desktop: the panel is capped to min(380px, 100vw) so it cannot push the
    page wider than the viewport."""
    # Arrange
    css = _css()
    # Act
    capped = "width: min(380px, 100vw)" in css
    # Assert
    assert capped, "the help panel must cap its width to min(380px, 100vw)"


def test_phone_panel_is_full_width() -> None:
    """On phones the panel spans the row (100vw) — the same primitive, no
    separate mobile component."""
    # Arrange
    css = _css()
    # Act
    phone = re.search(r"@media[^{]*max-width:\s*600px[^{]*\{(.*?)\}\s*\}", css, re.S)
    # Assert
    assert phone is not None and "width: 100vw" in phone.group(1), (
        "the phone help panel must be 100vw"
    )


def test_step_body_wraps_long_tokens() -> None:
    """A long token/URL in a step body must wrap, not force horizontal scroll."""
    # Arrange
    css = _css()
    # Act
    wraps = "overflow-wrap: anywhere" in css
    # Assert
    assert wraps, "step bodies must use overflow-wrap:anywhere to avoid horizontal overflow"


def test_first_open_state_is_namespaced_per_app() -> None:
    """The first-open marker is stx-help:<app>:done (same per-app namespace
    pattern as panes' stx-panes:<app>), so two apps on one page don't share it."""
    # Arrange
    src = _COMPONENT.read_text(errors="replace")
    # Act
    namespaced = "stx-help:" in src and ":done" in src
    # Assert
    assert namespaced, "the first-open state must be namespaced per app (stx-help:<app>:done)"


def test_the_templatetag_emits_the_button_and_guide_payload() -> None:
    """{% stx_help %} renders the data-stx-help root, the guide json_script
    element, and the app-help.css/js (versioned)."""
    # Arrange
    src = _TAG.read_text(errors="replace")
    # Act
    has_root = 'data-stx-help' in src
    has_payload = 'type="application/json"' in src
    has_assets = "app-help.css" in src and "app-help.js" in src
    # Assert
    assert has_root and has_payload and has_assets, (
        "the {% stx_help %} tag must emit the help root, the guide json payload, "
        "and the css/js assets"
    )


def test_the_prebuilt_bundle_is_generated_from_the_source() -> None:
    """js/app/app-help.js is the esbuild bundle of ts/app/app-help/auto-mount.ts."""
    # Arrange
    bundle = _BUNDLE.read_text(errors="replace")
    # Act
    generated = "AUTO-GENERATED from ts/app/app-help/auto-mount.ts" in bundle
    # Assert
    assert generated, (
        "app-help.js must remain the generated bundle of the canonical "
        "ts/app/app-help/auto-mount.ts, not a hand-maintained copy"
    )


def test_the_component_reads_the_guide_from_the_page_not_a_hardcoded_list() -> None:
    """The component loads its steps from the app's json_script element — the
    leaf declares content, the component renders it (no hardcoded steps)."""
    # Arrange
    src = _COMPONENT.read_text(errors="replace")
    # Act
    loads = "getElementById" in src and "stx-app-help-" in src
    # Assert
    assert loads, (
        "AppHelp must read its guide from the page's stx-app-help-<app> "
        "json_script element, not from a hardcoded step list"
    )
