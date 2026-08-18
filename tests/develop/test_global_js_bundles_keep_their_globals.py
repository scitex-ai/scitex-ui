#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Hand-written pure-JS bundles must keep exposing their window globals.

Some bundles under `js/app/` are NOT esbuild output — they are hand-written
IIFEs that attach to `window.STX` so a plain `<script>` tag in a Django
template can use them with no bundler. Consumers detect them by presence:

    if (window.STX && window.STX.Combobox) { …enhance… } else { …fall back… }

Rebuilding one of those from its TypeScript source with
`esbuild --format=esm` produces a file that is valid, passes every existing
test, and sets NO GLOBAL — so every consumer silently takes the fallback
branch forever. Nothing fails; the feature just stops existing.

I did exactly this to combobox.js while adding the Dropdown filter, and caught
it only because scitex-cards happened to mention they detect
`window.STX.Combobox`. That is too thin a thread to rely on twice.
"""

import pathlib
import re

import scitex_ui
from tests._checkout import static_dir

_JS = static_dir() / "js" / "app"

# bundle filename -> the global it must attach. Add an entry whenever a new
# hand-written IIFE bundle gains consumers that feature-detect it.
_GLOBAL_BUNDLES = {
    "combobox.js": "Combobox",
}


def test_hand_written_bundles_still_attach_their_globals():
    # Arrange
    missing = []

    # Act
    for filename, symbol in _GLOBAL_BUNDLES.items():
        path = _JS / filename
        if not path.exists():
            missing.append(f"{filename} (file absent)")
            continue
        source = path.read_text()
        if not re.search(r"window\.STX", source):
            missing.append(f"{filename} (no window.STX)")
        elif not re.search(rf"\b{re.escape(symbol)}\b", source):
            missing.append(f"{filename} (no {symbol})")

    # Assert
    assert not missing, (
        f"{', '.join(missing)} — a consumer feature-detecting "
        "`window.STX.<X>` will silently take its fallback branch forever. "
        "This is what happens when a hand-written IIFE bundle is regenerated "
        "with `esbuild --format=esm`: the output is valid and exports nothing "
        "to the page."
    )
