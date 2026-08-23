#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_dev_group_nests_skills.py

"""`skills` is canonical under `dev`, and the legacy top-level mount still works.

TWO DOCTRINES ASK FOR OPPOSITE THINGS HERE:

    §1a  03_required-introspection-commands.md:98-104 — "If the package ships
         `_skills/<pkg>/`, `<cli> skills` exists as a group with `list`, `get`,
         and `install` subcommands. SELF-CONTAINED (no scitex-dev runtime dep)."

    §13  20_dev-commands.md — `skills` is one of SIX FIXED verbs that mount
         under `dev`. The six NAMES are fixed; the verbs inside are not.

§1a wants `scitex-ui skills` to exist; §13 wants it off the top level. The
resolution is the one the fleet already uses for `list-python-apis` (§1a's own
file, line 23): canonical under `dev`, legacy top level kept as a Phase W
warn-forward alias during migration.

§13 CONTINUES TO WARN WHILE THIS ALIAS EXISTS, and that is the intended state,
not an unfinished fix. §13 is a WARN-tier finding and does not gate the build;
the auditor's own note says so in as many words — "never trade a working
capability for a quieter report — least of all for a warn-tier finding that is
not gating your build". Deleting the top-level mount would silence §13 and
break §1a, which is the wrong trade. The warn IS the migration marker, and it
retires when the alias does.

WHY NOT `scitex_dev.ecosystem.deprecated_alias()`, which the §13 hint offers.
The symbol exists — checked by import, not assumed — but it pulls in
scitex-dev, this package's OPTIONAL `[cli]` extra. Using it would give the
§1a-mandated command a scitex-dev runtime dependency and break it for every
install without the extra, which is exactly what §1a's "self-contained" clause
exists to prevent.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from click.testing import CliRunner

from scitex_ui._cli import main

#: Version the legacy spelling stops working. A compatibility window with no
#: closing date is the gate-that-cannot-fail in another costume (constitution
#: §5), so the removal version is written down and asserted.
REMOVED_IN = "0.20.0"


@pytest.fixture
def run() -> CliRunner:
    """click 8.2 removed ``CliRunner(mix_stderr=...)``; stderr is separate now.

    Named because the old spelling raises TypeError rather than degrading, so a
    test copied in from an older repo fails loudly instead of silently merging
    the two streams and hiding a warning written to the wrong one.
    """
    return CliRunner()


def test_dev_group_is_registered() -> None:
    """§13: the canonical mount point exists."""
    # Arrange
    commands = main.commands
    # Act
    present = "dev" in commands
    # Assert
    assert present, "§13 requires a `dev` group; none is registered"


def test_dev_is_a_group_not_a_leaf() -> None:
    """§13: `dev` never takes a positional argument directly."""
    # Arrange
    dev = main.commands["dev"]
    # Act
    is_group = hasattr(dev, "commands")
    # Assert
    assert is_group, "`dev` must be a GROUP — the doctrine forbids a bare leaf"


def test_skills_is_mounted_under_dev() -> None:
    """§13: `scitex-ui dev skills` is the canonical spelling."""
    # Arrange
    dev = main.commands["dev"]
    # Act
    mounted = "skills" in getattr(dev, "commands", {})
    # Assert
    assert mounted, f"expected `skills` under `dev`; found {sorted(dev.commands)}"


def test_canonical_spelling_runs(run: CliRunner) -> None:
    """The canonical command works end to end."""
    # Arrange
    argv = ["dev", "skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert result.exit_code == 0, result.exception


def test_canonical_spelling_produces_output(run: CliRunner) -> None:
    """ANTI-VACUITY for the drift test below.

    If the canonical command printed nothing, the drift comparison would be
    two empty strings and would pass having measured nothing.
    """
    # Arrange
    argv = ["dev", "skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert result.stdout.strip(), "canonical command produced no output"


def test_canonical_spelling_does_not_warn(run: CliRunner) -> None:
    """Only the legacy spelling warns; the canonical one is quiet."""
    # Arrange
    argv = ["dev", "skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert "DEPRECATED" not in result.stderr, "the canonical spelling must not warn"


def test_legacy_top_level_skills_is_still_registered() -> None:
    """§1a: the top-level group must not vanish during migration."""
    # Arrange
    commands = main.commands
    # Act
    present = "skills" in commands
    # Assert
    assert present, "§1a requires `<cli> skills` while `_skills/` ships"


def test_legacy_spelling_still_runs(run: CliRunner) -> None:
    """§1a: and it must still work, not merely exist."""
    # Arrange
    argv = ["skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert result.exit_code == 0, result.exception


def test_legacy_spelling_warns(run: CliRunner) -> None:
    """A silent alias is discovered when it is REMOVED — the worst moment."""
    # Arrange
    argv = ["skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert "DEPRECATED" in result.stderr, "the legacy spelling must announce itself"


def test_the_warning_names_its_replacement(run: CliRunner) -> None:
    """A deprecation that does not say what to use instead is just noise."""
    # Arrange
    argv = ["skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert "dev skills" in result.stderr, "the warning must name the replacement"


def test_the_warning_states_when_it_stops_working(run: CliRunner) -> None:
    """An open-ended deprecation is one nobody ever acts on (constitution §5)."""
    # Arrange
    argv = ["skills", "list"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert REMOVED_IN in result.stderr, "the warning must state the removal version"


def test_the_two_spellings_have_not_drifted(run: CliRunner) -> None:
    """The alias shares the canonical group's commands rather than copying them.

    A copy would be a second implementation, and the copy nobody exercises is
    the one that rots. Asserted on the observable consequence.
    """
    # Arrange
    canonical = run.invoke(main, ["dev", "skills", "list"])
    # Act
    legacy = run.invoke(main, ["skills", "list"])
    # Assert
    assert canonical.stdout == legacy.stdout, "the two spellings have diverged"


def test_the_warning_cannot_corrupt_json(run: CliRunner) -> None:
    """§14: the warning goes to stderr, so `--json | jq` keeps working.

    The assertion with teeth. A deprecation notice on stdout breaks every
    scripted caller of the legacy spelling — turning a migration aid into the
    breakage it exists to avoid.
    """
    # Arrange
    argv = ["skills", "list", "--json"]
    # Act
    result = run.invoke(main, argv)
    # Assert
    assert json.loads(result.stdout), "the alias no longer emits parseable JSON"


def test_skills_group_does_not_import_scitex_dev() -> None:
    """§1a's self-contained clause, asserted on the import graph.

    scitex-dev is an OPTIONAL extra. If the skills group reaches it at import
    time the command breaks for every install without `[cli]` — and it would
    still pass every behavioural test above on a machine where the extra
    happens to be installed, which is every machine we develop on.
    """
    # Arrange
    import scitex_ui._skills as skills_mod

    source = pathlib.Path(skills_mod.__file__).read_text()
    # Act
    offenders = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import scitex_dev", "from scitex_dev"))
    ]
    # Assert
    assert not offenders, f"§1a skills group imports scitex-dev: {offenders}"
