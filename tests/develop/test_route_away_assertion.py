#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_route_away_assertion.py

"""`assert_has_route_away` must fail on the page that prompted it.

THE GUARD THIS REPLACES COULD NOT FAIL. scitex-hub measured live prod on
2026-08-23, mobile UA, anonymous:

    /apps/cards/      6 anchors    navigable
    /apps/storage/    1 anchor     still a dead end

So the obvious assertion — "the page has at least one <a>" — is GREEN on
storage, the exact page this work exists to catch. It would have shipped,
passed, and told everyone the dead end was fixed. That is why the central case
here is not "does the helper accept a good page" but
`TestItIsSharperThanCountingAnchors`: it pins the naive predicate to the storage
sample and proves it GREEN, then proves the real predicate RED on the same
bytes. A guard that only ever agrees with the simpler guard IS the simpler
guard.

BOTH DIRECTIONS, ALWAYS. Per `test_detectors_carry_controls.py`, every detector
here carries a positive control (it fires on a real instance) and a negative one
(it stays quiet on something that merely resembles one). A detector tested in a
single direction is indistinguishable from one that is broken in the other.

SCOPE, stated because it bounds what a green means. This reads HREFS. It does
not ask whether a route is REACHABLE — an anchor can be present, well-formed,
and covered by an overlay, hidden by CSS, or left without an accessible name,
and this module will count it. Those are real dead ends and this will not catch
them. Pointing a browser at the page is what catches those;
`test_dim_renders_a_verdict.py` records the same boundary for the same reason.
"""

from __future__ import annotations

import re

import pytest

from scitex_ui.testing import (
    RouteAwayReport,
    assert_has_route_away,
    find_routes_away,
)

# --------------------------------------------------------------------------
# Samples, shaped after scitex-hub's 2026-08-23 prod measurement so these tests
# fail on the real defect rather than on a convenient invention.
# --------------------------------------------------------------------------

#: A dead end with exactly ONE anchor, as storage measured. The anchor is real
#: markup and goes nowhere — which is why an anchor COUNT reads it as healthy.
STORAGE_SHAPED = """
<body class="workspace-page">
  <div id="workspace-three-col">
    <div class="ws-module-pane">
      <h1>Storage</h1>
      <a href="#main-content">Skip to content</a>
    </div>
  </div>
</body>
"""

#: Navigable, as cards measured: links from the APP's own content, not the shell.
CARDS_SHAPED = """
<body class="workspace-page">
  <div id="workspace-three-col">
    <div class="ws-module-pane">
      <a href="/apps/cards/board/">Board</a>
      <a href="/apps/cards/mine/">Mine</a>
      <a href="/apps/cards/dm/">DM</a>
    </div>
  </div>
</body>
"""

#: What the shell renders once a composer supplies `launcher=`.
WITH_LAUNCHER_SLOT = """
<body class="workspace-page">
  <a class="stx-shell-launcher-link" href="/apps/"><span>&#8592;</span> Apps</a>
  <div id="workspace-three-col"><div class="ws-module-pane">Storage</div></div>
</body>
"""

STORAGE_PATH = "/apps/storage/"


@pytest.fixture
def storage_failure_message() -> str:
    """The AssertionError text raised for the storage-shaped dead end."""
    with pytest.raises(AssertionError) as excinfo:
        assert_has_route_away(STORAGE_SHAPED, current_path=STORAGE_PATH)
    return str(excinfo.value)


@pytest.fixture
def storage_report() -> RouteAwayReport:
    return find_routes_away(STORAGE_SHAPED, current_path=STORAGE_PATH)


class TestTheDefectItWasBuiltFor:
    """Storage must go RED; cards must stay GREEN."""

    def test_storage_shaped_page_is_rejected(self):
        # Arrange
        check = lambda: assert_has_route_away(  # noqa: E731
            STORAGE_SHAPED, current_path=STORAGE_PATH
        )
        # Act
        outcome = check
        # Assert
        with pytest.raises(AssertionError):
            outcome()

    def test_failure_message_names_the_defect(self, storage_failure_message):
        # Arrange
        expected = "no route away"
        # Act
        actual = storage_failure_message
        # Assert
        assert expected in actual

    def test_failure_message_names_why_the_anchor_did_not_count(
        self, storage_failure_message
    ):
        # Arrange
        expected = "in-page fragment"
        # Act
        actual = storage_failure_message
        # Assert
        assert expected in actual

    def test_failure_message_names_the_fix(self, storage_failure_message):
        # Arrange
        expected = "launcher="
        # Act
        actual = storage_failure_message
        # Assert
        assert expected in actual

    def test_cards_shaped_page_is_accepted(self):
        # Arrange
        sample = CARDS_SHAPED
        # Act
        report = assert_has_route_away(sample, current_path="/apps/cards/")
        # Assert
        assert report.has_route_away

    def test_cards_routes_include_its_own_content_links(self):
        # Arrange
        sample = CARDS_SHAPED
        # Act
        report = find_routes_away(sample, current_path="/apps/cards/")
        # Assert
        assert "/apps/cards/board/" in report.routes

    def test_launcher_slot_alone_is_enough(self):
        # Arrange -- storage's own content contributes nothing, so the slot is
        # the whole fix and must suffice unaided.
        sample = WITH_LAUNCHER_SLOT
        # Act
        report = assert_has_route_away(sample, current_path=STORAGE_PATH)
        # Assert
        assert report.routes == ("/apps/",)


class TestItIsSharperThanCountingAnchors:
    """Why this helper exists rather than `assert "<a" in html`."""

    def test_storage_sample_really_does_contain_one_anchor(self):
        """Pins the sample. If this fails, the sample stopped being the thing
        we are defending against and the test below proves nothing."""
        # Arrange
        sample = STORAGE_SHAPED
        # Act
        naive_count = len(re.findall(r"<a\s", sample))
        # Assert
        assert naive_count == 1

    def test_naive_predicate_would_have_passed_the_dead_end(self):
        """THE VACUOUS GUARD, written out so it cannot drift: green on storage."""
        # Arrange
        sample = STORAGE_SHAPED
        # Act
        naive_verdict = len(re.findall(r"<a\s", sample)) >= 1
        # Assert
        assert naive_verdict is True

    def test_real_predicate_is_red_on_the_same_bytes(self, storage_report):
        # Arrange
        expected = ()
        # Act
        actual = storage_report.routes
        # Assert
        assert actual == expected

    def test_real_predicate_still_sees_the_anchor(self, storage_report):
        """It rejects the anchor rather than failing to parse it."""
        # Arrange
        expected = 1
        # Act
        actual = storage_report.anchors_total
        # Assert
        assert actual == expected


REJECTED_FORMS = [
    ('<a href="#top">Top</a>', "in-page fragment"),
    ('<a href="">Nowhere</a>', "empty href"),
    ('<a href="   ">Nowhere</a>', "empty href"),
    ("<a>Not a link</a>", "no href attribute"),
    ('<a href="javascript:void(0)">Menu</a>', "non-navigating scheme"),
    ('<a href="JavaScript:void(0)">Menu</a>', "non-navigating scheme"),
]

ROUTING_FORMS = [
    '<a href="/apps/">Apps</a>',
    '<a href="../">Up</a>',
    '<a href="https://example.org/">Out</a>',
    '<a href="/apps/storage/files/#tree">Deep link with fragment</a>',
]


class TestWhatDoesNotCountAsARoute:
    """Each rejection, and a negative control that resembles it."""

    @pytest.mark.parametrize(("markup", "reason"), REJECTED_FORMS)
    def test_rejected_form_yields_no_route(self, markup, reason):
        # Arrange
        page = f"<body>{markup}</body>"
        # Act
        report = find_routes_away(page)
        # Assert
        assert report.routes == ()

    @pytest.mark.parametrize(("markup", "reason"), REJECTED_FORMS)
    def test_rejected_form_is_given_its_reason(self, markup, reason):
        # Arrange
        page = f"<body>{markup}</body>"
        # Act
        report = find_routes_away(page)
        # Assert
        assert report.rejected[0][1] == reason

    @pytest.mark.parametrize("markup", ROUTING_FORMS)
    def test_routing_form_is_counted(self, markup):
        """NEGATIVE CONTROL: these resemble the rejected forms — the last one
        even carries a fragment — and must be counted as routes."""
        # Arrange
        page = f"<body>{markup}</body>"
        # Act
        report = find_routes_away(page)
        # Assert
        assert len(report.routes) == 1


class TestSelfLinks:
    """A link back to the page you are already on is not an escape."""

    SELF = '<body><a href="/apps/storage/">Storage</a></body>'

    def test_rejected_when_current_path_is_supplied(self):
        # Arrange
        page = self.SELF
        # Act
        report = find_routes_away(page, current_path=STORAGE_PATH)
        # Assert
        assert report.routes == ()

    def test_rejection_names_the_self_link(self):
        # Arrange
        page = self.SELF
        # Act
        report = find_routes_away(page, current_path=STORAGE_PATH)
        # Assert
        assert report.rejected[0][1] == "self-link (same as current_path)"

    def test_counted_when_current_path_is_omitted(self):
        """The documented weaker behaviour, pinned so that weakening it stays a
        DECISION someone made rather than a regression nobody noticed."""
        # Arrange
        page = self.SELF
        # Act
        report = find_routes_away(page)
        # Assert
        assert report.routes == (STORAGE_PATH,)


class TestEmptyInputIsNotAFinding:
    """A fixture that fetched nothing must not read as a dead end."""

    @pytest.mark.parametrize("empty", ["", "   ", "\n\t "])
    def test_empty_input_raises_value_error(self, empty):
        # Arrange
        sample = empty
        # Act
        check = lambda: find_routes_away(sample)  # noqa: E731
        # Assert -- ValueError, NOT AssertionError. Collapsing the two would let
        # a broken fixture masquerade as a real finding.
        with pytest.raises(ValueError, match="fixture problem"):
            check()

    def test_real_markup_with_no_anchors_is_a_finding(self):
        """NEGATIVE CONTROL for the above: a genuine dead end must go through
        the ASSERTION path, not the ValueError path."""
        # Arrange
        page = "<body><h1>Storage</h1></body>"
        # Act
        check = lambda: assert_has_route_away(page)  # noqa: E731
        # Assert
        with pytest.raises(AssertionError, match="no <a> elements at all"):
            check()


class TestReportShape:
    """A fixed, declared shape with each signal in its own named field."""

    def test_returns_a_route_away_report(self):
        # Arrange
        sample = CARDS_SHAPED
        # Act
        report = find_routes_away(sample)
        # Assert
        assert isinstance(report, RouteAwayReport)

    def test_anchors_total_counts_every_anchor(self):
        # Arrange
        sample = CARDS_SHAPED
        # Act
        report = find_routes_away(sample)
        # Assert
        assert report.anchors_total == 3

    def test_report_is_frozen(self):
        # Arrange
        report = find_routes_away(CARDS_SHAPED)

        def mutate():
            report.routes = ()

        # Act
        check = mutate
        # Assert
        with pytest.raises(Exception):
            check()

    def test_a_dead_end_still_reports_the_anchors_it_rejected(
        self, storage_report
    ):
        """The interesting state: the page LOOKS linked and is not."""
        # Arrange
        expected = 1
        # Act
        actual = storage_report.anchors_total
        # Assert
        assert actual == expected
