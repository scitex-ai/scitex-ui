#!/usr/bin/env python3
"""Tests for ElementInspectorMiddleware and its gate."""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles"],
        DEFAULT_CHARSET="utf-8",
    )
    django.setup()

from django.http import HttpResponse  # noqa: E402
from django.test import override_settings  # noqa: E402

from scitex_ui.context_processors import element_inspector_enabled  # noqa: E402
from scitex_ui.middleware import ElementInspectorMiddleware  # noqa: E402

_JS = "js/utils/element-inspector.js"


class _User:
    def __init__(self, authenticated, staff):
        self.is_authenticated = authenticated
        self.is_staff = staff


class _Req:
    def __init__(self, user=None):
        self.user = user


def _apply(response, request=None):
    mw = ElementInspectorMiddleware(lambda req: response)
    return mw(request if request is not None else _Req())


# --- gate --------------------------------------------------------------

def test_gate_enabled_in_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is True


def test_gate_disabled_by_default():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is False


def test_gate_setting_enables_without_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False, SCITEX_UI_ELEMENT_INSPECTOR=True):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is True


def test_gate_setting_false_overrides_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True, SCITEX_UI_ELEMENT_INSPECTOR=False):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is False


def test_gate_staff_user_enabled():
    # Arrange
    req = _Req(_User(authenticated=True, staff=True))
    # Act
    with override_settings(DEBUG=False):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is True


def test_gate_non_staff_disabled():
    # Arrange
    req = _Req(_User(authenticated=True, staff=False))
    # Act
    with override_settings(DEBUG=False):
        enabled = element_inspector_enabled(req)
    # Assert
    assert enabled is False


# --- middleware --------------------------------------------------------

def test_injects_script_when_enabled():
    # Arrange
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert _JS in body


def test_injects_stylesheet_when_enabled():
    # Arrange
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert "element-inspector.css" in body


def test_injects_before_closing_body():
    # Arrange
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert body.index(_JS) < body.index("</body>")


def test_skips_when_disabled():
    # Arrange
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    # Act
    with override_settings(DEBUG=False):
        body = _apply(resp).content.decode()
    # Assert
    assert _JS not in body


def test_skips_non_html():
    # Arrange
    resp = HttpResponse("{}", content_type="application/json")
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert _JS not in body


def test_no_double_inject_when_already_present():
    # Arrange
    resp = HttpResponse(
        f'<html><body><script src="/static/scitex_ui/{_JS}"></script></body></html>',
        content_type="text/html",
    )
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert body.count(_JS) == 1


def test_updates_content_length():
    # Arrange
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    resp["Content-Length"] = str(len(resp.content))
    # Act
    with override_settings(DEBUG=True):
        out = _apply(resp)
    # Assert
    assert int(out["Content-Length"]) == len(out.content)


def test_noop_when_no_body_tag():
    # Arrange
    resp = HttpResponse("no body tag here", content_type="text/html")
    # Act
    with override_settings(DEBUG=True):
        body = _apply(resp).content.decode()
    # Assert
    assert body == "no body tag here"
