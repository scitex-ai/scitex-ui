#!/usr/bin/env python3
"""Guards that the post-publish RECORD can actually FAIL.

The record is ``.github/ci/verify_published_release.py``: after publish it
polls the PyPI version endpoint, downloads the wheel+sdist, checks their
sha256, installs the wheel, and asserts the installed package carries its own
declared static assets.

THIS FILE'S JOB IS THE REJECT ARMS. A verifier that only ever passes is the
exact "gate that cannot fail" the release-artifact gates exist to prevent —
and the 2026-07-28 v0.12.1 incident happened because a check's failure path
had never been exercised, so nobody noticed it was comparing the wrong thing.
So each offline-testable arm below has a POSITIVE control (the instrument sees
a true case) and a REJECT arm (it fails on the false case), mirroring
test_release_artifact_gates.py. The network-dependent arm (the poll loop) is
tested by monkeypatching the transport, not by hitting PyPI — these tests run
on every PR and must stay offline and bounded.

WHAT THIS DOES NOT CHECK: the happy path against a live published version.
That is exercised by hand once per release (and was for 0.22.0 on 2026-09-16:
sha256 OK, 529 static files, 63 installed assets). A live assertion here would
make the PR suite network-dependent and intermittently red — the exact flake
the record's own cache-lag note warns against.
"""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github" / "ci"))

from verify_published_release import (  # noqa: E402
    ASSET_COUNT_FLOOR,
    PypiFiles,
    VerifyEnvironmentError,
    VerifyError,
    _declared_static_assets_from_zip,
    _http_get,
    assert_file_hash,
    assert_version_metadata,
    download,
    fetch_version_payload,
    sha256_of,
)


def _mk(files: dict) -> PypiFiles:
    """A PypiFiles from {packagetype: (filename, url, sha256)}."""
    return PypiFiles(name="scitex-ui", version="0.0.0", yanked=False, files=files)


def _wheel_bytes(n_static: int) -> bytes:
    """A minimal wheel zip with n_static static files + a package marker."""
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("scitex_ui/__init__.py", "")
        for i in range(n_static):
            zf.writestr(f"scitex_ui/static/scitex_ui/css/part{i}.css", ".x{}{}{}{}\n".format(i, i, i, i))
    return buf.getvalue()


class TestVersionMetadata:
    def test_a_full_non_yanked_release_passes(self):
        # Arrange — a healthy version listing: both packagetypes, not yanked.
        payload = _mk(
            {
                "bdist_wheel": ("scitex_ui-0.0.0-py3-none-any.whl", "http://x/w.whl", "a"),
                "sdist": ("scitex_ui-0.0.0.tar.gz", "http://x/s.tar.gz", "b"),
            }
        )
        # Act
        raised = None
        try:
            assert_version_metadata(payload, "0.0.0")
        except VerifyError as exc:
            raised = exc
        # Assert — positive control: a true release is not rejected.
        assert raised is None

    def test_a_yanked_version_is_rejected(self):
        # Arrange
        payload = _mk(
            {
                "bdist_wheel": ("w.whl", "http://x/w.whl", "a"),
                "sdist": ("s.tar.gz", "http://x/s.tar.gz", "b"),
            }
        )
        payload = PypiFiles(name="scitex-ui", version="0.0.0", yanked=True, files=payload.files)
        # Act
        with pytest.raises(VerifyError, match="YANKED"):
            assert_version_metadata(payload, "0.0.0")
        # Assert — a yanked release is one the reader must act on.

    def test_an_sdist_only_release_is_rejected(self):
        # Arrange — no wheel: a consumer loading <script> assets gets nothing.
        payload = _mk({"sdist": ("s.tar.gz", "http://x/s.tar.gz", "b")})
        # Act
        with pytest.raises(VerifyError, match="missing"):
            assert_version_metadata(payload, "0.0.0")
        # Assert

    def test_a_version_that_does_not_round_trip_is_rejected(self):
        # Arrange — the endpoint answered a different version than asked.
        payload = PypiFiles(name="scitex-ui", version="9.9.9", yanked=False, files={
            "bdist_wheel": ("w.whl", "u", "a"), "sdist": ("s.tar.gz", "u", "b")})
        # Act
        with pytest.raises(VerifyError, match="round-trip"):
            assert_version_metadata(payload, "0.0.0")
        # Assert


class TestSha256:
    def test_sha256_of_reads_the_bytes(self, tmp_path):
        # Arrange
        data = b"scitex-ui wheel bytes"
        expected = hashlib.sha256(data).hexdigest()
        p = tmp_path / "input.bin"
        p.write_bytes(data)
        # Act
        actual = sha256_of(p)
        # Assert — the hash function is not the subject under test; it is the
        # instrument the mismatch arm relies on, so pin it down separately.
        assert actual == expected

    def test_a_matching_hash_passes(self, tmp_path):
        # Arrange
        p = tmp_path / "artifact.bin"
        p.write_bytes(b"artifact")
        good = hashlib.sha256(b"artifact").hexdigest()
        # Act
        raised = None
        try:
            assert_file_hash(p, good)
        except VerifyError as exc:
            raised = exc
        # Assert — positive control.
        assert raised is None

    def test_a_mismatched_hash_is_rejected(self, tmp_path):
        # Arrange
        p = tmp_path / "artifact.bin"
        p.write_bytes(b"artifact")
        bad = "0" * 64  # not the real digest
        # Act
        with pytest.raises(VerifyError, match="sha256 mismatch"):
            assert_file_hash(p, bad)
        # Assert — the arm that catches PyPI serving different bytes than uploaded.


class TestWheelStaticTree:
    def test_a_wheel_carrying_its_static_tree_passes(self, tmp_path):
        # Arrange — a wheel with well over the asset-count floor.
        p = tmp_path / "wheel_full.whl"
        p.write_bytes(_wheel_bytes(ASSET_COUNT_FLOOR + 10))
        # Act
        static = _declared_static_assets_from_zip(p)
        # Assert — positive control: the scan sees the tree.
        assert len(static) >= ASSET_COUNT_FLOOR

    def test_a_wheel_missing_its_static_tree_is_rejected(self, tmp_path):
        # Arrange — a wheel with too few static files to be a real release.
        p = tmp_path / "wheel_bare.whl"
        p.write_bytes(_wheel_bytes(0))
        # Act
        with pytest.raises(VerifyError, match="static files"):
            _declared_static_assets_from_zip(p)
        # Assert — the arm that catches a packaging exclude dropping the tree.


class TestDownload:
    def test_download_strips_a_query_string_from_the_filename(self, tmp_path):
        # Arrange — PyPI file URLs may carry a ?query; the on-disk name must not.
        dest = tmp_path / "dl"
        dest.mkdir(parents=True, exist_ok=True)
        seen = {}

        def fake_get(url, timeout):
            seen["url"] = url
            return b"file-bytes"

        monkey = pytest.MonkeyPatch()
        monkey.setattr(sys.modules["verify_published_release"], "_http_get", fake_get)
        try:
            # Act
            result = download("http://files.x/scitex_ui-0.0.0.whl?sig=abc#frag", dest, timeout=5)
        finally:
            monkey.undo()
        # Assert — the ?query#fragment bug the card's sibling cards enforce.
        assert result.name == "scitex_ui-0.0.0.whl"


class TestPollLoop:
    def test_a_lagging_version_endpoint_is_retried_then_resolves(self):
        # Arrange — 404 twice, then a good payload (the cache-lag behaviour
        # measured on 0.21.2 and 0.22.0). The instrument must not give up.
        import verify_published_release as mod
        good = {
            "info": {"name": "scitex-ui", "version": "0.0.0", "yanked": False},
            "urls": [
                {"packagetype": "bdist_wheel", "filename": "w.whl", "url": "u", "digests": {"sha256": "a"}},
                {"packagetype": "sdist", "filename": "s.tar.gz", "url": "u", "digests": {"sha256": "b"}},
            ],
        }
        calls = {"n": 0}

        def flaky_get(url, timeout):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise mod._Version404(url)
            return __import__("json").dumps(good).encode()

        monkey = pytest.MonkeyPatch()
        monkey.setattr(mod, "_http_get", flaky_get)
        monkey.setattr(mod.time, "sleep", lambda *_: None)
        try:
            # Act
            payload = fetch_version_payload("0.0.0", max_attempts=5, delay_s=0)
        finally:
            monkey.undo()
        # Assert — it retried past the lag and resolved.
        assert payload.version == "0.0.0" and calls["n"] == 3

    def test_a_persistent_404_is_an_environment_result_not_a_broken_artifact(self):
        # Arrange — the version never resolves within the budget.
        import verify_published_release as mod

        def always_404(url, timeout):
            raise mod._Version404(url)

        monkey = pytest.MonkeyPatch()
        monkey.setattr(mod, "_http_get", always_404)
        monkey.setattr(mod.time, "sleep", lambda *_: None)
        try:
            # Act
            with pytest.raises(VerifyEnvironmentError, match="never resolved"):
                fetch_version_payload("0.0.0", max_attempts=3, delay_s=0)
        finally:
            monkey.undo()
        # Assert — a not-yet-published version is UNKNOWN, not "artifact bad".

    def test_a_network_outage_is_an_environment_result(self):
        # Arrange — transport failure (not a 404) must not be retried as lag.
        import verify_published_release as mod

        def outage(url, timeout):
            raise VerifyEnvironmentError(f"no network to {url}")

        monkey = pytest.MonkeyPatch()
        monkey.setattr(mod, "_http_get", outage)
        try:
            # Act
            with pytest.raises(VerifyEnvironmentError, match="no network"):
                fetch_version_payload("0.0.0", max_attempts=3, delay_s=0)
        finally:
            monkey.undo()
        # Assert — an outage and a lag are different channels; conflating them
        # is how an outage would read as a broken release.
