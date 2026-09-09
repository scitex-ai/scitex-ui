#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_file_browser_twins_agree.py

"""The app file-browser is a PORT of the shell file-tree, and ports drift.

`css/app/file-browser/` was copied from the same source as
`css/shell/workspace-files-tree/`. Every one of its six files says so in its own
header:

    * Ported verbatim from scitex-cloud stx-app-file-tree/search.css

Two copies of one widget with no mechanism noticing when a fix lands on only
one. Measured 2026-09-03, that has happened twice in this pair:

    search.css   FIXED 2026-09-05. The shell twin was repaired in 0.19.1 to read
                 declared tokens; the app twin still named --workspace-bg-default
                 and --workspace-bg-input, DECLARED NOWHERE, so it rendered
                 #1e1e1e in BOTH themes while its twin followed the palette. The
                 app twin now reads --workspace-bg-primary /
                 --workspace-bg-elevated, the same two the shell twin uses.
                 The names were never OURS: the port carried scitex-cloud's
                 vocabulary, and an unknown token does not error in CSS — it
                 takes the fallback. That is why the light theme rendered a
                 black search box and nothing ever failed.
    states.css   the shell brightens a filename on inactive-hover; the app twin
                 has neither rule, though it styles that element elsewhere.

WHAT THIS GUARD CHECKS, AND WHAT IT DOES NOT

It checks ONE property: no token referenced under app/file-browser/ but not
under shell/workspace-files-tree/ may be undeclared. The twin is what makes a
failure actionable — it proves a DECLARED alternative already exists and is in
use for the same widget, so the message can name it.

It does NOT catch the states.css rule-level drift. That is deliberate and
measured, not an oversight:

    FILE level       catches rule-level drift, but FALSE-POSITIVES on
                     organisation — themes.css "diverges" only because the app
                     folds git-status badges into it while the shell files them
                     in git-status.css, with identical tokens and identical
                     fallback hexes. One of three red rows would have been wrong.
    DIRECTORY level  no organisation noise (app-only reduces to exactly the two
                     real tokens), but blind to rule-level drift.

Neither granularity sees both classes. This ships the directory half, which is
zero-noise today; the rule-level half needs a different comparison and is
tracked on
scitex-ui-half-pair-drift-check-mirror-direction-not-assertable-yet-20260818.

WHY THE PAIR LIST IS DERIVED RATHER THAN HARDCODED

Same basename is NOT evidence of twinning, and trusting it would have produced
this card's largest and most fictional finding: `app/media-viewer.css` and
`shell/media-viewer.css` share a name and share only 7 of 18 tokens — because
they are unrelated implementations (22 rules under one namespaced component
versus 66 rules of CSS-table styling). Nothing drifted; they were never copies.

So the pair list comes from the PROVENANCE HEADER, which is evidence of common
origin rather than a proxy for it. A seventh ported file is covered the day it
lands.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_CSS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src" / "scitex_ui" / "static" / "scitex_ui" / "css"
)
_APP = _CSS / "app" / "file-browser"
_SHELL = _CSS / "shell" / "workspace-files-tree"

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
_DECLARED = re.compile(r"^\s*(--[A-Za-z0-9_-]+)\s*:", re.M)

#: The header that makes a file a PORT rather than a coincidence of naming.
#:
#: `verbatim` IS OPTIONAL, AND THE REASON IS A TRAP THIS GUARD WALKED INTO.
#: The marker used to require it, which coupled the guard's POPULATION to a
#: claim about FIDELITY: repairing a ported file makes it no longer verbatim, so
#: telling the truth in its header silently removed it from this scan. Measured
#: 2026-09-05 — search.css was repaired to read declared tokens, its header was
#: updated to say so, and it vanished from `_ported_files()`. Nothing failed
#: except `test_a_known_ported_file_is_found`, the anti-vacuity control, which
#: is the only reason it was noticed rather than shipped as a quietly narrower
#: guard.
#:
#: What this marker must mean is PROVENANCE — "this file began as a port and has
#: a shell twin to stay in step with" — which stays true forever. Fidelity is
#: exactly the property that changes when the file is fixed, so it can never be
#: the thing the population is keyed on.
_PORTED = re.compile(r"Ported (?:verbatim )?from scitex-cloud stx-app-file-tree/")

#: App-only undeclared tokens that are KNOWN and awaiting a decision, each with
#: the card that owns it. Per the constitution: exemptions one at a time, in a
#: reviewable place, with a written reason — never a flag that silences the run.
#:
#: EMPTY AS OF 2026-09-05, and the two entries it held were deleted BY THIS
#: GUARD'S OWN INSTRUCTION rather than by choice: repointing search.css at
#: --workspace-bg-primary / --workspace-bg-elevated made
#: `test_each_exempt_token_is_still_used_by_the_app_twin` fail with "its _EXEMPT
#: entry describes nothing. Delete it." An exemption outliving its subject is a
#: silent widening of what the guard permits, so the staleness check is the part
#: that keeps the exemption list honest.
_EXEMPT: dict[str, str] = {}


def _strip(text: str) -> str:
    return _COMMENT.sub("", text)


def _tokens_used(directory: pathlib.Path) -> set[str]:
    """Every custom property REFERENCED under `directory`, comments stripped."""
    found: set[str] = set()
    for path in sorted(directory.glob("*.css")):
        found |= set(_VAR.findall(_strip(path.read_text(errors="replace"))))
    return found


def _tokens_declared() -> set[str]:
    """Every custom property DECLARED anywhere under css/."""
    found: set[str] = set()
    for path in sorted(_CSS.rglob("*.css")):
        found |= set(_DECLARED.findall(_strip(path.read_text(errors="replace"))))
    return found


def _ported_files() -> list[str]:
    """App files whose own header names them as ports of the shell widget."""
    return [
        path.name
        for path in sorted(_APP.glob("*.css"))
        if _PORTED.search(path.read_text(errors="replace"))
    ]


class TestTheDetectorsThemselves:
    """Literal-sample controls, both directions, for each pattern."""

    def test_the_comment_stripper_matches_a_comment(self):
        """POSITIVE control for `_COMMENT`.

        Two sibling files exempt their comment stripper from the controls check
        with the note "needs a does-not-eat-code control". That note is right
        about what the control should be, so this writes it rather than taking
        the exemption — an exemption whose reason says "a control is needed" is
        a TODO wearing a waiver's clothes."""
        # Arrange
        sample = "/* a comment */"
        # Act
        matched = _COMMENT.search(sample)
        # Assert
        assert matched is not None

    def test_the_comment_stripper_does_not_eat_code(self):
        """NEGATIVE control, and the one that matters for a stripper: a
        declaration with no comment must not match. A greedy pattern that
        swallowed code would silently empty every scan below and turn this
        whole module vacuously green."""
        # Arrange
        sample = "  --workspace-bg-primary: #0d1117;\n"
        # Act
        matched = _COMMENT.search(sample)
        # Assert
        assert matched is None

    def test_var_matches_a_reference(self):
        # Arrange
        sample = "  background: var(--workspace-bg-primary);\n"
        # Act
        matched = _VAR.search(sample)
        # Assert
        assert matched.group(1) == "--workspace-bg-primary"

    def test_var_ignores_a_declaration(self):
        """NEGATIVE control: declaring a token is not referencing it. Without
        this, every palette file would read as a consumer of its own tokens."""
        # Arrange
        sample = "  --workspace-bg-primary: #0d1117;\n"
        # Act
        matched = _VAR.search(sample)
        # Assert
        assert matched is None

    def test_declared_matches_a_declaration(self):
        # Arrange
        sample = "  --workspace-bg-primary: #0d1117;\n"
        # Act
        matched = _DECLARED.search(sample)
        # Assert
        assert matched.group(1) == "--workspace-bg-primary"

    def test_declared_ignores_a_reference(self):
        """NEGATIVE control, the mirror of the above: `var(--x)` is indented
        usage, not a declaration. A pattern that conflated them would report
        every consumed token as declared and never fail."""
        # Arrange
        sample = "  background: var(--workspace-bg-primary);\n"
        # Act
        matched = _DECLARED.search(sample)
        # Assert
        assert matched is None

    def test_ported_matches_the_real_header(self):
        # Arrange
        sample = " * Ported verbatim from scitex-cloud stx-app-file-tree/search.css\n"
        # Act
        matched = _PORTED.search(sample)
        # Assert
        assert matched is not None

    def test_ported_matches_a_repaired_header_that_dropped_verbatim(self):
        """POSITIVE control for the branch that `verbatim` being optional adds.

        Without this, widening the pattern would be untested on exactly the
        spelling it was widened for — and the widening exists because a REPAIRED
        file must stay in the population. A file is a port because of where it
        CAME FROM, never because it is still byte-identical to it.
        """
        # Arrange
        sample = " * Ported from scitex-cloud stx-app-file-tree/search.css, and\n"
        # Act
        matched = _PORTED.search(sample)
        # Assert
        assert matched is not None

    def test_ported_ignores_prose_about_porting(self):
        """NEGATIVE control. This file and its card both DISCUSS porting; a
        looser pattern would match the discussion and mint pairs from prose.

        It guards the widening too: dropping `verbatim` must not loosen the
        pattern into ordinary sentences about having ported something."""
        # Arrange
        sample = " * This widget was ported from somewhere, see the card.\n"
        # Act
        matched = _PORTED.search(sample)
        # Assert
        assert matched is None


class TestTheScansAreNotEmpty:
    """Every population here is a file scan. An empty one makes the real check
    VACUOUSLY true — which is how `children.css` reads as AGREE while both
    twins reference nothing at all."""

    def test_ported_files_are_found(self):
        # Arrange
        expected_minimum = 1
        # Act
        found = _ported_files()
        # Assert
        assert len(found) >= expected_minimum

    def test_a_known_ported_file_is_found(self):
        """A count alone would pass against the wrong directory."""
        # Arrange
        known = "search.css"
        # Act
        found = _ported_files()
        # Assert
        assert known in found

    def test_the_app_twin_references_tokens(self):
        # Arrange
        expected_minimum = 1
        # Act
        found = _tokens_used(_APP)
        # Assert
        assert len(found) >= expected_minimum

    def test_the_shell_twin_references_tokens(self):
        # Arrange
        expected_minimum = 1
        # Act
        found = _tokens_used(_SHELL)
        # Assert
        assert len(found) >= expected_minimum

    def test_a_known_declared_token_is_found(self):
        """Anti-vacuity for the declaration scan: if it returned nothing, every
        token would read as undeclared and the guard would fail loudly for the
        wrong reason — which is louder but no more correct."""
        # Arrange
        known = "--workspace-bg-primary"
        # Act
        found = _tokens_declared()
        # Assert
        assert known in found


class TestEveryPortedFileStillHasItsTwin:
    """A port whose counterpart was renamed or deleted is a half-pair."""

    def test_each_ported_file_has_a_shell_counterpart(self):
        # Arrange
        ported = _ported_files()
        # Act
        orphaned = sorted(n for n in ported if not (_SHELL / n).is_file())
        # Assert
        assert not orphaned, (
            f"These app/file-browser files declare themselves ports of the "
            f"shell file-tree, but no same-named file exists under "
            f"{_SHELL.name}/: {', '.join(orphaned)}. Either the shell file was "
            "renamed and the port's header is now lying, or the port is dead."
        )


class TestAppOnlyTokensAreDeclared:
    """The shippable half: a token the app twin uses, its twin does not, and
    nothing declares."""

    def test_no_app_only_token_is_undeclared(self):
        # Arrange
        app_only = _tokens_used(_APP) - _tokens_used(_SHELL)
        declared = _tokens_declared()
        # Act
        offenders = sorted(
            t for t in app_only if t not in declared and t not in _EXEMPT
        )
        # Assert
        assert not offenders, (
            "These tokens are referenced under app/file-browser/, are NOT used "
            "by its shell twin, and are declared nowhere under css/ — so they "
            "render their literal fallback forever and cannot follow the "
            f"theme: {', '.join(offenders)}.\n\n"
            "The twin is the evidence that a declared alternative exists: check "
            "what shell/workspace-files-tree/ uses for the same property and "
            "point at that. Add to _EXEMPT with a written reason only if the "
            "divergence is deliberate."
        )


class TestExemptionsStayHonest:
    """An exemption that no longer describes reality is a comment pretending to
    be a decision."""

    @pytest.mark.parametrize("token", sorted(_EXEMPT))
    def test_each_exempt_token_is_still_undeclared(self, token):
        """When someone finally declares one of these, the entry must GO — that
        removal is the forcing function, and without this check the list would
        quietly become a record of history."""
        # Arrange
        declared = _tokens_declared()
        # Act
        still_broken = token not in declared
        # Assert
        assert still_broken, (
            f"{token} is now declared, so its _EXEMPT entry is stale. Delete "
            "the entry — that deletion is how this guard tightens."
        )

    @pytest.mark.parametrize("token", sorted(_EXEMPT))
    def test_each_exempt_token_is_still_used_by_the_app_twin(self, token):
        # Arrange
        used = _tokens_used(_APP)
        # Act
        still_used = token in used
        # Assert
        assert still_used, (
            f"{token} is no longer referenced under app/file-browser/, so its "
            "_EXEMPT entry describes nothing. Delete it."
        )

    def test_an_empty_exemption_list_is_stated_not_skipped(self):
        """The two staleness checks above parametrize over `_EXEMPT`, so an
        EMPTY list makes both collect nothing and report as SKIPPED — a guard
        that asserts nothing while still being counted in the suite line.

        Empty is the CORRECT and strongest state here (no token is exempt), but
        `skipped` cannot distinguish it from the two bad reasons a collection
        comes back empty: the query broke, or the subject moved. This test is
        the denominator — it makes "no exemptions" an ASSERTION with a stated
        expectation rather than an absence, so the good case is visible and the
        bad ones would still fail above.
        """
        # Arrange
        exempt = _EXEMPT
        # Act
        count = len(exempt)
        # Assert
        assert count == 0, (
            f"{sorted(exempt)} are exempt. That is allowed — each entry carries "
            "a written reason and a card — but this test pins the count so the "
            "list cannot grow unnoticed. Update the expected count deliberately."
        )

    def test_every_exemption_states_a_reason(self):
        # Arrange
        blank = sorted(t for t, why in _EXEMPT.items() if not why.strip())
        # Act
        offenders = blank
        # Assert
        assert not offenders, (
            f"_EXEMPT entries with no written reason: {', '.join(offenders)}."
        )
