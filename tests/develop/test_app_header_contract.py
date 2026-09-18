#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract for the ONE canonical app header.

OPERATOR DIRECTION (2026-09-17, SDK owner): every app presents the SAME header
template — leaf title, leaf package version, the project picker, then
app-specific actions — so a user can predict it across apps and no leaf ships
its own header chrome. FigRecipe shipped one first (PR #406) and it is the
evidence for the shape here: same BEM vocabulary, plus the two defects a
per-leaf copy produces — a chrome row that only the leaf styles, and a version
badge that renders NOTHING once the app is mounted by the hub.

This test is STATIC on the shipped CSS + TS source (the half that runs in CI on
every change, same deliberate shape as test_project_selector_contract.py). It is
weaker than the 390px browser measurement recorded on the card, in exactly one
way: a green here means "the row, the slots and the phone rules are present in
the shipment", not "the header is usable on a phone". What it CAN prove — and
what a browser measurement cannot cheaply re-prove on every PR — is that the
single-definition and no-placeholder properties hold.

ONE ASSERTION PER TEST, THREE MARKER LINES (PA-307 §3 STX-TQ002/TQ007): each
test computes a value under `# Act` and asserts it under `# Assert`, so the
first failure names the property that broke. Where a property is a set — which
fallbacks disagree with theme.css — a helper returns the OFFENDERS and the test
asserts the list is empty.

SHAPE: every extractor carries a POSITIVE and a NEGATIVE control, per
test_detectors_carry_controls.py — a guard whose extractor stops matching turns
every assertion vacuously true. The ``_COMMENT`` stripper is exempted there
(same shape as test_project_selector_contract.py's) because a comment stripper
is only exercised through ``.sub()``, never searched.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_STATIC = _ROOT / "src/scitex_ui/static/scitex_ui"
_CSS = _STATIC / "css/app/app-header.css"
_SLOT_CSS = _STATIC / "css/app/project-selector.css"
_THEME_CSS = _STATIC / "css/shell/theme.css"
_TS = _STATIC / "ts/app/app-header"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)

_BLOCK = ".stx-app-header"
_TITLE = ".stx-app-header__title"
_ACTIONS = ".stx-app-header__actions"
_ACTION = ".stx-app-header__action"
_SLOT = ".stx-app-header__slot--project-selector"
_HIDDEN_VERSION = ".stx-app-header__version[hidden]"


def _css() -> str:
    return _COMMENT.sub("", _CSS.read_text(errors="replace"))


def _slot_css() -> str:
    return _COMMENT.sub("", _SLOT_CSS.read_text(errors="replace"))


def _theme_css() -> str:
    return _COMMENT.sub("", _THEME_CSS.read_text(errors="replace"))


def _rule_block(selector: str) -> str:
    """The text inside the FIRST rule whose selector list contains `selector`."""
    match = re.search(re.escape(selector) + r"\s*\{([^{}]*)\}", _css())
    return match.group(1) if match else ""


def _media_block(query: str, containing: str) -> str:
    """The text inside an @media matching `query` whose body contains `containing`."""
    text = _css()
    for match in re.finditer(r"@media([^{]*)\{", text):
        if query not in match.group(1):
            continue
        depth, index, start = 1, match.end(), match.end()
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        body = text[start : index - 1]
        if containing in body:
            return body
    return ""


def _ts_text() -> str:
    return "\n".join(
        path.read_text(errors="replace") for path in sorted(_TS.rglob("*.ts"))
    )


def _token_value(css_text: str, token: str) -> str | None:
    match = re.search(re.escape(token) + r"\s*:\s*([^;]+);", css_text)
    return match.group(1).strip() if match else None


def _declares(block: str, prop: str) -> bool:
    """True when `block` declares `prop` as its own property.

    Anchored at the start of a line so ``min-height`` does not read as
    ``height`` — the substring form of that mistake is how a guard ends up
    asserting the opposite of what it says.
    """
    return any(line.strip().startswith(f"{prop}:") for line in block.splitlines())


def _var_fallbacks(css_text: str) -> list[tuple[str, str]]:
    """Every ``var(--stx-*, <fallback>)`` pair, with the fallback PAREN-BALANCED.

    A fallback may itself contain a function call — ``env(safe-area-inset-left,
    0px)`` is exactly what shell/theme.css declares — so a `[^)]+` capture would
    truncate it and then compare a truncated string against the real value,
    reporting a drift that does not exist.
    """
    pairs: list[tuple[str, str]] = []
    for match in re.finditer(r"var\((--stx-[a-z-]+),", css_text):
        start, depth, index = match.end(), 1, match.end()
        while index < len(css_text) and depth:
            if css_text[index] == "(":
                depth += 1
            elif css_text[index] == ")":
                depth -= 1
            index += 1
        if depth == 0:
            pairs.append((match.group(1), css_text[start : index - 1].strip()))
    return pairs


def _fallback_disagreements() -> list[str]:
    """Tokens whose app-header.css fallback is undefined in or differs from theme.css."""
    css, theme = _css(), _theme_css()
    drift: list[str] = []
    for token, fallback in _var_fallbacks(css):
        declared = _token_value(theme, token)
        if declared is None:
            drift.append(f"{token} is not defined in shell/theme.css")
        elif fallback != declared:
            drift.append(f"{token}: fallback {fallback!r} != theme {declared!r}")
    return drift


# ── Extractor controls ────────────────────────────────────────────────────
# Both directions, so a broken extractor cannot make the guards below pass
# vacuously. Each control uses a LITERAL sample, never the tree.


def test_the_comment_stripper_matches_a_real_comment() -> None:
    """POSITIVE: _COMMENT matches a real block comment."""
    # Arrange
    sample = "/* a real comment */ .a { color: red; }"
    # Act
    match = _COMMENT.search(sample)
    # Assert
    assert match is not None


def test_the_comment_stripper_ignores_a_mention_of_the_word_comment() -> None:
    """NEGATIVE: prose about comments is not a comment."""
    # Arrange
    sample = "# this line mentions comments but is not one"
    # Act
    matched = _COMMENT.search(sample)
    # Assert
    assert matched is None


def test_the_rule_block_extractor_matches_a_literal_rule() -> None:
    """POSITIVE: the extractor returns the body of the rule it is given."""
    # Arrange
    sample = ".a { color: red; } .b { color: blue; }"
    # Act
    match = re.search(re.escape(".b") + r"\s*\{([^{}]*)\}", sample)
    # Assert
    assert match is not None and match.group(1).strip() == "color: blue;"


def test_the_rule_block_extractor_ignores_a_mention() -> None:
    """NEGATIVE: a comment that names a selector is not a rule for it."""
    # Arrange
    sample = _COMMENT.sub("", "/* .stx-app-header exists elsewhere */")
    # Act
    match = re.search(re.escape(_BLOCK) + r"\s*\{([^{}]*)\}", sample)
    # Assert
    assert match is None


def test_the_var_fallback_extractor_captures_a_nested_fallback() -> None:
    """POSITIVE: a nested fallback is captured whole, not truncated at its `)`."""
    # Arrange
    sample = ".a { padding: var(--stx-safe-inset-left, env(safe-area-inset-left, 0px)); }"
    # Act
    pairs = _var_fallbacks(sample)
    # Assert
    assert pairs == [("--stx-safe-inset-left", "env(safe-area-inset-left, 0px)")]


def test_the_var_fallback_extractor_ignores_a_mention() -> None:
    """NEGATIVE: a token name without a var() call yields no pair."""
    # Arrange
    sample = _COMMENT.sub("", "/* --stx-touch-target-min is documented here */")
    # Act
    pairs = _var_fallbacks(sample)
    # Assert
    assert pairs == []


def test_the_property_detector_is_not_fooled_by_a_longer_property_name() -> None:
    """POSITIVE control for _declares: `min-height` is not a declaration of `height`."""
    # Arrange
    block = "min-height: 40px;"
    # Act
    declares_height = _declares(block, "height")
    # Assert
    assert declares_height is False


def test_the_property_detector_sees_a_real_declaration() -> None:
    """POSITIVE control for _declares: a real declaration is seen."""
    # Arrange
    block = "height: 40px;"
    # Act
    declares_height = _declares(block, "height")
    # Assert
    assert declares_height is True


def test_the_files_under_test_are_not_empty() -> None:
    """POSITIVE: an empty or moved file would make every guard below vacuous."""
    # Arrange
    css, ts = _css(), _ts_text()
    # Act
    sizes = (len(css), len(ts))
    # Assert
    assert sizes[0] > 500 and sizes[1] > 500


# ── The canonical row ─────────────────────────────────────────────────────


def test_the_css_declares_the_block_class() -> None:
    """The block itself is shipped, not merely referenced."""
    # Arrange
    css = _css()
    # Act
    declared = re.search(re.escape(_BLOCK) + r"\s*\{", css) is not None
    # Assert
    assert declared


def test_the_block_is_a_flex_row() -> None:
    """The header is a flex row, so its slots line up instead of stacking."""
    # Arrange
    block = _rule_block(_BLOCK)
    # Act
    is_flex = _declares(block, "display") and "display: flex" in block
    # Assert
    assert is_flex


def test_the_block_centres_its_slots() -> None:
    """A mixed-height row aligns on the centre line, not the baseline."""
    # Arrange
    block = _rule_block(_BLOCK)
    # Act
    centred = "align-items: center" in block
    # Assert
    assert centred


def test_the_block_separates_itself_from_the_content() -> None:
    """The header owns a bottom rule; without it the row merges into the app."""
    # Arrange
    block = _rule_block(_BLOCK)
    # Act
    separated = "border-bottom" in block
    # Assert
    assert separated


def test_the_block_border_follows_the_theme() -> None:
    """The rule reads a token, so it cannot freeze a literal across palettes."""
    # Arrange
    block = _rule_block(_BLOCK)
    # Act
    thematic = "var(--workspace-border-subtle" in block
    # Assert
    assert thematic


def test_the_block_keeps_its_row_height_as_a_minimum() -> None:
    """min-height, not height: a taller control must not be clipped."""
    # Arrange
    block = _rule_block(_BLOCK)
    # Act
    fixed_height = _declares(block, "height")
    # Assert
    assert fixed_height is False


def test_the_title_truncates_with_an_ellipsis() -> None:
    """A long leaf name ends in an ellipsis rather than pushing the row wider."""
    # Arrange
    block = _rule_block(_TITLE)
    # Act
    truncates = "text-overflow: ellipsis" in block
    # Assert
    assert truncates


def test_the_title_clips_its_overflow() -> None:
    """The ellipsis only applies to content the element is allowed to clip."""
    # Arrange
    block = _rule_block(_TITLE)
    # Act
    clips = "overflow: hidden" in block
    # Assert
    assert clips


def test_the_title_can_shrink_inside_the_flex_row() -> None:
    """min-width:0 is what makes the ellipsis fire on a flex item at all."""
    # Arrange
    block = _rule_block(_TITLE)
    # Act
    can_shrink = "min-width: 0" in block
    # Assert
    assert can_shrink


def test_an_unknown_version_is_genuinely_absent() -> None:
    """A hidden badge must be display:none, not merely empty."""
    # Arrange
    block = _rule_block(_HIDDEN_VERSION)
    # Act
    absent = "display: none" in block
    # Assert
    assert absent


def test_the_actions_slot_does_not_claim_a_left_auto_margin() -> None:
    """The canonical slot owns the right push; a second auto-margin drifts it."""
    # Arrange
    block = _rule_block(_ACTIONS)
    # Act
    offsets_itself = "margin-left" in block
    # Assert
    assert offsets_itself is False


def test_the_action_control_is_styled_where_the_row_is_styled() -> None:
    """A control class with no rule renders unstyled in every adopting app."""
    # Arrange
    block = _rule_block(_ACTION)
    # Act
    styled = block.strip() != ""
    # Assert
    assert styled


def test_the_action_control_reads_as_clickable() -> None:
    """The action is a control, so the cursor says so."""
    # Arrange
    block = _rule_block(_ACTION)
    # Act
    pointer = "cursor: pointer" in block
    # Assert
    assert pointer


# ── Single definition across the package ───────────────────────────────────


def test_the_project_slot_keeps_its_definition_in_project_selector_css() -> None:
    """The pinned owner of the slot rule is unchanged by this component."""
    # Arrange
    slot_css = _slot_css()
    # Act
    owned = re.search(re.escape(_SLOT) + r"\s*\{", slot_css) is not None
    # Assert
    assert owned


def test_the_project_slot_pins_an_explicit_order() -> None:
    """The slot's order is what keeps the selector left-after-title."""
    # Arrange
    match = re.search(re.escape(_SLOT) + r"\s*\{([^{}]*)\}", _slot_css())
    # Act
    body = match.group(1) if match else ""
    # Assert
    assert "order" in body


def test_the_project_slot_is_not_redefined_here() -> None:
    """Two definitions in two layers is the duplicate-definition defect."""
    # Arrange
    block = _rule_block(".stx-app-header__slot--project-selector")
    # Act
    redefined = block.strip()
    # Assert
    assert redefined == ""


def test_the_component_renders_the_canonical_slot_class() -> None:
    """The header is a WRITER of the slot the placement contract pins."""
    # Arrange
    ts = _ts_text()
    # Act
    renders_slot = "${CLS}__slot--project-selector" in ts
    # Assert
    assert renders_slot


def test_the_component_declares_the_manifest_class_convention() -> None:
    """`const CLS` is what the generated class-manifest reads."""
    # Arrange
    ts = _ts_text()
    # Act
    declared = 'const CLS = "stx-app-header"' in ts
    # Assert
    assert declared


# ── The mount-metadata contract (scitex-app) ───────────────────────────────


def test_the_version_is_read_from_the_mount_stamp() -> None:
    """The badge reads the host-stamped attribute, not a leaf build constant."""
    # Arrange
    ts = _ts_text()
    # Act
    stamped = 'APP_VERSION_ATTRIBUTE = "data-app-version"' in ts
    # Assert
    assert stamped


def test_the_component_never_reads_a_build_time_constant() -> None:
    """A hub-mount compiles the bridge, so a build constant renders empty."""
    # Arrange
    ts = _ts_text()
    # Act
    forbidden = [name for name in ("import.meta.env", "process.env") if name in ts]
    # Assert
    assert forbidden == []


def test_the_resolver_can_answer_unknown() -> None:
    """Absence is expressed, never guessed at."""
    # Arrange
    ts = _ts_text()
    # Act
    answerable = "return null;" in ts
    # Assert
    assert answerable


def test_the_component_does_not_substitute_a_placeholder_version() -> None:
    """A placeholder version is indistinguishable from a real one."""
    # Arrange
    ts = _ts_text()
    # Act
    placeholder = "v0.0.0" in ts
    # Assert
    assert placeholder is False


def test_the_reader_mirrors_the_meta_name_scitex_app_writes() -> None:
    """scitex-app emits `stx-app-shell`; a reader of another name reaches nobody."""
    # Arrange
    ts = _ts_text()
    # Act
    mirrored = 'SHELL_PROPS_META_NAME = "stx-app-shell"' in ts
    # Assert
    assert mirrored


def test_the_reader_reads_the_payload() -> None:
    """The header consumes the host's declaration rather than re-deriving it."""
    # Arrange
    ts = _ts_text()
    # Act
    reads = "readShellProps" in ts
    # Assert
    assert reads


def test_the_title_comes_from_the_payload() -> None:
    """The host's title is the header's title."""
    # Arrange
    ts = _ts_text()
    # Act
    from_payload = "this.shellProps?.title" in ts
    # Assert
    assert from_payload


def test_the_version_comes_from_the_payload() -> None:
    """The host's version is the header's version."""
    # Arrange
    ts = _ts_text()
    # Act
    from_payload = "this.shellProps?.version" in ts
    # Assert
    assert from_payload


def test_the_project_slot_is_tied_to_the_project_scope() -> None:
    """A user-scoped app gets no selector, mirroring the writer's refusal."""
    # Arrange
    ts = _ts_text()
    # Act
    scope_tied = 'scope === "project"' in ts
    # Assert
    assert scope_tied


def test_the_project_slot_decision_is_a_named_rule() -> None:
    """The slot decision is readable in one place, not inlined at the call site."""
    # Arrange
    ts = _ts_text()
    # Act
    named = "wantsProjectSlot" in ts
    # Assert
    assert named


def test_a_payload_that_cannot_be_read_is_refused_not_swallowed() -> None:
    """A silently action-less header looks exactly like an app with no actions."""
    # Arrange
    ts = _ts_text()
    # Act
    refuses = "unreadable" in ts
    # Assert
    assert refuses


def test_an_action_that_names_neither_a_command_nor_an_href_is_refused() -> None:
    """A control that does nothing renders identically to a working one."""
    # Arrange
    ts = _ts_text()
    # Act
    refuses = "neither a command" in ts
    # Assert
    assert refuses


# ── Phones: 390px behaviour, as far as a static guard can carry it ─────────


def test_the_header_carries_a_phone_block() -> None:
    """The row has its own phone rules; without them it cannot wrap."""
    # Arrange
    block = _media_block("600px", containing=_BLOCK)
    # Act
    present = block.strip() != ""
    # Assert
    assert present


def test_the_phone_block_wraps_the_row() -> None:
    """Wrapping is what puts the full-width selector on its own row."""
    # Arrange
    block = _media_block("600px", containing="flex-wrap")
    # Act
    wraps = "flex-wrap: wrap" in block
    # Assert
    assert wraps


def test_the_phone_block_covers_interactive_controls_generically() -> None:
    """One rule covers the leaf's actions AND the selector's trigger."""
    # Arrange
    block = _media_block("600px", containing=":is(button")
    # Act
    generic = ":is(button, a, [role=" in block
    # Assert
    assert generic


def test_the_phone_block_sets_the_touch_minimum_height() -> None:
    """Under a coarse pointer every header control is a 44px target."""
    # Arrange
    block = _media_block("600px", containing="min-height")
    # Act
    minimum = "min-height: var(--stx-touch-target-min, 44px)" in block
    # Assert
    assert minimum


def test_the_phone_block_sets_the_touch_minimum_width() -> None:
    """The target is square-minimum, so a narrow control is still tappable."""
    # Arrange
    block = _media_block("600px", containing="min-width")
    # Act
    minimum = "min-width: var(--stx-touch-target-min, 44px)" in block
    # Assert
    assert minimum


def test_at_least_one_theme_token_is_used_with_a_fallback() -> None:
    """POSITIVE: the fallback comparison below is not measuring an empty set."""
    # Arrange
    css = _css()
    # Act
    pairs = _var_fallbacks(css)
    # Assert
    assert len(pairs) >= 3


def test_every_theme_token_here_is_defined_and_agrees_with_theme_css() -> None:
    """The fallbacks COPY theme.css values, so a drift in either direction fails.

    A page loading only app.css does not include shell/theme.css, which is why
    the fallbacks exist — and a copy that silently disagrees with its source is
    the frozen-literal class this repo cards.
    """
    # Arrange
    expected_drift: list[str] = []
    # Act
    disagreeing = _fallback_disagreements()
    # Assert
    assert disagreeing == expected_drift


def test_the_token_agreement_checker_can_report_a_difference() -> None:
    """POSITIVE control: the comparison is capable of disagreeing."""
    # Arrange
    sample_theme = ":root { --stx-touch-target-min: 48px; }"
    # Act
    declared = _token_value(sample_theme, "--stx-touch-target-min")
    # Assert
    assert declared == "48px" and declared != "44px"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
