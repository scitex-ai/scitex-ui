#!/usr/bin/env python3
"""``utilities/effects.css`` may only ADD tokens, never redefine primitives.

THE BUG THIS EXISTS FOR IS ALREADY IN PRODUCTION — in scitex-hub, measured
2026-08-23, and it is the reason this file's subject exists at all.

hub's ``primitives/spacing.css:41-43`` declares the transition durations
150/200/300ms. Their ``utilities/effects.css:25-27`` declares the SAME THREE
NAMES with 200/300/500ms. ``variables.css`` imports spacing first and effects
second, so effects wins: hub's spacing.css declarations are dead code, and hub
ran 33-67% slower than scitex-ui while the token names claimed parity across
both products.

Nothing reported it. The names matched, so no tool saw a conflict; only the
values differed, and CSS has no opinion about that. hub's own reading was that
it was an import-ORDER accident rather than a design judgement — which is
exactly why a comment saying "don't do this" would not have prevented it. It
was not done on purpose the first time.

THE TRAP THIS GUARDS, specifically. scitex-ui now imports the same file in the
same last position (``primitives/variables.css``). Being last is harmless only
while this file's token names are disjoint from every file above it. The moment
one overlaps, this package silently acquires hub's bug, in the direction that
is hardest to see: the primitives layer keeps DECLARING the value it no longer
supplies.

So the assertion is not "the values agree" but the stronger, order-independent
"the names do not collide". Values that agree today are one edit away from the
silent no-op described in test_primitives_define_each_token_once.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# Resolve the CHECKOUT rather than the installed package, for the reason given
# at length in test_primitives_define_each_token_once: a guard that goes red for
# the right reason in the wrong tree is indistinguishable from one that works.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CSS = _REPO_ROOT / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
_PRIMITIVES = _CSS / "primitives"
_EFFECTS = _CSS / "utils" / "effects.css"
_VARIABLES = _PRIMITIVES / "variables.css"

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_DECLARATION = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")

#: The import line that carries the effects layer into the primitives bundle.
#:
#: hub's fork spells this `../utilities/effects.css`, and the plan recorded on
#: the card was for scitex-ui to adopt that path verbatim so both variables.css
#: files would converge on an identical line. Reading the tree changed it:
#: scitex-ui ALREADY has the directory, named `utils/`, and `utils/layout.css`
#: opens with "Layout Utilities" — same concept, established name. Adding
#: `utilities/` beside it would have shipped two names for one directory, which
#: is the defect this whole convergence exists to remove, only inside a single
#: package instead of across two. hub changes one word instead.
_IMPORT_LINE = '@import url("../utils/effects.css");'


def _declared_in(path: pathlib.Path) -> set[str]:
    """Custom properties DEFINED in ``path``, with comments stripped first.

    Stripping is what separates a definition from prose ABOUT a definition.
    effects.css documents at length why ``--border-color`` is deliberately not
    defined there, so a scanner that reads comments would find the very token
    the file exists to not define.
    """
    text = _CSS_COMMENT.sub("", path.read_text(errors="replace"))
    return set(_DECLARATION.findall(text))


def _declared_in_primitives() -> dict[str, str]:
    """Token -> the primitives filename that defines it."""
    found: dict[str, str] = {}
    for path in sorted(_PRIMITIVES.glob("*.css")):
        for token in _declared_in(path):
            found.setdefault(token, path.name)
    for path in sorted(_PRIMITIVES.rglob("colors/*.css")):
        for token in _declared_in(path):
            found.setdefault(token, f"colors/{path.name}")
    return found


def test_declaration_pattern_matches_a_real_declaration() -> None:
    """POSITIVE control on the pattern itself, not on the tree it is aimed at.

    The tests below check the SHIPPED files. If the regex were broken they
    would fail too — but they would fail pointing at the stylesheet, and the
    reader would go looking for a missing token that is really there.
    """
    # Arrange
    sample = "  --border-width: 1px;"
    # Act
    match = _DECLARATION.search(sample)
    # Assert
    assert match is not None and match.group(1) == "--border-width", (
        f"_DECLARATION failed to read a declaration out of {sample!r}"
    )


def test_declaration_pattern_ignores_a_bare_mention() -> None:
    """NEGATIVE control: a token NAME without a colon is not a declaration.

    Note what this does NOT cover, because it is the interesting half: prose
    that quotes a full declaration — as effects.css does, verbatim, to explain
    which theme files own --border-color — DOES match this pattern. It must,
    since it is textually a declaration. Comment stripping is what separates
    them, which is why _CSS_COMMENT carries its own control below.
    """
    # Arrange
    sample = "the --border-width token is documented in utilities/effects.css"
    # Act
    match = _DECLARATION.search(sample)
    # Assert
    assert match is None, (
        f"_DECLARATION matched {match.group(0)!r} in prose that merely NAMES a "
        "token. Every comment mentioning a token would read as defining it."
    )


def test_comment_pattern_matches_a_real_comment() -> None:
    """POSITIVE control on the stripper."""
    # Arrange
    sample = "/* --border-color: red; */\n--border-width: 1px;"
    # Act
    stripped = _CSS_COMMENT.sub("", sample)
    # Assert
    assert "--border-color" not in stripped, (
        f"_CSS_COMMENT did not remove the comment from {sample!r}; a token "
        "discussed in prose would be counted as declared"
    )


def test_comment_stripper_does_not_eat_code() -> None:
    """NEGATIVE control: over-matching is the failure that hides real defects.

    A greedy or malformed stripper that swallows code silently empties the
    scan, and an empty scan reports a clean, converged layer. This is the
    control the other comment-stripping guards in this suite were exempted
    from carrying; there is no reason for a new file to inherit that gap.
    """
    # Arrange
    sample = "/* a */ --border-width: 1px; /* b */"
    # Act
    stripped = _CSS_COMMENT.sub("", sample)
    # Assert
    assert "--border-width: 1px;" in stripped, (
        f"_CSS_COMMENT consumed live code from {sample!r}, leaving "
        f"{stripped!r} — the scan would silently under-report"
    )


def test_the_scanner_finds_a_real_token_in_effects() -> None:
    """POSITIVE CONTROL: the scanner matches an instance that is really there.

    Without it, a renamed file or a broken regex yields an empty set, the
    collision check finds no collisions, and the suite reports convergence that
    was never measured.
    """
    # Arrange: the shipped effects.css is the fixture.
    # Act
    declared = _declared_in(_EFFECTS)
    # Assert
    assert "--border-width" in declared, (
        f"--border-width was not found in {_EFFECTS}. Either the file moved or "
        "the declaration regex is broken; either way the collision check below "
        "would pass without having looked at anything."
    )


def test_the_scanner_ignores_a_token_merely_MENTIONED_in_prose() -> None:
    """NEGATIVE CONTROL: a name discussed in a comment is not a definition.

    This is not a constructed sample. effects.css genuinely discusses
    ``--border-color`` in prose — that discussion is the record of why the
    token is NOT defined there — so if comment-stripping regressed, this guard
    would report the file defining the exact token it exists to leave alone.
    """
    # Arrange
    raw = _EFFECTS.read_text(errors="replace")
    # Act
    declared = _declared_in(_EFFECTS)
    # Assert
    assert "--border-color" in raw and "--border-color" not in declared, (
        "expected --border-color to appear in effects.css PROSE but not as a "
        "declaration. If it is missing from the prose the control is vacuous; "
        "if it is in `declared` the comment stripper is broken and every "
        "documented token would read as defined."
    )


def test_effects_defines_no_token_the_primitives_layer_already_defines() -> None:
    """The collision that made hub's spacing.css transitions dead code."""
    # Arrange
    primitives = _declared_in_primitives()
    # Act
    collisions = {
        token: primitives[token]
        for token in sorted(_declared_in(_EFFECTS))
        if token in primitives
    }
    # Assert
    if collisions:
        lines = [
            "utilities/effects.css redefines tokens the primitives layer "
            "already defines. variables.css imports effects LAST, so effects "
            "wins and the primitives declaration becomes dead code:",
            "",
        ]
        for token in sorted(collisions):
            lines.append(f"  {token}   also defined in primitives/{collisions[token]}")
        lines += [
            "",
            "This is exactly the defect measured in scitex-hub on 2026-08-23, "
            "where --transition-fast/normal/slow were declared in spacing.css "
            "and silently overridden from effects.css, leaving hub 33-67% "
            "slower than scitex-ui while the token names claimed parity.",
            "",
            "utilities/effects.css is an ADDITIVE layer. If a primitive needs a "
            "different value, change it in the primitives file that owns it.",
        ]
        pytest.fail("\n".join(lines))


def test_border_color_stays_theme_aware_in_the_colors_layer() -> None:
    """--border-color must not be flattened out of the theme system.

    The convergence note on this card proposed adopting BOTH --border-width and
    --border-color from hub "which it genuinely lacks". That was half wrong:
    scitex-ui owns --border-color already, theme-aware, resolving to a
    different source token per theme. Defining it in the theme-independent
    utilities layer would give it one flat value decided by import order, and
    the side that loses is dark mode — which this project treats as the
    default rather than a preference.
    """
    # Arrange
    theme_files = sorted((_PRIMITIVES / "colors").glob("_*.css"))
    # Act
    owners = [p.name for p in theme_files if "--border-color" in _declared_in(p)]
    # Assert
    assert len(owners) == len(theme_files) and "--border-color" not in _declared_in(
        _EFFECTS
    ), (
        "--border-color must be defined by EVERY theme file in primitives/"
        f"colors/ and by no other layer. Theme files: "
        f"{[p.name for p in theme_files]}; those defining it: {owners}. "
        "A theme that omits it inherits the other theme's border, and a copy "
        "in utilities/effects.css overrides both."
    )


def test_variables_css_imports_the_effects_utilities() -> None:
    """Item 3 of the convergence: both variables.css files carry this line."""
    # Arrange
    text = _VARIABLES.read_text(errors="replace")
    # Act
    present = _IMPORT_LINE in text
    # Assert
    assert present, (
        f"{_VARIABLES} must contain the line\n\n    {_IMPORT_LINE}\n\n"
        "scitex-hub's variables.css carries it verbatim. The two files converge "
        "by both containing it, not by hub deleting theirs — removing it here "
        "would re-fork the layer and drop --border-width from every consumer."
    )
