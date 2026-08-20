#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_mobile_panes_stay_reachable.py

"""No pane may be hidden below 768px without something able to bring it back.

THE DEFECT, measured 2026-08-18 in chromium at 390x844 against the rendered
shell — the first rendered-shell measurement this repo ever had:

    .ws-ai-pane      display:none   width 0
    .ws-viewer-pane  display:none   width 0
    .ws-module-pane  display:flex   width 390
    elements carrying .mobile-active-pane          0
    pane-switching rail / [data-pane-switch]       0
    VISIBLE clickable elements on the entire page  0

`mobile.css` hid every sidebar pane below 768px and revealed the active one via
`.mobile-active-pane` — a class that appears in exactly ONE file, mobile.css
itself, and that no template, js or ts in this package ever writes. The
destructive half shipped; the restorative half never ran. Console/Chat and
Viewer were not collapsed, they were UNREACHABLE, and the resizers that might
have dragged them back were hidden by the same media block.

WHY NOBODY NOTICED, and why this guard is shaped the way it is: nothing errors.
The page is valid, it paints, dark mode is correct, and there is no horizontal
overflow — my own overflow probe returned scrollWidth 390 == viewport 390, zero
offenders. Every cheap check passes. The failure is invisible to exactly the
tests one would think to write.

THE FIX THIS GUARD PINS is option (c): below 768px the three-column layout
becomes a vertical STACK. No switcher, no JS, no class. That removes the
orphaned reader rather than supplying it a writer — constitution §3, the
reader-with-no-writer should GO, not be joined.

WHAT THIS ASSERTS, and deliberately not more: that the shipped stylesheet does
not hide the declared panes at the mobile breakpoint. It is a STATIC check on
the CSS, which is weaker than the browser measurement that found the bug — but
it is the half that can run in CI on every change, and it is exactly the
property that regressed. The rendered measurement stays the acceptance test and
is recorded on the card; it needs a browser and a server and does not belong in
the unit suite.

The distinction matters because a green here does NOT mean "the shell is usable
on a phone". It means "nothing in this stylesheet hides a pane outright at that
breakpoint". Those are different claims and only the second is checked.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# From THIS FILE, never scitex_ui.__file__ — under a non-editable install the
# latter points into site-packages, and this guard would then assert about a
# different tree than the branch under review. PR #152 fixed that class across
# 19 modules after a guard was seen reporting pass or fail for one commit
# depending on the directory pytest ran from.
_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
)
_MOBILE = _CSS / "shell" / "mobile.css"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)

#: The panes an app declares through ``shell_context(panes=...)``. These are the
#: ones a user can legitimately expect to reach; ``ws-module-pane`` is the app's
#: own content and is always shown.
_DECLARED_PANES = ("ws-ai-pane", "ws-worktree-pane", "ws-viewer-pane")

#: The breakpoint the defect lives at.
_MOBILE_MEDIA = re.compile(r"@media[^{]*max-width:\s*768px[^{]*\{", re.I)


def _mobile_block() -> str:
    """The text inside `@media (max-width: 768px)`, comments stripped.

    Brace-matched rather than regex-extracted: the block contains nested rules,
    and a lazy `.*?` would stop at the first inner `}` and silently scan a
    fraction of it — a partial read that would let a hide rule further down go
    unseen while the test still passed.
    """
    text = _COMMENT.sub("", _MOBILE.read_text(errors="replace"))
    match = _MOBILE_MEDIA.search(text)
    if not match:
        return ""
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    return text[start:]


def test_the_mobile_media_block_is_found() -> None:
    """ANTI-VACUITY: an empty block makes every assertion below trivially true.

    Stated as a rule rather than merely applied, because scitex-hub asked for
    that after a mobile audit of mine reported "0 undersized touch targets" —
    while all 32 interactive elements were display:none. A check whose measured
    population is zero must FAIL, not pass.
    """
    # Arrange
    path = _MOBILE
    # Act
    block = _mobile_block()
    # Assert
    assert len(block) > 500, (
        f"extracted {len(block)} chars from the <=768px block in {path.name}; "
        "the file is ~284 lines, so this is a broken read and nothing asserted "
        "about its contents would mean anything"
    )


def test_the_brace_matcher_reaches_the_end_of_the_block() -> None:
    """The extractor must not stop at the first nested closing brace.

    Its own failure mode is a PARTIAL read, which looks identical to a clean
    one: fewer rules scanned, every assertion still green.
    """
    # Arrange
    block = _mobile_block()
    # Act
    rules = block.count("{")
    # Assert
    assert rules > 15, (
        f"only {rules} nested rules found inside the mobile block; the brace "
        "matcher stopped early and the scan is reading a fraction of the file"
    )


@pytest.mark.parametrize("pane", _DECLARED_PANES)
def test_a_declared_pane_is_not_hidden_outright_on_mobile(pane: str) -> None:
    """No `display: none` on a pane a user is meant to be able to reach.

    Parametrised per pane so a failure names WHICH one regressed, rather than
    reporting that "something" is hidden.
    """
    # Arrange
    block = _mobile_block()
    # Act — selectors that both mention this pane and set display:none
    offenders = [
        selector.strip()
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block)
        if pane in selector and re.search(r"display\s*:\s*none", body)
    ]
    # Assert
    assert not offenders, (
        f".{pane} is set to display:none below 768px by:\n"
        + "\n".join(f"    {o}" for o in offenders)
        + "\n\nA hidden pane is only acceptable if something can bring it back. "
        "The previous design revealed it via `.mobile-active-pane`, a class NO "
        "code in this package writes — so the pane was unreachable, not "
        "collapsed. Measured at 390x844: zero visible clickable elements on the "
        "whole page.\n"
        "Below 768px the three columns STACK. If you are re-introducing a "
        "single-pane mode, ship its writer in the same change."
    )


def test_no_rule_waits_on_a_class_nothing_writes() -> None:
    """`.mobile-active-pane` must not come back without a writer.

    This is the specific orphan that caused the defect. `test_shell_layout_
    classes_have_writers` catches the general class and currently carries this
    name in its `_KNOWN_ORPHANED` ceiling; when the stack fix lands, that entry
    retires. Asserting it here too is deliberate: this file is where someone
    looks when they are about to re-add a single-pane mode.
    """
    # Arrange
    block = _mobile_block()
    # Act
    orphaned = "mobile-active-pane" in block
    # Assert
    assert not orphaned, (
        "`.mobile-active-pane` is referenced in the <=768px block again. It has "
        "no writer anywhere in this package — it appears in mobile.css and "
        "nowhere else — so any rule depending on it never fires. Either ship "
        "the code that adds the class, or do not depend on it."
    )


def test_stacking_does_not_override_a_declared_unused_pane() -> None:
    """A pane declared `unused` must stay hidden, stack or no stack.

    CAUGHT IN THE FIX ITSELF, not in review of someone else's code. The first
    draft of the stacking rule wrote `display: flex !important` on all three
    panes. `.workspace-three-col > .ws-pane-unused { display: none }` in
    workspace-three-col.css carries NO `!important`, and `!important` outranks a
    normal declaration whatever the specificity — so every pane an app had
    explicitly declared `unused` would have been dragged back on screen at the
    width where screen space is scarcest.

    That is worse than the bug being fixed, because the app DECLARED its
    intent and the shell would have overridden it silently: constitution §2,
    a declaration that cannot be honoured must fail loudly, not evaporate.

    The rule this pins is not "avoid !important" — the mobile block is built on
    it and needs it to beat the desktop grid. It is that a blanket `!important`
    show-rule must exclude the panes something else is deliberately hiding.
    """
    # Arrange
    block = _mobile_block()
    # Act — show-rules (display != none) in the mobile block that name a pane
    unguarded = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
        if not re.search(r"display\s*:\s*(?!none)\S+\s*!important", body):
            continue
        for pane in _DECLARED_PANES:
            for part in selector.split(","):
                if pane in part and "ws-pane-unused" not in part:
                    unguarded.append(part.strip())
    # Assert
    assert not unguarded, (
        "these rules force a pane visible with `!important` below 768px "
        "without excluding `.ws-pane-unused`:\n"
        + "\n".join(f"    {u}" for u in sorted(set(unguarded)))
        + "\n\n`.ws-pane-unused` is how an app says `shell_context(panes="
        "{...: \"unused\"})`, and it hides with a plain `display: none` that any "
        "`!important` outranks. Add `:not(.ws-pane-unused)` to the selector so "
        "the stack shows the panes the app actually declared."
    )


def test_the_unused_pane_contract_is_still_written_the_way_this_assumes() -> None:
    """ANTI-VACUITY for the test above, and it is not a formality.

    That test is a no-op the moment `ws-pane-unused` is renamed or starts
    hiding some other way — it would scan for a class nobody writes, find no
    violations, and go green while the contract it guards is unenforceable.
    A guard whose subject has moved is the "check at the wrong layer" failure:
    it converts "I have not looked" into "I have looked".
    """
    # Arrange
    three_col = _CSS / "shell" / "workspace-three-col.css"
    # Act
    text = _COMMENT.sub("", three_col.read_text(errors="replace"))
    hides = re.search(
        r"\.ws-pane-unused\s*\{[^}]*display\s*:\s*none", text
    )
    # Assert
    assert hides, (
        f"{three_col.name} no longer hides `.ws-pane-unused` with `display: "
        "none`. The test above scans for exactly that class and would now pass "
        "vacuously. Point both at whatever replaced it."
    )
