#!/usr/bin/env python3
"""Guards against silently unpackaged static assets.

This package has shipped broken wheels three times for one reason: a file
under ``static/`` matched a blanket rule in the shared gitignore, so git never
tracked it, so hatchling never packaged it — and nothing failed. The wheel was
simply missing a file, while editable installs still saw it.

* 0.6.1/0.6.2 — ``**/*old*`` (a substring rule) matched ``_BinaryPlaceholder.ts``.
* 0.7.0 — ``**/*.svg`` (meant for generated figures) matched the brand favicon.

The invariant is narrow and checkable without building: **nothing under
``src/scitex_ui/static/`` may be gitignored.** An ignored file there is absent
from every published artifact, whatever the rule's intent was.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC = _REPO_ROOT / "src" / "scitex_ui" / "static"


def _gitignored(paths):
    """Return the subset of ``paths`` git would ignore.

    ``git check-ignore`` exits 1 when nothing matches, which is success here,
    so the return code is not an error condition.
    """
    result = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "check-ignore", "--stdin"],
        input="\n".join(str(p) for p in paths),
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_no_static_asset_is_gitignored():
    files = [p for p in _STATIC.rglob("*") if p.is_file()]
    assert files, f"no static files found under {_STATIC} — wrong repo root?"

    assert _gitignored(files) == []
