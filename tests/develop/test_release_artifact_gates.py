#!/usr/bin/env python3
"""The release gates must FAIL on the inputs they exist to reject.

The gates in .github/ci/assert_release_artifacts.py only run during a tag
release, which is the one moment nobody wants to be discovering that a guard
was vacuous. These tests execute both arms on every PR: the accept arm proves
the gate does not block a good release, and the reject arm proves it can fail
at all.

The reject arms are built from the ACTUAL 2026-07-28 incident (a v0.12.1 tag
producing a 0.11.1 wheel), not from an invented shape.
"""

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github" / "ci"))

from assert_release_artifacts import (  # noqa: E402
    ReleaseArtifactError,
    assert_dist_matches_tag,
    assert_wheel_contains,
    version_of,
)


def _make_wheel(path: Path, members: dict[str, str]) -> Path:
    # Arrange helper: a real zip, so membership is read from a manifest rather
    # than from a mock that would agree with whatever the gate asked it.
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return path


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("scitex_ui-0.12.1-py3-none-any.whl", "0.12.1"),
        ("scitex_ui-0.11.1-py3-none-any.whl", "0.11.1"),
        ("scitex_ui-0.12.1.tar.gz", "0.12.1"),
    ],
)
def test_version_of_reads_version_from_artifact_filename(filename, expected):
    # Arrange / Act
    actual = version_of(filename)

    # Assert
    assert actual == expected


def test_version_of_rejects_a_file_that_is_neither_wheel_nor_sdist():
    # Arrange
    stray = "release-notes.md"

    # Act / Assert — skipping unknown files would let a stray artifact ride
    # along unverified, so the gate must refuse rather than ignore.
    with pytest.raises(ReleaseArtifactError, match="neither a wheel nor an sdist"):
        version_of(stray)


def test_dist_matching_the_tag_passes(tmp_path):
    # Arrange
    (tmp_path / "scitex_ui-0.12.1-py3-none-any.whl").write_bytes(b"")
    (tmp_path / "scitex_ui-0.12.1.tar.gz").write_bytes(b"")

    # Act
    checked = assert_dist_matches_tag(tmp_path, "v0.12.1")

    # Assert
    assert len(checked) == 2


def test_dist_built_from_a_pre_bump_commit_fails_the_tag_check(tmp_path):
    # Arrange — the exact 2026-07-28 incident: tag v0.12.1, wheel 0.11.1.
    (tmp_path / "scitex_ui-0.11.1-py3-none-any.whl").write_bytes(b"")

    # Act / Assert
    with pytest.raises(ReleaseArtifactError, match="declares 0.11.1"):
        assert_dist_matches_tag(tmp_path, "v0.12.1")


def test_empty_dist_fails_rather_than_passing_vacuously(tmp_path):
    # Arrange — an empty directory satisfies "no mismatches" trivially, which
    # is how a build-produced-nothing failure reaches the upload step.

    # Act / Assert
    with pytest.raises(ReleaseArtifactError, match="no artifacts"):
        assert_dist_matches_tag(tmp_path, "v0.12.1")


def test_tag_without_leading_v_is_accepted(tmp_path):
    # Arrange — workflow_dispatch callers pass the bare version.
    (tmp_path / "scitex_ui-0.12.1-py3-none-any.whl").write_bytes(b"")

    # Act
    checked = assert_dist_matches_tag(tmp_path, "0.12.1")

    # Assert
    assert checked == ["scitex_ui-0.12.1-py3-none-any.whl"]


def test_wheel_carrying_its_assets_passes(tmp_path):
    # Arrange
    wheel = _make_wheel(
        tmp_path / "scitex_ui-0.12.1-py3-none-any.whl",
        {
            "scitex_ui/__init__.py": "",
            "scitex_ui/static/scitex_ui/js/app/context-menu.js": "export{}",
        },
    )

    # Act
    members = assert_wheel_contains(
        wheel, ["scitex_ui/static/scitex_ui/js/app/context-menu.js"]
    )

    # Assert
    assert "scitex_ui/static/scitex_ui/js/app/context-menu.js" in members


def test_importable_wheel_missing_its_static_assets_still_fails(tmp_path):
    # Arrange — the wheel imports fine; only the browser-facing assets are
    # gone. This is the failure a version check cannot see.
    wheel = _make_wheel(
        tmp_path / "scitex_ui-0.12.1-py3-none-any.whl",
        {"scitex_ui/__init__.py": ""},
    )

    # Act / Assert
    with pytest.raises(ReleaseArtifactError, match="missing 1 required asset"):
        assert_wheel_contains(
            wheel, ["scitex_ui/static/scitex_ui/js/app/context-menu.js"]
        )
