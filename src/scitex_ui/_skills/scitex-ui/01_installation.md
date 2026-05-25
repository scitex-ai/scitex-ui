---
description: |
  [TOPIC] scitex-ui Installation
  [DETAILS] pip install scitex-ui (Python registry+CLI) AND npm i to consume the TS/React frontend; smoke verify both sides.
tags: [scitex-ui-installation]
---

# Installation

`scitex-ui` is a **mixed Python + TypeScript/React** package. The Python
half ships the component registry, static-asset resolver, and CLI; the
frontend half (vanilla TS shell + React app components) is consumed via
the bundled static directory.

## Python side (registry + CLI + Django glue)

```bash
pip install scitex-ui
```

Optional CLI / MCP extras:

```bash
pip install 'scitex-ui[cli]'        # `scitex-ui` console script
pip install 'scitex-ui[mcp]'        # MCP tools for AI agents
```

## Frontend side (TS shell + React components)

The TypeScript sources live in
`<get_static_dir()>/ts/` and `react/`. Two consumption paths:

### A. Django static-asset auto-discovery (recommended)

```python
# settings.py
import scitex_ui
STATICFILES_DIRS = [scitex_ui.get_static_dir()]
```

Django will then serve `ts/shell/`, `ts/app/`, `react/app/`, and
`css/shell/` from your project.

### B. Bundle into your own app

If you build your own frontend with Vite/Webpack:

```bash
# in your app's package directory
npm install react react-dom monaco-editor   # peer deps only
```

Point your bundler at:

```js
import { initShell } from "<scitex_ui_static_dir>/ts/shell/index.ts";
import { DataTable } from "<scitex_ui_static_dir>/react/app/index.ts";
```

(The package is tagged `private` in `package.json` and is not published
to npm — it ships through the Python wheel's static directory.)

## Umbrella

```bash
pip install scitex            # also exposes import scitex.ui
```

`pip install scitex-ui` alone does NOT make `import scitex.ui` work —
install the umbrella for that form. See
`../../general/02_interface-python-api.md`.

## Verify

```bash
python -c "import scitex_ui; print(scitex_ui.__version__); print(scitex_ui.list_components())"
scitex-ui --help                  # if [cli] extra installed
```

Expected: a version string, a list of registered components, and the
CLI usage block.
