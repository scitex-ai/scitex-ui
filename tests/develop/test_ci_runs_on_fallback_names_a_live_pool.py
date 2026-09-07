#!/usr/bin/env python3
"""Guards that a workflow's `runs-on` fallback names a pool that actually exists.

WHY THIS EXISTS — measured 2026-09-04. Every `runs-on` in this repo reads

    ${{ fromJSON(vars.CI_RUNS_ON || '["self-hosted","Linux","X64","scitex-ci"]') }}

and the FALLBACK named `scitex-ci`, a label carried by exactly four runners, all
of them OFFLINE:

    offline  spartan-cpu-org-01     [self-hosted, Linux, X64, spartan-cpu, scitex-ci]
    offline  spartan-cpu-org-02     [... spartan-cpu, scitex-ci]
    offline  spartan-cpu-org-03     [... spartan-cpu, scitex-ci]
    offline  spartan-pooled-cpu-01  [... spartan-cpu, scitex-ci]

`vars.CI_RUNS_ON` is set to `scitex-org-cpu` and wins, so nothing was broken in
practice. But the moment that variable is unset — deleted, a fork, a new repo
copying these workflows — every job routes to a label no online runner carries
and **queues forever**.

THAT IS NOT A HYPOTHETICAL. It is the exact failure card
`ci-spartan-cpu-runner-pool-entirely-offline-20260822` records: the v0.17.0
release sat queued for ~41 HOURS against a dead label, never failed, and told
nobody. It surfaced only because someone queried PyPI directly instead of
trusting the tag push. The safety net was a trapdoor back into the original bug.

It is §2 verbatim — "a declaration that cannot be honoured must fail, not
evaporate." A queued-forever job is evaporation in its purest form: no red, no
notification, no verdict at all for any check to read. A job that FAILS is
recoverable; a job that never runs is invisible.

WHY CHANGING THE FALLBACK WAS SAFE, since touching release routing deserves an
explanation rather than a shrug. The fallback is only consulted when
`CI_RUNS_ON` is unset, and `CI_RUNS_ON` is currently `scitex-org-cpu`. So making
the fallback equal that value **changes nothing about where anything runs
today** — including the publish job that holds the PyPI credentials, which the
original card explicitly reserved for the operator. It only changes the disaster
case from a silent hang to running on the same pool it already uses.

WHAT THIS DOES NOT CHECK, so a pass is not read as more than it is: whether any
runner is online right now (that is environment state and would make this test
flaky), or whether `CI_RUNS_ON` is set (a repo variable, not visible from the
tree). Only that the value hard-coded as the fallback is not the known-dead
label.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_PKG_ROOT = pathlib.Path(__file__).resolve().parents[2]
_WORKFLOWS = _PKG_ROOT / ".github" / "workflows"

#: The label every fallback used to name. Measured 2026-09-04: carried by four
#: runners, all offline. Kept as a named constant rather than inlined so the
#: reason it is forbidden travels with it.
_DEAD_LABEL = "scitex-ci"

#: Matches the fallback literal inside a `runs-on` expression, capturing the
#: JSON array so the labels can be inspected rather than string-matched. Written
#: to require `CI_RUNS_ON ||` so it cannot accidentally match the unrelated
#: `SCITEX_CI_SIF` / `SCITEX_CI_APPTAINER` repo variables, which legitimately
#: contain the same characters.
_FALLBACK = re.compile(r"CI_RUNS_ON\s*\|\|\s*'(\[[^']*\])'")


#: GitHub honours BOTH `.yml` and `.yaml` for workflow files, so a `*.yml`-only
#: scan silently skips any workflow spelled the other way. Measured 2026-09-07:
#: `auto-merge-to-develop.yaml` was invisible to this guard on develop AND on
#: main. A detector that cannot SEE a file reports that file clean, which is the
#: quiet half of the same defect this module exists to catch.
_WORKFLOW_SUFFIXES = (".yml", ".yaml")


def _workflow_files() -> list[pathlib.Path]:
    """Every workflow file, in both extensions GitHub accepts."""
    return sorted(
        path
        for path in _WORKFLOWS.iterdir()
        if path.is_file() and path.suffix in _WORKFLOW_SUFFIXES
    )


def _fallbacks() -> list[tuple[str, str]]:
    """Every ``(workflow filename, fallback JSON)`` pair in .github/workflows."""
    found = []
    for path in _workflow_files():
        for match in _FALLBACK.finditer(path.read_text(encoding="utf-8")):
            found.append((path.name, match.group(1)))
    return found


@pytest.fixture
def fallbacks() -> list[tuple[str, str]]:
    """The fallbacks, or skip where there is no workflow tree.

    An installed wheel ships no `.github/`, so this guard is meaningful only in
    the source tree. Skipping says so rather than passing on an empty check.
    """
    if not _WORKFLOWS.is_dir():
        pytest.skip(f"no workflow tree at {_WORKFLOWS} (installed layout)")
    return _fallbacks()


def test_the_scan_finds_fallbacks_at_all(fallbacks) -> None:
    """POSITIVE CONTROL: an empty scan would make the guard below vacuous.

    If the expression syntax changes and this regex stops matching, the real
    check passes forever over zero rows — the precise shape of failure it
    exists to catch. This is the same lesson as the guard whose parameter list
    silently emptied.
    """
    # Arrange
    found = fallbacks
    # Act
    count = len(found)
    # Assert
    assert count > 0, (
        f"no `CI_RUNS_ON ||` fallback found in {_WORKFLOWS}; the pattern has "
        "stopped matching and the guard below is measuring nothing"
    )


def test_the_detector_would_catch_the_dead_label() -> None:
    """POSITIVE CONTROL: the pattern matches the exact string that was wrong.

    Without this, an over-tightened regex reports a clean tree forever.
    """
    # Arrange
    sample = """runs-on: ${{ fromJSON(vars.CI_RUNS_ON || '["self-hosted","scitex-ci"]') }}"""
    # Act
    match = _FALLBACK.search(sample)
    # Assert
    assert match and _DEAD_LABEL in match.group(1), (
        f"detector missed a fallback naming {_DEAD_LABEL!r}: {sample!r}"
    )


def test_the_detector_ignores_the_similarly_named_repo_variables() -> None:
    """NEGATIVE CONTROL: `SCITEX_CI_SIF` and friends must not be flagged.

    Those are real repo variables holding a container path and an apptainer
    binary. A pattern loose enough to hit them would flag correct config and get
    this guard deleted as noise.
    """
    # Arrange
    innocent = (
        "SCITEX_CI_SIF: ~/.scitex/dev/containers/ci-cpu.sif\n"
        "SCITEX_CI_APPTAINER: ~/.env-3.11/bin/apptainer\n"
        "# the scitex-ci label used to be the fallback\n"
    )
    # Act
    matches = _FALLBACK.findall(innocent)
    # Assert
    assert matches == [], f"detector flagged non-`runs-on` text: {matches}"


def test_the_detector_ignores_a_comment_that_merely_names_the_expression() -> None:
    """NEGATIVE CONTROL: prose naming the fallback must not be matched.

    A detector that cannot tell a real `runs-on` expression from a comment
    discussing one would flag this file's own docstring, and every workflow
    comment explaining the routing. Required by
    `test_detectors_carry_controls.py`, which rejected an earlier version of
    this file for lacking exactly this — correctly, and for the fifth time
    across this repo's detectors.
    """
    # Arrange
    sample = "# the CI_RUNS_ON || fallback used to name scitex-ci here"
    # Act
    hit = _FALLBACK.search(sample)
    # Assert
    assert hit is None, f"detector matched a mere mention: {sample!r}"


def test_no_fallback_names_the_dead_label(fallbacks) -> None:
    """The defect this file was written for."""
    # Arrange
    found = fallbacks
    # Act
    offenders = [f"{name}: {value}" for name, value in found if _DEAD_LABEL in value]
    # Assert
    assert offenders == [], (
        f"a `runs-on` fallback names {_DEAD_LABEL!r}, which no online runner "
        "carries — if CI_RUNS_ON is ever unset these jobs queue forever and "
        "report nothing:\n" + "\n".join(offenders)
    )


@pytest.fixture
def workflow_files_on_disk() -> set[str]:
    """Workflow filenames actually present, or skip where there is no tree.

    THE EXTENSIONS HERE ARE A LITERAL, deliberately NOT ``_WORKFLOW_SUFFIXES``.
    Deriving the expectation from the constant under test makes the assertion
    compare the scan against itself: narrowing the constant shrinks the
    expectation in lockstep and the test still passes. Measured 2026-09-07 --
    the first version did exactly that, and a mutation probe setting the
    constant to ``(".yml",)`` stayed GREEN. These two extensions are GitHub's
    rule, not ours, so the duplication is an independent oracle rather than a
    DRY violation.

    The skip lives in this fixture rather than in the test body because
    ``pytest.skip`` counts as an assertion construct under STX-TQ007, so a body
    holding both a skip and an assert carries two contracts. The sibling
    ``fallbacks`` fixture already establishes this shape in this module.
    """
    if not _WORKFLOWS.is_dir():
        pytest.skip(f"no workflow tree at {_WORKFLOWS} (installed layout)")
    return {
        path.name
        for path in _WORKFLOWS.iterdir()
        if path.is_file() and path.suffix in (".yml", ".yaml")
    }


def test_the_scan_covers_every_workflow_file(workflow_files_on_disk) -> None:
    """The scan must see EVERY workflow on disk, not merely a non-zero number.

    ``test_the_scan_finds_fallbacks_at_all`` is an anti-vacuity check: it proves
    the scan found SOMETHING. That cannot distinguish a scan covering every
    workflow from one covering all but a file whose extension it forgot -- both
    return a healthy-looking count. This checks the DENOMINATOR instead: the
    set of files scanned equals the set of workflow files present.

    IF THIS FAILS a workflow is not being audited by any test in this module,
    and its `runs-on` could name a pool with nothing online while the suite
    stays green. Add the extension to ``_WORKFLOW_SUFFIXES``; do not narrow the
    expectation.
    """
    # Arrange
    on_disk = workflow_files_on_disk
    # Act
    scanned = {path.name for path in _workflow_files()}
    # Assert
    assert scanned == on_disk, (
        f"the workflow scan covers {sorted(scanned)} but {sorted(on_disk)} are "
        f"present; {sorted(on_disk - scanned)} would be audited by nothing"
    )
