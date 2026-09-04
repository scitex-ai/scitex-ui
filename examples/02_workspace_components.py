#!/usr/bin/env python3
"""Inspect workspace frame component metadata (theme, shell, browser, status).

Usage:
    python 02_workspace_components.py
"""

from pathlib import Path

import scitex_session as stx

import scitex_ui

WORKSPACE_COMPONENTS = [
    "theme-provider",
    "app-shell",
    "file-browser",
    "status-bar",
]


@stx.session
def main(
    CONFIG=stx.INJECTED,
    logger=stx.INJECTED,
) -> int:
    """Inspect the workspace frame component subset and persist a summary."""
    OUT = Path(CONFIG.SDIR_RUN)

    lines = []
    logger.info("Workspace Frame Components:")
    logger.info("=" * 50)

    for name in WORKSPACE_COMPONENTS:
        meta = scitex_ui.get_component(name)
        if meta is None:
            logger.info(f"  {name}: NOT REGISTERED")
            continue
        logger.info(f"  {name} v{meta.version}")
        logger.info(f"    {meta.description}")
        logger.info(f"    CSS: {meta.css_file}")
        logger.info(f"    TS:  {meta.ts_entry}")
        lines.append(f"{name} v{meta.version} — {meta.description}")

    output_file = OUT / "workspace_components.txt"
    output_file.write_text("\n".join(lines) + "\n")
    logger.info(f"Saved to {output_file}")

    return 0


if __name__ == "__main__":
    main()
