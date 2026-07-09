#!/usr/bin/env python3
"""scitex-ui Django middleware.

``ElementInspectorMiddleware`` is the zero-friction way to make the
element inspector (Alt+I / Ctrl+I visual debugging overlay) available in a
Django app. Add a single line to ``MIDDLEWARE`` and the inspector's
``<link>`` + ``<script>`` are injected into every ``text/html`` response —
no per-app context-processor registration and no per-template
``{% include "scitex_ui/_element_inspector.html" %}`` needed::

    MIDDLEWARE = [
        ...
        "scitex_ui.middleware.ElementInspectorMiddleware",
    ]

To equip **every** scitex GUI app in develop + staging, add the line to
the shared settings and set the gate::

    SCITEX_UI_ELEMENT_INSPECTOR = SCITEX_ENV in {"development", "staging"}

Gating is delegated to :func:`scitex_ui.context_processors.element_inspector_enabled`,
so the middleware and the (still-supported) context-processor + partial
path stay in lock-step. The middleware never raises into a response: any
injection error is swallowed so a debug tool can never break a page.
"""

from django.templatetags.static import static

from .context_processors import element_inspector_enabled


class ElementInspectorMiddleware:
    """Inject the element inspector into enabled HTML responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_inject(request, response)
        except Exception:
            # A debug/QA overlay must never break the actual response.
            pass
        return response

    def _maybe_inject(self, request, response):
        # Only rewrite non-streaming, un-encoded HTML documents.
        if getattr(response, "streaming", False):
            return
        if response.get("Content-Encoding"):
            return
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return
        if not element_inspector_enabled(request):
            return

        charset = response.charset or "utf-8"
        try:
            body = response.content.decode(charset, errors="ignore")
        except (AttributeError, UnicodeDecodeError):
            return

        # Respect an app that already wires the inspector via the partial.
        if "js/utils/element-inspector.js" in body:
            return

        idx = body.rfind("</body>")
        if idx == -1:
            return

        body = body[:idx] + self._snippet() + body[idx:]
        data = body.encode(charset)
        response.content = data
        if response.get("Content-Length") is not None:
            response["Content-Length"] = str(len(data))

    @staticmethod
    def _snippet() -> str:
        css = static("scitex_ui/css/utils/element-inspector.css")
        js = static("scitex_ui/js/utils/element-inspector.js")
        return (
            f'<link rel="stylesheet" href="{css}">'
            f'<script src="{js}" defer></script>\n'
        )
