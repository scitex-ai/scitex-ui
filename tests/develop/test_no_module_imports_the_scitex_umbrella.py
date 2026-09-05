#!/usr/bin/env python3
"""Guards that nothing here depends on the `scitex` UMBRELLA package.

WHY THIS EXISTS — measured 2026-09-04 on develop @ ddbf1e8:

    $ .venv/bin/python examples/01_list_components.py
    ModuleNotFoundError: No module named 'scitex'   (line 10)   EXIT=1

`examples/01_list_components.py` and `examples/02_workspace_components.py` both
opened with a bare `import scitex as stx`. The umbrella is not installed here
and must not be — it pins its siblings with `==` and downgrades an installed
scitex-ui out from under you (measured 2026-08-18: 0.16.0 -> 0.6.0 plus ~40
other packages). So two of the four examples could not run, and
`00_run_all.sh` could not pass.

THE REASON IT SURVIVED IS THE REASON IT NEEDS A MECHANICAL CHECK. Nothing runs
the examples. They sit in `library_dirs = ["src", "tests", "examples"]`, so the
linter treats them as library code rather than scripts, and no CI job executes
`00_run_all.sh`. Their committed `*_out/FINISHED_SUCCESS` directories — from
back when the umbrella *was* installed — made them look exercised the whole
time. A directory of scripts that nothing runs is indistinguishable from a
directory of scripts that work.

THE HARD PART IS NOT FINDING THE UMBRELLA, IT IS THE TWO WAYS OF BEING WRONG
ABOUT IT. Both were found by measurement, and each cost this file a rewrite:

1. **The siblings.** Everything we legitimately depend on shares the prefix —
   `scitex_ui`, `scitex_session`, `scitex_io`, `scitex_repro`. A pattern
   anchored on the bare word flags all of them and the guard is deleted as
   noise within a week.

2. **The guarded optional import, which is CORRECT and must not be flagged.**
   `03_self_explanatory_demo.py` does

       try:
           import scitex as stx
       except ModuleNotFoundError:   # standalone: the umbrella is not installed
           stx = None

   deliberately, so the demo stays runnable standalone — which is the whole
   claim that file makes. The first version of this guard reported it as a
   defect. A hard dependency and a guarded optional one are not the same thing,
   and only the first breaks anything.

That second case is also why this works on the AST rather than on lines. The
regex used to survey the tree by hand missed the very import it later flagged,
because that one is indented inside a `try:` — a line-anchored pattern cannot
see nesting, and cannot tell an import from the word appearing in a comment.

WHAT A PASS DOES NOT MEAN: that the umbrella is absent from the environment, or
that any example produces correct output. Only that nothing here needs it.
"""

from __future__ import annotations

import ast
import importlib.util

import pytest

from tests._checkout import package_dir

_PKG_ROOT = package_dir().parent.parent
_EXAMPLES = _PKG_ROOT / "examples"
_SRC = package_dir()

_GUARD_EXCEPTIONS = frozenset({"ImportError", "ModuleNotFoundError"})


def _is_umbrella(name: str) -> bool:
    """True for `scitex` and its submodules, false for `scitex_*` siblings."""
    return name == "scitex" or name.startswith("scitex.")


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    """True if this handler would swallow a missing-module error."""
    caught = handler.type
    if caught is None:
        return True
    candidates = caught.elts if isinstance(caught, ast.Tuple) else [caught]
    return any(
        (getattr(node, "id", None) or getattr(node, "attr", None)) in _GUARD_EXCEPTIONS
        for node in candidates
    )


def _guarded_lines(tree: ast.AST) -> set[int]:
    """Line numbers of imports sitting inside a `try:` that catches ImportError.

    Those are deliberate optional dependencies, not hard ones.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(_catches_import_error(h) for h in node.handlers):
            continue
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    lines.add(sub.lineno)
    return lines


def _imported_names(tree: ast.AST) -> list[tuple[int, str]]:
    """Every ``(lineno, module)`` imported at any depth, absolute imports only."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def _umbrella_offenders_in_source(source: str, label: str) -> list[str]:
    """Unguarded umbrella imports in one module's source."""
    tree = ast.parse(source, filename=label)
    guarded = _guarded_lines(tree)
    return [
        f"{label}:{lineno}: imports {name!r}"
        for lineno, name in _imported_names(tree)
        if _is_umbrella(name) and lineno not in guarded
    ]


def _umbrella_offenders(root) -> list[str]:
    """Unguarded umbrella imports anywhere under ``root``."""
    offenders = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        offenders.extend(_umbrella_offenders_in_source(source, str(path.relative_to(_PKG_ROOT))))
    return offenders


def _unresolvable(root) -> list[str]:
    """Unguarded imports under ``root`` that do not resolve in this environment."""
    broken = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        guarded = _guarded_lines(tree)
        for lineno, name in _imported_names(tree):
            head = name.split(".")[0]
            if lineno in guarded or importlib.util.find_spec(head) is not None:
                continue
            broken.append(f"{path.name}:{lineno}: cannot resolve {head!r}")
    return broken


@pytest.fixture
def examples_dir():
    """The examples tree, or skip where there is none.

    An installed wheel ships no `examples/`, so this guard is meaningful only in
    the source tree. Skipping says so rather than passing on an empty check.
    """
    if not _EXAMPLES.is_dir():
        pytest.skip("no examples/ directory (installed wheel, not a source tree)")
    return _EXAMPLES


def test_detector_flags_a_bare_umbrella_import() -> None:
    """POSITIVE CONTROL: the exact line that broke the examples.

    Without this, an over-tightened detector reports a clean tree forever.
    """
    # Arrange
    source = "import scitex as stx\n"
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert len(offenders) == 1, f"detector missed a bare umbrella import: {offenders}"


def test_detector_flags_an_indented_umbrella_import() -> None:
    """POSITIVE CONTROL: nesting must not hide it.

    The hand-run regex that surveyed this tree was line-anchored and missed
    exactly this shape.
    """
    # Arrange
    source = "def f():\n    import scitex\n"
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert len(offenders) == 1, f"detector missed an indented umbrella import: {offenders}"


def test_detector_flags_a_submodule_umbrella_import() -> None:
    """POSITIVE CONTROL: `from scitex.session import ...` is still the umbrella."""
    # Arrange
    source = "from scitex.session import INJECTED\n"
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert len(offenders) == 1, f"detector missed a submodule umbrella import: {offenders}"


def test_detector_ignores_the_sibling_packages() -> None:
    """NEGATIVE CONTROL: the packages we legitimately depend on must not match.

    Every one of these shares the `scitex` prefix. Flagging them makes the
    check unusable, which is the failure mode that gets guards deleted.
    """
    # Arrange
    source = (
        "import scitex_ui\n"
        "import scitex_session as stx\n"
        "from scitex_ui import list_components\n"
        "from scitex_session import INJECTED\n"
        "import scitex_io\n"
    )
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert offenders == [], f"detector flagged legitimate sibling imports: {offenders}"


def test_detector_ignores_a_guarded_optional_umbrella_import() -> None:
    """NEGATIVE CONTROL: the shape `03_self_explanatory_demo.py` uses on purpose.

    A guarded import is an optional dependency, not a hard one, and breaks
    nothing when the umbrella is absent. The first version of this guard
    reported it as a defect; this control is what stops that regressing.
    """
    # Arrange
    source = "try:\n    import scitex as stx\nexcept ModuleNotFoundError:\n    stx = None\n"
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert offenders == [], f"detector flagged a guarded optional import: {offenders}"


def test_detector_ignores_a_mention_that_is_not_an_import() -> None:
    """NEGATIVE CONTROL: prose naming the umbrella must not be flagged.

    A line-based detector would fail this; an AST-based one cannot see a
    comment at all, which is the point of working on the tree.
    """
    # Arrange
    source = '"""Never install the scitex umbrella."""\n# scitex is the umbrella\nX = "scitex"\n'
    # Act
    offenders = _umbrella_offenders_in_source(source, "sample.py")
    # Assert
    assert offenders == [], f"detector flagged a mere mention: {offenders}"


def test_no_example_depends_on_the_umbrella(examples_dir) -> None:
    """The defect this file was written for."""
    # Arrange
    root = examples_dir
    # Act
    offenders = _umbrella_offenders(root)
    # Assert
    assert offenders == [], "examples depend on the umbrella:\n" + "\n".join(offenders)


def test_no_source_module_depends_on_the_umbrella() -> None:
    """The same constraint on the shipped package, where it matters more."""
    # Arrange
    root = _SRC
    # Act
    offenders = _umbrella_offenders(root)
    # Assert
    assert offenders == [], "src/ depends on the umbrella:\n" + "\n".join(offenders)


def test_every_unguarded_example_import_resolves(examples_dir) -> None:
    """Each example must be runnable, not merely free of the umbrella.

    The check above catches the name we know about. This catches the next one:
    any unguarded module-level import that does not resolve here. Resolving
    beats grepping for a blocklist, because a blocklist only ever knows about
    yesterday's mistake.
    """
    # Arrange
    root = examples_dir
    # Act
    broken = _unresolvable(root)
    # Assert
    assert broken == [], "examples have unresolvable imports:\n" + "\n".join(broken)
