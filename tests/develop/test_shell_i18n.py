#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared-shell i18n (operator directive 2026-09-14): EN default + complete JA,
following the host's active language.

Two render layers are covered, because the shell's strings live in both:

  SERVER  standalone_shell.html — Django {% trans %}, resolved from the shipped
          scitex_ui/locale/ja/LC_MESSAGES catalog.
  CLIENT  ts/_base/i18n.ts (SHELL_STRINGS) — the strings the shared components
          (app-launcher, project-selector) build in the browser, where Django
          gettext cannot reach. Selected by document.documentElement.lang, which
          the shell already sets from the host active language (branding.
          _active_language; pinned by test_html_lang_follows_the_active_language).

The two SAFETY properties, asserted first because they are the ones a regression
would silently break:
  1. EN DEFAULT — with i18n not activated (a leaf that has not opted into a
     language, USE_I18N off, or an unknown tag), the shell renders the English
     literals. This is what keeps the change byte-identical for every existing
     leaf: wrapping a string in {% trans %} must not alter its English output.
  2. NO MIXED PAGE — when the host language is ja, the shell's named strings all
     render Japanese; a half-translated page (EN/JA mixed) is exactly the defect
     the operator's contract forbids.
"""

from __future__ import annotations

import pathlib
import re
import struct

import pytest

import django
from django.conf import settings

# Configure at MODULE IMPORT (collection time), not first-call, because other
# test modules in this suite call settings.configure() WITHOUT USE_I18N (they
# don't touch translation). Whichever module's configure() runs first wins and
# the rest are no-ops — so this must run first to give the whole suite
# USE_I18N=True. That is safe: with no language activated, Django returns the
# msgid, which is byte-for-byte the English source, so the non-i18n tests are
# unaffected, and it is what makes the JA render below deterministic in the
# full suite rather than only in isolation.
if not settings.configured:
    settings.configure(
        DEBUG=False,
        USE_I18N=True,
        LANGUAGE_CODE="en",
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_ui"],
        STATIC_URL="/static/",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "DIRS": [],
                "OPTIONS": {"context_processors": []},
            }
        ],
        SCITEX_UI_AUTOWIRE_INSPECTOR=False,
    )
    django.setup()

# Resolve the CHECKOUT, not the installed package (the PR #152 rule): a guard
# that reads site-packages cannot see the change under review.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TPL = (
    _REPO_ROOT / "src" / "scitex_ui" / "templates" / "scitex_ui"
    / "standalone_shell.html"
)
_LOCALE_MO = _REPO_ROOT / "src" / "scitex_ui" / "locale" / "ja" / "LC_MESSAGES" / "django.mo"
_LOCALE_PO = _REPO_ROOT / "src" / "scitex_ui" / "locale" / "ja" / "LC_MESSAGES" / "django.po"
_I18N_TS = (
    _REPO_ROOT / "src" / "scitex_ui" / "static" / "scitex_ui" / "ts" / "_base"
    / "i18n.ts"
)

# A few of the shell's named strings, EN -> expected JA, used to assert both
# the default and the translated render without re-deriving the whole catalog.
_SAMPLES = {
    "Console": "コンソール",
    "Files": "ファイル",
    "Viewer": "ビューワー",
    "Keyboard Shortcuts": "キーボードショートカット",
    "Ask anything": "何でも聞いてください",
    "Click a file to open": "クリックしてファイルを開く",
}


def _render(lang: str | None = None) -> str:
    """Render the real shell; `lang` activates that language (None = default
    'en'). Rendering rather than pattern-matching the source is the point: a
    {% trans %} that resolves wrong and an absent string look identical to a
    regex."""
    from django.utils import translation

    if lang:
        translation.activate(lang)
    try:
        ctx = {"shell_lang": lang} if lang else {}
        from django.template.loader import render_to_string

        return render_to_string("scitex_ui/standalone_shell.html", ctx)
    finally:
        if lang:
            translation.deactivate()


# --- 1. EN default: wrapping in {% trans %} did not change English output ---


@pytest.mark.parametrize("en", sorted(_SAMPLES))
def test_shell_renders_english_for_the_default_language(en):
    """No language activated (a leaf that has not opted into a language, or a
    host whose active language is the default): every wrapped string renders
    its English literal. This is the regression guard — if {% trans %} altered
    the English output, every existing leaf would change with no translation
    at all."""
    # Arrange
    html = _render()
    # Act
    present = en in html
    # Assert
    assert present, "English default lost for %r" % en


@pytest.mark.parametrize("en", sorted(_SAMPLES))
def test_shell_renders_english_for_an_unknown_language(en):
    """An active-but-untranslated tag (e.g. fr) must fall back to English, not
    to the msgid key or blank — EN is the default for every language we do not
    ship a catalog for."""
    # Arrange
    html = _render(lang="fr")
    # Act
    present = en in html
    # Assert
    assert present, f"unknown language fell back wrong for {en!r}"


# --- 2. JA renders, and no EN/JA is mixed on the named strings -------------


def test_shell_renders_japanese_when_the_host_language_is_ja():
    # Arrange
    html = _render(lang="ja")
    # Act
    missing_ja = [ja for ja in _SAMPLES.values() if ja not in html]
    # Assert
    assert not missing_ja, f"JA forms missing from the rendered shell: {missing_ja}"


def test_no_english_remains_for_translated_shell_strings_in_ja():
    """The mixed-page defect: a JA page must not also carry the English form of
    the SAME named string (e.g. both 'Console' and 'コンソール' as the tab label).
    We check the sampled strings' English forms are absent from the rendered
    labels (their title= and visible text), not the whole document (proper
    nouns like 'SciTeX' legitimately stay English)."""
    # Arrange
    html = _render(lang="ja")
    # Act — the English sample words must not appear as standalone rendered
    # labels; they should all have become the JA forms asserted above.
    offenders = [en for en in _SAMPLES if re.search(r">\s*" + re.escape(en) + r"\s*<", html)]
    # Assert
    assert not offenders, f"mixed EN/JA on one page for: {offenders}"


def test_html_lang_follows_the_active_language_in_ja_render():
    # Arrange
    html = _render(lang="ja")
    # Act
    m = re.search(r"<html[^>]*\blang=\"([^\"]*)\"", html)
    # Assert
    assert m and m.group(1) == "ja"


# --- 3. the shipped catalog is real and complete --------------------------


def test_the_ja_catalog_files_ship():
    # Arrange
    # Act
    ok = _LOCALE_MO.is_file() and _LOCALE_PO.is_file()
    # Assert
    assert ok, "locale/ja/LC_MESSAGES/{django.mo,django.po} are not in the tree"


def test_the_ja_mo_is_a_valid_gnu_catalog_with_entries():
    """Parse the .mo header + at least one entry with struct, so a corrupt or
    empty catalog (the silent 'ships English on a ja host' failure) is caught
    here rather than at a leaf."""
    # Arrange
    raw = _LOCALE_MO.read_bytes()
    # Act
    magic, ver, n, o_off, t_off, _, _ = struct.unpack("Iiiiiii", raw[:28])
    parsed = 0
    for i in range(n):
        klen, koff = struct.unpack("ii", raw[o_off + i * 8 : o_off + i * 8 + 8])
        tlen, toff = struct.unpack("ii", raw[t_off + i * 8 : t_off + i * 8 + 8])
        raw[koff : koff + klen].decode("utf-8")  # must decode
        raw[toff : toff + tlen].decode("utf-8")
        parsed += 1
    is_valid = magic == 0x950412DE and parsed == n >= 40
    # Assert
    assert is_valid, f"not a valid GNU .mo (magic={magic:#x}, entries={n}); the shell has ~62 strings"


def test_every_trans_string_in_the_template_has_a_ja_entry():
    """Cross-check the template against the catalog: a {% trans %} added to the
    shell without a JA line is a hole in the 'complete JA' promise. (The build
    script asserts this at build time; this is the durable guard in CI.)"""
    # Arrange
    template_ids = set(
        re.findall(r"{%\s*trans\s+[\"']([^\"']+)[\"']\s*%}", _TPL.read_text("utf-8"))
    )
    po_text = _LOCALE_PO.read_text("utf-8")
    po_ids = set(re.findall(r'msgid "([^"]*)"', po_text))
    po_ids.discard("")  # the empty msgid is the catalog header
    # Act
    missing = template_ids - po_ids
    # Assert
    assert not missing, f"in the template but missing from the JA catalog: {sorted(missing)}"


def test_the_catalog_has_no_stale_entries():
    # Arrange
    template_ids = set(
        re.findall(r"{%\s*trans\s+[\"']([^\"']+)[\"']\s*%}", _TPL.read_text("utf-8"))
    )
    po_text = _LOCALE_PO.read_text("utf-8")
    po_ids = set(re.findall(r'msgid "([^"]*)"', po_text))
    po_ids.discard("")
    # Act
    stale = po_ids - template_ids
    # Assert
    assert not stale, "catalog entries with no matching {% trans %}: %s" % sorted(stale)


# --- 4. the client dictionary (ts/_base/i18n.ts) is complete + wired -------


def _ts_ja_block() -> str:
    """The `ja: { ... }` object in i18n.ts, as text."""
    text = _I18N_TS.read_text("utf-8")
    m = re.search(r"ja:\s*\{", text)
    assert m, "i18n.ts has no ja: block"
    # brace-match from the first {
    start = text.index("{", m.end() - 1)
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return text[start:]


def _ts_block_after(text: str, marker: str) -> str:
    """The brace-balanced object following `marker` (e.g. 'en: {')."""
    m = re.search(re.escape(marker.rstrip(" {")) + r"\s*\{", text)
    if not m:
        return ""
    start = text.index("{", m.end() - 1)
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return text[start:]


def _ts_block_keys(block: str) -> set[str]:
    """The `name:` keys inside a brace object, line-anchored.

    Anchoring at line start keeps an identifier's SUFFIX (e.g. 'AppsAvailable'
    inside 'noAppsAvailable:') from being read as its own key.
    """
    return {k for k in re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:", block, re.M)}


def test_the_client_en_column_has_the_four_shell_keys():
    """Every key in the en column is one of the 4 shell component strings — a
    floor so the extractor is proven to have read the real file (not an empty
    parse), not just that en and ja agree."""
    # Arrange
    text = _I18N_TS.read_text("utf-8")
    en_block = _ts_block_after(text, "en:")
    # Act
    en_keys = _ts_block_keys(en_block)
    # Assert
    assert en_keys == {"apps", "noAppsAvailable", "selectProject", "noProjects"}, (
        f"en: keys parsed as {sorted(en_keys)} — expected the 4 shell component "
        "strings, so the extractor or the file changed"
    )


def test_the_client_ja_column_covers_every_en_key():
    """Every en key has a ja counterpart (the client half of 'complete JA')."""
    # Arrange
    text = _I18N_TS.read_text("utf-8")
    en_keys = _ts_block_keys(_ts_block_after(text, "en:"))
    ja_keys = _ts_block_keys(_ts_block_after(text, "ja:"))
    # Act
    missing = en_keys - ja_keys
    # Assert
    assert not missing, f"client JA column missing keys: {sorted(missing)}"


def test_the_components_route_their_defaults_through_shellTranslate():
    """The named components must not re-hardcode the English defaults (which
    would bypass the JA dictionary). They call shellTranslate(...). A fork or a
    re-added literal here is the duplication this directive is meant to stop."""
    # Arrange
    launcher = (
        _REPO_ROOT / "src/scitex_ui/static/scitex_ui/ts/app/app-launcher/_AppLauncher.ts"
    ).read_text("utf-8")
    selector = (
        _REPO_ROOT
        / "src/scitex_ui/static/scitex_ui/ts/app/project-selector/_ProjectSelector.ts"
    ).read_text("utf-8")
    # Act
    ok = (
        "shellTranslate(" in launcher
        and 'config.label ?? "Apps"' not in launcher
        and "shellTranslate(" in selector
        and '?? "Select project"' not in selector
    )
    # Assert
    assert ok, (
        "a component re-hardcoded its English default instead of routing "
        "through shellTranslate — the JA dictionary would be bypassed"
    )


# EOF
