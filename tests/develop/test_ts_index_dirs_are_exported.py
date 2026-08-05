#!/usr/bin/env python3
"""Guards that every TypeScript directory declaring itself a module is importable.

A directory containing `index.ts` is asserting "I am a module boundary; import
me by my directory name". Node disagrees unless `package.json` says so, because
**subpath PATTERNS do not perform directory-index resolution**. `"./ts/*"` maps
`@scitex/ui/ts/shell/terminal` onto the *directory* `.../ts/shell/terminal`, and
importing a directory is `ERR_UNSUPPORTED_DIR_IMPORT`. Only an explicit entry
naming `index.ts` makes the bare specifier work.

WHY THIS IS A CHECK RATHER THAN A NOTE — it has already been fixed once and
regressed by omission. figrecipe's build broke on exactly this: they imported
`@scitex/ui/ts/shell/terminal`, it did not resolve, and they shipped a
workaround spelling every path as `.../terminal/index.ts`. The response added
bare entries for `./ts`, `./ts/shell` and `./ts/app` — and stopped there, while
34 other directories with an `index.ts` stayed unimportable, including `_base`,
whose bare specifier appears in this package's own documentation:

    src/scitex_ui/_skills/scitex-ui/41_dual-mode-mounting.md
      import { apiUrl, mountPrefix } from "@scitex/ui/ts/_base";

That import could never have worked. Documentation is not reach, and fixing the
three cases someone happened to report is not fixing the class.

HOW THE FAILURE WAS DISTINGUISHED FROM A PASS, since both are exceptions:

    @scitex/ui/ts/_base    ERR_UNSUPPORTED_DIR_IMPORT   never reached a file
    @scitex/ui/ts/shell    ERR_UNKNOWN_FILE_EXTENSION   resolved; node can't
                                                        load .ts, which is the
                                                        bundler's job

A fallback array (`["…/ts/*", "…/ts/*/index.ts"]`) was tried first and does NOT
work: Node returns the first target without checking existence, so it never
falls through. Explicit entries are the only mechanism.

WHAT THIS DOES NOT CHECK, so nobody reads a pass as more than it is: that the
target parses, that a bundler can load it, or that the module does anything.
Only that a directory claiming to be a module boundary can be addressed as one.
"""

from __future__ import annotations

import json
import pathlib

import pytest

import scitex_ui

_PKG_ROOT = pathlib.Path(scitex_ui.__file__).parent.parent.parent
_PACKAGE_JSON = _PKG_ROOT / "package.json"
_TS_ROOT = pathlib.Path(scitex_ui.__file__).parent / "static" / "scitex_ui" / "ts"


def _index_directories() -> list[str]:
    """Every directory under ts/ that ships an index.ts, as a posix subpath."""
    found = []
    for index in _TS_ROOT.rglob("index.ts"):
        rel = index.parent.relative_to(_TS_ROOT).as_posix()
        if rel != ".":  # ts/index.ts is the root barrel, exported as "./ts"
            found.append(rel)
    return sorted(found)


@pytest.fixture
def exports() -> dict:
    """The package's export map, or skip where there is no package.json.

    An installed wheel has no package.json beside the sources, so this guard is
    meaningful only in the source tree. Skipping says that out loud rather than
    passing mutely on an empty check.
    """
    if not _PACKAGE_JSON.is_file():
        pytest.skip(f"no package.json at {_PACKAGE_JSON} (installed layout)")
    return json.loads(_PACKAGE_JSON.read_text())["exports"]


def test_probe_finds_many_index_directories() -> None:
    """Positive control: an empty scan would make every assertion below vacuous."""
    # Arrange
    minimum_expected = 20

    # Act
    found = _index_directories()

    # Assert
    assert len(found) >= minimum_expected, f"expected many, found {len(found)}: {found}"


def test_probe_sees_the_base_directory() -> None:
    """Second control, naming a directory whose bare import is documented."""
    # Arrange
    documented = "_base"

    # Act
    found = _index_directories()

    # Assert
    assert documented in found, f"{documented} ships an index.ts; scan missed it"


def test_every_index_directory_has_a_bare_export(exports: dict) -> None:
    # Arrange
    directories = _index_directories()

    # Act
    missing = [d for d in directories if f"./ts/{d}" not in exports]

    # Assert
    assert not missing, (
        "These directories ship an index.ts but have no bare export entry, so "
        "`import ... from '@scitex/ui/ts/<dir>'` fails with "
        "ERR_UNSUPPORTED_DIR_IMPORT for every consumer:\n  "
        + "\n  ".join(f"./ts/{d}" for d in missing)
        + "\n\nAdd, for each:\n  "
        + "\n  ".join(
            f'"./ts/{d}": "./src/scitex_ui/static/scitex_ui/ts/{d}/index.ts"'
            for d in missing
        )
        + "\n\nThe './ts/*' pattern does NOT cover these — patterns do not do "
        "directory-index resolution, and a fallback array does not either."
    )


def test_declared_export_targets_exist(exports: dict) -> None:
    """A bare entry pointing at a moved or deleted index.ts is worse than none."""
    # Arrange
    candidates = {
        key: target
        for key, target in exports.items()
        if isinstance(target, str)
        and key.startswith("./ts/")
        and target.endswith("index.ts")
    }

    # Act
    dangling = [
        f"{key} -> {target}"
        for key, target in candidates.items()
        if not (_PKG_ROOT / target).is_file()
    ]

    # Assert
    assert not dangling, "export entries whose target file does not exist:\n  " + "\n  ".join(
        dangling
    )
