#!/usr/bin/env python3
"""Tests for the element-inspector gate + ElementInspectorMiddleware."""

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

def test_gate_on_in_debug():
    with override_settings(DEBUG=True):
        assert element_inspector_enabled(_Req()) is True


def test_gate_off_by_default():
    with override_settings(DEBUG=False):
        assert element_inspector_enabled(_Req()) is False


def test_gate_override_enables_without_debug():
    # The staging path: DEBUG False but the setting turns it on.
    with override_settings(DEBUG=False, SCITEX_UI_ELEMENT_INSPECTOR=True):
        assert element_inspector_enabled(_Req()) is True


def test_gate_override_false_beats_debug():
    with override_settings(DEBUG=True, SCITEX_UI_ELEMENT_INSPECTOR=False):
        assert element_inspector_enabled(_Req()) is False


def test_gate_staff_in_production():
    with override_settings(DEBUG=False):
        assert element_inspector_enabled(_Req(_User(True, True))) is True
        assert element_inspector_enabled(_Req(_User(True, False))) is False


# --- middleware --------------------------------------------------------

def test_middleware_injects_when_enabled():
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    with override_settings(DEBUG=True):
        out = _apply(resp)
    body = out.content.decode()
    assert "js/utils/element-inspector.js" in body
    assert "element-inspector.css" in body
    # injected before the closing body tag
    assert body.index("element-inspector.js") < body.index("</body>")


def test_middleware_skips_when_disabled():
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    with override_settings(DEBUG=False):
        out = _apply(resp)
    assert "element-inspector.js" not in out.content.decode()


def test_middleware_skips_non_html():
    resp = HttpResponse("{}", content_type="application/json")
    with override_settings(DEBUG=True):
        out = _apply(resp)
    assert "element-inspector.js" not in out.content.decode()


def test_middleware_no_double_inject_when_partial_present():
    html = (
        "<html><body>"
        '<script src="/static/scitex_ui/js/utils/element-inspector.js"></script>'
        "</body></html>"
    )
    resp = HttpResponse(html, content_type="text/html")
    with override_settings(DEBUG=True):
        out = _apply(resp)
    assert out.content.decode().count("js/utils/element-inspector.js") == 1


def test_middleware_updates_content_length():
    resp = HttpResponse("<html><body>hi</body></html>", content_type="text/html")
    resp["Content-Length"] = str(len(resp.content))
    with override_settings(DEBUG=True):
        out = _apply(resp)
    assert int(out["Content-Length"]) == len(out.content)


def test_middleware_no_body_tag_is_noop():
    resp = HttpResponse("no body tag here", content_type="text/html")
    with override_settings(DEBUG=True):
        out = _apply(resp)
    assert out.content.decode() == "no body tag here"
