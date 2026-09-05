#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_html_lang_follows_the_active_language.py

"""`<html lang>` must follow the active language, not a literal.

THE DEFECT, found by scitex-scholar 2026-08-23 in the SHIPPED 0.17.0 wheel:

    standalone_shell.html:3
    <html lang="en" data-theme-default="{{ shell_theme_default|default:'dark' }}">
              ^^^^ literal              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ dynamic

WHY IT MATTERS MORE THAN A METADATA SLIP: `lang` is where a screen reader takes
its PRONUNCIATION rules from. Japanese served as `lang="en"` is not mislabelled,
it is read aloud with English phonetics — closer to unusable than to imperfect.

WHY IT SURVIVED IN TWO SHELLS INDEPENDENTLY, which is the part worth keeping:

  a rendered-text sweep   reads page TEXT, and the text was correct Japanese.
                          AN ATTRIBUTE IS NOT TEXT, so the check could not see
                          it. Any i18n checker built by reading what a page SAYS
                          is blind to what the page DECLARES about what it says
                          — and those two are exactly what must agree.

  a human code review     the line CONTAINS `{{ }}`, so a skim registers "this
                          line is handled" and moves on. THE PRESENCE OF ONE
                          DYNAMIC THING CAMOUFLAGES THE STATIC THING BESIDE IT.
                          (scitex-hub's phrasing; it explains survival, not just
                          origin, and generalises well beyond this attribute.)

BLAST RADIUS: hub's own #691 fixes hub's global_base.html only. Every leaf
running STANDALONE — scholar, writer, figrecipe, storage — inherits this
template, so this file is the remaining half rather than a duplicate.
"""

from __future__ import annotations

import re

import pytest

_LANG_ATTR = re.compile(r"<html[^>]*\blang=\"([^\"]*)\"", re.I)


def _configure_django():
    """Configure Django in-test, matching test_shell_offers_a_way_out.py.

    Settings are configured HERE rather than at import so this module can be
    collected in an environment without Django, and because `USE_I18N` must be
    on for `translation.override` to do anything at all — with it off, every
    language silently resolves to the same value and the differ-test below would
    pass while measuring nothing.
    """
    django = pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            USE_I18N=True,
            LANGUAGE_CODE="en",
            INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
            STATIC_URL="/static/",
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "OPTIONS": {"context_processors": []},
                }
            ],
        )
        django.setup()
    return settings


def _rendered_lang(language: str | None) -> str:
    """Render the real shell with ``language`` active and return its lang attr."""
    _configure_django()
    from django.template.loader import render_to_string
    from django.utils import translation

    from scitex_ui.branding import shell_context

    with translation.override(language):
        html = render_to_string(
            "scitex_ui/standalone_shell.html",
            {**shell_context("lang-probe"), "mount_prefix": ""},
        )
    match = _LANG_ATTR.search(html)
    assert match, "no <html lang=...> in the rendered shell at all"
    return match.group(1)


def test_the_shell_renders_an_html_lang_attribute() -> None:
    """ANTI-VACUITY: every assertion below reads a group from this match."""
    # Arrange
    language = "en"
    # Act
    value = _rendered_lang(language)
    # Assert
    assert value, "<html lang> rendered empty — worse than wrong, since a screen reader then has no rule to apply"


@pytest.mark.parametrize("language", ["ja", "en", "fr"])
def test_html_lang_matches_the_active_language(language: str) -> None:
    """The attribute reports the language Django actually has active."""
    # Arrange
    expected = language
    # Act
    value = _rendered_lang(language)
    # Assert
    assert value == expected, f"active language {language!r} rendered as lang={value!r}"


def test_two_languages_do_not_render_the_same_lang() -> None:
    """THE LOAD-BEARING ONE, and it is not redundant with the parametrised test.

    With `lang="en"` hardcoded, the parametrised **en** case PASSES BY
    COINCIDENCE and only the others fail. One red among greens reads like a
    flake to anyone skimming a CI log, and flakes get re-run rather than fixed.

    Asserting that two languages render DIFFERENTLY states the actual property —
    the attribute VARIES — and cannot pass while a literal is there, whatever
    that literal happens to be. It would also catch a future regression to
    `lang="ja"`, which the en-case assertion alone would not.

    Shape suggested by scitex-scholar, who carried it over from hub's fix for
    the same bug in their own shell.
    """
    # Arrange
    japanese = _rendered_lang("ja")
    # Act
    english = _rendered_lang("en")
    # Assert
    assert japanese != english, (
        f"both languages rendered lang={japanese!r}; the attribute is not "
        "following the active language"
    )


def test_an_explicit_lang_overrides_the_active_one() -> None:
    """A caller may state it, for a page whose content is not the UI language."""
    # Arrange
    _configure_django()
    from django.utils import translation

    from scitex_ui.branding import shell_context

    with translation.override("en"):
        context = shell_context("lang-probe", lang="ja")
    # Act
    value = str(context["shell_lang"])
    # Assert
    assert value == "ja", f"explicit lang ignored; got {value!r}"


def test_the_fallback_is_en_when_translations_are_deactivated() -> None:
    """`get_language()` returns None with translations off — never render empty.

    An empty `lang=""` is worse than a wrong one: the screen reader has no rule
    to apply at all, rather than the wrong rule.
    """
    # Arrange
    _configure_django()
    from django.utils import translation

    from scitex_ui.branding import shell_context

    translation.deactivate_all()
    # Act
    try:
        value = str(shell_context("lang-probe")["shell_lang"])
    finally:
        translation.activate("en")
    # Assert
    assert value == "en", f"expected the 'en' fallback, got {value!r}"


def test_a_leaf_that_bypasses_shell_context_still_gets_a_language() -> None:
    """The template's OWN default, exercised without ``shell_context`` at all.

    RAISED BY scitex-scholar before this landed, and it is the "who are the
    CONSUMERS" question rather than the "can the check fail" question — the two
    are independent, and every other test in this file answers only the second.

    MEASURED BY THEM across the four leaves that render this shell:

        scitex-writer    calls shell_context      (6 sites)
        scitex-storage   calls shell_context      (4 sites)
        scitex-scholar   DOES NOT                 (0, control: render_to_string 2)
        figrecipe        DOES NOT                 (0)

    Two of four build their own context dict and call ``render_to_string``
    directly. So a fix delivered ONLY through ``shell_context`` reaches half the
    consumers, and every test above renders through that function — the path
    under test is the path they do not take.

    THE FAILURE IT GUARDS AGAINST IS WORSE THAN THE ORIGINAL BUG. Django renders
    an undefined variable as the EMPTY STRING, so a bare ``{{ shell_lang }}``
    would give those two leaves ``lang=""`` — no rule for a screen reader to
    apply at all, rather than the wrong rule. Repairing two leaves while
    degrading two others.

    The template therefore carries the default itself, and this test is what
    stops someone "tidying" it away on the reasonable-sounding grounds that
    ``shell_context`` already defaults it.
    """
    # Arrange
    _configure_django()
    from django.template.loader import render_to_string

    context = {"app_label": "Bypass", "mount_prefix": ""}  # NO shell_lang
    # Act
    html = render_to_string("scitex_ui/standalone_shell.html", context)
    # Assert
    assert _LANG_ATTR.search(html).group(1) == "en", (
        "a renderer that does not use shell_context got "
        f"lang={_LANG_ATTR.search(html).group(1)!r}; the template must default "
        "it, because two of the four leaves build their own context"
    )
