#!/usr/bin/env python3
"""Guards the FALLBACK inside `fromJSON(vars.CI_RUNS_ON || '...')`, and only that.

WHAT THIS IS NOT. It does not check where CI actually runs. It cannot: the
destination lives in a repo Actions variable, not in any file, so no test that
reads the repository can see it. Asserting on the default as though it were the
live value would be theatre — the default is used only when the variable is
unset, which is to say almost never.

WHAT IT IS. The default is a real, checkable property with its own failure
mode: if `CI_RUNS_ON` is ever deleted, renamed, or scoped away, every job
falls back to whatever string is written here. That fallback is the last thing
standing between a missing variable and an unintended destination, and nothing
asserted anything about it.

MEASURED 2026-08-10, so the current state is on record rather than assumed:

    repo variable   CI_RUNS_ON = ["self-hosted","Linux","X64","scitex-ci"]
    org variables   total_count 0   (exit 0 — genuinely empty, not a 403)
    environment     pypi, 0 variables

One setter, no shadowing layer above or below it, and its value is self-hosted
today. So the blind spot the sibling guard documents
(`test_fork_guard_own_workflows.py::test_no_job_targets_a_github_hosted_image`
sees literals and not expressions) is currently benign — which is worth
writing down, because "benign today" and "unchecked" are different facts and
only one of them was recorded.

THE REMAINING GAP, stated so a green run is not read as more than it is: a
change to the variable itself is invisible to this file and to every other
test here. Catching that needs something that queries the GitHub API — a
scheduled audit, not a unit test, since pytest would then need network and a
credential to pass. Card
`scitex-ui-hosted-runner-guard-blind-to-variable-destinations-20260805`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = _REPO / ".github" / "workflows"

#: A real `runs-on:` line using the expression form — capture the fallback.
#:
#: ANCHORED TO `runs-on:` AT LINE START ON PURPOSE. The first draft matched the
#: expression anywhere in the file and so counted two COMMENTS as destinations:
#: ci.yml:16 and the release workflow's line 60 both quote the expression as
#: documentation. A probe that deleted the expression from both real jobs left
#: this file GREEN, parametrised over nothing but prose. A guard that matches
#: its own comments is measuring the documentation, not the workflow.
_FALLBACK = re.compile(
    r"^\s*runs-on:\s*\$\{\{\s*fromJSON\(\s*vars\.CI_RUNS_ON\s*\|\|\s*'([^']*)'\s*\)",
    re.MULTILINE,
)

#: The jobs that are SUPPOSED to follow the variable. Named rather than counted,
#: so a job silently leaving the expression form fails here instead of shrinking
#: the parametrisation to nothing and passing.
_EXPECTED_WORKFLOWS = {"docs-sphinx.yml", "typecheck.yml"}

#: A destination is self-hosted iff it carries this label. GitHub-hosted images
#: are named (ubuntu-*, windows-*, macos-*) and never carry it.
_SELF_HOSTED = "self-hosted"


def _fallbacks() -> list[tuple[str, str]]:
    """(workflow filename, fallback literal) for every CI_RUNS_ON reference."""
    found: list[tuple[str, str]] = []
    for workflow in sorted(_WORKFLOW_DIR.glob("*.y*ml")):
        for match in _FALLBACK.finditer(workflow.read_text(encoding="utf-8")):
            found.append((workflow.name, match.group(1)))
    return found


def test_probe_finds_exactly_the_jobs_that_follow_the_variable() -> None:
    """Positive control, naming the workflows rather than counting them.

    A count is not enough. Counting `>= 1` passed while BOTH real jobs had
    their expression removed, because two comments elsewhere still quoted it —
    the parametrised assertion below then ran over prose and reported green.
    """
    # Arrange
    expected = _EXPECTED_WORKFLOWS

    # Act
    found = {workflow for workflow, _ in _fallbacks()}

    # Assert
    assert found == expected, (
        f"workflows following CI_RUNS_ON changed: expected {sorted(expected)}, "
        f"found {sorted(found)}.\n\n"
        "If a job deliberately stopped following the variable, remove it from "
        "_EXPECTED_WORKFLOWS with a reason. If one was added, add it — the "
        "point is that this set is a decision, not a side effect."
    )


@pytest.mark.parametrize(
    "workflow,fallback",
    _fallbacks(),
    ids=[f"{name}" for name, _ in _fallbacks()] or ["none"],
)
def test_fallback_destination_is_self_hosted(workflow: str, fallback: str) -> None:
    # Arrange
    required_label = _SELF_HOSTED

    # Act
    is_self_hosted = required_label in fallback

    # Assert
    assert is_self_hosted, (
        f"{workflow} falls back to {fallback!r}, which is not self-hosted.\n\n"
        "This value is used whenever the CI_RUNS_ON variable is unset — after "
        "a rename, a scope change, or a deletion. A hosted default turns any "
        "of those accidents into a silent move off our own hardware.\n\n"
        "Hosted runners are PERMITTED for public repos (operator, 2026-08-05), "
        "so this is not a policy wall. It is about which way an ACCIDENT "
        "resolves. If you want hosted by default, set it in the variable and "
        "edit this test with a reason."
    )
