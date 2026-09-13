#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The stx-app-scope consumer contract (TODO #48 / #144-149, scitex-app
PR #185 @ d8528de4) — the SDK-side invariants, pinned on the source.

The behavioral half (a project marker mounts a selector; a user/absent marker
mounts nothing, across light/dark/mobile) is covered by the two Node
strip-types render tests alongside this file, because scitex-ui has no JS
test runner. What a Python guard CAN and SHOULD pin is the structural
contract that a behavior test would only prove incidentally:

1. CROSS-PACKAGE NAME: the marker the consumer reads is byte-identical to the
   name the scitex-app SDK PRODUCES (`_app_scope.SCOPE_META_NAME`). A rename on
   either side must fail HERE, not surface as a silently-absent selector in a
   leaf three repos away.
2. REUSE, NOT FORK: the host imports the EXISTING ProjectSelector and defines
   no competing selector block. A second, look-alike picker is exactly the
   leaf-local duplication the shared-SDK principle (compass L18) exists to
   stop — and it is the one failure a behavior test would not flag, because a
   fork behaves correctly and still passes.
3. NO GLOBAL HEADER: the host takes a caller-supplied container, so it can
   only ever write where it is told — the "never a global Hub-header switcher"
   ruling is enforced by the shape of the API, and a guard pins that the host
   does not itself touch a header/global element.

Static on source, with positive + negative detector controls per
test_detectors_carry_controls.py (a guard whose extractor stops matching turns
every assertion vacuously true).
"""

from __future__ import annotations

import pathlib
import re

from tests._checkout import static_dir

_TS = static_dir() / "ts"
_SCOPE = _TS / "_base" / "scope.ts"
_HOST = _TS / "shell" / "app-scope-selector.ts"

#: The marker name the scitex-app SDK PRODUCES. Pinned to the producer's own
#: constant value (scitex_app._app_scope.SCOPE_META_NAME, PR #185). The consumer
#: must read exactly this; if the producer renames it, this constant is updated
#: in the same change and the test below stays the seam.
_SDK_SCOPE_META_NAME = "stx-app-scope"

#: The existing selector the host must REUSE (not fork). Named from the merged
#: L625 component; if it is renamed/removed, reuse-by-name below fails.
_REUSED_SELECTOR = "ProjectSelector"


def _scope_source() -> str:
    return _SCOPE.read_text(encoding="utf-8")


def _host_source() -> str:
    return _HOST.read_text(encoding="utf-8")


def _strip(text: str) -> str:
    """Comments stripped — a name PROSE names is not the name the code reads.
    (The comment-vs-construct inversion this repo has recorded three times.)"""
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


# --- 1. cross-package marker name ------------------------------------------


def test_the_scope_reader_reads_the_sdk_marker_name():
    """scope.ts must read the meta named exactly `stx-app-scope` — the name
    the producer injects. It does so via the exported APP_SCOPE_META_NAME
    constant; a drift here is invisible in every unit test (the test would
    write the same wrong name) and only surfaces as a project-scoped app
    rendering no selector."""
    # Arrange
    src = _strip(_scope_source())
    # Act — the reader builds its selector from the constant, and the constant
    # is the seam pinned in the next test.
    reads_via_constant = re.search(
        r"querySelector\(`meta\[name=\"\$\{APP_SCOPE_META_NAME\}\"", src
    ) is not None
    # Assert
    assert reads_via_constant, (
        "scope.ts no longer reads the marker through APP_SCOPE_META_NAME. "
        "If the meta name changed, update APP_SCOPE_META_NAME to match the "
        f"SDK's SCOPE_META_NAME ({_SDK_SCOPE_META_NAME!r}) so the consumer and "
        "producer agree."
    )


def test_the_marker_name_constant_matches_the_sdk():
    """The exported APP_SCOPE_META_NAME is the single seam to the producer.
    Pin its VALUE to the SDK's, so a rename on our side is caught here even
    before a leaf is affected."""
    # Arrange
    src = _strip(_scope_source())
    # Act
    declared = re.search(
        r"export const APP_SCOPE_META_NAME = \"([^\"]+)\"", src
    )
    # Assert
    assert declared and declared.group(1) == _SDK_SCOPE_META_NAME, (
        f"APP_SCOPE_META_NAME is {declared.group(1) if declared else 'MISSING'}, "
        f"but the scitex-app SDK emits {_SDK_SCOPE_META_NAME!r}. They must be "
        "byte-identical."
    )


# --- 2. reuse the existing selector, do not fork it -------------------------


def test_the_host_imports_the_existing_project_selector():
    # Arrange
    src = _strip(_host_source())
    # Act
    imports = re.search(
        r"import\s*\{[^}]*\b" + _REUSED_SELECTOR + r"\b[^}]*\}\s*from", src
    ) is not None
    # Assert
    assert imports, (
        f"app-scope-selector.ts no longer imports {_REUSED_SELECTOR}. The "
        "directive is to REUSE the existing selector, not fork it — a second "
        "picker is the leaf-local duplication compass L18 exists to stop."
    )


def test_the_host_defines_no_competing_selector_block():
    """A fork would announce itself as a new stx-app-* BEM block the host owns.
    The host must not declare a selector block of its own — it mounts the
    reused ProjectSelector (block `stx-app-project-selector`) into the caller's
    container and stops there."""
    # Arrange
    host = _strip(_host_source())
    # Act
    # Any `const CLS = "stx-app-..."` in the host would be it defining its own
    # component vocabulary = a fork.
    own_block = re.search(r"const CLS = \"(stx-app-[^\"]+)\"", host)
    # Assert
    assert own_block is None, (
        f"app-scope-selector.ts declares its own block {own_block.group(1)!r} "
        "— that is a FORK of the selector, not a consumer of it. It should "
        f"import {_REUSED_SELECTOR} and mount that; a host that builds its own "
        "markup duplicates the L625 component."
    )


def test_the_host_forwards_the_caller_container():
    """The no-header-switcher ruling is structural: the host writes only where
    the caller tells it to — it must forward `container` to the selector, so
    mounting into the global header would have to be a caller choice, not a
    host behavior."""
    # Arrange
    host = _strip(_host_source())
    # Act
    forwards_container = re.search(r"container:\s*options\.container", host) is not None
    # Assert
    assert forwards_container, (
        "the host must pass the caller's container to the selector; it may "
        "only write where it is told — that is how 'never a global header "
        "switcher' is guaranteed by shape."
    )


def test_the_host_never_reaches_a_global_header_element():
    # Arrange
    host = _strip(_host_source())
    # Act
    global_reach = re.search(
        r"querySelector\(\s*[\"'][.#](global-header|header|stx-shell-header)[\"'\s]",
        host,
    ) or re.search(r"getElementById\(\s*[\"'][a-z-]*header", host)
    # Assert
    assert global_reach is None, (
        "the host reaches for a global/header element by name — that is the "
        "exact forced-header switcher the 2026-09-10 ruling forbids. Mount "
        "into options.container only."
    )


# --- 3. the gate: absent/user renders nothing (structural half) -------------


def test_absent_marker_maps_to_user_not_to_a_selector():
    """The whole ruling hinges on the DEFAULT being 'no selector'. scope.ts
    must return user (and mayOfferProjectSelector false) when the marker is
    absent — never throw, never default to project. (The behavioral test
    proves the mount outcome; this pins the predicate's default so a future
    edit cannot flip absence into opt-in.)"""
    # Arrange
    src = _strip(_scope_source())
    # Act
    # the absent branch returns SCOPE_USER (not throw, not project)
    absent_returns_user = re.search(
        r"if \(!meta\) return SCOPE_USER;", src
    ) is not None
    # Assert
    assert absent_returns_user, (
        "scope.ts's absent-marker branch no longer returns SCOPE_USER. Absence "
        "is the SDK's user-scoped spelling (it emits no marker), so it must "
        "default to 'no selector' — defaulting to project would force a switcher "
        "onto every user-scoped app."
    )


# --- detector controls -----------------------------------------------------


def test_stripper_removes_a_comment_naming_the_marker():
    # Arrange — prose that MENTIONS the marker is not a read of it
    # Act
    stripped = _strip('  /* reads meta[name="stx-app-scope"] */')
    # Assert
    assert "stx-app-scope" not in stripped


def test_block_detector_fires_on_a_fork_shape():
    # Arrange — a host that DOES define its own block
    # Act
    found = re.search(r"const CLS = \"(stx-app-[^\"]+)\"", 'const CLS = "stx-app-scope-pick";')
    # Assert
    assert found is not None and found.group(1) == "stx-app-scope-pick"


def test_block_detector_ignores_a_mention():
    # Arrange — prose about a block, not a declaration. The real detector runs
    # _strip() first (removes /* */ comments, where the source keeps such prose),
    # so a mention inside a block comment is already gone; mirror that.
    # Act
    stripped = _strip('/* we reuse const CLS = "stx-app-x" */')
    found = re.search(r"const CLS = \"(stx-app-[^\"]+)\"", stripped)
    # Assert
    assert found is None


def test_files_exist_and_are_non_empty():
    """ANTI-VACUITY: if either source file vanished or moved, every check above
    would read '' and the reuse/absent ones would flip — a broken reader is
    indistinguishable from a clean tree without a population floor."""
    # Arrange
    # Act
    n = len(_scope_source()) + len(_host_source())
    # Assert
    assert n > 2000, (
        f"scope.ts + app-scope-selector.ts total {n} chars; the consumer "
        "modules moved or the path is wrong, so this guard is checking nothing"
    )
