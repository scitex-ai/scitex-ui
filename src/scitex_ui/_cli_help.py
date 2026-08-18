#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Resolve scitex-dev's CliHelp surface WITHOUT importing it at module scope.

Two ecosystem rules pull in opposite directions here, and this module is the
only place that reconciles them:

  §4b   a command's help must be constructed via ``CliHelp`` rather than left
        as a free-form docstring. The audit checks one thing — whether the
        command object carries a non-None ``_help_spec``.

  PS-213  console-script-deps-must-be-core. ``scitex_ui._cli:main`` is the
        entry point for the ``scitex-ui`` script, so anything it imports at
        module scope must be a CORE dependency. ``scitex-dev`` is NOT: it is
        the optional ``[cli]`` extra.

Importing ``SpecCommand`` at the top of ``_cli.py`` would satisfy §4b and break
PS-213 — a bare ``pip install scitex-ui`` followed by ``scitex-ui --help`` would
raise ModuleNotFoundError. So the classes are resolved LAZILY, at decoration
time, and fall back to plain click when scitex-dev is absent.

Both rules end up honoured rather than exempted:

  * PS-213 holds because no optional dependency is imported unguarded.
  * §4b holds WHERE IT RUNS. The audit only executes in environments that have
    scitex-dev installed, and in exactly those environments the real
    ``SpecCommand`` is used and ``_help_spec`` is set.

THE FALLBACK IS NOT A SILENT FAILURE. Without the extra the help still renders,
via click's ordinary docstring path — it is simply unstructured. That is the
documented behaviour of an optional extra, not a degraded mode pretending to be
the real one. `help_available()` reports which path is live so a caller (or a
test) can tell the two apart rather than guessing.

The same shape already exists in this package: ``_linter/_rules.py`` resolves
scitex-dev's ``Rule`` this way after a module-scope import of it silently
deactivated the entire UI rule corpus (#141). This is that lesson applied
before the fact rather than after.
"""

from __future__ import annotations

import importlib.util
from typing import Any

__all__ = [
    "cli_help",
    "examples",
    "help_available",
    "spec_command",
    "spec_group",
]


def _scitex_dev_present() -> bool:
    """True when scitex-dev can be imported, without importing it."""
    return importlib.util.find_spec("scitex_dev") is not None


def help_available() -> bool:
    """Whether the structured-help path is live in THIS environment.

    Exposed so callers and tests can distinguish "structured help" from
    "click's docstring fallback" explicitly. A test that cannot tell them
    apart would pass identically in both, which is the vacuous-assertion
    shape this package has been eliminating elsewhere.
    """
    return _scitex_dev_present()


def cli_help(**kwargs: Any) -> Any:
    """Build a ``CliHelp``, or return None when scitex-dev is absent.

    None is the correct fallback rather than a stub: ``SpecCommand`` requires a
    real spec, and when it is unavailable we are not using ``SpecCommand`` at
    all — click takes the docstring instead.
    """
    if not _scitex_dev_present():
        return None
    from scitex_dev.ecosystem import CliHelp

    return CliHelp(**kwargs)


def examples(*pairs: tuple[str, str]) -> tuple[Any, ...]:
    """Build ``Example`` objects from ``(cmd, note)`` pairs, lazily.

    ``Example`` is scitex-dev's too, so it gets the same treatment as the rest
    of the surface. Returns an empty tuple when the extra is absent, which is
    what ``CliHelp(examples=...)`` would receive by default anyway — and the
    spec is not built at all in that case.
    """
    if not _scitex_dev_present():
        return ()
    from scitex_dev.ecosystem import Example

    return tuple(Example(cmd=c, note=n) for c, n in pairs)


def spec_command(spec: Any) -> dict[str, Any]:
    """Decorator kwargs registering ``spec`` as a command's help.

    Returns ``{}`` when scitex-dev is absent, so the call site reads
    ``@group.command("x", **spec_command(SPEC))`` in both worlds and needs no
    conditional of its own.
    """
    if spec is None or not _scitex_dev_present():
        return {}
    from scitex_dev.ecosystem import SpecCommand

    return {"cls": SpecCommand, "help_spec": spec}


def spec_group(spec: Any, **extra: Any) -> dict[str, Any]:
    """Decorator kwargs for a group; ``extra`` carries command_categories."""
    if spec is None or not _scitex_dev_present():
        return {}
    from scitex_dev.ecosystem import SpecGroup

    return {"cls": SpecGroup, "help_spec": spec, **extra}
