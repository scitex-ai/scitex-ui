---
description: |
  [TOPIC] scitex-ui Python API
  [DETAILS] Top-level public callables — list_components, get_component, get_static_dir, get_docs_path; Django integration pattern.
tags: [scitex-ui-python-api]
---

# Python API

Top-level public surface re-exported from `scitex_ui`. Most of the
package is TypeScript/React; the Python side is a thin registry +
static-asset resolver + Django glue.

## Public symbols

| Name                | Kind     | Purpose                                            |
|---------------------|----------|----------------------------------------------------|
| `__version__`       | str      | Installed package version                          |
| `list_components()` | function | Enumerate registered React components              |
| `get_component(n)`  | function | Get metadata for one component (e.g. `"DataTable"`) |
| `get_static_dir()`  | function | Absolute `Path` to the bundled static-asset root   |
| `get_docs_path()`   | function | Absolute `Path` to bundled Sphinx HTML docs        |

## Component registry

```python
import scitex_ui

scitex_ui.list_components()
# ['DataTable', 'FileBrowser', 'MediaViewer', ...]

meta = scitex_ui.get_component("DataTable")
meta["entry"]        # path inside react/app/
meta["peer_deps"]    # required peer npm deps
```

## Static asset resolution

```python
import scitex_ui
from pathlib import Path

root: Path = scitex_ui.get_static_dir()
# .../scitex_ui/static/scitex_ui
(root / "css" / "shell" / "shell.css").exists()    # True
(root / "ts" / "shell" / "index.ts").exists()      # True
(root / "react" / "app" / "DataTable").is_dir()    # True
```

Works for both pip-installed wheels and editable (`pip install -e .`)
installs.

## Django integration (one-liner)

```python
# settings.py
import scitex_ui
STATICFILES_DIRS = [scitex_ui.get_static_dir()]
```

## Bundled documentation

```python
import scitex_ui
docs_root = scitex_ui.get_docs_path()
# Open <docs_root>/index.html in a browser, or wire into your docs site.
```

## Not exposed

- React components are **not Python** objects — load them via the
  static URLs above and a JS bundler.
- The MCP tool layer is exposed under the umbrella `scitex` MCP server
  (see SKILL.md "MCP Tools" table) — not as direct Python callables.
