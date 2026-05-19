#!/usr/bin/env python3
"""Tests for CLI commands."""

import json

import pytest

# click is an optional dep (scitex-ui[cli]); skip the whole module if it
# isn't installed so pytest collection stays green (PA-303).
pytest.importorskip("click")

from click.testing import CliRunner  # noqa: E402
from scitex_ui._cli import main  # noqa: E402


@pytest.fixture
def runner():
    return CliRunner()


def _invoke_json(runner, args):
    """Run a CLI command expecting a 0 exit and JSON stdout.

    Centralised so per-test bodies can keep a single behavioural assertion
    (STX-TQ007); a non-zero exit is surfaced via `pytest.fail` with the
    captured output so the failure mode is still loud.
    """
    result = runner.invoke(main, args)
    if result.exit_code != 0:
        pytest.fail(f"CLI {args!r} exited {result.exit_code}; output:\n{result.output}")
    return json.loads(result.output)


class TestCLIRoot:
    def test_help_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_help_scitex_ui_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Act
        # Assert
        # Assert
        assert "SciTeX UI" in result.output

    def test_no_args_shows_help_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main)
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_no_args_shows_help_scitex_ui_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main)
        # Act
        # Assert
        # Assert
        assert "SciTeX UI" in result.output

    def test_help_recursive_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_help_recursive_mcp_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Act
        # Assert
        # Assert
        assert "mcp" in result.output

    def test_version_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_version_scitex_ui_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Act
        # Assert
        # Assert
        assert "scitex-ui" in result.output


# Bare `version` subcommand was removed (audit-cli §1b — `--version`/-V
# is the canonical flag). Coverage of the version surface is in
# TestCLIRoot.test_version.


class TestListPythonAPIs:
    def test_list_apis_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_list_apis_get_component_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Act
        # Assert
        # Assert
        assert "get_component" in result.output

    def test_list_apis_verbose_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_list_apis_verbose_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Act
        # Assert
        # Assert
        assert "(" in result.output  # signatures

    def test_list_apis_json_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "--json"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_list_apis_json_data_module_scitex_ui(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        # Assert
        assert data["module"] == "scitex_ui"

    def test_list_apis_json_apis_in_data(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        # Assert
        assert "apis" in data

    def test_list_apis_json_get_component_in_names(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        names = [a["name"] for a in data["apis"]]
        # Assert
        assert "get_component" in names


# `list-components` subcommand is not yet implemented in scitex_ui._cli.
# Tests deferred until the surface lands.


class TestMCPGroup:
    def test_mcp_help_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_mcp_help_start_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Act
        # Assert
        # Assert
        assert "start" in result.output

    def test_mcp_help_doctor_in_result_output(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Act
        # Assert
        # Assert
        assert "doctor" in result.output

    def test_mcp_show_installation_result_exit_code_equals_n_0(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_mcpservers_in_result_output(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Act
        # Assert
        # Assert
        assert "mcpServers" in result.output

    def test_mcp_show_installation_json_result_exit_code_equals_n_0(self, runner):
        # Arrange
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation", "--json"])
        # Act
        # Assert
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_json_data_success_is_true(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert data["success"] is True

    def test_mcp_show_installation_json_scitex_ui_in_data_config_mcpservers(
        self, runner
    ):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert "scitex-ui" in data["config"]["mcpServers"]
