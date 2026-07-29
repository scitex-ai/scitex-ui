---
description: |
  [TOPIC] Dual-mode mounting — run the same app standalone AND as a scitex-hub built-in
  [DETAILS] The mount-prefix contract: scitex_ui.mount server-side, mountPrefix()/apiUrl() client-side, and why both refuse to guess a root mount.
tags: [scitex-ui-dual-mode-mounting]
---

# Dual-mode mounting

A SciTeX app runs at two different URLs and the code must not care which:

| Mode | Prefix |
|------|--------|
| standalone | `""` (mounted at `/`) |
| scitex-hub built-in | `/apps/u/<module_name>` |

Routing already spans both and needs nothing from you: `scitex_app.embed.scitex_urlpatterns` emits purely
relative patterns, so `include()` works under any prefix. What the **browser** never had was a way to learn
the prefix — so client code hardcoded `/api/...`, which is correct standalone and silently wrong embedded.

That is the whole bug this contract removes, and its shape is worth naming: **it passes every standalone test
and fails only once embedded.**

## The two halves

**Server — `scitex_ui.mount`.** Merge `mount_context(request, view_path=...)` into the context you render:

```python
from scitex_ui.branding import shell_context
from scitex_ui.mount import mount_context

def editor(request):                      # urls.py: path("editor/", editor)
    return render(request, "myapp/index.html", {
        **shell_context("Writer"),
        **mount_context(request, view_path="editor/"),
    })
```

`standalone_shell.html` includes `scitex_ui/_mount_marker.html` in its `<head>`, which renders
`<meta name="stx-mount" content="…">`. A GUI that owns its own layout can include that partial directly —
same as `_branding_head.html`, no shell adoption needed.

**Client — `@scitex/ui`.** Never build a URL by hand:

```ts
import { apiUrl, mountPrefix } from "@scitex/ui/ts/_base";

await fetch(apiUrl("/api/items"));   // "/api/items" standalone, "/apps/u/writer/api/items" embedded
```

`mountPrefix()` reads `<body data-api-base>` first (scitex-cards ships that spelling today), then
`<meta name="stx-mount">` (what the server half above emits, and what `scitex_app`'s `scitex_editor_page`
injects into built SPA documents).

## Three things that look like bugs and are the design

**1. Both halves THROW rather than defaulting to `/`.** `mountPrefix()` raises `MountPrefixMissingError`
when no marker is present; `mount_prefix()` raises `MountPrefixMismatch` when the declared route is not in
the URL. A default would be indistinguishable from a correct answer at the only moment it matters. Quoting
scitex-cards, who reached this independently: *"a missing marker is an integration bug, never a
silently-guessed root mount."*

**2. A root mount is `""`, not `"/"`,** so `f"{prefix}/api/x"` is well-formed in both modes. And the marker
is still emitted at root, with `content=""` — "mounted at root" and "nobody declared anything" must not
render identically, or the reader cannot tell them apart.

**3. You must pass `view_path` — there is deliberately no context processor.** `request.path` is the mount
prefix *plus* whatever route your view occupies, and only your view knows the latter because your view wrote
it in `urls.py`. A context processor would be silently correct for app-root views and silently wrong for
every other one, which is strictly worse than a raise.

`view_path` is forgiving about spelling: `"editor"`, `"/editor"` and `"editor/"` are the same. It is
**not** forgiving about being wrong — a route that is not a trailing segment of `request.path` raises.

## Two derivations that do not work

- **`request.path_info`** has `SCRIPT_NAME` stripped — that is exactly the prefix you are trying to read.
  Use `request.path`. This one is easy to get backwards and, again, fails only when embedded.
- **`request.path` minus `resolver_match.route`** looks right and is not: under `include()`, `route` is the
  FULL concatenated pattern, so the subtraction yields `"/"`. Measured and rejected by scitex-app.

## If you do nothing

You get no marker, and any client code calling `mountPrefix()` throws immediately. That is intended: loud,
instant, and identical in both modes. Existing apps that never call it are unaffected.
