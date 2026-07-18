#!/usr/bin/env python3
"""Tests for the shared GUI branding convention and how the shell renders it.

The shell assertions render the real ``standalone_shell.html`` rather than
grepping it, because the defects these guard against (missing favicon,
hardcoded dark theme, unset body font) were all only visible in the rendered
page.
"""

import re

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "DIRS": [],
            }
        ],
        DEFAULT_CHARSET="utf-8",
    )
    django.setup()

from django.template.loader import render_to_string  # noqa: E402

from scitex_ui.branding import (  # noqa: E402
    FAVICON_STATIC_PATH,
    shell_context,
    shell_title,
)

_SHELL = "scitex_ui/standalone_shell.html"

# Accent names the shell reserves for its own state rather than for an app.
_RESERVED_ACCENTS = {"color", "tint"}


def _render(context=None):
    return render_to_string(_SHELL, context or {})


def _css(relative_path):
    from scitex_ui import get_static_dir

    return (get_static_dir() / relative_path).read_text()


def _declared_accents():
    """Accent names declared as ``--app-accent-<name>`` tokens in theme.css."""
    css = _css("css/shell/theme.css")
    names = set(re.findall(r"--app-accent-([a-z0-9-]+)\s*:", css))
    return {n for n in names if not n.endswith("-tint")} - _RESERVED_ACCENTS


def _referenced_accents():
    """Accent tokens the sidebar's mapping rows actually reference.

    Keyed on ``var(--app-accent-<name>)`` rather than on the selector name,
    because alias rows are legitimate: ``[data-app-accent="vis"]`` groups with
    ``"visualizer"`` and points at the *visualizer* token, so it neither needs
    nor has a token of its own.
    """
    css = _css("css/shell/stx-shell-sidebar.css")
    names = set(re.findall(r"var\(--app-accent-([a-z0-9-]+)\)", css))
    return {n[: -len("-tint")] if n.endswith("-tint") else n for n in names} - (
        _RESERVED_ACCENTS
    )


# --- title convention -------------------------------------------------------


def test_shell_title_adds_the_brand_prefix():
    assert shell_title("Writer") == "SciTeX Writer"


def test_shell_title_is_idempotent_for_an_already_branded_name():
    assert shell_title("SciTeX Writer") == "SciTeX Writer"


def test_shell_title_degrades_to_the_bare_brand_for_a_blank_name():
    assert shell_title("   ") == "SciTeX"


def test_shell_context_exposes_the_branded_title_as_app_label():
    assert shell_context("Storage")["app_label"] == "SciTeX Storage"


def test_shell_context_omits_favicon_href_when_not_overridden():
    # Absent (not None), so it cannot shadow a value merged in earlier and the
    # shell falls through to the shared brand mark.
    assert "favicon_href" not in shell_context("Storage")


def test_shell_context_keeps_an_explicit_favicon_override():
    context = shell_context("Storage", favicon_href="/static/own.svg")

    assert context["favicon_href"] == "/static/own.svg"


# --- favicon ----------------------------------------------------------------


def test_shell_falls_back_to_the_shared_brand_favicon():
    html = _render({"app_label": "SciTeX Storage"})

    assert FAVICON_STATIC_PATH in html


def test_shell_uses_favicon_href_when_the_app_overrides_it():
    html = _render({"favicon_href": "/static/own.svg"})

    assert '<link rel="icon"\n              href="/static/own.svg" />' in html


def test_shared_favicon_asset_is_shipped_in_the_package():
    from scitex_ui import get_static_dir

    # get_static_dir() is the staticfiles root's scitex_ui/ dir, so the
    # namespaced FAVICON_STATIC_PATH is relative to its parent.
    asset = get_static_dir().parent / FAVICON_STATIC_PATH
    assert asset.is_file()


# --- theme ------------------------------------------------------------------


def test_shell_does_not_hardcode_a_resolved_theme():
    # Regression: <html data-theme="dark"> overrode a stored light preference.
    html = _render()

    assert 'data-theme="dark"' not in html


def test_shell_defaults_the_theme_to_dark_for_the_boot_script():
    html = _render()

    assert 'data-theme-default="dark"' in html


def test_shell_honours_an_explicit_light_theme_default():
    html = _render(shell_context("Storage", theme_default="light"))

    assert 'data-theme-default="light"' in html


def test_shell_loads_the_theme_boot_script_synchronously():
    # A defer/async here would paint the wrong theme first.
    html = _render()

    assert '<script src="/static/scitex_ui/js/shell/theme-boot.js"></script>' in html


# --- typography -------------------------------------------------------------


def test_shell_loads_the_typography_tokens():
    # Regression: without these the UA default wins and body text renders in
    # Times New Roman on every standalone GUI.
    html = _render()

    assert "scitex_ui/css/primitives/typography-vars.css" in html


# --- accent -----------------------------------------------------------------


def test_shell_sets_the_app_accent_when_one_is_given():
    html = _render(shell_context("Storage", accent="storage"))

    assert 'data-app-accent="storage"' in html


def test_shell_omits_the_app_accent_attribute_when_none_is_given():
    html = _render()

    assert "data-app-accent" not in html


def test_every_accent_token_is_referenced_by_a_mapping_row():
    # A token no row references is dead: apps set the attribute and nothing
    # lights up. `notebook` sat in that state until 0.7.0.
    assert _declared_accents() - _referenced_accents() == set()


def test_every_referenced_accent_token_is_declared():
    # The mirror failure: a row pointing at a var that was never declared
    # resolves to nothing, so the accent line silently disappears.
    assert _referenced_accents() - _declared_accents() == set()
