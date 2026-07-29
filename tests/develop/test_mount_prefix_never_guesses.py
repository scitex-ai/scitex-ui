#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The mount-prefix reader must THROW when the page carries no marker.

A SciTeX app runs at "/" standalone and under a prefix as a scitex-hub
built-in. The server side already spans both — scitex_app's urlpatterns are
relative — but the browser had no way to LEARN the prefix, so client code
hardcoded "/", which is correct standalone and silently wrong embedded.

The whole value of `mountPrefix()` is the refusal to guess. A default of "/"
would be indistinguishable from a correct answer in every standalone test and
would fail only once embedded — reintroducing the exact bug it exists to
remove. scitex-cards reached this independently and their chat.js says so:
"a missing marker is an integration bug, never a silently-guessed root mount."

So this guards the ABSENCE of a fallback, which is the thing a future
"helpful" edit is most likely to add. Source-level assertions, matching the
repo idiom for TypeScript that ships without a JS test runner.
"""

import pathlib
import re

import scitex_ui

_MOUNT_TS = (
    pathlib.Path(scitex_ui.__file__).parent
    / "static"
    / "scitex_ui"
    / "ts"
    / "_base"
    / "mount.ts"
)


def _source() -> str:
    return _MOUNT_TS.read_text(encoding="utf-8")


def test_mount_module_ships() -> None:
    # Arrange
    # Act
    found = _MOUNT_TS.is_file()
    # Assert
    assert found, f"{_MOUNT_TS} is the client half of the dual-mode contract"


def test_it_throws_when_no_marker_is_present() -> None:
    # Arrange — the refusal to guess IS the feature.
    src = _source()
    # Act
    throws = "throw new MountPrefixMissingError()" in src
    # Assert
    assert throws, "mountPrefix() must throw when the page carries no marker"


def test_it_defines_a_named_error_rather_than_a_bare_throw() -> None:
    # Arrange — a named error is what lets a consumer distinguish "integration
    # bug" from any other failure, instead of catching Error and guessing.
    src = _source()
    # Act
    declared = "class MountPrefixMissingError extends Error" in src
    # Assert
    assert declared


def test_the_error_message_names_both_accepted_markers() -> None:
    # Arrange — an error that does not say what to add is half-written. A
    # reader hitting this has a page and no idea what the server should emit.
    #
    # The message INTERPOLATES the two constants rather than repeating their
    # literals, so assert on the interpolation. My first version of this test
    # grepped the class body for the literal strings and failed against
    # correct code — the literals live in the const declarations above it.
    # Checking for the wrong spelling of the right thing is how a guard ends
    # up pinning the implementation instead of the property.
    src = _source()
    message_block = src[src.index("class MountPrefixMissingError") :]
    # Act
    names_both = (
        "${MOUNT_ATTRIBUTE}" in message_block
        and "${MOUNT_META_NAME}" in message_block
    )
    # Assert
    assert names_both, "the error must tell the reader which markers to emit"


def test_both_marker_constants_are_declared() -> None:
    # Arrange — pairs with the test above: interpolation is only meaningful if
    # the constants carry the real spellings consumers must emit.
    src = _source()
    # Act
    declared = 'MOUNT_ATTRIBUTE = "data-api-base"' in src and (
        'MOUNT_META_NAME = "stx-mount"' in src
    )
    # Assert
    assert declared


def test_no_default_root_fallback_survives_in_the_reader() -> None:
    # Arrange — the failure mode this file exists to prevent, expressed as the
    # code that would cause it. `?? "/"` / `|| "/"` after a marker lookup is
    # exactly the "helpful" edit that silently restores the bug.
    src = _source()
    # Act
    fallbacks = re.findall(r'(?:\?\?|\|\|)\s*["\']/["\']', src)
    # Assert
    assert fallbacks == [], (
        f"found a default-to-root fallback {fallbacks} — a guessed root mount "
        "works standalone and fails only once embedded, which is the bug"
    )


def test_it_is_exported_from_the_base_barrel() -> None:
    # Arrange — an implementation consumers cannot import is the reach defect
    # this repo has shipped before: present in the wheel, absent from the API.
    barrel = _MOUNT_TS.parent / "index.ts"
    # Act
    exported = "mountPrefix" in barrel.read_text(encoding="utf-8")
    # Assert
    assert exported, "mountPrefix must be reachable from ts/_base/index.ts"
