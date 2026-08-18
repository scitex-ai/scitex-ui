#!/usr/bin/env python3
"""Shared reading of the colour palettes, for the guards that assert on them.

WHY THIS EXISTS — five test files parse the same stylesheet, and three of them
carried their own copy of the same WCAG contrast arithmetic. That duplication
was invisible while `primitives/colors.css` was one flat file: every copy read
the same path and split it the same way, so they all agreed. The moment the
file has to change shape they stop agreeing, one at a time, and each has to be
found by its own failure.

It has to change shape. `colors.css` reached 505 lines against a 512-line
house limit, and each of the 15 remaining undefined tokens needs a declaration
in BOTH palettes plus a comment — so it splits into per-palette parts with
`colors.css` left as a barrel that imports them.

WHAT `palette_blocks` DOES ABOUT THAT: it inlines `@import`s before splitting,
to any depth. A barrel and a flat file therefore read identically, which is
what lets the split land without touching a single assertion in the guards.
Verified in both directions — this helper returns the same two blocks for the
flat file and for the barrel that replaced it.

WHAT IT DELIBERATELY DOES NOT DO: decide anything. It returns text, and every
judgement about what a token should be stays in the guard that makes it. A
helper that started asserting would become a place for one loosened rule to
quietly loosen five files at once.
"""

from __future__ import annotations

import pathlib
import re

#: Where the light palette ends and the dark one begins. Both blocks carry a
#: full palette; the dark one wins by source order, not by specificity — the
#: two selectors are both (0,1,0).
_DARK_SELECTOR = '[data-theme="dark"]'


def inline_imports(path: pathlib.Path, _seen: set[pathlib.Path] | None = None) -> str:
    """The stylesheet's text with every `@import` replaced by its target's text.

    Imports are inlined AT THEIR POSITION and children come before the parent's
    own rules, because that is what CSS does: an imported sheet is inserted at
    the point of its `@import`, and `@import` must precede every other rule.
    Order is not cosmetic here — for tokens declared in both palettes it is the
    only thing that decides which value renders.

    Cycles truncate rather than recurse forever.
    """
    seen = set() if _seen is None else _seen
    resolved = path.resolve()
    if resolved in seen or not path.is_file():
        return ""
    seen.add(resolved)

    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = re.match(r'\s*@import\s+"([^"]+)"', line)
        if match:
            out.append(inline_imports((path.parent / match.group(1)).resolve(), seen))
        else:
            out.append(line)
    return "".join(out)


def palette_blocks(path: pathlib.Path) -> tuple[str, str]:
    """The (light, dark) halves of a palette stylesheet, imports resolved.

    Splits at the dark selector, so `light` is everything before it and `dark`
    everything from it onward — the same partition the guards did individually,
    now done once and after inlining.
    """
    text = inline_imports(path)
    light, _, dark = text.partition(_DARK_SELECTOR)
    return light, dark


def declared(block: str, token: str) -> str | None:
    """The token's DECLARATION in this block, never a `var()` consumption."""
    match = re.search(rf"^\s*{re.escape(token)}\s*:\s*([^;]+);", block, re.M)
    return match.group(1).strip() if match else None


def resolve(block: str, value: str, depth: int = 6) -> str:
    """Follow `var()` aliases within a block, so assertions measure what RENDERS.

    A token whose value is `var(--other)` renders whatever `--other` renders, so
    comparing the literal text would measure the alias rather than the colour.
    """
    for _ in range(depth):
        match = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", value.strip())
        if not match:
            return value.strip()
        nxt = declared(block, match.group(1))
        if nxt is None:
            return value.strip()
        value = nxt
    return value.strip()


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    """Relative luminance per WCAG 2.x, accepting #abc and #aabbcc."""
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(foreground: str, background: str) -> float:
    """WCAG contrast ratio. AA for normal text is 4.5:1."""
    a, b = luminance(foreground), luminance(background)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)
