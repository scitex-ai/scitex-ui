#!/usr/bin/env python3
"""ContextMenu component metadata."""

from .._registry import register_component


class ContextMenu:
    """Right-click context menu surface with items, dividers and a danger variant.

    Positioned by the app; this supplies the surface, item states and
    separator styling only.

    CSS-only: no TypeScript entry. Apps own positioning and dismissal.
    CSS: scitex_ui/css/app/context-menu.css
    """

    name = "context-menu"
    version = "0.1.0"
    description = "Right-click context menu surface with items and dividers"
    css_file = "scitex_ui/css/app/context-menu.css"


register_component(ContextMenu.name, ContextMenu)
