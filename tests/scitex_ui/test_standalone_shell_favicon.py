#!/usr/bin/env python3
"""Tests for the favicon_href context var in standalone_shell.html."""

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
                "OPTIONS": {},
            }
        ],
        DEFAULT_CHARSET="utf-8",
    )
    django.setup()

from django.template.loader import render_to_string  # noqa: E402

_TEMPLATE = "scitex_ui/standalone_shell.html"


def test_favicon_link_rendered_when_favicon_href_set():
    # Arrange
    context = {"app_label": "SciTeX Plot", "favicon_href": "data:image/svg+xml,%3Csvg/%3E"}
    # Act
    html = render_to_string(_TEMPLATE, context)
    # Assert
    assert '<link rel="icon" href="data:image/svg+xml,%3Csvg/%3E">' in html


def test_no_favicon_link_when_favicon_href_absent():
    # Arrange
    context = {"app_label": "SciTeX Plot"}
    # Act
    html = render_to_string(_TEMPLATE, context)
    # Assert
    assert '<link rel="icon"' not in html


def test_app_label_still_renders_in_title():
    # Arrange
    context = {"app_label": "SciTeX Plot", "favicon_href": "/static/icon.svg"}
    # Act
    html = render_to_string(_TEMPLATE, context)
    # Assert
    assert "<title>SciTeX Plot</title>" in html


# EOF
