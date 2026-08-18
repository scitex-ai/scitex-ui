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

#: KNOWN ORPHANS — a CEILING, not a blessing. Deliberately a SEPARATE list from
#: ``_ADOPTER_RENDERED`` above, because the two mean opposite things and merging
#: them would destroy the only useful distinction here:
#:
#:     _ADOPTER_RENDERED   another repo owns writing this. Correct as it stands.
#:     _KNOWN_ORPHANED     NOBODY writes this. A defect, recorded so the guard
#:                         can ship and catch the NEXT one.
#:
#: An exemption list that mixes "fine" with "broken" tells a future reader
#: nothing, and the entry describing a real bug is the one that goes unread.
#: (scitex-hub made this argument about a different list of mine on 2026-08-18
#: and it was right: a live defect filed under a heading nobody searches is a
#: defect that has been hidden rather than tracked.)
#:
#: WHY SHIP THE GUARD RED-LISTED INSTEAD OF WAITING FOR THE FIX: the fix is a
#: design decision that lost its rationale when the operator ruled hub keeps its
#: own shell, so it is genuinely open. Meanwhile this check catches any NEW
#: orphan the moment it appears. Holding a working guard hostage to an unrelated
#: decision leaves the class undefended for as long as the decision takes.
#:
#: Every entry is tracked by
#: scitex-ui-mobile-active-pane-has-no-writer-panes-unreachable-below-768px-20260818
#: and the list must SHRINK. `test_no_stale_entries_in_known_orphaned` fails if
#: an entry acquires a writer, so a fixed class cannot linger here pretending
#: the debt is still owed.
_KNOWN_ORPHANED: dict[str, str] = {
    # THE DEFECT THIS FILE WAS WRITTEN FOR. mobile.css hides every pane below
    # 768px and reveals `.mobile-active-pane` — a class that appears in exactly
    # one file, mobile.css itself, and that no template/js/ts ever writes.
    # Measured at 390x844: zero visible clickable elements on the whole page.
    "mobile-active-pane": "the reveal half of the <=768px single-pane rule; no writer anywhere",
    "mobile-tab-bar": "the switcher the reveal rule assumes; never rendered",
    # The NEWER single-pane branch in the same stylesheet. It has a writer, but
    # in scitex-hub, not here — and per the operator's 2026-08-18 ruling hub
    # keeps its own shell, so it is not going to become this package's markup.
    # Listed rather than filed under _ADOPTER_RENDERED because no adopter is
    # CONTRACTUALLY expected to write it; that would be a claim I cannot support.
    "workspace-layout": "second single-pane branch; written by hub's own shell, not by any declared adopter contract",
    "workspace-pane": "child of workspace-layout, same story",
    # Styled-but-never-rendered leftovers, unrelated to the mobile defect.
    "ws-apps-nav": "styled in workspace-three-col.css; no template emits it",
    "ws-viewer-mode-toggle-btn": "styled in workspace-viewer-preview.css; no writer",
    "ws-worktree-empty": "styled in workspace-three-col.css; no writer",
}


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
        if cls not in written
        and cls not in _ADOPTER_RENDERED
        and cls not in _KNOWN_ORPHANED
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
            "and record it in the shell contract. Do NOT add it to "
            "_KNOWN_ORPHANED either: that list is a CEILING for debt that "
            "predates this guard, and it must only ever shrink.",
        ]
        pytest.fail("\n".join(lines))


def test_no_stale_entries_in_known_orphaned() -> None:
    """An entry that has acquired a writer must be deleted, not left standing.

    A ceiling list rots the same way an exemption list does: once a class is
    finally written, its entry silences nothing while still reading as
    outstanding debt — and worse, the NAME keeps its exemption, so something
    unrelated could later reuse it and inherit a pass nobody granted.

    This is the half that makes the ceiling honest. Without it, "the list must
    only shrink" is an instruction nobody enforces, which is the same shape as
    the defect this whole file exists to catch: a rule with no mechanism behind
    it.
    """
    # Arrange
    written = _written_tokens()
    # Act
    now_written = {cls for cls in _KNOWN_ORPHANED if cls in written}
    # Assert
    assert not now_written, (
        "these classes now HAVE a writer, so their _KNOWN_ORPHANED entries are "
        f"stale and must be deleted: {sorted(now_written)}"
    )


def test_known_orphaned_entries_are_still_styled() -> None:
    """An entry whose CSS rule is gone must also be deleted.

    The other way a ceiling entry goes stale: the fix was to DELETE the rule
    rather than to write the class. Then the entry describes nothing at all —
    it neither exempts nor documents — and it is pure noise pointing at a file
    that no longer mentions the name.
    """
    # Arrange
    layout = _layout_state_classes()
    # Act
    no_longer_styled = {cls for cls in _KNOWN_ORPHANED if cls not in layout}
    # Assert
    assert not no_longer_styled, (
        "these classes are no longer used in any `display` rule, so their "
        "_KNOWN_ORPHANED entries describe nothing and must be deleted: "
        f"{sorted(no_longer_styled)}"
    )
