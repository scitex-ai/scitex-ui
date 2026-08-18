#!/usr/bin/env python3
"""Every class the shell's LAYOUT rules depend on must be written by this package.

THE BUG THIS EXISTS FOR, measured 2026-08-18 in a real browser — the first
rendered-shell measurement this repo has ever had.

At any viewport <=768px, ``css/shell/mobile.css`` hid the Console/Chat, worktree
and Viewer panes with ``display: none !important`` and would reveal one via
``.mobile-active-pane``. Nothing in the package ever wrote that class. Its own
comment said "JS adds .mobile-active-pane"; that JS did not exist. The same
media block also hid every resizer, so nothing could drag the panes back.

Measured at 390x844: ai pane width 0, viewer width 0, module pane 390, and
ZERO visible clickable elements on the page. At 1280x900 the same document was
normal (ai 250px, viewer 481px). So a phone lost two panes permanently.

WHY NO EXISTING CHECK CAUGHT IT, and why this one is shaped the way it is:
nothing errored. The CSS was valid, the page painted, dark mode was correct, and
there was NO horizontal overflow — scrollWidth 390 == viewport 390, zero
offending elements. Every cheap check passed. The failure is invisible to
exactly the assertions someone would think to write, because the defect is not a
malformed rule; it is a rule whose destructive half shipped and whose
restorative half never did.

THE GENERAL SHAPE — a HALF-PAIR. One side of a two-sided contract exists and the
other does not, so the artifact is individually valid and jointly broken. Five
instances turned up in this package and its neighbours in a single afternoon:

  1. a forked design-token file      two producers, no link between them
  2. a diverged @import manifest     a producer silently dropped
  3. a class nothing writes          consumer with no producer   <- this test
  4. a pane nothing renders          producer with no consumer
  5. a packaged recipe path          producer never shipped in the wheel

This guard covers instance 3 for the classes where it is CATASTROPHIC rather
than merely untidy: the ones that decide whether a pane is on screen.

SCOPE, and why it is not "every class":
scitex-ui styles 97 shell classes that nothing in this package writes. That is
NOT 97 bugs — most are content classes rendered by an ADOPTER (chat messages,
viewer chrome, status-bar items) which this package deliberately only styles.
That arrangement is legitimate but currently UNDECLARED, which is its own
problem and is carded, not asserted here. Asserting a contract the repo does not
hold would make this guard red on arrival, and a red guard gets disabled rather
than obeyed.

So the assertion is narrowed to LAYOUT-STATE classes — those appearing in a rule
that sets ``display`` on a pane — because for those the package is
unambiguously both the styler AND the renderer: the shell owns its own layout.
The narrowing is by written reason, one entry at a time, never by a blanket flag.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# RESOLVE THE TREE UNDER TEST FROM THIS FILE, NOT FROM ``scitex_ui.__file__``.
#
# The obvious spelling — ``pathlib.Path(scitex_ui.__file__).parent`` — is what
# the other guards in tests/develop/ use, and on this machine it resolves to
# /opt/venv-sac/lib/python3.12/site-packages/scitex_ui (version 0.15.0), NOT to
# the checkout. Measured 2026-08-18: this test was written that way, run in a
# worktree, and went red — for the INSTALLED package. Right answer, wrong tree,
# and it would have stayed red after a correct fix here while being unable to
# verify it.
#
# That is a thermometer in someone else's box: the guard cannot see the change
# it is guarding. Deriving from ``__file__`` ties the assertion to the checkout
# the test itself lives in, which is the only tree a pull request can change.
# A non-editable install makes the two silently disagree, and "silently" is the
# whole problem — nothing about the import spelling announces which tree it read.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PACKAGE = _REPO_ROOT / "src" / "scitex_ui"
_STATIC = _PACKAGE / "static" / "scitex_ui"
_CSS = _STATIC / "css"
_TEMPLATES = _PACKAGE / "templates"

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
_CLASS_IN_SELECTOR = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
_WORDS = re.compile(r"[_a-zA-Z][\w-]*")

#: Classes that decide whether a pane occupies the screen live under these
#: prefixes. A miss here is invisible and catastrophic; a miss on a content
#: class is cosmetic. Deliberately narrow — see the module docstring.
_LAYOUT_PREFIX = re.compile(r"^(ws-|workspace-|mobile-)")

#: Layout classes an ADOPTER is contractually expected to write, so their
#: absence from this package is correct rather than a defect. Each entry needs
#: a reason and a card; this list must never become a way to silence the check.
#:
#: EMPTY ON PURPOSE at introduction. Everything currently orphaned is either the
#: bug this test exists for or is being removed alongside it. If an entry is
#: ever added here, it is a declaration that another repo owns that class — and
#: that declaration belongs in the shell contract document, not only here.
_ADOPTER_RENDERED: dict[str, str] = {}


def _layout_state_classes() -> dict[str, set[str]]:
    """Classes that appear in a selector of a rule which sets ``display``.

    Restricting to ``display`` is what makes this about VISIBILITY rather than
    styling. A rule that merely colours a pane cannot make it unreachable.
    """
    found: dict[str, set[str]] = {}
    for path in sorted(_CSS.rglob("*.css")):
        text = _CSS_COMMENT.sub("", path.read_text(errors="replace"))
        for selector, body in _RULE.findall(text):
            if not re.search(r"(^|[;{\s])display\s*:", body):
                continue
            for cls in _CLASS_IN_SELECTOR.findall(selector):
                if _LAYOUT_PREFIX.match(cls):
                    found.setdefault(cls, set()).add(
                        path.relative_to(_CSS).as_posix()
                    )
    return found


def _written_tokens() -> set[str]:
    """Classes this package actually PUTS ON AN ELEMENT.

    A WRITE is ``class="..."`` / ``className=`` in markup or JSX, an assignment
    to ``.className``, or ``classList.add|toggle|replace``. A class named inside
    a ``querySelector(".foo")`` string is a READ — it consumes the class, it does
    not produce it — and counting reads as writes is what a first version of this
    function did.

    THE MUTATION PROBE IS WHY THIS IS TIGHT. With reads counted, removing
    ``ws-ai-pane`` from standalone_shell.html did NOT make the guard notice: the
    class is also named in selector strings in mobile-swipe.js and the resizer
    TS, so the deleted writer was masked by surviving readers. The guard was
    therefore blind to exactly the edit it exists to catch, and it looked healthy
    the whole time because the ONE bug it was written for (a class named nowhere
    at all) still tripped it.

    That is the lesson worth keeping: a guard verified only against the bug that
    motivated it is verified against one input. Only the mutation probe — break
    something that currently passes, and require the guard to notice — measures
    whether it responds to CHANGE rather than to today's snapshot.

    ``classList.remove`` is deliberately NOT a write: code that only ever removes
    a class cannot be what puts it there.
    """
    tokens: set[str] = set()
    sources = list(_TEMPLATES.rglob("*.html"))
    for ext in ("*.js", "*.ts", "*.tsx"):
        sources += [p for p in _STATIC.rglob(ext) if "vendor" not in p.parts]
    for path in sources:
        text = path.read_text(errors="replace")
        # class="a b c" / className="a b" — markup and JSX, including the
        # class="..." inside a JS template literal that builds markup.
        #
        # The attribute value must run to the CLOSING QUOTE OF THE SAME TYPE.
        # A cheaper `["\'`]([^"\'`]*)` stops at the first quote of ANY type, and
        # a Django class attribute routinely contains the other kind:
        #     class="ws-ai-pane{% if panes.ai == 'unused' %} ws-pane-unused{% endif %}"
        # That truncates at `panes.ai == `, so `ws-pane-unused` looks unwritten
        # and the guard reports a false orphan. Caught here: the tightened scan
        # accused `.ws-pane-unused`, which the template plainly does write.
        for double, single, tick in re.findall(
            r'class(?:Name)?\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|`([^`]*)`)', text
        ):
            tokens.update(_WORDS.findall(double or single or tick))
        # el.classList.add("x", "y") / .toggle("x") / .replace("a", "b")
        for call in re.findall(
            r'classList\.(?:add|toggle|replace)\(([^)]*)\)', text
        ):
            for literal in re.findall(r'["\'`]([^"\'`]+)["\'`]', call):
                tokens.update(_WORDS.findall(literal))
    return tokens


def test_css_scan_finds_layout_state_classes() -> None:
    """ANTI-VACUITY, half one. A zero population must FAIL, not pass.

    STATED AS A GENERAL RULE because it is not specific to this test. While
    measuring the shell at 390px a touch-target audit reported "0 undersized
    targets" and looked clean — it had skipped every hidden element, and all 32
    interactive elements were ``display: none``. It rated a page with NO
    CONTROLS AT ALL as perfect.

    That is the gate-that-cannot-fail one level down: not a check configured to
    pass, but a check that passes by finding nothing to look at. Any check that
    filters a population before asserting over it needs this guard, or a parser
    bug and a clean codebase produce identical greens.
    """
    # Arrange: nothing to build — the shipped stylesheets are the fixture.
    # Act
    layout = _layout_state_classes()
    # Assert
    assert layout, (
        "no layout-state classes were found at all — the CSS parser matched "
        "nothing, so this module's other assertions would pass vacuously"
    )


def test_writer_scan_finds_class_tokens() -> None:
    """ANTI-VACUITY, half two: the writer side must also have a population.

    Split from the CSS half deliberately. If both lived in one test, the first
    failing assert would mask the second, and "which side of the scan broke"
    is exactly the question a red here has to answer.
    """
    # Arrange: the shipped templates and scripts are the fixture.
    # Act
    written = _written_tokens()
    # Assert
    assert written, (
        "no class-like tokens were found in any template/js/ts — the writer "
        "scan matched nothing, so every class would look orphaned"
    )


def test_every_layout_state_class_has_a_writer() -> None:
    """No pane may be hidden by a rule whose revealing half nothing produces."""
    # Arrange
    layout = _layout_state_classes()
    written = _written_tokens()
    # Act
    orphans = {
        cls: files
        for cls, files in layout.items()
        if cls not in written and cls not in _ADOPTER_RENDERED
    }
    # Assert
    if orphans:
        lines = [
            "Layout classes used in a `display` rule that NOTHING in this "
            "package writes.",
            "Each one is a pane whose visibility depends on a class that never "
            "arrives, so the rule's destructive half ships and its restorative "
            "half does not:",
            "",
        ]
        for cls in sorted(orphans):
            lines.append(f"  .{cls}")
            for f in sorted(orphans[cls]):
                lines.append(f"      styled in css/{f}")
        lines += [
            "",
            "Fix by writing the class where the markup is produced, or by "
            "deleting the rule. Do NOT add it to _ADOPTER_RENDERED unless "
            "another repo genuinely owns rendering it — and then say which, "
            "and record it in the shell contract.",
        ]
        pytest.fail("\n".join(lines))
