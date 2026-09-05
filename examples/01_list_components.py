#!/usr/bin/env python3
"""List all registered scitex-ui components and their metadata.

Usage:
    python 01_list_components.py
"""

from pathlib import Path

import scitex_session as stx

import scitex_ui


@stx.session
def main(
    CONFIG=stx.INJECTED,
    logger=stx.INJECTED,
) -> int:
    """List every registered component and dump a summary to SDIR_RUN."""
    OUT = Path(CONFIG.SDIR_RUN)

    components = scitex_ui.list_components()
    logger.info(f"Registered components ({len(components)}):")

    lines = []
    for name in components:
        meta = scitex_ui.get_component(name)
        info = f"  {name} v{meta.version} — {meta.description}"
        logger.info(info)
        lines.append(info)

    output_file = OUT / "components.txt"
    output_file.write_text("\n".join(lines) + "\n")
    logger.info(f"Saved to {output_file}")

    return 0


if __name__ == "__main__":
    main()
