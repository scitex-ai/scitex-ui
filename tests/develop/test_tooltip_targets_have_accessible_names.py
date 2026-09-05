#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_tooltip_targets_have_accessible_names.py

"""An element carrying `data-tooltip` must still have an accessible NAME.

A DESCRIPTION IS NOT A NAME. `data-tooltip` is a plain data attribute; nothing
in the platform exposes it to assistive technology, and the two mechanisms that
render it in this repo — `app/tooltip`'s mouse handlers and a CSS
`content: attr(data-tooltip)` rule — both produce something a screen reader
either never sees or cannot rely on. So a control whose only text is a
`data-tooltip` announces as "button", full stop.

MEASURED 2026-09-03, and the instance was in this package's own shipped
template:

    standalone_shell.html:463
    <button class="ws-viewer-formats-info-btn"
            data-tooltip="Supported formats: …"
            title="">           <- EMPTY
        <i class="fas fa-info-circle"></i>   <- no text
    </button>

No text content, an empty `title`, no `aria-label`. The `title=""` was almost
certainly deliberate — suppressing the native tooltip so the styled one shows
instead — and it removed the only accessible name the element had. A fix for one
problem that silently created another.

THE SIBLING FOUR LINES BELOW GETS IT RIGHT (`title="Keyboard shortcuts (Alt+/)"`),
so two adjacent icon-only buttons carried opposite conventions and the one with
the richer content was the unnamed one. Nothing flagged it, which is what this
guard is for.

SCOPE. It reads shipped templates in this package. It cannot see downstream
consumers — hub, cards, writer and the leaves render their own markup — so a
green run here says nothing about them. If the `title=""` idiom was copied
outward, the same defect exists in trees this test cannot reach.
"""

from __future__ import annotations

import html.parser
import pathlib

import pytest

from tests._checkout import templates_dir

#: Tags that never carry an accessible name from their own content and are not
#: interactive, so a tooltip on them is decorative rather than load-bearing.
_NON_INTERACTIVE = {"div", "span", "td", "th", "li", "p", "section"}


class _TooltipTargets(html.parser.HTMLParser):
    """Collect elements carrying `data-tooltip`, with their name sources."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[dict] = []
        self._stack: list[dict] = []

    def handle_starttag(self, tag, attrs) -> None:
        a = dict(attrs)
        if "data-tooltip" in a:
            self._stack.append(
                {
                    "tag": tag,
                    "line": self.getpos()[0],
                    "aria_label": (a.get("aria-label") or "").strip(),
                    "aria_labelledby": (a.get("aria-labelledby") or "").strip(),
                    "title": (a.get("title") or "").strip(),
                    "text": "",
                    "depth": 0,
                }
            )
        elif self._stack:
            self._stack[-1]["depth"] += 1

    def handle_endtag(self, tag) -> None:
        if not self._stack:
            return
        top = self._stack[-1]
        if top["depth"] > 0:
            top["depth"] -= 1
        elif tag == top["tag"]:
            self.found.append(self._stack.pop())

    def handle_data(self, data) -> None:
        if self._stack:
            self._stack[-1]["text"] += data

    def close(self) -> None:  # pragma: no cover - flush unclosed tags
        super().close()
        while self._stack:
            self.found.append(self._stack.pop())


def _named(el: dict) -> bool:
    """Does the element have an accessible name from any source?"""
    return bool(
        el["aria_label"] or el["aria_labelledby"] or el["title"] or el["text"].strip()
    )


def _targets() -> list[tuple[str, dict]]:
    out = []
    for path in sorted(templates_dir().rglob("*.html")):
        parser = _TooltipTargets()
        parser.feed(path.read_text())
        parser.close()
        for el in parser.found:
            if el["tag"] in _NON_INTERACTIVE:
                continue
            out.append((path.name, el))
    return out


def _ids() -> list[str]:
    return [f"{name}:{el['line']}:{el['tag']}" for name, el in _targets()]


@pytest.mark.parametrize(("name", "el"), _targets(), ids=_ids())
def test_each_tooltip_target_has_an_accessible_name(name: str, el: dict) -> None:
    """`data-tooltip` describes; it does not name.

    If this fails, add an `aria-label` — do NOT remove the `title=""`, which is
    there on purpose to suppress the native tooltip.
    """
    # Arrange
    where = f"{name}:{el['line']} <{el['tag']}>"

    # Act
    named = _named(el)

    # Assert
    assert named, (
        f"{where} carries data-tooltip but has NO accessible name: no text "
        f"content, no aria-label, no aria-labelledby, and title="
        f"{el['title']!r}. A screen reader announces only the role. "
        f"data-tooltip is a plain data attribute and is never exposed; add an "
        f"aria-label."
    )


def test_the_parser_finds_the_targets_it_audits() -> None:
    """Anti-vacuity: an empty parametrisation makes the guard above silent."""
    # Arrange
    minimum = 1

    # Act
    found = _targets()

    # Assert
    assert len(found) >= minimum, (
        "no data-tooltip elements were discovered in the shipped templates, so "
        "the guard is asserting about an empty set. Either the attribute moved "
        "or the parser stopped matching."
    )


def test_the_parser_flags_an_element_with_no_name() -> None:
    """POSITIVE control: it must catch the real defect shape.

    Modelled on the exact button this guard was written for — icon-only,
    empty title, tooltip carrying all the content.
    """
    # Arrange
    markup = (
        '<button class="x" data-tooltip="Supported formats: …" title="">'
        '<i class="fas fa-info-circle"></i></button>'
    )

    # Act
    parser = _TooltipTargets()
    parser.feed(markup)
    parser.close()

    # Assert
    assert not _named(parser.found[0]), (
        "an icon-only button with an empty title was credited with an "
        "accessible name, so the guard would pass the very defect it exists "
        "to catch."
    )


def test_the_parser_accepts_an_element_named_by_aria_label() -> None:
    """NEGATIVE control: it must stay silent on a correctly named element.

    This is the arm that separates "the templates are clean" from "the parser
    credits everything". Both produce a green run.
    """
    # Arrange
    markup = (
        '<button data-tooltip="Supported formats: …" '
        'aria-label="Supported file formats" title="">'
        '<i class="fas fa-info-circle"></i></button>'
    )

    # Act
    parser = _TooltipTargets()
    parser.feed(markup)
    parser.close()

    # Assert
    assert _named(parser.found[0]), (
        "an element named by aria-label was reported as unnamed, so the guard "
        "would fail correct markup and there would be no way to satisfy it."
    )


def test_the_parser_accepts_an_element_named_by_its_text() -> None:
    """Text content is a legitimate name source, so it must count."""
    # Arrange
    markup = '<button data-tooltip="More detail here">Export</button>'

    # Act
    parser = _TooltipTargets()
    parser.feed(markup)
    parser.close()

    # Assert
    assert _named(parser.found[0]), (
        "a button named by its own text content was reported as unnamed."
    )


def test_the_parser_rejects_a_whitespace_only_title() -> None:
    """A title of spaces is not a name, and reads as one to a naive check."""
    # Arrange
    markup = '<button data-tooltip="detail" title="   "><i></i></button>'

    # Act
    parser = _TooltipTargets()
    parser.feed(markup)
    parser.close()

    # Assert
    assert not _named(parser.found[0]), (
        "a whitespace-only title was credited as an accessible name. Assistive "
        "technology announces nothing for it, so crediting it would let the "
        "defect through wearing a fix."
    )


def test_the_parser_does_not_close_the_element_on_a_nested_end_tag() -> None:
    """Depth tracking: an inner `</i>` must not end the outer `<button>`.

    Without this the parser would close the element at its first nested end
    tag, capture no text, and report every button with an icon as unnamed —
    a false positive that would look exactly like the real finding.
    """
    # Arrange
    markup = '<button data-tooltip="d"><i class="icon"></i> Download</button>'

    # Act
    parser = _TooltipTargets()
    parser.feed(markup)
    parser.close()

    # Assert
    assert parser.found[0]["text"].strip() == "Download", (
        f"text captured was {parser.found[0]['text']!r}; the parser ended the "
        f"element at the nested </i> and lost the label that follows it."
    )
