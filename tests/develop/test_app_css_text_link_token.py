#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""`--text-link` must be DEFINED, in both palettes, and legible in each.

Five app stylesheets consume it as ``var(--text-link, #58a6ff)`` and until
0.15.0 no shipped stylesheet defined it, so every site rendered that one
fallback in BOTH palettes. Measured, that fallback is 2.36:1 against the light
palette's ``--bg-surface`` (#f8f7f5) — WCAG AA for normal text is 4.5:1 — so
light mode was failing by construction and no theme could fix it. The token
existing is what makes it fixable at all.

Two properties are pinned here, and the second is the one a future edit is most
likely to break:

1. The DARK value equals the historical fallback, so the default theme is
   visually unchanged by the token's introduction. That no-op is load-bearing:
   it is what let this ship without a screenshot of the dark surface.
2. Both palette values clear AA against the surface they sit on. Contrast is
   arithmetic, so it can be a test rather than a review comment — and a
   "tidy-up" that unifies the two palettes onto one hex would silently
   reintroduce the 2.36:1 failure. Here it fails instead.
"""

import pathlib
import re

import pytest

import scitex_ui

_CSS = pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui" / "css"

#: Every stylesheet carrying a copy of the palette. Both must define the token:
#: a page linking only shell/theme.css never sees primitives/colors.css, and
#: defining it in one place only is the exact defect that made the context menu
#: render dark-grey-on-dark (0.12.1).
_PALETTE_FILES = ("primitives/colors.css", "shell/theme.css")

#: The value the five call sites already rendered before the token existed.
_HISTORICAL_FALLBACK = "#58a6ff"

#: --bg-surface per palette, i.e. what a link actually sits on.
_LIGHT_SURFACE = "#f8f7f5"
_DARK_SURFACE = "#161b22"

_AA_NORMAL_TEXT = 4.5


def _channel(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(foreground: str, background: str) -> float:
    a, b = _luminance(foreground), _luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def _declarations(relative_path: str) -> list[str]:
    """Every ``--text-link`` value declared in one stylesheet, in file order.

    Reads the DECLARATION (``--text-link:``), never a ``var(--text-link)``
    consumption, so a file that merely uses the token cannot satisfy a test
    that asks whether it defines it.
    """
    text = (_CSS / relative_path).read_text(encoding="utf-8")
    return [m.strip() for m in re.findall(r"--text-link\s*:\s*([^;]+);", text)]


# ─────────────────────────── the token exists at all ────────────────────────


@pytest.mark.parametrize("path", _PALETTE_FILES)
def test_every_palette_file_defines_text_link(path: str) -> None:
    # Arrange
    declared = _declarations(path)
    # Act
    count = len(declared)
    # Assert
    assert count >= 2, (
        f"{path} declares --text-link {count} time(s); each palette file must "
        "define it for BOTH light and dark, or one theme falls back"
    )


def test_no_app_stylesheet_is_left_relying_on_the_bare_token() -> None:
    # Arrange — a consumption with NO fallback would render nothing if the
    # token were ever removed again; the fallbacks are the safety net and
    # should stay until the token is proven present everywhere.
    stylesheets = sorted(_CSS.rglob("*.css"))
    # Act
    bare = []
    for css in stylesheets:
        for lineno, line in enumerate(css.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"var\(\s*--text-link\s*\)", line):
                bare.append(f"{css.relative_to(_CSS)}:{lineno}")
    # Assert
    assert bare == [], f"var(--text-link) with no fallback at {bare}"


# ──────────────────── the dark no-op, which is load-bearing ─────────────────


def test_dark_value_is_the_historical_fallback() -> None:
    # Arrange — introducing the token must not change the DEFAULT theme, and
    # this equality is the whole evidence for that claim.
    declared = _declarations("primitives/colors.css")
    # Act
    dark = declared[-1]
    # Assert
    assert dark.lower() == _HISTORICAL_FALLBACK, (
        f"dark --text-link is {dark!r}, not the fallback {_HISTORICAL_FALLBACK!r} "
        "the five call sites already rendered — that makes this a visual change "
        "to the default theme, which needs eyes rather than a test"
    )


def test_the_two_palettes_do_not_share_one_value() -> None:
    # Arrange — the "tidy-up" that breaks this. One hex cannot clear AA on both
    # surfaces (measured: #58a6ff is 6.85 on dark and 2.36 on light), so
    # collapsing them necessarily fails one palette.
    declared = _declarations("primitives/colors.css")
    # Act
    distinct = len(set(v.lower() for v in declared))
    # Assert
    assert distinct >= 2, (
        "light and dark --text-link are the same value; no single hex clears "
        "AA on both #f8f7f5 and #161b22"
    )


# ─────────────────────────── legibility, as arithmetic ──────────────────────


def test_light_value_clears_aa_on_the_light_surface() -> None:
    # Arrange — the defect being fixed: 2.36:1 before this token existed.
    light = _declarations("primitives/colors.css")[0]
    # Act
    ratio = _contrast(light, _LIGHT_SURFACE)
    # Assert
    assert ratio >= _AA_NORMAL_TEXT, (
        f"light --text-link {light} is {ratio:.2f}:1 on {_LIGHT_SURFACE}, "
        f"below AA {_AA_NORMAL_TEXT}:1"
    )


def test_dark_value_clears_aa_on_the_dark_surface() -> None:
    # Arrange — pairs with the above so neither palette can be improved by
    # breaking the other.
    dark = _declarations("primitives/colors.css")[-1]
    # Act
    ratio = _contrast(dark, _DARK_SURFACE)
    # Assert
    assert ratio >= _AA_NORMAL_TEXT, (
        f"dark --text-link {dark} is {ratio:.2f}:1 on {_DARK_SURFACE}, "
        f"below AA {_AA_NORMAL_TEXT}:1"
    )


def test_the_contrast_helper_can_actually_fail() -> None:
    # Arrange — a positive control for the arithmetic itself. Three checks
    # today passed while measuring nothing; a contrast helper that returned a
    # large number unconditionally would make every assertion above vacuous.
    # Act
    ratio = _contrast(_HISTORICAL_FALLBACK, _LIGHT_SURFACE)
    # Assert
    assert ratio < _AA_NORMAL_TEXT, (
        "the known-bad pairing (#58a6ff on the light surface) must measure "
        f"BELOW AA; got {ratio:.2f}:1, so the helper is not discriminating"
    )
