#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_detectors_carry_controls.py

"""Every regex detector in this suite must carry controls in BOTH directions.

    it MATCHES a real instance           -> not blind
    it does NOT match a MENTION of one   -> not inverted

WHY THIS EXISTS, and it is not a style preference. Nearly every guard in
``tests/develop`` is a NEGATIVE assertion: "this pattern finds nothing bad in
the source." That shape passes trivially when the pattern is broken, when the
file moved, when the source is empty, or when the regex was never capable of
matching the thing it names. A green suite and a blind instrument are
indistinguishable from the outside, which is §2's "a gate that cannot fail is
not a gate" in its most common disguise.

THE HISTORY, because the rule was written down twice before it was enforced and
that is the whole argument for enforcing it:

  2026-08-26  #180 fixed a CSS guard that read a comment saying a file
              deliberately does NOT use a token as evidence that it DOES.
  2026-09-03  #181 reproduced the identical defect, in a guard written by the
              same author, one week later. `types.ts` documents why there is no
              `isAllowed` helper; that sentence contains `isAllowed`; the guard
              forbidding the helper fired on the prose forbidding it.
  Same night  scitex-app shipped the same shape independently, in another
              package, within the hour — their scanner matched a COMMENTED-OUT
              declaration and yielded a stale value. They had written their own
              version of this rule into their notes on 2026-08-20 and not acted
              on it for thirteen days.

Two agents, two written rules, three recurrences. Neither of us was careless
about the fact; both of us had recorded it. What neither had was anything that
fires without being recalled. So the rule stops being prose here.

WHY BOTH DIRECTIONS RATHER THAN ONE CHOSEN BY THE DETECTOR'S JOB. I proposed
picking the control to match the detector's failure mode — positive for guards
that assert an absence, negative for scanners that extract a value — with the
direction declared by the author. scitex-app refuted it with my own bug: my
absence-asserting guard's actual defect was a FALSE POSITIVE, the failure mode
my own taxonomy assigned to the other column. And a declared direction is worse
than no rule, because an author declaring a direction is an author exempting
themselves from the control that would have caught their bug. Their objection
was right and this file implements their form, not mine.

WHAT COUNTS AS A CONTROL, and the asymmetry is deliberate:

  POSITIVE  an assertion that the pattern MATCHED something. A string literal
            or a scan of the real tree both qualify — either demonstrates the
            instrument can fire at all.
  NEGATIVE  an assertion that the pattern did NOT match a specific string
            LITERAL. This one cannot be satisfied by scanning the tree, because
            "finds nothing in a clean tree" IS THE GUARD ITSELF, not a control
            on it. Accepting that would let a detector cite its own subject as
            its own control — the circularity this file exists to break.

THIS FILE IS ITSELF A DETECTOR, so it gets the treatment it enforces: the
fixtures at the bottom prove it reports a pattern with no controls AND stays
silent on one that has them. Without the second, "the codebase is clean" and
"the checker is broken" produce the same green.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from tests._checkout import REPO_ROOT

_TESTS = REPO_ROOT / "tests" / "develop"

#: Pattern methods whose result answers "did it match?".
_MATCH_METHODS = {"search", "match", "fullmatch", "findall", "finditer"}

#: Calls that pull content off disk. An argument containing one is a TREE SCAN,
#: never a fixed sample, however many string literals (paths) it also contains.
_READERS = {"read_text", "read_bytes", "open", "read", "readlines"}

#: Patterns exempted from one or both directions, each with a written reason.
#:
#: ONE ENTRY PER (module, pattern), never a blanket flag — §2's grandfathering
#: rule. `test_every_exemption_is_still_needed` deletes the entry's excuse the
#: moment the control appears, so an exemption cannot outlive its justification.
#: Seeded 2026-09-03 from the guard's own first run. NOT a grandfather flag —
#: every entry names one pattern, and `test_every_exemption_is_still_needed`
#: deletes it the moment both controls appear. The list is meant to shrink.
#:
#: test_dim_renders_a_verdict.py is DELIBERATELY ABSENT: it is the file whose
#: defect prompted this guard, so exempting it would have been the one
#: unacceptable entry. All eight of its patterns were controlled instead, and
#: writing those controls surfaced a real hole (a commented-out `export const`
#: reads as live unless comments are stripped first — the same defect
#: scitex-app found in their scanner the same night).
_EXEMPT: dict[tuple[str, str], str] = {
    # --- COMMENT-STRIPPER PATTERNS -------------------------------------------
    # These MATCH comments by design, so "must not match a mention" reads
    # oddly against them: a mention is exactly their subject. The direction
    # that means something here is "must not eat CODE" — over-stripping empties
    # the source every other guard reads, which is the silent failure. That is
    # a real, writable control; it has simply not been written yet.
    ("test_app_accents_agree_across_layers.py", "_CSS_COMMENT"): (
        "comment stripper; needs a does-not-eat-code control, not a "
        "does-not-match-a-mention one"
    ),
    ("test_mobile_panes_stay_reachable.py", "_COMMENT"): (
        "comment stripper; same shape as _CSS_COMMENT above"
    ),
    ("test_no_asset_paths_via_installed_package.py", "_PY_COMMENT_OR_DOCSTRING"): (
        "comment/docstring stripper; over-stripping is the hazard, not "
        "over-matching"
    ),
    ("test_primitives_define_each_token_once.py", "_CSS_COMMENT"): (
        "comment stripper; same shape"
    ),
    ("test_shell_layout_classes_have_writers.py", "_CSS_COMMENT"): (
        "comment stripper; same shape"
    ),
    # --- STRUCTURAL EXTRACTORS -----------------------------------------------
    # These pull a value out of source. Their real hazard is scitex-app's:
    # a COMMENTED-OUT declaration is syntactically identical to a live one, so
    # anchoring does not save you and a deleted symbol left in a comment still
    # reads as present. Genuine, unwritten debt — each needs both directions.
    ("test_app_accents_agree_across_layers.py", "_DECL"): "extractor; both directions unwritten",
    ("test_primitives_define_each_token_once.py", "_DECLARATION"): "extractor; both unwritten",
    ("test_shell_init_guards_its_containers.py", "_CONTAINER_ARG"): (
        "extractor; has a positive control, needs the commented-out-declaration "
        "negative"
    ),
    ("test_shell_init_guards_its_containers.py", "_GUARDED"): "extractor; both unwritten",
    ("test_shell_layout_classes_have_writers.py", "_CLASS_IN_SELECTOR"): "extractor; both unwritten",
    ("test_shell_layout_classes_have_writers.py", "_LAYOUT_PREFIX"): "extractor; both unwritten",
    ("test_shell_layout_classes_have_writers.py", "_RULE"): "extractor; both unwritten",
    ("test_shell_layout_classes_have_writers.py", "_WORDS"): "extractor; both unwritten",
    # --- SINGLE-PURPOSE MATCHERS ---------------------------------------------
    ("test_ci_runs_on_fallback_is_self_hosted.py", "_FALLBACK"): (
        "matches a workflow fallback expression; both directions unwritten"
    ),
    ("test_css_dark_token_not_shadowed.py", "_LIGHT_AXIS"): "both directions unwritten",
    ("test_html_lang_follows_the_active_language.py", "_LANG_ATTR"): (
        "has a positive control — the only pattern in the suite that did "
        "before this guard existed. Needs the negative"
    ),
    ("test_mobile_panes_stay_reachable.py", "_MOBILE_MEDIA"): "both directions unwritten",
    ("test_no_asset_paths_via_installed_package.py", "_OFFENDING"): "both directions unwritten",
    # --- #180's OWN GUARD, and the irony is worth recording -------------------
    # These belong to test_disabled_opacity_is_one_token.py, the guard added by
    # the PR that FIXED the first documentation inversion. It repaired one
    # detector and shipped two more with no controls, which is precisely why
    # "remember to add controls" failed as a rule and this file exists.
    ("test_disabled_opacity_is_one_token.py", "_BLOCK"): "both directions unwritten",
    ("test_disabled_opacity_is_one_token.py", "_LITERAL_OPACITY"): "both directions unwritten",
}


def _pattern_names(tree: ast.Module) -> set[str]:
    """Module-level ``NAME = re.compile(...)`` targets."""
    out: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        fn = node.value.func
        if isinstance(fn, ast.Attribute) and fn.attr == "compile":
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out.add(tgt.id)
    return out


def _call_info(
    node: ast.AST, names: set[str], literal_vars: frozenset[str] = frozenset()
) -> tuple[str, bool] | None:
    """If `node` is ``PATTERN.search(x)``, return (pattern, x_is_a_fixed_sample).

    `literal_vars` names locals bound to string constants. THE HOUSE AAA STYLE
    PUTS THE SAMPLE ON THE ARRANGE LINE:

        sample  = "# a comment naming it"      # Arrange
        matched = _P.search(strip(sample))     # Act
        assert matched is None                 # Assert

    so the literal is two indirections from the call and a checker that only
    inspects the argument subtree sees none. That is the third time in this
    file's development that the repo's own mandated test style blinded the
    analysis — first by putting the assertion on a separate line, then by
    wrapping the sample in a helper, now by naming it.
    """
    if not isinstance(node, ast.Call):
        return None
    fn = node.func
    if not isinstance(fn, ast.Attribute) or fn.attr not in _MATCH_METHODS:
        return None
    if not isinstance(fn.value, ast.Name) or fn.value.id not in names:
        return None
    # A string literal ANYWHERE in the argument, not just at the top level.
    #
    # `_P.search(_strip_comments("…"))` is a literal-derived sample — the input
    # is still fixed by the test and independent of the tree. Requiring the
    # literal to be the bare argument rejected a real, correct control in
    # test_dim_renders_a_verdict.py, which is a false negative in the CHECKER
    # rather than a missing control in the subject.
    #
    # The exclusion that matters survives: a tree scan — `_P.search(src)` or
    # `_P.search(path.read_text())` — contains no string literal at all, so it
    # is still not credited. `test_a_tree_scan_does_not_count_as_a_negative_
    # control` holds that line.
    # …but a path literal is NOT a sample. `_P.search(Path("x.css").read_text())`
    # contains a string literal and is still a tree scan — the test fixes the
    # file's NAME, not its CONTENTS, so the assertion says nothing about what
    # the pattern can distinguish. Reading calls disqualify the argument.
    reads_a_file = any(
        isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Attribute)
        and sub.func.attr in _READERS
        for a in node.args
        for sub in ast.walk(a)
    ) or any(
        isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Name)
        and sub.func.id in _READERS
        for a in node.args
        for sub in ast.walk(a)
    )
    literal = not reads_a_file and any(
        (isinstance(sub, ast.Constant) and isinstance(sub.value, str))
        or (isinstance(sub, ast.Name) and sub.id in literal_vars)
        for a in node.args
        for sub in ast.walk(a)
    )
    return fn.value.id, literal


def _is_negated(expr: ast.AST, target: ast.AST) -> bool:
    """Does `expr` assert that `target` did NOT match?

    True under a ``not``, or compared ``is None`` / ``== None``.
    """
    for sub in ast.walk(expr):
        if isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not):
            if any(inner is target for inner in ast.walk(sub)):
                return True
        if isinstance(sub, ast.Compare):
            if not any(inner is target for inner in ast.walk(sub.left)):
                continue
            for op, comp in zip(sub.ops, sub.comparators):
                if isinstance(comp, ast.Constant) and comp.value is None:
                    if isinstance(op, (ast.Is, ast.Eq)):
                        return True
    return False


def _controls(path: pathlib.Path) -> dict[str, dict[str, bool]]:
    """Return {pattern: {"positive": bool, "negative": bool}} for one module."""
    tree = ast.parse(path.read_text())
    names = _pattern_names(tree)
    found = {n: {"positive": False, "negative": False} for n in names}
    if not names:
        return found

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # `matched = PATTERN.search(sample)` — the repo's mandated AAA style
        # puts the call on the Act line and the check on the Assert line, so a
        # checker that only looks inside `assert` is blinded by the house rule.
        # (Measured: an earlier version of this analysis reported 27/28
        # uncontrolled for exactly that reason.)
        # Locals bound to a string constant — the Arrange-line samples.
        literal_vars = {
            tgt.id
            for stmt in ast.walk(fn)
            if isinstance(stmt, ast.Assign)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
            for tgt in stmt.targets
            if isinstance(tgt, ast.Name)
        }
        frozen = frozenset(literal_vars)

        bound: dict[str, tuple[str, bool]] = {}
        for stmt in ast.walk(fn):
            if not isinstance(stmt, ast.Assign):
                continue
            info = _call_info(stmt.value, names, frozen)
            if info is None:
                continue
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name):
                    bound[tgt.id] = info

        for stmt in ast.walk(fn):
            if not isinstance(stmt, ast.Assert):
                continue

            # Calls written directly inside the assert.
            for sub in ast.walk(stmt.test):
                info = _call_info(sub, names, frozen)
                if info is None:
                    continue
                pattern, literal = info
                if _is_negated(stmt.test, sub):
                    if literal:
                        found[pattern]["negative"] = True
                else:
                    found[pattern]["positive"] = True

            # References to a variable bound from a pattern call.
            for sub in ast.walk(stmt.test):
                if not isinstance(sub, ast.Name) or sub.id not in bound:
                    continue
                pattern, literal = bound[sub.id]
                if _is_negated(stmt.test, sub):
                    if literal:
                        found[pattern]["negative"] = True
                else:
                    found[pattern]["positive"] = True

    return found


def _modules_with_patterns() -> list[pathlib.Path]:
    out = []
    for path in sorted(_TESTS.glob("test_*.py")):
        if path.name == pathlib.Path(__file__).name:
            continue
        if _pattern_names(ast.parse(path.read_text())):
            out.append(path)
    return out


def _all_patterns() -> list[tuple[str, str]]:
    out = []
    for path in _modules_with_patterns():
        for name in sorted(_pattern_names(ast.parse(path.read_text()))):
            out.append((path.name, name))
    return out


@pytest.mark.parametrize(("module", "pattern"), _all_patterns())
def test_every_detector_can_match_a_real_instance(module: str, pattern: str) -> None:
    """POSITIVE control: prove the instrument is not blind.

    Without this, a negative guard passes identically whether the tree is clean
    or the pattern could never have matched anything.
    """
    # Arrange
    key = (module, pattern)

    # Act
    control = _controls(_TESTS / module)[pattern]["positive"]

    # Assert
    assert control or key in _EXEMPT, (
        f"{module}: `{pattern}` is never asserted to MATCH anything, so every "
        f"negative assertion using it passes whether the tree is clean or the "
        f"pattern is broken. Add a control — `assert {pattern}.search(<a real "
        f"instance>)` — or add {key!r} to _EXEMPT with a written reason."
    )


@pytest.mark.parametrize(("module", "pattern"), _all_patterns())
def test_every_detector_ignores_a_mere_mention(module: str, pattern: str) -> None:
    """NEGATIVE control: prove the instrument is not inverted.

    A substring detector cannot tell prose ABOUT a construct from the construct.
    That makes the file which best documents why it avoids something look
    identical to the file that still does it — and it has bitten this repo
    twice and scitex-app once.

    The sample must be a LITERAL. "Finds nothing in the tree" is the guard
    itself, not a control on the guard.
    """
    # Arrange
    key = (module, pattern)

    # Act
    control = _controls(_TESTS / module)[pattern]["negative"]

    # Assert
    assert control or key in _EXEMPT, (
        f"{module}: `{pattern}` is never asserted to NOT match a literal, so "
        f"nothing shows it can tell a real instance from a comment mentioning "
        f"one. Add a control — `assert {pattern}.search('# a comment naming "
        f"it') is None` — or add {key!r} to _EXEMPT with a written reason."
    )


@pytest.mark.parametrize("key", sorted(_EXEMPT))
def test_every_exemption_is_still_needed(key: tuple[str, str]) -> None:
    """Reverse check: an exemption must not outlive its justification.

    Without this, the list becomes a record of what was once true and quietly
    suppresses a guard that would now pass.
    """
    # Arrange
    module, pattern = key

    # Act
    control = _controls(_TESTS / module)[pattern]

    # Assert
    assert not (control["positive"] and control["negative"]), (
        f"{module}: `{pattern}` now has BOTH controls, so its _EXEMPT entry is "
        f"obsolete and is suppressing a check that would pass. Delete "
        f"{key!r} — reason on file was: {_EXEMPT[key]!r}"
    )


def test_the_analysis_finds_the_detectors_it_audits() -> None:
    """Anti-vacuity: an empty parametrisation would make both guards silent."""
    # Arrange
    minimum = 10

    # Act
    found = _all_patterns()

    # Assert
    assert len(found) >= minimum, (
        f"only {len(found)} compiled patterns discovered across "
        f"tests/develop; the parametrised guards above would then be asserting "
        f"about almost nothing and passing for the wrong reason."
    )


def test_the_analysis_reports_a_pattern_with_no_controls(tmp_path) -> None:
    """The checker must FAIL a detector that has neither control."""
    # Arrange
    module = tmp_path / "test_fixture_uncontrolled.py"
    module.write_text(
        "import re\n"
        '_P = re.compile(r"x")\n'
        "def test_thing():\n"
        "    assert not _P.search(open('f').read())\n"
    )

    # Act
    control = _controls(module)["_P"]

    # Assert
    assert not control["positive"] and not control["negative"], (
        "the checker credited a pattern that has no controls at all, so it "
        "would pass every uncontrolled detector in the suite."
    )


def test_the_analysis_credits_a_pattern_with_both_controls(tmp_path) -> None:
    """And it must stay SILENT on one that is properly controlled.

    This is the arm that separates "the suite is clean" from "the checker is
    broken". Both produce a green run; only this distinguishes them.
    """
    # Arrange
    module = tmp_path / "test_fixture_controlled.py"
    module.write_text(
        "import re\n"
        '_P = re.compile(r"\\bfoo\\b")\n'
        "def test_matches():\n"
        '    matched = _P.search("foo()")\n'
        "    assert matched is not None\n"
        "def test_ignores_a_mention():\n"
        '    matched = _P.search("# mentions foo in prose")\n'
        "    assert matched is None\n"
    )

    # Act
    control = _controls(module)["_P"]

    # Assert
    assert control["positive"] and control["negative"], (
        f"the checker failed to credit controls written in the repo's mandated "
        f"AAA style (call on the Act line, check on the Assert line). It read "
        f"{control}. A checker blinded by the house test style would report "
        f"the whole suite as uncontrolled."
    )


def test_a_tree_scan_does_not_count_as_a_negative_control(tmp_path) -> None:
    """The asymmetry, asserted rather than merely documented.

    "Finds nothing in the source" is the guard. Crediting it as the guard's own
    control would let a detector cite its own subject as its own evidence.
    """
    # Arrange
    module = tmp_path / "test_fixture_scan_only.py"
    module.write_text(
        "import re\n"
        '_P = re.compile(r"bad")\n'
        "def test_absent():\n"
        "    src = open('f').read()\n"
        "    assert _P.search(src) is None\n"
    )

    # Act
    control = _controls(module)["_P"]

    # Assert
    assert not control["negative"], (
        "a scan of the tree was credited as a NEGATIVE control. That is "
        "circular: the guard's own assertion would license the guard."
    )


def test_a_read_text_call_does_not_count_as_a_negative_control(tmp_path) -> None:
    """The other spelling of a tree scan, since the literal search widened.

    `_call_info` looks for a string literal anywhere inside the argument, so
    that `_P.search(_strip("…"))` counts. This asserts the widening did not
    also admit `_P.search(path.read_text())` — which reads the tree and would
    reintroduce the circularity from the other side.
    """
    # Arrange
    module = tmp_path / "test_fixture_read_text.py"
    module.write_text(
        "import re, pathlib\n"
        '_P = re.compile(r"bad")\n'
        "def test_absent():\n"
        '    assert _P.search(pathlib.Path("x.css").read_text()) is None\n'
    )

    # Act
    control = _controls(module)["_P"]

    # Assert
    assert not control["negative"], (
        "a `read_text()` scan was credited as a negative control. The path "
        "literal inside the call is not a SAMPLE — it names a file whose "
        "contents the test does not fix, so the assertion is a tree scan "
        "wearing a literal."
    )
