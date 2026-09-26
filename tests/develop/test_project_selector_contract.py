#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract for the ONE library-level project-selector primitive.

OPERATOR P1 (cross-app UX contract): every project-scoped app must present the
SAME layout template so a user can predict it; the project picker is a single
scitex-ui primitive, placed canonically on the LEFT of the app header (after
app identity/title, before app-specific actions), never arbitrarily
right-aligned, and responsively the same component on phones.

This test is STATIC on the shipped CSS + TS source — the half that runs in CI
on every change (same deliberate shape as test_responsive_shell_primitives.py).
A green here means "the guard and the one-primitive structure are present in
the stylesheet/source", not "the header is usable on a phone".

SHAPE: every detector carries a POSITIVE and a NEGATIVE control, so a broken
extractor cannot make the assertions vacuously true. Paths resolve from THIS
file, never scitex_ui.__file__ (the PR #152 failure class under a non-editable
install).
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CSS = _ROOT / "src/scitex_ui/static/scitex_ui/css/app/project-selector.css"
_TS = _ROOT / "src/scitex_ui/static/scitex_ui/ts"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _css() -> str:
    return _COMMENT.sub("", _CSS.read_text(errors="replace"))


def _rule_block(selector: str) -> str:
    """The text inside the FIRST rule whose selector list contains `selector`."""
    match = re.search(re.escape(selector) + r"\s*\{([^{}]*)\}", _css())
    return match.group(1) if match else ""


def _media_block(query: str, containing: str | None = None) -> str:
    """The text inside an @media matching `query`, comments stripped.

    When `containing` is given, returns the FIRST such block whose body also
    contains `containing` — needed because the file now has two 600px blocks
    (the component's and the header slot's) and the slot rules live in the
    latter.
    """
    text = _css()
    search_from = 0
    while True:
        match = re.search(r"@media[^{]*" + re.escape(query) + r"[^{]*\{", text[search_from:], re.I)
        if not match:
            return ""
        start = search_from + match.end() - 1
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    body = text[start + 1 : i]
                    if containing is None or containing in body:
                        return body
                    search_from = i + 1
                    break
        else:
            return ""


# ── Detector controls ─────────────────────────────────────────────────────

def test_rule_block_finds_a_real_rule() -> None:
    """Positive: the rule extractor is not blind."""
    # Arrange
    selector = ".stx-app-project-selector"
    # Act
    block = _rule_block(selector)
    # Assert
    assert "position" in block, "_rule_block returned no position for a known selector"


def test_rule_block_ignores_an_absent_selector() -> None:
    """Negative: a selector absent from the file yields an empty block."""
    # Arrange
    selector = ".stx-does-not-exist"
    # Act
    block = _rule_block(selector)
    # Assert
    assert block == "", f"_rule_block matched an absent selector: {block!r}"


def test_media_block_finds_the_phone_query() -> None:
    """Positive: the phone/coarse-pointer media block is locatable."""
    # Arrange
    query = "max-width: 600px"
    # Act
    block = _media_block(query)
    # Assert
    assert "44px" in block, "the phone media block has no 44px targets"


def test_comment_stripper_matches_a_real_css_comment() -> None:
    """Positive control for _COMMENT: it can match a real instance."""
    # Arrange
    sample = ".x { color: red; } /* trailing comment */"
    # Act
    matched = _COMMENT.search(sample)
    # Assert
    assert matched is not None, "_COMMENT cannot match a real CSS comment"


def test_comment_stripper_ignores_a_mere_mention() -> None:
    """Negative control for _COMMENT: a line that only mentions 'comment'
    is not a CSS block comment."""
    # Arrange
    sample = "# this line mentions comments but is not one"
    # Act
    matched = _COMMENT.search(sample)
    # Assert
    assert matched is None, "_COMMENT matched a mere mention of the word comment"


# ── Canonical left placement guard ────────────────────────────────────────

def test_header_slot_sets_an_explicit_order() -> None:
    """The guard exists and pins the slot's order, so a leaf cannot float it."""
    # Arrange
    block = _rule_block(".stx-app-header__slot--project-selector")
    # Act
    has_order = "order:" in block
    # Assert
    assert has_order, "the header slot must set an explicit order"


def test_header_slot_has_no_left_offset() -> None:
    """The slot sits immediately after the title: margin-left is 0."""
    # Arrange
    block = _rule_block(".stx-app-header__slot--project-selector")
    # Act
    has_zero_left = "margin-left:" in block and "0" in block
    # Assert
    assert has_zero_left, (
        "the header slot must carry margin-left:0 — it sits immediately after the title"
    )


def test_header_slot_uses_margin_right_auto() -> None:
    """margin-right:auto pushes app-specific actions right, keeping the
    selector left. Without it a leaf can right-align the selector."""
    # Arrange
    block = _rule_block(".stx-app-header__slot--project-selector")
    # Act
    has_auto_right = "margin-right: auto" in block
    # Assert
    assert has_auto_right, "the header slot must use margin-right:auto to pin the selector left"


def test_header_slot_order_is_one() -> None:
    """The slot is order 1: after identity/title (order 0), before actions (order 2+)."""
    # Arrange
    block = _rule_block(".stx-app-header__slot--project-selector")
    # Act
    has_order_one = re.search(r"order:\s*1\b", block) is not None
    # Assert
    assert has_order_one, (
        "the project selector must be order 1; a higher order lets it drift "
        "past the app-specific actions"
    )


def test_selector_does_not_self_right_align() -> None:
    """The base component must not declare a self-right-align; placement is
    the app header's job via the slot guard, not a per-app override."""
    # Arrange
    block = _rule_block(".stx-app-project-selector")
    # Act
    has_self_align = "margin-left: auto" in block or "margin-right:" in block
    # Assert
    assert not has_self_align, (
        "the component itself must not float right — placement belongs to the "
        "header slot guard, not the component"
    )


def test_phone_slot_is_full_width() -> None:
    """On phones the header slot spans the row: the trigger is a full-width
    tap target."""
    # Arrange
    block = _media_block("max-width: 600px", containing="stx-app-header__slot")
    # Act
    has_full_width = "width: 100%" in block
    # Assert
    assert has_full_width, "the phone header slot must be full-width"


def test_phone_slot_is_order_zero() -> None:
    """On the wrapped phone row the selector is the first thing: order 0."""
    # Arrange
    block = _media_block("max-width: 600px", containing="stx-app-header__slot")
    # Act
    has_order_zero = re.search(r"order:\s*0\b", block) is not None
    # Assert
    assert has_order_zero, "the phone header slot must be order 0 (first in the row)"


# ── Responsive: same component, 44px targets ─────────────────────────────

def test_phone_trigger_is_44px() -> None:
    """The trigger/search is 44px on phones (WCAG 2.5.5 + the operator's
    44px minimum)."""
    # Arrange
    block = _media_block("max-width: 600px")
    # Act
    has_44 = "height: 44px" in block
    # Assert
    assert has_44, "the phone trigger must be 44px tall"


def test_phone_options_are_44px_min() -> None:
    """The options are 44px min-height on phones."""
    # Arrange
    block = _media_block("max-width: 600px")
    # Act
    has_min_44 = "min-height: 44px" in block
    # Assert
    assert has_min_44, "the phone options must be 44px min-height"


def test_phone_panel_is_capped_not_hidden() -> None:
    """The phone panel caps its height (scrollable list) rather than hiding
    the picker — the same component is usable at 390."""
    # Arrange
    block = _media_block("max-width: 600px")
    # Act
    has_max_height = "max-height:" in block
    # Assert
    assert has_max_height, (
        "the phone panel must cap its height; hiding the picker would mean "
        "the component is not usable on a phone"
    )


# ── ONE primitive, not four (anti-fork guard) ────────────────────────────

def test_app_scope_selector_reuses_the_canonical_component() -> None:
    """The scope gate imports ProjectSelector from app/project-selector —
    it does not fork it."""
    # Arrange
    src = (_TS / "shell/app-scope-selector.ts").read_text(errors="replace")
    # Act
    reuses = 'from "../app/project-selector"' in src and "new ProjectSelector(" in src
    # Assert
    assert reuses, "app-scope-selector must mount the EXISTING ProjectSelector, not a copy"


def test_selector_nav_is_a_different_widget() -> None:
    """SelectorNav (the vertical nav strip) is NOT a project selector:
    different BEM root, no ProjectSelector import."""
    # Arrange
    src = (_ROOT / "src/scitex_ui/static/scitex_ui/react/app/selector-nav/SelectorNav.tsx").read_text(errors="replace")
    # Act
    is_nav = "stx-app-selector-nav" in src and "ProjectSelector" not in src
    # Assert
    assert is_nav, "SelectorNav must not import or alias the project picker — it is a nav strip"


def test_canonical_bundle_has_the_generated_header() -> None:
    """The distributable entry is js/app/project-selector.js, the esbuild
    bundle of project-selector/auto-mount.ts — the same component, one name."""
    # Arrange
    bundle = (_ROOT / "src/scitex_ui/static/scitex_ui/js/app/project-selector.js").read_text(errors="replace")
    # Act
    has_header = "AUTO-GENERATED from ts/app/project-selector/auto-mount.ts" in bundle
    # Assert
    assert has_header, (
        "project-selector.js must be the generated bundle of the canonical "
        "project-selector, not a hand-maintained second picker"
    )


def test_project_picker_js_is_marked_deprecated() -> None:
    """The old entry name is marked @deprecated so consumers migrate."""
    # Arrange
    alias = (_ROOT / "src/scitex_ui/static/scitex_ui/js/app/project-picker.js").read_text(errors="replace")
    # Act
    has_deprecated = "@deprecated" in alias
    # Assert
    assert has_deprecated, (
        "project-picker.js must be marked @deprecated so consumers know to "
        "migrate to project-selector.js"
    )


def test_project_picker_js_loads_the_canonical_bundle() -> None:
    """The alias loads the canonical bundle so old pages keep working."""
    # Arrange
    alias = (_ROOT / "src/scitex_ui/static/scitex_ui/js/app/project-picker.js").read_text(errors="replace")
    # Act
    loads_canonical = "project-selector.js" in alias
    # Assert
    assert loads_canonical, "the alias must import the canonical bundle"


def test_project_picker_js_is_not_the_generated_bundle() -> None:
    """The alias is hand-maintained, not the generated bundle — the bundle
    is project-selector.js."""
    # Arrange
    alias = (_ROOT / "src/scitex_ui/static/scitex_ui/js/app/project-picker.js").read_text(errors="replace")
    # Act
    is_generated = "AUTO-GENERATED" in alias
    # Assert
    assert not is_generated, (
        "project-picker.js is now a hand-maintained alias; the generated "
        "bundle is project-selector.js"
    )


# ── Provider URL contract ─────────────────────────────────────────────────

def test_provider_has_list_projects() -> None:
    """The provider contract requires a listProjects() method."""
    # Arrange
    src = (_TS / "app/project-selector/provider.ts").read_text(errors="replace")
    # Act
    has_list = "listProjects" in src
    # Assert
    assert has_list, "provider.ts must define listProjects()"


def test_provider_has_remember_project() -> None:
    """The provider contract requires a rememberProject() method."""
    # Arrange
    src = (_TS / "app/project-selector/provider.ts").read_text(errors="replace")
    # Act
    has_remember = "rememberProject" in src
    # Assert
    assert has_remember, "provider.ts must define rememberProject()"


def test_provider_remember_is_a_post() -> None:
    """rememberProject POSTs to the provider URL."""
    # Arrange
    src = (_TS / "app/project-selector/provider.ts").read_text(errors="replace")
    # Act
    is_post = 'method: "POST"' in src
    # Assert
    assert is_post, "rememberProject must be a POST request"


def test_provider_uses_same_origin_credentials() -> None:
    """The provider is same-origin; auth via cookies/CSRF, not tokens in URLs."""
    # Arrange
    src = (_TS / "app/project-selector/provider.ts").read_text(errors="replace")
    # Act
    same_origin = 'credentials: "same-origin"' in src
    # Assert
    assert same_origin, "the provider must use same-origin credentials"
