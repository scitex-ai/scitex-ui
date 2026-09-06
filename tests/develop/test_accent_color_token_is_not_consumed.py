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

_REMOVED_TOKEN = "--accent-color"
_REPLACEMENT_TOKEN = "--accent"


def _sites_consuming(token):
    """Stylesheets under css/ that read `token` via var(), as 'path:line'."""
    found = []
    for sheet in sorted(css_dir().rglob("*.css")):
        for number, line in enumerate(sheet.read_text().splitlines(), start=1):
            if token in _CONSUMES.findall(line):
                found.append(f"{sheet.relative_to(css_dir()).as_posix()}:{number}")
    return found


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
