"""Shared assertions for effect completion contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.graphics import ColorPair, Gradient

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_effect import BaseEffectIterator
    from terminaltexteffects.utils.graphics import Color


def assert_final_gradient(
    iterator: BaseEffectIterator,
    stops: tuple[Color, ...],
    steps: tuple[int, ...],
    direction: Gradient.Direction,
) -> None:
    """Check completed symbols, home coordinates, and independently configured gradient colors."""
    canvas = iterator.terminal.canvas
    expected = Gradient(*stops, steps=steps).build_coordinate_color_mapping(
        canvas.text_bottom,
        canvas.text_top,
        canvas.text_left,
        canvas.text_right,
        direction,
    )
    assert not iterator.active_characters
    characters = iterator.terminal.get_characters()
    assert characters
    for character in characters:
        visual = character.animation.current_character_visual
        color = expected[character.input_coord]
        assert character.is_visible
        assert character.motion.current_coord == character.input_coord
        assert visual.symbol == character.input_symbol
        assert visual.colors == ColorPair(fg=color)
        assert visual._fg_color_code == color.rgb_color
        assert visual._bg_color_code is None
