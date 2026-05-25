"""Pytest fixtures, rootdir marker, and subprocess-coverage wiring.

An empty conftest.py at tests/ is the canonical SciTeX
convention (audit-project PS208) — it pins the pytest
rootdir and gives downstream fixtures a home.

This file additionally wires subprocess-coverage support so that
any child Python interpreters spawned by tests (e.g. via
``subprocess.run([sys.executable, ...])``, ``jupyter nbconvert --execute``,
or pytest-xdist workers) write their coverage data into the same
``.coverage*`` shards that pytest-cov collects at session end.

``os.environ.setdefault`` would be a no-op here because pytest-cov has
already set ``COVERAGE_FILE`` to a tmp dir by the time conftest is
loaded — we force-set instead.
"""
from __future__ import annotations

import os
import sysconfig
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pin coverage's data file at the repo root and point process_startup
# at our pyproject so child interpreters configure themselves correctly.
os.environ["COVERAGE_PROCESS_START"] = str(_PROJECT_ROOT / "pyproject.toml")
os.environ["COVERAGE_FILE"] = str(_PROJECT_ROOT / ".coverage")


def _ensure_subprocess_coverage_shim() -> None:
    """Drop an idempotent ``.pth`` file in site-packages that auto-starts
    coverage in every child Python interpreter via
    ``coverage.process_startup()``.
    """
    purelib = Path(sysconfig.get_paths()["purelib"])
    pth = purelib / "_scitex_ui_subprocess_coverage.pth"
    shim = (
        "import os, coverage\n"
        "if os.environ.get('COVERAGE_PROCESS_START'):\n"
        "    coverage.process_startup()\n"
    )
    try:
        if not pth.exists() or pth.read_text() != shim:
            pth.write_text(shim)
    except OSError:
        # site-packages may be read-only (e.g. system Python); silently
        # skip — local dev venvs are writable and that's where this matters.
        pass


_ensure_subprocess_coverage_shim()
