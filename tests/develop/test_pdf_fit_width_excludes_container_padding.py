#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fit-width must size to the container's CONTENT box, not to `clientWidth`.

THE DEFECT THIS GUARDS, measured by scitex-writer on a phone (chromium
390x844, their PR #396 / v2.43.3), not inferred here:

    .pdf-viewer-host { padding: 16px }
    -> fit-width produced a 382px canvas at x=16
    -> right edge 398 on a 390px viewport
    -> container scrollWidth 414 vs clientWidth 382

`clientWidth` INCLUDES the horizontal padding (it excludes borders and the
scrollbar only), so dividing by it sizes the page to the padded box and the
canvas overflows the content box by exactly the two paddings. Writer worked
around it by deleting the horizontal gutter at phone width; every adopter would
have inherited the same bug, so it is fixed where the geometry is computed.

WHY A STATIC GUARD AND NOT ONLY THE UNIT TEST: the unit test covers the pure
arithmetic (`contentBoxWidth`). What it cannot see is a CALL SITE that stops
using it — someone reintroducing `clientWidth / baseWidth` would keep every
arithmetic test green while the defect returns. That is the one thing this file
is for. The end-to-end 390px geometry is recorded on the card from a real
browser; this is the change-time half.

ONE ASSERTION PER TEST, THREE MARKER LINES (PA-307 §3), and every detector
carries a positive and a negative control over LITERAL samples.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SOURCE = _ROOT / "src/scitex_ui/static/scitex_ui/ts/app/pdf-viewer/index.ts"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"(?m)^\s*//.*$")


def _source() -> str:
    """The module with its comments stripped — a comment about the fix is not the fix."""
    text = _LINE_COMMENT.sub("", _COMMENT.sub("", _SOURCE.read_text(errors="replace")))
    return text


def _fit_width_body() -> str:
    """The body of `async fitWidth()` — the one place the scale is computed."""
    match = re.search(r"async fitWidth\(\)[^{]*\{(.*?)\n  \}", _source(), re.S)
    return match.group(1) if match else ""


def _content_box_body() -> str:
    match = re.search(r"function contentBoxWidth\((.*?)\n\}", _source(), re.S)
    return match.group(1) if match else ""


# ── Extractor controls ────────────────────────────────────────────────────


def test_the_comment_stripper_matches_a_real_comment() -> None:
    """POSITIVE: _COMMENT matches a real block comment."""
    # Arrange
    sample = "/* a real comment */ const a = 1;"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is not None


def test_the_block_stripper_ignores_a_mere_mention() -> None:
    """NEGATIVE: a source line that merely mentions comments is not one to strip."""
    # Arrange
    sample = "const a = 1; // no block comment on this line"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is None


def test_the_line_stripper_matches_a_real_line_comment() -> None:
    """POSITIVE: _LINE_COMMENT matches a real `//` comment."""
    # Arrange
    sample = "// a real line comment\nconst a = 1;"
    # Act
    match = _LINE_COMMENT.search(sample)
    # Assert
    assert match is not None


def test_the_line_stripper_ignores_a_block_comment_line() -> None:
    """NEGATIVE: a `/* ... */` line is not a `//` comment."""
    # Arrange
    sample = "/* inline only */"
    # Act
    match = _LINE_COMMENT.search(sample)
    # Assert
    assert match is None


def test_the_extractors_refuse_to_be_vacuous() -> None:
    """POSITIVE: an empty extraction would make every assertion below pass."""
    # Arrange
    body, helper = _fit_width_body(), _content_box_body()
    # Act
    sizes = (len(body), len(helper))
    # Assert
    assert sizes[0] > 20 and sizes[1] > 20


def test_the_call_site_detector_can_find_the_defective_line() -> None:
    """POSITIVE control: the pattern DOES match the shape that shipped the bug."""
    # Arrange
    defective = "const target = this.container.clientWidth / baseWidth;"
    # Act
    found = re.search(r"clientWidth\s*/\s*baseWidth", defective) is not None
    # Assert
    assert found


def test_the_call_site_detector_does_not_match_the_corrected_line() -> None:
    """NEGATIVE control: the corrected call does not read as the defect."""
    # Arrange
    corrected = "const target = containerContentWidth(this.container) / baseWidth;"
    # Act
    found = re.search(r"clientWidth\s*/\s*baseWidth", corrected) is not None
    # Assert
    assert found is False


# ── The call site ─────────────────────────────────────────────────────────


def test_fit_width_no_longer_sizes_from_client_width() -> None:
    """The defect's own expression must be gone from the call site."""
    # Arrange
    body = _fit_width_body()
    # Act
    defective = re.search(r"clientWidth\s*/", body) is not None
    # Assert
    assert defective is False


def test_fit_width_sizes_from_the_content_box_helper() -> None:
    """The scale is computed from the helper, so the padding is subtracted."""
    # Arrange
    body = _fit_width_body()
    # Act
    uses_helper = "containerContentWidth(" in body
    # Assert
    assert uses_helper


def test_fit_width_still_guards_against_a_non_positive_scale() -> None:
    """A zero-width content box must not produce an infinite or zero scale."""
    # Arrange
    body = _fit_width_body()
    # Act
    guarded = "Number.isFinite(target)" in body and "target > 0" in body
    # Assert
    assert guarded


# ── The helper ────────────────────────────────────────────────────────────


def test_the_helper_subtracts_the_left_padding() -> None:
    """One side of the gutter is not a gutter: both must be removed."""
    # Arrange
    helper = _content_box_body()
    # Act
    subtracts = "paddingLeft" in helper
    # Assert
    assert subtracts


def test_the_helper_subtracts_the_right_padding() -> None:
    """The other side of the same gutter."""
    # Arrange
    helper = _content_box_body()
    # Act
    subtracts = "paddingRight" in helper
    # Assert
    assert subtracts


def test_the_helper_reads_both_paddings_from_the_live_box_model() -> None:
    """The paddings come from computed style, not from a hardcoded constant."""
    # Arrange
    source = _source()
    # Act
    reads_style = (
        "getComputedStyle(container)" in source
        and "style.paddingLeft" in source
        and "style.paddingRight" in source
    )
    # Assert
    assert reads_style


def test_the_helper_clamps_a_padding_larger_than_the_box() -> None:
    """A container narrower than its own padding sizes nothing, never negative."""
    # Arrange
    helper = _content_box_body()
    # Act
    clamps = "content > 0 ? content : 0" in helper
    # Assert
    assert clamps


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
