#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Every command this package registers must carry a structured help spec (§4b).

The audit reports §4b as a WARNING and exits 0, so nothing in CI fails when a
new command ships with a free-form docstring. That is the whole reason this
test exists: the convention is real, the enforcement is advisory, and a rule
that cannot fail a build is one nobody notices regressing.

THE COVERED SET IS DERIVED, NOT LISTED. It walks the live command tree, so a
command added next month is covered by construction. A hardcoded list of the
thirteen sites migrated today would silently exempt the fourteenth — and the
fourteenth is exactly the one nobody remembers to add.

TWO COMMANDS ARE EXEMPT AND THE EXEMPTION IS NAMED, not a blanket skip:
`completion` and `install-tab-completion` are attached by scitex-dev's
``attach_shell_completion`` (called from ``_cli.py``), so they are its code
living in our tree and we cannot spec them without editing scitex-dev.

Measured 2026-08-15, and it is why the exemption is legitimate rather than
convenient — both are HIDDEN deprecated aliases:

    completion                 leaf  spec=False  hidden=True
    install-tab-completion     leaf  spec=False  hidden=True
    install-shell-completion   leaf  spec=True   visible
    print-shell-completion     leaf  spec=True   visible

scitex-dev specs every completion command it EXPOSES; only the back-compat
aliases lack one — the same shape as our own hidden ``mcp installation``. So
the exemption covers legacy surface, not a gap in the convention.

``test_exempt_commands_are_still_foreign`` re-derives the claim every run, so
if either ever becomes ours the exemption fails rather than quietly widening.

WHY THE `help_available()` GATE MATTERS HERE: with scitex-dev absent the whole
migration degrades to plain click by design (PS-213 — scitex-dev is the
optional [cli] extra and ``_cli.py`` is the console-script entry point). In
that environment EVERY command legitimately lacks a spec, so an unguarded
coverage assertion would fail for the right reason at the wrong time. Gating on
``help_available()`` keeps the test honest in both worlds — and
``test_structured_help_path_is_live_here`` asserts which world the suite is
running in, so a green run cannot mean "skipped everything".
"""

from __future__ import annotations

import click
import pytest

from scitex_ui._cli import main
from scitex_ui._cli_help import help_available

#: Commands attached by scitex-dev rather than declared here. Each entry is a
#: command we do NOT own; see the module docstring for why that is not a
#: blanket exemption.
_FOREIGN = {
    "scitex-ui completion",
    "scitex-ui install-tab-completion",
}


def _walk(cmd, ctx, path="scitex-ui"):
    """Yield (dotted-path, command) for the whole live tree."""
    yield path, cmd
    if isinstance(cmd, click.Group):
        for name in sorted(cmd.list_commands(ctx)):
            sub = cmd.get_command(ctx, name)
            if sub is None:
                continue
            child = click.Context(sub, parent=ctx, info_name=name)
            yield from _walk(sub, child, f"{path} {name}")


def _tree():
    return list(_walk(main, click.Context(main)))


def _has_spec(cmd) -> bool:
    return getattr(cmd, "_help_spec", None) is not None


def test_structured_help_path_is_live_here():
    """Positive control — proves the coverage test below is not vacuous."""
    # Arrange
    expected = True

    # Act
    live = help_available()

    # Assert
    assert live is expected, (
        "scitex-dev is not importable in this environment, so every command "
        "legitimately falls back to plain click and the coverage assertion "
        "below would pass by being skipped rather than by being satisfied"
    )


def test_every_owned_command_carries_a_help_spec():
    """§4b, derived from the live tree so a new command cannot escape it."""
    # Arrange
    tree = _tree()

    # Act
    missing = sorted(p for p, c in tree if p not in _FOREIGN and not _has_spec(c))

    # Assert
    assert missing == [], (
        f"{missing} register without a CliHelp spec. Decorate with "
        "cls=SpecCommand / SpecGroup via scitex_ui._cli_help.spec_command / "
        "spec_group. The audit only WARNS about this, so nothing else fails."
    )


def test_the_tree_is_not_empty():
    """A walk that returns nothing would make the coverage test trivially green."""
    # Arrange
    minimum = 5

    # Act
    found = len(_tree())

    # Assert
    assert found >= minimum, (
        f"walked only {found} commands; the tree walk is broken, and a broken "
        "walk makes every other assertion in this file meaningless"
    )


@pytest.mark.parametrize("path", sorted(_FOREIGN))
def test_exempt_commands_are_still_foreign(path):
    """An exemption must keep earning itself, or it silently widens."""
    # Arrange
    present = {p for p, _ in _tree()}

    # Act
    still_unowned = path not in present or not _has_spec(dict(_tree())[path])

    # Assert
    assert still_unowned, (
        f"{path} now carries a help spec, so it is no longer scitex-dev's "
        "un-specced command. Remove it from _FOREIGN — an exemption that "
        "outlives its reason is how a covered set quietly shrinks."
    )
