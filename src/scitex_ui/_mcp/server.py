#!/usr/bin/env python3
"""MCP server for scitex-ui — skills and documentation via Model Context Protocol."""

from __future__ import annotations

import json as _json_mod

from fastmcp import FastMCP

mcp = FastMCP("scitex-ui")


def _json(obj):
    """Serialize to JSON string."""
    return _json_mod.dumps(obj, indent=2, default=str)


# =============================================================================
# Skills Tools
# =============================================================================


# §5 — skills introspection tools (per audit-mcp-tools convention)
@mcp.tool()
def ui_skills_list() -> str:
    """List the names of every skill page shipped by scitex-ui.

    Returns
    -------
        JSON string with `{"success": true, "package": "scitex-ui",
        "skills": ["01_python-api", "02_cli", ...]}`.
    """
    try:
        from pathlib import Path

        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-ui"
        names = sorted(p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md")
        return _json_mod.dumps(
            {"success": True, "package": "scitex-ui", "skills": names},
            indent=2,
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_skills_get(name: str) -> str:
    """Fetch the full Markdown content of one scitex-ui skill page.

    Args:
        name: Skill page name without `.md`, e.g. `01_python-api`.

    Returns
    -------
        JSON string with `{"success": true, "package": "scitex-ui",
        "name": <name>, "content": <markdown>}`, or an error envelope.
    """
    try:
        from pathlib import Path

        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-ui"
        target = skills_dir / f"{name}.md"
        if not target.exists():
            available = sorted(
                p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md"
            )
            return _json_mod.dumps(
                {
                    "success": False,
                    "error": f"unknown skill {name!r}; available: {available}",
                },
                indent=2,
            )
        return _json_mod.dumps(
            {
                "success": True,
                "package": "scitex-ui",
                "name": name,
                "content": target.read_text(encoding="utf-8"),
            },
            indent=2,
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


# =============================================================================
# Python API Parity Tools (§6)
# =============================================================================


@mcp.tool()
def ui_get_component(name: str) -> str:
    """Get metadata for a registered component by name.

    Args:
        name: Component name, e.g. ``app-shell``.

    Returns
    -------
        JSON string with component metadata, or ``{"success": false, ...}``
        if the component is not found.
    """
    try:
        from scitex_ui._registry import get_component

        meta = get_component(name)
        if meta is None:
            return _json_mod.dumps(
                {"success": False, "error": f"component {name!r} not found"},
                indent=2,
            )
        cls = meta
        result = {
            "name": cls.name,
            "version": cls.version,
            "description": cls.description,
            "ts_entry": cls.ts_entry,
            "css_file": cls.css_file,
        }
        return _json_mod.dumps({"success": True, "component": result}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_list_components() -> str:
    """List the names of every registered frontend component.

    Returns
    -------
        JSON string with ``{"success": true, "components": [...]}``.
    """
    try:
        from scitex_ui._registry import list_components

        names = list_components()
        return _json_mod.dumps(
            {"success": True, "components": names}, indent=2
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_get_static_dir() -> str:
    """Return the absolute path to scitex-ui's static asset directory.

    Returns
    -------
        JSON string with ``{"success": true, "path": "..."}``.
    """
    try:
        from scitex_ui import get_static_dir

        path = str(get_static_dir())
        return _json_mod.dumps({"success": True, "path": path}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_get_docs_path() -> str:
    """Return the absolute path to scitex-ui's bundled documentation directory.

    Returns
    -------
        JSON string with ``{"success": true, "path": "..."}``.
    """
    try:
        from scitex_ui import get_docs_path

        path = str(get_docs_path())
        return _json_mod.dumps({"success": True, "path": path}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


# =============================================================================
# Server Entry Point
# =============================================================================


def run_server(transport: str = "stdio") -> None:
    """Run the MCP server."""
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_server()


# EOF
