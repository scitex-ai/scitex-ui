---
description: |
  [TOPIC] scitex-ui CLI Reference
  [DETAILS] Top-level subcommands of `scitex-ui` — docs, skills, mcp, list-python-apis (requires the [cli] extra).
tags: [scitex-ui-cli-reference]
---

# CLI Reference

`scitex-ui` is the entry point installed by
`pip install 'scitex-ui[cli]'` (the `[cli]` extra pulls click).

```text
scitex-ui [OPTIONS] COMMAND [ARGS]...
```

## Top-level options

| Flag                | Purpose                                              |
|---------------------|------------------------------------------------------|
| `-V / --version`    | Show the version and exit                            |
| `--help-recursive`  | Show help for all subcommands                        |
| `--json`            | Emit structured JSON output (where supported)        |
| `-h / --help`       | Show this message and exit                           |

## Configuration precedence

```
CLI flags  →  ./config.yaml  →  $SCITEX_UI_CONFIG
           →  ~/.scitex/ui/config.yaml  →  built-in defaults
```

## Commands

| Command            | Purpose                                              |
|--------------------|------------------------------------------------------|
| `docs`             | View package documentation (bundled Sphinx HTML)     |
| `skills`           | View package skills (workflow-oriented guides)       |
| `mcp`              | MCP server management (start / stop / status)        |
| `list-python-apis` | List the public Python API surface                   |

## Examples

```bash
scitex-ui docs                           # open bundled docs
scitex-ui skills list                    # list available skill leaves
scitex-ui skills get 02_quick-start      # show one leaf
scitex-ui mcp start                      # start the standalone MCP server
scitex-ui list-python-apis               # dump the public Python tree
scitex-ui --help-recursive | head -60    # full surface dump
```

## Frontend tooling

There is **no `scitex-ui` frontend CLI** — the TS/React sources are
consumed via the bundled static directory. Use your project's existing
JS toolchain (`npm` / `vite` / `webpack`) to bundle them. See
`02_quick-start.md` for the Django integration pattern.
