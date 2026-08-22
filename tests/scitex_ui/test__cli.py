#!/usr/bin/env python3
"""Tests for CLI commands."""

import json
import os
from pathlib import Path

import pytest

# click is an optional dep (scitex-ui[cli]); skip the whole module if it
# isn't installed so pytest collection stays green (PA-303).
pytest.importorskip("click")

import click  # noqa: E402
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
    def test_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Assert
        assert result.exit_code == 0

    def test_help_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Assert
        assert "SciTeX UI" in result.output

    def test_no_args_shows_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main)
        # Assert
        assert result.exit_code == 0

    def test_no_args_shows_help_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main)
        # Assert
        assert "SciTeX UI" in result.output

    def test_help_recursive_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Assert
        assert result.exit_code == 0

    def test_help_recursive_contains_mcp(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Assert
        assert "mcp" in result.output

    def test_version_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Assert
        assert result.exit_code == 0

    def test_version_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Assert
        assert "scitex-ui" in result.output


# Bare `version` subcommand was removed (audit-cli §1b — `--version`/-V
# is the canonical flag). Coverage of the version surface is in
# TestCLIRoot.test_version.


class TestListPythonAPIs:
    def test_list_apis_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_contains_get_component(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Assert
        assert "get_component" in result.output

    def test_list_apis_verbose_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_verbose_shows_signatures(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Assert
        assert "(" in result.output  # signatures

    def test_list_apis_json_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "--json"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_json_module_is_scitex_ui(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        # Assert
        assert data["module"] == "scitex_ui"

    def test_list_apis_json_has_apis_key(self, runner):
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
    def test_mcp_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_help_contains_start(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert "start" in result.output

    def test_mcp_help_contains_doctor(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert "doctor" in result.output

    def test_mcp_show_installation_exit_zero(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_contains_mcpservers(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Assert
        assert "mcpServers" in result.output

    def test_mcp_show_installation_json_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation", "--json"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_json_success_is_true(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert data["success"] is True

    def test_mcp_show_installation_json_has_scitex_ui(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert "scitex-ui" in data["config"]["mcpServers"]


# §13 (doctrine 20_dev-commands.md): self-maintenance surfaces live under
# the `dev` group. `scitex-ui dev skills` is the canonical spelling; the
# local skills group is self-contained (no scitex-dev runtime dep), so
# this class passes in BOTH a bare install and a [cli] install.
class TestDevGroup:
    def test_dev_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "--help"])
        # Assert
        assert result.exit_code == 0

    def test_dev_help_lists_skills(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "--help"])
        # Assert
        assert "skills" in result.output

    def test_bare_dev_shows_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev"])
        # Assert
        assert result.exit_code == 0

    def test_bare_dev_shows_skills(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev"])
        # Assert
        assert "skills" in result.output

    def test_skills_list_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "list"])
        # Assert
        assert result.exit_code == 0

    def test_skills_list_contains_first_leaf(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "list"])
        # Assert
        assert "01_installation" in result.output

    def test_skills_list_json_returns_nonempty_list(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["dev", "skills", "list", "--json"])
        # Assert
        assert isinstance(data, list) and data

    def test_skills_list_json_names(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["dev", "skills", "list", "--json"])
        # Assert
        assert "01_installation" in [entry["name"] for entry in data]

    def test_skills_get_known_leaf_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "get", "01_installation"])
        # Assert
        assert result.exit_code == 0

    def test_skills_get_missing_exit_one(self, runner):
        # `skills get` raises SystemExit(1) for an unknown name (not a
        # click UsageError, so the exit code is 1, not 2).
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "get", "no-such-skill"])
        # Assert
        assert result.exit_code == 1

    def test_skills_install_dry_run_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "install", "--dry-run"])
        # Assert
        assert result.exit_code == 0

    def test_skills_install_dry_run_previews(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["dev", "skills", "install", "--dry-run"])
        # Assert
        assert "would" in result.output

    def test_top_level_skills_not_advertised(self, runner):
        # The legacy spelling is a HIDDEN alias, so `scitex-ui --help`
        # must not list a top-level `skills` command anymore. Holds in
        # both worlds: bare install (no command at all) and [cli]
        # install (command present but hidden).
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Assert
        assert not any(
            line.strip().startswith("skills")
            for line in result.output.splitlines()
        )


# Phase W (doctrine 11_deprecation.md): the legacy top-level `skills`
# spelling forwards to `dev skills` with a once-per-shell stderr warning.
# The alias is built by scitex_dev.ecosystem.deprecated_alias, so it only
# exists where scitex-dev is installed — a bare install has no alias at
# all, and this class skips as a whole there.
class TestSkillsLegacyAlias:
    @pytest.fixture(autouse=True)
    def _needs_scitex_dev(self):
        pytest.importorskip("scitex_dev")

    def test_alias_registered_as_command_not_group(self):
        # click.Group is a subclass of click.Command, so both clauses are
        # required: the alias must be a leaf Command that forwards, not a
        # nested Group.
        # Arrange
        # Act
        cmd = main.commands.get("skills")
        # Assert
        assert isinstance(cmd, click.Command) and not isinstance(
            cmd, click.Group
        )

    def test_alias_command_is_hidden(self):
        # Arrange
        # Act
        cmd = main.commands.get("skills")
        # Assert
        assert cmd is not None and cmd.hidden

    def test_alias_carries_audit_metadata(self):
        # The §13 CLI auditor reads this dict statically (escape hatch),
        # so its exact shape is part of the contract.
        # Arrange
        from scitex_ui._dev_group import _ALIAS_REMOVE_IN

        # Act
        meta = getattr(main.commands["skills"], "_deprecated_alias", None)
        # Assert
        assert meta == {
            "target": "dev skills",
            "remove_in": _ALIAS_REMOVE_IN,
            "phase": "warn",
        }

    def test_alias_list_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["skills", "list"])
        # Assert
        assert result.exit_code == 0

    def test_alias_list_same_content(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["skills", "list"])
        # Assert
        assert "01_installation" in result.output

    def test_alias_help_forwards_to_real_group(self, runner):
        # A group-targeted alias suppresses its own --help option so the
        # REAL group's help is printed (click_compat: add_help_option is
        # False when the target is a Group).
        # Arrange
        # Act
        result = runner.invoke(main, ["skills", "--help"])
        # Assert
        assert result.exit_code == 0 and "list" in result.output

    def test_alias_warns_on_stderr(self, runner):
        # The warning fires once per shell session: scitex-dev writes a
        # marker file `${XDG_RUNTIME_DIR:-/tmp}/scitex-cli-dep-<user>-
        # <parent-pid>-<old-name>.flag` and skips if it exists. Clear it
        # so THIS invocation is the first of the session and the warning
        # is guaranteed to fire here, whatever ran earlier in this
        # process — no mocking, this is the mechanism's own state.
        # Arrange
        base = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
        for marker in base.glob(f"scitex-cli-dep-*-{os.getppid()}-skills.flag"):
            marker.unlink(missing_ok=True)
        # Act
        result = runner.invoke(main, ["skills", "list"])
        # Assert (click >= 8.2: stderr is separate from result.output)
        assert "deprecated" in result.stderr and "dev skills" in result.stderr
