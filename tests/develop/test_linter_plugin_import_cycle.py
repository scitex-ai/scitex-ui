#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Importing our own linter modules must not deactivate our own linter rules.

Until 0.14.3 ``_linter/_rules.py`` imported scitex-dev's ``Rule`` at MODULE
SCOPE, which closed an import cycle:

    import scitex_ui._linter._rules
      -> from scitex_dev.linter._rules._base import Rule    (module scope)
      -> scitex_dev.linter.__init__ runs _register_sweep_cli()
      -> ... which reaches scitex-dev's plugin loader
      -> loader imports scitex_ui._linter_plugin, CALLS get_plugin()
      -> get_plugin() needs build_rules from a module still on the line above
      -> ImportError, caught by the loader, plugin dropped

The loader does not fail on that. It warns and carries on, so a run with the
UI corpus ACTIVE and a run with it INACTIVE differ by one line of yellow text
— measured 2026-08-09 as 41 rules / 7 UI versus 34 / 0.

TWO THINGS MAKE THIS BUG HARD TO TEST, and both shaped the tests below.

First, the happy path passes in every broken state: ``get_plugin()`` returned
a correct dict throughout, so any test calling it directly goes green while
the real load path is broken. The behavioural tests here therefore assert on
the WARNING being absent and the CORPUS being active, never on get_plugin().

Second, whether the bug reproduces at all depends on an optional dependency.
scitex-dev's ``_register_sweep_cli()`` is wrapped in ``except Exception:
pass``; without ``click`` it dies silently, the loader never runs during our
import, and the cycle cannot close. Three earlier investigation passes
concluded "does not reproduce" from venvs that were structurally incapable of
showing it. So the behavioural tests SKIP when the loader demonstrably does
not run at import — and because a skip is not evidence, the structural test
below carries the invariant instead and can never skip.
"""

import ast
import subprocess
import sys
import textwrap

import pytest

import scitex_ui
from tests._checkout import package_dir

_RULES_PY = package_dir() / "_linter" / "_rules.py"

#: Verbatim from scitex-dev's loader; the whole failure is that this is only
#: a warning, so scanning stderr for it is the only way to see it.
_WARNING_MARKER = "failed to load plugin 'ui'"

#: The import order that closed the cycle. Importing OUR module first is both
#: the natural move when debugging the UI rules and the one that broke.
_REENTRANT_TRIGGER = "scitex_ui._linter._rules"


def _module_scope_scitex_dev_imports(source: str) -> list[int]:
    """Return line numbers of imports that pull in scitex-dev AT IMPORT TIME.

    "Module scope" means *executed when the module is imported*, which is not
    the same as *a direct child of the module body*. The historical defect was

        try:
            from scitex_dev.linter._rules._base import Rule
        except ImportError:
            ...

    — nested inside a ``Try``, and therefore invisible to a check that only
    walks ``tree.body``. An earlier draft of this file did exactly that and
    PASSED against the unfixed module; the mutation probe is what caught it.
    So: recurse through everything, and prune only at ``def``/``async def``,
    whose bodies run on call rather than on import. That deferral is the fix,
    so it must read as a pass.
    """
    hits = []

    def walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue  # body runs at CALL time — this is the remedy
            if isinstance(child, ast.ImportFrom):
                if child.module and child.module.startswith("scitex_dev"):
                    hits.append(child.lineno)
            elif isinstance(child, ast.Import):
                if any(a.name.startswith("scitex_dev") for a in child.names):
                    hits.append(child.lineno)
            walk(child)

    walk(ast.parse(source))
    return sorted(hits)


def _run_probe(trigger: str) -> subprocess.CompletedProcess:
    """Import ``trigger`` in a COLD interpreter, then list the linter rules.

    A cold subprocess is required: the cycle only exists while the module is
    mid-import, so anything already in this process's ``sys.modules`` has by
    definition passed the point where it could fail.
    """
    code = textwrap.dedent(
        f"""
        import importlib
        importlib.import_module({trigger!r})
        from scitex_dev.linter import list_rules
        rules = list_rules()
        ids = sorted(r.id for r in rules)
        ui = [i for i in ids if "UI" in i]
        print("TOTAL=%d UI=%d" % (len(ids), len(ui)))
        """
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _loader_runs_at_import() -> bool:
    """Does scitex-dev's plugin loader run when its linter is imported?

    The precondition for this bug existing at all. False in a minimal venv
    (no ``click``), where ``_register_sweep_cli``'s swallowed failure means
    the loader never runs and the cycle cannot close.
    """
    code = textwrap.dedent(
        """
        import sys
        import scitex_dev.linter
        print("LOADER_RAN=%s" % ("scitex_ui._linter_plugin" in sys.modules))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    return "LOADER_RAN=True" in proc.stdout


_needs_reentrant_loader = pytest.mark.skipif(
    not _loader_runs_at_import(),
    reason=(
        "scitex-dev's plugin loader does not run at import in this venv "
        "(typically: click absent, so _register_sweep_cli fails into its "
        "except-pass), so the import cycle cannot close here. The structural "
        "test in this file carries the invariant instead."
    ),
)


def test_rules_module_does_not_import_scitex_dev_at_module_scope():
    """The invariant the fix encodes. Never skips, in any environment."""
    # Arrange
    source = _RULES_PY.read_text(encoding="utf-8")

    # Act
    hits = _module_scope_scitex_dev_imports(source)

    # Assert
    assert hits == [], (
        f"{_RULES_PY.name} imports scitex-dev at module scope (line(s) {hits}). "
        "That closes the plugin-loader cycle and silently deactivates the "
        "entire UI rule corpus. Resolve Rule inside build_rules() instead."
    )


def test_module_scope_detector_flags_a_module_scope_import():
    """Positive control: the detector above must be able to say "present"."""
    # Arrange
    source = "from scitex_dev.linter._rules._base import Rule\n"

    # Act
    hits = _module_scope_scitex_dev_imports(source)

    # Assert
    assert hits == [1], "detector cannot see the very import it exists to catch"


def test_module_scope_detector_flags_the_historical_try_wrapped_import():
    """The shape that actually shipped, and that a naive detector misses.

    This is the regression test for the GUARD, not for the module: the first
    draft of the detector walked only ``tree.body`` and so passed the unfixed
    file. Without this control, the structural test could quietly go blind
    again and still look green.
    """
    # Arrange
    source = (
        "try:\n"
        "    from scitex_dev.linter._rules._base import Rule\n"
        "except ImportError:\n"
        "    Rule = object\n"
    )

    # Act
    hits = _module_scope_scitex_dev_imports(source)

    # Assert
    assert hits == [2], "try-wrapped import at module scope not detected"


def test_module_scope_detector_ignores_a_function_scope_import():
    """The fix must READ as a pass, or the guard forbids its own remedy."""
    # Arrange
    source = "def f():\n    from scitex_dev.linter._rules._base import Rule\n"

    # Act
    hits = _module_scope_scitex_dev_imports(source)

    # Assert
    assert hits == [], "deferred import wrongly flagged as module scope"


def test_warning_detector_recognises_the_real_loader_warning():
    """Positive control for the stderr scan used by the two tests below.

    Recorded verbatim from the reproduction on 2026-08-09, so the assertions
    that this string is ABSENT cannot pass merely because they never matched.
    """
    # Arrange
    observed = (
        "[scitex-dev linter] WARNING: failed to load plugin 'ui': ImportError: "
        "cannot import name 'build_rules' from partially initialized module "
        "'scitex_ui._linter._rules' (most likely due to a circular import)"
    )

    # Act
    detected = _WARNING_MARKER in observed

    # Assert
    assert detected, "stderr scan would not have caught the real warning"


@_needs_reentrant_loader
def test_reentrant_import_emits_no_plugin_load_warning():
    """The symptom: importing our module must not drop our own plugin."""
    # Arrange
    trigger = _REENTRANT_TRIGGER

    # Act
    proc = _run_probe(trigger)

    # Assert
    assert _WARNING_MARKER not in proc.stderr, (
        f"importing {_REENTRANT_TRIGGER} made scitex-dev drop the 'ui' plugin:"
        f"\n{proc.stderr}"
    )


@_needs_reentrant_loader
def test_reentrant_import_leaves_the_ui_corpus_active():
    """The consequence, which is what actually matters.

    Asserted separately from the warning because the warning is cosmetic and
    this is not: a dropped plugin means every UI rule silently stops running.
    """
    # Arrange: expected count comes from the corpus itself, so adding a rule
    # does not turn this into a chore — only losing the corpus fails it.
    from scitex_ui._linter._rules import build_rules

    expected = f"UI={len(build_rules())}"

    # Act
    proc = _run_probe(_REENTRANT_TRIGGER)

    # Assert
    assert expected in proc.stdout, (
        f"the UI rule corpus is not active after a re-entrant import; expected "
        f"{expected} (stdout={proc.stdout.strip()!r}, "
        f"stderr={proc.stderr.strip()!r})"
    )


def test_rule_class_is_scitex_devs_own_when_it_is_installed():
    """Guards the failure mode a naive fix would introduce.

    Deferring the import fixes the cycle; deferring it into a bare
    ``except ImportError`` would ALSO make the warning go away, by quietly
    building every rule from the fallback dataclass instead. That reads as
    fixed and is not, so pin the class identity.
    """
    # Arrange
    pytest.importorskip("scitex_dev", reason="fallback path is correct here")
    from scitex_ui._linter._rules import build_rules

    # Act
    rule = next(iter(build_rules().values()))

    # Assert
    assert type(rule).__module__.startswith("scitex_dev"), (
        f"rules built from {type(rule).__module__}.{type(rule).__name__}, not "
        "scitex-dev's Rule — the soft-import silently swallowed a real failure"
    )
