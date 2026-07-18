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


#: Panes an app may declare. See :func:`shell_context`'s ``panes`` parameter.
PANE_NAMES = ("ai", "files", "viewer")

#: What an app may declare a pane to BE. Declared, never inferred.
#:
#: ``"unused"``            the app does not use this pane at all — collapse it
#:                         and give the app's content the width back.
#: ``"client-populated"``  the pane IS used, but its content arrives after
#:                         mount, so it is legitimately empty at render time.
#: ``"used"``              the pane is populated server-side.
#:
#: Only ``"unused"`` changes the layout. The other two are equivalent today and
#: both mean "leave it alone"; they are distinct because they say different
#: things about the app, and a future change may care about the difference.
PANE_STATES = ("unused", "client-populated", "used")


def shell_context(
    tool: str,
    *,
    accent: str | None = None,
    favicon_href: str | None = None,
    theme_default: str = "dark",
    panes: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build a ``standalone_shell.html`` context.

    :param tool: tool name, with or without the ``SciTeX`` prefix.
    :param accent: value for the shell's ``data-app-accent`` (e.g. ``"storage"``);
        must have a mapping row in ``css/shell/stx-shell-sidebar.css``.
    :param favicon_href: explicit override. Left out, the shell falls back to the
        shared brand mark — which is what almost every tool should do. Note that
        supplying one means the shared mark never renders for your app.
    :param theme_default: theme used when the visitor has no stored preference.
        Dark by default; a stored preference always wins (see ``_theme_boot``).
    :param panes: what each pane IS, e.g. ``{"ai": "unused", "files": "unused"}``.
        Keys from :data:`PANE_NAMES`, values from :data:`PANE_STATES`. Omitted
        panes are left visible.

    **Why panes are declared rather than detected.** The obvious design is
    "collapse a pane with no content", and it is wrong: a pane populated by JS
    after mount has no content at render time either. scitex-writer's file tree
    is exactly that, so an emptiness check would have collapsed their primary
    working surface on every page load. Emptiness at render time is uncorrelated
    with whether a pane matters — only the app knows, so the app says.

    Opt-in for the same reason: forgetting to declare leaves the page exactly as
    it is today, while an opt-out default that guessed wrong would hide a
    working pane. The failure mode of forgetting must be invisible, not
    destructive.

    Keys are omitted rather than set to ``None`` so they cannot shadow a value
    a caller merged in earlier.

    :raises ValueError: on an unknown pane name or state. A typo must fail
        loudly here rather than silently leaving a pane visible, which would
        look identical to not having declared it at all.
    """
    context: dict[str, object] = {
        "app_label": shell_title(tool),
        "shell_theme_default": theme_default,
    }
    if accent:
        context["app_accent"] = accent
    if favicon_href:
        context["favicon_href"] = favicon_href
    if panes:
        for name, state in panes.items():
            if name not in PANE_NAMES:
                raise ValueError(
                    f"unknown pane {name!r}; expected one of {PANE_NAMES}"
                )
            if state not in PANE_STATES:
                raise ValueError(
                    f"unknown state {state!r} for pane {name!r}; "
                    f"expected one of {PANE_STATES}"
                )
        context["panes"] = dict(panes)
    return context
