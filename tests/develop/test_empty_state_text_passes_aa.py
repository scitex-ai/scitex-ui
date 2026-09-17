#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The EmptyState's text must pass WCAG 2.1 AA, and must not STACK opacity on it.

FOUND BY scitex-ui-gui, 2026-09-17, rendered in chromium (playwright headless)
with axe-core 4.10.2 against scitex-ui develop @ 5169aaa — not inferred here.
Their measurement, both themes, 1440x900 and 390x844:

    .stx-app-empty__title              14px/500  #777777 on #f8f7f5  4.18 FAIL
    .stx-app-empty__hint               12px, opacity:.6  -> 2.16     FAIL
    .stx-app-empty--compact > __title  12px, opacity:.85 -> 3.22     FAIL
    dark theme: hint 2.87, compact title 4.43                        FAIL

TWO LAYERS, and this file guards the one that is this component's:
  1. the LIGHT `--text-muted` (#777777) is below AA on every shipped light
     surface (4.26 / 4.18 / 4.00). That is a PALETTE decision tracked on
     scitex-ui-text-muted-fails-aa-against-any-light-surface-20260906 — 131
     consumed sites, so it is not this file's call.
  2. `css/app/empty.css` STACKED `opacity` on top of that failing token, which
     MULTIPLIES the ratio (0.6 turned 4.18 into 3.22). Even a token that passes
     cannot survive that, so this half is the component's own defect: the hint
     is quieter by SIZE, never by a second alpha.

WHAT THIS FILE COMPUTES, per the lesson on my own palette card ("compute the
post-fix number, not just the pre-fix one"): the shipped colour of the
empty-state text is resolved through the palette indirection and its contrast is
recomputed against every shipped surface, in BOTH themes. A later palette change
that drops the text token below AA fails HERE, in the component that depends on
it, rather than shipping behind a green diff.

ONE ASSERTION PER TEST, THREE MARKER LINES (PA-307 §3); every detector carries a
positive and a negative control over LITERAL samples.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests._checkout import css_dir

from . import _css_palette

_CSS = css_dir() / "app" / "empty.css"
_COLORS = css_dir() / "primitives" / "colors.css"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)

#: Every background an empty state is rendered on, in both palettes.
_SURFACES = ("--bg-page", "--bg-surface", "--bg-muted")

#: WCAG 2.1 SC 1.4.3, normal text. The sizes here are 12-14px, all normal.
_AA_BODY = 4.5

#: Rules whose opacity is a deliberate DECORATIVE treatment, not text. The icon
#: glyph accompanies the title and names nothing on its own (SC 1.4.11 does not
#: apply to it), so it is exempt BY SELECTOR and the exemption is asserted below
#: rather than assumed.
_DECORATIVE = ("__icon",)


def _blocks() -> tuple[str, str]:
    return _css_palette.palette_blocks(_COLORS)


def _css() -> str:
    return _COMMENT.sub("", _CSS.read_text(errors="replace"))


def _rule_block(selector: str) -> str:
    """The body of the rule whose LAST selector in the group is `selector`.

    Exact selector equality, not a substring: `.stx-app-empty` must not match
    `.stx-app-empty__hint`, which is how a guard ends up measuring a rule it did
    not name.
    """
    for match in _RULE.finditer(_css()):
        parts = [part.strip() for part in match.group(1).split(",")]
        if parts and parts[-1] == selector:
            return match.group(2)
    return ""


def _resolved(block: str, token: str) -> str:
    """What `token` renders as in this palette, through the alias chain."""
    value = _css_palette.declared(block, token)
    return _css_palette.resolve(block, value) if value is not None else ""


def _text_colour_token() -> str:
    """The token the empty-state TEXT consumes (the base rule's `color`)."""
    match = re.search(r"color:\s*var\(\s*(--[\w-]+)", _rule_block(".stx-app-empty"))
    return match.group(1) if match else ""


def _worst_ratio(block: str) -> float:
    """The lowest contrast the text colour achieves on this palette's surfaces."""
    colour = _resolved(block, _text_colour_token())
    return min(_css_palette.contrast(colour, _resolved(block, surface)) for surface in _SURFACES)


def _rules_carrying_opacity() -> list[str]:
    """Selectors of NON-decorative rules that set `opacity`."""
    offenders: list[str] = []
    for match in _RULE.finditer(_css()):
        selector = match.group(1).strip()
        if any(exempt in selector for exempt in _DECORATIVE):
            continue
        if re.search(r"(?m)^\s*opacity\s*:", match.group(2)):
            offenders.append(selector)
    return offenders


# ── Extractor controls ────────────────────────────────────────────────────


def test_the_comment_stripper_matches_a_real_comment() -> None:
    """POSITIVE: _COMMENT matches a real block comment."""
    # Arrange
    sample = "/* a real comment */ .a { color: red; }"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is not None


def test_the_comment_stripper_ignores_a_mere_mention() -> None:
    """NEGATIVE: prose about comments is not a comment to strip."""
    # Arrange
    sample = "// line comment, not a block comment"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is None


def test_the_rule_extractor_matches_a_literal_rule() -> None:
    """POSITIVE: _RULE finds a real rule and both of its halves."""
    # Arrange
    sample = ".a { color: red; }"
    # Act
    match = _RULE.search(sample)
    # Assert
    assert match is not None and match.group(2).strip() == "color: red;"


def test_the_rule_extractor_ignores_a_bare_selector_mention() -> None:
    """NEGATIVE: a selector named without a block is not a rule."""
    # Arrange
    sample = ".stx-app-empty__hint -- selector mention, no braces"
    # Act
    match = _RULE.search(sample)
    # Assert
    assert match is None


def test_the_palette_reader_is_not_vacuous() -> None:
    """POSITIVE: the shared reader finds the text token in BOTH palettes."""
    # Arrange
    light, dark = _blocks()
    # Act
    found = (
        _css_palette.declared(light, "--text-secondary") is not None
        and _css_palette.declared(dark, "--text-secondary") is not None
    )
    # Assert
    assert found


def test_the_opacity_detector_can_see_a_text_rule_that_sets_it() -> None:
    """POSITIVE control: the pattern matches the shape this card removed."""
    # Arrange
    defective = ".stx-app-empty__hint {\n  font-size: 12px;\n  opacity: 0.6;\n}"
    # Act
    found = re.search(r"(?m)^\s*opacity\s*:", defective) is not None
    # Assert
    assert found


def test_the_opacity_detector_does_not_fire_on_the_decorative_icon() -> None:
    """NEGATIVE control: the icon's exemption is by selector, not by accident."""
    # Arrange
    icon_selector = ".stx-app-empty__icon"
    # Act
    exempt = any(marker in icon_selector for marker in _DECORATIVE)
    # Assert
    assert exempt


# ── The shipped component ─────────────────────────────────────────────────


def test_the_empty_state_text_colour_is_a_token_not_a_literal() -> None:
    """A literal here would freeze one theme's value into the component."""
    # Arrange
    body = _rule_block(".stx-app-empty")
    # Act
    token = re.search(r"color:\s*var\(\s*(--[\w-]+)", body) is not None
    # Assert
    assert token


def test_the_text_colour_token_is_declared_in_both_palettes() -> None:
    """A token in one palette only dangles the other theme."""
    # Arrange
    light, dark = _blocks()
    # Act
    declared = (
        _css_palette.declared(light, _text_colour_token()) is not None
        and _css_palette.declared(dark, _text_colour_token()) is not None
    )
    # Assert
    assert declared


def test_the_empty_state_text_passes_aa_in_the_light_theme() -> None:
    """THE FIX, as arithmetic: the resolved colour clears 4.5 on every surface."""
    # Arrange
    light, _ = _blocks()
    # Act
    worst = _worst_ratio(light)
    # Assert
    assert worst >= _AA_BODY, f"light empty-state text is {worst:.2f}:1 on its worst surface"


def test_the_empty_state_text_passes_aa_in_the_dark_theme() -> None:
    """Both themes, because the renderer is shared and the card measured both."""
    # Arrange
    _, dark = _blocks()
    # Act
    worst = _worst_ratio(dark)
    # Assert
    assert worst >= _AA_BODY, f"dark empty-state text is {worst:.2f}:1 on its worst surface"


def test_the_contrast_check_can_fail() -> None:
    """POSITIVE control: the threshold is capable of reporting the old defect."""
    # Arrange
    surface = "#f8f7f5"
    # Act
    ratio = _css_palette.contrast("#777777", surface)
    # Assert
    assert ratio < _AA_BODY


def test_the_contrast_check_is_sane_on_a_known_pair() -> None:
    """POSITIVE control: black on white is 21:1, so the maths is not inverted."""
    # Arrange
    black, white = "#000000", "#ffffff"
    # Act
    ratio = _css_palette.contrast(black, white)
    # Assert
    assert round(ratio, 2) == 21.0


def test_no_text_rule_stacks_an_opacity_on_the_colour() -> None:
    """THE SECOND FIX: the hint is quieter by size, never by a second alpha."""
    # Arrange
    expected: list[str] = []
    # Act
    offenders = _rules_carrying_opacity()
    # Assert
    assert offenders == expected, (
        f"these rules dim text with opacity, which MULTIPLIES the ratio: {offenders}"
    )


def test_the_decorative_icon_keeps_its_opacity() -> None:
    """The exemption is load-bearing: the detector is not 'no opacity anywhere'."""
    # Arrange
    icon = _rule_block(".stx-app-empty__icon")
    # Act
    dimmed = "opacity" in icon
    # Assert
    assert dimmed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
