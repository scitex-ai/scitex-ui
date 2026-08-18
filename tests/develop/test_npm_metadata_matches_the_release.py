#!/usr/bin/env python3
"""Guards that `package.json` tells consumers the truth about this package.

WHY THIS EXISTS — measured 2026-08-11, right after publishing 0.15.0. The
Python package had reached `0.15.0`; `package.json` still said `0.1.0`. It had
said `0.1.0` through fourteen releases, and nothing anywhere noticed.

The reason it could stay wrong so long is the reason it needs a mechanical
check rather than a note. Every consumer today links by path —

    figrecipe      "@scitex/ui": "file:../../../../../scitex-ui"
    scitex-writer  "@scitex/ui": "file:../../../../../scitex-ui"
    scitex-cloud   "@scitex/ui": "file:../scitex-ui"

— and npm ignores the version range for a `file:` dependency. So the field is
**unused by the only consumers there are**, which means being wrong costs
nothing today and everything on the day someone reads it: it is the sole
version signal any npm-side reader gets, and it is one this package publishes
about itself.

WHAT THIS DOES NOT CHECK, so a pass is not read as more than it is: whether
`@scitex/ui` is published anywhere (it is not — the registry 404s and
`private: true` would refuse a publish), or whether any consumer resolves it.
Reach is a property of the filesystem here, not of this file. See card
`scitex-ui-ts-half-has-no-release-channel-20260811` for that open question.
Only that the two version fields in this repo agree.

A SECOND CHECK WAS DRAFTED HERE AND DELETED, which is worth recording because
the deletion is the finding. It asserted that the description must not say
"React", on the reasoning that this package ships TypeScript/DOM modules. That
reasoning came from reading the `ts/` tree in an installed wheel and inferring
the absence of the other. `react/` exists: 14 `.tsx` components, react
peerDependencies, and `main`/`types` both pointing at `react/index.ts`. The
description was accurate and the guard would have forced a true statement to be
edited into a false one. Absence inferred from where you happened to look is
not absence.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

import scitex_ui

_PKG_ROOT = pathlib.Path(scitex_ui.__file__).parent.parent.parent
_PACKAGE_JSON = _PKG_ROOT / "package.json"
_PYPROJECT = _PKG_ROOT / "pyproject.toml"


@pytest.fixture
def package_json() -> dict:
    """The npm manifest, or skip where there is none.

    An installed wheel ships no package.json, so this guard is meaningful only
    in the source tree. Skipping says so rather than passing on an empty check.
    """
    if not _PACKAGE_JSON.is_file():
        pytest.skip(f"no package.json at {_PACKAGE_JSON} (installed layout)")
    return json.loads(_PACKAGE_JSON.read_text())


@pytest.fixture
def pyproject_version() -> str:
    """The released version, read from the file the release ritual bumps."""
    if not _PYPROJECT.is_file():
        pytest.skip(f"no pyproject.toml at {_PYPROJECT} (installed layout)")
    match = re.search(
        r'^version\s*=\s*"([^"]+)"', _PYPROJECT.read_text(), flags=re.MULTILINE
    )
    assert match, "pyproject.toml declares no top-level version"
    return match.group(1)


def test_probe_reads_a_plausible_pyproject_version(pyproject_version: str) -> None:
    """Positive control: a misread version would make the parity check vacuous."""
    # Arrange
    semver = re.compile(r"^\d+\.\d+\.\d+")

    # Act
    parsed = semver.match(pyproject_version)

    # Assert
    assert parsed, f"did not read a version from pyproject.toml, got {pyproject_version!r}"


def test_npm_version_matches_the_released_version(
    package_json: dict, pyproject_version: str
) -> None:
    # Arrange
    declared = package_json.get("version")

    # Act
    agrees = declared == pyproject_version

    # Assert
    assert agrees, (
        f"package.json says {declared!r} but this package released "
        f"{pyproject_version!r}.\n\n"
        "Bump the 'version' field in package.json to match. It is the only "
        "version signal an npm-side reader gets, and because every consumer "
        "links with 'file:' (where npm ignores the range) a stale value costs "
        "nothing until the moment someone believes it."
    )
