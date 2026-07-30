"""Locally-declared self-hosted jobs must refuse fork code before checkout.

scitex-ai/.github#23 put a pre-checkout fork guard on the five REUSABLE
workflows this repo calls. A reusable workflow cannot guard a job declared
locally, so `typecheck` and `docs-sphinx` — both `on: pull_request`, both
`runs-on: [self-hosted, Linux, X64, spartan-cpu]`, both running
`actions/checkout` — were outside that PR's reach entirely. Found by auditing
this repo afterwards rather than assuming the shared fix covered it.

The jobs run BARE on shared University of Melbourne HPC nodes: no container,
no overlay, two concurrent jobs sharing one $HOME (measured by scitex-hpc on
the CI supervisor allocation, job 28161762, spartan-bm062). `npm ci` runs the
PR's own lifecycle scripts; sphinx EXECUTES the PR's conf.py as Python.

Operator, 2026-07-30: 「大学の資源を外部の人にも使わせる形になったら一発で
アウト」. Operator, 2026-07-14 (PS-169): 「github側のランナーというのは本当に
もう一切使わないでください…強制です、例外なしです」. Nothing sits in the
intersection, so fork code is REFUSED here, not re-routed.

THE COVERED SET IS DERIVED, NOT LISTED: a job needs the guard when its
workflow has a `pull_request` trigger AND the job resolves to a self-hosted
runner AND the job checks out. Add such a job and these tests go red on the
change that adds it. The release workflow is excluded by the trigger arm (tags
only), not by an exemption — `github.event.pull_request` is always null there.

WHAT THIS DOES NOT CLAIM. For `pull_request`, GitHub runs workflow definitions
from the PR's own head, so a fork can delete these guards in its own PR. The
boundary is the fork-PR approval policy (`all_external_contributors`, measured
on 74/74 public scitex-ai repos, 2026-07-30) — a human click. This closes the
default path only.

Mutation-checked: moving a guard after checkout, dropping one, relaxing the
predicate, or adding a self-hosted PR job without a guard each turn at least
one test red.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = _REPO / ".github" / "workflows"

_GUARD_IF = (
    "github.event_name == 'pull_request' && "
    "github.event.pull_request.head.repo.full_name != github.repository"
)
_GUARD_NAME = "Refuse to run fork-authored code on self-hosted infrastructure"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _triggers(workflow: dict) -> dict:
    """The `on:` block. YAML 1.1 parses the bare key `on` as the boolean True."""
    for key in (True, "on"):
        if key in workflow:
            block = workflow[key]
            if isinstance(block, dict):
                return block
            if isinstance(block, list):
                return dict.fromkeys(block)
            return {str(block): None}
    return {}


def _reacts_to_pull_request(workflow: dict) -> bool:
    return "pull_request" in _triggers(workflow)


def _is_self_hosted(job: dict) -> bool:
    """True for both spellings this repo uses.

    The list form names the labels directly. The fleet's canonical expression
    form embeds them in a fromJSON default:

        runs-on: ${{ fromJSON(vars.CI_RUNS_ON || '["self-hosted",...]') }}

    A membership test alone would miss the second and silently exempt every
    job that uses it — which is most of the release workflow.
    """
    runs_on = job.get("runs-on", "")
    if isinstance(runs_on, dict):
        runs_on = runs_on.get("labels", [])
    if isinstance(runs_on, list):
        return "self-hosted" in [str(label) for label in runs_on]
    return "self-hosted" in str(runs_on)


def _checks_out(job: dict) -> bool:
    steps = job.get("steps") or []
    return any("actions/checkout" in str(step.get("uses", "")) for step in steps)


def _guarded_jobs() -> list[tuple[str, str, dict]]:
    found: list[tuple[str, str, dict]] = []
    for path in sorted(_WORKFLOW_DIR.glob("*.y*ml")):
        workflow = _load(path)
        if not _reacts_to_pull_request(workflow):
            continue
        for job_id, job in (workflow.get("jobs") or {}).items():
            if _is_self_hosted(job) and _checks_out(job):
                found.append((path.name, job_id, job))
    return found


_TARGETS = _guarded_jobs()
_IDS = [f"{workflow}:{job_id}" for workflow, job_id, _ in _TARGETS]


# ---------------------------------------------------------------------------
# The selector first. An empty parametrize list reports SKIPPED, and a suite
# of skips reads as a pass — so these are the positive control for the file.
# ---------------------------------------------------------------------------


def test_selector_finds_both_locally_declared_jobs() -> None:
    # Arrange
    known_today = 2
    # Act
    found = len(_TARGETS)
    # Assert
    assert found >= known_today, f"selector found only {_IDS} — it is broken"


def test_selector_includes_the_required_typecheck_job() -> None:
    # Arrange
    expected = "typecheck.yml:typecheck"
    # Act
    selected = _IDS
    # Assert
    assert expected in selected, "typecheck is a required check and must be covered"


def test_selector_excludes_the_tag_triggered_release_workflow() -> None:
    # Arrange
    release = "pypi-publish-and-github-release-on-tag.yml"
    # Act
    release_jobs = [i for i in _IDS if i.startswith(release)]
    # Assert
    assert not release_jobs, "release runs on tags; there is no pull_request to gate"


def test_self_hosted_detection_handles_the_fromjson_expression_form() -> None:
    # Arrange
    expression_job = {
        "runs-on": '${{ fromJSON(vars.CI_RUNS_ON || \'["self-hosted","Linux"]\') }}'
    }
    # Act
    detected = _is_self_hosted(expression_job)
    # Assert
    assert detected, "the expression form must not silently read as hosted"


# ---------------------------------------------------------------------------
# The guard itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("workflow", "job_id", "job"), _TARGETS, ids=_IDS)
def test_guard_step_is_present(workflow: str, job_id: str, job: dict) -> None:
    # Arrange
    steps = job["steps"]
    # Act
    names = [step.get("name") for step in steps]
    # Assert
    assert _GUARD_NAME in names, f"{workflow}:{job_id} has no fork guard"


@pytest.mark.parametrize(("workflow", "job_id", "job"), _TARGETS, ids=_IDS)
def test_guard_step_precedes_every_checkout(
    workflow: str, job_id: str, job: dict
) -> None:
    # Arrange
    steps = job["steps"]
    # Act
    guard_at = next(
        i for i, step in enumerate(steps) if step.get("name") == _GUARD_NAME
    )
    first_checkout_at = next(
        i
        for i, step in enumerate(steps)
        if "actions/checkout" in str(step.get("uses", ""))
    )
    # Assert
    assert guard_at < first_checkout_at, (
        f"{workflow}:{job_id} guards AFTER checkout — fork content is already on "
        "the node by then, so the step is a report, not a barrier"
    )


@pytest.mark.parametrize(("workflow", "job_id", "job"), _TARGETS, ids=_IDS)
def test_guard_predicate_is_the_sanctioned_one(
    workflow: str, job_id: str, job: dict
) -> None:
    # Arrange
    guard = next(s for s in job["steps"] if s.get("name") == _GUARD_NAME)
    # Act
    normalised = " ".join(str(guard.get("if", "")).split())
    # Assert
    assert normalised == _GUARD_IF, f"{workflow}:{job_id} predicate drifted"


@pytest.mark.parametrize(("workflow", "job_id", "job"), _TARGETS, ids=_IDS)
def test_guard_exits_nonzero_rather_than_skipping(
    workflow: str, job_id: str, job: dict
) -> None:
    # Arrange
    guard = next(s for s in job["steps"] if s.get("name") == _GUARD_NAME)
    # Act
    body = guard.get("run", "")
    # Assert
    assert "exit 1" in body, (
        f"{workflow}:{job_id} guard does not fail. A skipped job's check can be "
        "reported as successful to branch protection — a red that looks green"
    )


@pytest.mark.parametrize(("workflow", "job_id", "job"), _TARGETS, ids=_IDS)
def test_guard_tells_the_reviewer_what_to_do_instead(
    workflow: str, job_id: str, job: dict
) -> None:
    # Arrange
    guard = next(s for s in job["steps"] if s.get("name") == _GUARD_NAME)
    # Act
    body = guard.get("run", "")
    # Assert
    assert "gh pr checkout" in body, (
        f"{workflow}:{job_id} states the refusal without the remedy; an error "
        "that only says what broke is half-written"
    )


# ---------------------------------------------------------------------------
# PS-169 locally: no job in this repo may resolve to a GitHub-hosted image.
# ---------------------------------------------------------------------------


_HOSTED_PREFIXES = ("ubuntu-", "macos-", "windows-")
_ALL_JOBS = [
    (path.name, job_id, job)
    for path in sorted(_WORKFLOW_DIR.glob("*.y*ml"))
    for job_id, job in (_load(path).get("jobs") or {}).items()
]


@pytest.mark.parametrize(
    ("workflow", "job_id", "job"),
    _ALL_JOBS,
    ids=[f"{w}:{j}" for w, j, _ in _ALL_JOBS],
)
def test_no_job_targets_a_github_hosted_image(
    workflow: str, job_id: str, job: dict
) -> None:
    # Arrange
    runs_on = job.get("runs-on", "")
    labels = runs_on if isinstance(runs_on, list) else [str(runs_on)]
    # Act
    hosted = [
        label for label in labels if str(label).startswith(_HOSTED_PREFIXES)
    ]
    # Assert
    assert not hosted, (
        f"{workflow}:{job_id} targets {hosted}. Operator mandate 2026-07-14 "
        "(PS-169) forbids GitHub-hosted runners with no exceptions; if the "
        "self-hosted pool cannot run it, fix the pool"
    )
