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
    CSS_REFERENCE_FLOOR,
    PypiFiles,
    VerifyEnvironmentError,
    VerifyError,
    _declared_static_assets_from_zip,
    _http_get,
    assert_file_hash,
    assert_shipped_css_references_resolve,
    assert_version_metadata,
    download,
    fetch_version_payload,
    sha256_of,
)


def _css_tree(tmp_path: Path, *, references: int, missing: int = 0) -> Path:
    """A wheel-shaped css/ tree with `references` resolving, `missing` dangling.

    Each reference points at a sibling file that IS written, so the only
    dangling ones are the deliberate `missing` count.
    """
    css_dir = tmp_path / "scitex_ui" / "static" / "scitex_ui" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    body: list[str] = []
    for i in range(references):
        body.append(f".c{i} {{ background: url('img/a{i}.png'); }}")
        (css_dir / "img").mkdir(exist_ok=True)
        (css_dir / "img" / f"a{i}.png").write_bytes(b"\x89PNG")
    for i in range(missing):
        body.append(f".m{i} {{ background: url('img/gone{i}.png'); }}")
    (css_dir / "bundle.css").write_text("\n".join(body) + "\n")
    return css_dir


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
        # Assert — a yanked release is one the reader must act on.
        with pytest.raises(VerifyError, match="YANKED"):
            assert_version_metadata(payload, "0.0.0")

    def test_an_sdist_only_release_is_rejected(self):
        # Arrange — no wheel: a consumer loading <script> assets gets nothing.
        payload = _mk({"sdist": ("s.tar.gz", "http://x/s.tar.gz", "b")})
        # Act
        # Assert
        with pytest.raises(VerifyError, match="missing"):
            assert_version_metadata(payload, "0.0.0")

    def test_a_version_that_does_not_round_trip_is_rejected(self):
        # Arrange — the endpoint answered a different version than asked.
        payload = PypiFiles(name="scitex-ui", version="9.9.9", yanked=False, files={
            "bdist_wheel": ("w.whl", "u", "a"), "sdist": ("s.tar.gz", "u", "b")})
        # Act
        # Assert
        with pytest.raises(VerifyError, match="round-trip"):
            assert_version_metadata(payload, "0.0.0")


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
        # Assert — the arm that catches PyPI serving different bytes than uploaded.
        with pytest.raises(VerifyError, match="sha256 mismatch"):
            assert_file_hash(p, bad)


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
        # Assert — the arm that catches a packaging exclude dropping the tree.
        with pytest.raises(VerifyError, match="static files"):
            _declared_static_assets_from_zip(p)


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
        # Act
        try:
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
        # Act
        try:
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
        # Act
        try:
        # Assert — a not-yet-published version is UNKNOWN, not "artifact bad".
            with pytest.raises(VerifyEnvironmentError, match="never resolved"):
                fetch_version_payload("0.0.0", max_attempts=3, delay_s=0)
        finally:
            monkey.undo()

    def test_a_network_outage_is_an_environment_result(self):
        # Arrange — transport failure (not a 404) must not be retried as lag.
        import verify_published_release as mod

        def outage(url, timeout):
            raise VerifyEnvironmentError(f"no network to {url}")

        monkey = pytest.MonkeyPatch()
        monkey.setattr(mod, "_http_get", outage)
        # Act
        try:
        # Assert — an outage and a lag are different channels; conflating them
        # is how an outage would read as a broken release.
            with pytest.raises(VerifyEnvironmentError, match="no network"):
                fetch_version_payload("0.0.0", max_attempts=3, delay_s=0)
        finally:
            monkey.undo()


class TestCssReferencesInThePublishedWheel:
    """Arm 6: presence is not resolvability.

    The asset-presence check above passes on a wheel whose stylesheet points at
    a file that is not there — 0.20.1 shipped exactly that (a path quoted inside
    a CSS comment, which a consumer's collectstatic reads as live).

    The scan is applied to the INSTALLED tree, and these are the offline reject
    arms: a clean tree passes, a dangling reference fails, and a tree too small
    to be evidence fails rather than reading as clean.
    """

    def test_a_clean_installed_tree_passes_and_reports_the_count(self, tmp_path):
        # Arrange — a wheel-shaped tree just over the floor, all resolving.
        css_dir = _css_tree(tmp_path, references=CSS_REFERENCE_FLOOR + 5)
        # Act
        references = assert_shipped_css_references_resolve(css_dir)
        # Assert — positive control: the instrument sees a true case.
        assert references >= CSS_REFERENCE_FLOOR

    def test_a_dangling_reference_in_the_installed_wheel_is_rejected(self, tmp_path):
        # Arrange — the floor is satisfied, so only the dangling ref can fail.
        css_dir = _css_tree(tmp_path, references=CSS_REFERENCE_FLOOR, missing=1)
        # Act
        # Assert — a consumer's collectstatic reads that path as live.
        with pytest.raises(VerifyError, match="do not resolve"):
            assert_shipped_css_references_resolve(css_dir)

    def test_a_reference_inside_a_comment_is_still_reported(self, tmp_path):
        # Arrange — the 0.20.1 shape: the ONLY dangling path is inside a
        # comment, where a human would call it prose and a browser does not.
        css_dir = _css_tree(tmp_path, references=CSS_REFERENCE_FLOOR)
        bundle = css_dir / "bundle.css"
        bundle.write_text(
            bundle.read_text() + ".x { /* was: url('img/gone.png') */ }\n"
        )
        # Act
        # Assert — the scan is comment-INCLUSIVE on purpose.
        with pytest.raises(VerifyError, match="do not resolve"):
            assert_shipped_css_references_resolve(css_dir)

    def test_a_tree_below_the_reference_floor_is_rejected(self, tmp_path):
        # Arrange — a tree that resolves perfectly but is too small to prove it.
        css_dir = _css_tree(tmp_path, references=CSS_REFERENCE_FLOOR - 1)
        # Act
        # Assert — a clean-looking result from a drifted walk is not evidence.
        with pytest.raises(VerifyError, match="floor"):
            assert_shipped_css_references_resolve(css_dir)

    def test_a_tree_with_no_stylesheets_at_all_is_rejected(self, tmp_path):
        # Arrange — the extreme of the case above: nothing to scan.
        empty = tmp_path / "scitex_ui" / "static" / "scitex_ui" / "css"
        empty.mkdir(parents=True)
        # Act
        # Assert — "no findings" must never be produced by scanning nothing.
        with pytest.raises(VerifyError, match="no stylesheets"):
            assert_shipped_css_references_resolve(empty)

    def test_an_absent_scan_module_is_an_environment_result(self, tmp_path):
        # Arrange — the record reuses the checkout's scan; if that file moves,
        # the record cannot run. That is an environment gap, not a bad release.
        import verify_published_release as mod

        monkey = pytest.MonkeyPatch()
        monkey.setattr(mod, "_CSS_SCAN_MODULE", "no_such_scan_module")
        # Act
        try:
            css_dir = _css_tree(tmp_path, references=CSS_REFERENCE_FLOOR)
        # Assert — the two channels stay distinct.
            with pytest.raises(VerifyEnvironmentError, match="is absent"):
                assert_shipped_css_references_resolve(css_dir)
        finally:
            monkey.undo()

    def test_the_record_shares_the_gates_own_instrument(self):
        # Arrange — one instrument, two trees. A rename on either side must
        # break this test rather than silently giving the record its own scan.
        import verify_published_release as mod

        repo_root = Path(__file__).resolve().parents[2]
        # Act
        gate = repo_root / "tests" / "develop" / f"{mod._CSS_SCAN_MODULE}.py"
        # Assert
        assert gate.is_file(), (
            f"the record imports {mod._CSS_SCAN_MODULE} as its scan; that file "
            "is the pre-upload gate's own, and it moved"
        )
