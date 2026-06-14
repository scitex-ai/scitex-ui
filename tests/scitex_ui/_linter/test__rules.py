"""Tests for the UI-101..105 Rule corpus."""

from __future__ import annotations

import pytest

from scitex_ui._linter._rules import CATEGORY, build_rules


def test_build_rules_returns_five_rules():
    # Arrange
    rules = build_rules()
    # Act
    ids = set(rules.keys())
    # Assert
    assert ids == {"STX-UI101", "STX-UI102", "STX-UI103", "STX-UI104", "STX-UI105"}


def test_all_rules_share_ui_category():
    # Arrange
    rules = build_rules()
    # Act
    cats = {r.category for r in rules.values()}
    # Assert
    assert cats == {CATEGORY} == {"ui"}


@pytest.mark.parametrize(
    "rule_id,expected_severity",
    [
        ("STX-UI101", "warning"),
        ("STX-UI102", "warning"),
        ("STX-UI103", "warning"),
        # UI-104 is intentionally WARN in the current scitex-ui release.
        # The severity flip to ERROR is scheduled for scitex-ui 0.7.0;
        # this test guards the current release surface — when 0.7.0 lands,
        # this parameter flips to "error" with the version bump.
        ("STX-UI104", "warning"),
        ("STX-UI105", "warning"),
    ],
)
def test_rule_severity_matches_current_release(rule_id, expected_severity):
    # Arrange
    rules = build_rules()
    # Act
    rule = rules[rule_id]
    # Assert
    assert rule.severity == expected_severity


def test_ui104_message_documents_severity_flip_plan():
    # Arrange — UI-104 must self-document the WARN → ERROR migration plan
    # so users see it in `scitex-linter list-rules` output, not only in
    # the SKILL doc. This guards against silent severity flips.
    rules = build_rules()
    # Act
    msg = rules["STX-UI104"].message
    # Assert
    assert "warning → error" in msg.lower() or "warning to error" in msg.lower()
    assert "0.7" in msg


def test_all_rules_carry_requires_scitex_ui_marker():
    # Arrange — mirrors scitex-io's plugin convention so the linter knows
    # the rules require the scitex-ui package to make sense.
    rules = build_rules()
    # Act + Assert
    for rule in rules.values():
        assert rule.requires == "scitex-ui"


def test_each_rule_has_actionable_suggestion():
    # Arrange — every rule must teach the fix, not just the violation.
    rules = build_rules()
    # Act + Assert
    for rule in rules.values():
        suggestion = rule.suggestion or ""
        # The suggestion must be non-trivial — > 40 chars — and must
        # reference either a scitex-ui component or a theme token.
        assert len(suggestion) > 40, f"{rule.id} suggestion too short"
        lowered = suggestion.lower()
        assert (
            "var(--" in lowered
            or "scitex_ui." in lowered
            or "scitex-ui" in lowered
            or "dropdown" in lowered
        ), f"{rule.id} suggestion doesn't mention a component or token"
