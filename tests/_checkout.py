#!/usr/bin/env python3
"""Locate the package tree UNDER TEST — the checkout, never site-packages.

WHY THIS MODULE EXISTS, measured 2026-08-18.

Twenty-two test modules located shipped assets like this::

    pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui" / ...

On this host that resolves to
``/opt/venv-sac/lib/python3.12/site-packages/scitex_ui`` (version 0.15.0), NOT
to the checkout. So every one of those guards was asserting about the INSTALLED
package rather than the code a pull request changes.

It is invisible rather than obvious, and that is the point:

* Where the install IS editable, the two paths are the same file and everything
  works. The bug only appears where it matters — a non-editable install, i.e.
  precisely the environment where a stale package could differ from the branch.
* A guard written that way can go RED FOR THE RIGHT REASON IN THE WRONG TREE.
  That happened: a new guard was written with this spelling, run in a worktree,
  and reported exactly the right offending classes — because the installed copy
  carried the same defect. The red looked like proof and was a coincidence.
  Had the checkout then been fixed, the guard would have stayed red and the fix
  would have looked ineffective.
* Symmetrically, a regression INTRODUCED in a branch is undetectable: the guard
  reads a package that does not contain the regression and passes.

So: a check that cannot see the change it guards. §2's "a gate that cannot fail
is not a gate", in the form where the gate looks like it is working.

USE :func:`package_dir` for anything that asserts about SOURCE. Reach for
``scitex_ui.__file__`` only when the assertion is genuinely ABOUT THE INSTALLED
ARTIFACT — a packaging test verifying what shipped — and say so in a comment,
because the next reader cannot tell the two intentions apart from the code.

``tests/develop/test_no_asset_paths_via_installed_package.py`` enforces this.
"""

from __future__ import annotations

import pathlib

#: Repo root: this file is ``<root>/tests/_checkout.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def package_dir() -> pathlib.Path:
    """Return ``<checkout>/src/scitex_ui``.

    Raises rather than returning a wrong-but-plausible path: a silently wrong
    root would make every guard that uses it pass vacuously, which is the
    failure this module exists to prevent.
    """
    pkg = REPO_ROOT / "src" / "scitex_ui"
    if not pkg.is_dir():
        raise RuntimeError(
            f"expected the package source at {pkg}, which does not exist. "
            f"REPO_ROOT resolved to {REPO_ROOT} from {__file__}. If the tests "
            "directory moved relative to the repo root, update REPO_ROOT here "
            "rather than falling back to scitex_ui.__file__ — that reads "
            "site-packages and silently checks the wrong tree."
        )
    return pkg


def static_dir() -> pathlib.Path:
    """Return ``<checkout>/src/scitex_ui/static/scitex_ui``."""
    return package_dir() / "static" / "scitex_ui"


def css_dir() -> pathlib.Path:
    """Return the shipped stylesheet root in the checkout."""
    return static_dir() / "css"


def templates_dir() -> pathlib.Path:
    """Return ``<checkout>/src/scitex_ui/templates``."""
    return package_dir() / "templates"
