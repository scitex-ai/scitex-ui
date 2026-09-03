#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_disabled_opacity_is_one_token.py

"""The disabled appearance is ONE value, defined once.

MEASURED 2026-09-03, before the consolidation: sixteen literal opacities across
fifteen stylesheets, split EIGHT-EIGHT between 0.4 and 0.5.

That is not a majority with an outlier — it is a coin flip propagated by
copy-paste in both directions, and there is no semantic split beneath it. The
tempting reading is "0.4 for buttons, 0.5 for content"; it fails, because
recent-pane's and git-panel's buttons were 0.4 while toast's and media-input's
were 0.5. Buttons sat on both sides.

0.5 won on LEGIBILITY: half the sites dim TEXT rather than icons, and WCAG
exempts disabled controls from contrast minimums — which is exactly why such a
value drifts to whoever typed last unless it is decided once.

WHY THIS GUARD COVERS TWO SPELLINGS. `.disabled` (a class) and `:disabled` (the
native pseudo-class) are both in use here for one concept. The first survey of
this defect searched only the class and reported FIVE files; including the
pseudo-class made it fifteen. A guard that watches one spelling would license
the other to drift, and would do so invisibly — which is how the count was
wrong by 3x to begin with.

DIM IS NOT THIS TOKEN. The "sign in to use this" state is a SIBLING of disabled,
not a reuse of it: "broken" and "available once you sign in" are different facts
and must not share an appearance. When dim lands it gets its own value, and this
guard should keep passing unchanged.
"""

from __future__ import annotations

import re

from tests._checkout import css_dir

#: Any `selector { ... }` block. The selector is everything since the previous
#: brace, so only its LAST LINE is the real selector — a preceding comment that
#: happens to say "disabled" must not qualify the block. Getting that wrong once
#: matched `.stx-toast { opacity: 0 }`, whose zero is a hidden-by-default
#: animation start state; rewriting it to 0.5 would have left every toast
#: permanently half-visible on first paint.
_BLOCK = re.compile(r"([^{}]*)\{([^}]*)\}")

#: A hardcoded opacity, i.e. not `var(--disabled-opacity)`.
_LITERAL_OPACITY = re.compile(r"opacity:\s*[0-9.]+\s*;")

#: Files that MUST keep a literal, one entry at a time and each with its reason.
#: Never widen this to a pattern — a blanket exemption would re-license the very
#: drift this guard exists to stop.
_MUST_STAY_LITERAL = {
    # app/context-menu.css is one of two files in _THEME_ONLY
    # (test_app_css_token_layer.py): it advertises itself as consumable with
    # shell/theme.css ALONE. --disabled-opacity lives in primitives/spacing.css,
    # and NO SINGLE HOME SATISFIES BOTH CONTRACTS — app.css imports primitives
    # but not shell/theme.css, so relocating the token to theme.css would break
    # the other fourteen sites instead of this one. Reaching across that layer
    # is how the context menu once rendered dark-on-dark on a live page, which
    # is the incident test_app_css_token_layer was written for.
    #
    # This exemption retires when the app.css/primitives layering question is
    # decided (scitex-ui-app-css-tokens-defined-nowhere-20260728) — at which
    # point one home becomes reachable from both and the literal can go.
    "context-menu.css",
}


def _disabled_blocks() -> list[tuple[str, str, str]]:
    """(file, selector, body) for every rule whose SELECTOR mentions disabled."""
    found: list[tuple[str, str, str]] = []
    for path in sorted(css_dir().rglob("*.css")):
        if "vendor" in path.parts:
            continue
        for match in _BLOCK.finditer(path.read_text(encoding="utf-8", errors="replace")):
            selector = match.group(1).rstrip().split("\n")[-1].strip()
            if "disabled" in selector.lower():
                found.append((path.name, selector, match.group(2)))
    return found


def test_no_disabled_rule_hardcodes_an_opacity() -> None:
    """A disabled rule reads the token; it does not carry its own number."""
    # Arrange
    blocks = _disabled_blocks()

    # Act
    offenders = sorted(
        f"{name}: {selector[:60]}"
        for name, selector, body in blocks
        if _LITERAL_OPACITY.search(body) and name not in _MUST_STAY_LITERAL
    )

    # Assert
    assert not offenders, (
        f"{len(offenders)} disabled rule(s) hardcode an opacity instead of "
        f"reading var(--disabled-opacity): {'; '.join(offenders)}. This is how "
        "the value reached an even 8/8 split between 0.4 and 0.5 across fifteen "
        "files — every copy is a place the next person can disagree with. Use "
        "the token in primitives/spacing.css."
    )


def test_each_exemption_is_still_needed() -> None:
    """The reverse check: an exemption that no longer applies must be DELETED.

    Without this, `_MUST_STAY_LITERAL` only ever grows and becomes a record of
    what was once true. The forcing function is that removing the literal must
    REQUIRE removing the entry — otherwise a fixed file keeps its licence to
    drift and nobody notices.

    Same shape as the ceiling in test_app_css_tokens_resolve.py, whose own
    docstring records that a list asserting only "does not grow" leaves a fixed
    entry sitting there green forever.
    """
    # Arrange
    literal_files = {
        name
        for name, _, body in _disabled_blocks()
        if _LITERAL_OPACITY.search(body)
    }

    # Act
    stale = sorted(_MUST_STAY_LITERAL - literal_files)

    # Assert
    assert not stale, (
        f"{len(stale)} exemption(s) in _MUST_STAY_LITERAL no longer carry a "
        f"literal opacity: {', '.join(stale)}. The constraint that justified "
        "them is gone — delete the entry rather than leaving it to describe "
        "the past."
    )


def test_the_guard_sees_both_disabled_spellings() -> None:
    """ANTI-VACUITY, and specifically about the failure that caused this card.

    The first survey searched `.disabled` and reported five files; adding
    `:disabled` made it fifteen. So this guard must be shown to see BOTH, not
    merely to find something — a population made entirely of one spelling would
    pass while licensing the other to drift.
    """
    # Arrange
    selectors = [selector for _, selector, _ in _disabled_blocks()]

    # Act
    spellings = {
        "class": any(".disabled" in s for s in selectors),
        "pseudo": any(":disabled" in s for s in selectors),
    }

    # Assert
    assert all(spellings.values()), (
        f"the guard's population is missing a spelling: {spellings}. Both "
        "`.disabled` and `:disabled` are in use in this package; if one no "
        "longer appears, either it was genuinely retired — retire it here too, "
        "deliberately — or this file's selector matching has stopped seeing it "
        "and is now guarding half of what it claims."
    )
