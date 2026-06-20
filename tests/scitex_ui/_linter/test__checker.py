"""Tests for the file-tree walker emitting UI-101..105 UIViolations.

No mocks — fixture files written via tmp_path so each test exercises the
real regex + walker code paths.
"""

from __future__ import annotations

from pathlib import Path

from scitex_ui._linter._checker import scan_path


# --------------------------------------------------------------------------- #
# UI-101 — vanilla <select> without data-app-themed                            #
# --------------------------------------------------------------------------- #


def test_ui101_flags_vanilla_select_in_tsx(tmp_path: Path) -> None:
    # Arrange
    tsx = tmp_path / "Filter.tsx"
    tsx.write_text(
        'export const Filter = () => (\n  <select name="kind">\n    <option>a</option>\n  </select>\n);\n'
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI101" in ids


def test_ui101_skips_select_with_data_app_themed_attr(tmp_path: Path) -> None:
    # Arrange
    tsx = tmp_path / "Filter.tsx"
    tsx.write_text(
        '<select name="kind" data-app-themed="true">\n  <option>a</option>\n</select>\n'
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI101" for v in violations)


def test_ui101_skips_select_in_skip_dir_node_modules(tmp_path: Path) -> None:
    # Arrange — vendored deps under node_modules must be ignored entirely.
    nm = tmp_path / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "vendor.tsx").write_text("<select><option /></select>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


# --------------------------------------------------------------------------- #
# UI-102 — raw hex / rgb in app CSS                                            #
# --------------------------------------------------------------------------- #


def test_ui102_flags_raw_hex_color(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text("body { background: #112233; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI102" in ids


def test_ui102_skips_var_only_css(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text("body { background: var(--bg-page); color: var(--text-primary); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


def test_ui102_flags_rgb_literal(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "x.css"
    css.write_text("a { color: rgb(255, 128, 0); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI102" for v in violations)


def test_ui102_skips_hex_in_comment(tmp_path: Path) -> None:
    # Arrange — comments shouldn't trigger; they're not active style.
    css = tmp_path / "x.css"
    css.write_text("/* historical: was #112233 */\nbody { color: var(--text); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


# --------------------------------------------------------------------------- #
# UI-103 — scitex-ui shell fingerprint copied into consumer CSS                #
# --------------------------------------------------------------------------- #


def test_ui103_flags_stx_shell_sidebar_selector(tmp_path: Path) -> None:
    # Arrange — consumer copied a shell selector into their own CSS.
    css = tmp_path / "board.css"
    css.write_text(".stx-shell-sidebar { padding: 1rem; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI103" for v in violations)


# --------------------------------------------------------------------------- #
# UI-104 — consumer-side modifications to shell/primitives layout             #
# --------------------------------------------------------------------------- #


def test_ui104_flags_consumer_css_under_shell_path(tmp_path: Path) -> None:
    # Arrange — consumer repo has a CSS file living under the shell tree.
    shell_dir = tmp_path / "scitex_ui" / "css" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "consumer_override.css").write_text(".app-shell { display: grid; }\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=True)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI104" in ids


def test_ui104_suppressed_when_running_inside_scitex_ui_itself(
    tmp_path: Path,
) -> None:
    # Arrange — same path, but scitex-ui's own dev tree may edit it.
    shell_dir = tmp_path / "scitex_ui" / "css" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "theme.css").write_text("body { color: var(--text); }\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=False)

    # Assert
    assert all(v.rule.id != "STX-UI104" for v in violations)


# --------------------------------------------------------------------------- #
# UI-105 — raw color literal inside a scrollbar rule                          #
# --------------------------------------------------------------------------- #


def test_ui105_flags_raw_hex_in_webkit_scrollbar_thumb(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text(
        ".stx-todo-board ::-webkit-scrollbar-thumb {\n  background: #6a40a8;\n}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI105" in ids


def test_ui105_skips_scrollbar_thumb_using_var(tmp_path: Path) -> None:
    # Arrange — the OPERATOR-APPROVED pattern: local var backed by token.
    css = tmp_path / "board.css"
    css.write_text(
        ":root { --stx-scrollbar-thumb: var(--workspace-border-default); }\n"
        ".stx-todo-board ::-webkit-scrollbar-thumb {\n"
        "  background: var(--stx-scrollbar-thumb);\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI105" for v in violations)


def test_ui105_flags_scrollbar_color_declaration_with_raw_rgb(
    tmp_path: Path,
) -> None:
    # Arrange — Firefox-side declaration; same rule applies.
    css = tmp_path / "x.css"
    css.write_text(
        ".my-app { scrollbar-color: rgb(106, 64, 168) rgb(240, 240, 240); }\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI105" for v in violations)


# --------------------------------------------------------------------------- #
# Smoke + invariants                                                          #
# --------------------------------------------------------------------------- #


def test_scan_path_returns_empty_for_clean_consumer_tree(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text(
        ":root { --my-bg: var(--bg-page); }\n"
        ".my-app { background: var(--my-bg); color: var(--text-primary); }\n"
    )
    tsx = tmp_path / "App.tsx"
    tsx.write_text("import { Dropdown } from 'scitex_ui';\nexport default Dropdown;\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


def test_scan_path_accepts_single_file_returns_one_violation(
    tmp_path: Path,
) -> None:
    # Arrange
    css = tmp_path / "x.css"
    css.write_text("body { color: #ff0000; }\n")
    # Act
    violations = scan_path(css)
    # Assert
    assert len(violations) == 1


def test_scan_path_accepts_single_file_violation_carries_correct_rule_id(
    tmp_path: Path,
) -> None:
    # Arrange — same single-file scan as above but assert the rule id only.
    css = tmp_path / "x.css"
    css.write_text("body { color: #ff0000; }\n")
    # Act
    violations = scan_path(css)
    # Assert
    assert violations[0].rule.id == "STX-UI102"


def test_violation_carries_correct_line_number(tmp_path: Path) -> None:
    # Arrange — line 3 carries the offender.
    css = tmp_path / "x.css"
    css.write_text(
        "body { color: var(--text); }\n"
        "main { padding: 1rem; }\n"
        "footer { background: #abcdef; }\n"
    )
    # Act
    violations = scan_path(css)
    # Assert
    assert violations[0].line == 3


def test_violation_carries_source_line_containing_offender(tmp_path: Path) -> None:
    # Arrange — same fixture; this guards the source_line capture path.
    css = tmp_path / "x.css"
    css.write_text(
        "body { color: var(--text); }\n"
        "main { padding: 1rem; }\n"
        "footer { background: #abcdef; }\n"
    )
    # Act
    violations = scan_path(css)
    # Assert
    assert "#abcdef" in violations[0].source_line
