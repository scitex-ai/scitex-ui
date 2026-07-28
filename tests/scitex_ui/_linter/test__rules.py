"""Tests for the UI-101..106 Rule corpus."""

from __future__ import annotations

import pytest

from scitex_ui._linter._rules import CATEGORY, build_rules


def test_build_rules_returns_six_rules():
    # Arrange
    rules = build_rules()
    # Act
    ids = set(rules.keys())
    # Assert
    assert ids == {
        "STX-UI101",
        "STX-UI102",
        "STX-UI103",
        "STX-UI104",
        "STX-UI105",
        "STX-UI106",
    }


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
        ("STX-UI106", "warning"),
    ],
)
def test_rule_severity_matches_current_release(rule_id, expected_severity):
    # Arrange
    rules = build_rules()
    # Act
    rule = rules[rule_id]
    # Assert
    assert rule.severity == expected_severity


def test_ui104_message_documents_severity_flip_keyword():
    # Arrange — UI-104 must self-document the WARN → ERROR migration plan
    # so users see it in `scitex-linter list-rules` output, not only in
    # the SKILL doc. This guards against silent severity flips.
    rules = build_rules()
    # Act
    msg_lower = rules["STX-UI104"].message.lower()
    # Assert
    assert "warning → error" in msg_lower or "warning to error" in msg_lower


def test_ui104_message_documents_severity_flip_version_number():
    # Arrange — the flip date (scitex-ui 0.7.0) must appear inline; the
    # version number is the most operator-actionable bit of the warning.
    rules = build_rules()
    # Act
    msg = rules["STX-UI104"].message
    # Assert
    assert "0.7" in msg


@pytest.mark.parametrize(
    "rule_id",
    ["STX-UI101", "STX-UI102", "STX-UI103", "STX-UI104", "STX-UI105", "STX-UI106"],
)
def test_all_rules_carry_requires_scitex_ui_marker(rule_id):
    # Arrange — mirrors scitex-io's plugin convention so the linter knows
    # the rules require the scitex-ui package to make sense.
    rules = build_rules()
    # Act
    rule = rules[rule_id]
    # Assert
    assert rule.requires == "scitex-ui"


@pytest.mark.parametrize(
    "rule_id",
    ["STX-UI101", "STX-UI102", "STX-UI103", "STX-UI104", "STX-UI105", "STX-UI106"],
)
def test_each_rule_suggestion_is_non_trivial_length(rule_id):
    # Arrange — every rule must teach the fix, not just the violation.
    rules = build_rules()
    # Act
    suggestion = rules[rule_id].suggestion or ""
    # Assert
    assert len(suggestion) > 40


@pytest.mark.parametrize(
    "rule_id",
    ["STX-UI101", "STX-UI102", "STX-UI103", "STX-UI104", "STX-UI105", "STX-UI106"],
)
def test_each_rule_suggestion_mentions_component_or_token(rule_id):
    # Arrange — the suggestion must point at a concrete fix surface.
    rules = build_rules()
    # Act
    lowered = (rules[rule_id].suggestion or "").lower()
    # Assert
    assert (
        "var(--" in lowered
        or "scitex_ui." in lowered
        or "scitex-ui" in lowered
        or "dropdown" in lowered
    )


def test_ui106_suggestion_names_the_feature_detected_global():
    # Arrange — consumers feature-detect `window.STX.Combobox` before layering
    # the enhancement, so a suggestion that only says "use the combobox" leaves
    # the reader unable to write the guard.
    rules = build_rules()
    # Act
    suggestion = rules["STX-UI106"].suggestion or ""
    # Assert
    assert "window.STX.Combobox" in suggestion
