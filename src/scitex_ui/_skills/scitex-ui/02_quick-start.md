---
description: |
  [TOPIC] scitex-ui Quick Start
  [DETAILS] Smallest example — wire scitex-ui static assets into a Django app and mount the workspace shell.
tags: [scitex-ui-quick-start]
---

# Quick Start

## 1. Wire the Python side into Django

```python
# settings.py
import scitex_ui

STATICFILES_DIRS = [scitex_ui.get_static_dir()]
```

This exposes `ts/shell/`, `ts/app/`, `react/app/`, and `css/shell/` as
Django static URLs.

## 2. Render the workspace shell in a template

```html
<!-- templates/workspace.html -->
{% load static %}
<link rel="stylesheet" href="{% static 'scitex_ui/css/shell/shell.css' %}">

<div id="shell-root"></div>

<script type="module">
  import { initShell } from "{% static 'scitex_ui/ts/shell/index.ts' %}";

  initShell({
    root: document.getElementById("shell-root"),
    modules: ["fileTree", "toolbar", "viewer", "terminal", "chat"],
  });
</script>
```

`initShell` is the vanilla-TS entry point; no React required for the
shell itself.

## 3. (Optional) Mount a React app component

```tsx
// react/app/MyPanel.tsx
import { DataTable } from "@scitex-ui/react/DataTable";

export function MyPanel() {
  return <DataTable rows={...} columns={...} />;
}
```

## 4. Introspect components from Python

```python
import scitex_ui

scitex_ui.list_components()           # ["DataTable", "FileBrowser", ...]
scitex_ui.get_component("DataTable")  # metadata dict
```

## 5. CLI — MCP / docs / skills

```bash
scitex-ui mcp start
scitex-ui docs
scitex-ui skills list
```

## Next steps

- `04_cli-reference.md` — full `scitex-ui` subcommand surface
- `03_python-api.md` — Python API reference
- `30_shell-framework.md` — shell architecture
- `32_frontend-components.md` — React DataTable / FileBrowser / MediaViewer
- `34_frontend-components-theme.md` — CSS theming
