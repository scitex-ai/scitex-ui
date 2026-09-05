#!/usr/bin/env python3
"""No shipped stylesheet may name an asset that does not ship — comments included.

THE BUG THIS EXISTS FOR SHIPPED, AND BROKE A PRODUCTION BUILD. scitex-ui
0.20.1's ``utils/effects.css`` opened with a comment quoting the line hub's
``variables.css`` carries:

        (an at-import of effects.css from a utilities directory)

It was inside ``/* ... */``, so it looked inert. Django's staticfiles
post-processor rewrites asset references by REGEX, and below 6.1 it does not
know what a comment is. Every scitex-hub PR went red on 2026-09-05 with
``MissingFileError: The file 'scitex_ui/css/utilities/effects.css' could not be
found``, gating their production rebuild.

THE BOUNDARY IS MEASURED FROM BOTH SIDES, 2026-09-05, because one side alone
would have been a guess:

    Django 6.1.1 (here)          _css_ignored_re PRESENT   does NOT reproduce
    Django 6.0.8 (hub CI)        _css_ignored_re ABSENT    reproduces

So "Django ignores comments" is true of 6.1+ and false of 6.0.x, and the
failure needs BOTH a quoted path here and a pre-6.1 reader there. Naming only
one cause would send the next reader looking in one repo for a fault that
takes two.

WHY A GUARD ALREADY EXISTED AND DID NOT CATCH IT. test_css_bundle_index.py has
``test_no_import_points_at_a_missing_file``, named for precisely this failure.
Its scope is the two GENERATED bundles (all.css, primitives/variables.css) and
their comment-stripped import lines. utils/effects.css is not a bundle, so it
was never examined; the reference was in a comment, so a comment-stripping
reader would have skipped it anyway. The guard was not weak, it was pointed
somewhere else — which is the failure worth remembering, because a green run
from it said nothing at all about this file.

THIS SCAN IS DELIBERATELY COMMENT-BLIND, AND THAT IS NOT AN OVERSIGHT. Django
6.1.1 DOES skip comments (``_css_ignored_re`` in contrib/staticfiles/storage.py,
"Ignore URLs in comments and string literals"), and running the real 6.1.1
post-processor over the 0.20.1 bytes does NOT reproduce the failure. Matching
that behaviour would make this guard green on exactly the file that broke hub.
A library cannot choose its consumers' Django version, so the rule here is
stricter than any single reader: if a ``url(`` or quoted ``@import`` token names
a path, that path resolves — wherever in the file it appears. Being stricter
than the strictest consumer is the only setting that is safe for all of them.

Describe such a line in prose instead. Prose costs a sentence; a byte-identical
quotation costs everyone's collectstatic.
"""

from __future__ import annotations

import pathlib
import re

# Resolve the CHECKOUT rather than the installed package, for the reason given
# at length in test_primitives_define_each_token_once: a guard that reads the
# installed copy goes green on stale bytes after an edit nobody reinstalled.
_CSS_DIR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_ui"
    / "static"
    / "scitex_ui"
    / "css"
)

# Copied VERBATIM from django/contrib/staticfiles/storage.py (6.1.1), because a
# paraphrase of a consumer's regex is a different regex, and the difference only
# shows up as a false green.
_URL = re.compile(r"""url\((?P<quote>['"]{0,1})\s*(?P<url>.*?)(?P=quote)\)""")
_IMPORT = re.compile(r"""@import\s*["']\s*(?P<url>.*?)["']""")

# References Django does not resolve against the static tree.
_EXTERNAL = ("data:", "http:", "https:", "//", "#", "var(")


def _unresolved_in(text: str, base: pathlib.Path) -> list[tuple[int, str]]:
    """Return (line, url) for every reference in ``text`` that does not exist.

    ``base`` is the directory the stylesheet lives in, since CSS resolves
    relative references against the importing file rather than the root.
    """
    out = []
    for match in list(_URL.finditer(text)) + list(_IMPORT.finditer(text)):
        url = match.group("url").strip()
        if not url or url.startswith(_EXTERNAL):
            continue
        if not (base / url).resolve().exists():
            out.append((text[: match.start()].count("\n") + 1, url))
    return out


def _reference_count(text: str) -> int:
    """How many references the patterns see at all."""
    return len(list(_URL.finditer(text))) + len(list(_IMPORT.finditer(text)))


def _scan_shipped() -> list[str]:
    """Every unresolvable reference across the shipped stylesheets."""
    findings = []
    for css in sorted(_CSS_DIR.rglob("*.css")):
        for line, url in _unresolved_in(css.read_text(), css.parent):
            findings.append(f"{css.relative_to(_CSS_DIR)}:{line} -> {url}")
    return findings


def test_no_shipped_stylesheet_references_a_missing_file():
    """The subject: nothing in the shipped CSS names an asset that is absent."""
    # Arrange
    # Act
    findings = _scan_shipped()
    # Assert
    assert not findings, (
        "These references do not resolve, and Django's staticfiles "
        "post-processor fails collectstatic on them even inside a comment:\n  "
        + "\n  ".join(findings)
        + "\n\nIf the reference is illustrative, write it as PROSE rather than "
        "as CSS syntax — see the header of this file."
    )


class TestTheScanReadsWhatDjangoReads:
    """Controls. Without these, an empty finding list is not evidence.

    A scan that matched nothing would report a clean tree forever, and that is
    the exact shape of the failure this file documents: a guard that was green
    because it was looking elsewhere.
    """

    def test_the_patterns_find_references_in_the_real_tree(self):
        """Proves the scan is reading CSS, not matching nothing."""
        # Arrange
        total = sum(_reference_count(c.read_text()) for c in _CSS_DIR.rglob("*.css"))
        # Act
        found_plenty = total > 50
        # Assert
        assert found_plenty, (
            f"only {total} references seen across the whole CSS tree; the "
            f"patterns are broken and a clean result would mean nothing"
        )

    def test_a_reference_inside_a_block_comment_is_still_seen(self, tmp_path):
        """The 0.20.1 defect itself: comment-blindness is the point."""
        # Arrange
        text = '/* was: @import url("../nope/gone.css"); */\n:root{--a:1px}\n'
        # Act
        found = _unresolved_in(text, tmp_path)
        # Assert
        assert found == [(1, "../nope/gone.css")], (
            f"a reference inside a comment was not reported: {found}; this "
            f"guard would have been green on the bytes that broke hub"
        )

    def test_a_dangling_reference_in_live_css_is_seen(self, tmp_path):
        """The ordinary case, so comment handling is not the only thing tested."""
        # Arrange
        text = '@import "../nope/gone.css";\n:root{--a:1px}\n'
        # Act
        found = _unresolved_in(text, tmp_path)
        # Assert
        assert found == [(1, "../nope/gone.css")], (
            f"a plain dangling import was not reported: {found}"
        )

    def test_a_reference_that_resolves_is_not_reported(self, tmp_path):
        """Proves the scan is not simply flagging everything it sees."""
        # Arrange
        (tmp_path / "real.css").write_text(":root{--a:1px}\n")
        text = '@import "real.css";\n'
        # Act
        found = _unresolved_in(text, tmp_path)
        # Assert
        assert found == [], f"a resolvable reference was wrongly reported: {found}"

    def test_a_data_uri_is_not_reported(self, tmp_path):
        """Inline assets have no path to resolve and must not be flagged."""
        # Arrange
        text = ".x{background:url(data:image/svg+xml;base64,AAAA)}\n"
        # Act
        found = _unresolved_in(text, tmp_path)
        # Assert
        assert found == [], f"a data: URI was wrongly reported: {found}"

    def test_an_external_url_is_not_reported(self, tmp_path):
        """Remote assets are not resolved against the static tree either."""
        # Arrange
        text = "@import url(https://example.invalid/x.css);\n"
        # Act
        found = _unresolved_in(text, tmp_path)
        # Assert
        assert found == [], f"an external URL was wrongly reported: {found}"


class TestThePatternsSeparateSyntaxFromProse:
    """Direct controls on the two regexes, in both directions.

    THE LINE THESE DRAW IS PROSE vs SYNTAX, NOT COMMENT vs CODE. This detector
    is deliberately comment-blind — that is the whole point of the file — so
    "ignores a mere mention" cannot mean "ignores things in comments" here. It
    means the narrower and still-necessary thing: naming the construct in a
    sentence must not register as writing it. That distinction is what makes
    the prose fix above a real fix rather than a relabelling, so it is worth an
    explicit control: if `_URL` matched the word "url" in running text, the
    rewrite would not have helped anyone.
    """

    def test_url_pattern_matches_real_css_syntax(self):
        """Positive: the instrument is not blind."""
        # Arrange
        # Act
        hit = _URL.search('background: url("logo.svg")')
        # Assert
        assert hit is not None, "_URL cannot match an ordinary url() reference"

    def test_url_pattern_ignores_prose_naming_the_function(self):
        """Negative: a sentence about url() is not a url() reference."""
        # Arrange
        # Act
        hit = _URL.search("the url token is what Django rewrites")
        # Assert
        assert hit is None, f"_URL matched prose rather than syntax: {hit}"

    def test_import_pattern_matches_real_css_syntax(self):
        """Positive: the instrument is not blind."""
        # Arrange
        # Act
        hit = _IMPORT.search('@import "../utils/effects.css";')
        # Assert
        assert hit is not None, "_IMPORT cannot match an ordinary at-import"

    def test_import_pattern_ignores_prose_naming_the_at_rule(self):
        """Negative: this is the exact prose the fix above substitutes in."""
        # Arrange
        # Act
        hit = _IMPORT.search("an at-import of effects.css from their utilities")
        # Assert
        assert hit is None, f"_IMPORT matched prose rather than syntax: {hit}"
