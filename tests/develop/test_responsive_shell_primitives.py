#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared responsive shell primitives (card
scitex-ui-responsive-shell-primitives-20260914) — the guard.

THE DEFECT this ships against, measured 2026-08-22 on live production at
390x844 (hub-mobile-390-workspace-shell-overflows-and-hides-controls-20260822):
the workspace shell overflows exactly 48px, driven by the hub's in-flow
``#mobile-hamburger-btn``; cards (standalone shell) overflowed 0, so the shared
cause is the workspace shell, not a per-app leaf. 48 == the shell rail
``--ui-collapsed-pane-width``.

THE CONTRACT, agreed with scitex-hub (DM, 2026-09-13): the shared shell ships
(a) a no-horizontal-overflow guard (``overflow-x: clip`` — NOT ``hidden``, and
NOT ``min-width: 0`` alone, which the hub measured to be a WORSE bug: it shrinks
the header-left box while its content paints over the visitor badge, invisible
to getBoundingClientRect and caught only by elementFromPoint), (b) shared
responsive tokens (breakpoint / touch-min / safe-area) in theme.css so hub and
every leaf reference the SAME value instead of re-hardcoding 768px / 44px /
env(safe-area-inset-*), and (c) two small utilities (touch-target minimum +
keyboard focus ring) that were previously re-implemented per leaf.

This test is STATIC on the shipped CSS — the half that can run in CI on every
change. It is weaker than the 390px browser measurement (recorded on the card
with a consuming-route screenshot), in exactly the same deliberate way
test_mobile_panes_stay_reachable.py is: a green here means "the guard and the
tokens are present in the stylesheet", not "the shell is usable on a phone".

SHAPE: every detector in this file carries a POSITIVE and a NEGATIVE control,
per test_detectors_carry_controls.py — a guard whose extractor stops matching
turns every assertion vacuously true. The ``_COMMENT`` stripper is exempted
there (same shape as test_mobile_panes_stay_reachable.py's _COMMENT) because a
comment stripper is only exercised through .sub(), not .search().
"""

from __future__ import annotations

import pathlib
import re

import pytest

# From THIS FILE, never scitex_ui.__file__ — under a non-editable install the
# latter points into site-packages and the guard would assert about a
# different tree than the branch under review (the PR #152 failure class).
_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "css"
)
_MOBILE = _CSS / "shell" / "mobile.css"
_THEME = _CSS / "shell" / "theme.css"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def _mobile_block() -> str:
    """The text inside ``@media (max-width: 768px)``, comments stripped.

    Brace-matched (not regex-lazy) so nested rules are not truncated — the
    same extractor test_mobile_panes_stay_reachable.py relies on.
    """
    text = _COMMENT.sub("", _MOBILE.read_text(errors="replace"))
    match = re.search(r"@media[^{]*max-width:\s*768px[^{]*\{", text, re.I)
    if not match:
        return ""
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    return text[start:]


# --- the overflow guard ----------------------------------------------------


def test_the_mobile_media_block_is_present() -> None:
    # Arrange
    # Act
    block = _mobile_block()
    # Assert
    assert len(block) > 500, (
        f"extracted {len(block)} chars from the <=768px block in "
        f"{_MOBILE.name}; a broken read would make every guard below vacuous"
    )


def test_the_viewport_fit_guard_is_defined() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    defined = bool(
        re.search(r"\.stx-viewport-fit\b[^{]*\{", block)
    )
    # Assert
    assert defined, (
        ".stx-viewport-fit is not defined in the <=768px block; the shared "
        "no-horizontal-overflow guard is missing and the 48px regression "
        "returns the moment the hub's header row stops shrinking"
    )


def test_the_viewport_fit_guard_uses_clip() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    guard = [
        body
        for sel, body in _RULE.findall(block)
        if ".stx-viewport-fit" in sel
    ]
    uses_clip = any(re.search(r"overflow-x\s*:\s*clip", b) for b in guard)
    # Assert
    assert uses_clip, "the guard must be overflow-x: clip (agreed with scitex-hub)"


def test_the_viewport_fit_guard_is_not_hidden() -> None:
    """``hidden`` would make the container a scroll box and clip the panes
    that are meant to scroll vertically (the exact reason mobile.css' pane
    rules avoid it)."""
    # Arrange
    block = _mobile_block()
    # Act
    guard = [
        body
        for sel, body in _RULE.findall(block)
        if ".stx-viewport-fit" in sel
    ]
    uses_hidden = any(re.search(r"overflow-x\s*:\s*hidden", b) for b in guard)
    # Assert
    assert not uses_hidden, (
        "the guard must NOT be overflow-x: hidden — that turns the shell root "
        "into a scroll container and clips the panes that are meant to scroll "
        "vertically (the pane rules above this rule deliberately avoid it)"
    )


def test_min_width_zero_is_not_the_guard() -> None:
    """The hub measured min-width:0 ALONE as a WORSE bug: it shrinks the
    header-left box while its content paints over the visitor badge. The guard
    must not be expressed as a min-width:0 on the shell root."""
    # Arrange
    block = _mobile_block()
    # Act
    offenders = [
        sel.strip()
        for sel, body in _RULE.findall(block)
        if ".stx-viewport-fit" in sel and re.search(r"min-width\s*:\s*0", body)
    ]
    # Assert
    assert not offenders, (
        f"{offenders} carries min-width:0 as if it were the overflow fix — "
        "the hub measured that as a worse bug (content paints over the "
        "visitor badge, invisible to getBoundingClientRect). clip is the "
        "containment; min-width:0 is not."
    )


# --- the shared tokens -----------------------------------------------------

#: (token name, the value it must carry, where it must live). The breakpoint
#: token lives in theme.css; mobile.css' @media selector keeps the 768px
#: literal (a var() cannot appear in a media query), so the token is the
#: documented single value and the two are pinned in sync below.
_TOKENS = (
    ("--stx-narrow-breakpoint", "768px"),
    ("--stx-touch-target-min", "44px"),
    ("--stx-safe-inset-top", "env(safe-area-inset-top"),
    ("--stx-safe-inset-right", "env(safe-area-inset-right"),
    ("--stx-safe-inset-bottom", "env(safe-area-inset-bottom"),
    ("--stx-safe-inset-left", "env(safe-area-inset-left"),
)


@pytest.mark.parametrize(
    "token,expected",
    _TOKENS,
    ids=lambda v: str(v),
)
def test_the_shared_token_is_defined_once(token: str, expected: str) -> None:
    # Arrange
    text = _COMMENT.sub("", _THEME.read_text(errors="replace"))
    # Act
    declared = re.findall(re.escape(token) + r"\s*:\s*([^;]+)", text)
    carries = bool(declared) and any(expected in v for v in declared)
    # Assert
    assert carries, (
        f"{token} in {_THEME.name} must be declared with a value containing "
        f"{expected!r}; got {declared}"
    )


@pytest.mark.parametrize(
    "token",
    (
        "--stx-safe-inset-top",
        "--stx-safe-inset-right",
        "--stx-safe-inset-bottom",
        "--stx-safe-inset-left",
    ),
    ids=lambda v: str(v),
)
def test_the_safe_area_token_carry_a_zero_fallback(token: str) -> None:
    """env(safe-area-inset-*) is unavailable in non-standalone browser
    contexts; the `, 0px` fallback keeps the tokens safe (0px) there. A token
    that resolves to `initial` (no fallback) would make padding that
    references it a hard parse error in those contexts."""
    # Arrange
    theme = _COMMENT.sub("", _THEME.read_text(errors="replace"))
    # Act
    has_fallback = bool(
        re.search(re.escape(token) + r"\s*:\s*env\([^)]*,\s*0px\)", theme)
    )
    # Assert
    assert has_fallback, f"{token} lacks the `, 0px` fallback in env()"


def test_mobile_css_and_the_breakpoint_token_agree() -> None:
    """The @media selector cannot use a var(), so mobile.css keeps the 768px
    literal. This pins that the literal and the token do not drift apart —
    the two halves of 'one breakpoint value'."""
    # Arrange
    mobile = _COMMENT.sub("", _MOBILE.read_text(errors="replace"))
    theme = _COMMENT.sub("", _THEME.read_text(errors="replace"))
    media_768 = bool(re.search(r"@media[^{]*max-width:\s*768px", mobile))
    token_768 = bool(re.search(r"--stx-narrow-breakpoint\s*:\s*768px", theme))
    # Act
    agree = media_768 and token_768
    # Assert
    assert agree, (
        f"mobile.css @media uses 768px={media_768} but "
        f"--stx-narrow-breakpoint is 768px={token_768}; the breakpoint "
        "token and the media query have drifted — they must name the same "
        "value (the token is the documented single source)"
    )


# --- the two shared utilities ---------------------------------------------


def test_the_touch_min_utility_is_defined() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    defined = bool(
        re.search(r"\.stx-touch-min\b[^{]*\{", block)
    )
    # Assert
    assert defined, ".stx-touch-min is missing from the <=768px block"


def test_the_touch_min_utility_references_the_shared_token() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    util = [
        body
        for sel, body in _RULE.findall(block)
        if re.search(r"\.stx-touch-min\b", sel)
    ]
    references = any(
        re.search(r"min-height\s*:\s*var\(--stx-touch-target-min", b)
        and re.search(r"min-width\s*:\s*var\(--stx-touch-target-min", b)
        for b in util
    )
    # Assert
    assert references, (
        ".stx-touch-min must reference the shared --stx-touch-target-min "
        "token for both min-width and min-height"
    )


def test_the_focus_ring_utility_is_defined() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    defined = bool(
        re.search(r"\.stx-focus-ring\b[^{]*\{", block)
    )
    # Assert
    assert defined, ".stx-focus-ring is missing from the <=768px block"


def test_the_focus_ring_uses_focus_visible() -> None:
    # Arrange
    block = _mobile_block()
    # Act
    rules = [
        (sel, body)
        for sel, body in _RULE.findall(block)
        if ".stx-focus-ring" in sel
    ]
    uses_focus_visible = any(
        ":focus-visible" in sel and re.search(r"outline\s*:\s*\d+px\s+solid", body)
        for sel, body in rules
    )
    # Assert
    assert uses_focus_visible, (
        "the focus ring must use :focus-visible + a solid outline"
    )


def test_the_focus_ring_suppresses_pointer_taps() -> None:
    """The pointer-tap case must be suppressed, or a touch device shows a
    focus outline on every tap."""
    # Arrange
    block = _mobile_block()
    # Act
    rules = [
        (sel, body)
        for sel, body in _RULE.findall(block)
        if ".stx-focus-ring" in sel
    ]
    suppresses = any(
        ":focus:not(:focus-visible)" in sel and "outline" in body
        for sel, body in rules
    )
    # Assert
    assert suppresses, (
        "the pointer-tap case must be suppressed "
        "(:focus:not(:focus-visible)) or a touch device shows a focus "
        "outline on every tap"
    )


# --- detector controls -----------------------------------------------------


def test_the_rule_scanner_sees_the_guard_shape() -> None:
    # Arrange — a literal sample with the exact shape the shipped rule has
    # Act
    rules = _RULE.findall("  .stx-viewport-fit {\n    overflow-x: clip;\n  }\n")
    # Assert
    assert any(".stx-viewport-fit" in sel for sel, _ in rules)


def test_the_rule_scanner_rejects_a_comment_mention() -> None:
    # Arrange — prose naming the class, not a rule
    # Act
    rules = _RULE.findall("/* .stx-viewport-fit is defined below */")
    # Assert
    assert not any(".stx-viewport-fit" in sel for sel, _ in rules)


def test_the_clip_detector_ignores_hidden() -> None:
    # Arrange
    sample = "  .x { overflow-x: hidden; }  "
    # Act
    matched = re.search(r"overflow-x\s*:\s*clip", sample)
    # Assert
    assert matched is None


# EOF
