#!/usr/bin/env python3
"""Django app configuration for scitex-ui.

``ScitexUiConfig.ready()`` auto-wires the element inspector (the Alt+I
visual-debugging overlay) into the host project's settings, so every
scitex GUI app that lists ``scitex_ui`` in ``INSTALLED_APPS`` gets it in
develop/staging **without** hand-wiring middleware or a context processor.

This closes the copy-paste settings drift that silently left some apps
(scitex-writer, figrecipe) without Alt+I while others (scitex-todo) had it:
the shared shell already ``{% include %}``s the inspector partial, but the
partial no-ops unless the flag is produced by the context processor or the
middleware — a hidden, easy-to-forget per-app opt-in. Auto-wiring makes the
opt-in the default and template-independent.
"""

from django.apps import AppConfig

_MIDDLEWARE = "scitex_ui.middleware.ElementInspectorMiddleware"
_CONTEXT_PROCESSOR = "scitex_ui.context_processors.element_inspector"


def _ensure_middleware(settings) -> None:
    """Append :class:`ElementInspectorMiddleware` to ``settings.MIDDLEWARE``.

    No-op when ``MIDDLEWARE`` is unset or already contains the entry. The
    middleware is self-gating and injects into ``text/html`` responses, so
    it equips even apps that do not extend the shared shell.
    """
    middleware = getattr(settings, "MIDDLEWARE", None)
    if middleware is None or _MIDDLEWARE in middleware:
        return
    settings.MIDDLEWARE = [*middleware, _MIDDLEWARE]


def _ensure_context_processor(settings) -> None:
    """Append the ``element_inspector`` context processor to Django template
    engines that lack it (keeps the ``{% include %}`` partial path working).

    Skips non-Django backends (e.g. Jinja2) and engines without a
    ``context_processors`` list. The middleware de-dupes, so this is belt
    and suspenders rather than a second injection.
    """
    templates = getattr(settings, "TEMPLATES", None)
    if not templates:
        return
    for engine in templates:
        if "DjangoTemplates" not in engine.get("BACKEND", ""):
            continue
        options = engine.setdefault("OPTIONS", {})
        processors = options.get("context_processors")
        if processors is None or _CONTEXT_PROCESSOR in processors:
            continue
        options["context_processors"] = [*processors, _CONTEXT_PROCESSOR]


class ScitexUiConfig(AppConfig):
    name = "scitex_ui"
    verbose_name = "SciTeX UI Components"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Auto-wire the element inspector unless explicitly opted out.

        Runs once during ``django.setup()`` — before the middleware stack is
        loaded (``BaseHandler.load_middleware``) and before template engines
        are instantiated — so the appended entries take effect. The
        middleware is self-gating via
        :func:`scitex_ui.context_processors.element_inspector_enabled` (a
        no-op in production) and de-dupes against templates that already
        include the partial. Opt out with
        ``SCITEX_UI_AUTOWIRE_INSPECTOR = False``.
        """
        from django.conf import settings

        if not getattr(settings, "SCITEX_UI_AUTOWIRE_INSPECTOR", True):
            return
        _ensure_middleware(settings)
        _ensure_context_processor(settings)
