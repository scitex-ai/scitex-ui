#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""No token may end the cascade with its dark value shadowed by a later light one.

``:root`` and ``[data-theme="dark"]`` are BOTH specificity (0,1,0). Equal. So
when two files declare the same token on the theme axis, nothing decides the
winner except which file the bundle imports later — and the bundles are built
by ``css/_build-index.ts``, whose ``findCssFiles()`` returns ``files.sort()``.
Alphabetical. Not curated.

Eight files currently declare a ``[data-theme="dark"]`` block, so this is not a
hypothetical about some future split of ``colors.css``; it is how the stylesheet
is assembled today. ``primitives/colors.css`` lands at index 32 of 88 in
``all.css`` and ``shell/theme.css`` at 65, which means theme.css re-declares 66
of colors.css's dark tokens from a LATER position under
``:root, [data-theme="light"]``.

That is fine for 64 of them, because theme.css also supplies its own dark value
and therefore owns both palettes. It is fine for the remaining 2 only by luck:
they are ``transparent`` in every block that sets them, so being overridden
changes nothing. Nothing enforces either condition. Add one token to a light
block without a dark counterpart, in a file that sorts after the file that gave
it a dark value, and the token silently renders its LIGHT value in dark mode.

The failure is invisible to every check we already have. The build succeeds, the
bundle is valid CSS, and every token is still *defined* — so
``test_app_css_tokens_resolve.py`` passes, because it asks whether a token has a
definition, not which definition wins. The only symptom is dark mode quietly
rendering light values, on the theme the constitution makes the default because
the operator's eyes are sensitive.

WHY THE DETECTOR IS NARROW, and why that narrowness is the load-bearing part: a
first pass that flagged *any* later non-dark redeclaration reported 100 hits.
Nearly all were ``[data-app-accent="writer"]`` and friends in
``stx-shell-sidebar.css`` — an ORTHOGONAL axis. A per-app accent is not
competing with dark mode; it is answering a different question, and a token can
legitimately be set by both. Only ``:root`` / ``html`` / ``[data-theme="light"]``
compete on the theme axis, and restricting to those took 100 down to 66, then to
2. ``test_detector_ignores_an_orthogonal_axis`` pins that restriction, because a
detector that flags everything is indistinguishable from one that works right up
until someone reads its output.
"""

import pathlib
import re

import pytest

import scitex_ui

_CSS = pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui" / "css"

#: The generated bundles. Each is an independent cascade, so a token can be
#: shadowed in one and clean in another — they import different file sets.
_BUNDLES = ("all.css", "shell.css", "app.css")

#: Selectors that compete with `[data-theme="dark"]` on the THEME axis.
#: Anything else (`[data-app-accent="..."]`, `.stx-foo`, media queries) is a
#: different question and must not be treated as a light-mode declaration.
_LIGHT_AXIS = re.compile(
    r'(:root|html|\[data-theme="light"\])'
    r'(\s*,\s*(:root|html|\[data-theme="light"\]))*\s*$'
)

#: Tokens allowed to end the cascade shadowed, each with the reason it is inert.
#: Listed ONE AT A TIME with a written reason rather than silenced by a blanket
#: flag — and `test_known_inert_entry_is_still_inert` re-derives the reason on
#: every run, so an entry that stops being inert fails instead of lingering.
_KNOWN_INERT = {
    "--app-accent-color": "transparent in every block that sets it",
    "--app-accent-tint": "transparent in every block that sets it",
}


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _bundle_order(bundle: str) -> list[str]:
    """The bundle's @import list, in source order — the cascade's spine."""
    text = (_CSS / bundle).read_text(encoding="utf-8")
    return [
        m.group(1)
        for line in text.splitlines()
        if line.strip().startswith("@import")
        for m in [re.search(r'"(.+?)"', line)]
        if m
    ]


def _theme_declarations(path: pathlib.Path) -> list[tuple[str, str]]:
    """(axis, token) for every theme-axis declaration, in source order.

    axis is "dark" or "light"; blocks on any other axis are skipped entirely
    rather than folded into "light", which is the distinction that took the
    first pass from 100 false hits to 66 real ones.
    """
    if not path.exists():
        return []
    body = _strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
    found: list[tuple[str, str]] = []
    for selector, block in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
        collapsed = " ".join(selector.split())
        if '[data-theme="dark"]' in collapsed:
            axis = "dark"
        elif _LIGHT_AXIS.match(collapsed):
            axis = "light"
        else:
            continue
        found.extend((axis, m.group(1)) for m in re.finditer(r"(--[\w-]+)\s*:", block))
    return found


def _shadowed(declarations: list[tuple[str, str]]) -> set[str]:
    """Tokens whose LAST theme-axis declaration is light despite having a dark one."""
    last: dict[str, str] = {}
    had_dark: set[str] = set()
    for axis, token in declarations:
        last[token] = axis
        if axis == "dark":
            had_dark.add(token)
    return {t for t in had_dark if last[t] == "light"}


def _bundle_declarations(bundle: str) -> list[tuple[str, str]]:
    ordered: list[tuple[str, str]] = []
    for rel in _bundle_order(bundle):
        ordered.extend(_theme_declarations(_CSS / rel.lstrip("./")))
    return ordered


@pytest.mark.parametrize("bundle", _BUNDLES)
def test_no_token_ends_the_cascade_with_its_dark_value_shadowed(bundle):
    """The invariant: a later light block must never be a token's final word."""
    # Arrange
    declarations = _bundle_declarations(bundle)

    # Act
    offenders = _shadowed(declarations) - set(_KNOWN_INERT)

    # Assert
    assert offenders == set(), (
        f"{bundle}: {sorted(offenders)} end the cascade with a light value even "
        "though an earlier file gave them a dark one. `:root` and "
        '`[data-theme="dark"]` have EQUAL specificity, so the later import wins '
        "and these render their LIGHT values in dark mode. Either give the later "
        "file a dark block too, or move the declaration."
    )


def test_detector_flags_a_light_block_that_follows_a_dark_one():
    """Positive control — without it, an empty offender set proves nothing."""
    # Arrange
    declarations = [("dark", "--bg-surface"), ("light", "--bg-surface")]

    # Act
    offenders = _shadowed(declarations)

    # Assert
    assert offenders == {"--bg-surface"}, (
        "the detector did not flag a light declaration following a dark one, so "
        "a green run above would mean nothing"
    )


def test_detector_ignores_a_dark_block_that_follows_a_light_one():
    """Negative control — a detector that flags everything is not a detector."""
    # Arrange
    declarations = [("light", "--bg-surface"), ("dark", "--bg-surface")]

    # Act
    offenders = _shadowed(declarations)

    # Assert
    assert offenders == set(), (
        "dark following light is the CORRECT order and must not be reported"
    )


def test_detector_ignores_an_orthogonal_axis():
    """`[data-app-accent=...]` is a different question, not a light declaration."""
    # Arrange
    sidebar = _CSS / "shell" / "stx-shell-sidebar.css"

    # Act
    axes = {axis for axis, _ in _theme_declarations(sidebar)}

    # Assert
    assert "light" not in axes, (
        "stx-shell-sidebar.css declares tokens under `[data-app-accent=...]`, an "
        "axis orthogonal to light/dark. Counting those as light declarations is "
        "what produced 100 false hits before the selector filter was narrowed."
    )


@pytest.mark.parametrize("token", sorted(_KNOWN_INERT))
def test_known_inert_entry_is_still_inert(token):
    """A ceiling entry that stops being inert must fail, not linger."""
    # Arrange
    values = set()
    for rel in _bundle_order("all.css"):
        body = _strip_comments(
            (_CSS / rel.lstrip("./")).read_text(encoding="utf-8", errors="ignore")
        )
        for selector, block in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
            collapsed = " ".join(selector.split())
            if '[data-theme="dark"]' in collapsed or _LIGHT_AXIS.match(collapsed):
                values.update(
                    m.group(1).strip()
                    for m in re.finditer(rf"{token}\s*:\s*([^;]+);", block)
                )

    # Act
    distinct = {v for v in values if v}

    # Assert
    assert len(distinct) <= 1, (
        f"{token} is on the known-inert list because it is "
        f"{_KNOWN_INERT[token]!r}, but it now resolves to {sorted(distinct)} "
        "across theme blocks. Being shadowed is no longer harmless — remove it "
        "from _KNOWN_INERT and fix the ordering."
    )
