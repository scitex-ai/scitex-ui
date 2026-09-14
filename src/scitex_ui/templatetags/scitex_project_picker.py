#!/usr/bin/env python3
"""``{% scitex_project_picker %}``: the project picker an app places in its own UI.

    {% load scitex_project_picker %}
    {% scitex_project_picker scope="project" provider_url="/api/projects/" current=project_id %}

Renders nothing unless the app is project-scoped. ``scope`` defaults to the
``app_scope`` context variable (scitex-app's context processor), else "user".
``navigate`` (default ``?project={id}``) is where a pick goes; pass "" to only
emit ``stx-project-selector:change`` for the app to handle.
"""

from __future__ import annotations

from django import template
from django.template.loader import render_to_string

register = template.Library()

SCOPE_USER = "user"
SCOPE_PROJECT = "project"
DEFAULT_NAVIGATE = "?project={id}"


def is_project_scope(scope) -> bool:
    """True for "project"; False for "user" or empty; raises on anything else."""
    normalized = str(scope or SCOPE_USER).strip().lower()
    if normalized not in (SCOPE_USER, SCOPE_PROJECT):
        raise ValueError(f"app scope must be 'user' or 'project', got {scope!r}")
    return normalized == SCOPE_PROJECT


@register.simple_tag(takes_context=True)
def scitex_project_picker(
    context,
    provider_url: str = "",
    scope=None,
    current: str = "",
    navigate: str = DEFAULT_NAVIGATE,
    placeholder: str = "",
):
    if scope is None:
        scope = context.get("app_scope")
    if not is_project_scope(scope) or not provider_url:
        return ""
    return render_to_string(
        "scitex_ui/_project_picker.html",
        {
            "provider_url": provider_url,
            "current": current or "",
            "navigate": navigate,
            "placeholder": placeholder,
        },
    )


# EOF
