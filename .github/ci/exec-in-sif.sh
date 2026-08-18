#!/usr/bin/env bash
# Outer apptainer-exec wrapper for scitex-ui's self-hosted CI.
#
# Runs ON THE RUNNER (outside the SIF). Resolves the apptainer binary + SIF
# image, then `apptainer exec`s the SIF and hands off to an INNER script (run
# inside the container). Keeps every workflow job's YAML down to one line —
# `bash .github/ci/exec-in-sif.sh <inner-script> [args...]` — and concentrates
# all the SIF plumbing (binary resolution, ~-expansion, scratch, binds) in one
# version-controlled place.
#
# HOST-INDEPENDENT BY CONSTRUCTION. This script used to assume Spartan in four
# places — a required apptainer path under ~/.env-3.11, a PATH prepend to that
# directory, an APPTAINER_TMPDIR under /data/gpfs/projects/punim0264, and an
# unconditional --bind of that same tree. On a runner without them it failed at
# the mkdir, before the apptainer path was even consulted. Each is now used
# WHEN PRESENT and skipped when absent, so the same script works on Spartan and
# on a plain Linux runner. Measured 2026-08-05: scitex-compute-01/02 carry
# apptainer at /usr/bin/apptainer and have no /data/gpfs and no ~/.env-3.11.
#
# Optional env (repo Actions Variables — overrides, not requirements):
#   SCITEX_CI_APPTAINER   path to a specific apptainer binary
#                         (Spartan: ~/.env-3.11/bin/apptainer)
#   SCITEX_CI_SIF         path to the CI SIF image
#                         (default: ~/.scitex/dev/containers/ci-cpu.sif)
#
# Usage:
#   bash .github/ci/exec-in-sif.sh run-in-sif.sh 3.12
#
# Fail-loud (operator directive): a missing apptainer or SIF is a HARD error —
# never a silent fallback to a bare-runner install. What changed is WHERE we
# look, not whether we fail when it is absent.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift || true

# ~-expand the Actions-Variable paths: a quoted "~/…" is NOT tilde-expanded by
# the shell, so substitute a leading ~ with $HOME ourselves.
expand_tilde() { printf '%s' "${1/#\~/$HOME}"; }

# The runner's job shell is --noprofile --norc (no Lmod), so a shim directory
# has to be put on PATH explicitly — but only if it actually exists here.
[ -d "$HOME/.env-3.11/bin" ] && export PATH="$HOME/.env-3.11/bin:$PATH"

# apptainer: the configured path wins WHEN USABLE, otherwise resolve from PATH.
# A configured-but-missing path is reported rather than silently ignored — it
# means the variable describes a different machine, which is worth knowing.
APPTAINER=""
if [ -n "${SCITEX_CI_APPTAINER:-}" ]; then
    CONFIGURED="$(expand_tilde "$SCITEX_CI_APPTAINER")"
    if [ -x "$CONFIGURED" ]; then
        APPTAINER="$CONFIGURED"
    else
        echo "::warning::SCITEX_CI_APPTAINER=$CONFIGURED is not executable on $(hostname -s); falling back to PATH"
    fi
fi
APPTAINER_FROM="SCITEX_CI_APPTAINER"
if [ -z "$APPTAINER" ]; then
    APPTAINER="$(command -v apptainer || true)"
    APPTAINER_FROM="PATH"
fi
# Name BOTH attempts in the failure: "which one did you even try" is the whole
# diagnosis when a job lands on an unfamiliar runner.
[ -n "$APPTAINER" ] && [ -x "$APPTAINER" ] || {
    echo "::error::no apptainer on this runner. Tried (1) SCITEX_CI_APPTAINER=${SCITEX_CI_APPTAINER:-<unset>} — not an executable here; (2) 'apptainer' on PATH ($PATH) — not found. Install apptainer on this runner, or point SCITEX_CI_APPTAINER at a working shim. Running the job outside the SIF on a bare-runner install is NOT an acceptable fallback."
    exit 1
}

SIF="$(expand_tilde "${SCITEX_CI_SIF:-$HOME/.scitex/dev/containers/ci-cpu.sif}")"
[ -f "$SIF" ] || {
    echo "::error::CI SIF missing at $SIF — rebuild it: scitex-container apptainer build ci-cpu"
    exit 1
}

# apptainer scratch. Prefer the shared project FS where it exists (keeps HOME
# clean on Spartan, whose HOME is inode-capped); otherwise host-local scratch
# under $HOME. NOT ${TMPDIR:-/tmp}: the runner profile rewrites TMPDIR per job
# and /tmp is wiped between them, so a shared, stable, fleet-wide location makes
# a scratch-related failure reproducible instead of one-shot. Same path the rest
# of the fleet uses (scitex-dev and siblings), so a finding on one node transfers.
GPFS_ROOT="/data/gpfs/projects/punim0264"
if [ -d "$GPFS_ROOT" ]; then
    export APPTAINER_TMPDIR="$GPFS_ROOT/ywatanabe/ci/apptainer-tmp"
else
    export APPTAINER_TMPDIR="$HOME/.cache/scitex-ci/apptainer-tmp"
fi
mkdir -p "$APPTAINER_TMPDIR"

# --bind the project tree only where it exists: on Spartan $HOME/.scitex is a
# symlink into punim0264 and the bind is what makes it resolve inside the
# container. Binding a nonexistent source is a hard apptainer error, so this
# must stay conditional. Building the WHOLE argv as one array (rather than
# splicing a possibly-empty BIND_ARGS into a fixed command) means the bind is
# genuinely absent when it does not apply — and the echoed plan below is then
# the exact argv, not an approximation of it. --pwd "$PWD" keeps the checkout
# as cwd.
APPTAINER_ARGV=(exec --pwd "$PWD")
if [ -d "$GPFS_ROOT" ]; then
    APPTAINER_ARGV+=(--bind "$GPFS_ROOT")
    GPFS_STATE="present (scratch on GPFS, punim0264 bound)"
else
    GPFS_STATE="absent (scratch under \$HOME, no GPFS bind)"
fi

# Echo the resolved plan. When a run fails on an unfamiliar node the FIRST
# question is which profile it took — that answer must be in the log, not
# reconstructed after the fact.
echo "exec-in-sif: apptainer=$APPTAINER (via $APPTAINER_FROM)"
echo "exec-in-sif: sif=$SIF"
echo "exec-in-sif: $GPFS_ROOT $GPFS_STATE"
echo "exec-in-sif: APPTAINER_TMPDIR=$APPTAINER_TMPDIR"
echo "exec-in-sif: + $APPTAINER ${APPTAINER_ARGV[*]} $SIF bash .github/ci/$INNER $*"

exec "$APPTAINER" "${APPTAINER_ARGV[@]}" "$SIF" bash ".github/ci/$INNER" "$@"
