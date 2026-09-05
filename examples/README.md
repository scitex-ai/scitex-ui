# Examples

Demonstrations of `scitex-ui` functionality.

| Script | Description |
|--------|-------------|
| `00_run_all.sh` | Run every `NN_*.py` example and report PASS/FAIL |
| `01_list_components.py` | List registered UI components and their metadata |
| `02_workspace_components.py` | Inspect the workspace shell's component set |
| `03_self_explanatory_demo.py` | Generate a single self-contained page showing what is in the library |
| `quickstart.py` | Smallest useful call: registry + static/docs paths |

## Running

```bash
# Run all
bash examples/00_run_all.sh

# Run individually
python examples/01_list_components.py
```

## The demo page

`03_self_explanatory_demo.py` writes one standalone HTML file — no server, no
build step, no dependencies beyond `scitex_ui` itself:

```bash
python examples/03_self_explanatory_demo.py -o /tmp/scitex-ui.html
```

It renders the palette on real components in both themes, and lets you **swap
the accent colour on the page** to compare the shipped value against
alternatives. That is the point of it: a brand colour cannot be judged from a
hex value or from prose, only from a screen.

**Both the component list and the colours are read from the package at build
time** — the catalogue comes from `scitex_ui.list_components()` and the palette
from the shipped `shell/theme.css`. So the page cannot claim a component that
does not exist, miss one that does, or show a colour the library stopped using.
A hand-written gallery would be a second source of truth that goes stale
silently, which is the defect class this package spent 2026-08-18 removing from
its own stylesheets.

### Scope

This is a **catalogue** — it answers *"what is in scitex-ui, and what does it
read"*. It deliberately does **not** answer *"how do I start an app"*: that is
`scitex-app`'s template, and the boundary is agreed with them so the two do not
ship overlapping demos. If you came here to start a project, go there instead.
