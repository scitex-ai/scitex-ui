#!/usr/bin/env python3
"""Guards for the bottom action bar (action-bar).

WHY THIS FILE EXISTS, and it is not symmetry with the other component contracts.

This primitive was extracted from two real phone implementations, and the two
requirements it carries are exactly the ones the extraction inventory measured as
being re-derived per app (card
ui-mobile-layout-primitives-extract-from-apps-20260914):

  1. THE BAR SITS ABOVE TWO OTHER THINGS. scitex-writer's implementation says it
     in a comment -- "Above the hub's site dock when there is one, and above the
     iOS home bar always: a fixed bar at bottom: 0 puts its buttons under both."
     Losing either term puts the buttons under the dock or under the gesture bar,
     and NOTHING ELSE FAILS when that happens: the bar still renders, still looks
     right in jsdom, and is simply unclickable on a real phone.

  2. THE RESERVATION GOES ON THE CONSUMER'S CONTAINER, NEVER ON THE PAGE. The
     launcher overlay shares this bottom edge and hub PR 923 section 4 forbids
     reserving a band there (tests/develop/test_launcher_overlay_contract.py
     enforces it for the overlay). A band on body/html/:root is a permanently
     shorter app surface: invisible on a wide screen, dead space on every phone.
     This file applies the SAME detector to the new stylesheet, so the rule
     survives being copied into a second file, and it carries controls in both
     directions per tests/develop/test_detectors_carry_controls.py.

The height itself is published by TypeScript and MEASURED rather than assumed, so
these guards assert the mechanism (a measured rect, one published custom
property) rather than a number that a translated label would invalidate.

One assertion per test, with the AAA markers on their own lines, because PA-307
section 3 requires it of every file in this directory.
"""

from __future__ import annotations

import re

import scitex_ui
from tests._checkout import css_dir, package_dir, static_dir

_CSS = css_dir() / "app" / "action-bar.css"
#: ``static_dir()`` is <pkg>/static/scitex_ui (NOT <pkg>/static) -- the same depth
#: note test_component_coverage.py carries. Appending "scitex_ui/" here would
#: double the segment and every lookup below would silently miss.
_TS_DIR = static_dir() / "ts" / "app" / "action-bar"
_JS = static_dir() / "js" / "app" / "action-bar.js"

#: Mirrors ``test_launcher_overlay_contract.py``: a padding/margin-bottom on the
#: page itself. Comments are stripped first (this stylesheet explains the rule it
#: obeys, and the explanation contains the words).
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_BAND_ON_PAGE = re.compile(
    r"([^{}]*(?:\bbody\b|\bhtml\b|:root)[^{}]*)\{([^{}]*?(?:padding|margin)-bottom\s*:[^{}]*)\}"
)

_MODULE_FILES = ("index.ts", "mount.ts", "auto-mount.ts", "types.ts", "_ActionBar.ts")


def _read(path) -> str:
    return path.read_text(encoding="utf-8")


def _stripped(css: str) -> str:
    return _COMMENT.sub("", css)


def _rule(selector: str) -> str:
    """The declaration block of ``selector`` in the shipped stylesheet."""
    match = re.search(rf"{re.escape(selector)}\s*\{{(.*?)\}}", _stripped(_read(_CSS)), re.S)
    assert match, f"no {selector} rule found in {_CSS}"
    return match.group(1)


def _bottom_offset() -> str:
    match = re.search(r"bottom\s*:\s*(.*?);", _rule(".stx-action-bar"), re.S)
    assert match, "the bar declares no bottom offset"
    return match.group(1)


# --------------------------------------------------------------------------- #
# 1. The bar clears both bottom obstacles.
# --------------------------------------------------------------------------- #
def test_the_bar_is_out_of_flow() -> None:
    """A bar in flow would push content instead of overlaying it."""
    # Arrange
    rule = _rule(".stx-action-bar")
    # Act
    fixed = "position: fixed" in rule
    # Assert
    assert fixed, "the bar must be position: fixed"


def test_the_bar_clears_the_dock() -> None:
    """Writer: "Above the hub's site dock when there is one"."""
    # Arrange
    offset = _bottom_offset()
    # Act
    clears_dock = "--site-dock-clearance" in offset
    # Assert
    assert clears_dock, f"the bar must sit above the hub's site dock: {offset}"


def test_the_bar_carries_a_zero_fallback_for_a_page_without_the_dock() -> None:
    """Without the hub stylesheet there is no dock, so 0 is right, not missing."""
    # Arrange
    offset = _bottom_offset()
    # Act
    falls_back = "0px" in offset
    # Assert
    assert falls_back, f"the dock clearance needs a 0px fallback: {offset}"


def test_the_bar_clears_the_gesture_bar() -> None:
    """Writer: "and above the iOS home bar always"."""
    # Arrange
    offset = _bottom_offset()
    # Act
    clears_gesture_bar = "--stx-safe-inset-bottom" in offset
    # Assert
    assert clears_gesture_bar, f"the bar must sit above the home indicator: {offset}"


def test_the_bar_stays_below_the_launcher_overlay() -> None:
    """The two share the bottom edge; the launcher is 10050."""
    # Arrange
    match = re.search(r"z-index\s*:\s*(\d+)", _rule(".stx-action-bar"))
    # Act
    z = int(match.group(1)) if match else 0
    # Assert
    assert 0 < z < 10050, f"the action bar must not outrank the launcher overlay; z={z}"


# --------------------------------------------------------------------------- #
# 2. The reservation is the consumer's, not the page's.
# --------------------------------------------------------------------------- #
def test_the_reservation_is_a_utility_the_consumer_applies() -> None:
    """One line in the consumer, and the last line of content stays reachable."""
    # Arrange
    rule = _rule(".stx-action-bar-space")
    # Act
    reserves_height = "padding-bottom" in rule
    # Assert
    assert reserves_height, "the space utility must reserve the bar's height"


def test_the_reservation_consumes_the_measured_height() -> None:
    """A second constant would drift from the bar the primitive measured."""
    # Arrange
    rule = _rule(".stx-action-bar-space")
    # Act
    uses_published_height = "--stx-action-bar-height" in rule
    # Assert
    assert uses_published_height, "the reservation must consume the measured height"


def test_the_reservation_clears_the_same_two_obstacles_as_the_bar() -> None:
    """Clear the bar but not the dock and the content still hides behind the dock."""
    # Arrange
    rule = _rule(".stx-action-bar-space")
    # Act
    clears_both = "--site-dock-clearance" in rule and "--stx-safe-inset-bottom" in rule
    # Assert
    assert clears_both, "the reservation must add the dock + gesture-bar offsets"


def test_no_rule_reserves_a_band_on_the_page() -> None:
    """The launcher overlay shares this edge and forbids a page-level band."""
    # Arrange
    css = _stripped(_read(_CSS))
    # Act
    reserved = _BAND_ON_PAGE.findall(css)
    # Assert
    assert reserved == [], f"no page-level bottom band in action-bar.css; found {reserved}"


def test_items_use_the_shared_touch_target_token() -> None:
    """One app's 44 and another's 38 is the defect this extraction removes."""
    # Arrange
    rule = _rule(".stx-action-bar__item")
    # Act
    shared_token = "--stx-touch-target-min" in rule
    # Assert
    assert shared_token, "bar controls must use the shared 44px token, not a literal"


# --------------------------------------------------------------------------- #
# 3. The height is measured and published, never assumed.
# --------------------------------------------------------------------------- #
def test_the_primitive_measures_the_bar() -> None:
    """A translated label or a two-item row is taller than any constant."""
    # Arrange
    source = _read(_TS_DIR / "_ActionBar.ts")
    # Act
    measures = "getBoundingClientRect" in source
    # Assert
    assert measures, "the published height must be MEASURED from the rendered bar"


def test_the_primitive_publishes_the_height_as_a_custom_property() -> None:
    """The stylesheet consumes it; nothing else may carry the number."""
    # Arrange
    source = _read(_TS_DIR / "_ActionBar.ts")
    # Act
    publishes = "setProperty" in source and "--stx-action-bar-height" in source
    # Assert
    assert publishes, "the measured height must be published on the container"


def test_the_primitive_never_publishes_on_the_page() -> None:
    """The same rule as the band detector, one layer up."""
    # Arrange
    source = _read(_TS_DIR / "_ActionBar.ts")
    # Act
    on_page = "documentElement" in source or "document.body" in source
    # Assert
    assert not on_page, "the reservation must never be published on body/html"


# --------------------------------------------------------------------------- #
# 4. Wiring: registered, declared, built.
# --------------------------------------------------------------------------- #
def test_the_component_is_registered() -> None:
    """An unregistered component is invisible to list_components()."""
    # Arrange
    name = "action-bar"
    # Act
    component = scitex_ui.get_component(name)
    # Assert
    assert component is not None, f"{name} is not in list_components()"


def test_the_component_declares_the_stylesheet() -> None:
    # Arrange
    component = scitex_ui.get_component("action-bar")
    # Act
    declared = getattr(component, "css_file", None)
    # Assert
    assert declared == "scitex_ui/css/app/action-bar.css", f"css_file is {declared}"


def test_the_component_declares_the_ts_entry() -> None:
    # Arrange
    component = scitex_ui.get_component("action-bar")
    # Act
    declared = getattr(component, "ts_entry", None)
    # Assert
    assert declared == "scitex_ui/ts/app/action-bar/index", f"ts_entry is {declared}"


def test_the_component_declares_the_bundle() -> None:
    # Arrange
    component = scitex_ui.get_component("action-bar")
    # Act
    declared = getattr(component, "js_file", None)
    # Assert
    assert declared == "scitex_ui/js/app/action-bar.js", f"js_file is {declared}"


def test_the_stylesheet_ships() -> None:
    # Arrange
    path = _CSS
    # Act
    shipped = path.is_file()
    # Assert
    assert shipped, f"missing {path}"


def test_the_bundle_ships() -> None:
    """A browser does not execute .ts, and this component ships no build step."""
    # Arrange
    path = _JS
    # Act
    shipped = path.is_file()
    # Assert
    assert shipped, f"missing {path}"


def test_the_bundle_keeps_its_page_global() -> None:
    """How a plain Django template mounts the primitive."""
    # Arrange
    source = _read(_JS)
    # Act
    exposes = "stxActionBar" in source
    # Assert
    assert exposes, "the pre-built bundle must keep exposing window.stxActionBar"


def test_the_package_directory_is_the_checkout() -> None:
    """A control on this file's own assumptions, in the launcher contract's spirit.

    These guards read FILES from the checkout while the component registry comes
    from the imported package. If package_dir() ever resolved elsewhere, every
    assertion above would quietly measure a different tree.
    """
    # Arrange
    package = package_dir()
    # Act
    is_package = package.name == "scitex_ui" and (package / "static").is_dir()
    # Assert
    assert is_package, f"package_dir() resolved to {package}"


# --------------------------------------------------------------------------- #
# Controls — one pair per detector, so a green above is neither blind nor
# inverted. Positive: the pattern matched a real instance. Negative: it declined
# a string literal. Tree scans count as neither direction.
# --------------------------------------------------------------------------- #
def test_the_module_directory_has_all_five_files() -> None:
    """A control for _MODULE_FILES: the declared tuple names real files."""
    # Arrange
    present = [name for name in _MODULE_FILES if (_TS_DIR / name).is_file()]
    # Act
    count = len(present)
    # Assert
    assert count == len(_MODULE_FILES), f"missing module files: {set(_MODULE_FILES) - set(present)}"


def test_the_band_detector_matches_a_page_level_reservation() -> None:
    # Arrange
    sample = "body:has(> .site-dock) { padding-bottom: var(--site-dock-clearance); }"
    # Act
    found = _BAND_ON_PAGE.search(sample)
    # Assert
    assert found is not None


def test_the_band_detector_declines_a_container_level_reservation() -> None:
    # Arrange
    sample = ".stx-action-bar-space { padding-bottom: var(--stx-action-bar-height); }"
    # Act
    found = _BAND_ON_PAGE.search(sample)
    # Assert
    assert found is None


def test_the_comment_stripper_removes_a_comment() -> None:
    # Arrange
    sample = "/* body { padding-bottom: 88px; } */ .a { color: red; }"
    # Act
    stripped = _COMMENT.sub("", sample)
    # Assert
    assert "padding-bottom" not in stripped


def test_the_comment_stripper_keeps_the_surrounding_rule() -> None:
    # Arrange
    sample = "/* body { padding-bottom: 88px; } */ .a { color: red; }"
    # Act
    stripped = _COMMENT.sub("", sample)
    # Assert
    assert "color: red" in stripped
