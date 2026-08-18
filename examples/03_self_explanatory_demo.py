#!/usr/bin/env python3
"""Generate a single self-contained page that explains scitex-ui by showing it.

    python examples/03_self_explanatory_demo.py

The page lands in this run's session directory (``CONFIG.SDIR_RUN``),
alongside the logs, per the ecosystem example convention (PS-501/PS-503).

WHY THIS EXISTS, in the operator's words (Telegram, chat 8379369979, msg 3639,
2026-08-18T06:51:26Z, relayed by scitex-hub; translation mine, not his):

    「製品が紫、どうですかね、なんかよくわかってなくて、、
      サイテクスユーアイのデモアプリがあると良いですね、自己説明的な」

    "the product being purple, how about it, I don't really understand it ...
     a scitex-ui demo app would be good, a self-explanatory one"

BOTH HALVES ARRIVED AS ONE MESSAGE, and that is the design brief. He raised a
colour he cannot evaluate and asked for a self-explanatory demo IN THE SAME
BREATH. So this page is the answer to the purple question, and that constrains
it in a specific way:

  * it must NOT assert purple as the brand. Two responses would be wrong --
    picking a new colour for him, and defending the current one with theory.
  * the accent must be CHANGEABLE ON THE PAGE, so the comparison is his to make
    in ten seconds rather than a thing he takes on trust.
  * it must render the palette on REAL components in BOTH themes, because a
    brand colour cannot be judged from a hex value or from prose.

THE CATALOGUE IS GENERATED FROM THE REGISTRY, NOT HAND-WRITTEN. Every component
row comes from ``scitex_ui.list_components()`` / ``get_component()``, so the
page cannot claim a component that does not exist or miss one that does. A
hand-written gallery is a second source of truth that silently goes stale --
which is the same defect class this package spent 2026-08-18 fixing in its own
stylesheets, where a palette duplicated across two layers drifted and nothing
noticed.

SCOPE, agreed with scitex-app so we do not ship two overlapping demos:

    THIS      is a CATALOGUE -- "what is in scitex-ui, and what does it read".
              One page, no backend, no auth, no project skeleton.
    scitex-app is the TEMPLATE -- "how do I start an app". Layout, settings, the
              mount contract.

This file therefore deliberately does NOT show how to start a project. If a
reader asks that, the answer is a link to scitex-app, not another section here.
"""

from __future__ import annotations

import html
import json
import pathlib
import re

import scitex as stx

import scitex_ui

#: Read out of shell/theme.css at generation time rather than hardcoded here.
#: A demo that hardcodes the palette is exactly the second source of truth this
#: page exists to avoid.
_TOKEN_DECL = re.compile(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);", re.M)
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)

#: Candidate accents offered for live comparison. The FIRST is whatever the
#: package currently ships, read from the palette -- it is presented as one
#: option among several, not as the answer, which is the whole point.
_ALTERNATIVES = [
    ("teal", "#2e7070", "#6ab0b0"),
    ("green", "#3d7a5e", "#6ba89a"),
    ("blue", "#3e6080", "#7a9ab8"),
    ("amber", "#a07040", "#d4a87a"),
    ("crimson", "#8a4a5a", "#c08a9a"),
]


def _palette(css_dir: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    """(light, dark) token maps read from the shipped shell/theme.css."""
    text = _CSS_COMMENT.sub("", (css_dir / "shell" / "theme.css").read_text())
    light_src, _, dark_src = text.partition('[data-theme="dark"]')
    light = {m.group(1): m.group(2).strip() for m in _TOKEN_DECL.finditer(light_src)}
    dark = {m.group(1): m.group(2).strip() for m in _TOKEN_DECL.finditer(dark_src)}
    return light, dark


def _components() -> list[dict[str, str]]:
    rows = []
    for name in scitex_ui.list_components():
        meta = scitex_ui.get_component(name)
        rows.append(
            {
                "name": name,
                "version": getattr(meta, "version", ""),
                "description": getattr(meta, "description", ""),
                "css": getattr(meta, "css_file", "") or "",
                "ts": getattr(meta, "ts_entry", "") or "",
            }
        )
    return rows


def _swatches(light: dict[str, str], dark: dict[str, str]) -> str:
    """Every semantic token, rendered as its own colour, both themes side by side."""
    skip = ("--app-accent-",)  # shown in their own section
    rows = []
    for token in sorted(light):
        if token.startswith(skip) or not light[token].startswith("#"):
            continue
        lv, dv = light[token], dark.get(token, light[token])
        rows.append(
            f'<tr><td><code>{html.escape(token)}</code></td>'
            f'<td><span class="sw" style="background:{html.escape(lv)}"></span>'
            f'<code>{html.escape(lv)}</code></td>'
            f'<td><span class="sw" style="background:{html.escape(dv)}"></span>'
            f'<code>{html.escape(dv)}</code></td></tr>'
        )
    return "\n".join(rows)


def _catalogue(rows: list[dict[str, str]]) -> str:
    out = []
    for r in rows:
        ts = (
            f'<code>{html.escape(r["ts"])}</code>'
            if r["ts"]
            else '<span class="none">css only</span>'
        )
        out.append(
            f'<tr><td><strong>{html.escape(r["name"])}</strong>'
            f'<span class="ver">v{html.escape(r["version"])}</span></td>'
            f'<td>{html.escape(r["description"])}</td>'
            f'<td><code>{html.escape(r["css"])}</code><br>{ts}</td></tr>'
        )
    return "\n".join(out)


def build(css_dir: pathlib.Path) -> str:
    light, dark = _palette(css_dir)
    rows = _components()
    shipped_light = light.get("--accent", "#6d4cad")
    shipped_dark = dark.get("--accent", "#a371f7")
    alts = [("shipped", shipped_light, shipped_dark), *_ALTERNATIVES]
    return _TEMPLATE.format(
        n_components=len(rows),
        n_tokens=len(light),
        version=getattr(scitex_ui, "__version__", "?"),
        swatches=_swatches(light, dark),
        catalogue=_catalogue(rows),
        alternatives=json.dumps(alts),
        shipped_light=shipped_light,
        shipped_dark=shipped_dark,
    )


_TEMPLATE = """<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>scitex-ui — what is in it</title>
<style>
:root {{
  --accent: {shipped_light};
  --bg: #faf9f7; --surface: #f8f7f5; --fg: #333; --muted: #777; --line: #ddd;
}}
[data-theme="dark"] {{
  --accent: {shipped_dark};
  --bg: #0d1117; --surface: #161b22; --fg: #e6edf3; --muted: #8b949e; --line: #30363d;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
.wrap {{ max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 5rem; }}
h1 {{ font-size: 1.6rem; margin: 0 0 .25rem; }}
h2 {{ font-size: 1.1rem; margin: 2.5rem 0 .75rem; padding-bottom: .35rem;
     border-bottom: 2px solid var(--accent); }}
.lede {{ color: var(--muted); margin: 0 0 2rem; }}
.bar {{ position: sticky; top: 0; z-index: 5; background: var(--surface);
        border-bottom: 1px solid var(--line); padding: .6rem 1.25rem;
        display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }}
button {{ font: inherit; padding: .35rem .7rem; border-radius: 6px;
          border: 1px solid var(--line); background: var(--bg); color: var(--fg);
          cursor: pointer; }}
button.on {{ border-color: var(--accent); color: var(--accent); font-weight: 600; }}
.dot {{ width: .8rem; height: .8rem; border-radius: 50%; display: inline-block;
        margin-right: .35rem; vertical-align: -1px; }}
table {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
th, td {{ text-align: left; padding: .45rem .6rem; border-bottom: 1px solid var(--line);
          vertical-align: top; }}
th {{ color: var(--muted); font-weight: 600; }}
code {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .85em; }}
.sw {{ display: inline-block; width: 1.1rem; height: 1.1rem; border-radius: 4px;
       border: 1px solid var(--line); margin-right: .4rem; vertical-align: -3px; }}
.ver {{ color: var(--muted); font-size: .78em; margin-left: .4rem; }}
.none {{ color: var(--muted); font-style: italic; font-size: .85em; }}
.demo {{ display: flex; gap: .6rem; flex-wrap: wrap; align-items: center;
         padding: 1rem; background: var(--surface); border: 1px solid var(--line);
         border-radius: 8px; }}
.btn-primary {{ background: var(--accent); color: #fff; border-color: var(--accent);
                font-weight: 600; }}
.btn-ghost {{ color: var(--accent); border-color: var(--accent); }}
.badge {{ background: var(--accent); color: #fff; border-radius: 999px;
          padding: .1rem .55rem; font-size: .78rem; font-weight: 600; }}
.tile {{ border-left: 3px solid var(--accent); padding: .5rem .75rem;
         background: var(--bg); border-radius: 0 6px 6px 0; }}
a {{ color: var(--accent); }}
.scroll {{ overflow-x: auto; }}
.note {{ color: var(--muted); font-size: .85rem; margin-top: .5rem; }}
</style>
</head>
<body>

<div class="bar">
  <strong>scitex-ui {version}</strong>
  <button id="theme">◑ theme</button>
  <span style="flex:1"></span>
  <span style="color:var(--muted);font-size:.85rem">accent:</span>
  <span id="accents"></span>
</div>

<div class="wrap">
<h1>What is in scitex-ui</h1>
<p class="lede">
  {n_components} registered components, {n_tokens} semantic tokens.
  Everything below is read from the package at build time — the component list
  comes from the registry and the colours from the shipped stylesheet, so this
  page cannot drift from the library it describes.
</p>

<h2>The accent, applied</h2>
<p>Change it in the bar above and watch every element below move together.
  These are the surfaces a brand colour actually lands on.</p>
<div class="demo">
  <button class="btn-primary">Primary action</button>
  <button class="btn-ghost">Secondary</button>
  <button>Neutral</button>
  <span class="badge">badge</span>
  <div class="tile">an accented tile</div>
  <a href="#">a link</a>
</div>
<p class="note">
  The shipped value is one option here, not the answer. Compare it against the
  others in both themes before deciding whether it should stay.
</p>

<h2>Semantic tokens</h2>
<div class="scroll"><table>
<thead><tr><th>token</th><th>light</th><th>dark</th></tr></thead>
<tbody>
{swatches}
</tbody></table></div>

<h2>Components</h2>
<div class="scroll"><table>
<thead><tr><th>name</th><th>what it is</th><th>where it lives</th></tr></thead>
<tbody>
{catalogue}
</tbody></table></div>

<p class="note">
  This page is a catalogue: it answers "what is in scitex-ui". It deliberately
  does not answer "how do I start an app" — that is scitex-app's template.
</p>
</div>

<script>
const ALTS = {alternatives};
const root = document.documentElement;
let current = 0;

function apply() {{
  const [, lightV, darkV] = ALTS[current];
  const dark = root.dataset.theme === "dark";
  root.style.setProperty("--accent", dark ? darkV : lightV);
  [...document.querySelectorAll("#accents button")].forEach((b, i) =>
    b.classList.toggle("on", i === current));
}}

ALTS.forEach(([name, lightV, darkV], i) => {{
  const b = document.createElement("button");
  b.innerHTML = '<span class="dot" style="background:' + lightV + '"></span>' + name;
  b.onclick = () => {{ current = i; apply(); }};
  document.getElementById("accents").appendChild(b);
}});

document.getElementById("theme").onclick = () => {{
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  apply();
}};

apply();
</script>
</body>
</html>
"""


@stx.session
def main(
    CONFIG=stx.session.INJECTED,
    logger=stx.session.INJECTED,
) -> int:
    """Write the demo page into this run's session directory."""
    OUT = pathlib.Path(CONFIG.SDIR_RUN)

    css_dir = pathlib.Path(scitex_ui.get_static_dir()) / "css"
    if not (css_dir / "shell" / "theme.css").exists():
        # Fail loud and NAME THE PATH. A demo that silently emits an unthemed
        # page is the exact failure this package shipped for fourteen releases:
        # an undefined custom property is not an error, so the page renders
        # successfully and wrong.
        logger.error(f"no shell/theme.css under {css_dir}")
        return 1

    page = build(css_dir)
    output_file = OUT / "index.html"
    output_file.write_text(page, encoding="utf-8")

    logger.info(f"components : {len(scitex_ui.list_components())}")
    logger.info(f"css source : {css_dir}")
    logger.info(f"wrote      : {output_file} ({len(page):,} bytes)")
    return 0


if __name__ == "__main__":
    main()
