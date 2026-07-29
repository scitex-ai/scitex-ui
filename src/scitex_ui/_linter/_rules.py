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

    UI107 = Rule(
        id="STX-UI107",
        severity="error",
        category=CATEGORY,
        message=(
            "root-anchored API path literal in client code — correct "
            "standalone, silently wrong once the app is mounted as a "
            "scitex-hub built-in under /apps/u/<module>/"
        ),
        suggestion=(
            "Join the path onto the mount prefix the server put in the page:\n"
            '  import { apiUrl } from "@scitex/ui/ts/_base";\n'
            '  await fetch(apiUrl("/api/items"));\n'
            "and have the view declare the prefix:\n"
            "  from scitex_ui.mount import mount_context\n"
            "  render(request, tpl, {..., **mount_context(request)})\n"
            "apiUrl() THROWS when the marker is absent rather than "
            "defaulting to '/', because a default works standalone and "
            "fails only embedded. Needs scitex-ui >= 0.13.0; see "
            "`scitex-ui skills get 41_dual-mode-mounting`."
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
        UI107.id: UI107,
    }


#: What this linter CANNOT see. Emitted on EVERY run, clean or not.
#:
#: A check whose output is indistinguishable from a complete one is the
#: defect this exists to prevent: "no violations found" reads as "nothing
#: is wrong" when it may mean "nothing was looked at". scitex-dev made
#: stating the gap in the EMITTED VERDICT a requirement rather than a
#: preference (2026-07-29) — not the docstring, not the card, the output.
#: Their own corpus does the same for unregistered rule categories.
#:
#: Every entry here is a property of the code in `_checker.py`, not a
#: guess. Add one whenever a rule's reach narrows.
COVERAGE_GAPS: tuple[tuple[str, str], ...] = (
    (
        "runtime-generated markup",
        "this is a static text scanner: elements created or populated at "
        "runtime by JS are never inspected. STX-UI106 in particular counts "
        "<option> tags in source, so a <select> filled from fetch() looks "
        "empty to it and will not be flagged however long it gets.",
    ),
    (
        "built output",
        "dist/ and build/ are skipped, so what a consumer actually ships is "
        "not scanned — only the sources it was built from.",
    ),
    (
        "HTML assembled in Python",
        "only .css/.html/.htm/.ts/.tsx/.js/.jsx are read. Markup built by "
        "string concatenation inside .py is invisible.",
    ),
    (
        "URLs built at runtime",
        "STX-UI107 matches a root-anchored path LITERAL. A URL assembled by "
        'concatenation (`"/" + kind + "/items"`) or read from config is not '
        "a literal and is not flagged, so a clean UI-107 run is not evidence "
        "an app is mount-safe. This is the same blind spot as STX-UI106 and "
        "the reason the mount reader THROWS at runtime: the static check "
        "cannot be the only gate.",
    ),
    (
        "comment/exemption detection is line-prefix based",
        "STX-UI107 skips a line whose first non-space characters are //, /*, "
        "* or <!--, and skips a line that also contains `apiUrl(` — because "
        "the correct fix, apiUrl(\"/api/x\"), contains the literal being "
        "flagged. Both tests are per-LINE, so a literal inside a block "
        "comment whose body does not start with * , or an apiUrl() call "
        "split across lines, will be judged wrongly. Measured 2026-07-30: "
        "both of scitex-ui's own two matches were documentation, one of "
        "them the docstring for apiUrl itself.",
    ),
)


def coverage_notice() -> str:
    """Render the always-emitted statement of what was NOT inspected."""
    lines = [
        "NOT EVERYTHING WAS INSPECTED — this verdict covers only what a "
        "static scan of the source can see:",
    ]
    lines += [f"  - {name}: {detail}" for name, detail in COVERAGE_GAPS]
    return "\n".join(lines)


__all__ = [
    "Rule",
    "UIViolation",
    "CATEGORY",
    "build_rules",
    "COVERAGE_GAPS",
    "coverage_notice",
]
