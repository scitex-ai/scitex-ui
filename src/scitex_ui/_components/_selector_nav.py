#!/usr/bin/env python3
"""SelectorNav component metadata."""

from .._registry import register_component


class SelectorNav:
    """Vertical icon+label navigation strip.

    Items, labels and a pinned footer section; icon size follows
    `--ui-nav-icon-size`. Originally scitex-cloud's selector-nav.

    CSS-only: no TypeScript entry. Apps own the active item.
    CSS: scitex_ui/css/app/selector-nav.css
    """

    name = "selector-nav"
    version = "0.1.0"
    description = "Vertical icon+label navigation strip with footer section"
    ts_entry = None  # CSS-only component
    css_file = "scitex_ui/css/app/selector-nav.css"


register_component(SelectorNav.name, SelectorNav)
