#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_shell_offers_a_way_out.py

"""An app mounted through the shell must have something to click to leave.

THE DEFECT THIS EXISTS FOR, measured by scitex-hub on live prod 2026-08-19 at
390x844, anonymous:

    /apps/storage/   header 0   nav 0   TOTAL ANCHOR ELEMENTS: 0   links to "/": 0
    /apps/cards/     header 0   nav 1   total anchors: 3           links to "/": 0

The sharp statement is not "the header is missing". `/apps/storage/` contained
NO ANCHOR ELEMENTS AT ALL — a visitor who landed there had nothing on the page
to click in order to leave. Browser-back worked; the page offered nothing.

THEIR CONTROL IS WHAT MAKES IT THIS PACKAGE'S DEFECT rather than one app's.
Cards mounts identically and extends the same shell. It has three links, but
they come from ITS OWN CONTENT — and decisively, links-to-root is 0 for BOTH.
So the shell supplies no route out to anything mounted through it; storage is
simply the app whose own content does not compensate.

Reproduced here against origin/develop before building anything: the shell
template contained 0 `<a>`, 0 `<header>`, 0 `<nav>` across 496 lines, with all
16 `href=` attributes belonging to `<link rel="stylesheet">`.

WHY THE FIX IS A SLOT AND NOT A HARDCODED LINK, which is what this file is
really guarding. Per the dual-mode contract (`_skills/scitex-ui/41_dual-mode-
mounting.md`) a STANDALONE app is mounted at `/`. A "back to launcher" link
pointing at `/` would therefore point at the app's own root — a self-link, not
an escape — in exactly the mode this shell is named for. Only a mounting
platform knows where its launcher is, so only it can say.

So the property is conditional in BOTH directions, and both are asserted below:

    given a destination  ->  a reachable route to it MUST exist
    given none           ->  NO such route may be invented

A test that only checked the first would pass on a shell that always renders a
link to `/`, which is the wrong fix.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# Resolved from THIS FILE, never from ``scitex_ui.__file__``: under a
# non-editable install the latter points into site-packages, so the guard would
# assert about a different tree than the branch under review. That is not
# hypothetical — it is what PR #152 fixed across 19 modules, after a guard was
# observed reporting `15 passed` or `3 failed` for the same commit depending on
# which directory pytest was invoked from.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TEMPLATE = (
    _REPO_ROOT
    / "src" / "scitex_ui" / "templates" / "scitex_ui" / "standalone_shell.html"
)
_CSS = _REPO_ROOT / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"

_LINK_CLASS = "stx-shell-launcher-link"


def _render(context: dict[str, object]) -> str:
    """Render the real shell template through Django, or skip.

    Rendering rather than pattern-matching the source is the point: a `{% if %}`
    that never fires and a block that is absent look identical to a regex, and
    "renders only when given a destination" is precisely the property at issue.
    """
    django = pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=False,
            INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
            STATIC_URL="/static/",
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "DIRS": [],
                    "OPTIONS": {"context_processors": []},
                }
            ],
            SCITEX_UI_AUTOWIRE_INSPECTOR=False,
        )
        django.setup()

    from django.template.loader import render_to_string

    return render_to_string("scitex_ui/standalone_shell.html", context)


def _anchors(html: str) -> list[str]:
    return re.findall(r"<a\b[^>]*>", html, flags=re.I)


def test_the_template_renders_at_all() -> None:
    """ANTI-VACUITY. Every assertion below is about what IS or IS NOT in the
    rendered page, and an empty render satisfies half of them for free.

    This is the rule scitex-hub asked be stated generally rather than merely
    applied, after a mobile touch-target audit of mine reported "0 undersized
    targets" — because all 32 interactive elements were `display:none`. A check
    whose measured population is zero must FAIL, not pass.
    """
    # Arrange
    context: dict[str, object] = {}
    # Act
    html = _render(context)
    # Assert
    assert len(html) > 2000, (
        f"shell rendered {len(html)} chars; the template is ~500 lines, so this "
        "is a broken render and no assertion about its contents means anything"
    )


def test_a_launcher_destination_produces_a_reachable_link() -> None:
    """GIVEN a destination, the page must offer a route to it."""
    # Arrange
    context: dict[str, object] = {
        "launcher": {"url": "/apps/store/", "label": "Apps"}
    }
    # Act
    html = _render(context)
    # Assert
    assert f'href="/apps/store/"' in html, (
        "shell_context(launcher=...) was supplied but the rendered page carries "
        "no link to it — which is the defect this guard exists for, with the "
        "destination now known instead of missing"
    )


def test_the_link_carries_the_supplied_label() -> None:
    """The label is the composer's, not this package's — it must survive."""
    # Arrange
    context: dict[str, object] = {
        "launcher": {"url": "/apps/store/", "label": "Apps"}
    }
    # Act
    html = _render(context)
    # Assert
    assert "Apps" in html, "the launcher label was dropped in rendering"


def test_no_launcher_means_no_invented_route() -> None:
    """GIVEN no destination, the shell must NOT invent one.

    This is the half that stops the wrong fix. A shell that always links to `/`
    would pass the give-it-a-destination test above and be WRONG for standalone
    apps, which are themselves mounted at `/` — the link would point at the
    page it is on.
    """
    # Arrange
    context: dict[str, object] = {}
    # Act
    html = _render(context)
    # Assert
    assert _LINK_CLASS not in html, (
        "the shell rendered a launcher link without being given a destination; "
        "a standalone app is mounted at '/' so any invented link is a self-link"
    )


def test_the_way_out_is_not_inside_a_pane() -> None:
    """The link must not live inside `.workspace-three-col`.

    Every pane is `display:none !important` below 768px — that media block IS
    the defect being fixed. An escape route placed inside the thing that
    disappears disappears with it, and the page would measure zero anchors on a
    phone exactly as prod did, while passing every other test in this file.
    """
    # Arrange
    html = _render({"launcher": {"url": "/apps/store/", "label": "Apps"}})
    # Act
    before, sep, _after = html.partition('id="workspace-three-col"')
    # Assert
    assert sep and _LINK_CLASS in before, (
        "the launcher link must be a direct child of <body>, BEFORE "
        "#workspace-three-col — inside it, the <=768px rules hide it along with "
        "every pane, which is the exact failure this guard exists to prevent"
    )


def test_the_link_is_styled_somewhere_in_the_shipped_css() -> None:
    """A link the package renders but never styles is a half-shipped feature.

    Not asserting on appearance — only that the class a consumer receives is
    known to the stylesheets they also receive. An unstyled anchor is still
    clickable, so this would not have shown up in the anchor-count measurement
    that started this.
    """
    # Arrange
    sheets = sorted(_CSS.rglob("*.css"))
    # Act
    styled_in = [p.name for p in sheets if _LINK_CLASS in p.read_text(errors="replace")]
    # Assert
    assert styled_in, (
        f".{_LINK_CLASS} is rendered by the shell but appears in none of the "
        f"{len(sheets)} shipped stylesheets"
    )
