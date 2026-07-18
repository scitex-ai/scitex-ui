#!/usr/bin/env python3
"""Shared SciTeX GUI branding: tab title convention + brand favicon.

Before this module each tool hand-rolled its own tab branding, so the fleet
drifted: some tabs showed the generic browser globe, and titles read
"FigRecipe Editor" / "SciTeX Writer" / "default-project — SciTeX".

The convention is:

* **Title** — ``"SciTeX <Tool>"`` (SciTeX Writer, SciTeX Scholar, SciTeX
  FigRecipe, SciTeX Todo). :func:`shell_title` normalises a tool name into
  that form and is idempotent, so passing ``"SciTeX Writer"`` is also fine.
* **Favicon** — the shared brand mark at ``scitex_ui/img/scitex-favicon.svg``,
  rendered whenever a view supplies no ``favicon_href``.

Usage in a view::

    from scitex_ui.branding import shell_context

    def index(request):
        return render(request, "myapp/index.html", {
            **shell_context("Storage", accent="storage"),
            ...,
        })

**Adopting the shared mark means DELETING your workaround, not just
upgrading.** An existing ``favicon_href`` — or your own ``<link rel="icon">``
in ``extra_css`` — wins, deliberately: an app that wants its own mark must be
able to keep it. But that means upgrading alone changes nothing, and the tab
still shows the old icon. It renders *a* favicon, which is not the same as
rendering *the* mark, and nothing warns you. At 0.7.1 three of the four
shell-extending GUIs were in exactly that state. To adopt: remove the
``favicon_href`` key from your context, or delete the local link tag.

**The shell emits exactly ONE ``<link rel="icon">``.** Setting ``favicon_href``
while keeping your existing tag moves the duplicate rather than removing it.
Sized variants (``rel="icon" sizes="32x32"``) and ``apple-touch-icon`` cannot be
expressed here and belong in your own ``extra_css`` — the shell owns the single
primary icon, the app owns the rest.

**Not every GUI renders this shell.** These helpers assume
``standalone_shell.html``; a GUI that owns its own layout can still get the
mark via ``{% include "scitex_ui/_branding_head.html" %}`` in its own
``<head>``, with no shell adoption and no layout migration.
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

    **Why panes are declared rather than detected.** Two reasons.

    1. Apps were reaching into the shell's internals instead. scitex-writer hid
       these panes with a stylesheet targeting
       ``.workspace-three-col > .ws-ai-pane`` and siblings — private class names
       this package is free to rename, which would have broken them silently
       and invisibly to both sides. A declaration is an API the shell is
       obliged not to break; a stylesheet aimed at its DOM is not.
    2. "Collapse a pane with no content" would measure the wrong thing anyway.
       A pane filled by JS after mount has no content at render time either, so
       emptiness is uncorrelated with whether the pane matters. This is a
       property of client-side rendering, not a claim about any one app.

    Only the app knows which of its panes it uses, so the app says.

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
