#!/usr/bin/env python3
"""{% scitex_project_picker %}: only project-scope apps render a picker."""

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        USE_I18N=True,
        LANGUAGE_CODE="en",
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
    )
    django.setup()

from django.template import Context, engines  # noqa: E402

PICKER = (
    "{% load scitex_project_picker %}"
    '{% scitex_project_picker provider_url="/api/projects/" current="alice/paper" %}'
)


def _render(context):
    return engines["django"].from_string(PICKER).template.render(Context(context))


def test_user_scope_app_renders_no_picker():
    # Arrange
    context = {"app_scope": "user"}
    # Act
    html = _render(context)
    # Assert
    assert html == ""


def test_app_without_declared_scope_renders_no_picker():
    # Arrange
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert html == ""


def test_project_scope_app_renders_the_picker_mount():
    # Arrange
    context = {"app_scope": "project"}
    # Act
    html = _render(context)
    # Assert
    assert 'data-stx-project-picker data-provider-url="/api/projects/"' in html


def test_project_scope_picker_carries_the_explicit_project():
    # Arrange
    context = {"app_scope": "project"}
    # Act
    html = _render(context)
    # Assert
    assert 'data-current="alice/paper"' in html


def test_unknown_scope_fails_loud():
    # Arrange
    context = {"app_scope": "projcet"}
    # Act
    render = lambda: _render(context)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        render()


# EOF
