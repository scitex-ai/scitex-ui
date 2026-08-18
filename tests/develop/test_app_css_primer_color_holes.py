#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The Primer `--color-*` names our components consume must be DEFINED.

``primitives/colors.css`` ships a "GitHub Primer-style aliases" block of 29
tokens that re-point Primer names onto this palette's own semantics. Six names
our stylesheets actually consume were missing from it, so each rendered the
literal fallback written at its call site — a Primer DARK hex — under BOTH
palettes. Measured against the light ``--bg-surface`` (#f8f7f5):

    --color-attention-fg      #d29922   2.36:1     AA for normal text is 4.5:1
    --color-done-fg           #a371f7   3.13:1
    --color-success-emphasis  #2ea043   3.15:1

That is the same defect ``test_app_css_text_link_token.py`` pins: below AA by
construction, and unfixable by any theme because the value lived at the call
sites rather than in a palette.

FIVE of the six are fixed here. The sixth, ``--color-accent-muted``, is left
undefined deliberately and ``test_accent_muted_is_left_undefined_on_purpose``
records why: its four call sites carry THREE different fallbacks, so no single
definition preserves what renders today. That is the ``--border-subtle``
situation, and it needs eyes rather than arithmetic.

Two properties carry the change, as in the ``--text-link`` guard:

1. The DARK value equals the historical fallback, so the default theme is
   provably unchanged and this could ship without a screenshot of it.
2. The LIGHT value clears AA on the surface it sits on. Contrast is
   arithmetic, so it is a test rather than a review comment — and the
   "tidy-up" that collapses the two palettes onto one hex would silently
   restore the failure this fixes.

Scope note, so a future reader does not read an omission as a bug: unlike
``--text-link``, these are NOT added to ``shell/theme.css``. That file carries
no ``--color-*`` token at all, and every consuming stylesheet lives under
``css/app/``, which reaches ``primitives/colors.css`` through both ``app.css``
and ``all.css``. Introducing a lone Primer family into theme.css would be a new
structural decision, not the filling of a hole.
"""

import re

import pytest

from tests._checkout import css_dir

from . import _css_palette

_CSS = css_dir()
_COLORS = "primitives/colors.css"

#: token -> the literal every one of its call sites already rendered.
_HISTORICAL_FALLBACK = {
    "--color-attention-fg": "#d29922",
    "--color-done-fg": "#a371f7",
    "--color-canvas-overlay": "#2d333b",
    "--color-success-emphasis": "#2ea043",
    "--color-success-subtle": "rgba(46, 160, 67, 0.2)",
}

#: The subset used as a foreground, i.e. where legibility is arithmetic.
#: --color-canvas-overlay is a surface and --color-success-subtle an alpha
#: wash; neither has a meaningful contrast ratio of its own.
_FOREGROUND_TOKENS = (
    "--color-attention-fg",
    "--color-done-fg",
    "--color-success-emphasis",
)

_LIGHT_SURFACE = "#f8f7f5"
_DARK_SURFACE = "#161b22"
_AA_NORMAL_TEXT = 4.5


#: The WCAG arithmetic was byte-identical in three files; it now lives once.
#: `_declared` and `_resolve` below are DELIBERATELY not shared — this file
#: takes the LAST declaration and matches unanchored, the sibling file takes the
#: FIRST and anchors to line start. Those are different rules, each probed
#: against its own tests, and collapsing them here would silently re-decide one.
_contrast = _css_palette.contrast


def _palette_blocks() -> tuple[str, str]:
    """The light and dark halves of colors.css, split at the dark selector.

    Reads through `@import`, so this keeps working when colors.css becomes a
    barrel over per-palette parts instead of one flat file.
    """
    text = _css_palette.inline_imports(_CSS / _COLORS)
    marker = '[data-theme="dark"]'
    assert marker in text, f"{_COLORS} no longer has a {marker} block"
    light, dark = text.split(marker, 1)
    return light, dark


def _declared(block: str, token: str) -> str | None:
    """The value ``token`` is DECLARED with in one palette block.

    Matches the declaration (``--x:``) and never a ``var(--x)`` consumption, so
    a block that merely reads the token cannot satisfy a test asking whether it
    defines it.
    """
    found = re.findall(rf"{re.escape(token)}\s*:\s*([^;]+);", block)
    return found[-1].strip() if found else None


def _resolve(block: str, value: str) -> str:
    """Resolve one level of ``var(--x)`` against the same palette block.

    The light values are aliases onto this palette's own semantics, so the hex
    that actually renders is one hop away. Asserting on the resolved value
    measures what a user sees rather than what the file happens to spell.
    """
    match = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", value.strip())
    if not match:
        return value.strip()
    inner = _declared(block, match.group(1))
    assert inner is not None, f"{value} points at a token {_COLORS} does not define"
    return _resolve(block, inner)


# ─────────────────────────── the tokens exist at all ────────────────────────


@pytest.mark.parametrize("token", sorted(_HISTORICAL_FALLBACK))
def test_both_palettes_define_the_token(token: str) -> None:
    # Arrange
    light_block, dark_block = _palette_blocks()
    # Act
    light, dark = _declared(light_block, token), _declared(dark_block, token)
    # Assert
    assert light and dark, (
        f"{token} is declared in light={light!r} dark={dark!r}; a token missing "
        "from one palette falls back to its call-site literal in that theme, "
        "which is the defect this file exists to close"
    )


@pytest.mark.parametrize("token", sorted(_HISTORICAL_FALLBACK))
def test_call_sites_keep_their_fallback(token: str) -> None:
    # Arrange — a bare var() would render nothing if the token were ever
    # removed again; the fallbacks stay as the safety net.
    bare = []
    for css in sorted(_CSS.rglob("*.css")):
        for lineno, line in enumerate(css.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"var\(\s*{re.escape(token)}\s*\)", line):
                bare.append(f"{css.relative_to(_CSS)}:{lineno}")
    # Act
    offenders = ", ".join(bare)
    # Assert
    assert bare == [], f"var({token}) with no fallback at {offenders}"


# ──────────────────── the dark no-op, which is load-bearing ─────────────────


@pytest.mark.parametrize("token,fallback", sorted(_HISTORICAL_FALLBACK.items()))
def test_dark_value_is_the_historical_fallback(token: str, fallback: str) -> None:
    # Arrange — introducing these tokens must not change the DEFAULT theme, and
    # this equality is the entire evidence for that claim.
    _, dark_block = _palette_blocks()
    # Act
    dark = _resolve(dark_block, _declared(dark_block, token) or "")
    # Assert
    assert dark.lower().replace(" ", "") == fallback.lower().replace(" ", ""), (
        f"dark {token} is {dark!r}, not the {fallback!r} its call sites already "
        "rendered — that makes this a visual change to the default theme, which "
        "needs eyes rather than a test"
    )


@pytest.mark.parametrize("token", sorted(_HISTORICAL_FALLBACK))
def test_the_two_palettes_do_not_share_one_value(token: str) -> None:
    # Arrange — the "tidy-up" that breaks this. The dark hexes measure 2.36,
    # 3.13 and 3.15 on the light surface, so collapsing the palettes onto one
    # value necessarily reintroduces the failure.
    light_block, dark_block = _palette_blocks()
    # Act
    light = _resolve(light_block, _declared(light_block, token) or "")
    dark = _resolve(dark_block, _declared(dark_block, token) or "")
    # Assert
    assert light.lower() != dark.lower(), (
        f"light and dark {token} are both {light!r}; one value cannot serve a "
        "warm-white and a near-black surface"
    )


# ─────────────────────────── legibility, as arithmetic ──────────────────────


@pytest.mark.parametrize("token", _FOREGROUND_TOKENS)
def test_light_value_clears_aa_on_the_light_surface(token: str) -> None:
    # Arrange — the defect being fixed; these read 2.36:1, 3.13:1, 3.15:1.
    light_block, _ = _palette_blocks()
    # Act
    light = _resolve(light_block, _declared(light_block, token) or "")
    ratio = _contrast(light, _LIGHT_SURFACE)
    # Assert
    assert ratio >= _AA_NORMAL_TEXT, (
        f"light {token} resolves to {light} — {ratio:.2f}:1 on {_LIGHT_SURFACE}, "
        f"below AA {_AA_NORMAL_TEXT}:1"
    )


@pytest.mark.parametrize("token", _FOREGROUND_TOKENS)
def test_dark_value_clears_aa_on_the_dark_surface(token: str) -> None:
    # Arrange — pairs with the above so neither palette can be improved by
    # breaking the other.
    _, dark_block = _palette_blocks()
    # Act
    dark = _resolve(dark_block, _declared(dark_block, token) or "")
    ratio = _contrast(dark, _DARK_SURFACE)
    # Assert
    assert ratio >= _AA_NORMAL_TEXT, (
        f"dark {token} is {dark} — {ratio:.2f}:1 on {_DARK_SURFACE}, below AA "
        f"{_AA_NORMAL_TEXT}:1"
    )


@pytest.mark.parametrize("token", _FOREGROUND_TOKENS)
def test_the_contrast_helper_can_actually_fail(token: str) -> None:
    # Arrange — a positive control per token. A helper that returned a large
    # number unconditionally would make every assertion above vacuous, and the
    # known-bad pairing is exactly the one this change removes.
    fallback = _HISTORICAL_FALLBACK[token]
    # Act
    ratio = _contrast(fallback, _LIGHT_SURFACE)
    # Assert
    assert ratio < _AA_NORMAL_TEXT, (
        f"the known-bad pairing ({fallback} on {_LIGHT_SURFACE}) must measure "
        f"BELOW AA; got {ratio:.2f}:1, so the helper is not discriminating"
    )


# ───────────────── the one that is deliberately NOT fixed ───────────────────


def _accent_muted_fallbacks() -> set[str]:
    """Every distinct fallback written at a ``--color-accent-muted`` call site."""
    pattern = re.compile(r"var\(\s*--color-accent-muted\s*,\s*([^)]*\)?[^)]*)\)")
    found = set()
    for css in sorted(_CSS.rglob("*.css")):
        for match in pattern.finditer(css.read_text(encoding="utf-8")):
            found.add(match.group(1).strip().lower().replace(" ", ""))
    return found


def test_accent_muted_call_sites_still_disagree() -> None:
    # Arrange — this disagreement IS the reason the sixth hole is left open:
    # no single definition can preserve what every site renders today.
    expected_minimum = 2
    # Act
    fallbacks = _accent_muted_fallbacks()
    # Assert
    assert len(fallbacks) >= expected_minimum, (
        f"--color-accent-muted now has one agreed fallback ({fallbacks}) — the "
        "reason for leaving it undefined has gone, so define it alongside the "
        "other five"
    )


def test_accent_muted_is_left_undefined_on_purpose() -> None:
    # Arrange — defining it is not a lint fix but a visual change at four
    # sites. Pinned so the next reader does not "finish the job" by guessing.
    light_block, dark_block = _palette_blocks()
    # Act
    defined = _declared(light_block, "--color-accent-muted") or _declared(
        dark_block, "--color-accent-muted"
    )
    # Assert
    assert defined is None, (
        f"--color-accent-muted is defined as {defined!r} while its call sites "
        f"still disagree about what they render "
        f"({sorted(_accent_muted_fallbacks())}); pick the value with a "
        "screenshot, not with this test green by accident"
    )
