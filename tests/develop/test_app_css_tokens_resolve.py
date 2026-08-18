#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A `var(--x)` with no fallback and no definition renders as nothing.

app.css used to import nothing from primitives/, so `--status-error`,
`--bg-secondary` and friends resolved to NOTHING for anyone loading app.css
alone. The rule was present and did nothing — invisible to any test that only
asserts the rule exists. It is also why components accumulated literal hex
fallbacks and why consuming projects hard-code colours instead of inheriting
the palette: the shared tokens existed, but not in the layer that needed them.

THE DISTINCTION THAT MATTERS, and the reason this file does not simply ban
undefined tokens:

    var(--x, 1000)   an intentional override HOOK. Undefined on purpose;
                     the consumer supplies it. Perfectly healthy.
    var(--x)         no fallback. If undefined, the property is unset and
                     the declaration silently does nothing.

Only the second is a defect. A guard that flagged both would have 25 false
positives in app.css alone and would be turned off within a week.
"""

import pathlib
import re

import pytest

from tests._checkout import css_dir

_CSS = css_dir()

# Supplied by the consuming page, legitimately undefined here.
_CONSUMER_SUPPLIED = {"--app-accent-color", "--app-accent-tint"}

# Pre-existing breakage in shell/ stylesheets, measured 2026-07-28. This is a
# CEILING, not a blessing: the list must never grow. Each entry is a
# `var(--x)` with no fallback that nothing defines, so the declaration is
# currently inert wherever it appears.
_KNOWN_BROKEN_IN_ALL = {
    # --primary-color, --secondary-color and --secondary-dark were RETIRED from
    # this ceiling on 2026-08-18. They were not renamed on a hunch: what each
    # one styled was read out of typography.css, and the link pair was measured
    # rendering in chromium first --
    #
    #     before   link rgb(51,51,51) == body rgb(51,51,51), decoration none
    #     after    link rgb(44,93,143) light / rgb(88,166,255) dark, != body
    #
    # -- so a link in body content had NO visual distinction from surrounding
    # text at all. `a` and `a:hover` now read --text-link / --text-link-hover,
    # and the six heading rules plus `.text-primary` read --text-primary.
    "--accent-color",
    # --text-dark / --text-light STAY, and the reason is sharper than "unknown".
    # They are LITERAL colour utilities (`.text-light`, `.text-dark`) whose
    # names describe an absolute colour, while every candidate token in the
    # palette FLIPS with the theme. Mapping `.text-light` to --text-inverse
    # would make it render DARK in dark mode -- inverting the one thing its
    # name promises. Fixing them means deciding whether literal-colour
    # utilities belong in a themed system at all, which is a design call.
    "--text-dark",
    "--text-light",
    # These two are two drifted copies of one widget rather than a naming
    # problem; see card
    # scitex-ui-two-search-css-twins-disagree-and-one-renders-no-background-20260818
    "--workspace-bg-default",
    "--workspace-bg-input",
    "--workspace-border-muted",
}


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _expand(bundle: pathlib.Path, _seen: set[pathlib.Path] | None = None) -> str:
    """The bundle's text with every `@import` inlined, to any depth.

    Depth matters. This used to follow exactly ONE level, which was correct only
    because no stylesheet in the tree imported another. The moment one does —
    and splitting an over-long token file is the obvious reason to — the tokens
    behind that second hop become invisible here. The tests that ask "is this
    token defined anywhere?" would then answer from a smaller corpus and the
    ones asking "is anything undefined?" would answer from a larger one, so a
    refactor with no visual effect could turn this file red or, worse, quiet.

    Cycles are possible in principle (`a` imports `b` imports `a`), so visited
    files are tracked; a cycle truncates rather than recurses forever.
    """
    seen = set() if _seen is None else _seen
    resolved = bundle.resolve()
    if resolved in seen or not bundle.exists():
        return ""
    seen.add(resolved)
    text = _strip_comments(bundle.read_text())
    parts = [text]
    for rel in re.findall(r'@import\s+"([^"]+)"', text):
        parts.append(_expand((bundle.parent / rel).resolve(), seen))
    return "\n".join(parts)


def _defined(css: str) -> set[str]:
    return set(re.findall(r"^\s*(--[\w-]+)\s*:", css, flags=re.MULTILINE))


def _used_without_fallback(css: str) -> set[str]:
    return set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", css))


def test_expand_follows_an_import_two_levels_down(tmp_path) -> None:
    """Control: the recursion above must be LIVE, not merely present.

    Nothing in the tree nests today, so making `_expand` recursive produced a
    byte-identical result on all three bundles — which is exactly what dead code
    produces too. This fixture nests on purpose so the capability is asserted
    rather than assumed, and it keeps asserting it after the tree does nest.
    """
    # Arrange
    (tmp_path / "leaf.css").write_text(":root {\n  --probe-token: #123456;\n}\n")
    (tmp_path / "mid.css").write_text('@import "./leaf.css";\n')
    bundle = tmp_path / "bundle.css"
    bundle.write_text('@import "./mid.css";\n')

    # Act
    defined = _defined(_expand(bundle))

    # Assert
    assert "--probe-token" in defined, (
        "_expand stopped before the second hop, so tokens behind a nested "
        "@import are invisible to every check in this file"
    )


def test_expand_survives_an_import_cycle(tmp_path) -> None:
    """A cycle must truncate, not recurse until the stack runs out."""
    # Arrange
    (tmp_path / "a.css").write_text('@import "./b.css";\n:root {\n  --from-a: 1px;\n}\n')
    (tmp_path / "b.css").write_text('@import "./a.css";\n:root {\n  --from-b: 2px;\n}\n')

    # Act
    defined = _defined(_expand(tmp_path / "a.css"))

    # Assert
    assert {"--from-a", "--from-b"} <= defined, (
        "a cycle should still yield both files' tokens exactly once"
    )


def test_app_bundle_has_no_inert_token_references():
    # Arrange
    css = _expand(_CSS / "app.css")

    # Act
    broken = sorted(_used_without_fallback(css) - _defined(css) - _CONSUMER_SUPPLIED)

    # Assert
    assert not broken, (
        f"app.css uses {len(broken)} token(s) with no fallback and no "
        f"definition: {', '.join(broken)}. Each renders as an unset property "
        "— the declaration exists and does nothing."
    )


def test_shell_bundle_inert_token_list_does_not_grow():
    # Arrange
    css = _expand(_CSS / "all.css")

    # Act
    broken = _used_without_fallback(css) - _defined(css) - _CONSUMER_SUPPLIED
    new = sorted(broken - _KNOWN_BROKEN_IN_ALL)

    # Assert
    assert not new, (
        f"{len(new)} NEW inert token reference(s) in all.css: "
        f"{', '.join(new)}. Define them, or give them a fallback if they are "
        "meant to be consumer-supplied override hooks."
    )


@pytest.mark.parametrize("token", sorted(_KNOWN_BROKEN_IN_ALL))
def test_ceiling_entry_is_still_broken(token):
    """Every name in the ceiling must still BE broken — the reverse check.

    ``test_shell_bundle_inert_token_list_does_not_grow`` above only asserts the
    set does not GROW. Nothing asserted the other direction, so once one of
    these tokens was fixed the ceiling would keep naming it and stay green.

    That matters because this list is the FORCING FUNCTION for
    scitex-ui-app-css-tokens-defined-nowhere: fixing a token is supposed to
    REQUIRE deleting its entry here, which is what makes the remaining work
    visible. A ceiling that silently keeps a fixed entry drops the forcing
    function and decays into a record of history.

    The sibling guard in test_shell_ts_reachability.py has had exactly this
    reverse check on ``_ALLOWED_ORPHANS`` since 0.14.2, where it did its job —
    emptying that allowlist is what forced the orphan question to be answered
    rather than left to rot. Same shape, same risk; this file was missing it.
    """
    # Arrange
    css = _expand(_CSS / "all.css")

    # Act
    broken = _used_without_fallback(css) - _defined(css) - _CONSUMER_SUPPLIED

    # Assert
    assert token in broken, (
        f"{token} is listed in _KNOWN_BROKEN_IN_ALL but is no longer inert in "
        "all.css — it now resolves, or its call sites are gone. Delete the "
        "entry. Leaving it makes the ceiling describe the past and quietly "
        "removes the pressure to fix what genuinely remains."
    )


def test_app_bundle_carries_the_status_palette():
    # Arrange
    css = _expand(_CSS / "app.css")
    required = {
        "--status-success",
        "--status-error",
        "--status-warning",
        "--status-info",
    }

    # Act
    missing = sorted(required - _defined(css))

    # Assert
    assert not missing, (
        f"app.css does not define {missing}. Components then either hard-code "
        "hex or carry literal fallbacks, and consuming projects copy them — "
        "which is how one palette quietly becomes several."
    )


def test_app_bundle_does_not_import_typography_rules():
    # Arrange — primitives/typography.css carries ~63 RULE blocks including
    # `body` and `h1`-`h6`; importing it here would restyle the host page
    # rather than contribute tokens.
    text = (_CSS / "app.css").read_text()

    # Act
    imports_rules = re.search(r'@import\s+"\./primitives/typography\.css"', text)

    # Assert
    assert not imports_rules, (
        "app.css imports primitives/typography.css, which sets element-level "
        "rules on body and headings — app.css must contribute tokens only"
    )
