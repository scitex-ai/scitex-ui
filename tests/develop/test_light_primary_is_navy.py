"""Light-theme primary is the SciTeX navy (operator decision 2026-09-15)."""

from tests._checkout import css_dir

from . import _css_palette


def test_light_primary_token_is_scitex_navy():
    # Arrange
    colors = css_dir() / "primitives" / "colors.css"
    # Act
    light, _ = _css_palette.palette_blocks(colors)
    # Assert
    assert _css_palette.declared(light, "--color-primary") == "#1a2a40"
