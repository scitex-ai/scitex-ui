#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_shell_init_guards_its_containers.py

"""`initShell` must not construct a widget for a container that is not there.

THE DEFECT, reported by figrecipe via scitex-hub on 2026-09-02 and located here
the same day: opting into a widget is a CONFIG fact, the container existing is a
DOM fact, and nothing linked them.

    _shell-init.ts   if (config.fileTree) { new ShellFileTree({
                       container: "#ws-worktree-tree", ...   <- HARDCODED
    BaseComponent    if (!el) throw new Error(
                       `${name}: container not found: ${config.container}`)

`initShell` hardcodes the selectors the SHELL TEMPLATE would render. A leaf
running standalone renders its own markup and those containers are simply absent,
so an app that passed `config.fileTree` got a throw for a container it never
asked for.

WHAT IS **NOT** THE BUG, stated because the obvious fix is wrong: BaseComponent's
throw is CORRECT and must not be weakened. A consumer who explicitly names a
container and gets nothing should hear about it loudly, with the component and
the selector named — which is exactly what that error does. The defect is one
layer up, in the caller that supplies a selector the app never chose.

SCOPE — WHAT THIS TEST CAN AND CANNOT SEE. It reads the SOURCE and checks that
every hardcoded container selector in `_shell-init.ts` is also passed to
`containerFor`. It cannot prove the guard WORKS at runtime; that needs a DOM.
What it prevents is the regression that actually happened: a new widget added to
`initShell` with a hardcoded selector and no gate. Two sites existed when this
was written and only one was in the original bug report, so "the next one will
remember" was already false once.
"""

from __future__ import annotations

import re

from tests._checkout import static_dir

#: Selector literals passed as a `container:` value, e.g. `container: "#foo"`.
_CONTAINER_ARG = re.compile(r'container:\s*"(#[^"]+)"')

#: Selector literals handed to the guard, e.g. `containerFor("#foo", "bar")`.
_GUARDED = re.compile(r'containerFor\(\s*"(#[^"]+)"')


def _shell_init_source() -> str:
    path = static_dir() / "ts" / "shell" / "_shell-init.ts"
    return path.read_text(encoding="utf-8")


def test_every_hardcoded_container_is_guarded() -> None:
    """A selector `initShell` invents must be checked before it is used."""
    # Arrange
    source = _shell_init_source()

    # Act
    unguarded = sorted(set(_CONTAINER_ARG.findall(source)) - set(_GUARDED.findall(source)))

    # Assert
    assert not unguarded, (
        f"{len(unguarded)} container selector(s) hardcoded in initShell without a "
        f"containerFor() gate: {', '.join(unguarded)}. An app that opts into the "
        "widget while rendering its own markup will get BaseComponent's "
        "container-not-found throw for an element it never asked for. Gate the "
        "construction on containerFor(selector, widgetName)."
    )


def test_the_guard_has_something_to_check() -> None:
    """ANTI-VACUITY: with no selectors found, the check above passes on nothing.

    The regexes here are the whole instrument. If `initShell` is refactored so
    containers arrive some other way — a constant, a config default, an import —
    both patterns match zero and the assertion above becomes green while
    checking nothing. That is the failure mode this file exists to prevent, so
    it must not be able to commit it.
    """
    # Arrange
    source = _shell_init_source()

    # Act
    found = _CONTAINER_ARG.findall(source)

    # Assert
    assert found, (
        "no `container: \"#...\"` literals found in _shell-init.ts, so "
        "test_every_hardcoded_container_is_guarded passed vacuously. Either the "
        "selectors moved and this file's regex must follow them, or initShell no "
        "longer hardcodes containers and this guard can be retired deliberately."
    )
