#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_dim_renders_a_verdict.py

"""Guards for the Dim component — the presentation half of an authorization verdict.

Dim renders "you cannot use this right now, and here is why" onto a control that
stays visible and reachable. It is a SIBLING of the disabled state, not a
synonym: "broken / not usable" and "available once you sign in" are different
facts, and rendering them identically tells the user that signing in will not
help — the login-wall behaviour the operator's 2026-09-02 ruling rules out.

SCOPE — WHAT THESE GUARDS CAN AND CANNOT SEE, said plainly because the gap is
real. They read SOURCE. This repo has no DOM harness and no JavaScript test
runner (``package.json`` defines exactly one script, ``typecheck``), so nothing
here executes ``applyVerdict`` or inspects a rendered element. What is verified
is structural: that the four kind strings are what the other side of the
boundary believes, that the accessibility decisions cannot be quietly reversed,
and that the stylesheet consumes the shared token rather than a literal.
Behaviour is covered only by ``tsc --noEmit`` and by review. A DOM harness would
be a genuine addition and is deliberately not smuggled in with this component.

WHY THE KIND STRINGS ARE PINNED HERE. They are a SECOND COPY of
``scitex_app.authz``'s constants, in another repo, and nothing on this side can
detect a rename on theirs. scitex-app is building the check that can — it reads
these constants out of this package's shipped source, and it runs on their side
on purpose: the breakage would appear here, but the cause is there, so a check
nearest the rename prevents rather than detects. Their own caveat, recorded
because it is load-bearing: that CI leg is currently a RECORD, not a required
context, so today nothing blocks on it.
"""

from __future__ import annotations

import re

import pytest

from tests._checkout import css_dir, static_dir

#: The five kinds, exactly as `scitex_app.authz` spells them.
#:
#: UNRESOLVED added 2026-09-05, by the route the previous version of this file
#: prescribed: scitex-app's implementation reached a case with no verdict to
#: return, they announced it, and the shape was agreed before either side moved.
_EXPECTED_KINDS = {
    "ALLOWED": "allowed",
    "DENIED": "denied",
    "DENIED_NOT_SIGNED_IN": "denied-because-not-signed-in",
    "DENIED_NOT_ENTITLED": "denied-because-not-entitled",
    "UNRESOLVED": "unresolved",
}

#: `export const NAME = "value";`
_CONST = re.compile(r'export const (\w+)\s*=\s*"([^"]+)"')

#: A boolean convenience over the verdict, in any of its tempting spellings.
_BOOLEAN_HELPER = re.compile(r"\bis(?:Allowed|Denied|Dim|Disabled|Permitted)\b")

#: A property literally named `allowed` — the same collapse by another route.
_ALLOWED_PROPERTY = re.compile(r"^\s*allowed\??\s*:", re.MULTILINE)

#: The native `disabled` attribute or property. Must NOT match `aria-disabled`.
_NATIVE_DISABLED = re.compile(
    r'setAttribute\(\s*"disabled"|(?<!aria-)\bel\.disabled\s*='
)

#: Any literal opacity value, e.g. `opacity: 0.5`.
_LITERAL_OPACITY = re.compile(r"opacity:\s*[0-9.]+")

#: The `Verdict` union body, used to count its members.
_UNION = re.compile(r"export type Verdict =([^;]+);", re.DOTALL)


#: A `/* ... */` block comment, including JSDoc.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

#: A line whose first non-space character starts a `//` comment.
#:
#: Deliberately anchored rather than matching `//` anywhere: a mid-line `//`
#: also occurs inside string literals ("https://..."), and a stripper that ate
#: those would silently remove CODE, turning these guards vacuous in the one
#: direction nobody would notice.
_LINE_COMMENT = re.compile(r"^[ \t]*//.*$", re.MULTILINE)


def _strip_ts_comments(text: str) -> str:
    """Remove comments so that PROSE ABOUT a construct is not read AS the construct.

    THIS EXISTS BECAUSE IT ALREADY HAPPENED, TWICE. In #180 a CSS guard read a
    comment saying a file deliberately does NOT use a token as evidence that it
    DOES. Writing this module reproduced it exactly: the docstring in types.ts
    explaining why there is no `isAllowed` helper contains the string
    `isAllowed`, so the guard forbidding that helper fired on the sentence
    forbidding it.

    That is a documentation inversion — a substring detector makes the file that
    best explains why it avoids something look identical to the file that still
    does it, which penalises exactly the code that documents its reasoning.
    """
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def _types_src() -> str:
    raw = (static_dir() / "ts" / "app" / "dim" / "types.ts").read_text()
    return _strip_ts_comments(raw)


def _dim_src() -> str:
    raw = (static_dir() / "ts" / "app" / "dim" / "_Dim.ts").read_text()
    return _strip_ts_comments(raw)


def _css_src() -> str:
    return (css_dir() / "app" / "dim.css").read_text()


def _union_members() -> list[str]:
    """Return the member type names of the `Verdict` union.

    Raises rather than asserting when the union cannot be found: a missing union
    is a broken instrument, not a failed contract, and the two should not report
    themselves the same way.
    """
    match = _UNION.search(_types_src())
    if match is None:
        raise RuntimeError(
            "could not locate `export type Verdict = ...;` in types.ts — the "
            "guard cannot count members it cannot find"
        )
    return re.findall(r"\b(\w+Verdict)\b", match.group(1))


@pytest.mark.parametrize(("name", "value"), sorted(_EXPECTED_KINDS.items()))
def test_each_kind_constant_keeps_the_string_scitex_app_uses(
    name: str, value: str
) -> None:
    """The kind vocabulary must not drift from scitex_app.authz's.

    A rename on their side is invisible to both suites — four kinds before, four
    after — so this pins the VALUES rather than merely counting them. If this
    goes red, do not edit it to match: find out whether scitex-app renamed a
    kind, because every verdict of that kind is currently falling through the
    switch on this side.
    """
    # Arrange
    source = _types_src()

    # Act
    declared = dict(_CONST.findall(source))

    # Assert
    assert declared.get(name) == value, (
        f"`{name}` is {declared.get(name)!r} in types.ts, expected {value!r}. "
        f"These four strings are a shared vocabulary with scitex_app.authz. If "
        f"scitex-app renamed this kind, this component has stopped handling it: "
        f"the switch falls through and the control renders as though the "
        f"verdict never arrived. Declared constants: {sorted(declared)}"
    )


def test_the_verdict_union_has_exactly_five_members() -> None:
    """A SIXTH kind must not appear quietly.

    THIS GUARD WORKED, and the count moved for the reason it named. Its previous
    version said: "Four are complete only for the server-rendered path. The
    moment anything fetches a verdict client-side, 'authorization not yet
    resolved' needs its own kind — and that is a conversation with scitex-app,
    not a local edit."

    That is precisely what happened on 2026-09-05. scitex-app's A/B
    decomposition needed a tri-state resolve, case B (attempted and failed) had
    no verdict to return, they ANNOUNCED it rather than shipping it, and the
    shape — one `unresolved`, not one per axis, no payload — was agreed before
    either side moved. The number is 5 because a conversation concluded, not
    because a build was red.

    The bar is unchanged for the next one. Adding a PAYLOAD to an existing kind
    remains the backward compatible way to carry new information and does not
    trip this — `upgrade_url` on not-entitled is arriving that way.
    """
    # Arrange
    expected = 5

    # Act
    members = _union_members()

    # Assert
    assert len(members) == expected, (
        f"the Verdict union has {len(members)} members ({members}), expected "
        f"{expected}. A new kind breaks exhaustiveness for every consumer's "
        f"switch and needs coordination with scitex-app before it ships."
    )


def test_dim_never_sets_the_native_disabled_attribute() -> None:
    """`disabled` would take the explanation out of tab order.

    This is the whole accessibility argument for dim being its own state: the
    native attribute removes the control from the tab sequence, so a keyboard
    user never reaches the one piece of text telling them that signing in would
    fix this.
    """
    # Arrange
    source = _dim_src()

    # Act
    offender = _NATIVE_DISABLED.search(source)

    # Assert
    assert offender is None, (
        f"_Dim.ts sets the native disabled attribute or property "
        f"({offender.group(0)!r} if matched). Use `aria-disabled` instead — "
        f"`disabled` drops the control out of tab order, making the reason "
        f"attached via aria-describedby unreachable for the users who most "
        f"need it."
    )


def test_dim_sets_aria_disabled() -> None:
    """Dimmed but still announcing as operable is worse than either state alone."""
    # Arrange
    source = _dim_src()

    # Act
    present = 'setAttribute("aria-disabled", "true")' in source

    # Assert
    assert present, (
        "_Dim.ts no longer sets aria-disabled. Without it the control looks "
        "unavailable and claims to be available — the two halves disagree, and "
        "assistive technology believes the claim."
    )


@pytest.mark.parametrize("filename", ["types.ts", "_Dim.ts"])
def test_no_boolean_convenience_over_the_verdict(filename: str) -> None:
    """No `isAllowed()`, in either file.

    It would be shorter than `verdict.kind === ALLOWED`, read naturally, pass
    review, and silently collapse "sign in and this works" into "this will never
    work". scitex-app asserts the same absence on their side.
    """
    # Arrange
    sources = {"types.ts": _types_src, "_Dim.ts": _dim_src}

    # Act
    offender = _BOOLEAN_HELPER.search(sources[filename]())

    # Assert
    assert offender is None, (
        f"{filename} defines a boolean convenience over the verdict "
        f"({offender.group(0)!r} if matched). Write the comparison instead — "
        f"the point is that the reader sees themselves choosing which denials "
        f"they are lumping together."
    )


def test_the_verdict_types_declare_no_allowed_property() -> None:
    """A boolean field invites the same collapse the helper would."""
    # Arrange
    source = _types_src()

    # Act
    offender = _ALLOWED_PROPERTY.search(source)

    # Assert
    assert offender is None, (
        "types.ts declares a property named `allowed`. Its presence invites "
        "`if (verdict.allowed)`, which treats 'not signed in' and 'never' as "
        "the same answer."
    )


def test_dim_css_consumes_the_shared_disabled_token() -> None:
    """Dim is a variant of one appearance, not a fourth private definition."""
    # Arrange
    source = _css_src()

    # Act
    consumes = "var(--disabled-opacity)" in source

    # Assert
    assert consumes, (
        "app/dim.css no longer consumes --disabled-opacity. Dim shares the "
        "visual weight of a control you cannot operate; only the AFFORDANCE "
        "differs, and that is carried by cursor and focusability."
    )


def test_dim_css_hardcodes_no_opacity() -> None:
    """#180 consolidated sixteen literals into one token a week ago."""
    # Arrange
    source = _css_src()

    # Act
    offender = _LITERAL_OPACITY.search(source)

    # Assert
    assert offender is None, (
        f"app/dim.css hardcodes an opacity "
        f"({offender.group(0)!r} if matched). That is the drift #180 removed — "
        f"two values propagated by copy-paste until nobody could say which was "
        f"intended."
    )


def test_the_reason_is_exposed_via_aria_describedby() -> None:
    """The assistive and keyboard path, which the tooltip cannot serve.

    `app/tooltip` binds mouseenter/mouseleave only — no focus, no
    aria-describedby (measured 2026-09-03). Delegating the explanation to it
    alone would put it exactly where a keyboard user cannot get it.
    """
    # Arrange
    source = _dim_src()

    # Act
    present = 'addDescribedBy(el, node.id, "first")' in source

    # Assert
    assert present, (
        "_Dim.ts no longer adds its reason node to aria-describedby, so the "
        "control announces as unavailable with no stated reason.\n"
        "NOTE it must ADD to the list, never setAttribute: aria-describedby "
        "holds several ids and app/tooltip writes its own. Assigning would "
        "silently discard the other description — and Chrome computes a "
        "healthy-looking result either way, so nothing would show it."
    )


def test_dim_never_assigns_the_describedby_attribute_wholesale() -> None:
    """Assigning would discard a description another component owns.

    `aria-describedby` is a LIST. dim was the only writer until app/tooltip
    began adding its own id, at which point `setAttribute` became a silent
    overwrite — and a silent one specifically, because the computed description
    still resolves cleanly from whatever survives.
    """
    # Arrange
    source = _dim_src()

    # Act
    offender = 'setAttribute("aria-describedby"' in source

    # Assert
    assert not offender, (
        "_Dim.ts assigns aria-describedby wholesale. Use addDescribedBy / "
        "removeDescribedBy from _base/aria-describedby, which add and remove "
        "only this component's id and leave every other description intact."
    )


def test_dim_adds_its_reason_first_in_the_description_order() -> None:
    """The denial must be announced before the description.

    Readers announce the list in IDREF order (measured in Chrome 151), so a
    reason added "last" would tell the user what the control does and only
    belatedly that they cannot use it — which removes the information that
    would make someone decide signing in is worth it.
    """
    # Arrange
    source = _dim_src()

    # Act
    first = '"first"' in source

    # Assert
    assert first, (
        "_Dim.ts no longer adds its reason at position 'first'. A denial is "
        "ACTIONABLE and a tooltip merely DESCRIBES; the actionable sentence "
        "has to arrive first, and neither component controls which of them "
        "runs first, so the position argument is what guarantees the order."
    )


def test_the_reason_is_also_exposed_via_data_tooltip() -> None:
    """The sighted mouse path — the half aria-describedby does not cover."""
    # Arrange
    source = _dim_src()

    # Act
    present = 'setAttribute("data-tooltip"' in source

    # Assert
    assert present, (
        "_Dim.ts no longer sets data-tooltip, so sighted mouse users lose the "
        "reason. Hub specified both paths; neither alone reaches everyone."
    )


def test_dim_css_is_imported_by_the_app_bundle() -> None:
    """A stylesheet nobody imports ships dead.

    `app.css` is generated, so a component added without regenerating it looks
    complete in review and renders unstyled on a page.
    """
    # Arrange
    bundle = (css_dir() / "app.css").read_text()

    # Act
    imported = '@import "./app/dim.css";' in bundle

    # Assert
    assert imported, (
        "app/dim.css is not imported by app.css. Regenerate the bundle with "
        "`npx tsx css/_build-index.ts` from src/scitex_ui/static/scitex_ui."
    )


def test_the_constant_regex_finds_the_constants() -> None:
    """Anti-vacuity: the kind-pinning test must not assert about an empty dict."""
    # Arrange
    source = _types_src()

    # Act
    found = _CONST.findall(source)

    # Assert
    assert len(found) >= len(_EXPECTED_KINDS), (
        f"_CONST matched {len(found)} `export const` declarations, fewer than "
        f"the {len(_EXPECTED_KINDS)} kinds. The kind-pinning test would then be "
        f"comparing against an empty mapping and passing for the wrong reason."
    )


def test_the_boolean_helper_regex_can_match_a_boolean_helper() -> None:
    """Anti-vacuity: a broken regex would report a clean codebase."""
    # Arrange
    sample = "export function isAllowed(v: Verdict): boolean {}"

    # Act
    matched = _BOOLEAN_HELPER.search(sample)

    # Assert
    assert matched is not None, (
        "_BOOLEAN_HELPER cannot match a literal `isAllowed`, so its guard "
        "passes on any input whatsoever."
    )


def test_a_real_boolean_helper_still_trips_the_guard_after_stripping() -> None:
    """The load-bearing probe: stripping must not have BLUNTED the guard.

    The comment stripper was added because the guard fired on a docstring. There
    are two ways to make that red go away — repair the detector so prose stops
    counting, or weaken it so nothing counts — and both produce an identical
    green suite. This asserts the first: a genuine `isAllowed` in CODE, with a
    docstring above it, is still caught.
    """
    # Arrange
    sample = (
        "/** A helper like isAllowed is forbidden, see the card. */\n"
        "export function isAllowed(v: Verdict): boolean {\n"
        "  return v.kind === ALLOWED;\n"
        "}\n"
    )

    # Act
    offender = _BOOLEAN_HELPER.search(_strip_ts_comments(sample))

    # Assert
    assert offender is not None, (
        "after comment-stripping, a real `isAllowed` FUNCTION is no longer "
        "detected. The stripper has blunted the guard rather than repairing "
        "it: prose stopped counting and so did code."
    )


def test_the_comment_stripper_removes_prose_that_names_the_construct() -> None:
    """The other half of the pair: prose alone must NOT trip the guard."""
    # Arrange
    sample = "/** No isAllowed helper here, deliberately. */\nexport const X = 1;\n"

    # Act
    offender = _BOOLEAN_HELPER.search(_strip_ts_comments(sample))

    # Assert
    assert offender is None, (
        "a comment merely NAMING `isAllowed` still trips the guard, so a file "
        "that documents why it avoids the helper is indistinguishable from one "
        "that defines it."
    )


def test_the_comment_stripper_leaves_a_url_inside_a_string_alone() -> None:
    """A stripper that ate `https://` would remove code and pass vacuously.

    This is the failure direction nobody notices: over-stripping makes every
    negative assertion above succeed against an emptier and emptier file.
    """
    # Arrange
    sample = 'const u = "https://scitex.ai/signin";\n'

    # Act
    stripped = _strip_ts_comments(sample)

    # Assert
    assert "https://scitex.ai/signin" in stripped, (
        f"the comment stripper damaged a string literal containing `//`: "
        f"{stripped!r}. Over-stripping silently empties the source these "
        f"guards read, so every negative assertion would pass for the wrong "
        f"reason."
    )


def test_the_native_disabled_regex_can_match_a_native_disabled_call() -> None:
    """Anti-vacuity for the load-bearing accessibility guard."""
    # Arrange
    sample = 'el.setAttribute("disabled", "");'

    # Act
    matched = _NATIVE_DISABLED.search(sample)

    # Assert
    assert matched is not None, (
        "_NATIVE_DISABLED cannot match a real native-disabled call, so the "
        "guard forbidding it is inert."
    )


def test_the_native_disabled_regex_ignores_aria_disabled() -> None:
    """The discrimination that matters — the two spellings share a substring.

    Without this, a guard written to forbid `disabled` would also forbid
    `aria-disabled`, i.e. forbid the very attribute the component is required to
    set. That is the documentation-inversion shape: a substring detector that
    cannot tell a thing from its opposite.
    """
    # Arrange
    sample = 'el.setAttribute("aria-disabled", "true");'

    # Act
    matched = _NATIVE_DISABLED.search(sample)

    # Assert
    assert matched is None, (
        "_NATIVE_DISABLED matches `aria-disabled`, so it would reject the "
        "required attribute and force the component into the wrong behaviour."
    )


def test_the_literal_opacity_regex_can_match_a_literal() -> None:
    """Anti-vacuity for the token guard."""
    # Arrange
    sample = "opacity: 0.4;"

    # Act
    matched = _LITERAL_OPACITY.search(sample)

    # Assert
    assert matched is not None, (
        "_LITERAL_OPACITY cannot match a literal opacity, so the guard against "
        "hardcoding one is inert."
    )


def test_the_literal_opacity_regex_ignores_a_token_reference() -> None:
    """It must not fire on the correct spelling, or the component cannot comply."""
    # Arrange
    sample = "opacity: var(--disabled-opacity);"

    # Act
    matched = _LITERAL_OPACITY.search(sample)

    # Assert
    assert matched is None, (
        "_LITERAL_OPACITY matches a var() reference, so it would reject the "
        "very spelling the guard exists to require."
    )


def test_the_constant_regex_ignores_a_commented_out_declaration() -> None:
    """A commented-out declaration is NOT prose, and anchoring does not save you.

    scitex-app found this exact hole in their own scanner on 2026-09-03: they
    anchored on `export const NAME =` believing it immune to comments, and
    `// export const MOUNT_META_NAME = "stx-OLD"` matched perfectly and yielded
    the stale value. It is syntactically identical to the real thing.

    This repo is protected by stripping comments BEFORE searching, not by the
    anchor. That protection is what this asserts — remove the stripper and a
    deleted constant left behind in a comment would still read as present.
    """
    # Arrange
    sample = '// export const DENIED = "stale";\n'

    # Act
    matched = _CONST.search(_strip_ts_comments(sample))

    # Assert
    assert matched is None, (
        "a commented-out declaration was read as a live one. The kind-pinning "
        "guard would then accept a constant that has been DELETED, as long as "
        "its corpse remains in a comment — which is exactly the hole "
        "scitex-app found in their own scanner, where anchoring on "
        "`export const NAME =` matched the comment perfectly."
    )


def test_the_union_regex_finds_a_real_union() -> None:
    """Positive control for the union counter."""
    # Arrange
    sample = "export type Verdict =\n  | A\n  | B;\n"

    # Act
    matched = _UNION.search(sample)

    # Assert
    assert matched is not None, (
        "_UNION cannot match a real union declaration, so the exactly-four "
        "guard would be counting an empty match and passing vacuously."
    )


def test_the_union_regex_ignores_a_commented_out_union() -> None:
    """Negative control: a union in a comment is not a union."""
    # Arrange
    sample = "// export type Verdict = A | B;\nconst x = 1;\n"

    # Act
    matched = _UNION.search(_strip_ts_comments(sample))

    # Assert
    assert matched is None, (
        "a commented-out union was read as the live declaration, so deleting "
        "the real union while leaving it in a comment would go unnoticed."
    )


def test_the_allowed_property_regex_matches_a_real_property() -> None:
    """Positive control: it must recognise the field it forbids."""
    # Arrange
    sample = "interface V {\n  allowed: boolean;\n}\n"

    # Act
    matched = _ALLOWED_PROPERTY.search(sample)

    # Assert
    assert matched is not None, (
        "_ALLOWED_PROPERTY cannot match a real `allowed:` field, so the guard "
        "forbidding it is inert."
    )


def test_the_allowed_property_regex_ignores_a_mention_in_prose() -> None:
    """Negative control: naming the forbidden field must not trip the guard."""
    # Arrange
    sample = "// there is deliberately no allowed: property here\nconst x = 1;\n"

    # Act
    matched = _ALLOWED_PROPERTY.search(_strip_ts_comments(sample))

    # Assert
    assert matched is None, (
        "a comment explaining the ABSENCE of an `allowed:` property tripped "
        "the guard against it — the documentation inversion this module was "
        "written to eliminate."
    )


def test_the_block_comment_stripper_matches_a_block_comment() -> None:
    """Positive control for the stripper's own pattern."""
    # Arrange
    sample = "/* a JSDoc block */\nconst x = 1;\n"

    # Act
    matched = _BLOCK_COMMENT.search(sample)

    # Assert
    assert matched is not None, (
        "_BLOCK_COMMENT cannot match a block comment, so _strip_ts_comments "
        "removes nothing and every prose mention counts as code again."
    )


def test_the_block_comment_stripper_leaves_code_alone() -> None:
    """Negative control: it must not eat the code between comments."""
    # Arrange
    sample = "const kept = 1;\n"

    # Act
    matched = _BLOCK_COMMENT.search(sample)

    # Assert
    assert matched is None, (
        "_BLOCK_COMMENT matched a line with no block comment in it, so the "
        "stripper would delete code and every negative guard would pass "
        "against an emptied source."
    )


def test_the_line_comment_stripper_matches_a_line_comment() -> None:
    """Positive control for the line-comment half of the stripper."""
    # Arrange
    sample = "  // an explanatory line\n"

    # Act
    matched = _LINE_COMMENT.search(sample)

    # Assert
    assert matched is not None, (
        "_LINE_COMMENT cannot match an indented `//` comment, so prose on "
        "such lines still counts as code."
    )


def test_the_line_comment_stripper_ignores_a_url_in_a_string() -> None:
    """Negative control, and the reason the pattern is anchored to line start.

    `//` also appears inside every absolute URL. A stripper that removed from
    any `//` onward would truncate the string and silently delete code — a
    false negative, which is strictly worse than the false positive it fixes.
    """
    # Arrange
    sample = 'const u = "https://scitex.ai/signin";\n'

    # Act
    matched = _LINE_COMMENT.search(sample)

    # Assert
    assert matched is None, (
        "_LINE_COMMENT matched a URL inside a string literal. Stripping from "
        "there would remove real code and empty the source that every "
        "negative assertion in this module reads."
    )


def test_dim_is_registered_under_its_name() -> None:
    """A component absent from the registry is undiscoverable."""
    # Arrange
    from scitex_ui._components import Dim

    # Act
    name = Dim.name

    # Assert
    assert name == "dim", f"the Dim component registered as {name!r}"


def test_dim_points_at_its_stylesheet() -> None:
    """The registry path must match where the file actually lives."""
    # Arrange
    from scitex_ui._components import Dim

    # Act
    declared = Dim.css_file

    # Assert
    assert declared == "scitex_ui/css/app/dim.css", (
        f"Dim.css_file is {declared!r}, which does not match the shipped "
        f"stylesheet path."
    )


def test_dim_points_at_its_typescript_entry() -> None:
    """The registry path must match where the module actually lives."""
    # Arrange
    from scitex_ui._components import Dim

    # Act
    declared = Dim.ts_entry

    # Assert
    assert declared == "scitex_ui/ts/app/dim/index", (
        f"Dim.ts_entry is {declared!r}, which does not match the shipped "
        f"module path."
    )
