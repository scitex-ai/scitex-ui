"""Brand palette: navy #1a2a40 + gold #b8956a, one chrome accent on every app."""

import colorsys
import re
from pathlib import Path

CSS = Path(__file__).resolve().parents[2] / "src/scitex_ui/static/scitex_ui/css"
LIGHT = CSS / "primitives/colors/_light.css"
DARK = CSS / "primitives/colors/_dark.css"
THEME = CSS / "shell/theme.css"


def _pairs(path: Path) -> list[tuple[str, str]]:
    text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
    return re.findall(r"^\s*(--[a-z0-9_-]+)\s*:\s*([^;]+);", text, flags=re.M)


def _decls(path: Path) -> dict[str, str]:
    return dict(_pairs(path))


def test_brand_anchors_are_the_operator_values():
    # Arrange
    light = _decls(LIGHT)
    # Act
    anchors = (light["--stx-navy-900"], light["--stx-gold-500"], light["--stx-gold-300"])
    # Assert
    assert anchors == ("#1a2a40", "#b8956a", "#d4a87a")


def test_theme_layer_mirrors_the_brand_tokens():
    # Arrange
    light, theme = _decls(LIGHT), _decls(THEME)
    stx = {k: v for k, v in light.items() if k.startswith(("--stx-navy-", "--stx-gold-", "--stx-hue-"))}
    # Act
    drift = {k: (v, theme.get(k)) for k, v in stx.items() if theme.get(k) != v}
    # Assert
    assert len(stx) > 25 and not drift, drift


def test_icon_hues_carry_no_purple():
    # Arrange
    hues = {k: v for k, v in _decls(LIGHT).items() if k.startswith("--stx-hue-")}
    # Act
    purple = []
    for name, hx in hues.items():
        r, g, b = (int(hx[i : i + 2], 16) / 255 for i in (1, 3, 5))
        if 245 <= colorsys.rgb_to_hls(r, g, b)[0] * 360 < 320:
            purple.append(name)
    # Assert
    assert len(hues) == 8 and not purple, purple


def test_every_app_accent_is_the_single_brand_accent():
    # Arrange
    for path in (LIGHT, DARK, THEME):
        # Act
        values = {
            v.strip()
            for k, v in _pairs(path)
            if k.startswith("--app-accent-") and k not in ("--app-accent-color", "--app-accent-tint")
        }
        # Assert
        assert values == {"var(--stx-accent)", "var(--stx-accent-tint)"}, (path.name, values)


def test_warning_is_no_longer_the_brand_gold():
    # Arrange
    light, dark = _decls(LIGHT), _decls(DARK)
    # Act
    pair = (light["--_warning"], dark["--status-warning"])
    # Assert
    assert pair == ("#c4561a", "#f59a52")
