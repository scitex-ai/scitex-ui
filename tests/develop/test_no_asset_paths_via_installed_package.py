#!/usr/bin/env python3
"""No test may locate shipped assets through the INSTALLED package.

THE RULE: use ``tests._checkout`` for anything asserting about SOURCE.
``scitex_ui.__file__`` points at whatever is on ``sys.path`` — under a
non-editable install that is site-packages, not the branch under review.

WHY A META-TEST RATHER THAN JUST FIXING THE FILES. Twenty-two modules had the
old spelling. Fixing twenty-two files leaves the twenty-third to be written the
same way — and that is not hypothetical: the defect was FOUND by writing a new
guard with the old spelling, hours after the class had already been identified,
by someone holding all the context. A rule that must be remembered is forgotten
at exactly the moment it matters (§7), so it is mechanical here instead.

WHAT THIS DELIBERATELY DOES NOT FORBID: importing ``scitex_ui`` (tests must, to
test it), or reading ``scitex_ui.__version__``, or calling ``get_static_dir()``
— that is a PUBLIC API whose whole job is to answer "where did the install put
its assets", and a test of that function must use the install. Only the
``__file__``-to-filesystem-path pattern is refused, because that is the one that
silently substitutes one tree for another.

EXEMPTIONS live in :data:`_ABOUT_THE_INSTALLED_ARTIFACT`, one entry at a time
with a written reason — never a blanket switch. A test that genuinely asserts
about what SHIPPED is correct to read the installed package; it just has to say
so, because the code alone cannot distinguish that intent from the bug.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests._checkout import REPO_ROOT

_TESTS = REPO_ROOT / "tests"

#: ``module name -> why it may read the installed package``.
#: One entry at a time, each with a reason. Never a blanket switch.
_ABOUT_THE_INSTALLED_ARTIFACT: dict[str, str] = {
    "test_branding.py": (
        "Coherently about the INSTALLED app, not by accident. It configures "
        "Django with INSTALLED_APPS=['...staticfiles', 'scitex_ui'], so "
        "render_to_string resolves standalone_shell.html through the installed "
        "app, and its _css() helper reads via the public get_static_dir(). "
        "Repointing only its _templates_dir() at the checkout would leave one "
        "of three resolution paths reading a different tree than the other "
        "two — self-inconsistency is worse than either choice made uniformly. "
        "If this module should test the checkout, the fix is to point Django "
        "at the checkout as well, which is a larger change than this guard."
    ),
}

#: ``Path(scitex_ui.__file__)`` — the pattern that turns an import into a tree.
#: Matches across a line break, since the offending lines are often wrapped.
_OFFENDING = re.compile(r"Path\s*\(\s*scitex_ui\.__file__\s*\)", re.S)

#: This module and the helper necessarily NAME the pattern in prose.
_MAY_MENTION_IT = {"test_no_asset_paths_via_installed_package.py", "_checkout.py"}

_PY_COMMENT_OR_DOCSTRING = re.compile(
    r'"""(?:.|\n)*?"""' r"|'''(?:.|\n)*?'''" r"|#[^\n]*",
)


def _offending_modules() -> dict[str, list[int]]:
    """``relative path -> line numbers`` of real (non-comment) uses."""
    found: dict[str, list[int]] = {}
    for path in sorted(_TESTS.rglob("test_*.py")) + sorted(_TESTS.rglob("conftest.py")):
        if path.name in _MAY_MENTION_IT:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if path.name in _ABOUT_THE_INSTALLED_ARTIFACT:
            continue
        source = path.read_text(errors="replace")
        # Blank out comments and docstrings so a module that DISCUSSES the
        # pattern is not accused of using it. Replaced with same-length runs of
        # newlines-preserving filler so line numbers stay accurate.
        stripped = _PY_COMMENT_OR_DOCSTRING.sub(
            lambda m: re.sub(r"[^\n]", " ", m.group(0)), source
        )
        lines = [
            i
            for i, line in enumerate(stripped.splitlines(), 1)
            if _OFFENDING.search(line)
        ]
        if lines:
            found[rel] = lines
    return found


def test_test_tree_is_discoverable() -> None:
    """ANTI-VACUITY: if no test modules are found, the scan proves nothing.

    Without this, a wrong ``REPO_ROOT`` yields an empty file list, the check
    below finds no offenders, and the suite reports the codebase clean — the
    exact failure shape this module exists to stop, reproduced inside it.
    """
    # Arrange: the tests tree itself is the fixture.
    root = _TESTS
    # Act
    modules = list(root.rglob("test_*.py"))
    # Assert
    assert len(modules) > 20, (
        f"only {len(modules)} test modules found under {_TESTS}; the scan did "
        "not run, so a passing result below would be meaningless"
    )


def test_no_test_locates_assets_via_installed_package() -> None:
    """Asset paths must come from the checkout, not from ``sys.path``."""
    # Arrange
    fix_hint = (
        "Fix: `from tests._checkout import css_dir, static_dir, "
        "templates_dir, package_dir`."
    )
    # Act
    offenders = _offending_modules()
    # Assert
    if offenders:
        lines = [
            "These test modules locate package files through the INSTALLED "
            "package rather than the checkout:",
            "",
        ]
        for rel in sorted(offenders):
            nums = ", ".join(str(n) for n in offenders[rel])
            lines.append(f"  {rel}  (line{'s' if len(offenders[rel]) > 1 else ''} {nums})")
        lines += [
            "",
            "Under a non-editable install `scitex_ui.__file__` is site-packages, "
            "so these assert about a DIFFERENT TREE than the one under review — "
            "a regression in the branch is invisible to them, and a fix to the "
            "branch cannot turn them green.",
            "",
            fix_hint,
            "",
            "If a module genuinely asserts about what SHIPPED, add it to "
            "_ABOUT_THE_INSTALLED_ARTIFACT with the reason — one entry, never a "
            "blanket exemption.",
        ]
        pytest.fail("\n".join(lines))
