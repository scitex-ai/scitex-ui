#!/usr/bin/env python3
"""Guards the token contract of `css/app/*.css`.

TWO SEPARATE CLAIMS, because conflating them is what shipped the bug:

1. Every custom property an app stylesheet consumes must be DEFINED BY SOME
   SHIPPED LAYER. A token defined nowhere silently becomes its hardcoded
   fallback forever — it can never follow the theme — which is invisible until
   it lands next to a token that does follow it.

2. The stylesheets a consumer is told to cherry-pick ALONGSIDE ONLY
   `shell/theme.css` must consume only tokens theme.css defines.

Claim 2 is the one that bit. `context-menu.css` promised `Requires:
shell/theme.css`, and I repeated that to scitex-cards as sufficient. It also
read `--bg-secondary`, which lives in `primitives/colors.css`. So on their page:

    --text-secondary   resolved via theme.css and followed the theme
    --bg-secondary     resolved to nothing, took a hardcoded dark literal,
                       and could never follow the theme

In the light palette those collide into dark-grey-on-dark. The operator's live
chat showed a context menu that looked disabled and clicked fine.

WHAT THIS GUARD DELIBERATELY DOES NOT CLAIM: that every app stylesheet works
under theme.css alone. Measured 2026-07-28 — 17 of them legitimately consume
the primitives layer (`--border-subtle`, `--status-*`, `--workspace-bg-*`,
`--text-dimmed`, `--text-link`), and `app.css` does NOT import that layer while
`all.css` does. So an adopter linking `app.css` alone has partially-unresolved
tokens across 17 components. That is a real finding and it is CARDED, not
papered over here: asserting a contract the repo does not hold would make this
guard red on arrival, and a red guard gets disabled rather than obeyed.
"""

from __future__ import annotations

import pathlib
import re

import pytest

import scitex_ui
from tests._checkout import css_dir

_CSS = css_dir()
_THEME = _CSS / "shell" / "theme.css"
_APP = _CSS / "app"

# Opt-in overrides: consumed with a documented default, defined by the ADOPTER
# only if they want to change it. Absence is the designed state, not a gap.
_ADOPTER_OVERRIDES = {"--stx-context-menu-z"}

# Components documented as consumable with theme.css ALONE — the cherry-pick
# path handed to adopters who do not want the whole bundle. These must not
# reach into another layer.
_THEME_ONLY = {"context-menu.css", "attachment.css"}


def _defined_in(text: str) -> set[str]:
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", text))


def _consumed_by(path: pathlib.Path) -> set[str]:
    return set(re.findall(r"var\((--[a-z0-9-]+)", path.read_text()))


def _all_shipped_tokens() -> set[str]:
    tokens: set[str] = set()
    for css in _CSS.rglob("*.css"):
        tokens |= _defined_in(css.read_text())
    return tokens | _ADOPTER_OVERRIDES


def _app_stylesheets() -> list[pathlib.Path]:
    return sorted(_APP.rglob("*.css"))


def test_token_extraction_is_not_vacuous():
    # Arrange
    # Act
    tokens = _all_shipped_tokens()
    # Assert
    assert len(tokens) > 100, (
        f"only {len(tokens)} tokens parsed across the CSS tree; the extraction "
        f"drifted and every check below would pass over an empty set"
    )


def test_theme_only_set_matches_real_files():
    # Arrange
    names = {p.name for p in _app_stylesheets()}
    # Act
    missing = sorted(_THEME_ONLY - names)
    # Assert
    assert not missing, f"_THEME_ONLY names {missing}, which no longer ship"


@pytest.mark.parametrize("name", sorted(_THEME_ONLY))
def test_theme_only_components_have_no_undefined_tokens(name):
    """The narrow version of claim 1, scoped to what this PR actually fixed.

    The REPO-WIDE version is red on arrival: measured 2026-07-28, 15 app
    stylesheets consume tokens defined in NO shipped stylesheet at all —
    `--text-link` and `--border-subtle` among them — so those render their
    hardcoded fallback forever. That is a real pre-existing defect of the same
    class, and it is CARDED with the measurement rather than fixed in a rush
    here. Shipping the wide assertion red would just get the guard disabled.
    """
    # Arrange
    shipped = _all_shipped_tokens()
    # Act
    undefined = sorted(_consumed_by(_APP / name) - shipped)
    # Assert
    assert not undefined, (
        f"{name} consumes {undefined}, which NO shipped stylesheet defines. "
        f"Those can only ever render as their hardcoded fallback, so they never "
        f"follow the theme — and next to a token that does, they collide."
    )


@pytest.mark.parametrize("name", sorted(_THEME_ONLY))
def test_theme_only_components_need_only_theme(name):
    # Arrange
    theme_tokens = _defined_in(_THEME.read_text()) | _ADOPTER_OVERRIDES
    sheet = _APP / name
    # Act
    beyond = sorted(_consumed_by(sheet) - theme_tokens)
    # Assert
    assert not beyond, (
        f"{name} is documented as consumable with shell/theme.css alone, but "
        f"consumes {beyond} from another layer. An adopter following that "
        f"header gets the hardcoded fallback for these and the themed value "
        f"for the rest — exactly how the context menu rendered dark-on-dark on "
        f"a live page. Use a theme.css token, or stop advertising theme-only."
    )


# EOF
