"""Guard: a `pull_request_target` workflow executed from the DEFAULT branch must
pin the SAME org callee as develop.

This is DoD 3 of scitex-ui-cla-check-queues-forever-on-a-dead-pool-from-stale-
main-20260904 — the generalisation, not "spartan-cpu is dead".

WHY THIS SHAPE (from the card's investigation, c_e09db1ff18aa):
`pull_request_target` IGNORES the PR's branch and executes the workflow from the
DEFAULT branch (main). So the file under review (on develop) is NOT the file that
runs. The 2026-08-22 defect: main's cla.yml pinned an org callee (`@1c593985`)
that hard-coded `spartan-cpu` (an offline pool); develop's had already been
repointed (`@f5d19f5b`, which defaults runs_on to ubuntu-latest). Every PR since
08-22 ran MAIN's stale pin and queued forever — and a queued job cannot go red,
so nothing alerted. The fix landed via the develop->main promotion (PR #209); the
effect was observed on live PRs (DoD 2).

WHAT THIS GUARDS: the CLASS recurring — the moment main and develop diverge again
on a PRT workflow's callee pin, the default branch silently executes the stale
copy. A guard reading the WORKING TREE cannot see this (the card's gap #2). So
this reads BOTH refs via `git show origin/main:<path>` / `origin/develop:<path>`
— OFFLINE (same-repo refs, no runners API, no network) — and compares the org
callee pins on the `pull_request_target`-triggered workflows.

THE INVARIANT: for PRT-triggered workflows, the set of
(workflow, callee, pin-sha) on main must EQUAL the set on develop. Any difference
means the default branch executes a workflow/callee develop does not — the
silent-stale-execution defect. Divergence in EITHER direction is flagged (main
older than develop, the 08-22 shape, AND main carrying a PRT pin develop lacks).

THE TWO CHANNELS (kept opposite, as the sibling guard does):
  - a ref cannot be read (main missing, fetch not run) -> FAIL LOUD. A guard that
    silently cannot answer its own question is the failure mode this card is
    about; it must never read an unreadable ref as "clean".
  - the refs read fine but the pins differ -> FAIL, naming the exact divergence.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

#: Repo root, resolved from this file's location (tests/develop/ -> parents[2]).
#: Same shape as the sibling guard; a wrong root fails the denominator probe
#: rather than reading the wrong population.
_PKG_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: GitHub honours BOTH .yml and .yaml. The sibling guard's lesson
#: (c_e09db1ff18aa): auto-merge-to-develop.yaml was invisible to a *.yml-only scan
#: on develop AND main. A PRT workflow spelled .yaml is exactly the shape that
#: would evade a narrower scan, so both extensions are in scope.
_WORKFLOW_SUFFIXES = (".yml", ".yaml")

#: The trigger that makes a workflow execute from the DEFAULT branch rather than
#: the PR's branch. Only PRT-triggered workflows are in this guard's population.
_PRT = "pull_request_target"

#: An org reusable-workflow pin: `uses: scitex-ai/.github/.github/workflows/
#: <name>@<sha>`. The pin is the CALLEE the default branch actually executes.
#: Requires the full org path (not just @sha) so an unrelated org pin cannot
#: masquerade as the PRT callee.
_CALLEE_PIN = re.compile(
    r"(?m)^[ \t-]*uses:\s*scitex-ai/\.github/\.github/workflows/"
    r"(?P<callee>[^\s'\"@]+)@(?P<sha>[0-9a-f]{7,40})"
)


def _git_show(ref: str, path: str) -> str | None:
    """Return the file at `ref:path`, or None if absent on that ref. No network:
    refs in the local repo. An absent path (CalledProcessError) is the "not on
    this ref" signal, distinct from a transport failure (raises, caught by the
    fail-loud channel in the guard body)."""
    try:
        return subprocess.check_output(
            ["git", "-C", str(_PKG_ROOT), "show", f"{ref}:{path}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None


def _list_workflow_files(ref: str) -> list[str]:
    """Every workflow BASENAME on `ref`, both GitHub extensions. The colon form
    (ref:.github/workflows/) yields names relative to that dir, not full paths —
    the full-path form would make _git_show prepend the dir twice and read
    nothing, which the denominator probe then (correctly) refuses to call clean."""
    out = subprocess.check_output(
        ["git", "-C", str(_PKG_ROOT), "ls-tree", "--name-only", ref + ":.github/workflows/"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [
        line
        for line in out.splitlines()
        if line and line.endswith(_WORKFLOW_SUFFIXES)
    ]


def _prt_pins(ref: str) -> list[tuple[str, str, str]]:
    """For every pull_request_target-triggered workflow on `ref`, the set of
    (workflow, callee, pin-sha) it executes — the population the default branch
    actually runs for PRs."""
    pins: list[tuple[str, str, str]] = []
    for name in _list_workflow_files(ref):
        body = _git_show(ref, f".github/workflows/{name}")
        if body is None:
            continue  # absent on this ref: caught by the set comparison
        if _PRT not in body:
            continue  # not executed from the default branch: out of population
        for m in _CALLER_PIN(body):
            pins.append((name, m.group("callee"), m.group("sha")))
    return pins


def _CALLER_PIN(text: str):
    """The org callee pins in `text`, as match objects."""
    return _CALLEE_PIN.finditer(text)


def test_callee_pin_detector_matches_a_real_uses_entry():
    # Arrange
    text = "    uses: scitex-ai/.github/.github/workflows/cla.yml@f5d19f5b"
    # Act
    match = _CALLEE_PIN.search(text)
    # Assert
    assert match


def test_callee_pin_detector_ignores_a_comment_mention():
    # Arrange
    text = "# uses: scitex-ai/.github/.github/workflows/cla.yml@1c593985"
    # Act
    match = _CALLEE_PIN.search(text)
    # Assert
    assert match is None


def pins_agree(main_pins, develop_pins) -> list[str]:
    """Pure comparison: return the divergence descriptions (empty = agree).

    Factored out of the git-read path so the REJECT arm is testable with
    synthetic inputs — `main` is immutable, so the negative control cannot be a
    live ref mutation. A set comparison (not "main must be newer") because the
    defect is DIVERGENCE in either direction, and "newer" is a SHA-timestamp
    heuristic this guard refuses to invent (the card's discipline: do not guess
    a cause for a measured anomaly)."""
    def _only(one, ref, other):
        oset = set(other)
        return [f"{'/'.join(p)} on {ref} only" for p in one if p not in oset]

    return sorted(_only(main_pins, "main", develop_pins) + _only(develop_pins, "develop", main_pins))


def _read_pins():
    """Read PRT callee pins for both refs. Fail-loud on unreadable ref."""
    try:
        main_pins = _prt_pins("origin/main")
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.fail(
            f"cannot read origin/main PRT pins ({exc!r}). This guard compares "
            "the default branch against develop; if it cannot read the default "
            "branch the answer is UNKNOWN, not clean. Run `git fetch origin "
            "main` and retry — never read an unreadable ref as agreement."
        )
    try:
        develop_pins = _prt_pins("origin/develop")
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.fail(
            f"cannot read origin/develop PRT pins ({exc!r}). Same fail-loud "
            "channel as origin/main: an unreadable ref is UNKNOWN, not clean."
        )
    return main_pins, develop_pins


def test_develop_has_prt_callee_pins():
    """Anti-vacuity denominator: at least one PRT workflow with an org callee
    pin must be present on develop. If this reads empty, the divergence check
    below passes over nothing — the sibling guard's "a forgotten extension
    makes the scan report clean" trap, in the ref dimension."""
    # Arrange
    _, develop_pins = _read_pins()
    # Act
    n = len(develop_pins)
    # Assert
    assert n > 0, (
        "no pull_request_target workflow with an org callee pin was found on "
        "origin/develop. Either the PRT trigger spelling changed (check the "
        f"{_PRT!r} literal) or the callee-pin regex no longer matches the "
        "`uses: scitex-ai/.github/.github/workflows/<name>@<sha>` shape — the "
        "guard would then prove nothing, which is the failure it prevents."
    )


def test_default_branch_prt_pins_agree_with_develop():
    # Arrange
    main_pins, develop_pins = _read_pins()
    # Act
    divergences = pins_agree(main_pins, develop_pins)
    # Assert — the default branch executes exactly what develop runs for PRs.
    assert not divergences, (
        "the DEFAULT branch's pull_request_target callee pins diverge from "
        "develop:\n  " + "\n  ".join(divergences) + "\n\n"
        "pull_request_target executes the workflow from the DEFAULT branch, so "
        "a divergent pin means PRs are running a callee develop does not use — "
        "the silent-stale-execution defect of 2026-08-22 (main pinned an "
        "offline-runner callee develop had already repointed). Sync develop -> "
        "main (the promotion-PR shape) or repoint the divergent callee pin so "
        "the default branch matches develop."
    )


def test_the_guard_sees_a_divergent_pin():
    # Reject arm, at the LOGIC level (main is immutable, so no live ref can be
    # mutated to produce one). A main pin that differs from develop's must be
    # flagged — otherwise the guard is the "cannot fail" gate it guards against.
    # Arrange — the 08-22 shape in miniature: develop repointed, main still old.
    main_pins = [("cla.yml", "cla.yml", "1c59398500000000000000000000000000000000")]
    develop_pins = [("cla.yml", "cla.yml", "f5d19f5b7424fcf985137bb6acff54f5d0e11749")]
    # Act
    divergences = pins_agree(main_pins, develop_pins)
    # Assert — BOTH sides named: main's stale pin AND develop's current one.
    assert len(divergences) == 2 and any("on main only" in d for d in divergences) and any(
        "on develop only" in d for d in divergences
    ), (
        "a divergent PRT callee pin must be flagged on BOTH the main and the "
        f"develop side (the stale one and the current one), got: {divergences}"
    )


def test_agreeing_pins_pass_the_guard():
    # Positive control: identical pins on both refs produce no divergence.
    # Arrange
    pins = [("cla.yml", "cla.yml", "f5d19f5b7424fcf985137bb6acff54f5d0e11749")]
    # Act
    divergences = pins_agree(pins, list(pins))
    # Assert
    assert divergences == []


def test_a_new_prt_workflow_on_main_is_a_divergence():
    # Reject arm, direction two: main carrying a PRT pin develop lacks is ALSO a
    # divergence (develop is ahead; the default branch running a pin develop does
    # not use is the risk, the mirror of the 08-22 shape).
    # Arrange
    main_pins = [
        ("cla.yml", "cla.yml", "f5d19f5b7424fcf985137bb6acff54f5d0e11749"),
        ("other.yml", "other.yml", "aaaa1111bbbb2222cccc3333dddd4444eeee5555"),
    ]
    develop_pins = [("cla.yml", "cla.yml", "f5d19f5b7424fcf985137bb6acff54f5d0e11749")]
    # Act
    divergences = pins_agree(main_pins, develop_pins)
    # Assert — only the extra main-side pin is named, develop's matching pin is not.
    assert len(divergences) == 1 and "other.yml" in divergences[0] and "on main only" in divergences[0], (
        f"a main-only PRT pin must be the single divergence, got: {divergences}"
    )
