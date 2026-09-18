#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tour player — the static half of its contract.

Card ``ui-shared-brand-dock-tour-primitives-20260917`` (slice 3, second half),
SSOT: scitex-hub PR 923 §8:

    "Stable IDs/data attributes, not translated labels, locate controls."
    "The player can switch audio/subtitle language without losing position."
    "Produce desktop first, then 390 px where the app supports the flow."

WHAT IS ASSERTED HERE, AND WHY EACH ONE. Behaviour (position preservation, chapter
seeking, the language choices staying independent) is covered by the vitest suite
(tests/scitex_ui/vitest/tour-player.test.ts) — jsdom can hold a media element's
position, so that is where it belongs. This file holds the parts that only exist
in the shipped assets:

  - the hooks the recording pipeline targets. A pipeline that drives the real
    browser by label breaks the moment the label is translated, and translation is
    the point of this slice, so the hooks are asserted to exist and to be stable;
  - the touch targets (§4's 44px rule, and the tour is a phone-length video);
  - the asset trio (CSS + TS + the esbuild bundle a browser can actually run);
  - `prefers-reduced-motion`, because a control row that animates is motion.

SHAPE: one assertion per test, AAA markers in order (PA-307).
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_STATIC = _ROOT / "src" / "scitex_ui" / "static" / "scitex_ui"
_CSS = _STATIC / "css" / "app" / "tour-player.css"
_BUNDLE = _STATIC / "js" / "app" / "tour-player.js"
_COMPONENT = _STATIC / "ts" / "app" / "tour-player" / "_TourPlayer.ts"

#: The hook vocabulary the recording pipeline drives, and the reason it is data
#: rather than prose: hub PR 923 §8 makes the SAME action timeline drive EN and JA
#: recordings, so a locator that contains a label cannot survive the second locale.
_ACTS = ("play-pause", "prev-chapter", "next-chapter", "audio-language", "caption-language")


def _css() -> str:
    return _CSS.read_text(errors="replace")


def test_the_three_asset_halves_ship() -> None:
    """CSS + TS + a bundle a bundler-less adopter can actually execute."""
    # Arrange
    parts = [_CSS, _COMPONENT, _BUNDLE]
    # Act
    present = [part.is_file() for part in parts]
    # Assert
    assert all(present), f"tour-player needs css, ts and its esbuild bundle; present={present}"


def test_the_bundle_names_its_canonical_entry_point() -> None:
    """The bundler-less path is js/app/tour-player.js, generated from auto-mount."""
    # Arrange
    bundle = _BUNDLE.read_text(errors="replace") if _BUNDLE.is_file() else ""
    # Act
    generated = "AUTO-GENERATED from ts/app/tour-player/auto-mount.ts" in bundle
    # Assert
    assert generated, "js/app/tour-player.js must be the generated bundle, not a hand-written copy"


def test_every_control_carries_a_data_hook() -> None:
    """Labels are translated; the hooks the pipeline targets are not."""
    # Arrange
    src = _COMPONENT.read_text(errors="replace") if _COMPONENT.is_file() else ""
    # Act
    missing = [act for act in _ACTS if f'"{act}"' not in src]
    # Assert
    assert missing == [], f"the player must publish every hook the pipeline drives; missing {missing}"


def test_the_controls_are_44px_touch_targets() -> None:
    """A tour is watched on a phone; the control row is the thing thumbs hit."""
    # Arrange
    css = _css()
    # Act
    match = re.search(r"\.stx-tour-player__control\s*\{([^}]*)\}", css)
    body = match.group(1) if match else ""
    # Assert
    assert "min-width: 44px" in body and "min-height: 44px" in body, (
        "each player control must be at least 44px on both axes"
    )


def test_the_control_row_does_not_overflow_a_390px_phone() -> None:
    """§8 asks for the 390 px pass; the row wraps rather than pushing the page."""
    # Arrange
    css = _css()
    # Act
    match = re.search(r"\.stx-tour-player__controls\s*\{([^}]*)\}", css)
    body = match.group(1) if match else ""
    # Assert
    assert "flex-wrap: wrap" in body, "the control row must wrap instead of overflowing a phone"


def test_the_player_honours_reduced_motion() -> None:
    """A fade is motion, and this primitive is the one place a video already moves."""
    # Arrange
    css = _css()
    # Act
    media = re.search(r"@media\s*\(prefers-reduced-motion\s*:\s*reduce\)", css)
    # Assert
    assert media is not None, "the player must state its reduced-motion behaviour"


def test_the_player_is_a_registered_component() -> None:
    """`css/app/*.css` must be discoverable through list_components()."""
    # Arrange
    import scitex_ui

    # Act
    registered = [name for name in scitex_ui.list_components() if "tour-player" in name]
    # Assert
    assert registered != [], "an unregistered stylesheet answers 'no' to an author searching for it"
