#!/usr/bin/env python3
"""Template context processors for scitex-ui.

Install in Django settings to expose scitex-ui flags to every template::

    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "scitex_ui.context_processors.element_inspector",
    ]
"""

from django.conf import settings


def element_inspector(request):
    """Expose whether the Alt+I element inspector should load.

    The inspector is a developer/QA tool, so it is gated:

    - Enabled when ``settings.DEBUG`` is true, or
    - Enabled for authenticated staff users in production.
    - ``settings.SCITEX_UI_ELEMENT_INSPECTOR`` (bool) overrides both.

    Safe default: if this processor is not installed the flag is simply
    absent (falsy) in templates, so ``_element_inspector.html`` renders
    nothing and the inspector never loads for end users.
    """
    enabled = bool(getattr(settings, "DEBUG", False))
    if not enabled:
        user = getattr(request, "user", None)
        enabled = bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_staff", False)
        )
    enabled = bool(getattr(settings, "SCITEX_UI_ELEMENT_INSPECTOR", enabled))
    return {"stx_element_inspector_enabled": enabled}
