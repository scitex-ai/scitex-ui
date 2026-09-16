"""The three shell tokens repointed to their defined targets must not be
consumed again.

scitex-ui-nine-shell-tokens-consumed-but-defined-nowhere-20260906: shell/
consumed NINE tokens defined by no palette, so each rendered a frozen literal.
This file resolves the three whose intent was UNAMBIGUOUS — the consumption
named its target token as the fallback, so the repoint is a pure alias removal,
not a design decision:

    --fg-default   -> --text-primary            (the fallback said so)
    --tab-accent   -> --color-accent-emphasis   (the fallback said so)
    --font-mono    -> --mono-font-family        (the defined :root mono stack)

Zero visual change: each site's fallback literal is preserved, and the target
token is defined in the resolution set, so the value it resolves to is the one
the author already wrote as the fallback.

The other six are NOT touched here — they are genuine decisions (a target color
or a role), and one (--fg-muted) has THREE different fallback intents across
12 sites, so a single repoint would silently change two of them. They stay on
the card, measured, with the contrast evidence attached.

WHY THIS IS A GUARD AND NOT A REMOVAL. A token consumed by no palette is
correct in exactly one theme by accident (see --accent-color, its sibling guard
test_accent_color_token_is_not_consumed.py). Re-pointing a site back to
var(--fg-default) would re-create that shape silently; this assertion is what
keeps it green-by-actually-asserting rather than green-by-absent.
"""

import re

from tests._checkout import css_dir

_CONSUMES = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)

# token -> the defined target it was repointed onto. If a site regresses to the
# left key, the right key is what it should read instead.
_REPOINTED = {
    "--fg-default": "--text-primary",
    "--tab-accent": "--color-accent-emphasis",
    "--font-mono": "--mono-font-family",
}

# The guard scans the whole css/ tree (see _sites_consuming). The aliases were
# consumed in BOTH shell/ (this card) and app/ (the parent card's population):
#   shell/   --font-mono x3, --fg-default x2, --tab-accent x1   (this PR's card)
#   app/     --font-mono x1 (package-docs-sidebar.css)          (parent card)
# Repointing the app/ site is safe because app.css imports the primitives layer
# (colors/spacing/typography-vars), so --mono-font-family resolves there —
# verified, not assumed.


def _blank_comments(text):
    """Replace comment bodies with blank lines, preserving line numbering, so a
    token MENTIONED in prose is not counted as a token USED (the inversion the
    sibling guard documents)."""
    return _CSS_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _sites_consuming(token):
    """Every stylesheet under css/ that reads `token` via var(), as 'path:line'.

    The whole css/ tree (shell/, app/, primitives/), not just shell/: the three
    aliases are defined by no palette, so a consumer is broken wherever it lives.
    --font-mono had one app/ site (package-docs-sidebar.css) in addition to the
    three shell/ sites — scoping to shell/ alone would have let the app/ site
    keep rendering a frozen literal while the guard reported clean.
    """
    found = []
    for sheet in sorted(css_dir().rglob("*.css")):
        source = _blank_comments(sheet.read_text())
        for number, line in enumerate(source.splitlines(), start=1):
            if token in _CONSUMES.findall(line):
                found.append(f"{sheet.relative_to(css_dir()).as_posix()}:{number}")
    return found


def test_the_consumes_pattern_matches_a_real_declaration():
    # Arrange — the exact shape being guarded, taken from the tree's own history.
    real = "  color: var(--fg-default, var(--text-primary, #e6edf3));"

    # Act
    match = _CONSUMES.search(real)

    # Assert
    assert match and match.group(1) == "--fg-default", (
        "_CONSUMES cannot match a real var() declaration, so the no-consumer "
        "assertions below would pass whether the tree is clean or the pattern "
        "is broken"
    )


def test_the_consumes_pattern_does_not_match_a_definition():
    # Arrange — a DEFINITION whose value is a bare literal, not a consumption.
    # (A definition like `--x: var(--y)` legitimately contains a var(), which is
    # why the sibling guard's control uses a hex value — a token being DECLARED
    # is not a token being READ.)
    definition = "  --font-mono: ui-monospace, monospace;"

    # Act
    match = _CONSUMES.search(definition)

    # Assert
    assert match is None, (
        f"_CONSUMES matched a definition ({match.group(0) if match else ''!r}), "
        "so it cannot tell declaring a token from reading one"
    )


def test_the_comment_pattern_matches_a_real_comment():
    # Arrange
    comment = "/* a bare var(--font-mono) would render an unstyled box */"

    # Act
    match = _CSS_COMMENT.search(comment)

    # Assert
    assert match, (
        "_CSS_COMMENT cannot match a real CSS comment, so _blank_comments is a "
        "no-op and the scan silently reverts to counting prose as code"
    )


def test_the_comment_pattern_does_not_eat_a_code_line():
    # Arrange — the direction that actually matters for a stripper: over-
    # matching empties the source every assertion below reads, failing silently.
    code = "  font-family: var(--mono-font-family, monospace);"

    # Act
    match = _CSS_COMMENT.search(code)

    # Assert
    assert match is None, (
        f"_CSS_COMMENT matched code ({match.group(0) if match else ''!r}); an "
        "over-eager stripper blanks the stylesheet and every scan then passes "
        "against an empty file"
    )


def test_the_scan_finds_a_real_consuming_token():
    # Arrange — --text-primary IS consumed by shell/, so a scan that cannot
    # find it cannot have established the absence of the repointed ones.
    token = "--text-primary"

    # Act
    sites = _sites_consuming(token)

    # Assert
    assert sites, (
        "positive control failed: no site consumes --text-primary, so this scan "
        "cannot demonstrate a real absence for any other token"
    )


def test_the_scan_ignores_a_token_no_stylesheet_uses():
    # Arrange — a name deliberately absent from the tree.
    token = "--zzz-token-no-stylesheet-defines-or-uses"

    # Act
    sites = _sites_consuming(token)

    # Assert
    assert sites == [], (
        f"negative control failed: {token} was reported at {sites}, so this "
        "scan matches names that are not there"
    )


def test_each_repointed_alias_is_no_longer_consumed():
    # Arrange — the three tokens this file fixed, and any that still have consumers.
    offenders = {
        token: _sites_consuming(token)
        for token in _REPOINTED
        if _sites_consuming(token)
    }

    # Act + Assert — none of them may be read via var() anywhere under css/.
    assert not offenders, (
        "a repointed shell alias is being consumed again, recreating a "
        f"defined-nowhere token (correct in one theme by accident): "
        f"{offenders}. Use the target: {_REPOINTED}."
    )
