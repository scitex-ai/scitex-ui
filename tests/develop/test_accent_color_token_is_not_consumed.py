"""`--accent-color` is defined by no palette, so every site using it renders a
frozen literal that cannot follow the theme.

Measured 2026-09-06 before removal: six sites, all falling back to `#58a6ff`, a
GitHub-DARK blue. Against the LIGHT palette all four contrast-relevant sites
failed WCAG — 2.36-2.40 where 3.0 (focus indicator) or 4.5 (text) is required —
while passing in dark. A token no palette defines is correct in exactly one
theme by accident.

The sharpest instance: `.rmc-textarea:focus` sets `outline: none` and colours
its border with this token, so the only focus indicator on that control scored
2.40 against its own background.

Repointed to `--accent`, which IS defined in both palettes (#6d4cad light,
#a371f7 dark) and scores 5.16-6.07 at every site.

WHY THIS GUARD IS NARROW. `shell/` carries NINE other consume-but-never-define
tokens (--accent-primary, --border-subtle, --color-accent-muted, --fg-default,
--fg-muted, --folder-color, --font-mono, --tab-accent, --text-dimmed), so a
shell-wide undefined-token assertion would be red on arrival — and a red guard
gets disabled rather than obeyed. That wider population is carded with its
measurement attached; this file guards only the token that was fixed, and so
ships green while actually asserting something.
"""

import re

from tests._checkout import css_dir

_CONSUMES = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)

_REMOVED_TOKEN = "--accent-color"
_REPLACEMENT_TOKEN = "--accent"


def _blank_comments(text):
    """Replace comment bodies with blank lines, preserving line numbering.

    Without this the scan counts a token MENTIONED in prose as a token USED.
    Measured 2026-09-06 on a throwaway version of this same scan: it reported
    20 undefined tokens in css/app/, of which two (`--green`, `--text`) existed
    only inside comments — and `--green`'s single appearance was in the sentence
    explaining why the file deliberately does NOT use it. The detector inverted
    on the documentation of the correct behaviour.
    """
    return _CSS_COMMENT.sub(
        lambda m: "\n" * m.group(0).count("\n"), text
    )


def _sites_consuming(token):
    """Stylesheets under css/ that read `token` via var(), as 'path:line'."""
    found = []
    for sheet in sorted(css_dir().rglob("*.css")):
        source = _blank_comments(sheet.read_text())
        for number, line in enumerate(source.splitlines(), start=1):
            if token in _CONSUMES.findall(line):
                found.append(f"{sheet.relative_to(css_dir()).as_posix()}:{number}")
    return found


def test_the_consumes_pattern_matches_a_real_declaration():
    # Arrange — the exact shape this guard removed, taken from the tree's own
    # history rather than transcribed from the pattern.
    real = "  background: var(--accent-color, #58a6ff);"

    # Act
    match = _CONSUMES.search(real)

    # Assert
    assert match, (
        "_CONSUMES cannot match a real var() declaration, so every negative "
        "assertion built on it would pass whether the tree is clean or the "
        "pattern is broken"
    )


def test_the_consumes_pattern_does_not_match_a_token_definition():
    # Arrange — a DEFINITION, not a consumption. Confusing the two is the live
    # risk for this pattern: a guard that counts definitions as uses would
    # accuse the palette that legitimately declares the token.
    definition = "  --accent-color: #58a6ff;"

    # Act
    match = _CONSUMES.search(definition)

    # Assert
    assert match is None, (
        f"_CONSUMES matched a definition ({match.group(0) if match else ''!r}), "
        "so it cannot tell declaring a token from reading one"
    )


def test_the_comment_pattern_matches_a_real_comment():
    # Arrange
    comment = "/* a bare var(--accent-color) would render an unstyled box */"

    # Act
    match = _CSS_COMMENT.search(comment)

    # Assert
    assert match, (
        "_CSS_COMMENT cannot match a real CSS comment, so _blank_comments is a "
        "no-op and the scan silently reverts to counting prose as code"
    )


def test_the_comment_pattern_does_not_eat_a_code_line():
    # Arrange — the direction that actually matters for a stripper: over-
    # matching empties the source every assertion below reads, which fails
    # silently and green.
    code = "  background: var(--accent, #6d4cad);"

    # Act
    match = _CSS_COMMENT.search(code)

    # Assert
    assert match is None, (
        f"_CSS_COMMENT matched code ({match.group(0) if match else ''!r}); an "
        "over-eager stripper blanks the stylesheet and every scan then passes "
        "against an empty file"
    )


def test_the_scan_ignores_a_token_only_mentioned_in_a_comment():
    # Arrange — prose naming the token, which must NOT count as a use. This is
    # the inversion that made a throwaway version of this scan report 20
    # undefined tokens when 4 were real.
    prose = "/* a bare var(--accent-color) would render an unstyled box */\n"

    # Act
    survives = _CONSUMES.findall(_blank_comments(prose))

    # Assert
    assert survives == [], (
        f"the scan read {survives} out of a comment, so it cannot tell a USE "
        "from a MENTION and would accuse a file that merely documents the token"
    )


def test_the_detector_finds_a_token_the_tree_really_consumes():
    # Arrange — --accent is read by the very sites this card repointed, so a
    # detector that cannot find it cannot have found --accent-color either.
    token = _REPLACEMENT_TOKEN

    # Act
    sites = _sites_consuming(token)

    # Assert
    assert sites, (
        f"positive control failed: no site consumes {token}, so this scan "
        "cannot demonstrate a real absence for any other token"
    )


def test_the_detector_ignores_a_token_no_stylesheet_uses():
    # Arrange — a name deliberately absent from the tree.
    token = "--zzz-token-no-stylesheet-defines-or-uses"

    # Act
    sites = _sites_consuming(token)

    # Assert
    assert sites == [], (
        f"negative control failed: {token} was reported at {sites}, so this "
        "scan matches names that are not there"
    )


def test_no_stylesheet_consumes_the_palette_less_accent_color_token():
    # Arrange
    token = _REMOVED_TOKEN

    # Act
    sites = _sites_consuming(token)

    # Assert
    assert sites == [], (
        f"{_REMOVED_TOKEN} is defined by no palette, so these sites render a "
        f"frozen literal that cannot follow the theme: {sites}. Use "
        f"{_REPLACEMENT_TOKEN}, which is defined in both palettes."
    )
