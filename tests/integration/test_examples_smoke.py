#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/integration/test_examples_smoke.py

"""End-to-end smoke: every example script must run to completion.

Skipped when the umbrella `scitex` package isn't importable (CI installs
only `scitex-ui[dev]`, which doesn't pull `scitex` — the converted
`@stx.session` examples need it). The per-example syntax/import smoke
lives in `tests/examples/test_*.py` and runs unconditionally.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted(Path(__file__).resolve().parents[2].joinpath("examples").glob("*.py"))


def _scitex_session_works() -> bool:
    """Return True iff a no-op `@stx.session` runs end-to-end.

    `import scitex` alone isn't enough — the session lifecycle pulls in
    `scitex_repro.RandomStateManager`, which probes optional ML libs
    (tensorflow / jax). In environments where those libs are partially
    installed but broken (protobuf version skew, jax circular imports),
    every `@stx.session` example would fail for reasons unrelated to
    scitex-ui. Skip in that case so the smoke test doesn't mask its
    own real signal.
    """
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import scitex as stx\n"
                "@stx.session\n"
                "def main(CONFIG=stx.session.INJECTED, "
                "logger=stx.session.INJECTED):\n"
                "    return 0\n"
                "main()\n"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return r.returncode == 0


def test_examples_directory_is_non_empty():
    """The repository must ship at least one example script."""
    # Arrange
    # Act
    found = EXAMPLES
    # Assert
    assert found, "no example scripts found"


@pytest.mark.skipif(
    not _scitex_session_works(),
    reason="scitex.session machinery not functional in this environment",
)
@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda p: p.name)
def test_example_script_runs_to_completion(ex, tmp_path):
    """Run an examples/*.py script to completion in `tmp_path`."""
    # Arrange
    # Act
    r = subprocess.run(
        [sys.executable, str(ex)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
    )
    # Assert
    assert r.returncode == 0, f"{ex.name} failed: {r.stderr[-2000:]}"


# EOF
