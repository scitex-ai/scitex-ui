"""`@scitex/ui` is consumed by sibling checkout, never from the npm registry.

Operator decision, 2026-07-29: 「npm 公開はやめたんです」 — npm publishing was
abandoned. This pins that decision where it is enforced rather than remembered.

The card this closes (scitex-ui-npm-package-absent-from-registry-20260722) was
opened because the repo carried a publishable-looking npm surface, a card
saying the publish was DONE, and a registry that 404s. Two of those three are
now fixed; this guards the third from coming back.
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_JSON = _REPO_ROOT / "package.json"


def _manifest() -> dict:
    return json.loads(_PACKAGE_JSON.read_text())


def test_package_json_exists() -> None:
    # Arrange — consumers resolve @scitex/ui through this file's exports map
    # via a sibling checkout (figrecipe, scitex-writer). Deleting it to "remove
    # the npm surface" would break them, which is why the answer is `private`
    # rather than deletion.
    # Act
    found = _PACKAGE_JSON.is_file()
    # Assert
    assert found, f"{_PACKAGE_JSON} is required for sibling-checkout consumers"


def test_package_is_marked_private() -> None:
    # Arrange — `npm publish` REFUSES a package with private:true. That makes
    # the operator's decision mechanical instead of a note someone can miss,
    # and it costs sibling-checkout consumers nothing: local resolution through
    # the exports map works identically for a private package.
    # Act
    private = _manifest().get("private")
    # Assert
    assert private is True, (
        "package.json must keep `private: true` — @scitex/ui is not published "
        "to npm (operator decision 2026-07-29). Removing this re-opens the "
        "accidental-publish path the registry card was filed for."
    )


def test_exports_map_still_present() -> None:
    # Arrange — private:true must not be mistaken for "this package is unused".
    # The exports map is the thing sibling consumers actually resolve through,
    # so it has to survive any future tidy-up of the npm surface.
    # Act
    exports = _manifest().get("exports")
    # Assert
    assert exports, "exports map is how sibling checkouts resolve @scitex/ui"
