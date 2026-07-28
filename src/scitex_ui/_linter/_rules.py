"""Rule definitions for scitex-ui's UI-101..105 component-usage corpus.

Imported by both:
- :mod:`scitex_ui._linter_plugin` — the entry-point that registers the
  rules with scitex-dev's linter (visible via ``scitex-linter list-rules``).
- :mod:`scitex_ui._linter._checker` — the standalone CSS/HTML/TSX
  walker that actively flags violations.

Severity ramp note for UI-104: the rule starts as ``warning`` in scitex-ui
0.6.0 and is scheduled to flip to ``error`` in 0.7.0 (standard adoption
window). Plan migrations off shared-foundation CSS edits in the WARN window.
The flip is documented in the rule message and the doctrine MD; the version
gate is enforced at the rule-build site below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


# Try to import scitex-dev's canonical Rule dataclass. The plugin entry
# point requires it (so `scitex-linter list-rules` displays correctly),
# but a soft-import lets the standalone walker still produce violations
# when scitex-dev is not installed in the consumer's venv.
try:
    from scitex_dev.linter._rules._base import Rule  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised when scitex-dev absent

    @dataclass(frozen=True)
    class Rule:  # type: ignore[no-redef]
        """Soft-fallback Rule shape — mirrors scitex-dev's Rule when absent."""

        id: str
        severity: str
        category: str
        message: str
        suggestion: str
        requires: str = ""


@dataclass(frozen=True)
class UIViolation:
    """One concrete violation emitted by the scitex-ui walker.

    Distinct from scitex-dev's ``Issue`` (which is Python-AST-bound) — a
    ``UIViolation`` is file/line-bound and carries the source-of-truth
    Rule so consumers can format messages the same way the entry-point
    linter does.
    """

    rule: Rule
    path: str
    line: int
    col: int
    source_line: str = ""


# Public category — surfaces in the entry-point listing and shared by
# all 5 rules. Distinct from scitex-dev's "io"/"path"/"plot" categories
# so consumers can mute the UI corpus independently (``--disable UI`` etc.).
CATEGORY = "ui"


def build_rules() -> Mapping[str, Rule]:
    """Construct the rule corpus keyed by rule id.

    Returns
    -------
    Mapping[str, Rule]
        ``{"STX-UI101": Rule(...), ..., "STX-UI105": Rule(...)}``.
    """

    UI101 = Rule(
        id="STX-UI101",
        severity="warning",
        category=CATEGORY,
        message=(
            "`<select>` element without theme opt-in — native widget will "
            "render OS-default colours and break dark-theme cohesion"
        ),
        suggestion=(
            "Use scitex_ui.Dropdown instead. If a native <select> is required "
            "(printer dialog, legacy form), add `data-app-themed='true'` and "
            "ship a `body select { background: var(--bg-surface); color: "
            "var(--text-primary); border: 1px solid var(--border-default); }` "
            "rule. See _skills/scitex-ui/40_component-usage-doctrine.md."
        ),
        requires="scitex-ui",
    )

    UI102 = Rule(
        id="STX-UI102",
        severity="warning",
        category=CATEGORY,
        message=(
            "raw hex / rgb()/rgba() literal in app CSS — themes drift "
            "when colours are hard-coded instead of token-referenced"
        ),
        suggestion=(
            "Replace the literal with the matching theme token: "
            "var(--text-primary) / var(--text-secondary) / var(--bg-page) / "
            "var(--bg-surface) / var(--border-default) / "
            "var(--status-{success,warning,error,info}) / "
            "var(--app-accent-<your-app>). See _skills/scitex-ui/"
            "34_frontend-components-theme.md for the full token table."
        ),
        requires="scitex-ui",
    )

    UI103 = Rule(
        id="STX-UI103",
        severity="warning",
        category=CATEGORY,
        message=(
            "scitex-ui shell/primitive CSS rule signature appears in a "
            "consumer's static/<app>/ tree — a local copy of shared styling "
            "that will drift the moment scitex-ui ships a theme tweak"
        ),
        suggestion=(
            "Delete the local copy and import the scitex-ui stylesheet via "
            "<link rel='stylesheet' href=\"{% static 'scitex_ui/css/shell/"
            "theme.css' %}\">. Copies drift; imports stay synced."
        ),
        requires="scitex-ui",
    )

    UI104 = Rule(
        id="STX-UI104",
        severity="warning",  # → flip to "error" in scitex-ui 0.7.0
        category=CATEGORY,
        message=(
            "consumer-repo CSS modifies scitex_ui/css/shell/* or "
            "scitex_ui/css/primitives/* — these are the SHARED foundation "
            "of every SciTeX app (operator directive 13298). Severity "
            "flips warning → error in scitex-ui 0.7.0; migrate now."
        ),
        suggestion=(
            "Do not edit shared shell/primitive CSS from a consumer repo. "
            "If a token is missing, file an additive request against "
            "scitex-ui itself. See _skills/scitex-ui/40_component-usage-"
            "doctrine.md §UI-104."
        ),
        requires="scitex-ui",
    )

    UI105 = Rule(
        id="STX-UI105",
        severity="warning",
        category=CATEGORY,
        message=(
            "raw hex / rgb() literal inside a scrollbar rule — themes "
            "drift; scrollbar colours should reference workspace-border "
            "tokens via a consumer-local var indirection"
        ),
        suggestion=(
            "Define consumer-local scrollbar vars backed by workspace-border "
            "tokens:\n"
            "  :root { --scrollbar-thumb: var(--workspace-border-default);\n"
            "          --scrollbar-track: var(--workspace-bg-secondary); }\n"
            "  .my-app, .my-app * { scrollbar-color: var(--scrollbar-thumb) "
            "var(--scrollbar-track); }\n"
            "  .my-app ::-webkit-scrollbar-thumb { background: "
            "var(--scrollbar-thumb); }"
        ),
        requires="scitex-ui",
    )

    UI106 = Rule(
        id="STX-UI106",
        severity="warning",
        category=CATEGORY,
        message=(
            "long native `<select>` with no way to narrow it — a picker "
            "past a dozen options is unscannable, and the native widget "
            "offers only type-to-jump on the FIRST character"
        ),
        suggestion=(
            "Layer scitex-ui's fuzzy Combobox over it as a progressive "
            "enhancement — the <select> stays as the fallback:\n"
            '  <script type="module" '
            'src="{% static \'scitex_ui/js/app/combobox.js\' %}"></script>\n'
            "  if (window.STX && window.STX.Combobox) {\n"
            "    document.querySelectorAll('select.my-filter')\n"
            "      .forEach((el) => new window.STX.Combobox({ from: el }));\n"
            "  }\n"
            "Fuzzy is subsequence matching, so `sui` finds `scitex-ui`. "
            "Needs scitex-ui >= 0.12.1."
        ),
        requires="scitex-ui",
    )

    return {
        UI101.id: UI101,
        UI102.id: UI102,
        UI103.id: UI103,
        UI104.id: UI104,
        UI105.id: UI105,
        UI106.id: UI106,
    }


__all__ = ["Rule", "UIViolation", "CATEGORY", "build_rules"]
