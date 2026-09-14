API Reference
=============

.. automodule:: scitex_ui
   :members:
   :undoc-members:
   :show-inheritance:

Shell context and branding
--------------------------

The primary public surface. ``shell_context()`` builds the context a view hands
to ``standalone_shell.html``; everything a consumer configures about the shell —
panes, accent, favicon, language, and the launcher slot — is declared here.

.. automodule:: scitex_ui.branding
   :members:
   :undoc-members:
   :show-inheritance:

Mounting
--------

For a platform composing this package's apps under a prefix, and for a leaf that
must work both standalone and mounted.

.. automodule:: scitex_ui.mount
   :members:
   :undoc-members:
   :show-inheritance:

Django integration
------------------

Registered in a consumer's ``settings.py`` rather than called directly.

.. automodule:: scitex_ui.apps
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui.context_processors
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui.middleware
   :members:
   :undoc-members:
   :show-inheritance:

Translations
------------

A leaf app's djangojs catalog, embedded with ``{% load scitex_i18n %}{% scitex_js_catalog "<app package>" %}``
and read in TypeScript by ``gettext`` / ``ngettext`` / ``interpolate`` from ``ts/_base/gettext.ts``.

.. automodule:: scitex_ui.i18n
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui.templatetags.scitex_i18n
   :members:

Project scope
-------------

The project picker a project-scope app places in its own UI, fed by a provider of
the projects the user can access. An explicit project always beats the last visited one.

.. automodule:: scitex_ui.project_scope
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui.templatetags.scitex_project_picker
   :members:

Registry
--------

.. automodule:: scitex_ui._registry
   :members:
   :undoc-members:

Testing helpers
---------------

Contract assertions a CONSUMER runs in its own suite. Documented because these
are meant to be imported from outside this package.

.. automodule:: scitex_ui.testing
   :members:
   :undoc-members:
   :show-inheritance:

Components
----------

.. automodule:: scitex_ui._components._theme_provider
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui._components._app_shell
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui._components._status_bar
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui._components._file_browser
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: scitex_ui._components._package_docs_sidebar
   :members:
   :undoc-members:
   :show-inheritance:
