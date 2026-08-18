#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Five tokens our stylesheets read, nothing defined, and every site agreed.

These five are not a family. What groups them is a property that makes them
DECIDABLE without looking at a rendered shell: every call site of each token
spelled the same fallback, so that agreed literal is what renders today,
everywhere, in both palettes. Pinning it on the palette it suits makes that
palette a provable no-op and leaves only the other palette to argue about.

That is the same move as ``--text-link`` (0.14.1) and the Primer five
(0.14.3) — and the reason the REST of the undefined-token card is still open
is that its remaining members fail this test: ``--border-subtle`` (10 sites,
3 different fallbacks), ``--text-dimmed`` (5/2), ``--accent-primary`` (4/2),
``--color-accent-muted`` (4/3), ``--folder-color`` (2/2), ``--font-mono``
(5/5). No value preserves what those render, so defining one is a visual
change that needs eyes rather than arithmetic.

``--accent`` IS THE ONE DELIBERATE VISUAL CHANGE, and it inverts the pattern
every earlier token on that card followed. Its literal ``#6d4cad`` measures
**2.71:1** against the dark ``--bg-surface`` (#161b22), and two of its three
sites in ``app/combobox.css`` are ``color:`` — so the status quo fails WCAG AA
on the DEFAULT theme, not the light one. Pinning dark to the historical value
would have codified a measured accessibility failure in the name of a no-op.
Dark takes ``#a371f7`` (5.16:1), already this palette's purple via
``--color-done-fg``, so the change borrows an existing value rather than
inventing one; LIGHT keeps ``#6d4cad``, where it measures 5.97:1. The literal
was always a light-surface purple being rendered on a dark shell.

The tests below pin, in order of what a future edit is most likely to break:
the no-op equality for the four pinned tokens, the deliberate exception for
``--accent`` (asserted in BOTH directions, so neither reverting it nor
forgetting why it differs passes quietly), and the contrast floor for every
token used as text.
"""

import pathlib
import re

import pytest

import scitex_ui

from . import _css_palette

_CSS = pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui" / "css"
_COLORS = _CSS / "primitives" / "colors.css"

#: --bg-surface as each palette actually resolves it (--_white / --_scitex-01).
_LIGHT_SURFACE = "#f8f7f5"
_DARK_SURFACE = "#161b22"

_AA_NORMAL_TEXT = 4.5

#: The literal every call site of each token already rendered, and the palette
#: that literal belongs on. Four sit on dark (they were written for the dark
#: shell); --accent's sits on LIGHT, which is the whole reason it is special.
_PINNED_DARK = {
    "--danger-color": "#f85149",
    "--workspace-text-muted": "#888888",
    "--border-primary": "#30363d",
    "--bg-hover": "rgba(255, 255, 255, 0.08)",
}

#: --accent, pinned on light instead. Kept apart from the dict above so the
#: asymmetry is visible rather than buried in a data structure.
_ACCENT_HISTORICAL = "#6d4cad"
_ACCENT_DARK_REPLACEMENT = "#a371f7"

#: Tokens used as `color:` somewhere, i.e. the ones a contrast floor applies
#: to. --border-primary is a border and --bg-hover a background wash; neither
#: carries a normal-text contrast claim, and asserting one would be theatre.
_TEXT_TOKENS = ("--danger-color", "--accent", "--workspace-text-muted")


#: Palette reading and contrast arithmetic moved to `_css_palette` — three
#: files carried byte-identical copies of the maths below, and `_palette_blocks`
#: read colors.css as a flat file, which stops being true when it becomes a
#: barrel over per-palette parts. The names are re-bound rather than rewritten
#: at every call site, so not one assertion in this file changed.
_contrast = _css_palette.contrast
_declared = _css_palette.declared
_resolve = _css_palette.resolve


def _palette_blocks() -> tuple[str, str]:
    """The (light, dark) halves of colors.css, `@import`s resolved first."""
    return _css_palette.palette_blocks(_COLORS)


@pytest.mark.parametrize("token", sorted(_PINNED_DARK))
def test_pinned_token_is_defined_in_both_palettes(token):
    """A token defined in one palette only is the defect that opened the card."""
    # Arrange
    light, dark = _palette_blocks()

    # Act
    present = (_declared(light, token), _declared(dark, token))

    # Assert
    assert all(present), f"{token} missing from a palette: {present}"


@pytest.mark.parametrize("token,literal", sorted(_PINNED_DARK.items()))
def test_dark_equals_the_literal_its_call_sites_already_rendered(token, literal):
    """The no-op evidence — this is what let the change ship unscreenshotted."""
    # Arrange
    _, dark = _palette_blocks()

    # Act
    declared = _resolve(dark, _declared(dark, token) or "")

    # Assert
    assert declared.replace(" ", "") == literal.replace(" ", ""), (
        f"{token} dark is {declared!r}, not the historical fallback {literal!r}. "
        "That equality is the ONLY evidence the default theme is unchanged."
    )


def test_accent_light_keeps_the_historical_literal():
    """--accent inverts the pattern: its no-op palette is LIGHT, not dark."""
    # Arrange
    light, _ = _palette_blocks()

    # Act
    declared = _resolve(light, _declared(light, "--accent") or "")

    # Assert
    assert declared == _ACCENT_HISTORICAL, (
        f"--accent light is {declared!r}; the historical literal "
        f"{_ACCENT_HISTORICAL!r} belongs on THIS palette, where it measures "
        "5.97:1. Moving it to dark reintroduces a 2.71:1 failure."
    )


def test_accent_dark_does_not_pin_the_below_aa_literal():
    """The deliberate exception, asserted so a 'tidy-up' cannot undo it.

    Reverting --accent dark to #6d4cad would look like restoring consistency
    with the other four. It would restore a measured AA failure on the theme
    the operator actually uses.
    """
    # Arrange
    _, dark = _palette_blocks()

    # Act
    declared = _resolve(dark, _declared(dark, "--accent") or "")

    # Assert
    assert declared != _ACCENT_HISTORICAL, (
        "--accent dark was pinned back to #6d4cad, which measures 2.71:1 on "
        f"{_DARK_SURFACE} — below AA — at two `color:` sites in combobox.css."
    )


@pytest.mark.parametrize("token", _TEXT_TOKENS)
def test_text_tokens_clear_aa_in_both_palettes(token):
    """Contrast is arithmetic, so it can be a test rather than a review note."""
    # Arrange
    light, dark = _palette_blocks()
    pairs = (
        (_resolve(light, _declared(light, token) or ""), _LIGHT_SURFACE),
        (_resolve(dark, _declared(dark, token) or ""), _DARK_SURFACE),
    )

    # Act
    ratios = [(v, s, _contrast(v, s)) for v, s in pairs if v.startswith("#")]

    # Assert
    assert all(r >= _AA_NORMAL_TEXT for _, _, r in ratios), (
        f"{token} below AA: "
        + ", ".join(f"{v} on {s} = {r:.2f}:1" for v, s, r in ratios)
    )


def test_contrast_helper_reports_the_known_bad_pairing_as_failing():
    """Positive control: the arithmetic above must be able to say "fail".

    Without this, every contrast assertion could pass because the helper
    returns something large for everything.
    """
    # Arrange
    known_bad = (_ACCENT_HISTORICAL, _DARK_SURFACE)

    # Act
    ratio = _contrast(*known_bad)

    # Assert
    assert ratio < _AA_NORMAL_TEXT, (
        f"{_ACCENT_HISTORICAL} on {_DARK_SURFACE} measured {ratio:.2f}:1; it is "
        "2.71:1 and is the reason --accent's dark value differs. If this "
        "passes, the contrast helper cannot fail and the tests above are void."
    )


@pytest.mark.parametrize("token", sorted(_PINNED_DARK) + ["--accent"])
def test_palettes_do_not_collapse_onto_one_value(token):
    """A unify-the-duplicates edit silently restores the failures above."""
    # Arrange
    light, dark = _palette_blocks()

    # Act
    values = (
        _resolve(light, _declared(light, token) or ""),
        _resolve(dark, _declared(dark, token) or ""),
    )

    # Assert
    assert values[0] != values[1], (
        f"{token} now renders {values[0]!r} in both palettes. These tokens are "
        "two-valued on purpose; one value cannot suit both surfaces."
    )
