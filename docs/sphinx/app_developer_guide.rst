App Developer Guide
===================

The app-developer guide for ``scitex-ui`` lives outside the sphinx tree
because the canonical copy is bundled with the pip package and
discoverable from the ``scitex-ui skills`` CLI.

Read it via one of:

* CLI: ``scitex-ui skills get frontend-components``
* MCP: ``skills_get(name="frontend-components")``
* Source: ``src/scitex_ui/skills/references/frontend-components.md``
* GitHub: `docs/APP_DEVELOPER_GUIDE.md
  <https://github.com/ywatanabe1989/scitex-ui/blob/main/docs/APP_DEVELOPER_GUIDE.md>`_

This stub exists so the sphinx ``toctree`` reference in
``docs/sphinx/index.rst`` resolves to a titled document (sphinx treats
``:caption: Contents`` toctree entries without a title as a warning,
which the CI escalates to an error).
