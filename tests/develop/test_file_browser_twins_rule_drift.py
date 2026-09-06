"""Rule-level drift between the file-browser twins.

PR #193's guard compares TOKENS at directory granularity and is blind to a RULE
the shell has and the app lacks. The measured instance it cannot see:

    .wft-item.inactive .wft-name       { transition: color .15s ease; }
    .wft-item.inactive:hover .wft-name { color: var(--color-fg-default, ...); }

invisible to a token diff because --color-fg-default is used elsewhere under
app/, so it never enters the app-only set.

METHOD. Strip each twin's DECLARED prefix, then diff normalised selectors.
Declared, not derived: a derived mapping is the heuristic that produced the
media-viewer false pair. A wrong prefix collapses LOUDLY (132 unpaired instead
of 38), which is the control below.

THE EXEMPTION IS A RULE, NOT A LIST, for the 30 that share a structural reason:
a selector is exempt when some class in it exists NOWHERE in the app twin's
vocabulary — a feature the app does not have (23 `.context-git-*` rules: 13
"git" hits in the shell twin, 0 in the app) or the shell's own root container.
That rule provably does NOT absorb real drift, since `.name` and `.inactive`
both exist in the app twin.

WHAT SURVIVES IS NAMED, IN TWO SECTIONS WITH DIFFERENT LIFECYCLES. Measured
2026-09-06 by reading all six survivors:

  _PERMANENT  the twins express the SAME BEHAVIOUR through a DIFFERENT DOM
              CONTRACT. No selector comparison can ever absorb these — the
              vocabulary is shared, so the rule above does not fire, and the
              selectors genuinely differ, so the diff is right to report them.
              Reviewed only if the behaviour changes.
  _TRACKED    real asymmetries, each with the card that owns it AND ITS FIX
              DIRECTION. Direction matters: two of three point at the SHELL as
              the defective side, so reading this output as a to-port list
              would ship the shell's dead CSS into the app.
"""

import re

from tests._checkout import css_dir

SHELL_PREFIX = "wft-"
APP_PREFIX = "stx-app-file-tree__"

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_AT_BLOCK = re.compile(r"@(?:keyframes|font-face|counter-style)\b[^{]*\{", re.I)
_CLASS = re.compile(r"\.([A-Za-z0-9_-]+)")

# Same behaviour, different DOM contract. NOT drift; NOT portable.
_PERMANENT = {
    "base.css": {
        ".folder.expanded > .folder-toggle .chevron":
            "app rotates via .chevron.expanded (base.css:101) — same "
            "transform, keyed on the chevron rather than the folder",
        ".file":
            "cursor:pointer; the app applies it to the item instead "
            "(base.css:41)",
    },
    "children.css": {
        ".children.expanded .children.expanded .children.expanded "
        ".children.expanded .children.expanded:has(> .item:hover)":
            "hand-written five-level specificity ladder, documented in the "
            "shell source; the app has no equivalent nesting depth",
    },
}

# Real asymmetries. Each names its owner and WHICH SIDE to change.
_TRACKED = {
    "states.css": {
        ".item.inactive .name":
            "PORT TO APP — scitex-ui-two-search-css-twins-disagree-and-one-"
            "renders-no-background-20260818",
        ".item.inactive:hover .name":
            "PORT TO APP — same card",
        ".error i":
            "PORT TO APP — the app renders <i class='fas fa-exclamation-"
            "triangle'> (_FileTreeRenderer.ts:24) but never styles it; the "
            "shell sets font-size:16px",
        '[data-theme="dark"] .target-badge':
            "DELETE FROM SHELL — repeats its own base rule "
            "(.target-badge{display:none}) verbatim; dead CSS",
        '[data-theme="dark"] .file.target':
            "DELETE FROM SHELL — pins rgba(47,129,247,.15) over "
            "--color-accent-subtle, which IS defined in both palettes, so the "
            "override defeats theming; the app follows the token correctly",
    },
}


def _shell_dir():
    return css_dir() / "shell/workspace-files-tree"


def _app_dir():
    return css_dir() / "app/file-browser"


def _strip_at_blocks(text):
    """Drop @keyframes/@font-face bodies; their heads are not selectors."""
    out, i = [], 0
    while True:
        match = _AT_BLOCK.search(text, i)
        if not match:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:match.start()])
        depth, j = 1, match.end()
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        i = j


def _selectors(path):
    text = _strip_at_blocks(_CSS_COMMENT.sub("", path.read_text()))
    found = set()
    for head in re.findall(r"([^{}]+)\{", text):
        for one in head.split(","):
            one = " ".join(one.split())
            if one and not one.startswith("@"):
                found.add(one)
    return found


def _normalise(selector, prefix):
    return re.sub(r"\.%s" % re.escape(prefix), ".", selector)


def _app_vocabulary():
    """Every class the app twin uses, prefix stripped (state classes included)."""
    names = set()
    for sheet in _app_dir().glob("*.css"):
        for selector in _selectors(sheet):
            names |= set(_CLASS.findall(_normalise(selector, APP_PREFIX)))
    return names


def _shell_only(name, vocabulary=None):
    shell = {_normalise(s, SHELL_PREFIX) for s in _selectors(_shell_dir() / name)}
    app = {_normalise(s, APP_PREFIX) for s in _selectors(_app_dir() / name)}
    only = shell - app
    if vocabulary is None:
        return only
    return {s for s in only if set(_CLASS.findall(s)) <= vocabulary}


def _pairs():
    return sorted(
        p.name for p in _shell_dir().glob("*.css") if (_app_dir() / p.name).exists()
    )


def _named(name):
    return set(_PERMANENT.get(name, {})) | set(_TRACKED.get(name, {}))


def test_the_comment_pattern_matches_a_real_comment():
    # Arrange
    comment = "/* Loading state */"

    # Act
    match = _CSS_COMMENT.search(comment)

    # Assert
    assert match, "_CSS_COMMENT cannot match a real comment, so stripping is a no-op"


def test_the_comment_pattern_does_not_eat_a_code_line():
    # Arrange
    code = "  transform: rotate(90deg);"

    # Act
    match = _CSS_COMMENT.search(code)

    # Assert
    assert match is None, (
        "_CSS_COMMENT matched code; an over-eager stripper empties the "
        "stylesheet and every comparison then passes against nothing"
    )


def test_the_at_block_pattern_matches_a_keyframes_head():
    # Arrange
    head = "@keyframes wft-spin {"

    # Act
    match = _AT_BLOCK.search(head)

    # Assert
    assert match, (
        "_AT_BLOCK cannot match @keyframes, so its percentage stops leak in as "
        "selectors — they did, until measured on 2026-09-06 (41 -> 38)"
    )


def test_the_at_block_pattern_does_not_match_an_ordinary_rule():
    # Arrange
    rule = ".wft-item.inactive .wft-name {"

    # Act
    match = _AT_BLOCK.search(rule)

    # Assert
    assert match is None, "_AT_BLOCK matched a normal rule; real selectors would vanish"


def test_the_class_pattern_matches_a_class_token():
    # Arrange
    selector = ".item.inactive .name"

    # Act
    found = _CLASS.findall(selector)

    # Assert
    assert found == ["item", "inactive", "name"], (
        f"_CLASS read {found}; the exemption rule depends on seeing every class "
        "including unprefixed state classes"
    )


def test_the_class_pattern_does_not_match_a_bare_word():
    # Arrange — an element selector carries no class at all.
    selector = "div > span"

    # Act
    match = _CLASS.search(selector)

    # Assert
    assert match is None, (
        f"_CLASS invented a class ({match.group(0) if match else ''!r}) out of "
        "an element selector; the exemption rule would then compare noise"
    )


def test_the_twins_share_selectors_so_something_is_being_compared():
    # Arrange
    pairs = _pairs()

    # Act
    shared = sum(
        len({_normalise(s, SHELL_PREFIX) for s in _selectors(_shell_dir() / n)}
            & {_normalise(s, APP_PREFIX) for s in _selectors(_app_dir() / n)})
        for n in pairs
    )

    # Assert
    assert shared > 0, (
        f"anti-vacuity: {len(pairs)} file pairs share no normalised selectors, "
        "so every shell-only result is meaningless"
    )


def test_a_wrong_prefix_collapses_loudly_rather_than_pairing_nothing():
    # Arrange
    bogus = "zzz-no-such-prefix-"

    # Act
    unpaired = len(
        {_normalise(s, bogus) for s in _selectors(_shell_dir() / "states.css")}
        - {_normalise(s, bogus) for s in _selectors(_app_dir() / "states.css")}
    )

    # Assert
    assert unpaired > len(_shell_only("states.css")), (
        "a wrong prefix must produce MORE unpaired selectors, not silently "
        "zero; a mapping that fails quietly is how the media-viewer false pair "
        "happened"
    )


def test_the_exemption_rule_does_not_absorb_the_tracked_drift():
    # Arrange
    vocabulary = _app_vocabulary()

    # Act
    surviving = _shell_only("states.css", vocabulary)

    # Assert
    assert set(_TRACKED["states.css"]) <= surviving, (
        "positive control: the vocabulary rule swallowed drift it must report. "
        f"Expected {sorted(_TRACKED['states.css'])} to survive, got "
        f"{sorted(surviving)}"
    )


def test_every_named_exemption_is_still_a_real_shell_only_selector():
    # Arrange
    vocabulary = _app_vocabulary()

    # Act
    stale = {
        name: sorted(_named(name) - _shell_only(name, vocabulary))
        for name in _pairs()
        if _named(name) - _shell_only(name, vocabulary)
    }

    # Assert
    assert stale == {}, (
        f"these exemptions no longer describe anything: {stale}. Either the "
        "asymmetry was fixed (delete the entry) or a prefix changed. An "
        "exemption list that outlives its subject silences future drift."
    )


def test_no_unnamed_rule_level_drift_between_the_twins():
    # Arrange
    vocabulary = _app_vocabulary()

    # Act
    unnamed = {
        name: sorted(_shell_only(name, vocabulary) - _named(name))
        for name in _pairs()
        if _shell_only(name, vocabulary) - _named(name)
    }

    # Assert
    assert unnamed == {}, (
        f"the shell twin has rules its app twin lacks, using classes the app "
        f"DOES have: {unnamed}. Decide the FIX DIRECTION before acting — two of "
        "the three tracked entries are shell defects, so this is a list of "
        "asymmetries, not a list of things to port. Then add it to _TRACKED "
        "with its owning card, or to _PERMANENT if the twins express the same "
        "behaviour through different contracts."
    )
