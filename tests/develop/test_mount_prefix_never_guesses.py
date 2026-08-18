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

It also guards the one thing a source-level test can check that a behavioural
one cannot: that the marker NAME agrees across the three files that spell it —
mount.ts, mount.py, and the template partial. Each is correct in isolation
while disagreeing, which renders a marker nobody reads. The behaviour of the
writer (derivation, the root-mount empty string, the shell actually emitting
it) is covered in ``tests/scitex_ui/test_mount.py``.
"""

import pathlib
import re

import scitex_ui
from tests._checkout import package_dir
from scitex_ui.mount import MOUNT_META_NAME

_PACKAGE = package_dir()

_MOUNT_TS = _PACKAGE / "static" / "scitex_ui" / "ts" / "_base" / "mount.ts"
_MARKER_HTML = _PACKAGE / "templates" / "scitex_ui" / "_mount_marker.html"
_SHELL_HTML = _PACKAGE / "templates" / "scitex_ui" / "standalone_shell.html"


def _source() -> str:
    return _MOUNT_TS.read_text(encoding="utf-8")


def _marker_markup() -> str:
    """The partial's MARKUP, with its ``{% comment %}`` prose removed.

    The comment block explains the design and therefore quotes the very
    spellings these tests look for. Grepping the whole file would match the
    explanation of the code instead of the code — a guard that passes on prose
    is a guard that cannot fail.
    """
    text = _MARKER_HTML.read_text(encoding="utf-8")
    _, _, markup = text.rpartition("{% endcomment %}")
    assert markup.strip(), "the partial has no markup outside its comment block"
    return markup


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


# ─────────────────── the WRITER: a reader needs something to read ───────────
#
# mount.ts shipped in 0.12.0 with every test above passing and NO scitex-ui
# template emitting a marker. `rg "stx-mount|data-api-base" src/` returned four
# hits, all inside mount.ts itself. The reader was correct and reached nobody.


def test_the_marker_partial_ships() -> None:
    # Arrange
    partial = _MARKER_HTML
    # Act
    found = partial.is_file()
    # Assert
    assert found, f"{partial} is the writer half of the contract"


def test_the_shell_includes_the_marker_partial() -> None:
    # Arrange — four consuming repos extend this shell (cards, writer,
    # figrecipe, cloud; six templates between them), so it is the reach path.
    # scholar and hub own their own <head> and take the partial directly.
    shell = _SHELL_HTML.read_text(encoding="utf-8")
    # Act
    included = '{% include "scitex_ui/_mount_marker.html" %}' in shell
    # Assert
    assert included, "standalone_shell.html must include the mount marker"


def test_the_reader_declares_the_same_marker_name_as_the_writer() -> None:
    # Arrange — mount.ts declares it for the reader, scitex_ui.mount for the
    # writer. Either drifting alone produces a marker that is emitted and never
    # read, with nothing failing anywhere.
    src = _source()
    # Act
    agrees = f'MOUNT_META_NAME = "{MOUNT_META_NAME}"' in src
    # Assert
    assert agrees, "mount.ts must declare the same name as scitex_ui.mount"


def test_the_partial_emits_the_marker_name_both_sides_agree_on() -> None:
    # Arrange — the third spelling of the same string, in the template that
    # actually renders it.
    markup = _marker_markup()
    # Act
    emits = f'name="{MOUNT_META_NAME}"' in markup
    # Assert
    assert emits, "the partial must emit the name the reader looks for"


def test_the_partial_gates_on_the_declared_flag() -> None:
    # Arrange — the marker must be emitted whenever a prefix was DECLARED,
    # including the root mount whose prefix is the empty string.
    markup = _marker_markup()
    # Act
    gates_on_flag = "{% if stx_mount_declared %}" in markup
    # Assert
    assert gates_on_flag, "the marker must be emitted whenever a prefix was declared"


def test_the_partial_does_not_gate_on_the_prefix_value() -> None:
    # Arrange — the "helpful" edit that breaks standalone. A root mount IS the
    # empty string, so `{% if stx_mount_prefix %}` is false for it and the
    # marker vanishes in exactly the mode where its absence is invisible,
    # because hardcoded "/" happens to work there.
    markup = _marker_markup()
    # Act
    gates_on_value = re.search(r"{%\s*if\s+stx_mount_prefix\s*%}", markup)
    # Assert
    assert gates_on_value is None, (
        "gating on the prefix VALUE drops the marker for a root mount, which is "
        "the one case where the bug is silent"
    )
