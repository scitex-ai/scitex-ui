#!/usr/bin/env python3
"""Template context processors for scitex-ui.

Install in Django settings to expose scitex-ui flags to every template::

    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "scitex_ui.context_processors.element_inspector",
    ]
"""

from django.conf import settings


def element_inspector_enabled(request=None) -> bool:
    """Return whether the element inspector should load for this request.

    Single source of truth for the gating, shared by the
    :func:`element_inspector` context processor and
    :class:`scitex_ui.middleware.ElementInspectorMiddleware`.

    Precedence:

    1. ``settings.SCITEX_UI_ELEMENT_INSPECTOR`` — if set (not ``None``), its
       boolean value wins. This is the knob deployments use to turn the
       inspector on in **develop and staging** and off in production
       (e.g. ``SCITEX_UI_ELEMENT_INSPECTOR = SCITEX_ENV in {"development",
       "staging"}`` in shared settings), independent of ``DEBUG``.
    2. ``settings.DEBUG`` — on for local development.
    3. Authenticated staff users — so it stays reachable in production for
       operators without exposing it to end users.
    4. Otherwise off.
    """
    override = getattr(settings, "SCITEX_UI_ELEMENT_INSPECTOR", None)
    if override is not None:
        return bool(override)
    if getattr(settings, "DEBUG", False):
        return True
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_staff", False)
    )


def element_inspector(request):
    """Expose whether the Alt+I / Ctrl+I element inspector should load.

    Sets ``stx_element_inspector_enabled`` for ``_element_inspector.html``.
    Gating is delegated to :func:`element_inspector_enabled`. Safe default:
    if this processor is not installed the flag is simply absent (falsy) in
    templates, so nothing is loaded.
    """
    return {"stx_element_inspector_enabled": element_inspector_enabled(request)}
