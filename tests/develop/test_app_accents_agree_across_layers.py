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

    Without this, a wrong path or a broken regex yields empty sets on both
    sides, the equality below holds trivially, and the suite reports the palette
    consistent. "Measured and agreed" and "did not measure" would be the same
    green, which is the failure mode this whole file exists to prevent.
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
