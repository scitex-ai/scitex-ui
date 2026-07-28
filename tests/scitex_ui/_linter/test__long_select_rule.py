#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""STX-UI106 — a long native <select> has no way to narrow it.

Operator sent a screenshot of a 14-item project picker with no filter, and
asked whether the rule "always put a fuzzy filter on a list like this" could be
ENFORCED rather than merely stated. Most of it cannot: judging whether a given
list needs a filter is a UX call. This slice can, because it is a countable
property of the markup.

The threshold matches Dropdown's DEFAULT_FILTER_THRESHOLD on purpose. A lint
that disagreed with the component it recommends would be advice nobody could
satisfy.
"""

import pathlib
import tempfile

import pytest

from scitex_ui._linter._checker import scan_path


def _options(count: int) -> str:
    return "".join(
        f'<option value="{i}">item {i}</option>' for i in range(count)
    )


def _scan(markup: str) -> list[str]:
    directory = pathlib.Path(tempfile.mkdtemp())
    path = directory / "page.html"
    path.write_text(markup)
    return [violation.rule.id for violation in scan_path(path)]


@pytest.mark.parametrize("count", [9, 14, 40])
def test_select_longer_than_the_threshold_is_flagged(count):
    # Arrange
    markup = f"<select id='f-agent'>{_options(count)}</select>"

    # Act
    fired = _scan(markup)

    # Assert
    assert "STX-UI106" in fired, (
        f"a {count}-option native select was not flagged; past ~8 entries the "
        "native widget offers only first-character type-to-jump"
    )


@pytest.mark.parametrize("count", [0, 3, 8])
def test_short_select_is_left_alone(count):
    # Arrange — a deliberately short action menu must not be nagged, or the
    # rule gets muted repo-wide and stops protecting the long ones.
    markup = f"<select>{_options(count)}</select>"

    # Act
    fired = _scan(markup)

    # Assert
    assert "STX-UI106" not in fired, f"{count} options should not fire UI106"


@pytest.mark.parametrize(
    "attr", ["data-no-combobox='1'", "data-stx-combobox='1'"]
)
def test_explicit_opt_out_is_honoured(attr):
    # Arrange — some long selects are genuinely fine (an ordered list scrolled
    # by position rather than searched by name), and one already enhanced must
    # not be told to enhance itself.
    markup = f"<select {attr}>{_options(20)}</select>"

    # Act
    fired = _scan(markup)

    # Assert
    assert "STX-UI106" not in fired, f"{attr} must suppress the rule"


def test_rule_carries_a_runnable_suggestion():
    # Arrange — a warning that does not say what to write instead gets muted.
    from scitex_ui._linter._rules import build_rules

    # Act
    suggestion = build_rules()["STX-UI106"].suggestion

    # Assert
    assert "window.STX.Combobox" in suggestion, (
        "the suggestion must name the symbol consumers feature-detect, not "
        "just tell them to 'use the combobox'"
    )
