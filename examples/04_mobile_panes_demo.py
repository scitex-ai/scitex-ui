#!/usr/bin/env python3
"""Write a standalone demo page for the mobile panes primitive.

    python examples/04_mobile_panes_demo.py

The panes are rendered by the real ``{% scitex_panes %}`` template tag; the
page inlines the shipped token and panes stylesheets plus ``js/app/panes.js``
so it opens from disk; it lands in this run's session directory
(``CONFIG.SDIR_RUN``). Resize below 640px (or use a phone) to get the tab bar.
``?theme=dark`` shows the dark tokens.
"""

from __future__ import annotations

import pathlib
import re

import django
import scitex_session as stx
from django.conf import settings

import scitex_ui

_TEMPLATE = """{% load scitex_panes %}
{% scitex_panes "demo" columns="240px minmax(0,1fr) 280px" %}
  {% scitex_pane "data" label="Data" icon="▦" order=1 %}
    <header class="demo-head" data-stx-pane-header><strong>Data</strong><button>Import</button></header>
    <div class="demo-body">
      <p>Rows from <code>measurements.csv</code>.</p>
      <div class="demo-rail" aria-label="columns">
        <span>time</span><span>voltage</span><span>current</span><span>temperature</span>
        <span>pressure</span><span>humidity</span><span>phase</span><span>trial</span>
      </div>
      <ul class="demo-list">{% for i in rows %}<li>trial {{ i }}</li>{% endfor %}</ul>
    </div>
  {% endscitex_pane %}
  {% scitex_pane "plot" label="Plot" icon="▲" order=2 %}
    <header class="demo-head" data-stx-pane-header><strong>Plot</strong><button>Export</button></header>
    <div class="demo-body">
      <div class="demo-types">
        <button data-type="line">Line</button><button data-type="scatter">Scatter</button>
        <button data-type="bar">Bar</button><button data-type="box">Box</button>
      </div>
      <div class="demo-canvas">plot preview</div>
    </div>
  {% endscitex_pane %}
  {% scitex_pane "settings" label="Settings" icon="◆" order=3 %}
    <header class="demo-head" data-stx-pane-header><strong>Settings</strong></header>
    <div class="demo-body">
      <details class="stx-acc" open><summary>Axis</summary>
        <div class="stx-acc__body"><label>X label <input value="time (s)"></label></div>
      </details>
      <details class="stx-acc"><summary>Legend</summary>
        <div class="stx-acc__body">Position, columns, frame.</div>
      </details>
      <details class="stx-acc"><summary>Export</summary>
        <div class="stx-acc__body">DPI, format, size.</div>
      </details>
    </div>
  {% endscitex_pane %}
{% endscitex_panes %}
"""

_PAGE_CSS = """
body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg-page); color: var(--text-primary); }
.demo-site-header { height: 48px; display: flex; align-items: center; padding: 0 16px;
  border-bottom: 1px solid var(--border-muted); background: var(--bg-surface); font-weight: 600; }
:root { --site-header-height: 49px; }
.stx-panes:not(.stx-panes--single) { height: calc(100vh - 49px); }
.stx-panes__pane { background: var(--bg-surface); border-right: 1px solid var(--border-muted); overflow: auto; }
.demo-head { display: flex; align-items: center; justify-content: space-between; min-height: 44px;
  padding: 0 12px; border-bottom: 1px solid var(--border-muted); }
.demo-head button, .demo-types button { min-height: 36px; padding: 0 12px; border-radius: 6px;
  border: 1px solid var(--border-default); background: var(--bg-page); color: var(--text-primary); font: inherit; }
.demo-body { padding: 12px; }
.demo-rail { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.demo-rail span { flex: none; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--border-muted); }
.demo-list { padding-left: 18px; line-height: 2; }
.demo-types { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.demo-canvas { display: grid; place-items: center; min-height: 260px; border: 1px dashed var(--border-default);
  border-radius: 6px; color: var(--text-muted); }
.stx-acc input { font: inherit; font-size: 16px; margin-left: 8px; background: var(--bg-page); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px; padding: 4px 8px; }
.stx-panes--single > .stx-panes__pane { border-right: 0; }
"""

_PAGE_JS = """
const theme = new URLSearchParams(location.search).get("theme");
if (theme) document.documentElement.setAttribute("data-theme", theme);
document.addEventListener("click", (event) => {
  const type = event.target.closest("[data-type]");
  if (type) document.querySelector(".demo-canvas").textContent = type.dataset.type + " plot";
});
"""


def _configure_django() -> None:
    if not settings.configured:
        settings.configure(
            USE_I18N=False,
            STATIC_URL="/static/",
            INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
            TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}],
        )
        django.setup()


def _inline_css(path: pathlib.Path) -> str:
    """The stylesheet with its relative @imports inlined."""
    text = path.read_text(encoding="utf-8")

    def expand(match: re.Match) -> str:
        return _inline_css((path.parent / match.group(1)).resolve())

    return re.sub(r'@import\s+"([^"]+)";', expand, text)


#: The two tags the demo drops, because it inlines both assets below.
#:
#: Anchored on the URL, NOT on the quoting. Django's {% static %} appends a
#: cache-busting query (".../panes.css?v=4d9422bced5f"), so a pattern that
#: requires the closing quote right after ".css" matches NOTHING — the page then
#: ships two references to files it never makes available. Measured 2026-09-17
#: in a browser at 1440x900 and 390x844: both 404 on every load of every theme,
#: and it is silent, because the inlined copies below still style and drive the
#: panes. Nothing on the page looks wrong; only the network log says so.
_DROP_INLINED_LINK = re.compile(r'<link[^>]*href="[^"]*panes\.css[^"]*"[^>]*>')
_DROP_INLINED_SCRIPT = re.compile(r'<script[^>]*src="[^"]*panes\.js[^"]*"[^>]*>\s*</script>')


def build() -> str:
    """The demo page as one HTML string."""
    _configure_django()
    from django.template import Context, engines

    static = pathlib.Path(scitex_ui.get_static_dir())
    panes = engines["django"].from_string(_TEMPLATE).template.render(Context({"rows": range(1, 31)}))
    tokens = _inline_css(static / "css" / "primitives" / "colors.css")
    tokens += _inline_css(static / "css" / "primitives" / "spacing.css")
    panes_css = (static / "css" / "app" / "panes.css").read_text(encoding="utf-8")
    panes_js = (static / "js" / "app" / "panes.js").read_text(encoding="utf-8")
    panes = _DROP_INLINED_LINK.sub("", panes)
    panes = _DROP_INLINED_SCRIPT.sub("", panes)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>scitex-ui mobile panes</title>"
        f"<style>{tokens}\n{panes_css}\n{_PAGE_CSS}</style>"
        f"<script>{_PAGE_JS}</script></head><body>"
        '<div class="demo-site-header">SciTeX demo</div>'
        f"{panes}"
        f'<script type="module">{panes_js}</script>'
        "</body></html>\n"
    )


@stx.session
def main(
    CONFIG=stx.INJECTED,
    logger=stx.INJECTED,
) -> int:
    """Write the demo page into this run's session directory."""
    output_file = pathlib.Path(CONFIG.SDIR_RUN) / "index.html"
    output_file.write_text(build(), encoding="utf-8")
    logger.info(f"wrote {output_file}")
    return 0


if __name__ == "__main__":
    main()
