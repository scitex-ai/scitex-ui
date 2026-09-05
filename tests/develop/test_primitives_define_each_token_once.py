#!/usr/bin/env python3
"""No design token may be defined by two different primitives files.

THE BUG THIS EXISTS FOR, found 2026-08-18 while building a divergence inventory
of scitex-hub's forked copy of this layer — i.e. found by auditing someone
else's package and being contradicted by the result.

The inventory reported that scitex-ui "gained" 8 typography tokens over hub,
which reads like an improvement. It was the opposite: hub defined them ONCE, and
scitex-ui defined the same 8 names with the same values in TWO files —
``primitives/typography.css`` and ``primitives/typography-vars.css``.

WHY IDENTICAL DUPLICATES ARE STILL A BUG. Nothing was rendering wrong, because
the two copies agreed. Two definitions that agree are indistinguishable from one
definition — until somebody edits one. Then the winner is decided by bundle
source order, and the loser's edit silently does nothing. The person who made
the edit sees no error, no warning, and no effect, and has no reason to suspect a
second definition exists.

Measured at the time: shell.css imported typography-vars.css at line 57 and
typography.css at line 58; all.css at 41 and 42. So typography.css won, and an
edit to the file NAMED for the tokens would have been the silent no-op. (A note
on the same card had this backwards — it predicted typography.css would sort
first alphabetically and therefore lose. ``-`` (0x2D) sorts before ``.`` (0x2E),
so ``typography-vars.css`` comes first and typography.css, arriving later, wins.
The prediction was wrong in the direction that would have made the bug look
harmless.)

SSoT (constitution §1): one authoritative place for each fact. A token's
authoritative place is the primitives file named for its family.

SCOPE: primitives only. A THEME file legitimately redefines a primitive token —
that is what theming is — so this guard would be wrong to forbid it. It asks
only that the base layer not disagree with itself, which is why it can assert
zero rather than needing an allowlist.
"""

from __future__ import annotations

import pathlib
import re
from collections import defaultdict

import pytest

# Resolve the CHECKOUT, not the installed package. Deriving this from
# ``scitex_ui.__file__`` reads site-packages when the install is not editable,
# so the guard would silently check a different tree than the one under review.
# Measured 2026-08-18 on a sibling guard: it went red for the right reason in
# the wrong tree, which is indistinguishable from working.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PRIMITIVES = (
    _REPO_ROOT / "src" / "scitex_ui" / "static" / "scitex_ui" / "css" / "primitives"
)

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_DECLARATION = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")


def _definitions_by_token() -> dict[str, set[str]]:
    """Token -> the set of primitives filenames that DEFINE it."""
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted(_PRIMITIVES.glob("*.css")):
        text = _CSS_COMMENT.sub("", path.read_text(errors="replace"))
        for token in _DECLARATION.findall(text):
            found[token].add(path.name)
    return found


def test_primitives_scan_finds_tokens() -> None:
    """ANTI-VACUITY: a zero population must FAIL rather than pass.

    Without this, a bad path or a broken regex produces an empty mapping, the
    duplicate check finds no duplicates, and the suite reports the codebase
    clean. A parser that did not run and a codebase with no defects return the
    same green, and only this assertion tells them apart.
    """
    # Arrange: the shipped primitives directory is the fixture.
    # Act
    definitions = _definitions_by_token()
    # Assert
    assert definitions, (
        f"no custom properties found under {_PRIMITIVES} — the scan did not "
        "run, so a passing duplicate check below would prove nothing"
    )


def test_no_token_is_defined_in_two_primitives_files() -> None:
    """A token defined twice is decided by bundle order, not by intent."""
    # Arrange
    definitions = _definitions_by_token()
    # Act
    duplicated = {
        token: files for token, files in definitions.items() if len(files) > 1
    }
    # Assert
    if duplicated:
        lines = [
            "These design tokens are defined in more than one primitives file.",
            "Whichever file the bundle imports LAST wins, so an edit to the "
            "other one silently does nothing:",
            "",
        ]
        for token in sorted(duplicated):
            lines.append(f"  {token}   defined in: "
                         f"{', '.join(sorted(duplicated[token]))}")
        lines += [
            "",
            "Keep the definition in the primitives file named for that token "
            "family and delete the other. Theme files may still override a "
            "primitive — this guard only covers the primitives layer, because "
            "the base layer must not disagree with itself.",
        ]
        pytest.fail("\n".join(lines))
