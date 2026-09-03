#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_api_docs_list_every_public_module.py

"""The API reference enumerates modules by hand, so a new one is invisible.

`docs/sphinx/api/scitex_ui.rst` lists each module in an explicit `automodule`
stanza rather than autosummarising a package. That is a reasonable choice — it
controls ordering and lets each section carry prose — but it has no failure
mode: **sphinx builds clean whether or not a module is listed.** Nothing in CI
notices an omission, so the docs silently drift behind the code.

MEASURED 2026-09-03, before this guard existed. The file documented the
top-level module, one private registry and five private components — and omitted
`branding` and `mount`, the two modules a consumer is actually told to import.
`shell_context()` lives in `branding`. scitex-hub imports from it. The operator's
dual-mode requirement is expressed through `mount`. Neither was in the rendered
docs, and every build was green.

WHY IT IS SCOPED TO PUBLIC MODULES. A leading underscore is this package's
declaration that something is internal, so requiring stanzas for `_cli` or
`_registry` would demand documentation of things deliberately not offered. The
rule is therefore: **every module a consumer may import must appear.** Private
ones MAY appear — several do, and that is a separate question this guard does
not answer.

THE ENUMERATIONS ARE ASSERTED NON-EMPTY, which is the part worth copying. Both
halves of this check are directory/file scans, and a scan that stops matching
yields an empty set — at which point "every public module is documented" is
VACUOUSLY TRUE and the test passes forever. That failure is indistinguishable
from success in a summary line. scitex-app spent a day on the same shape in a
different instrument on 2026-09-03: a cross-package check that had never run in
CI, reported as a skip nobody read.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE = _ROOT / "src" / "scitex_ui"
_RST = _ROOT / "docs" / "sphinx" / "api" / "scitex_ui.rst"

#: Public modules deliberately NOT documented, each with a written reason.
#: Per the constitution, exemptions are granted one at a time in a reviewable
#: place — never by loosening the rule itself.
_EXEMPT: dict[str, str] = {}

_AUTOMODULE = re.compile(r"^\.\.\s+automodule::\s+scitex_ui\.([A-Za-z0-9_.]+)\s*$", re.M)


def _public_modules() -> set[str]:
    """Top-level modules a consumer may import, by name."""
    return {
        path.stem
        for path in _PACKAGE.glob("*.py")
        if not path.stem.startswith("_")
    }


def _documented_modules() -> set[str]:
    """Module paths carrying an ``automodule`` stanza in the API reference."""
    return set(_AUTOMODULE.findall(_RST.read_text(encoding="utf-8")))


class TestTheDetectorItself:
    """Literal-sample controls, both directions.

    Distinct from the scan checks below: those read the REAL file, which is the
    guard doing its job rather than a control on the guard. "Finds nothing in
    the tree" and "could never match anything" are indistinguishable without a
    literal.
    """

    def test_it_matches_a_real_stanza(self):
        """POSITIVE control: prove the pattern is not blind."""
        # Arrange
        sample = ".. automodule:: scitex_ui.branding\n   :members:\n"
        # Act
        found = _AUTOMODULE.findall(sample)
        # Assert
        assert found == ["branding"]

    def test_it_ignores_prose_that_merely_mentions_one(self):
        """NEGATIVE control: prove the pattern is not inverted.

        The mention is indented, which is what makes it prose rather than a
        directive — and the anchored pattern is what makes that distinction.

        Two shapes here are dictated by `test_detectors_carry_controls.py`, and
        both are worth keeping rather than working around:

        `.search(...) is None` rather than `.findall(...) == []` — equally
        strong, but only the first is recognised as a negation.

        The sample is an INLINE LITERAL rather than a module constant, because
        the meta-guard counts only locals bound to a string constant inside the
        function. That is the right strictness: a control whose sample is a
        reference proves nothing about what the sample contains. Adapting this
        file is a smaller change than widening a guard the whole suite depends
        on to accommodate one new caller."""
        # Arrange
        sample = "   To document a module, add .. automodule:: scitex_ui.foo\n"
        # Act
        matched = _AUTOMODULE.search(sample)
        # Assert
        assert matched is None


class TestTheInstrumentItself:
    """Both halves are scans. An empty scan makes the real check vacuous."""

    def test_the_package_scan_finds_modules(self):
        # Arrange
        expected_minimum = 1
        # Act
        found = _public_modules()
        # Assert
        assert len(found) >= expected_minimum

    def test_the_package_scan_finds_a_module_known_to_exist(self):
        """Positive control: a count alone would pass on the wrong directory."""
        # Arrange
        known = "branding"
        # Act
        found = _public_modules()
        # Assert
        assert known in found

    def test_the_rst_scan_finds_stanzas(self):
        # Arrange
        expected_minimum = 1
        # Act
        found = _documented_modules()
        # Assert
        assert len(found) >= expected_minimum

    def test_the_rst_scan_finds_a_stanza_known_to_be_present(self):
        """Positive control for the regex: if it stopped matching, every module
        would read as undocumented and the failure would look like a real
        finding rather than a broken detector."""
        # Arrange
        known = "_registry"
        # Act
        found = _documented_modules()
        # Assert
        assert known in found


class TestEveryPublicModuleIsDocumented:
    @pytest.mark.parametrize("module", sorted(_public_modules()))
    def test_module_has_an_automodule_stanza(self, module):
        # Arrange
        reason = _EXEMPT.get(module)
        # Act
        documented = module in _documented_modules()
        # Assert
        assert documented or reason, (
            f"scitex_ui.{module} is importable by consumers but has no "
            f"`.. automodule:: scitex_ui.{module}` stanza in "
            f"docs/sphinx/api/scitex_ui.rst, so it does not appear in the "
            f"rendered API reference. Sphinx builds clean either way. Add a "
            f"stanza, or add an entry to _EXEMPT with a written reason."
        )


class TestPrivateModulesAreNotRequired:
    """NEGATIVE CONTROL. Without this, a guard that demanded stanzas for
    everything would pass the tests above and be wrong."""

    def test_a_private_module_exists_to_control_against(self):
        """The control is worthless if no private module is actually present."""
        # Arrange
        expected = "_cli"
        # Act
        private_files = {p.stem for p in _PACKAGE.glob("_*.py")}
        # Assert
        assert expected in private_files

    def test_a_private_module_is_not_in_the_required_set(self):
        # Arrange
        private = "_cli"
        # Act
        required = _public_modules()
        # Assert
        assert private not in required


class TestExemptionsAreHonest:
    """An exemption must name a module that exists, or it is a stale note."""

    def test_every_exemption_names_a_real_public_module(self):
        # Arrange
        public = _public_modules()
        # Act
        stale = sorted(set(_EXEMPT) - public)
        # Assert
        assert not stale, (
            f"_EXEMPT names module(s) that are not public modules of this "
            f"package: {', '.join(stale)}. Drop the entry."
        )

    def test_every_exemption_states_a_reason(self):
        # Arrange
        blank = sorted(m for m, why in _EXEMPT.items() if not why.strip())
        # Act
        offenders = blank
        # Assert
        assert not offenders, (
            f"_EXEMPT entries with no written reason: {', '.join(offenders)}. "
            "An exemption without a reason is the blanket flag this rule exists "
            "to avoid."
        )
