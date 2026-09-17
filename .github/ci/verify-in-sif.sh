#!/usr/bin/env bash
# Runs INSIDE the reused scitex-ci SIF (apptainer exec — invoked via
# exec-in-sif.sh). Post-publish RECORD: verify the PUBLISHED artifact for the
# version this tag named.
#
# THIS IS A RECORD, NOT A GATE. It runs after the publish step, so it cannot
# prevent a bad publish — it reports one. The pre-upload gate is
# tests/develop/test_packaging.py (a locally built wheel, checked before
# upload, on every PR). This answers the question that gate structurally
# cannot: are the bytes PyPI actually serves installable and self-consistent?
# The consumer (scitex-hub CI, scitex-app's kind-agreement check) installs the
# PUBLISHED wheel, so a release that ships but does not install is a release
# that did not happen — and this is the one check that would have told us.
#
# WHY in the SIF: the self-hosted runner has no Python on the bare node. The
# SIF bakes python 3.11/3.12/3.13 + pip at /opt/venv-<ver>. The verifier needs
# only pip + network + its own module (checked out); it imports scitex_ui from
# the throwaway --target dir it pip-installs the published wheel into, so the
# SIF's base env does NOT need scitex_ui — the check is consumer-true.
#
# The version is passed explicitly (like build-in-sif.sh gets the tag) so a
# workflow_dispatch re-verify (where GITHUB_REF is a branch, not a tag) still
# checks the right version.
#
# Fail-loud (operator directive): a missing interpreter, or a RECORD FAILED
# verdict, is a HARD error (non-zero exit) that names the exact cause. A
# RECORD NOT RUN (environment) is also a hard error — an outage must not read
# as a pass.
set -euo pipefail

V="${1:-3.12}"
VERSION="${2:?version to verify required (e.g. 0.22.1)}"
VENV="/opt/venv-$V"
PY="$VENV/bin/python"
test -x "$PY" || {
    echo "::error::baked python missing in $VENV — rebuild the SIF: scitex-container apptainer build ci-cpu"
    exit 1
}

export LC_ALL=C.UTF-8 LANG=C.UTF-8

# Writable scratch (the runner's TMPDIR=~/.cache/tmp does not resolve inside
# the container; node-local /tmp is writable + ephemeral). Point every cache
# pip might touch here, and unset a VIRTUAL_ENV leaked from the runner profile.
TMPDIR="/tmp/verify-scitex_ui-${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-0}-$V"
export TMPDIR
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
export UV_CACHE_DIR="$TMPDIR/uv-cache"
export XDG_CACHE_HOME="$TMPDIR"
export PIP_CACHE_DIR="$TMPDIR/pip-cache"
unset VIRTUAL_ENV || true
export PATH="$VENV/bin:$PATH"

CI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== RECORD: verify published scitex-ui $VERSION ==="
# The verifier returns 0 (OK), 1 (RECORD FAILED — the artifact is wrong), or
# 3 (RECORD NOT RUN — an environment gap). Both 1 and 3 must fail the job: a
# wrong artifact is the thing to catch, and an outage must not read as a pass.
set +e
"$PY" "$CI_DIR/verify_published_release.py" "$VERSION" "$TMPDIR"
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
    echo "::error::record exited $RC for $VERSION (0=OK, 1=artifact wrong, 3=environment gap; both 1 and 3 are release-blocking)"
    exit "$RC"
fi
echo "=== RECORD: $VERSION verified — the published artifact is installable and carries its declared assets ==="
