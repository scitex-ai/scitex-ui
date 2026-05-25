"""Minimal CLI for scitex-ui — docs, skills, introspection.

Follows the same pattern as scitex-stats and scitex-app CLIs.
Every SciTeX package provides: docs, skills, mcp, introspect, list-python-apis.
"""

from __future__ import annotations

import sys

try:
    import click
except ImportError:

    def main():
        print(
            "ERROR: click not installed. pip install scitex-ui[cli]",
            file=sys.stderr,
        )
        raise SystemExit(1)

else:
    CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

    def _get_version() -> str:
        try:
            from importlib.metadata import version

            return version("scitex-ui")
        except Exception:
            return "0.0.0"

    @click.group(
        context_settings=CONTEXT_SETTINGS,
        invoke_without_command=True,
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
    @click.group(invoke_without_command=True)
    @click.pass_context
    def mcp_group(ctx):
        """MCP (Model Context Protocol) server commands."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @mcp_group.command("start")
    @click.option("--dry-run", is_flag=True, help="Print launch plan without starting.")
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="Suppress interactive confirmation (assume yes).",
    )
    def mcp_start(dry_run, yes):
        """Start the scitex-ui MCP server.

        \b
        Examples:
          scitex-ui mcp-group start
          scitex-ui mcp-group start --dry-run
        """
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

    @mcp_group.command("doctor")
    def mcp_doctor():
        """Check MCP server health and dependencies.

        \b
        Examples:
          scitex-ui mcp doctor
        """
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

    @mcp_group.command("list-tools")
    @click.option(
        "-v",
        "--verbose",
        count=True,
        help="Verbosity: -v sig, -vv +desc, -vvv full.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
    def mcp_list_tools(verbose, as_json):
        """List available MCP tools.

        \b
        Examples:
          scitex-ui mcp list-tools
          scitex-ui mcp list-tools -vv
        """
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

    @mcp_group.command("show-installation")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
    def mcp_show_installation(as_json):
        """Show MCP server installation instructions.

        \b
        Examples:
          scitex-ui mcp show-installation
        """
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
        "installation", hidden=True, context_settings={"ignore_unknown_options": True}
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
    @main.command("list-python-apis")
    @click.option("-v", "--verbose", count=True, help="-v names, -vv +sigs, -vvv +docs")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
    def list_python_apis(verbose, as_json):
        """List public Python APIs in scitex-ui.

        \b
        Example:
          $ scitex-ui list-python-apis
          $ scitex-ui list-python-apis -vv
          $ scitex-ui list-python-apis --json
        """
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

# audit-cli §1a — packages with _skills/ MUST expose
# `<cli> skills {list,get,install}`.
from ._skills import skills_group as _skills_group

main.add_command(_skills_group, name="skills")

try:
    from scitex_dev._cli._completion import attach_shell_completion

    attach_shell_completion(main, prog_name="scitex-ui")
except Exception:
    pass
