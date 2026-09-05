#!/usr/bin/env python3
"""Guards against silently unpackaged static assets.

Lives in ``tests/develop/`` rather than ``tests/scitex_ui/`` because it checks
repo packaging configuration, not a source module — there is no
``src/scitex_ui/packaging.py`` for it to mirror.

This package has shipped broken wheels three times for one reason: a file
under ``static/`` matched a blanket rule in the shared gitignore, so git never
tracked it, so hatchling never packaged it — and nothing failed. The wheel was
simply missing a file, while editable installs still saw it.

* 0.6.1/0.6.2 — ``**/*old*`` (a substring rule) matched ``_BinaryPlaceholder.ts``.
* 0.7.0 — ``**/*.svg`` (meant for generated figures) matched the brand favicon.

The invariant is narrow and checkable without building: **nothing under
``src/scitex_ui/static/`` may be gitignored.** An ignored file there is absent
from every published artifact, whatever the rule's intent was.

THAT CLAIM IS NOT THE ONE WE ACTUALLY CARE ABOUT, and the difference matters:
"not EXCLUDED" and "IN the wheel" look interchangeable and are not. The first
constrains a config file; the second constrains the artifact a consumer
installs. Only the second is what an adopter experiences.

The gap is not hypothetical. scitex-cards refused to delete their working
right-click JS because they checked the INSTALLED package and found
``ts/app/context-menu`` absent — the module was merged, but no release
contained it. Their gate fired because it was mechanical rather than
remembered, which is the only reason it worked. So the second half of this
file builds the wheel and asserts every registered component's declared assets
are inside it. Knowing the trap does not route you around it; a check does.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import scitex_ui

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC = _REPO_ROOT / "src" / "scitex_ui" / "static"


def _static_files():
    return [p for p in _STATIC.rglob("*") if p.is_file()]


def _gitignored(paths):
    """Return the subset of ``paths`` git would ignore.

    ``git check-ignore`` exits 1 when nothing matches, which is the success
    case here, so the return code is not an error condition.
    """
    result = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "check-ignore", "--stdin"],
        input="\n".join(str(p) for p in paths),
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_static_dir_is_not_empty():
    # Arrange — a wrong repo root would make the real guard below pass
    # vacuously, so pin that down separately.
    static = _STATIC
    # Act
    files = _static_files()
    # Assert
    assert files, f"no static files found under {static} — wrong repo root?"


def test_no_static_asset_is_gitignored():
    # Arrange
    files = _static_files()
    # Act
    ignored = _gitignored(files)
    # Assert
    assert ignored == []


# --- artifact-level: what a consumer actually installs ---------------------


@pytest.fixture(scope="module")
def wheel_names(tmp_path_factory) -> list[str]:
    """Every path inside a freshly built wheel.

    Module-scoped: the build costs seconds, and every assertion below reads
    the same artifact.
    """
    outdir = tmp_path_factory.mktemp("wheel")

    # THE BUILD TOOL'S ABSENCE AND A BROKEN WHEEL NEED OPPOSITE RESPONSES, so
    # they must not surface identically. Checked BEFORE running, because
    # `-m build` exits non-zero for both reasons and `check=True` then raises a
    # bare CalledProcessError that names neither.
    #
    # Measured 2026-08-18 in the agent venv: the two assertions below reported
    # as ERRORS at fixture setup with `subprocess.CalledProcessError` and no
    # further detail. The actual cause was `No module named build` — a missing
    # dev dependency, not a packaging defect. In a summary reading
    # "282 passed, 2 errors" that is indistinguishable from infrastructure
    # noise, and it is how the gate stayed dead without anyone noticing.
    #
    # This is §2's "a gate that cannot fail is not a gate" in its quieter form:
    # the gate could not PASS either. It returned the same answer whether the
    # wheel was perfect or catastrophically wrong.
    if importlib.util.find_spec("build") is None:
        pytest.fail(
            "the packaging gate cannot run: the `build` module is not "
            f"installed for {sys.executable}.\n\n"
            "This is an ENVIRONMENT gap, not a packaging defect — the wheel "
            "has not been examined at all, so treat this as UNKNOWN rather "
            "than as a pass.\n\n"
            "Fix:  python -m pip install build\n"
            "(`build` is a dev dependency precisely so this check stays "
            "offline and bounded; see the --no-isolation note below.)"
        )

    # --no-isolation deliberately: the default builds in a fresh venv and
    # DOWNLOADS the backend, which turns this into a network-dependent test
    # that hangs rather than fails when the index is slow. hatchling is a dev
    # dependency precisely so this stays offline and bounded.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(outdir),
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        # check=False + an explicit failure so the BUILD OUTPUT reaches the
        # reader. `check=True` raises a CalledProcessError whose str() shows
        # the command and the exit code and discards stdout/stderr — i.e. it
        # says a build failed and never says why.
        pytest.fail(
            f"wheel build failed (exit {result.returncode}). The build tool IS "
            "installed, so this is a genuine packaging failure rather than a "
            f"missing dependency.\n\n--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    wheels = list(outdir.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    with zipfile.ZipFile(wheels[0]) as zf:
        return zf.namelist()


def _declared_assets() -> list[str]:
    """Every css_file / ts_entry declared by a registered component."""
    assets: list[str] = []
    for name in scitex_ui.list_components():
        cls = scitex_ui.get_component(name)
        if getattr(cls, "css_file", None):
            assets.append(cls.css_file)
        if getattr(cls, "ts_entry", None):
            # ts_entry omits the extension by package convention.
            assets.append(f"{cls.ts_entry}.ts")
    return assets


def test_wheel_contains_something(wheel_names):
    # Arrange — a wheel that failed to collect static assets would make the
    # real guard below pass over an empty expectation.
    # Act
    static_in_wheel = [n for n in wheel_names if "/static/scitex_ui/" in n]
    # Assert
    assert static_in_wheel, "the wheel carries no static assets at all"


def test_every_declared_asset_is_in_the_wheel(wheel_names):
    # Arrange
    declared = _declared_assets()
    packaged = set(wheel_names)
    # Act
    missing = sorted(a for a in declared if f"scitex_ui/static/{a}" not in packaged)
    # Assert
    assert not missing, (
        f"{missing} are declared by registered components but are NOT in the "
        f"wheel. list_components() would promise them to adopters while the "
        f"installed package cannot serve them — the defect scitex-cards caught "
        f"by checking their installed tree rather than trusting a merge."
    )


def test_declared_assets_is_not_empty():
    # Arrange
    # Act
    declared = _declared_assets()
    # Assert
    assert len(declared) > 20, (
        f"only {len(declared)} declared assets discovered; the registry lookup "
        f"drifted, so the wheel guard would prove nothing"
    )
