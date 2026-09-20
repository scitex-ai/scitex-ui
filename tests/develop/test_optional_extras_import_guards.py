#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PS-233 — the optional extras must not be needed to import the package.

``scitex-dev`` (``[cli]``) and ``fastmcp`` (``[mcp]``) are optional
distributions that scitex-ui imports only when their capability is used. A bare
``pip install scitex-ui`` must still import the package, the console-script
entry point, the MCP module and the linter rules — and must be able to TELL
that the capability is absent instead of crashing.

WHY THE ABSENCE IS SIMULATED RATHER THAN SKIPPED ON. These facts hold exactly
where the extra is NOT installed, so ``pytest.importorskip("fastmcp")`` would
skip in the one environment that matters and run only where the defect cannot
appear. Instead the observations come from a COLD SUBPROCESS that parks ``None``
in ``sys.modules`` for both roots — which is what "not installed" looks like to
the import system: ``import x`` raises ImportError and
``importlib.util.find_spec(x)`` returns None.

``test_the_blocker_really_blocks`` is the positive control. Without it a
simulation that silently stopped simulating would turn every assertion below
green while proving nothing.

ONE SUBPROCESS, ONE OBSERVABLE PER TEST. The probe runs once per module (a
subprocess per assertion would cost seconds for no extra evidence) and reports
JSON; each test then asserts a single observable, so a failure names the
behaviour that broke. The probe sets ``probe_complete`` last, and the fixture
fails without it, so a truncated report can never read as a pass.

PYTHONPATH points at THIS CHECKOUT's ``src/``, never site-packages —
``tests/_checkout.py`` documents why a guard must read the branch under test.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import pytest

from tests._checkout import package_dir

#: Import roots of the optional extras: `[cli]` and `[mcp]`.
_BLOCKED_ROOTS = ("scitex_dev", "fastmcp")

_PREAMBLE = """
import sys
for _root in %r:
    sys.modules[_root] = None
    for _sub in [m for m in list(sys.modules) if m.startswith(_root + ".")]:
        sys.modules.pop(_sub, None)
""" % (_BLOCKED_ROOTS,)

_PROBE = """
import json

report = {}

import scitex_ui

report["package_import"] = True

from scitex_ui import _cli_help

report["help_available"] = _cli_help.help_available()
report["cli_help"] = _cli_help.cli_help(summary="probe")
report["examples"] = _cli_help.examples(("a", "b"))
report["spec_command"] = _cli_help.spec_command(object())
report["spec_group"] = _cli_help.spec_group(object())

from scitex_ui._mcp import server

report["mcp_import"] = True
report["fastmcp_available"] = server.FASTMCP_AVAILABLE
report["tool_defined"] = callable(server.ui_skills_list)
try:
    server.run_server()
except RuntimeError as exc:
    report["run_server_refused_with_hint"] = "pip install scitex-ui[mcp]" in str(exc)

from scitex_ui._linter import _rules

built = _rules.build_rules()
report["rule_count"] = len(built)
report["rules_all_fallback"] = all(
    isinstance(r, _rules._FallbackRule) for r in built.values()
)
report["rule_ids"] = sorted(str(r.id) for r in built.values())

from click.testing import CliRunner

from scitex_ui._cli import main

report["cli_main_import"] = True
start = CliRunner().invoke(main, ["mcp", "start"])
report["mcp_start_exit"] = start.exit_code
report["mcp_start_hint"] = "pip install scitex-ui[mcp]" in start.output
report["cli_help_exit"] = CliRunner().invoke(main, ["--help"]).exit_code

report["probe_complete"] = True
print(json.dumps(report))
"""


def _run_blocked(body: str) -> subprocess.CompletedProcess:
    """Run *body* in a fresh interpreter that cannot see the optional extras."""
    code = textwrap.dedent(_PREAMBLE) + textwrap.dedent(body)
    env = {
        **os.environ,
        # The checkout, ahead of site-packages: see the module docstring.
        "PYTHONPATH": os.pathsep.join(
            [str(package_dir().parent), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep),
    }
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


@pytest.fixture(scope="module")
def no_extras_report() -> dict:
    """Everything the no-extras world reports, from one cold interpreter."""
    # Arrange / Act
    proc = _run_blocked(_PROBE)

    # Assert (a fixture failure, so `pytest.fail` rather than `assert`)
    if proc.returncode != 0:
        pytest.fail(
            f"the probe interpreter failed with the optional extras absent:\n"
            f"{proc.stderr}"
        )
    try:
        report = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        pytest.fail(f"the probe emitted no JSON report:\n{proc.stdout}{proc.stderr}")
    if not report.get("probe_complete"):
        pytest.fail(
            f"the probe stopped early, so every assertion below would be read "
            f"from a partial report: {sorted(report)}"
        )
    return report


# --------------------------------------------------------------- control ---
def test_the_blocker_really_blocks():
    """Positive control — the simulation must be able to say "absent"."""
    # Arrange
    code = "import fastmcp"

    # Act
    proc = _run_blocked(code)

    # Assert
    assert proc.returncode != 0 and (
        "ImportError" in proc.stderr or "ModuleNotFoundError" in proc.stderr
    ), (
        f"the sys.modules blocker no longer blocks: import fastmcp returned "
        f"{proc.returncode} with stderr={proc.stderr.strip()!r}. Every test in "
        f"this file would then pass without testing the optional-extras world."
    )


# ------------------------------------------------------------- package -----
def test_the_package_imports_without_the_optional_extras(no_extras_report):
    """The property the guards exist to provide: bare install, still imports."""
    # Arrange
    observed = no_extras_report["package_import"]

    # Act
    imported = observed is True

    # Assert
    assert imported, "`import scitex_ui` must not need the optional extras"


def test_the_console_script_entry_point_imports_without_the_optional_extras(
    no_extras_report,
):
    """`scitex_ui._cli:main` is what the `scitex-ui` script loads."""
    # Arrange
    observed = no_extras_report["cli_main_import"]

    # Act
    imported = observed is True

    # Assert
    assert imported, "the console-script entry point must not need the extras"


def test_the_cli_still_renders_help_without_the_optional_extras(no_extras_report):
    """A bare install can still run the command it shipped."""
    # Arrange
    observed = no_extras_report["cli_help_exit"]

    # Act
    exit_code = observed

    # Assert
    assert exit_code == 0, f"`scitex-ui --help` exited {exit_code}"


# --------------------------------------------------------- structured help -
def test_help_available_reports_the_capability_absent(no_extras_report):
    """§4b's surface is optional, and its absence has to be reportable."""
    # Arrange
    observed = no_extras_report["help_available"]

    # Act
    live = observed

    # Assert
    assert live is False, "help_available() must say so when scitex-dev is absent"


def test_cli_help_degrades_to_none(no_extras_report):
    """None is the documented fallback: click then uses the docstring."""
    # Arrange
    observed = no_extras_report["cli_help"]

    # Act
    spec = observed

    # Assert
    assert spec is None, f"cli_help() returned {spec!r}, not the documented None"


def test_examples_degrades_to_an_empty_tuple(no_extras_report):
    """Matches what CliHelp(examples=...) would receive by default."""
    # Arrange
    observed = no_extras_report["examples"]

    # Act
    built = observed

    # Assert
    assert built == [], f"examples() returned {built!r}, not ()"


def test_spec_command_degrades_to_empty_kwargs(no_extras_report):
    """Returns {}, so the decorator call site reads the same in both worlds."""
    # Arrange
    observed = no_extras_report["spec_command"]

    # Act
    kwargs = observed

    # Assert
    assert kwargs == {}, f"spec_command() returned {kwargs!r}, not {{}}"


def test_spec_group_degrades_to_empty_kwargs(no_extras_report):
    """Returns {}, same contract as spec_command."""
    # Arrange
    observed = no_extras_report["spec_group"]

    # Act
    kwargs = observed

    # Assert
    assert kwargs == {}, f"spec_group() returned {kwargs!r}, not {{}}"


# ---------------------------------------------------------------- mcp ------
def test_the_mcp_module_stays_importable_without_fastmcp(no_extras_report):
    """The [mcp] surface must not make `import scitex_ui._mcp.server` fatal."""
    # Arrange
    observed = no_extras_report["mcp_import"]

    # Act
    imported = observed is True

    # Assert
    assert imported, "scitex_ui._mcp.server must import without fastmcp"


def test_the_mcp_flag_reports_the_capability_absent(no_extras_report):
    """A caller has to be able to tell, without guessing at an AttributeError."""
    # Arrange
    observed = no_extras_report["fastmcp_available"]

    # Act
    available = observed

    # Assert
    assert available is False, "FASTMCP_AVAILABLE must be False without fastmcp"


def test_the_mcp_tool_functions_stay_defined(no_extras_report):
    """The definitions do not need fastmcp; only the registration does."""
    # Arrange
    observed = no_extras_report["tool_defined"]

    # Act
    defined = observed is True

    # Assert
    assert defined, "the tool functions must remain callable Python functions"


def test_run_server_refuses_with_the_install_command(no_extras_report):
    """Serving without fastmcp fails loudly, never as AttributeError on None."""
    # Arrange
    observed = no_extras_report["run_server_refused_with_hint"]

    # Act
    refused = observed is True

    # Assert
    assert refused, "run_server() must raise RuntimeError naming the [mcp] extra"


def test_mcp_start_exits_one_without_fastmcp(no_extras_report):
    """Exit code 1 is what the `mcp start` help spec documents."""
    # Arrange
    observed = no_extras_report["mcp_start_exit"]

    # Act
    exit_code = observed

    # Assert
    assert exit_code == 1, f"`scitex-ui mcp start` exited {exit_code}, not 1"


def test_mcp_start_names_the_install_command(no_extras_report):
    """A bare failure would leave the user with no remedy."""
    # Arrange
    observed = no_extras_report["mcp_start_hint"]

    # Act
    named = observed is True

    # Assert
    assert named, "`scitex-ui mcp start` must name `pip install scitex-ui[mcp]`"


# ------------------------------------------------------------- linter ------
def test_the_rule_corpus_still_builds_without_scitex_dev(no_extras_report):
    """The #141 fallback path: rules must exist without scitex-dev's Rule."""
    # Arrange
    observed = no_extras_report["rule_count"]

    # Act
    count = observed

    # Assert
    assert count > 0, "the UI rule corpus must not be empty without scitex-dev"


def test_every_built_rule_is_the_fallback_class(no_extras_report):
    """The documented degradation, not an import error dressed as one."""
    # Arrange
    observed = no_extras_report["rules_all_fallback"]

    # Act
    all_fallback = observed is True

    # Assert
    assert all_fallback, "every rule must be a _FallbackRule when scitex-dev is absent"


def test_the_built_rules_are_the_ui_corpus(no_extras_report):
    """A corpus of the wrong rules would satisfy the two tests above."""
    # Arrange
    observed = no_extras_report["rule_ids"]

    # Act
    ui_only = all(str(rid).startswith("STX-UI") for rid in observed)

    # Assert
    assert ui_only, f"unexpected rule ids without scitex-dev: {observed}"
