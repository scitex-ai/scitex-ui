#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_describedby_is_shared_not_owned.py

"""`aria-describedby` is a LIST, and no component may assign it.

THE COLLISION THIS PREVENTS. Two components legitimately describe the same
control: `app/dim` explains why it is unusable, `app/tooltip` explains what it
does. Both are worth hearing. But the attribute holds a SPACE-SEPARATED LIST of
ids, and a component that treats it as a scalar and calls `setAttribute`
discards whatever the other one wrote — whichever runs second wins.

scitex-app named the fix: "the ownable unit is not the attribute, it is the ID."
Each component adds and removes only its own id, and the race stops existing
instead of being arbitrated.

WHY THIS NEEDS A TEST RATHER THAN A CONVENTION. Today dim sets `data-tooltip` to
the SAME text it puts in its reason node, so both descriptions say the same
thing and the collision is INVISIBLE. It works by coincidence. The first time a
consumer sets its own `data-tooltip` on a dimmable control, the denial reason is
silently replaced by the tooltip text — nothing fails, and a screen-reader user
is simply told the wrong thing.

AND THE TEARDOWN HALF IS UNDETECTABLE ANY OTHER WAY. Measured by scitex-app in
Chrome 151 over CDP (`Accessibility.getFullAXTree`):

    aria-describedby="dim-reason tip-desc"   -> both, in that order
    aria-describedby="tip-desc dim-reason"   -> the reverse, exactly
    aria-describedby="dim-reason no-such-id" -> "Sign in to use this."

That last row is the important one. A DANGLING id produces no error, no warning
and no gap — the description computes cleanly from whatever survives, and the
accessibility tree looks perfectly healthy while carrying one description
instead of two. So a broken teardown cannot be caught by inspecting the computed
description. It can only be caught by asserting on the id LIST, which is what
this module does.

SCOPE. Source-level, like every guard in this directory: it reads the TypeScript
and checks which API each component calls. It cannot execute the DOM code — this
repo has no JS test runner — so it verifies that neither component can assign,
not that the resulting list is correct at runtime. The runtime behaviour is
covered by `tsc` and by scitex-app's browser measurement above.
"""

from __future__ import annotations

import re

from tests._checkout import static_dir

_TS = static_dir() / "ts"

#: `setAttribute("aria-describedby", ...)` — the assignment that discards.
_ASSIGNS = re.compile(r'setAttribute\(\s*["\']aria-describedby["\']')

#: `removeAttribute("aria-describedby")` — clearing, which discards just as much.
_CLEARS = re.compile(r'removeAttribute\(\s*["\']aria-describedby["\']')

#: `= "aria-describedby"` — BINDING the literal to a name.
#:
#: WHY THIS EXISTS: `_ASSIGNS` and `_CLEARS` are anchored on the LITERAL inside
#: the call, which is deliberate — it is what lets the helper assign through its
#: own `ATTR` constant without tripping its own guard. scitex-app read that,
#: confirmed the design is right, and then named the gap it leaves:
#:
#:     const A = "aria-describedby";
#:     el.setAttribute(A, ...);        <- invisible to _ASSIGNS
#:
#: A component that declares its OWN constant evades the literal anchor and can
#: clobber the shared list. Measured 2026-09-04: no file does this today, and
#: `setAttribute(CONST, ...)` has exactly two sites in ts/ — the helper (correct)
#: and `_Dim.ts:196` writing a DIFFERENT attribute through `ATTR_SIGN_IN_URL`.
#: So the evading SHAPE is already idiomatic inside a guarded file. Proximity,
#: not abuse — which is the argument for closing it while it is still cheap.
#:
#: THE ANCHOR IS THE ASSIGNMENT, NOT THE MENTION, and that is what makes this
#: affordable. scitex-app first proposed asserting ZERO literal occurrences
#: inside _WRITERS and measured it failing on arrival — `_Dim.ts` has 4 and
#: `_Tooltip.ts` 3, every one legitimate (the import path, and prose). Excluding
#: those needs comment-stripping and import-anchoring, i.e. re-importing the
#: hardest problem in this repo's guards to close a narrow gap.
#:
#: Requiring `=` before the string sidesteps all of it:
#:     from "../../_base/aria-describedby"    no `=`  -> ignored
#:     // aria-describedby is the a11y path   no `=`  -> ignored
#:     const A = "aria-describedby";                  -> MATCHED
#:
#: WHAT IT DOES NOT CATCH, stated so a pass is not read as more than it is:
#: deliberate construction (`"aria-" + "describedby"`, a template literal, a
#: computed key). This raises the floor against the ACCIDENTAL path — someone
#: reaching for setAttribute naturally — and does not claim to defeat a
#: determined bypass. A guard that claimed the latter would be lying.
_BINDS = re.compile(r'=\s*["\']aria-describedby["\']')

#: The shared helpers every writer must go through.
#:
#: THE TRAILING PAREN IS LOad-BEARING and was added because a probe caught its
#: absence. Checking for the bare identifier is satisfied by the IMPORT LINE:
#:
#:     import { addDescribedBy, removeDescribedBy } from "../../_base/..."
#:
#: so a component that imports the helper and never calls it passed the guard.
#: The probe "tooltip stops adding its description id" deleted the call, left
#: the import, and the guard stayed GREEN — a detector satisfied by the
#: paperwork rather than the behaviour.
_ADD = "addDescribedBy("
_REMOVE = "removeDescribedBy("

#: Components that describe controls and therefore share the attribute.
_WRITERS = {
    "dim": _TS / "app" / "dim" / "_Dim.ts",
    "tooltip": _TS / "app" / "tooltip" / "_Tooltip.ts",
}

_HELPER = _TS / "_base" / "aria-describedby.ts"


def test_the_shared_helper_exists() -> None:
    """Anti-vacuity: every guard below is about code that must be present."""
    # Arrange
    path = _HELPER

    # Act
    present = path.is_file()

    # Assert
    assert present, (
        f"{path} is missing. Every assertion in this module is about routing "
        f"writes through it, so its absence makes them all vacuous."
    )


def test_dim_writes_through_the_helper() -> None:
    """dim must add its reason id, not assign the attribute."""
    # Arrange
    source = _WRITERS["dim"].read_text()

    # Act
    routed = _ADD in source

    # Assert
    assert routed, (
        f"_Dim.ts does not call {_ADD}. It must add its reason node's id to "
        f"the list; assigning would discard app/tooltip's description."
    )


def test_tooltip_writes_through_the_helper() -> None:
    """tooltip must add its description id, not assign the attribute."""
    # Arrange
    source = _WRITERS["tooltip"].read_text()

    # Act
    routed = _ADD in source

    # Assert
    assert routed, (
        f"_Tooltip.ts does not call {_ADD}. Without it the tooltip text is "
        f"never exposed to assistive technology at all — `data-tooltip` is a "
        f"plain data attribute that nothing announces."
    )


def test_dim_removes_only_its_own_id() -> None:
    """Teardown must not clear the attribute.

    Undetectable in the computed description: a cleared attribute and a
    correctly-scoped removal both produce a healthy-looking tree.
    """
    # Arrange
    source = _WRITERS["dim"].read_text()

    # Act
    scoped = _REMOVE in source

    # Assert
    assert scoped, (
        f"_Dim.ts does not call {_REMOVE}. Clearing aria-describedby on "
        f"teardown removes descriptions dim does not own, and the symptom — "
        f"one description instead of two — appears nowhere."
    )


def test_tooltip_removes_only_its_own_id() -> None:
    """Same contract on the other side, and it is the likelier one to break.

    The tooltip hides on scroll, resize, mouseleave and focusout, so its
    teardown path runs far more often than dim's.
    """
    # Arrange
    source = _WRITERS["tooltip"].read_text()

    # Act
    scoped = _REMOVE in source

    # Assert
    assert scoped, (
        f"_Tooltip.ts does not call {_REMOVE}. It hides on four separate "
        f"events, so an unscoped teardown would wipe dim's denial reason on "
        f"the next scroll."
    )


def test_no_component_assigns_the_attribute() -> None:
    """The assignment that started this. Neither writer may do it."""
    # Arrange
    offenders = {
        name: _ASSIGNS.search(path.read_text())
        for name, path in _WRITERS.items()
    }

    # Act
    guilty = sorted(name for name, hit in offenders.items() if hit)

    # Assert
    assert not guilty, (
        f"{guilty} assign aria-describedby wholesale. The attribute is a LIST "
        f"shared between components; assigning silently discards the other's "
        f"description, and the computed result still looks healthy."
    )


def test_no_component_clears_the_attribute() -> None:
    """Clearing discards exactly as much as assigning, and reads as cleanup."""
    # Arrange
    offenders = {
        name: _CLEARS.search(path.read_text()) for name, path in _WRITERS.items()
    }

    # Act
    guilty = sorted(name for name, hit in offenders.items() if hit)

    # Assert
    assert not guilty, (
        f"{guilty} call removeAttribute('aria-describedby'). Use "
        f"{_REMOVE} so only the calling component's id is dropped — the "
        f"other description must survive."
    )


def test_the_helper_is_the_only_place_the_attribute_is_written() -> None:
    """One writer for the list mechanics, so the rule lives in one place.

    Deliberately POSITIVE: the helper is the ONE file allowed to assign, and if
    it stops doing so the components' calls write nothing at all.

    It assigns through a CONSTANT (`setAttribute(ATTR, ...)`) rather than the
    literal, which is why `_ASSIGNS` — anchored on the literal — does not and
    should not match it. That is the mechanical difference between the file
    that owns the attribute and the files forbidden from touching it.
    """
    # Arrange
    source = _HELPER.read_text()

    # Act
    writes = "setAttribute(ATTR" in source

    # Assert
    assert writes, (
        "the helper no longer assigns aria-describedby via its ATTR constant, "
        "so either the mechanics moved or the constant was renamed. Every "
        "addDescribedBy/removeDescribedBy call in the components would then "
        "be writing nothing, silently."
    )


def test_the_assignment_pattern_can_actually_match() -> None:
    """Positive control: a guard that cannot fire forbids nothing."""
    # Arrange
    sample = 'el.setAttribute("aria-describedby", node.id);'

    # Act
    matched = _ASSIGNS.search(sample)

    # Assert
    assert matched is not None, (
        "_ASSIGNS cannot match a real assignment, so every guard forbidding "
        "one passes on any input."
    )


def test_the_assignment_pattern_ignores_a_different_attribute() -> None:
    """Negative control: it must fire on THIS attribute and no other.

    Both components legitimately assign `aria-disabled` and others. A pattern
    that caught those would forbid correct behaviour — dim's whole design rests
    on setting aria-disabled.
    """
    # Arrange
    sample = 'el.setAttribute("aria-disabled", "true");'

    # Act
    matched = _ASSIGNS.search(sample)

    # Assert
    assert matched is None, (
        "_ASSIGNS matched an assignment to a DIFFERENT aria attribute. It "
        "would forbid `aria-disabled`, which dim is required to set — a guard "
        "that makes correct code impossible."
    )


def test_the_guards_read_source_that_may_mention_the_forbidden_call() -> None:
    """The documentation-inversion risk, stated and bounded rather than assumed.

    This module's patterns are substring detectors over TypeScript that
    DOCUMENTS why it no longer assigns. If a component's comment ever spells
    the forbidden call literally, these guards would flag the best-documented
    file as the guilty one — the inversion this repo has shipped twice.

    It does not happen TODAY: the components describe the rule in prose without
    writing the literal call. This asserts that, so the day someone adds an
    illustrative code sample to a comment, this fails and names the fix
    (strip comments first, as test_dim_renders_a_verdict.py does) rather than
    the components mysteriously appearing to violate the rule.
    """
    # Arrange
    sources = {name: path.read_text() for name, path in _WRITERS.items()}

    # Act
    mentions = sorted(
        name
        for name, src in sources.items()
        for line in src.splitlines()
        if _ASSIGNS.search(line) and line.lstrip().startswith(("//", "*", "/*"))
    )

    # Assert
    assert not mentions, (
        f"{mentions} mention the forbidden call inside a COMMENT. The guards "
        f"in this module do not strip comments, so that prose now reads as a "
        f"violation. Either reword the comment or add comment-stripping here — "
        f"do not weaken the pattern."
    )


def test_the_clear_pattern_can_actually_match() -> None:
    """Positive control for the second forbidden call."""
    # Arrange
    sample = 'el.removeAttribute("aria-describedby");'

    # Act
    matched = _CLEARS.search(sample)

    # Assert
    assert matched is not None, (
        "_CLEARS cannot match a real removeAttribute call, so the guard "
        "against clearing is inert."
    )


def test_an_unused_import_does_not_satisfy_the_helper_guards() -> None:
    """The hole a probe found: paperwork is not behaviour.

    An earlier version checked for the bare identifier `addDescribedBy`, which
    the import line contains. Deleting the CALL while leaving the import kept
    the guard green — it verified that the component had been told about the
    helper, not that it used it.

    This is the same shape as a detector satisfied by a mention rather than an
    instance, arriving through imports instead of comments.
    """
    # Arrange
    import_only = (
        'import { addDescribedBy, removeDescribedBy } from "../../_base/x";\n'
        "export function show(el) { el.classList.add('x'); }\n"
    )

    # Act
    satisfied = _ADD in import_only

    # Assert
    assert not satisfied, (
        f"the helper guard is satisfied by an import alone ({_ADD!r} matched a "
        f"file that never calls it). Require the call, not the identifier."
    )


def test_the_clear_pattern_ignores_a_different_attribute() -> None:
    """Negative control: it must not fire on unrelated attribute removal.

    Both components legitimately remove `aria-disabled`, `data-tooltip` and
    others. A pattern that caught those would forbid correct teardown.
    """
    # Arrange
    sample = 'el.removeAttribute("data-tooltip");'

    # Act
    matched = _CLEARS.search(sample)

    # Assert
    assert matched is None, (
        "_CLEARS matched the removal of an unrelated attribute, so it would "
        "forbid the ordinary teardown both components must perform."
    )


def test_the_bind_pattern_matches_a_private_constant() -> None:
    """POSITIVE CONTROL: the exact evasion scitex-app named must be caught.

    Without this, an over-tightened pattern reports a clean tree forever while
    the hole it was written for stays open.
    """
    # Arrange
    sample = 'const A = "aria-describedby";'

    # Act
    matched = _BINDS.search(sample)

    # Assert
    assert matched is not None, (
        "_BINDS missed a private constant binding the attribute name, which is "
        "the one thing it exists to catch."
    )


def test_the_bind_pattern_ignores_the_import_path() -> None:
    """NEGATIVE CONTROL: the module path is not a binding.

    Every writer imports from `_base/aria-describedby`, so a pattern that fired
    on the path would flag correct code in every file it guards — which is
    precisely how the zero-occurrences proposal died.
    """
    # Arrange
    sample = 'import { addDescribedBy } from "../../_base/aria-describedby";'

    # Act
    matched = _BINDS.search(sample)

    # Assert
    assert matched is None, (
        f"_BINDS matched an import path: {sample!r}. Every guarded file "
        "contains one, so this would be a permanent false positive."
    )


def test_the_bind_pattern_ignores_prose() -> None:
    """NEGATIVE CONTROL: a comment naming the attribute is not a binding.

    This file's own docstring names it many times. A detector that ate its own
    documentation would be unusable.
    """
    # Arrange
    sample = "// aria-describedby holds a space-separated list of ids"

    # Act
    matched = _BINDS.search(sample)

    # Assert
    assert matched is None, (
        f"_BINDS matched prose: {sample!r}. Mentioning the attribute must "
        "never be an offence; only binding it to a name is."
    )


def test_only_the_helper_binds_the_attribute_name() -> None:
    """No component may declare its own constant for the shared attribute.

    The helper binds it once, at `_base/aria-describedby.ts`, and that single
    binding is what makes the helper the only writer. A component with its own
    constant can call `setAttribute` through it and clobber the shared list
    without tripping `_ASSIGNS`, which anchors on the literal.
    """
    # Arrange
    offenders = sorted(
        str(path.relative_to(_TS))
        for path in _TS.rglob("*.ts")
        if path != _HELPER and _BINDS.search(path.read_text())
    )

    # Act
    guilty = offenders

    # Assert
    assert not guilty, (
        "These modules bind the literal \"aria-describedby\" to a name of their "
        f"own: {', '.join(guilty)}. A private constant evades _ASSIGNS and lets "
        "the module assign the attribute directly, discarding every other "
        "component's description id. Import addDescribedBy/removeDescribedBy "
        "from _base/aria-describedby instead — it owns the only binding."
    )


def test_the_helper_still_binds_it() -> None:
    """Anti-vacuity: the guard above is meaningless if nothing binds it at all.

    If the helper stopped declaring the constant — renamed, inlined, moved —
    `test_only_the_helper_binds_the_attribute_name` would pass over an empty
    world and report a clean tree while the shared-writer design had dissolved.
    """
    # Arrange
    source = _HELPER.read_text()

    # Act
    matched = _BINDS.search(source)

    # Assert
    assert matched is not None, (
        f"{_HELPER.name} no longer binds \"aria-describedby\" to a name. Either "
        "it was renamed or the helper stopped owning the attribute, and the "
        "sole-binding guard is now asserting nothing."
    )
