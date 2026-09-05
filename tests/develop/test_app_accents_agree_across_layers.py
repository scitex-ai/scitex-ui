#!/usr/bin/env python3
"""Both palette-carrying layers must declare the SAME app accents.

`primitives/colors/` and `shell/theme.css` each carry a copy of the palette, and
THAT DUPLICATION IS DELIBERATE — it is what makes `shell/theme.css` consumable
on its own. The package documents that contract in several places:

    css/app/context-menu.css   "Requires: shell/theme.css - and ONLY that."
    css/app/reply-quote.css    "Requires: shell/theme.css (tokens only - no
                                shell adoption needed)"
    _skills/.../20_css-theme.md   offers theme.css as a standalone <link>

So a page may link `shell/theme.css` alone and never see the primitives layer.
Removing a token from theme.css because "it is already in colors/" breaks every
such page, silently.

THE PACKAGE HAS ALREADY SHIPPED THAT BUG ONCE. From
`tests/develop/test_app_css_text_link_token.py`:

    "a page linking only shell/theme.css never sees primitives/colors.css, and
     defining it in one place only is the exact defect that made the context
     menu render dark-grey-on-dark (0.12.1)."

I RE-CREATED IT AND CI CAUGHT ME. Measured 2026-08-18: the two layers disagreed
— `comms`, `storage` and `todo` were in theme.css only, `apps` in colors/ only —
and I read that as duplication to be consolidated. I moved everything into
colors/ and stripped theme.css. `test_branding.py::
test_every_referenced_accent_token_is_declared` went red, because it reads
declarations from theme.css and the sidebar's mapping rows still referenced 17
tokens that no longer existed there.

THE DEFECT WAS NEVER THE DUPLICATION. It was that the duplication was
INCOMPLETE. Two layers that both carry the palette is the design; two layers
that carry DIFFERENT palettes is the bug, and it is the bug that left
scitex-hub's `comms` tile with no accent bar — hub loads the primitives layer,
which lacked the token theme.css had.

So this guard asserts AGREEMENT, not exclusivity. Adding an accent means adding
it to both layers, in both palettes. That is more typing than a single
definition and it is the price of theme.css standing alone; the guard is what
stops the copies drifting apart again.

WHAT IT DOES NOT COVER: whether an accent NAME an app declares actually exists.
The consumer is a manifest string in another package (`"accent_color": "comms"`),
not a `var()` call, so no search of this repo can see it. That is exactly why
hub's own `var(--app-accent-storage` search came back empty while a real
consumer existed — the control proved the search RAN, not that it asked the
right question.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# Resolved from THIS FILE, not from ``scitex_ui.__file__``: the latter points at
# site-packages under a non-editable install, so the guard would assert about a
# different tree than the branch under review. PR #152 introduces a shared
# ``tests._checkout`` helper; switch to it once that lands.
_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
)

_COLORS = _CSS / "primitives" / "colors"
_THEME = _CSS / "shell" / "theme.css"

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_DECL = re.compile(r"^\s*--app-accent-([a-z0-9-]+)\s*:", re.M)

#: The bare brand accent, WITH ITS VALUE. Capturing the value is the whole
#: correction: the previous guard matched `^\s*--accent\s*:` and counted hits,
#: which cannot see what a declaration says or which block it sits in.
_BARE_ACCENT = re.compile(r"^\s*--accent\s*:\s*([^;]+);", re.M)

#: A block opener. Only `[data-theme="dark"]` is treated as dark; everything
#: else (`:root`, `[data-theme="light"]`) is light, which is this repo's
#: convention — dark is always explicitly attributed, light is the default.
_BLOCK_OPEN = re.compile(r"([^{}]*)\{", re.S)


def _bare_accent_by_block(text: str) -> dict[str, str]:
    """Map "light"/"dark" to the ``--accent`` value declared in that block.

    A block that declares it TWICE keeps the last value, matching the cascade.
    A block that declares it not at all is absent from the mapping, which is
    what makes "declared in the dark block" assertable rather than inferred
    from a count.
    """
    stripped = _CSS_COMMENT.sub("", text)
    found: dict[str, str] = {}
    for match in _BLOCK_OPEN.finditer(stripped):
        selector = match.group(1)
        kind = "dark" if 'data-theme="dark"' in selector else "light"
        end = stripped.find("}", match.end())
        body = stripped[match.end() : end if end != -1 else len(stripped)]
        for value in _BARE_ACCENT.findall(body):
            found[kind] = value.strip()
    return found

#: Current-app STATE assigned at render time by ``[data-app-accent="x"]``, not
#: per-app palette entries.
_STATE = {"color", "tint"}


def _accent_names(text: str) -> set[str]:
    """Per-app accent names declared in one stylesheet's text."""
    stripped = _CSS_COMMENT.sub("", text)
    names = set(_DECL.findall(stripped))
    return {n[: -len("-tint")] if n.endswith("-tint") else n for n in names} - _STATE


def _theme_names() -> set[str]:
    return _accent_names(_THEME.read_text(errors="replace"))


def _colors_names() -> set[str]:
    names: set[str] = set()
    for path in sorted(_COLORS.glob("*.css")):
        names |= _accent_names(path.read_text(errors="replace"))
    return names


def test_both_layers_declare_some_accents() -> None:
    """ANTI-VACUITY: two empty sets are equal, and that must not read as a pass.

    AN AGREEMENT-SHAPED CHECK FAILS OPEN; AN EXISTENCE-SHAPED ONE FAILS SAFE.
    That distinction is why this test carries more weight here than the same
    boilerplate does elsewhere, and it is worth stating rather than assuming:

        existence  ("token X is declared")     a broken scan finds nothing,
                                               the assertion fails, and the red
                                               is loud. Wrong reason, right
                                               colour.
        agreement  ("both layers match")       a broken scan finds nothing on
                                               BOTH sides, the sets are equal,
                                               and the check goes GREEN while
                                               having measured nothing at all.

    So the population assertion below is not defensive boilerplate — it is the
    only thing standing between "measured and agreed" and "did not measure".
    Skip it on an existence check and you get a confusing failure; skip it here
    and you get a silent pass.

    (Named by scitex-hub, comparing this guard against their own existence-shaped
    one during the same review.)
    """
    # Arrange
    theme, colors = _theme_names(), _colors_names()
    # Act
    smaller = min(len(theme), len(colors))
    # Assert
    assert smaller > 10, (
        f"theme.css declared {len(theme)} accent names and the colors layer "
        f"{len(colors)}; at least one scan did not run, so the agreement check "
        "below would prove nothing"
    )


def test_the_two_palette_layers_declare_the_same_accents() -> None:
    """Neither layer may carry an accent the other lacks."""
    # Arrange
    theme, colors = _theme_names(), _colors_names()
    # Act
    only_theme, only_colors = theme - colors, colors - theme
    # Assert
    if only_theme or only_colors:
        pytest.fail(
            "the two palette layers disagree, so which accents an adopter gets "
            "depends on which stylesheet they happen to load:\n"
            f"  only in shell/theme.css     {sorted(only_theme) or '-'}\n"
            f"  only in primitives/colors/  {sorted(only_colors) or '-'}\n\n"
            "Both layers carry the palette ON PURPOSE — theme.css is documented "
            "as consumable alone (see css/app/context-menu.css). So the fix is "
            "to ADD the missing names to the layer that lacks them, in BOTH "
            "palettes.\n\nDo NOT 'de-duplicate' by deleting from one side: that "
            "is how scitex-hub's comms tile lost its accent bar, and how the "
            "context menu rendered dark-grey-on-dark in 0.12.1."
        )


def test_the_bare_accent_token_is_in_both_layers() -> None:
    """`--accent` is a palette token and must honour the same contract.

    IT DID NOT, AND THE ACCENT-FAMILY CHECKS ABOVE MISS IT. They match
    ``--app-accent-<name>``; the brand accent is the bare ``--accent``, a
    different token, so scoping this file to the family left the one token an
    app is most likely to want outside it.

    Found by scitex-scholar, who grepped the INSTALLED 0.15.0 wheel before
    adopting and got zero. Measured here on the tree: --text-link, --bg-surface
    and --text-primary are each declared in BOTH layers; --accent was declared
    only in primitives/colors/, while ``css/app/combobox.css`` consumes
    ``var(--accent)`` at three sites. So an app taking the documented
    theme.css-alone path rendered that accent as nothing — silently, because an
    undefined custom property resolves to nothing rather than erroring.

    Same defect as the comms tile, one token family over. Which is the argument
    for this test existing rather than the fix being enough: I fixed the family
    I was looking at and left the sibling, and only someone checking a shipped
    artifact for a different reason noticed.

    THE COUNT THIS TEST USED TO DO WAS THE WRONG PREDICATE, and scitex-hub
    found it by EXECUTING the regex against constructed fixtures rather than
    reading it. `^\\s*--accent\\s*:` counted >= 2 hits in theme.css, capturing
    no value and no block context, so all three of these passed GREEN:

        the shipped shape                                 correct
        dark copied the light literal                     the 2.71:1 regression
        dark block has NO --accent; light declares twice   a missing token

    And `_dark.css` was never opened at all, so the bare --accent there was
    guarded by NOTHING.

    The defect being guarded is an AGREEMENT defect — light-to-light and
    dark-to-dark, across two files. The changelog in the same PR explained that
    an agreement check fails OPEN while an existence check fails SAFE. I wrote
    that distinction in prose and then shipped the existence check. This is the
    agreement check it was documented to be; the assertions live in the
    per-block tests below, and this one keeps the history.
    """
    # Arrange
    theme = _THEME.read_text(errors="replace")
    # Act
    blocks = _bare_accent_by_block(theme)
    # Assert -- both blocks present. Value agreement is asserted separately.
    assert set(blocks) == {"light", "dark"}, (
        f"shell/theme.css declares the bare --accent in blocks {sorted(blocks)}; "
        "expected both light and dark. theme.css is documented as consumable "
        "alone and app/combobox.css reads var(--accent) at three sites, so a "
        "token missing from either block renders as nothing for any app taking "
        "that path."
    )


def test_the_dark_primitives_file_declares_the_bare_accent() -> None:
    """ANTI-VACUITY for the two agreement tests below.

    `_dark.css` was opened by no test in this module before today, so a
    comparison against it could have been comparing against nothing.
    """
    # Arrange
    dark_text = (_COLORS / "_dark.css").read_text(errors="replace")
    # Act
    blocks = _bare_accent_by_block(dark_text)
    # Assert
    assert "dark" in blocks


def test_theme_light_accent_matches_the_primitives_light_value() -> None:
    """Same token, two layers, one value — or an app sees a different accent
    depending on which stylesheet it linked."""
    # Arrange
    theme = _bare_accent_by_block(_THEME.read_text(errors="replace"))
    primitives = _bare_accent_by_block(
        (_COLORS / "_light.css").read_text(errors="replace")
    )
    # Act
    pair = (theme.get("light"), primitives.get("light"))
    # Assert
    assert pair[0] == pair[1], (
        f"--accent in the light block is {pair[0]!r} in shell/theme.css and "
        f"{pair[1]!r} in primitives/colors/_light.css. Both are shipped and "
        "either can be linked alone, so they must agree."
    )


def test_theme_dark_accent_matches_the_primitives_dark_value() -> None:
    # Arrange
    theme = _bare_accent_by_block(_THEME.read_text(errors="replace"))
    primitives = _bare_accent_by_block(
        (_COLORS / "_dark.css").read_text(errors="replace")
    )
    # Act
    pair = (theme.get("dark"), primitives.get("dark"))
    # Assert
    assert pair[0] == pair[1], (
        f"--accent in the dark block is {pair[0]!r} in shell/theme.css and "
        f"{pair[1]!r} in primitives/colors/_dark.css."
    )


def test_the_two_palettes_do_not_collapse_onto_one_accent() -> None:
    """THE 2.71:1 REGRESSION, asserted directly.

    #6d4cad measures 2.71:1 against the dark surface and two of the three
    `var(--accent)` sites in app/combobox.css are `color:`. So the tidy-up that
    unifies the palettes onto the light literal reintroduces a WCAG AA failure
    on the theme the operator actually uses. The old count could not see it.
    """
    # Arrange
    blocks = _bare_accent_by_block(_THEME.read_text(errors="replace"))
    # Act
    collapsed = blocks.get("light") == blocks.get("dark")
    # Assert
    assert collapsed is False, (
        f"both palettes declare --accent as {blocks.get('light')!r}. No single "
        "value clears AA on both surfaces: #6d4cad is 5.97:1 on light and "
        "2.71:1 on dark; #a371f7 is 5.16:1 on dark."
    )


class TestTheDetectorItself:
    """Literal-sample controls for `_BARE_ACCENT`, both directions."""

    def test_it_captures_a_value(self):
        """POSITIVE control: the previous predicate matched without capturing,
        which is exactly what made it blind."""
        # Arrange
        sample = "  --accent: #6d4cad;\n"
        # Act
        matched = _BARE_ACCENT.search(sample)
        # Assert
        assert matched.group(1).strip() == "#6d4cad"

    def test_it_ignores_a_longer_token_that_starts_the_same(self):
        """NEGATIVE control: `--accent-color` is a DIFFERENT token, and the
        bare-accent check must not claim it. A hyphen is a word character, so
        a `\\b`-based pattern would absorb it — that exact mistake inflated a
        finding to 55 files on 2026-08-05."""
        # Arrange
        sample = "  --accent-color: #f00;\n"
        # Act
        matched = _BARE_ACCENT.search(sample)
        # Assert
        assert matched is None

    def test_the_block_pattern_captures_a_selector(self):
        """POSITIVE control for `_BLOCK_OPEN`."""
        # Arrange
        sample = '[data-theme="dark"] {\n'
        # Act
        matched = _BLOCK_OPEN.search(sample)
        # Assert
        assert matched.group(1).strip() == '[data-theme="dark"]'

    def test_the_block_pattern_ignores_a_declaration_with_no_brace(self):
        """NEGATIVE control: a declaration line is not a block opener.

        Without this, a pattern that matched every line would still satisfy the
        positive control above and would attribute every declaration to a
        block of its own — which is the presence-not-placement failure this
        whole change exists to fix, reintroduced inside its own fix."""
        # Arrange
        sample = "  --accent: #6d4cad;\n"
        # Act
        matched = _BLOCK_OPEN.search(sample)
        # Assert
        assert matched is None


class TestHubsFixturesGoRed:
    """The three shapes that passed the old count must now fail.

    These are hub's constructed fixtures from the PR #156 review, kept verbatim
    in spirit: they are the specification for this guard, so they are asserted
    rather than described.
    """

    def test_dark_copying_the_light_literal_is_rejected(self):
        # Arrange
        sample = (
            '[data-theme="light"] { --accent: #6d4cad; }\n'
            '[data-theme="dark"] { --accent: #6d4cad; }\n'
        )
        # Act
        blocks = _bare_accent_by_block(sample)
        # Assert -- identical values, which the collapse test forbids
        assert blocks["light"] == blocks["dark"]

    def test_two_declarations_in_the_light_block_leave_dark_absent(self):
        # Arrange
        sample = (
            '[data-theme="light"] { --accent: #6d4cad; --accent: #7744aa; }\n'
            '[data-theme="dark"] { --bg: #000; }\n'
        )
        # Act
        blocks = _bare_accent_by_block(sample)
        # Assert -- the old count saw 2 and passed; the block map sees no dark
        assert "dark" not in blocks

    def test_the_shipped_shape_is_accepted(self):
        """The control that makes the two rejections meaningful."""
        # Arrange
        sample = (
            '[data-theme="light"] { --accent: #6d4cad; }\n'
            '[data-theme="dark"] { --accent: #a371f7; }\n'
        )
        # Act
        blocks = _bare_accent_by_block(sample)
        # Assert
        assert blocks == {"light": "#6d4cad", "dark": "#a371f7"}


def test_light_and_dark_declare_the_same_accents() -> None:
    """A name in one palette only is a silent theme-specific hole."""
    # Arrange
    light = _accent_names((_COLORS / "_light.css").read_text(errors="replace"))
    dark = _accent_names((_COLORS / "_dark.css").read_text(errors="replace"))
    # Act
    only_one = (light - dark) | (dark - light)
    # Assert
    assert not only_one, (
        "these accents are declared in one palette but not the other, so the "
        "app loses its accent in whichever theme lacks it, with no error: "
        f"{sorted(only_one)}"
    )
