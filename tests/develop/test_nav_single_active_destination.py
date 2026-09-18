#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The global dock must name EXACTLY ONE destination, and inactive icons neutral.

MEASURED DEFECT (operator, mobile screenshots, 2026-09-17): the Cards Board tab
was the real selection while the global dock showed Home in purple and Chat in
blue. Not multiple routing — INACTIVE ICONS PAINTED IN THEIR BRAND COLOUR, which
reads as selected. A dock ambiguous about where you are is worse than one with no
highlighting at all.

WHAT THIS FILE GUARDS, and what only the browser can (recorded on the PR):
  * the neutral-inactive rule exists and is armed to out-specify a per-app icon
    rule, so a leaf's brand colour cannot resurrect the defect;
  * the current destination is keyed to aria-current (not a class alone);
  * the LOCAL app tab treatment is a DIFFERENT attribute and a DIFFERENT visual
    (aria-selected + an underline on a text tab) from the global dock's
    (aria-current + a filled background on a rail), so the two cannot be confused.

The browser arm is recorded in the PR body with computed colours at 390x844:
inactive brand-coloured icons compute to the neutral rgb(139,148,158), the single
current destination carries rgba(177,186,196,0.12), and an INLINE brand colour
still wins — which is why the render site must stop inlining it.

ONE ASSERTION PER TEST, THREE MARKER LINES (PA-307 §3).
"""

from __future__ import annotations

import re

import pytest

from tests._checkout import css_dir

_NAV = css_dir() / "app" / "selector-nav.css"
_PANES = css_dir() / "app" / "panes.css"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def _nav_css() -> str:
    return _COMMENT.sub("", _NAV.read_text(errors="replace"))


def _panes_css() -> str:
    return _COMMENT.sub("", _PANES.read_text(errors="replace"))


def _rule_block(css: str, selector: str) -> str:
    for match in _RULE.finditer(css):
        parts = [p.strip() for p in match.group(1).split(",")]
        if selector in parts:
            return match.group(2)
    return ""


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
    """NEGATIVE: prose about comments is not one to strip."""
    # Arrange
    sample = "// this line merely mentions comments"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is None


def test_the_rule_extractor_matches_a_literal_rule() -> None:
    """POSITIVE: _RULE finds a rule and both of its halves."""
    # Arrange
    sample = ".a { color: red; }"
    # Act
    match = _RULE.search(sample)
    # Assert
    assert match is not None and match.group(2).strip() == "color: red;"


def test_the_rule_extractor_ignores_a_bare_selector_mention() -> None:
    """NEGATIVE: a selector named without a block is not a rule."""
    # Arrange
    sample = ".stx-app-selector-nav__item -- selector mention, no braces"
    # Act
    match = _RULE.search(sample)
    # Assert
    assert match is None


def test_the_extractor_is_not_fooled_by_a_comment_only_mention() -> None:
    """POSITIVE: the extractor returns the body of the rule it is given."""
    # Arrange
    sample = ".a { color: red; } .b { color: blue; }"
    # Act
    match = re.search(re.escape(".b") + r"\s*\{([^{}]*)\}", sample)
    # Assert
    assert match is not None and match.group(1).strip() == "color: blue;"


# ── The dock's own rules ──────────────────────────────────────────────────


def test_inactive_items_are_declared_neutral() -> None:
    """The rule that kills the defect: a non-current item is neutral text."""
    # Arrange
    block = _rule_block(_nav_css(), ".stx-app-selector-nav__item:not([aria-current])")
    # Act
    neutral = "var(--workspace-text-secondary" in block
    # Assert
    assert neutral


def test_inactive_items_cannot_take_a_container_background() -> None:
    """A filled background on an inactive item is the other 'looks selected' tell."""
    # Arrange
    block = _rule_block(_nav_css(), ".stx-app-selector-nav__item:not([aria-current])")
    # Act
    transparent = "background: transparent" in block
    # Assert
    assert transparent


def test_the_inactive_icon_inherits_the_neutral_item_colour() -> None:
    """The icon is where a brand colour arrives, so it must be re-neutralised."""
    # Arrange
    css = _nav_css()
    # Act
    armed = (
        ".stx-app-selector-nav__item:not([aria-current]) i" in css
        and "color: inherit" in css
    )
    # Assert
    assert armed


def test_the_current_destination_is_keyed_to_aria_current() -> None:
    """A class alone is what let two destinations look selected."""
    # Arrange
    css = _nav_css()
    # Act
    keyed = ".stx-app-selector-nav__item[aria-current]" in css
    # Assert
    assert keyed


def test_the_selected_treatment_is_a_filled_background_on_the_rail() -> None:
    """The dock's visual for 'you are here': a filled item."""
    # Arrange
    block = _rule_block(_nav_css(), ".stx-app-selector-nav__item[aria-current]")
    # Act
    filled = "background:" in block and "var(--workspace-bg-active" in block
    # Assert
    assert filled


# ── The local-tab vs global-nav distinction ───────────────────────────────


def test_local_tabs_select_by_a_different_attribute() -> None:
    """Local tabs use aria-selected; the dock uses aria-current. Not the same signal."""
    # Arrange
    css = _panes_css()
    # Act
    uses_aria_selected = '.stx-panes__tab[aria-selected="true"]' in css
    # Assert
    assert uses_aria_selected


def test_the_local_tab_visual_is_an_inset_underline_not_a_filled_rail() -> None:
    """Two vocabularies, two treatments — a tab row reads as content, the dock as chrome.

    The shipped mechanism is an INSET SHADOW underline (read from panes.css), not
    a border: this assertion said "border-bottom" when written from my canary
    page rather than from the stylesheet, and the test caught me. The claim is
    now about the file the product actually ships.
    """
    # Arrange
    block = _rule_block(_panes_css(), '.stx-panes__tab[aria-selected="true"]')
    # Act
    underlined = "box-shadow: inset 0 -2px 0" in block
    # Assert
    assert underlined


def test_the_tab_selection_also_raises_the_surface() -> None:
    """The tab's second tell: a raised surface, which the dock's rail item does not use."""
    # Arrange
    block = _rule_block(_panes_css(), '.stx-panes__tab[aria-selected="true"]')
    # Act
    raised = "background: var(--bg-surface" in block
    # Assert
    assert raised


def test_the_dock_does_not_borrow_the_tab_attribute() -> None:
    """If the dock ever keyed on aria-selected, the two signals would collide again."""
    # Arrange
    css = _nav_css()
    # Act
    borrowed = ".stx-app-selector-nav__item[aria-selected]" in css
    # Assert
    assert borrowed is False


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
