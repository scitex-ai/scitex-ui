#!/usr/bin/env python3
"""Project selector component metadata."""

from .._registry import register_component


class ProjectSelector:
    """The standard project-picking pattern (compass L625).

    A dropdown that lists the user's projects, shows the current selection
    on the trigger, and emits ``stx-project-selector:change`` (bubbles,
    detail ``{id, name}``) when the selection changes.

    Presentational + behavioural: the DATA comes from the consuming app (it
    knows the user and their project permissions); this component owns the
    pattern — the markup, the BEM vocabulary, and the event contract.

    The generic combobox is a near-miss rather than a fit: it is search-first
    and value-based, built for long option lists. Projects are a short,
    ordered, identity-bearing list, so a plain dropdown with a visible
    current selection is the right shape.

    Options are real ``<button>``s, so keyboard operability (Tab, Enter,
    Space) comes from the platform instead of a hand-rolled key handler.

    CSS: scitex_ui/css/app/project-selector.css
    """

    name = "project-selector"
    version = "0.1.0"
    description = (
        "Standard project dropdown: lists projects, shows the current "
        "selection, emits stx-project-selector:change"
    )
    ts_entry = "scitex_ui/ts/app/project-selector/index"
    css_file = "scitex_ui/css/app/project-selector.css"
    # Pre-built ES-module sibling for consumers without a bundler step:
    # a browser executes the .js module directly where it cannot execute
    # the .ts. Mirrors the TS API (same exports). Rebuild command is in
    # the file banner.
    js_file = "scitex_ui/js/app/project-selector.js"


register_component(ProjectSelector.name, ProjectSelector)
