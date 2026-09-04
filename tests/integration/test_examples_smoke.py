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

    Importing the package alone isn't enough — the session lifecycle pulls in
    `scitex_repro.RandomStateManager`, which probes optional ML libs
    (tensorflow / jax). In environments where those libs are partially
    installed but broken (protobuf version skew, jax circular imports),
    every `@stx.session` example would fail for reasons unrelated to
    scitex-ui. Skip in that case so the smoke test doesn't mask its
    own real signal.

    THIS PROBE USED TO IMPORT THE UMBRELLA, AND THAT MADE IT USELESS — measured
    2026-09-04. It ran `import scitex as stx`, so in a normal agent container
    (where the umbrella is deliberately absent) it returned False, and the
    caller then reported "the session framework is unavailable here".

    The session framework was NOT unavailable. `scitex_session` was installed
    and working the whole time; only the umbrella was missing. Meanwhile
    `01_list_components.py` and `02_workspace_components.py` were themselves
    failing because THEY imported the umbrella — a scitex-ui defect. So this
    probe shared the exact defect it was supposed to control for, agreed with
    it, and certified our bug as somebody else's environment problem. A control
    that fails the same way as its subject confirms nothing.

    It now probes what the examples actually use.
    """
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import scitex_session as stx\n"
                "@stx.session\n"
                "def main(CONFIG=stx.INJECTED, logger=stx.INJECTED):\n"
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


#: Failure text that means "this environment cannot host the scitex session
#: framework", not "this example is broken". Kept NARROW and named: anything
#: outside this set is a real failure and is reported as one.
#:
#: The one legitimate cause left: the session framework is present but its ML
#: stack is broken (protobuf skew, jax circular imports), which is the case the
#: original author guarded for.
#:
#: `"No module named 'scitex'"` WAS IN THIS SET AND HAD TO COME OUT — measured
#: 2026-09-04. It was listed on the reasoning that the umbrella is deliberately
#: absent from a normal agent container, which is true, and that its absence is
#: therefore unrelated to scitex-ui, which is NOT. An example that cannot run
#: without the umbrella is an example with the wrong dependency, and that is our
#: defect to fix, not the environment's to supply. Keeping the string here made
#: exactly that defect unreportable: `01_list_components.py` and
#: `02_workspace_components.py` imported the umbrella, failed, matched this
#: entry, and were skipped — for as long as it took someone to run them by hand.
#:
#: An example that genuinely wants the umbrella guards the import (see
#: `03_self_explanatory_demo.py`) and does not fail this way at all.
_UNRELATED_ENV_FAILURE = (
    "scitex_repro",
    "tensorflow",
    "jax",
    "protobuf",
)


def _run_example_or_skip(ex, tmp_path):
    """Run one example; skip iff its failure is a confirmed environment gap.

    Lives outside the test so the test body holds ONE assertion and no
    top-level branch. The branch is a decision about whether this environment
    can host the example at all, which is a different question from whether
    the example works — folding both into the test function put two intents in
    one function's clothes (STX-TQ006/TQ007) and made the failure message
    ambiguous about which one had fired.
    """
    r = subprocess.run(
        [sys.executable, str(ex)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if r.returncode == 0:
        return r
    if not any(k in r.stderr for k in _UNRELATED_ENV_FAILURE):
        return r
    if _scitex_session_works():
        return r
    pytest.skip(
        f"{ex.name} needs the scitex session framework, which is independently "
        f"confirmed unavailable here — not a scitex-ui defect. Run with `-rs` "
        f"to see this; it is a REAL GAP in coverage for this example, NOT a "
        f"pass.\nstderr tail:\n{r.stderr[-500:]}"
    )


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda p: p.name)
def test_example_script_runs_to_completion(ex, tmp_path):
    """Run an examples/*.py script to completion in `tmp_path`.

    THE SKIP USED TO BE A BLANKET ONE AND IT BLINDED THIS TEST COMPLETELY.
    Previously: `@pytest.mark.skipif(not _scitex_session_works(), ...)`, applied
    to EVERY example. `_scitex_session_works()` is False whenever `import
    scitex` fails — and the umbrella is absent in a normal agent container.

    So on 2026-08-23 example 03 died on its own import line with
    `ModuleNotFoundError: No module named 'scitex'` and NOTHING REPORTED IT:
    the absence that broke the example is the same absence that switched off
    the test. A gate disabled by exactly the condition it exists to detect is
    the strongest form of §2's "a gate that cannot fail" — it is not merely
    always-green, it is always-green PRECISELY WHEN IT MATTERS.

    It also over-reached: three of the four examples do not use the session at
    all, and they were skipped too.

    THE ORIGINAL INTENT WAS SOUND and is preserved. Environments with a
    partially-installed ML stack (protobuf skew, jax circular imports) make
    `@stx.session` examples fail for reasons that have nothing to do with
    scitex-ui, and reporting those as scitex-ui failures would bury the real
    signal. So the polarity is inverted rather than the guard removed:

        before   skip everything if the umbrella is unavailable
        after    RUN everything; skip an individual example only when it
                 actually failed AND the failure names the known-broken
                 machinery AND that machinery is independently confirmed broken

    A failure that does not match stays a failure.
    """
    # Arrange
    # Act
    r = _run_example_or_skip(ex, tmp_path)
    # Assert
    assert r.returncode == 0, f"{ex.name} failed: {r.stderr[-2000:]}"


def test_at_least_one_example_runs_without_the_session_framework():
    """ANTI-VACUITY: if EVERY example needs the umbrella, this file proves nothing.

    The per-example skip above is honest, but it degrades gracefully into
    measuring nothing: an environment without the umbrella would skip all four
    and the suite would report green having executed no example at all. That is
    the state this file was in before 2026-08-23, and it is how example 03 came
    to be broken and unnoticed.

    So at least one example must be runnable with scitex-ui ALONE. That is also
    the property the package claims — «Stand Alone でもきれいに動く» — and an
    example that cannot demonstrate it is not demonstrating the package.
    """
    # Arrange
    standalone = [
        ex for ex in EXAMPLES
        if "import scitex as stx" not in ex.read_text(encoding="utf-8", errors="replace")
        or "except ModuleNotFoundError" in ex.read_text(encoding="utf-8", errors="replace")
    ]
    # Act
    count = len(standalone)
    # Assert
    assert count >= 1, (
        "every example requires the scitex umbrella, so in any environment "
        "without it this smoke test skips everything and asserts nothing. "
        "At least one example must run on scitex-ui alone."
    )


# EOF
