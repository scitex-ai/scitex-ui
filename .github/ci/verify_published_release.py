#!/usr/bin/env python3
"""Post-publish RECORD: "does the PUBLISHED artifact contain what the consumer installs?"

THIS IS A RECORD, NOT A GATE (the card's own §2 question, answered): it runs
AFTER the publish step, so it cannot prevent a bad publish — it can only
report one. A bad publish has already happened by the time this runs, and the
reader of the failure is whoever is about to unblock a consumer from a wheel
that is already on PyPI. The pre-upload GATE is a different, stronger artifact
and already exists: ``tests/develop/test_packaging.py`` (a locally built wheel
is checked before upload, on every PR). Do not read this file as a duplicate of
that gate; it answers the question the gate structurally cannot — whether the
bytes PyPI actually serves are installable and self-consistent.

WHY IT EXISTS (card scitex-ui-release-wheel-verification-...-20260905): the
"download the just-published wheel, check sha256, check its contents, import
it in a clean env" dance was hand-written as a throwaway THREE times in one
session (0.21.2, 0.22.0, + a 0.21.2 re-verify after PyPI index lag). §3:
"prefer durable automation to manual steps; never rely on memory."

WHAT IT DOES, given a published version:
  1. Polls the PyPI VERSION endpoint ``/pypi/scitex-ui/<v>/json`` — NOT the
     ``/pypi/scitex-ui/json`` latest endpoint — until the version resolves.
     The latest endpoint lags after publish (hit on 0.21.2 and 0.22.0), so a
     check that polls it would intermittently fail for a reason unrelated to
     the package. This is the consumer's real question: "can I install <v>
     yet?".
  2. Asserts the version metadata is sane (not yanked, and BOTH a wheel and
     an sdist are present — an sdist-only or wheel-only release is a different
     artifact than this one intends).
  3. Downloads the wheel and the sdist and asserts each sha256 matches the
     digest PyPI itself reports. A mismatch means PyPI is serving bytes that
     are not the bytes that were uploaded.
  4. Asserts the wheel carries the full static tree (a count floor, so an
     empty or remnant result cannot read as clean).
  5. Installs the wheel into a throwaway target dir and imports ``scitex_ui``
     from there, then asserts every asset the INSTALLED package's own
     component registry declares is present in the installed static tree. This
     is the consumer-true signal: a package that installs but is missing its
     own declared assets renders nothing for the adopter. The asset set comes
     from the installed registry (self-consistent — the package asserts its
     own manifest is present), so there is no second hardcoded manifest to
     drift.
  6. Scans the INSTALLED stylesheets for references that do not resolve inside
     the wheel, comment-INCLUSIVE (a path quoted inside a CSS comment is still
     read as live by a consumer's collectstatic). It REUSES the pre-upload
     gate's own scan functions rather than re-implementing them: presence is
     not resolvability, and 0.20.1 shipped a stylesheet whose asset was present
     and whose reference still broke every hub build.

Fail-loud (operator directive): every step asserts non-empty output; any
failure is a hard error naming the exact cause, never a silent skip. The two
conditions that need opposite responses are kept in opposite channels, exactly
as test_packaging.py does: an ENVIRONMENT gap (no network, no pip) is a
different code from a WRONG artifact, so an outage never reads as a broken
release.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assert_release_artifacts import (  # noqa: E402
    ReleaseArtifactError,
    assert_wheel_contains,
)

#: The PyPI project name (as published). The version endpoint is keyed by this.
PROJECT = "scitex-ui"
VERSION_ENDPOINT = f"https://pypi.org/pypi/{PROJECT}/{{version}}/json"

#: Floor for the registry-derived asset set. The package declares dozens of
#: components; if this reads <20, the registry lookup drifted and the asset
#: check would prove nothing. (Mirrors test_packaging's `len(declared) > 20`.)
ASSET_COUNT_FLOOR = 20

#: Floor for the comment-INCLUSIVE CSS reference scan (arm 6). The shipped css/
#: tree carries hundreds of `url(...)` / quoted `@import` references; if the
#: walk or the instrument reads fewer than this, "no unresolved reference"
#: would prove nothing. Mirrors ASSET_COUNT_FLOOR's role.
CSS_REFERENCE_FLOOR = 100

#: The repo's own scan, IMPORTED rather than re-implemented: the pre-upload gate
#: scans the CHECKOUT with these functions and this record must scan the WHEEL
#: with the SAME instrument. A second implementation would drift, and the green
#: one would mean less than it appears to.
_CSS_SCAN_MODULE = "test_shipped_css_references_all_resolve"
_CSS_SCAN_NAMES = ("_reference_count", "_unresolved_in")


class VerifyError(ReleaseArtifactError):
    """The published artifact contradicts what was intended to be published."""


class VerifyEnvironmentError(ReleaseArtifactError):
    """The record could not be RUN — no network, no pip. Verdict is UNKNOWN,
    not "the artifact is bad". This channel must stay distinct from VerifyError
    or the reader would treat an outage as a broken release."""


@dataclasses.dataclass(frozen=True)
class PypiFiles:
    """The downloadable files for one version, as PyPI reports them.

    ``files`` maps ``packagetype`` -> (filename, url, sha256). An empty
    ``files`` dict after a parse failure (rather than an absent field) lets the
    guards below report their own assertion instead of raising AttributeError
    — the same discipline as test_packaging.WheelBuild.
    """

    name: str
    version: str
    yanked: bool
    files: dict


def _http_get(url: str, timeout: int) -> bytes:
    """A single GET. Raises VerifyEnvironmentError on any network failure —
    distinct from a wrong-artifact finding, so an outage never reads as a
    broken release. A 404 is re-raised as _404 so the caller can distinguish
    "not published yet" (retry) from "down" (environment)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise _Version404(url) from exc
        raise VerifyEnvironmentError(
            f"{url} returned HTTP {exc.code} (not 404) — an unexpected answer, "
            "treated as a non-finding rather than a broken release."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VerifyEnvironmentError(
            f"could not reach {url} ({exc!r}). This is an ENVIRONMENT gap — "
            "the record did not run, so the verdict is UNKNOWN, not 'the "
            "artifact is broken'. Re-run once network is available."
        ) from exc


class _Version404(Exception):
    """Internal marker: the version endpoint answered 404 (not resolvable yet)."""


def fetch_version_payload(
    version: str,
    *,
    timeout: int = 30,
    max_attempts: int = 8,
    delay_s: float = 15.0,
) -> PypiFiles:
    """Poll the VERSION endpoint until the published version resolves.

    Polls (rather than fetching once) because PyPI's version endpoint lags
    after publish — measured on 0.21.2 and 0.22.0, both of which were slow to
    resolve on the first query. A single fetch would make this record flaky in
    exactly the window after a release, which is the only window it is ever run
    in.
    """
    url = VERSION_ENDPOINT.format(version=version)
    last_error: Exception | None = None
    for _attempt in range(1, max_attempts + 1):
        try:
            raw = _http_get(url, timeout)
            payload = json.loads(raw)
            files = {
                f["packagetype"]: (f["filename"], f["url"], f["digests"]["sha256"])
                for f in payload.get("urls", [])
            }
            return PypiFiles(
                name=payload["info"]["name"],
                version=payload["info"]["version"],
                yanked=bool(payload["info"].get("yanked", False)),
                files=files,
            )
        except VerifyEnvironmentError:
            raise  # a network/shape error is not "not published yet"
        except _Version404 as exc:
            last_error = exc
            time.sleep(delay_s)
            continue
        except (KeyError, json.JSONDecodeError) as exc:
            raise VerifyEnvironmentError(
                f"{url} answered but did not parse as a version payload "
                f"({exc!r}) — treating as a non-finding, not a broken release."
            ) from exc
    raise VerifyEnvironmentError(
        f"the version endpoint {url} never resolved in {max_attempts} attempts "
        f"(last: {last_error!r}). Either the publish has not propagated to "
        "PyPI's index yet, or the version was never uploaded. Do not treat "
        "this as a broken artifact — treat it as 'not queryable yet'."
    )


def assert_version_metadata(payload: PypiFiles, version: str) -> None:
    """The version the record was asked to verify is the version PyPI reports,
    and it is a full release (not yanked, both packagetypes present)."""
    package_version = version.removeprefix("v")
    if payload.version != package_version:
        raise VerifyError(
            f"PyPI reports {payload.version} for the {version} endpoint — the "
            "version did not round-trip."
        )
    if payload.yanked:
        raise VerifyError(
            f"{version} is YANKED on PyPI. A consumer will not install a "
            "yanked version by default; the release is effectively withdrawn."
        )
    missing = [pt for pt in ("bdist_wheel", "sdist") if pt not in payload.files]
    if missing:
        raise VerifyError(
            f"{version} is missing {missing} on PyPI — expected both a wheel "
            "and an sdist. An sdist-only release cannot carry the static "
            "assets a browser loads, and a wheel-only one breaks consumers who "
            "build from source."
        )


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest_dir: Path, *, timeout: int) -> Path:
    """Download a file from PyPI's file host into dest_dir. Returns the path.
    The query string is stripped from the filename (PyPI file URLs may carry
    one), matching the ?query#fragment discipline the card's siblings enforce."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw = _http_get(url, timeout)
    dest = dest_dir / Path(url.split("?")[0]).name
    dest.write_bytes(raw)
    return dest


def assert_file_hash(path: Path, reported_sha256: str) -> None:
    """The downloaded bytes match the digest PyPI itself reports. A mismatch
    means PyPI is serving different bytes than were uploaded."""
    actual = sha256_of(path)
    if actual != reported_sha256:
        raise VerifyError(
            f"{path.name} sha256 mismatch: PyPI reports {reported_sha256} but "
            f"the downloaded bytes hash to {actual}. PyPI is serving different "
            "bytes than were uploaded."
        )


def _declared_static_assets(scitex_ui) -> list[str]:
    """Every wheel path the package's own component registry declares.

    Derived, not hardcoded: a second manifest would go stale exactly as the
    throwaway scripts did. Mirrors test_packaging._declared_assets (same
    registry, same ``scitex_ui/static/<asset>`` wheel-path shape). Passing the
    imported module in (rather than importing at module load) is deliberate —
    this record verifies what a CONSUMER installs, so its expectations come
    from that installed package, not from the checkout we might have edited.
    """
    assets: list[str] = []
    for name in scitex_ui.list_components():
        cls = scitex_ui.get_component(name)
        if getattr(cls, "css_file", None):
            assets.append(f"scitex_ui/static/{cls.css_file}")
        if getattr(cls, "ts_entry", None):
            assets.append(f"scitex_ui/static/{cls.ts_entry}.ts")
    return assets


def _declared_static_assets_from_zip(wheel_path: Path) -> list[str]:
    """Every ``scitex_ui/static/`` path in the wheel's own manifest.

    Used for the pre-install zip check: the wheel must carry the full static
    tree. A count floor guards against an empty or remnant result reading as
    clean. This is a shape check (the tree is present); the authoritative
    registry-asset check happens after install, against the installed package
    (assert_installed_assets), so there is no second hardcoded manifest.
    """
    with zipfile.ZipFile(wheel_path) as zf:
        members = set(zf.namelist())
    static = sorted(m for m in members if "/static/scitex_ui/" in m)
    if len(static) < ASSET_COUNT_FLOOR:
        raise VerifyError(
            f"the published wheel carries only {len(static)} static files "
            f"(< {ASSET_COUNT_FLOOR} floor) — the packaging dropped the static "
            "tree, so no version check would catch it."
        )
    return static


def pip_install_wheel(wheel_path: Path, target_dir: Path, *, python: str) -> None:
    """Install the wheel into an isolated target dir. A ``--no-index`` wheel
    install is pure extraction (no build, no network), so this verifies that
    the PUBLISHED wheel is a valid, installable artifact — the gate's local
    build is not the same bytes a consumer pulls, and this is the step that
    proves they are."""
    result = subprocess.run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--quiet",
            "--no-index",
            f"--target={target_dir}",
            str(wheel_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise VerifyError(
            f"pip could not install the published wheel (exit "
            f"{result.returncode}).\n--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


def assert_installed_assets(target_dir: Path) -> list[str]:
    """After the wheel is pip-installed into target_dir, every asset the
    INSTALLED package's registry declares must actually be present in the
    installed static tree. This is the consumer-true signal: a package that
    installs and imports but is missing its own declared assets renders nothing
    for the adopter.

    The asset set is read from the installed registry (self-consistent), so
    there is no second hardcoded manifest to drift.
    """
    prev = sys.path[:]
    sys.path.insert(0, str(target_dir))
    for mod in list(sys.modules):
        if mod == "scitex_ui" or mod.startswith("scitex_ui."):
            del sys.modules[mod]
    try:
        scitex_ui = importlib.import_module("scitex_ui")
    finally:
        sys.path[:] = prev

    declared = _declared_static_assets(scitex_ui)
    if len(declared) < ASSET_COUNT_FLOOR:
        raise VerifyError(
            f"the installed package declares only {len(declared)} static assets "
            f"(< {ASSET_COUNT_FLOOR} floor) — the registry lookup drifted, so "
            "this asset check would prove nothing."
        )
    missing = sorted(a for a in declared if not (target_dir / a).is_file())
    if missing:
        raise VerifyError(
            f"{missing} are declared by the installed package's component "
            "registry but are NOT present in the installed static tree. The "
            "wheel installs and imports, so no version check would catch this "
            "— the assets are absent from the artifact a consumer installs."
        )
    return declared


def _load_css_scan():
    """The CHECKOUT's comment-INCLUSIVE CSS reference scan, as a library.

    Imported, not re-implemented: the pre-upload gate scans the checkout with
    these functions, and this record must scan the WHEEL with the same
    instrument. Two implementations would drift apart and the green one would
    mean less than it looks like it means.

    Raising VerifyEnvironmentError (not VerifyError) on a missing module is
    deliberate: the record job checks the repo out, so an absent tests/develop
    is an environment gap, never a statement about the artifact.
    """
    repo_root = Path(__file__).resolve().parents[2]
    scan_path = repo_root / "tests" / "develop" / f"{_CSS_SCAN_MODULE}.py"
    if not scan_path.is_file():
        raise VerifyEnvironmentError(
            f"{scan_path} is absent, so the published wheel's CSS references "
            "cannot be scanned. The record job checks out the repo; a missing "
            "file is an environment gap, not a bad artifact."
        )
    sys.path.insert(0, str(scan_path.parent))
    try:
        scan = importlib.import_module(_CSS_SCAN_MODULE)
    except ImportError as exc:
        raise VerifyEnvironmentError(
            f"{_CSS_SCAN_MODULE} is present but not importable ({exc}) — the "
            "record cannot run its CSS arm."
        ) from exc
    missing = [name for name in _CSS_SCAN_NAMES if not hasattr(scan, name)]
    if missing:
        raise VerifyEnvironmentError(
            f"{_CSS_SCAN_MODULE} no longer exposes {missing}. The gate and this "
            "record must share ONE instrument: update this import rather than "
            "re-implementing the scan here, or the two will disagree and nobody "
            "will be told which one is right."
        )
    return scan


def assert_shipped_css_references_resolve(static_dir: Path) -> int:
    """Every reference in the WHEEL's CSS must resolve INSIDE the wheel.

    WHY THIS ARM, separately from the asset-presence check above: presence is
    not resolvability. 0.20.1 shipped a path QUOTED INSIDE A CSS COMMENT, which
    Django reads as live, and it broke collectstatic for every hub build — the
    asset was present and the release still shipped a broken stylesheet. The
    pre-upload gate catches that in the CHECKOUT; this catches it in the bytes
    PyPI serves, which is the only place a build-time difference between the two
    can show up.

    The scan deliberately does NOT strip comments: a reference a stylesheet's
    reader would act on is reported whether or not a human meant it as prose.
    """
    scan = _load_css_scan()

    css_files = sorted(static_dir.rglob("*.css"))
    if not css_files:
        raise VerifyError(
            f"no stylesheets under {static_dir}, so the reference scan would "
            "report a clean wheel by scanning nothing."
        )

    findings: list[str] = []
    references = 0
    for path in css_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        references += scan._reference_count(text)
        for line, url in scan._unresolved_in(text, path.parent):
            findings.append(f"{path.relative_to(static_dir)}:{line}: {url}")

    if references < CSS_REFERENCE_FLOOR:
        raise VerifyError(
            f"the installed CSS carries only {references} references "
            f"(< {CSS_REFERENCE_FLOOR} floor) — the walk or the instrument "
            "drifted, so 'no unresolved reference' would prove nothing."
        )
    if findings:
        raise VerifyError(
            f"{len(findings)} reference(s) in the PUBLISHED wheel's stylesheets "
            "do not resolve inside it (a consumer's collectstatic reads these as "
            "live):\n  " + "\n  ".join(findings[:20])
        )
    return references


def verify_version(version: str, *, scratch: Path, python: str, **poll_kw) -> dict:
    """Orchestrate the full record. Returns a small summary for logging.

    Raises VerifyError (the artifact is wrong) or VerifyEnvironmentError (the
    record could not run) — the reader must not conflate the two.
    """
    payload = fetch_version_payload(version, **poll_kw)
    assert_version_metadata(payload, version)

    downloads = scratch / "downloads"
    checks: dict = {"name": payload.name, "version": version}

    wheel_name, wheel_url, wheel_sha = payload.files["bdist_wheel"]
    sdist_name, sdist_url, sdist_sha = payload.files["sdist"]

    wheel_path = download(wheel_url, downloads, timeout=120)
    sdist_path = download(sdist_url, downloads, timeout=120)
    assert_file_hash(wheel_path, wheel_sha)
    assert_file_hash(sdist_path, sdist_sha)
    checks["wheel_sha256_ok"] = True
    checks["sdist_sha256_ok"] = True
    checks["wheel_name"] = wheel_name
    checks["sdist_name"] = sdist_name

    # Shape check on the published wheel: it carries the full static tree.
    static = _declared_static_assets_from_zip(wheel_path)
    # Reuse the gate's own membership helper against the full static set —
    # a record of the same invariant, run against the PUBLISHED bytes.
    assert_wheel_contains(wheel_path, static)
    checks["wheel_static_files"] = len(static)

    # Consumer-true signal: install + import + assert the installed tree.
    target_dir = scratch / "install"
    pip_install_wheel(wheel_path, target_dir, python=python)
    checks["installed_assets"] = len(assert_installed_assets(target_dir))

    # Arm 6: the installed CSS must be SELF-CONSISTENT — presence is not
    # resolvability, and 0.20.1 shipped a resolvable-looking stylesheet that
    # broke every consumer's collectstatic.
    checks["installed_css_references"] = assert_shipped_css_references_resolve(
        target_dir / "scitex_ui" / "static" / "scitex_ui" / "css"
    )

    return checks


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"usage: {argv[0]} <version> [scratch-dir]", file=sys.stderr)
        return 2
    version = argv[1]
    scratch = Path(argv[2]) if len(argv) >= 3 else Path(f"/tmp/verify-scitex_ui-{version}")
    print(f"=== RECORD: verify published {PROJECT} {version} ===")
    print("This is a RECORD (post-publish), not a gate — it reports, it does not prevent.")
    try:
        checks = verify_version(version, scratch=scratch, python=sys.executable)
    except VerifyError as exc:
        print(f"::error::RECORD FAILED: {exc}", file=sys.stderr)
        return 1
    except VerifyEnvironmentError as exc:
        print(f"::warning::RECORD NOT RUN (environment): {exc}", file=sys.stderr)
        return 3
    for k, v in checks.items():
        print(f"  {k}: {v}")
    print(
        f"OK: {version} on PyPI is a full, non-yanked release; wheel+sdist "
        "sha256 match PyPI's report; the published wheel is installable, "
        "carries every static asset its own registry declares, and every "
        "reference in its stylesheets resolves inside the wheel."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
