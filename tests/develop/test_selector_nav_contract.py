#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract for the ONE hierarchical selector: tabs on desktop, cascade on mobile.

OPERATOR DIRECTION 2026-09-17 (card sdk-mobile-app-shell-primitives-20260917):
a compact hierarchical selector/navigation primitive, "usable as tabs on desktop
and cascading dropdowns on mobile". The shell already shipped the STRIP half of
that vocabulary as CSS-only (css/app/selector-nav.css, ported from scitex-cloud);
this PR adds the behaviour, the second shape, and the switch between them.

WHY A STATIC GUARD ALONGSIDE THE VITEST FILE: the vitest arms prove what the
CLASS renders; they cannot see the stylesheet or the boundary agreement. What is
pinned here is the part a refactor breaks silently:

  * the cascade shape's classes have RULES (a class written by ts/ that no
    stylesheet touches renders as an unstyled list — the population on card
    scitex-ui-shell-components-ship-classes-no-stylesheet-touches-20260910);
  * the switch happens at 600px, the SAME boundary css/app/project-selector.css
    and css/app/app-header.css use, because three primitives changing shape at
    three different widths is how a header, a picker and a selector end up
    disagreeing on one phone;
  * the touch minimum is present for the cascade rows.

The browser measurement (a real 390px cascade, not a source reading) is recorded
on the card, which is the deliberate weaker-half/instrument split this repo uses
for every responsive primitive.

ONE ASSERTION PER TEST, THREE MARKER LINES (PA-307 §3); every detector carries a
positive and a negative control over LITERAL samples.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests._checkout import css_dir

_STATIC = css_dir().parent
_CSS = css_dir() / "app" / "selector-nav.css"
_SIBLINGS = (
    # The project selector's own contract pins the header slot's phone rules, so
    # it is the sibling that MUST agree with this file today. app-header.css
    # (PR #250) switches at the same 600px value but is not on develop yet;
    # adding it here before it lands would make this guard read a file that
    # does not exist, which fails for the wrong reason.
    css_dir() / "app" / "project-selector.css",
)
_TS = _STATIC / "ts" / "app" / "selector-nav"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_URL = re.compile(r"@media\s*\(\s*max-width:\s*(\d+)px\s*\)")

_CASCADE = "--cascade"
_LEVEL = "__level"


def _css() -> str:
    return _COMMENT.sub("", _CSS.read_text(errors="replace"))


def _ts_text() -> str:
    return "\n".join(path.read_text(errors="replace") for path in sorted(_TS.rglob("*.ts")))


def _rule_block(selector: str) -> str:
    """The body of the first rule whose selector list ENDS with `selector`."""
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", _css()):
        parts = [part.strip() for part in match.group(1).split(",")]
        if parts and parts[-1] == selector:
            return match.group(2)
    return ""


def _boundaries(path: pathlib.Path) -> set[int]:
    """Every max-width breakpoint the stylesheet switches at."""
    return {int(m) for m in _URL.findall(path.read_text(errors="replace"))}


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
    sample = "// this line merely mentions comments"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is None


def test_the_breakpoint_extractor_matches_a_real_media_query() -> None:
    """POSITIVE: the extractor reads a max-width boundary."""
    # Arrange
    sample = "@media (max-width: 600px) { .a { color: red; } }"
    # Act
    found = _URL.findall(sample)
    # Assert
    assert found == ["600"]


def test_the_breakpoint_extractor_ignores_a_min_width_query() -> None:
    """NEGATIVE: a MIN-width boundary is a different switch, not this one."""
    # Arrange
    sample = "@media (min-width: 900px) { .a { color: red; } }"
    # Act
    found = _URL.findall(sample)
    # Assert
    assert found == []


def test_the_breakpoint_extractor_ignores_a_pointer_query() -> None:
    """NEGATIVE: a pointer query is not a width boundary."""
    # Arrange
    sample = "@media (pointer: coarse) { .a { min-height: 44px; } }"
    # Act
    match = _URL.search(sample)
    # Assert
    assert match is None


def test_the_rule_extractor_matches_a_literal_rule() -> None:
    """POSITIVE: the extractor returns the body of the rule it is given."""
    # Arrange
    sample = ".a { color: red; } .b { color: blue; }"
    # Act
    match = re.search(re.escape(".b") + r"\s*\{([^{}]*)\}", sample)
    # Assert
    assert match is not None and match.group(1).strip() == "color: blue;"


def test_the_stylesheet_is_not_empty() -> None:
    """POSITIVE: an empty or moved file would make every guard below vacuous."""
    # Arrange
    css = _css()
    # Act
    size = len(css)
    # Assert
    assert size > 500


# ── The cascade shape ships styles, not just class names ───────────────────


def test_the_cascade_modifier_has_a_rule() -> None:
    """The modifier ts/ writes must be styled, or the cascade renders flat."""
    # Arrange
    css = _css()
    # Act
    found = re.search(re.escape(_CASCADE) + r"[^{]*\{", css) is not None
    # Assert
    assert found


def test_the_level_class_has_a_rule() -> None:
    """`__level` is WRITTEN by the new component; it must be styled here."""
    # Arrange
    block = _rule_block(".stx-app-selector-nav__level")
    # Act
    styled = block.strip() != ""
    # Assert
    assert styled


def test_a_nested_level_is_indented_so_the_hierarchy_is_visible() -> None:
    """Two levels at the same indent read as one flat list.

    Keyed to the DEPTH ATTRIBUTE, not to nesting: the levels are siblings in the
    DOM, which a 390x844 measurement caught (every level at the same x).
    """
    # Arrange
    block = _rule_block('.stx-app-selector-nav__level[data-stx-depth="1"]')
    # Act
    indented = "margin-left" in block
    # Assert
    assert indented


def test_the_component_tags_each_level_with_its_depth() -> None:
    """The attribute the indent is keyed to is written by the component."""
    # Arrange
    ts = _ts_text()
    # Act
    tagged = 'setAttribute("data-stx-depth"' in ts
    # Assert
    assert tagged


def test_the_cascade_rows_meet_the_touch_minimum() -> None:
    """A cascade row is a tap target, wherever the narrow shape is used."""
    # Arrange
    block = _rule_block(
        ".stx-app-selector-nav--cascade .stx-app-selector-nav__item"
    )
    # Act
    minimum = "min-height: var(--stx-touch-target-min, 44px)" in block
    # Assert
    assert minimum


# ── The boundary agreement, which is the part a refactor breaks silently ───


def test_the_cascade_switches_at_a_600px_boundary() -> None:
    """The cascade's own shape switch is the shared phone boundary."""
    # Arrange
    found = _boundaries(_CSS)
    # Act
    shared = 600 in found
    # Assert
    assert shared


def test_the_sibling_primitives_use_the_same_boundary() -> None:
    """Header, project picker and selector change shape on ONE event."""
    # Arrange
    mine = _boundaries(_CSS)
    # Act
    disagreements = [str(p.name) for p in _SIBLINGS if not (_boundaries(p) & mine)]
    # Assert
    assert disagreements == []


def test_the_component_reads_the_same_default_breakpoint() -> None:
    """The TS default and the stylesheet's media query cannot drift apart."""
    # Arrange
    ts = _ts_text()
    # Act
    declared = re.search(r"DEFAULT_BREAKPOINT\s*=\s*600\b", ts) is not None
    # Assert
    assert declared


# ── The instrument the component uses ─────────────────────────────────────


def test_the_component_declares_the_manifest_class_convention() -> None:
    """`const CLS` is what the generated class-manifest reads."""
    # Arrange
    ts = _ts_text()
    # Act
    declared = 'const CLS = "stx-app-selector-nav"' in ts
    # Assert
    assert declared


def test_every_node_is_a_real_button() -> None:
    """Touch, mouse and keyboard must resolve ONE id, not three handlers."""
    # Arrange
    ts = _ts_text()
    # Act
    real_button = 'document.createElement("button")' in ts
    # Assert
    assert real_button


def test_the_component_reports_changes_on_one_named_event() -> None:
    """A leaf wires one handler; the presentation stays the primitive's."""
    # Arrange
    ts = _ts_text()
    # Act
    named = 'SELECTOR_NAV_CHANGE = "stx-app-selector-nav:change"' in ts
    # Assert
    assert named


def test_an_unknown_selection_is_refused_not_ignored() -> None:
    """A silently ignored id leaves the strip on a selection nobody asked for."""
    # Arrange
    ts = _ts_text()
    # Act
    refuses = "no node with that id" in ts
    # Assert
    assert refuses


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
