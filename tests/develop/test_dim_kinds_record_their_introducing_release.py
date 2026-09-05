#!/usr/bin/env python3
"""Every verdict kind states which release first shipped it.

THIS IS LOAD-BEARING FOR ANOTHER REPOSITORY, which is why it is asserted rather
than trusted. scitex-app's cross-package agreement check installs scitex-ui
UNPINNED, so an older wheel makes their Python kind set disagree with this
file's. Their failure message (their #133, merged 2026-09-05) ends:

    "...this is a stale install rather than a broken contract — types.ts
     records each kind's introducing release next to the kind."

A reader who hits that red follows the pointer here. If the provenance lines
were ever removed, the pointer would lead nowhere and NOTHING WOULD FAIL: not
their CI, not this suite, not a build. The person following it would be worse
off than with no pointer at all.

CONTRAST WITH THE OTHER COUPLING ON THIS FILE, because the difference decides
what needs a guard:

    VerdictKind union, parsed by their #131
        broken by me -> their CI fails LOUDLY (they deliberately wrote no
        fallback to the constants, so a rename cannot silently revert them to
        the one-directional behaviour they just fixed)

    provenance lines, pointed at by their #133 message
        removed by me -> degrades SILENTLY

Only the second needs anything from this repo. The first already has a
mechanism, and duplicating it here in prose would be weaker than the mechanism
it duplicates.

WHAT THIS DELIBERATELY DOES NOT ASSERT: that the versions are CORRECT. That
needs the published wheels (0.19.1 has no types.ts; 0.20.0 and 0.20.1 carry four
kinds; 0.20.2 carries five) and belongs with the release-verification work.
Presence is what the pointer depends on, and presence is checkable here forever
without knowing anything about scitex-app's current implementation — which is
precisely the claim this file's own header refuses to write down, because it
goes stale the day they change it.
"""

from __future__ import annotations

import re

import pytest

from tests._checkout import static_dir

_TYPES = static_dir() / "ts" / "app" / "dim" / "types.ts"

#: `export const NAME = "value";` — same shape test_dim_renders_a_verdict uses.
_CONST = re.compile(r'export const (\w+)\s*=\s*"([^"]+)"')

#: The provenance sentence, e.g. `Ships from scitex-ui 0.20.2.`
_PROVENANCE = re.compile(r"Ships from scitex-ui (\d+\.\d+\.\d+)")


def _blocks() -> dict[str, str]:
    """Map each kind constant to the text preceding it since the last constant.

    That span is the constant's own doc comment. Splitting on the declarations
    rather than parsing comments keeps this robust to whether a kind is
    documented with a one-line or a multi-paragraph block — both forms are in
    the file today.
    """
    text = _TYPES.read_text()
    out: dict[str, str] = {}
    cursor = 0
    for match in _CONST.finditer(text):
        out[match.group(1)] = text[cursor : match.start()]
        cursor = match.end()
    return out


def _kind_names() -> list[str]:
    """The constant names, for parametrisation."""
    return sorted(_blocks())


@pytest.mark.parametrize("kind", _kind_names())
def test_every_kind_states_the_release_that_introduced_it(kind: str) -> None:
    """The subject: each kind carries a provenance line in its doc comment."""
    # Arrange
    block = _blocks()[kind]
    # Act
    found = _PROVENANCE.search(block)
    # Assert
    assert found is not None, (
        f"{kind} has no 'Ships from scitex-ui <version>' line in its doc "
        f"comment. scitex-app's agreement-check failure message tells a reader "
        f"that this file records each kind's introducing release; removing it "
        f"makes that pointer lead nowhere, and nothing else anywhere fails."
    )


def test_the_scan_finds_the_kinds_at_all() -> None:
    """Control: an empty kind set would make every assertion above vacuous."""
    # Arrange
    # Act
    count = len(_blocks())
    # Assert
    assert count >= 5, (
        f"only {count} kind constants found in {_TYPES.name}; the parametrised "
        f"guard above would be nearly empty and would pass by default"
    )


class TestTheProvenancePatternSeparatesAStatementFromAMention:
    """Controls on `_PROVENANCE`, both directions.

    Without these, a pattern that matched nothing would report every kind as
    undocumented, and a pattern that matched any version-shaped string would
    accept a paragraph that merely names a release in passing — this file's
    header does exactly that, twice.
    """

    def test_the_pattern_matches_a_real_provenance_line(self) -> None:
        """Positive: the instrument is not blind."""
        # Arrange
        # Act
        hit = _PROVENANCE.search(" * Ships from scitex-ui 0.20.0.")
        # Assert
        assert hit is not None, "_PROVENANCE cannot match a real provenance line"

    def test_the_pattern_ignores_prose_that_merely_names_a_release(self) -> None:
        """Negative: naming a version is not stating where a kind ships from."""
        # Arrange
        # Act
        hit = _PROVENANCE.search(" * 0.20.0 and 0.20.1 carry four kinds.")
        # Assert
        assert hit is None, f"_PROVENANCE matched a passing mention: {hit}"


class TestTheConstantPatternSeparatesADeclarationFromAMention:
    """Controls on `_CONST`, for the same reason."""

    def test_the_pattern_matches_a_real_declaration(self) -> None:
        """Positive."""
        # Arrange
        # Act
        hit = _CONST.search('export const UNRESOLVED = "unresolved";')
        # Assert
        assert hit is not None, "_CONST cannot match a real declaration"

    def test_the_pattern_ignores_prose_naming_a_constant(self) -> None:
        """Negative: a sentence about UNRESOLVED is not a declaration of it."""
        # Arrange
        # Act
        hit = _CONST.search(" * UNRESOLVED is the fifth kind, added 2026-09-05.")
        # Assert
        assert hit is None, f"_CONST matched prose rather than a declaration: {hit}"
