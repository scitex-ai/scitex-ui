#!/usr/bin/env python3
"""Release gates: the artifact must match the tag, and must contain its assets.

WHY THIS EXISTS (incident 2026-07-28, tag v0.12.1):
the release pipeline built a wheel, uploaded it, and only then discovered the
wheel said ``0.11.1`` while the tag said ``v0.12.1``. PyPI answered ``400 Bad
Request`` — a message that names neither the version nor the mismatch. The tag
had been created on a ref that predated the version bump, and *every* job up to
the upload passed: tests green, build green, artifact uploaded. Nothing in the
pipeline compared the thing it built to the thing it was asked to build.

The second gate covers the rung after that one. "Published" is not "consumable":
a wheel can resolve from PyPI and still be missing the static assets a browser
needs, because a packaging exclude silently dropped them. That failure is
invisible to any check that only asks whether the version exists.

Both gates are importable functions rather than inline shell so their FAILURE
arms can be executed by tests on every PR. A gate whose failure path never runs
is indistinguishable from one that cannot fail.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

# PEP 427: <distribution>-<version>(-<build>)?-<python>-<abi>-<platform>.whl,
# and PEP 625 for sdists: <name>-<version>.tar.gz. Both put the version in the
# second '-'-delimited field, with the distribution name normalised first.
_WHEEL_RE = re.compile(r"^(?P<name>[^-]+)-(?P<version>[^-]+)-.*\.whl$")
_SDIST_RE = re.compile(r"^(?P<name>.+)-(?P<version>[^-]+)\.tar\.gz$")


class ReleaseArtifactError(AssertionError):
    """A release artifact contradicts the release it claims to be."""


def version_of(filename: str) -> str:
    """Return the version encoded in a wheel or sdist *filename*.

    Raises ReleaseArtifactError for anything that is neither, so an unexpected
    file in dist/ fails the gate instead of being skipped by it.
    """
    for pattern in (_WHEEL_RE, _SDIST_RE):
        match = pattern.match(filename)
        if match:
            return match.group("version")
    raise ReleaseArtifactError(
        f"{filename!r} is neither a wheel nor an sdist; refusing to guess its "
        "version. Remove it from dist/ or teach this gate about it."
    )


def assert_dist_matches_tag(dist_dir: Path | str, tag: str) -> list[str]:
    """Every artifact in *dist_dir* must carry the version named by *tag*.

    *tag* may be given with or without a leading ``v``. Returns the filenames
    checked, so a caller can log what it actually verified rather than assuming
    the directory was non-empty.
    """
    expected = tag[1:] if tag.startswith("v") else tag
    dist_dir = Path(dist_dir)

    files = sorted(p.name for p in dist_dir.glob("*") if p.is_file())
    if not files:
        raise ReleaseArtifactError(
            f"{dist_dir} contains no artifacts. A release that builds nothing "
            "must not reach the upload step."
        )

    mismatched = {f: version_of(f) for f in files}
    mismatched = {f: v for f, v in mismatched.items() if v != expected}
    if mismatched:
        detail = ", ".join(f"{f} declares {v}" for f, v in mismatched.items())
        raise ReleaseArtifactError(
            f"tag {tag} expects version {expected}, but {detail}. The tag most "
            "likely points at a commit that predates the version bump — check "
            "which branch the release PR merged into before re-tagging."
        )
    return files


def assert_wheel_contains(wheel: Path | str, required: list[str]) -> list[str]:
    """*wheel* must contain every path in *required*.

    Membership is checked against the wheel's own manifest, not against a build
    directory, because the packaging config is exactly what is under test here.
    """
    wheel = Path(wheel)
    with zipfile.ZipFile(wheel) as zf:
        members = set(zf.namelist())

    missing = [path for path in required if path not in members]
    if missing:
        raise ReleaseArtifactError(
            f"{wheel.name} is missing {len(missing)} required asset(s): "
            f"{', '.join(sorted(missing))}. The wheel resolves and imports, so "
            "no version check would catch this — the assets are absent from the "
            "artifact itself, which means consumers get a package that installs "
            "and then renders nothing."
        )
    return sorted(members)


# The bundles a consuming project loads with a <script> tag. Absent from the
# wheel they fail silently in a browser, so they are named here rather than
# discovered: a glob would happily match zero files and call that success.
REQUIRED_WHEEL_ASSETS = [
    f"scitex_ui/static/scitex_ui/js/app/{name}.js"
    for name in (
        "attachment",
        "combobox",
        "confirm-modal",
        "context-menu",
        "dropdown",
        "empty",
        "file-tabs",
        "receipt",
        "reply-quote",
        "tooltip",
    )
]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <tag> <dist-dir>", file=sys.stderr)
        return 2

    _, tag, dist_dir = argv
    try:
        checked = assert_dist_matches_tag(dist_dir, tag)
        print(f"version gate OK: {len(checked)} artifact(s) declare {tag}")

        wheels = sorted(Path(dist_dir).glob("*.whl"))
        if not wheels:
            raise ReleaseArtifactError(
                f"{dist_dir} has no wheel. An sdist-only release cannot carry "
                "the static assets consumers load, so this is not publishable."
            )
        for wheel in wheels:
            assert_wheel_contains(wheel, REQUIRED_WHEEL_ASSETS)
            print(
                f"asset gate OK: {wheel.name} carries all "
                f"{len(REQUIRED_WHEEL_ASSETS)} required bundles"
            )
    except ReleaseArtifactError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
