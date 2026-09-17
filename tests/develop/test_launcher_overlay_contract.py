#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Launcher overlay contract — the floating dock must overlay, never reserve.

Card: ``ui-shared-brand-dock-tour-primitives-20260917`` (parent
``hub-private-beta-login-to-wow-journey-20260917``), SSOT: scitex-hub PR 923,
``docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md`` §4 "Shared shell and launcher".

    The floating launcher overlays content; it does not reserve a full-width
    bottom strip. Apps use the full available viewport.

WHAT THIS GUARD IS FOR. The shipped hub dock solves the collision between a
bottom-fixed dock and page content by RESERVING A BAND: ``body:has(> .site-dock)
{ padding-bottom: var(--site-dock-clearance) }`` (hub
``static/shared/css/components/site-dock.css``). That reservation is what makes
the strip permanent — the dock is translucent, floats over the page, and the
page is nonetheless permanently shorter by its height. §4 forbids the
reservation and moves the collision to the one moment it matters: while an
actionable control has FOCUS.

So the SDK primitive must ship two halves, and both are assertable:

  CSS  ``css/shell/launcher-overlay.css`` — fixed, OUT OF FLOW, translucent at
       rest, opaque on interaction, no page-level band, safe-area aware,
       reduced-motion aware, 44px targets.
  TS   ``ts/shell/launcher-overlay/`` — the collision runtime, so a focused
       actionable control is never left behind the overlay.

STATIC ON PURPOSE. This is the half that runs in CI on every change. The
geometry claim itself ("zero intersection between a focused control and the
overlay") is a BROWSER measurement and belongs to the evidence on the card, not
here — a green here means "the primitive does not reserve a band and carries the
interaction states", not "no control is ever covered".

SHAPE: every detector below carries a POSITIVE and a NEGATIVE control, per
test_detectors_carry_controls.py — a guard whose pattern stops matching turns
every assertion vacuously true, and one that over-matches inverts the finding.
"""

from __future__ import annotations

import pathlib
import re

_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "css"
)
_TS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "ts"
)

_OVERLAY_CSS = _CSS / "shell" / "launcher-overlay.css"
_PANES_CSS = _CSS / "app" / "panes.css"
#: Shell runtime modules are single files built to an IIFE bundle (ADR 0002),
#: unlike ts/app/ components which are directories with an ESM bundle. The
#: bundle is what a browser runs: a .ts file is installed but not consumable.
_OVERLAY_TS = _TS / "shell" / "launcher-overlay.ts"
_OVERLAY_JS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "js"
    / "shell"
    / "launcher-overlay.js"
)

_COMMENT = re.compile(r"/\*.*?\*/", re.S)

#: A rule that RESERVES a band at the bottom of the page for the overlay.
#: §4: "Do not solve collisions with a permanent full-width spacer." The
#: selector must address the page itself — a `padding-bottom` on the overlay is
#: its own layout, not the page's.
_BAND_ON_PAGE = re.compile(
    r"([^{}]*(?:\bbody\b|\bhtml\b|:root)[^{}]*)\{([^{}]*?(?:padding|margin)-bottom\s*:[^{}]*)\}",
    re.S,
)

#: The hub's reservation, from the SDK side: a height calculation that subtracts
#: a dock band from the viewport. Whatever the token is called, subtracting it is
#: the reservation the SSOT removes.
_DOCK_HEIGHT_SUBTRACTION = re.compile(r"-\s*var\(\s*--[\w-]*(?:dock|launcher)[\w-]*height")

#: The full-viewport claim: a dynamic viewport height with a static fallback for
#: browsers that predate `dvh` (200% zoom and mobile URL-bar collapse both ride
#: on this rather than on a reserved band).
_DVH = re.compile(r"\b100dvh\b")
_VH_FALLBACK = re.compile(r"\b100vh\b")

#: Notch / gesture-bar awareness on the bottom edge, where the overlay lives.
_SAFE_BOTTOM = re.compile(r"env\(\s*safe-area-inset-bottom")

#: Motion must be optional (§4 lists `prefers-reduced-motion`).
_REDUCED_MOTION = re.compile(r"@media\s*\(prefers-reduced-motion\s*:\s*reduce\)")

#: The interaction states that must make the overlay opaque (§4).
_OPAQUE_STATES = (
    ":hover",
    ":focus-within",
    ":active",
    "[aria-expanded=\"true\"]",
    "[data-stx-launcher-open]",
    "[data-stx-launcher-pressed]",
)


def _strip(text: str) -> str:
    """The stylesheet with comments removed, so prose cannot satisfy a rule."""
    return _COMMENT.sub("", text)


def _read(path: pathlib.Path) -> str:
    """The file's text with comments removed."""
    return _strip(path.read_text(encoding="utf-8"))


def _overlay_css() -> str:
    """The overlay stylesheet, or a readable failure if it is not there.

    Reading a missing file as "" would make every content assertion below pass
    vacuously — the exact blindness the control pairs exist to prevent. The
    file's absence is a finding, so it is raised as one.
    """
    assert _OVERLAY_CSS.is_file(), f"missing primitive stylesheet: {_OVERLAY_CSS}"
    return _read(_OVERLAY_CSS)


def test_the_primitive_exists() -> None:
    """The SDK cannot ship the overlay behaviour without the files."""
    # Arrange / Act
    present = [_OVERLAY_CSS.is_file(), _OVERLAY_TS.is_file(), _OVERLAY_JS.is_file()]
    # Assert
    assert all(present), (
        "css/shell/launcher-overlay.css, ts/shell/launcher-overlay.ts and its "
        "esbuild bundle js/shell/launcher-overlay.js are the three halves of this "
        f"primitive; present={present}"
    )


def test_the_overlay_does_not_reserve_a_band_on_the_page() -> None:
    """§4: apps use the full viewport; the collision is handled at focus time."""
    # Arrange
    css = _overlay_css()
    # Act
    reserved = _BAND_ON_PAGE.findall(css)
    # Assert
    assert reserved == [], (
        "the launcher overlay must not reserve a page-level bottom band; found "
        f"{[sel.strip() for sel, _ in reserved]}"
    )


def test_the_panes_primitive_no_longer_reserves_a_dock_band() -> None:
    """The SDK's own height calculation must not subtract a floating overlay."""
    # Arrange
    css = _read(_PANES_CSS)
    # Act
    subtracted = _DOCK_HEIGHT_SUBTRACTION.findall(css)
    # Assert
    assert subtracted == [], (
        "panes.css must size to the viewport, not to (viewport - dock height): a "
        f"floating overlay owns no band; found {subtracted}"
    )


def test_the_overlay_states_every_interaction_that_must_make_it_opaque() -> None:
    """§4: opaque on hover, focus-within, touch/press, expansion, or open menu."""
    # Arrange
    css = _overlay_css()
    # Act
    missing = [state for state in _OPAQUE_STATES if state not in css]
    # Assert
    assert missing == [], (
        "every interaction state in §4 must be stated in the stylesheet, or the "
        f"overlay stays translucent exactly when a user is aiming at it; missing {missing}"
    )


def test_the_full_viewport_claim_carries_a_static_fallback() -> None:
    """`dvh` for the modern path, `vh` for the browsers that predate it."""
    # Arrange
    css = _overlay_css()
    # Act
    dynamic, static = _DVH.search(css), _VH_FALLBACK.search(css)
    # Assert
    assert dynamic is not None and static is not None, (
        "the full-viewport rule needs `100dvh` with a `100vh` fallback; "
        f"dvh={dynamic is not None} vh={static is not None}"
    )


def test_the_overlay_respects_the_bottom_safe_area() -> None:
    """The overlay sits on the bottom edge, where the gesture bar and notch are."""
    # Arrange
    css = _overlay_css()
    # Act
    safe = _SAFE_BOTTOM.search(css)
    # Assert
    assert safe is not None, (
        "the overlay must offset by env(safe-area-inset-bottom) (or the shared "
        "--stx-safe-inset-bottom token that wraps it)"
    )


def test_the_overlay_honours_reduced_motion() -> None:
    """§4 lists prefers-reduced-motion; a fade is motion."""
    # Arrange
    css = _overlay_css()
    # Act
    media = _REDUCED_MOTION.search(css)
    # Assert
    assert media is not None, "the overlay must disable its transition under prefers-reduced-motion"


# ---------------------------------------------------------------------------
# Controls — one pair per detector. Each demonstrates the pattern can fire (so a
# green above is not a blind instrument) and can decline (so it is not inverted).
# ---------------------------------------------------------------------------


def test_the_stripper_removes_a_comment_and_keeps_the_rule() -> None:
    """Positive: the comment is GONE. Negative: the code beside it survived."""
    # Arrange
    sample = "/* padding-bottom: 88px; */ .a { color: red; }"
    # Act
    stripped = _COMMENT.sub("", sample)
    # Assert
    assert "padding-bottom" not in stripped
    assert "color: red" in stripped


def test_the_rule_detector_matches_a_page_level_band() -> None:
    # Arrange
    sample = "body:has(> .stx-launcher-overlay) { padding-bottom: 88px; }"
    # Act
    found = _BAND_ON_PAGE.search(sample)
    # Assert
    assert found is not None


def test_the_rule_detector_declines_a_band_on_the_overlay_itself() -> None:
    # Arrange
    sample = ".stx-launcher-overlay { padding-bottom: 6px; margin-bottom: 0; }"
    # Act
    found = _BAND_ON_PAGE.search(sample)
    # Assert
    assert found is None


def test_the_margin_form_of_the_reservation_is_also_caught() -> None:
    # Arrange
    sample = ":root { margin-bottom: var(--stx-launcher-clearance); }"
    # Act
    found = _BAND_ON_PAGE.search(sample)
    # Assert
    assert found is not None


def test_the_band_detector_declines_a_mention_in_a_comment() -> None:
    # Arrange
    sample = "/* body { padding-bottom: 88px } is the reservation this forbids */"
    # Act
    found = _BAND_ON_PAGE.search(_COMMENT.sub("", sample))
    # Assert
    assert found is None


def test_the_dock_subtraction_detector_matches_the_hub_token() -> None:
    # Arrange
    sample = "height: calc(100dvh - var(--site-dock-height, 0px));"
    # Act
    found = _DOCK_HEIGHT_SUBTRACTION.search(sample)
    # Assert
    assert found is not None


def test_the_dock_subtraction_detector_declines_a_header_subtraction() -> None:
    # Arrange
    sample = "height: calc(100dvh - var(--site-header-height, 44px));"
    # Act
    found = _DOCK_HEIGHT_SUBTRACTION.search(sample)
    # Assert
    assert found is None


def test_the_viewport_detector_matches_the_dynamic_unit() -> None:
    # Arrange
    sample = ".stx-viewport-full { min-height: 100dvh; }"
    # Act
    found = _DVH.search(sample)
    # Assert
    assert found is not None


def test_the_viewport_detector_declines_a_static_only_height() -> None:
    # Arrange
    sample = ".stx-viewport-full { min-height: 100vh; }"
    # Act
    found = _DVH.search(sample)
    # Assert
    assert found is None


def test_the_fallback_detector_matches_the_static_unit() -> None:
    # Arrange
    sample = ".stx-viewport-full { min-height: 100vh; }"
    # Act
    found = _VH_FALLBACK.search(sample)
    # Assert
    assert found is not None


def test_the_fallback_detector_declines_the_dynamic_unit() -> None:
    # Arrange
    sample = ".stx-viewport-full { min-height: 100dvh; }"
    # Act
    found = _VH_FALLBACK.search(sample)
    # Assert
    assert found is None


def test_the_safe_area_detector_matches_the_env_form() -> None:
    # Arrange
    sample = "bottom: calc(12px + env(safe-area-inset-bottom, 0px));"
    # Act
    found = _SAFE_BOTTOM.search(sample)
    # Assert
    assert found is not None


def test_the_safe_area_detector_declines_a_bare_mention() -> None:
    # Arrange
    sample = ".stx-launcher-overlay { --note: safe-area-inset-bottom; }"
    # Act
    found = _SAFE_BOTTOM.search(sample)
    # Assert
    assert found is None


def test_the_motion_detector_matches_the_reduce_query() -> None:
    # Arrange
    sample = "@media (prefers-reduced-motion: reduce) { .a { transition: none; } }"
    # Act
    found = _REDUCED_MOTION.search(sample)
    # Assert
    assert found is not None


def test_the_motion_detector_declines_an_unrelated_media_query() -> None:
    # Arrange
    sample = "@media (min-width: 768px) { .a { color: red; } }"
    # Act
    found = _REDUCED_MOTION.search(sample)
    # Assert
    assert found is None
