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
import re

import pytest
from click.testing import CliRunner
from packaging.version import Version

from scitex_ui._cli import main
from scitex_ui._dev_group import REMOVED_IN

#: Version the legacy spelling stops working. A compatibility window with no
#: closing date is the gate-that-cannot-fail in another costume (constitution
#: §5), so the removal version is written down and asserted.
#:
#: IT USED TO BE RE-DECLARED HERE AS A LITERAL, and that is half of why the
#: window expired unnoticed: the value lived in three hand-written places (this
#: constant, the alias attribute, and the prose inside the alias's help text)
#: with nothing holding them in agreement. Imported now, so the test cannot
#: drift from the thing it tests.

_PKG_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PYPROJECT = _PKG_ROOT / "pyproject.toml"


@pytest.fixture
def shipped_version() -> str:
    """The released version, read from the file the release ritual bumps."""
    if not _PYPROJECT.is_file():
        pytest.skip(f"no pyproject.toml at {_PYPROJECT} (installed layout)")
    match = re.search(
        r'^version\s*=\s*"([^"]+)"', _PYPROJECT.read_text(), flags=re.MULTILINE
    )
    assert match, "pyproject.toml declares no top-level version"
    return match.group(1)


def test_probe_reads_a_plausible_shipped_version(shipped_version: str) -> None:
    """POSITIVE CONTROL: a misread version makes the expiry check vacuous.

    If the regex stopped matching and this returned something like `0.0.0`, the
    guard below would pass forever no matter how stale the window got — the
    exact shape of failure it exists to catch.
    """
    # Arrange
    parsed = Version(shipped_version)
    # Act
    plausible = parsed > Version("0.0.0")
    # Assert
    assert plausible, f"read an implausible shipped version: {shipped_version!r}"


def test_the_removal_version_has_not_already_passed(shipped_version: str) -> None:
    """The stated removal version must still be in the FUTURE.

    THIS IS THE GUARD THAT WAS MISSING, and its absence shipped a false
    statement to every user of 0.20.0. `_removed_in` said "0.20.0" while
    pyproject said "0.20.0", so `scitex-ui skills` told people the spelling
    "is removed in scitex-ui 0.20.0" — on 0.20.0, where it worked fine.

    The pre-existing check asserted the warning CONTAINS the version string. A
    message can contain a version and still be false; containment is not
    validity. That is the same defect as a guard counting occurrences when the
    bug is placement, and it is why this file's own §5 comment about
    gate-that-cannot-fail did not save it: the rule was quoted correctly and
    then enforced by a check that could not fail.

    IF YOU ARE HERE BECAUSE THIS WENT RED, do not reflexively bump
    `REMOVED_IN`. Bumping is a treadmill unless the §1a/§13 collision at the
    top of this file has actually been resolved — §1a requires `<cli> skills`
    to EXIST while `_skills/` ships, so the spelling may never be removable,
    which would make "removed in X" false in principle rather than early.
    Decide that, then set the value.
    """
    # Arrange
    stated, shipped = Version(REMOVED_IN), Version(shipped_version)
    # Act
    still_future = stated > shipped
    # Assert
    assert still_future, (
        f"the deprecation window has expired: it promises removal in "
        f"{REMOVED_IN} but {shipped_version} is already shipped, so the "
        f"warning users see is false. Resolve the §1a/§13 question and set a "
        f"real date — do not simply bump the number."
    )


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
