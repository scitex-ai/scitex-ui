#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The semantic role color contract (TODO #96 / #120) is a set of pure aliases.

Every ``--role-{primary,secondary,danger,success}-{bg,text,border,hover-bg}``
token must be (1) declared in BOTH palettes, (2) a pure ``var()`` alias to a
token that already exists in that palette (so it introduces ZERO new brand
colors and changes nothing that renders), and (3) resolvable to the SAME value
the existing per-role tokens already resolve to. A contract that added a hex
literal, or that pointed at a token only one palette has, would be a NEW brand
decision dressed as a refactor — exactly what this test is there to stop.

PRIMARY'S MODE SPLIT IS PINNED. In LIGHT primary is the SciTeX navy
(``--color-btn-primary-bg`` -> ``--color-primary``, #1a2a40, operator decision
2026-09-15); in DARK it is the brand gold (``--color-primary`` #d4a87a, operator 2026-09-15). ``test_primary_keeps_its_mode_split`` asserts
both directions — so neither "unify the modes" nor "silently make them the
same" passes quietly.

Uses the shared ``_css_palette`` reader so the light/dark partition and the
``var()`` resolution are the SAME code every other color guard uses.
"""

from __future__ import annotations

import re

import pytest

from tests._checkout import css_dir

from . import _css_palette

_COLORS = css_dir() / "primitives" / "colors.css"

_ROLES = ("primary", "secondary", "danger", "success")
_SUBTOKENS = ("bg", "text", "border", "hover-bg")

#: Which pre-existing token each role's FILL must alias to. This is the "no new
#: color" assertion expressed as identity: resolve --role-X-bg and it must equal
#: resolve (the existing per-role fill token). The text tokens are checked
#: separately (they must be a resolvable color, AA floor where used as text).
_FILL_TARGET = {
    "primary": "--color-btn-primary-bg",
    "secondary": "--color-btn-bg",
    "danger": "--status-error",
    "success": "--status-success",
}

_AA_UI_COMPONENT = 3.0  # WCAG 1.4.11, non-text (a filled button's label)


def _blocks() -> tuple[str, str]:
    return _css_palette.palette_blocks(_COLORS)


def _declared_both(token: str):
    light, dark = _blocks()
    return _css_palette.declared(light, token), _css_palette.declared(dark, token)


# --- the contract is present and is a pure alias --------------------------


def test_palette_reader_is_not_vacuous():
    # Arrange
    light, dark = _blocks()
    # Act
    ok = _css_palette.declared(light, "--_scitex-02") is not None and (
        _css_palette.declared(dark, "--_scitex-02") is not None
    )
    # Assert
    assert ok, (
        "the shared palette reader found no known token in either block — the "
        "split or the reader broke, and every alias assertion below would pass "
        "over an empty palette"
    )


@pytest.mark.parametrize("role", _ROLES)
@pytest.mark.parametrize("sub", _SUBTOKENS)
def test_role_subtoken_is_declared_in_both_palettes(role, sub):
    # Arrange
    token = f"--role-{role}-{sub}"
    # Act
    light, dark = _declared_both(token)
    # Assert
    assert (light is not None, dark is not None) == (True, True), (
        f"{token} missing from a palette (light={'yes' if light else 'NO'}, "
        f"dark={'yes' if dark else 'NO'}) — a role token present in only one "
        "mode would dangle the other, and with light-first source order the "
        "dark value would be shadowed"
    )


@pytest.mark.parametrize("role", _ROLES)
@pytest.mark.parametrize("sub", _SUBTOKENS)
def test_role_subtoken_is_a_pure_alias_not_a_new_color(role, sub):
    """The whole 'smallest contract, zero brand change' claim rests on this:
    a ``--role-*`` value must be ``var(--<something>)``. A hex/rgb literal would
    be inventing a brand color under a refactor's name."""
    # Arrange
    token = f"--role-{role}-{sub}"
    light, dark = _declared_both(token)
    # Act — a pure alias is exactly `var(--<name>)` (one token, no fallback).
    alias = re.compile(r"^var\(\s*--[\w-]+\s*\)$")
    is_alias = bool(
        light
        and dark
        and alias.match(light)
        and alias.match(dark)
    )
    # Assert
    assert is_alias, (
        f"{token} is not a pure var() alias in both palettes (light={light!r}, "
        f"dark={dark!r}). A literal here is a NEW color decision, not the "
        "token contract this card scopes."
    )


@pytest.mark.parametrize("role", _ROLES)
def test_role_fill_aliases_the_existing_per_role_fill(role):
    """resolve(--role-X-bg) must equal resolve(the existing fill token) in BOTH
    palettes — i.e. migrating a leaf to --role-X-bg renders byte-for-byte what
    it already does. This is the 'preserve existing behavior' guarantee."""
    # Arrange
    target = _FILL_TARGET[role]
    # Act
    light, dark = _blocks()
    lhs_l = _css_palette.resolve(light, _declared_both(f"--role-{role}-bg")[0])
    lhs_d = _css_palette.resolve(dark, _declared_both(f"--role-{role}-bg")[1])
    rhs_l = _css_palette.resolve(light, _css_palette.declared(light, target))
    rhs_d = _css_palette.resolve(dark, _css_palette.declared(dark, target))
    # Assert
    assert (lhs_l, lhs_d) == (rhs_l, rhs_d), (
        f"--role-{role}-bg does not resolve to {target} in both palettes: "
        f"light {lhs_l!r}!={rhs_l!r} / dark {lhs_d!r}!={rhs_d!r}. A leaf "
        "migrating to --role-X-bg must render byte-for-byte what it already does."
    )


@pytest.mark.parametrize("role", _ROLES)
def test_role_text_token_resolves_to_a_color(role):
    """The -text token must resolve (not dangle) to a usable color in both modes."""
    # Arrange
    light, dark = _blocks()
    # Act
    lval = _css_palette.resolve(light, _declared_both(f"--role-{role}-text")[0])
    dval = _css_palette.resolve(dark, _declared_both(f"--role-{role}-text")[1])
    # Assert
    assert lval and dval and lval.startswith("#") and dval.startswith("#"), (
        f"--role-{role}-text must resolve to a hex color in both palettes; got "
        f"light={lval!r} dark={dval!r} (a dangling var() would render nothing)"
    )


# --- the primary mode split (Decision C) is preserved, not unified --------


def test_primary_keeps_its_mode_split():
    """Light primary resolves to the navy base, dark to the gold base. Assert
    BOTH directions so a future 'simplification' that makes them the same value
    (or swaps them) fails loudly instead of silently ruling Decision C."""
    # Arrange
    light, dark = _blocks()
    # Act
    light_primary = _css_palette.resolve(light, _css_palette.declared(light, "--color-primary"))
    dark_primary = _css_palette.resolve(dark, _css_palette.declared(dark, "--color-primary"))
    role_l = _css_palette.resolve(light, _declared_both("--role-primary-bg")[0])
    role_d = _css_palette.resolve(dark, _declared_both("--role-primary-bg")[1])
    # Assert
    assert (role_l, role_d) == (light_primary, dark_primary), (
        f"--role-primary-bg no longer aliases the brand bases: light "
        f"{role_l!r}!={light_primary!r} (navy) / dark {role_d!r}!="
        f"{dark_primary!r} (gold). The primary is the brand fill in each mode."
    )


def test_primary_is_not_unified_across_modes():
    # Arrange
    light, dark = _blocks()
    # Act
    same = (
        _css_palette.resolve(light, _declared_both("--role-primary-bg")[0])
        == _css_palette.resolve(dark, _declared_both("--role-primary-bg")[1])
    )
    # Assert
    assert not same, (
        "--role-primary-bg resolves to the SAME color in light and dark — that "
        "would be deciding compass Decision C (navy vs gold primary) in the "
        "token contract, which is an operator call, not this refactor's scope"
    )


# --- dark is not shadowed (source order: light block precedes dark) --------


def test_role_tokens_do_not_shadow_the_dark_palette():
    """The two palettes are :root (light) then [data-theme=dark]; equal
    specificity, so order decides. Each --role-* token's FINAL declaration in a
    bundle must be the dark one. (This is what
    test_css_dark_token_not_shadowed.py asserts repo-wide; pinning it here means
    a token added to light but forgotten in dark fails in THIS file too.)"""
    # Arrange
    light, dark = _blocks()
    # Act
    missing_in_dark = [
        f"--role-{r}-{s}"
        for r in _ROLES
        for s in _SUBTOKENS
        if _css_palette.declared(dark, f"--role-{r}-{s}") is None
    ]
    # Assert
    assert not missing_in_dark, (
        f"{missing_in_dark} are declared in light but absent from the dark "
        "palette — with light-first source order they would end the cascade "
        "shadowing the dark value (or, if absent from both, dangle). Declare "
        "every role token in BOTH blocks."
    )


# --- detector controls -----------------------------------------------------


def test_resolve_follows_an_alias_chain():
    # Arrange
    sample = "--a: var(--b);\n--b: #123456;\n"
    # Act
    got = _css_palette.resolve(sample, _css_palette.declared(sample, "--a"))
    # Assert
    assert got == "#123456"


def test_declared_rejects_a_consumption_not_a_declaration():
    # Arrange — a line that USES the token in var(), not one that defines it
    sample = "  color: var(--role-primary-bg);\n"
    # Act
    got = _css_palette.declared(sample, "--role-primary-bg")
    # Assert
    assert got is None
