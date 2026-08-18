#!/usr/bin/env python3
"""Per-app accent tokens live in the colors layer, and only there.

THE DEFECT, measured 2026-08-18 across scitex-ui and scitex-hub.

``--app-accent-<name>`` was defined in TWO layers — ``primitives/colors/*`` and
``shell/theme.css`` — and the two DISAGREED:

    only in shell/theme.css     comms, storage, todo
    only in primitives/colors/  apps
    in both, identical values    15 names

Which definition an adopter sees depends on which stylesheet they load, and an
adopter that loads only the primitives layer sees neither ``storage`` nor
``comms``. scitex-hub is exactly that adopter.

CONSEQUENCE, and it was live rather than theoretical: hub's ``comms_app``
declares ``"accent_color": "comms"`` in its manifest, hub's stylesheets defined
``--app-accent-comms`` zero times, and the tile had been rendering with no
accent bar. Nothing errored. ``var()`` on an undefined custom property resolves
to nothing, so the only symptom is an absent 2px bar that a person has to
notice — and in July a person did, for a different app, which is why a test
pinning ``--app-accent-storage`` existed at all. That test is what caught this
one, by failing when hub deleted the file it asserted on.

WHY THE COLORS LAYER RATHER THAN THE THEME LAYER, since the taxonomy argues the
other way. An app accent is arguably a DERIVED decision — it maps a product name
onto a palette entry — which by our own primitives-vs-derived rule belongs with
the theme. It is put in the colors layer anyway, deliberately, because that is
the layer adopters already load: consolidating into the theme layer would fix
the duplication and leave ``comms`` broken until every adopter takes on loading
``shell/theme.css``.

That is CHEAPER COORDINATION CHOSEN OVER TIDIER TAXONOMY, knowingly and
temporarily. It is recorded here rather than rationalised because a future
reader is entitled to know the layering question was answered by logistics, and
to reopen it when the logistics change.

WHAT THIS GUARD DOES NOT COVER: whether an accent NAME an app declares actually
exists. That is a cross-repo question — the consumer is a manifest string in
another package (``"accent_color": "comms"``), not a ``var()`` call — and no
search of this repo can see it. It is the reason hub's own ``var(--app-accent-
storage`` search came back empty while a real consumer existed: the control
proved the search RAN, not that it asked the right question.
"""

from __future__ import annotations

import pathlib
import re

import pytest

# Resolved from THIS FILE, not from ``scitex_ui.__file__``: the latter points at
# site-packages under a non-editable install, so the guard would assert about a
# different tree than the branch under review. PR #152 introduces a shared
# ``tests._checkout`` helper for exactly this; switch to it once that lands
# rather than keeping a second copy of the derivation.
_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
)

_COLORS = _CSS / "primitives" / "colors"
_THEME = _CSS / "shell" / "theme.css"

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_DECL = re.compile(r"^\s*(--app-accent-[a-z0-9-]+)\s*:", re.M)

#: Current-app STATE, assigned at render time by ``[data-app-accent="x"]``.
#: Not per-app palette entries, so they legitimately live with the shell.
_STATE = {"--app-accent-color", "--app-accent-tint"}


def _per_app(path: pathlib.Path) -> set[str]:
    if not path.is_file():
        return set()
    text = _CSS_COMMENT.sub("", path.read_text(errors="replace"))
    return {t for t in _DECL.findall(text) if t not in _STATE}


def _colors_layer() -> set[str]:
    found: set[str] = set()
    for path in sorted(_COLORS.glob("*.css")):
        found |= _per_app(path)
    return found


def test_colors_layer_defines_app_accents() -> None:
    """ANTI-VACUITY: an empty colors layer would make the checks below pass.

    A wrong path or a broken regex yields an empty set, every "not duplicated"
    assertion trivially holds, and the suite reports a clean codebase. This is
    the one assertion that distinguishes "measured and found nothing wrong"
    from "did not measure".
    """
    # Arrange: the shipped colors layer is the fixture.
    layer = _COLORS
    # Act
    found = _colors_layer()
    # Assert
    assert len(found) > 20, (
        f"only {len(found)} per-app accent declarations found under {layer}; "
        "the scan did not run, so the checks below would prove nothing"
    )


def test_theme_layer_defines_no_per_app_accents() -> None:
    """The theme layer may hold accent STATE, never per-app palette entries."""
    # Arrange
    allowed = ", ".join(sorted(_STATE))
    # Act
    strays = _per_app(_THEME)
    # Assert
    if strays:
        pytest.fail(
            "shell/theme.css defines per-app accent tokens:\n  "
            + "\n  ".join(sorted(strays))
            + "\n\nThese belong in primitives/colors/ so that an adopter loading "
            "the primitives layer alone still gets them. Defining them here too "
            "means the two layers can drift, and the adopter silently sees "
            f"whichever it happens to load.\nOnly {allowed} may live here — "
            "they are render-time state, not palette entries."
        )


def test_light_and_dark_define_the_same_accent_names() -> None:
    """A name in one palette and not the other is a silent theme-specific hole."""
    # Arrange
    light = _per_app(_COLORS / "_light.css")
    dark = _per_app(_COLORS / "_dark.css")
    # Act
    only_one = (light - dark) | (dark - light)
    # Assert
    assert not only_one, (
        "these accent tokens are defined in one palette but not the other, so "
        "the app loses its accent in whichever theme lacks it — and nothing "
        f"errors: {sorted(only_one)}"
    )
