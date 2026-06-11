#!/usr/bin/env python3
"""Combobox component metadata.

A fuzzy-typeahead select primitive: a trigger button opens a popover
containing a search input and a filtered list of options. Used wherever
a plain ``<select>`` would be too narrow (long option lists, the need
to search by substring, the need to create a new value on the fly).

Consumers today
---------------
- ``scitex-todo``'s board filterbar (project / host / status / blocker /
  agent / date) and the card right-click move-to-project picker.

Design follows the same shape as :mod:`._dropdown` — Python registry
stub here, TS class + CSS in ``static/scitex_ui/``.
"""

from .._registry import register_component


class Combobox:
    name = "combobox"
    version = "0.1.0"
    description = (
        "Fuzzy-typeahead select: trigger opens a search input + filtered "
        "option list; arrow keys navigate, Enter selects, Esc closes. "
        "Optional onCreate for 'add new value' flows."
    )
    ts_entry = "scitex_ui/ts/app/combobox/index"
    css_file = "scitex_ui/css/app/combobox.css"


register_component(Combobox.name, Combobox)
