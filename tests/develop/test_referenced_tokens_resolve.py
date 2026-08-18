#!/usr/bin/env python3
"""A `var(--x)` with NO fallback must resolve to a declaration somewhere.

THIS GUARD EXISTS BECAUSE THE PACKAGE HAS SHIPPED THE SAME DEFECT THREE TIMES,
and each instance was found by a person looking at something else:

    0.12.1  the context menu rendered dark-grey-on-dark, because --text-link
            was declared in one layer only.
    2026-08 scitex-hub's `comms` tile had no accent bar, because
            --app-accent-comms existed in shell/theme.css and not in
            primitives/colors/.
    0.15.0  shell/theme.css carried NO --accent at all while
            css/app/combobox.css reads var(--accent) at three sites. Found by
            scitex-scholar grepping the INSTALLED WHEEL before adopting --
            fourteen releases after it broke.

ONE MECHANISM UNDERLIES ALL THREE, and it is the reason a written warning was
never going to be enough: **an undefined CSS custom property is not an error.**
`color: var(--nope)` makes the declaration invalid at computed-value time, the
element inherits, and the page renders and SUCCEEDS -- wrong. No console
warning, no build failure, no 404. The only symptom is a colour somebody has to
notice, in a theme they happen to be looking at.

So the three incidents are one CLASS, and this test is the mechanical barrier
for it (constitution 7, "pave the road behind you": prefer a hook to a warning,
because a rule that must be remembered is forgotten exactly when it matters).

WHY *NO FALLBACK* IS THE CONDITION, RATHER THAN "IS DECLARED"
------------------------------------------------------------
Measured on the 0.16.0 tree: 30 tokens are referenced but never declared, and
24 of them are referenced WITH a `var(--x, fallback)`. Those are deliberate --
`--stx-toast-*`, `--stx-drawer-*` and friends are documented override hooks an
ADOPTER is invited to set, and the fallback is the shipped default. Flagging all
30 would make this guard 80% noise, and a noisy guard gets silenced, which is
the constitution-2 failure mode of a gate that cannot fail wearing a different
hat.

The 6 with no fallback are the ones with no safety net. That is the whole
distinction, and it is why this test reads the fallback comma rather than just
the token name.

WHAT THIS GUARD CANNOT SEE, stated so nobody reads more into a green than it
carries. scitex-hub named the three failure modes while setting hub's dependency
floor, and this covers exactly one of them:

    1. file absent            -> @import 404s, page visibly unstyled   LOUD
    2. token absent           -> var() resolves to nothing             <-- THIS TEST
    3. token present, VALUE STALE -> renders wrong, silently           NOT COVERED

Mode 3 is a question about which VERSION a consumer resolved, so no test inside
this repo can answer it; it needs a per-token "first correct in" map read from
published wheels. See `tools/token_floors.py`.

Nor does this follow `@import`: it unions declarations across every CSS file in
the tree, which is deliberately more permissive than any single entry point. A
token declared in `primitives/` and referenced from a file that only ever loads
`shell/theme.css` passes here. That LAYER-AGREEMENT question is the separate
concern of `test_app_accents_agree_across_layers.py`, and the two guards are
complementary rather than redundant.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# Resolved from THIS FILE, never from ``scitex_ui.__file__``: under a
# non-editable install the latter points into site-packages, so the guard would
# assert about a DIFFERENT TREE than the branch under review -- and would go red
# or green for reasons having nothing to do with the change. That is not
# hypothetical; it is what PR #152 was opened to fix across 19 modules.
_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
)

#: Comments are stripped BEFORE scanning. Token names appear in prose all over
#: this tree -- every palette file explains its own tokens -- so a scan that
#: reads comments finds "declarations" that do not exist and goes quietly green.
_COMMENT = re.compile(r"/\*.*?\*/", re.S)

_DECL = re.compile(r"^\s*(--[A-Za-z0-9_-]+)\s*:", re.M)

#: Group 2 captures the comma that introduces a fallback, which is the entire
#: signal this guard keys on. ``var(--x)`` -> group(2) is None (no safety net);
#: ``var(--x, #fff)`` -> group(2) is "," (defaulted on purpose).
_USE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(,)?")

#: KNOWN-UNRESOLVED, one entry per token with a written reason, per constitution
#: 2: "Exempt rules one at a time, in a config file, each with a written reason
#: -- reviewable, greppable, and individually revisitable. Never with a flag
#: that silences the whole run."
#:
#: These six are REAL DEFECTS, not false positives. They are listed rather than
#: fixed because the fix is a MAPPING DECISION and not a colour choice: five of
#: the six are one abandoned rename, and guessing what they were meant to be
#: would replace a silent bug with a confident wrong one.
#:
#: Deleting an entry from this dict is how each gets fixed. The test asserts the
#: dict has no STALE entries too, so a token that gets fixed cannot linger here
#: pretending the debt is still owed.
_KNOWN_UNRESOLVED = {
    # primitives/typography.css reaches for a colour vocabulary that predates
    # the semantic palette (--text-primary / --text-secondary / --text-muted)
    # and was never migrated with it. What each one actually STYLES was read
    # out of the file rather than guessed from its name:
    #
    #   --primary-color    h1..h6, all six heading rules      -> --text-primary
    #   --secondary-color  `a { color }` AND `.text-secondary` -> TWO ROLES
    #   --secondary-dark   `a:hover`                           -> no equivalent
    #   --text-light       `.text-light` utility class         -> --text-inverse?
    #   --text-dark        `.text-dark` utility class          -> --text-primary?
    #
    # --secondary-color IS WHY THESE ARE DEFERRED RATHER THAN RENAMED. It serves
    # two different semantics in one file -- link colour and secondary text --
    # which map to two DIFFERENT modern tokens (--text-link, --text-secondary).
    # No single rename satisfies both, and a confident sed would collapse a
    # distinction the palette deliberately draws while looking tidy in the diff.
    #
    # WORSE, AND SEPARATELY TRUE: --text-link IS declared (3 files) and used
    # across the tree (5 files), but NEVER in typography.css -- so links styled
    # by this file render with no colour while the WCAG-fixed value sits one
    # line away. That is the defect scitex-hub carried for nine days, here, with
    # no stale fork to blame.
    "--primary-color": "legacy typography palette, never migrated; see card scitex-ui-six-css-tokens-referenced-with-no-fallback-and-no-declaration-20260818",
    "--secondary-color": "legacy typography palette; serves TWO roles (link + secondary text) so it must be SPLIT before it can be mapped; same card",
    "--secondary-dark": "legacy typography palette, `a:hover`, no modern equivalent yet; same card",
    "--text-dark": "legacy typography palette, `.text-dark` utility; same card",
    "--text-light": "legacy typography palette, `.text-light` utility; same card",
    # shell/media-viewer.css, three sites (border-bottom, background, border).
    # Reads like a typo for --workspace-border-muted's real sibling
    # --workspace-border-subtle, but "reads like" is not evidence, so it is
    # recorded rather than silently renamed.
    "--workspace-border-muted": "probably meant --workspace-border-subtle, unconfirmed; same card",
    # THE THREE BELOW ARE WHY THIS GUARD EARNED ITS KEEP, and they are worth
    # reading before trusting any hand-rolled version of this scan.
    #
    # A one-off script measured this tree first and reported SIX. It tracked
    # "has a fallback" PER TOKEN instead of PER USE, so a token referenced once
    # WITH a fallback and once WITHOUT was marked globally safe. All three of
    # these are exactly that shape, and all three are real: the fallback-free
    # site renders nothing.
    #
    # --accent-color is referenced six times in shell/ WITH `, #58a6ff`, and
    # once in primitives/typography.css WITHOUT. So five sites degrade to a
    # blue and the sixth degrades to nothing.
    "--accent-color": "one fallback-free use in primitives/typography.css; six others carry `, #58a6ff`; same card",
    # THESE TWO ARE FILED ELSEWHERE ON PURPOSE, and the reason is worth reading
    # before adding anything to this dict.
    #
    #   shell/workspace-files-tree/search.css:7   var(--workspace-bg-default)
    #   app/file-browser/search.css:7             var(--workspace-bg-default, #1e1e1e)
    #
    # Confirmed DIFFERENT FILES (88 vs 85 lines, `.wft-search-box` vs
    # `.stx-app-file-tree__search-box`, the latter headed "Ported verbatim from
    # scitex-cloud"). Two drifted copies of one widget: the app copy renders
    # #1e1e1e, the shell copy renders nothing. A user can see that today.
    #
    # scitex-hub's objection to listing them here, which I accept: an exemption
    # list is where a LIVE RENDERING DIVERGENCE goes to die. Nobody searches it
    # when they hit the visual bug, and the stale-exemption test below will
    # never retire these -- the exemption stays legitimately true for as long as
    # the tokens stay undeclared, so they can sit here CORRECTLY forever while
    # the widget keeps rendering two ways. They stay in this dict only because
    # the guard must be green; the WORK is tracked as its own card.
    "--workspace-bg-default": "NOT a naming problem -- two drifted copies of one widget; see card scitex-ui-two-search-css-twins-disagree-and-one-renders-no-background-20260818",
    "--workspace-bg-input": "same two files, same asymmetry; same card as --workspace-bg-default",
}


def _css_files() -> list[pathlib.Path]:
    return sorted(p for p in _CSS.rglob("*.css"))


def _scan() -> tuple[set[str], dict[str, set[str]]]:
    """Return (declared token names, {token: files that use it with NO fallback})."""
    declared: set[str] = set()
    bare_uses: dict[str, set[str]] = {}
    for path in _css_files():
        text = _COMMENT.sub("", path.read_text(errors="replace"))
        declared |= set(_DECL.findall(text))
        for match in _USE.finditer(text):
            if match.group(2) is None:  # no fallback
                name = match.group(1)
                bare_uses.setdefault(name, set()).add(
                    str(path.relative_to(_CSS))
                )
    return declared, bare_uses


"""ANTI-VACUITY, split across the three tests below.

This guard's shape is "no member of set X is missing from set Y". A scan that
reads zero files produces an empty X, and an empty X satisfies that FOR FREE --
green, having measured nothing. The three assertions that follow are the only
thing standing between "checked" and "did not check", and they are separate
tests so a failure names which half of the scan died rather than stopping at
the first one.
"""


def test_the_scan_finds_the_css_files() -> None:
    """Zero files read would make the resolution check vacuously true."""
    # Arrange
    root = _CSS
    # Act
    files = _css_files()
    # Assert
    assert len(files) > 50, f"only {len(files)} css files found under {root}"


def test_the_scan_finds_declarations() -> None:
    """Zero declarations would make EVERY reference look unresolved (red, wrong reason)."""
    # Arrange
    _ = _CSS
    # Act
    declared, _unused = _scan()
    # Assert
    assert len(declared) > 100, f"only {len(declared)} tokens declared; scan looks broken"


def test_the_scan_finds_fallback_free_references() -> None:
    """Zero fallback-free uses is the vacuous-green case: nothing left to check."""
    # Arrange
    _ = _CSS
    # Act
    _declared, bare_uses = _scan()
    # Assert
    assert len(bare_uses) > 50, (
        f"only {len(bare_uses)} fallback-free var() uses found; the fallback "
        "comma detection in _USE is probably broken, which would silently "
        "exempt every reference in the tree"
    )


def test_every_fallback_free_token_reference_resolves() -> None:
    """The class-killer: `var(--x)` with no fallback must have a declaration."""
    # Arrange
    declared, bare_uses = _scan()
    # Act
    unresolved = {
        name: files
        for name, files in bare_uses.items()
        if name not in declared and name not in _KNOWN_UNRESOLVED
    }
    # Assert
    if unresolved:
        detail = "\n".join(
            f"  {name}\n" + "".join(f"      {f}\n" for f in sorted(files))
            for name, files in sorted(unresolved.items())
        )
        pytest.fail(
            "these custom properties are referenced with NO fallback and are "
            f"declared nowhere in {_CSS.name}/:\n\n{detail}\n"
            "An undefined custom property is NOT an error -- the declaration "
            "becomes invalid at computed-value time and the element INHERITS, "
            "so the page renders successfully and wrong. That is the mechanism "
            "behind the 0.12.1 context-menu bug, hub's missing comms accent "
            "bar, and shell/theme.css shipping without --accent for fourteen "
            "releases.\n\n"
            "Fix by declaring the token in BOTH palette layers (primitives/ AND "
            "shell/theme.css -- see test_app_accents_agree_across_layers.py for "
            "why both), or by giving the reference an explicit fallback if it "
            "is meant to be an adopter override hook."
        )


def test_no_stale_entries_in_the_known_unresolved_list() -> None:
    """An exemption that has been fixed must not linger.

    A list of known problems is itself a thing that rots: once a token is
    declared, its entry here silently exempts nothing while still reading as
    outstanding debt. Worse, the name could be re-used later and inherit an
    exemption nobody granted it. So the list is asserted to be exactly the set
    of still-broken tokens, not a superset.
    """
    # Arrange
    declared, bare_uses = _scan()
    # Act
    now_declared = {n for n in _KNOWN_UNRESOLVED if n in declared}
    no_longer_used = {n for n in _KNOWN_UNRESOLVED if n not in bare_uses}
    # Assert
    assert not (now_declared or no_longer_used), (
        "_KNOWN_UNRESOLVED is out of date -- delete these entries:\n"
        f"  now declared     : {sorted(now_declared) or '-'}\n"
        f"  no longer used   : {sorted(no_longer_used) or '-'}"
    )
