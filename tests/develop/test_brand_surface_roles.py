#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Every brand surface must ship the foreground that is legible ON it.

Card ``ui-shared-brand-dock-tour-primitives-20260917`` (parent
``hub-private-beta-login-to-wow-journey-20260917``), SSOT: scitex-hub PR 923,
``docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md`` sections 2 and 9:

    "Use the same navy/gold auth shell for sign-in, signup, OTP, and payment."
    SDK owns "Navy/gold semantic tokens, app/auth/settings shell primitives".

THE DEFECT, MEASURED 2026-09-17 in chromium against the shipped theme.css, both
themes, on a rendered page (not inferred from the file):

    pairing                       light            dark
    --stx-gold  on --stx-brand    5.21:1           1.00:1
    --stx-navy-900 on --stx-brand 1.00:1           6.68:1

Both themes are the SAME rule with a different winner. ``--stx-brand`` is the
brand surface and it SWITCHES HUE per theme (light navy, dark gold), while the
scales are declared once and do not. So a consumer pairing ``--stx-brand`` with
either scale is legible in exactly one theme and invisible in the other — same
code path, no error, no warning, and a screenshot-only review of either theme
alone looks fine. The auth shell is where brand surfaces and their foregrounds
meet, so this is the last place it can be left implicit.

WHAT IS SHIPPED HERE, and it is deliberately two roles rather than one: in light
the two brand surfaces differ (navy brand, gold accent), in dark they are the
same value. A single ``--stx-on-brand`` cannot cover both, so:

    --stx-on-brand   legible on --stx-brand   (light: sand on navy, dark: navy on gold)
    --stx-on-gold    legible on --stx-gold    (navy, both themes)

A SECOND FINDING, same class, measured the same way: ``theme.css`` documents
itself as the single source a page may link ALONE, and three tokens it is consumed
as owning resolve to NOTHING there — ``--color-primary``, ``--color-on-primary``,
``--focus-ring-color``. Two earlier fixes in this repo had exactly this shape
(``--accent``, ``--text-link``) and each was resolved by declaring the token in
both layers. Declaring it here as well is the same repair, not a new rule.

AA is 4.5:1 for normal text. These are checked as the CASCADE resolves them —
a token the ``:root`` block declares once still applies in dark, so a naive split
of the file at the dark selector reports it as missing when it is not (that
inference error is why the numbers above came from a browser).
"""

from __future__ import annotations

import pathlib
import re

import pytest

from . import _css_palette as palette

_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "css"
)
_THEME = _CSS / "shell" / "theme.css"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)

#: AA for normal text (WCAG 2.1 SC 1.4.3).
_AA = 4.5

#: (foreground role, surface role, why this pair exists in the product).
_BRAND_PAIRS = (
    ("--stx-on-brand", "--stx-brand", "text/icon on a brand-coloured surface (auth shell, badges)"),
    ("--stx-on-gold", "--stx-gold", "text/icon on the gold accent surface (Recommended badge, tab bar)"),
)

#: Tokens theme.css is consumed as owning: a page that links only shell.css, or
#: only theme.css, must still resolve them. Two earlier fixes in this repo
#: (--accent, --text-link) were exactly this, and were fixed in both layers.
_SELF_SUFFICIENT = ("--color-primary", "--color-on-primary", "--focus-ring-color")


def _blocks() -> tuple[str, str]:
    """(light, dark) halves of theme.css, comments stripped, imports resolved."""
    text = _COMMENT.sub("", _THEME.read_text(encoding="utf-8"))
    light, _, dark = text.partition('[data-theme="dark"]')
    return light, dark


def _resolved(token: str, theme: str) -> str | None:
    """The token's value AS THE CASCADE RESOLVES IT in ``theme``.

    Both selectors are ``:root``/``[data-theme=...]`` at equal specificity, so
    source order decides: a token the dark block declares wins there, and one it
    leaves alone keeps the value the light block gave it. Reading the dark half in
    isolation is the inference this helper exists to prevent.
    """
    light, dark = _blocks()
    declared = palette.declared(dark if theme == "dark" else light, token)
    if declared is None and theme == "dark":
        declared = palette.declared(light, token)
    if declared is None:
        return None
    return palette.resolve(dark if theme == "dark" else light, declared) or palette.resolve(light, declared)


def _ratio(foreground: str | None, background: str | None) -> float:
    """WCAG contrast, refusing to score a pair the cascade never resolved."""
    assert foreground and background, f"unresolved pair: {foreground} on {background}"
    return palette.contrast(foreground, background)


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def test_theme_css_declares_the_tokens_it_is_consumed_as_owning() -> None:
    """A page linking theme.css alone must not render an undefined colour."""
    # Arrange
    light, dark = _blocks()
    # Act
    missing = [t for t in _SELF_SUFFICIENT if palette.declared(light, t) is None]
    # Assert
    assert missing == [], f"theme.css is the documented single source; unresolved there: {missing}"


def test_every_brand_pair_ships_both_roles_in_both_themes() -> None:
    """A pair with no foreground role is the defect: the consumer invents one."""
    # Arrange
    pairs = [(fg, bg) for fg, bg, _ in _BRAND_PAIRS]
    # Act
    undefined = [
        (fg, bg, theme)
        for fg, bg in pairs
        for theme in ("light", "dark")
        if _resolved(fg, theme) is None or _resolved(bg, theme) is None
    ]
    # Assert
    assert undefined == [], f"brand surfaces and their foregrounds must both exist: {undefined}"


@pytest.mark.parametrize("foreground,surface", [(fg, bg) for fg, bg, _ in _BRAND_PAIRS])
def test_on_brand_roles_clear_aa_in_both_themes(foreground: str, surface: str) -> None:
    """The measurement that caught the 1.00:1 pairing, as a test."""
    # Arrange
    ratios = {
        theme: _ratio(_resolved(foreground, theme), _resolved(surface, theme))
        for theme in ("light", "dark")
    }
    # Act
    failing = {t: round(r, 2) for t, r in ratios.items() if r < _AA}
    # Assert
    assert failing == {}, f"{foreground} on {surface} below AA ({_AA}:1): {failing}"


def test_the_brand_surface_and_its_scales_are_different_roles() -> None:
    """Documents WHY two on-roles exist: the surfaces do not switch together.

    Not a style point. In light the brand surface is navy and the gold accent is
    gold; in dark the brand surface IS the gold. A consumer that treats
    ``--stx-brand`` as theme-stable pairs it with the wrong foreground in one
    theme, which is the 1.00:1 measurement above.
    """
    # Arrange
    light_brand, dark_brand = _resolved("--stx-brand", "light"), _resolved("--stx-brand", "dark")
    # Act
    switches = light_brand != dark_brand
    # Assert
    assert switches is True, "if --stx-brand ever stops switching, one of the on-roles is dead weight"


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_the_comments_stripper_removes_a_comment() -> None:
    # Arrange
    sample = "/* --stx-on-brand: #fff; */ .a { color: red; }"
    # Act
    stripped = _COMMENT.sub("", sample)
    # Assert
    assert "--stx-on-brand" not in stripped


def test_the_comments_stripper_keeps_the_declaration() -> None:
    # Arrange
    sample = "/* --stx-on-brand: #fff; */ .a { color: red; }"
    # Act
    stripped = _COMMENT.sub("", sample)
    # Assert
    assert "color: red" in stripped


def test_the_ratio_helper_matches_a_known_pair() -> None:
    # Arrange
    white, black = "#ffffff", "#000000"
    # Act
    ratio = _ratio(white, black)
    # Assert
    assert round(ratio, 1) == 21.0


def test_the_ratio_helper_declines_to_call_a_low_contrast_pair_legible() -> None:
    # Arrange
    gold, gold = "#b8956a", "#b8956a"
    # Act
    ratio = _ratio(gold, gold)
    # Assert
    assert ratio < _AA
