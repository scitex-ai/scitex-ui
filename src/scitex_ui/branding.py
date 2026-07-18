#!/usr/bin/env python3
"""Shared SciTeX GUI branding: tab title convention + brand favicon.

Every SciTeX tool GUI renders through ``scitex_ui/standalone_shell.html``.
Before this module each tool hand-rolled its own tab branding, so the fleet
drifted: some tabs showed the generic browser globe, and titles read
"FigRecipe Editor" / "SciTeX Writer" / "default-project — SciTeX".

The convention is:

* **Title** — ``"SciTeX <Tool>"`` (SciTeX Writer, SciTeX Scholar, SciTeX
  FigRecipe, SciTeX Todo). :func:`shell_title` normalises a tool name into
  that form and is idempotent, so passing ``"SciTeX Writer"`` is also fine.
* **Favicon** — the shared brand mark shipped at
  ``scitex_ui/img/scitex-favicon.svg``. The shell falls back to it whenever a
  view supplies no ``favicon_href``, so a tool gets correct branding by doing
  nothing. Pass ``favicon_href`` only to deliberately override it.

Usage in a view::

    from scitex_ui.branding import shell_context

    def index(request):
        return render(request, "myapp/index.html", {
            **shell_context("Storage", accent="storage"),
            ...,
        })

which yields ``app_label="SciTeX Storage"`` and, for apps that want it, the
``data-app-accent`` value for the shell's accent line.
"""

from __future__ import annotations

BRAND = "SciTeX"

#: Static path of the shared brand mark, relative to the staticfiles root.
FAVICON_STATIC_PATH = "scitex_ui/img/scitex-favicon.svg"


def shell_title(tool: str) -> str:
    """Return the tab title for ``tool`` in the ``"SciTeX <Tool>"`` convention.

    Idempotent: a name that already carries the brand prefix is returned
    unchanged, so callers can pass either ``"Writer"`` or ``"SciTeX Writer"``.
    An empty/blank name degrades to the bare brand rather than ``"SciTeX "``.
    """
    name = (tool or "").strip()
    if not name:
        return BRAND
    if name == BRAND or name.startswith(f"{BRAND} "):
        return name
    return f"{BRAND} {name}"


def shell_context(
    tool: str,
    *,
    accent: str | None = None,
    favicon_href: str | None = None,
    theme_default: str = "dark",
) -> dict[str, object]:
    """Build the branding half of a ``standalone_shell.html`` context.

    :param tool: tool name, with or without the ``SciTeX`` prefix.
    :param accent: value for the shell's ``data-app-accent`` (e.g. ``"storage"``);
        must have a mapping row in ``css/shell/stx-shell-sidebar.css``.
    :param favicon_href: explicit override. Left out, the shell falls back to the
        shared brand mark — which is what almost every tool should do.
    :param theme_default: theme used when the visitor has no stored preference.
        Dark by default; a stored preference always wins (see ``theme-boot.js``).

    Keys are omitted rather than set to ``None`` so they cannot shadow a value
    a caller merged in earlier.
    """
    context: dict[str, object] = {
        "app_label": shell_title(tool),
        "shell_theme_default": theme_default,
    }
    if accent:
        context["app_accent"] = accent
    if favicon_href:
        context["favicon_href"] = favicon_href
    return context
