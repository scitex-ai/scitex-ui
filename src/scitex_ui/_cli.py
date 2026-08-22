"""Minimal CLI for scitex-ui — docs, skills, introspection.

Follows the same pattern as scitex-stats and scitex-app CLIs.
Every SciTeX package provides: docs, skills, mcp, introspect, list-python-apis.
"""

from __future__ import annotations

# `click` is a HARD core dependency (declared in [project.dependencies]).
# The `scitex-ui` console-script does an unguarded module-load import so a
# broken install fails loudly at import time — the correct CI signal —
# rather than degrading to a runtime hint. PS-213 console-script-deps-
# must-be-core enforces this ecosystem-wide.
import click

# Structured help (§4b) resolved LAZILY — scitex-dev is the optional [cli]
# extra, and this module is the console-script entry point, so importing it
# here at module scope would violate PS-213. See _cli_help for the full
# reconciliation of the two rules.
from ._cli_help import cli_help, examples as _examples, spec_command, spec_group

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

_MAIN_HELP = cli_help(
    summary="SciTeX UI — shared React/TypeScript components for the workspace.",
    description=(
        "Provides the shell, primitives and app components that consuming "
        "SciTeX apps mount, plus the docs/skills/MCP surfaces every package "
        "exposes.",
        "Config is loaded with the SciTeX precedence chain: config.yaml -> "
        "$SCITEX_UI_CONFIG -> ~/.scitex/ui/config.yaml -> defaults.",
    ),
    version_of="scitex-ui",
)

_DEV_HELP = cli_help(
    summary="Self-maintenance surfaces for this package.",
    description=(
        "Housekeeping, not domain: `scitex-ui --help` should read as the tool, "
        "not as the tool's own upkeep (doctrine 20_dev-commands.md, §13).",
        "`dev` is a group only and never takes a positional argument directly.",
    ),
)

_SKILLS_ALIAS_HELP = cli_help(
    summary="DEPRECATED spelling of `scitex-ui dev skills`.",
    description=(
        "Kept as a Phase W warn-forward alias so nothing in the wild breaks "
        "mid-migration (§1a requires `<cli> skills` to exist while `_skills/` "
        "ships; §13 wants it under `dev`). Removed in scitex-ui 0.20.0.",
        "Use `scitex-ui dev skills` — identical behaviour, no warning.",
    ),
)

_MCP_HELP = cli_help(
    summary="MCP (Model Context Protocol) server commands.",
    description=(
        "Start the server, check its dependencies, list the tools it exposes, "
        "and print the client configuration needed to install it.",
    ),
)


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("scitex-ui")
    except Exception:
        return "0.0.0"


@click.group(
    context_settings=CONTEXT_SETTINGS,
    invoke_without_command=True,
    **spec_group(_MAIN_HELP),
)
@click.version_option(_get_version(), "-V", "--version", prog_name="scitex-ui")
@click.option(
    "--help-recursive", is_flag=True, help="Show help for all subcommands."
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit structured JSON output (propagates to subcommands that honour it).",
)
@click.pass_context
def main(ctx, help_recursive, as_json):
    """SciTeX UI — shared React/TypeScript components for the workspace.

    \b
    Config is loaded with the SciTeX precedence chain:
      config.yaml -> $SCITEX_UI_CONFIG -> ~/.scitex/ui/config.yaml -> defaults
    """
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    if help_recursive:
        click.echo(ctx.get_help())
        click.echo()
        group = ctx.command
        if isinstance(group, click.Group):
            for name in sorted(group.list_commands(ctx)):
                cmd = group.get_command(ctx, name)
                sub_ctx = click.Context(cmd, parent=ctx, info_name=name)
                click.echo(f"{'=' * 60}")
                click.echo(f"Command: {name}")
                click.echo(f"{'=' * 60}")
                click.echo(sub_ctx.get_help())
                click.echo()
        ctx.exit(0)
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# -- MCP commands --------------------------------------------------------
@click.group(
    invoke_without_command=True,
    **spec_group(
        _MCP_HELP,
        command_categories=[
            ("Run", ["start", "doctor"]),
            ("Inspect", ["list-tools", "show-installation"]),
        ],
    ),
)
@click.pass_context
def mcp_group(ctx):
    """MCP (Model Context Protocol) server commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@mcp_group.command(
    "start",
    **spec_command(
        cli_help(
            summary="Start the scitex-ui MCP server.",
            description=("Serves the scitex-ui tool surface over stdio transport.",),
            examples=_examples(
                ("{prog}", ""),
                ("{prog} --dry-run", "print the launch plan only"),
            ),
            exit_codes=((0, "server exited normally"), (1, "fastmcp not installed")),
        )
    ),
)
@click.option("--dry-run", is_flag=True, help="Print launch plan without starting.")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Suppress interactive confirmation (assume yes).",
)
def mcp_start(dry_run, yes):
    """Start the scitex-ui MCP server."""
    if dry_run:
        click.echo("DRY RUN — would start scitex-ui MCP server (stdio transport)")
        return
    try:
        from ._mcp.server import mcp as mcp_server
    except ImportError as e:
        click.secho(
            "Error: fastmcp not installed. pip install scitex-ui[mcp]",
            fg="red",
            err=True,
        )
        raise SystemExit(1) from e
    mcp_server.run()

@mcp_group.command(
    "doctor",
    **spec_command(
        cli_help(
            summary="Check MCP server health and dependencies.",
            description=(
                "Reports whether fastmcp is importable and whether the server "
                "loads, with the tool count as evidence it actually started.",
            ),
            examples=_examples(("{prog}", "")),
        )
    ),
)
def mcp_doctor():
    """Check MCP server health and dependencies."""
    click.echo("Checking MCP dependencies...")
    try:
        import fastmcp

        click.echo(f"  [OK] fastmcp {fastmcp.__version__}")
    except ImportError:
        click.echo("  [!!] fastmcp not installed")
        click.echo("    Install with: pip install scitex-ui[mcp]")
        return

    try:
        from ._mcp.server import mcp as mcp_server
        import asyncio

        tool_count = len(asyncio.run(mcp_server.list_tools()))
        click.echo(f"  [OK] MCP server loaded ({tool_count} tools)")
    except Exception as e:
        click.echo(f"  [!!] MCP server error: {e}")
        return

    click.echo()
    click.echo("MCP server is ready.")
    click.echo("Run with: scitex-ui mcp start")

@mcp_group.command(
    "list-tools",
    **spec_command(
        cli_help(
            summary="List available MCP tools.",
            description=(
                "Verbosity is cumulative: -v adds each tool's first "
                "description line, -vv the full description.",
            ),
            examples=_examples(
                ("{prog}", "names only"),
                ("{prog} -vv", "names with full descriptions"),
                ("{prog} --json", "machine-readable"),
            ),
        )
    ),
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbosity: -v sig, -vv +desc, -vvv full.",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def mcp_list_tools(verbose, as_json):
    """List available MCP tools."""
    try:
        from ._mcp.server import mcp as mcp_server
    except ImportError as e:
        raise click.ClickException(
            f"fastmcp not installed. pip install scitex-ui[mcp]\n{e}"
        ) from e

    import asyncio

    tools = asyncio.run(mcp_server.list_tools())

    if as_json:
        import json

        output = {
            "total": len(tools),
            "tools": [
                {"name": t.name, "description": t.description or ""} for t in tools
            ],
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.secho(f"scitex-ui MCP: {len(tools)} tools", fg="cyan", bold=True)
    click.echo()
    for tool in sorted(tools, key=lambda t: t.name):
        if verbose == 0:
            click.echo(f"  {tool.name}")
        else:
            click.echo(f"  {tool.name}")
            if tool.description:
                desc = (
                    tool.description.split("\n")[0].strip()
                    if verbose == 1
                    else tool.description.strip()
                )
                click.echo(f"    {desc}")
            click.echo()

@mcp_group.command(
    "show-installation",
    **spec_command(
        cli_help(
            summary="Show MCP server installation instructions.",
            description=(
                "Prints the mcpServers entry to add to a client config, or the "
                "same config as JSON for scripted installation.",
            ),
            examples=_examples(
                ("{prog}", ""),
                ("{prog} --json", "emit just the config block"),
            ),
            see_also=("mcp start", "mcp doctor"),
        )
    ),
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def mcp_show_installation(as_json):
    """Show MCP server installation instructions."""
    import json as json_mod

    config = {
        "mcpServers": {
            "scitex-ui": {
                "command": "scitex-ui",
                "args": ["mcp", "start"],
            }
        }
    }
    if as_json:
        click.echo(json_mod.dumps({"success": True, "config": config}, indent=2))
    else:
        click.secho("MCP Server Installation", fg="cyan", bold=True)
        click.echo()
        click.echo("Add to your Claude Code settings (~/.claude/settings.json):")
        click.echo()
        click.echo(json_mod.dumps(config, indent=2))
        click.echo()
        click.echo("Or start manually:")
        click.echo("  scitex-ui mcp start")

# Deprecation redirect: mcp installation -> mcp show-installation
@mcp_group.command(
    "installation",
    hidden=True,
    context_settings={"ignore_unknown_options": True},
    **spec_command(
        cli_help(
            summary="(deprecated) Renamed to `show-installation`.",
            description=(
                "Kept as a hidden command so the old invocation fails with a "
                "named redirect rather than click's generic 'No such command'.",
            ),
            examples=_examples(
                ("{prog}", "always exits 2; use `mcp show-installation`"),
            ),
            exit_codes=((2, "always — this alias never succeeds"),),
            see_also=("mcp show-installation",),
        )
    ),
)
@click.pass_context
def mcp_installation_deprecated(ctx):
    """(deprecated) Renamed to `show-installation`."""
    click.echo(
        "error: `scitex-ui mcp installation` was renamed to "
        "`scitex-ui mcp show-installation`.\n"
        "Re-run with: scitex-ui mcp show-installation",
        err=True,
    )
    ctx.exit(2)

main.add_command(mcp_group, "mcp")

# -- Introspection ------------------------------------------------------
@main.command(
    "list-python-apis",
    **spec_command(
        cli_help(
            summary="List public Python APIs in scitex-ui.",
            description=(
                "Reads `scitex_ui.__all__`, so it reports the surface the "
                "package actually exports rather than everything importable.",
            ),
            examples=_examples(
                ("{prog}", "names only"),
                ("{prog} -vv", "names with signatures"),
                ("{prog} --json", "machine-readable"),
            ),
        )
    ),
)
@click.option("-v", "--verbose", count=True, help="-v names, -vv +sigs, -vvv +docs")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_python_apis(verbose, as_json):
    """List public Python APIs in scitex-ui."""
    import inspect

    import scitex_ui

    names = sorted(getattr(scitex_ui, "__all__", []))
    apis = []
    for name in names:
        obj = getattr(scitex_ui, name, None)
        if obj is None:
            continue
        entry = {"name": name, "type": type(obj).__name__}
        if callable(obj):
            try:
                entry["signature"] = str(inspect.signature(obj))
            except (TypeError, ValueError):
                pass
        doc = inspect.getdoc(obj) or ""
        if doc:
            entry["doc"] = doc.strip().split("\n")[0]
        apis.append(entry)

    if as_json:
        import json as _json

        click.echo(_json.dumps({"module": "scitex_ui", "apis": apis}, indent=2))
        return

    click.secho("scitex_ui Python APIs", fg="cyan", bold=True)
    for api in apis:
        sig = api.get("signature", "")
        click.echo(f"  {click.style(api['name'], fg='green')}{sig}")
        if verbose >= 2 and api.get("doc"):
            click.echo(f"    {api['doc']}")

# Wire shared subcommands from scitex-dev
try:
    from scitex_dev.cli import docs_click_group, skills_click_group

    main.add_command(docs_click_group(package="scitex-ui"))
    main.add_command(skills_click_group(package="scitex-ui"))
except ImportError:
    pass


# EOF


# audit §4 — inject version into root --help
try:
    from importlib.metadata import version as _v

    main.help = f"scitex-ui (v{_v('scitex-ui')}) — " + (main.help or "").lstrip()
except Exception:
    pass

# §13 vs §1a — TWO DOCTRINES ASK FOR OPPOSITE THINGS, and this block is where
# they meet. Both are quoted rather than paraphrased, because the resolution
# only makes sense if you can see that neither was ignored.
#
#   §1a, 03_required-introspection-commands.md:98-104 —
#     "If the package ships `_skills/<pkg>/`, `<cli> skills` exists as a group
#      with `list`, `get`, and `install` subcommands. SELF-CONTAINED (no
#      scitex-dev runtime dep) so users can introspect bundled skills without
#      discovering the ecosystem-wide tooling first."
#
#   §13, 20_dev-commands.md — `skills` is one of SIX FIXED verbs that mount
#     under `dev`. The doctrine is explicit that the six NAMES are fixed even
#     though the verbs inside each are not.
#
# So §1a wants `scitex-ui skills` to exist and §13 wants it gone from top level.
#
# THE AUDITOR'S HINT DOES NOT WORK HERE. It offers
# `scitex_dev.ecosystem.deprecated_alias()`, which imports scitex-dev — and
# scitex-dev is this package's OPTIONAL [cli] extra (pyproject `[project.
# optional-dependencies] cli`). Routing the §1a-mandated command through it
# would hand that command a scitex-dev runtime dependency and break it for
# every install without the extra, which is the exact thing §1a's
# "self-contained" clause exists to prevent. The hint is right about the SHAPE
# and wrong about the MECHANISM, so the alias below is plain click.
#
# THE FLEET ALREADY SOLVED THIS, one line away in §1a's own file (:23), for
# `list-python-apis`: "the legacy top-level mount stays as a Phase W
# warn-forward alias during migration". Same collision, same answer —
# canonical under `dev`, legacy top level kept and warning.
from ._skills import skills_group as _skills_group


class _WarnForwardMixin:
    """A Phase W alias: works exactly as before, says where it moved.

    Deliberately NOT a silent alias. A rename nobody is told about is
    discovered when it is REMOVED, which is the worst possible moment; the
    point of a Phase W window is that the warning arrives while both spellings
    still work.

    The warning goes to STDERR (§14) so it can never corrupt `--json` output
    being piped into something — that is the difference between a migration
    aid and the breakage it exists to avoid.

    A MIXIN rather than a base class because the base has to be chosen at
    import time: `SpecGroup` when scitex-dev is importable (so §4b's help-spec
    coverage sees a spec), plain `click.Group` when it is not (so §1a's
    self-contained rule still holds without the optional [cli] extra). Writing
    it as a mixin keeps ONE copy of the warning logic across both.
    """

    _canonical = ""
    _removed_in = ""

    def invoke(self, ctx):
        click.echo(
            f"DEPRECATED: `{ctx.command_path}` has moved to `{self._canonical}` "
            f"and this spelling is removed in scitex-ui {self._removed_in}. "
            f"Update to `{self._canonical}`; the two behave identically today.",
            err=True,
        )
        return super().invoke(ctx)


@click.group(name="dev", **spec_group(_DEV_HELP))
def dev_group():
    """Self-maintenance surfaces (§13). Group only — never takes an argument."""


# CANONICAL (§13).
dev_group.add_command(_skills_group, name="skills")
main.add_command(dev_group, name="dev")

# LEGACY (§1a), warn-forward. Shares the canonical group's subcommands rather
# than re-declaring them, so the two spellings cannot drift apart — a copy
# would be a second implementation, and the one that is not exercised is the
# one that rots.
_alias_kwargs = spec_group(_SKILLS_ALIAS_HELP)
_alias_base = _alias_kwargs.pop("cls", click.Group)
_WarnForwardGroup = type(
    "_WarnForwardGroup", (_WarnForwardMixin, _alias_base), {}
)

_skills_alias = _WarnForwardGroup(
    name="skills",
    commands=_skills_group.commands,
    **_alias_kwargs,
)
_skills_alias._canonical = "scitex-ui dev skills"
_skills_alias._removed_in = "0.20.0"
main.add_command(_skills_alias, name="skills")

# UI-101..105 component-usage lint walker — `scitex-ui lint <path>`.
# Plugin entry-point (`scitex_dev.linter.plugins`) handles RULE registration;
# this subcommand handles ACTIVE SCAN of .css/.html/.tsx files that the
# in-tree scitex-dev checker (Python-AST-only) doesn't cover.
from ._linter._cli import lint as _lint_command

main.add_command(_lint_command, name="lint")

try:
    from scitex_dev._cli._completion import attach_shell_completion

    attach_shell_completion(main, prog_name="scitex-ui")
except Exception:
    pass
