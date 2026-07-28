#!/usr/bin/env python3
"""No worktree directory may be tracked as a gitlink.

A `git worktree add` creates a directory containing its own `.git`. If anyone
then runs `git add` on it — `git add .worktrees/foo`, or a `git add -A` from
before the ignore rule existed — git records it as mode 160000, a SUBMODULE
reference, not as files. `.gitmodules` has no matching entry, so every CI job
that touches submodules ends with:

    fatal: No url found for submodule path '.worktrees/…' in .gitmodules
    ##[warning]The process '/usr/bin/git' failed with exit code 128

`.gitignore` cannot prevent this. It applies only to UNTRACKED paths, so once
a gitlink is committed the ignore rule is real but powerless — which is exactly
why adding `/.worktrees/` to .gitignore did not make the warning go away.

This test reads the git INDEX rather than the filesystem, because the entry
being wrong is precisely a fact about the index. A legitimate submodule stays
legal: it must simply be declared in .gitmodules.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _tracked_gitlinks() -> list[str]:
    # `ls-files -s` prints "<mode> <object> <stage>\t<path>"; 160000 is the
    # gitlink mode. Asking git avoids re-implementing index parsing.
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        line.split("\t", 1)[1]
        for line in out.splitlines()
        if line.startswith("160000 ")
    ]


def _declared_submodules() -> set[str]:
    gitmodules = REPO_ROOT / ".gitmodules"
    if not gitmodules.exists():
        return set()
    out = subprocess.run(
        ["git", "config", "--file", str(gitmodules), "--get-regexp", r"^submodule\..*\.path$"],
        capture_output=True,
        text=True,
    ).stdout
    return {line.split(" ", 1)[1] for line in out.splitlines() if " " in line}


def test_no_gitlink_is_tracked_without_a_gitmodules_entry():
    # Arrange
    tracked = _tracked_gitlinks()
    declared = _declared_submodules()

    # Act
    undeclared = sorted(set(tracked) - declared)

    # Assert — name the fix, since the obvious one (.gitignore) does not work.
    assert not undeclared, (
        f"{len(undeclared)} path(s) are tracked as gitlinks with no .gitmodules "
        f"entry: {', '.join(undeclared)}. Every CI job that walks submodules "
        "fails with exit 128 on these. Adding them to .gitignore will NOT help "
        "— ignore rules apply only to untracked paths. Untrack them instead:\n"
        f"    git rm --cached {' '.join(undeclared)}\n"
        "If one is a real submodule, declare it in .gitmodules."
    )


def test_worktrees_dir_is_never_tracked_at_all():
    # Arrange — the guard above allows a declared submodule anywhere; this one
    # is specific: .worktrees/ holds local scratch checkouts and nothing in it
    # should ever be in the index, declared or not.
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", ".worktrees"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    # Act / Assert
    assert not tracked, (
        f".worktrees/ has {len(tracked)} tracked path(s): {', '.join(tracked)}. "
        "These are local working directories, not source."
    )
