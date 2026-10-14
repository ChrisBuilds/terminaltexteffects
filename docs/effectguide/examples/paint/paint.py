"""Paint: the text fades in from dark gray to a color gradient across it.

An Effect Guide example for the Color chapter.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

DIRECTIONS = {
    "vertical": Gradient.Direction.VERTICAL,
    "horizontal": Gradient.Direction.HORIZONTAL,
    "radial": Gradient.Direction.RADIAL,
    "diagonal": Gradient.Direction.DIAGONAL,
}


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "paint", Paint, PaintConfig


@dataclass
class PaintConfig(BaseConfig):
    """Configuration for the Paint effect."""

    parser_spec = argutils.ParserSpec(
        name="paint",
        help="The text fades in from dark gray to a color gradient across it.",
        description="paint | The text fades in from dark gray to a color gradient across it.",
        epilog="Example: tte paint --direction radial",
    )
    direction: typing.Literal["vertical", "horizontal", "radial", "diagonal"] = argutils.ArgSpec(
        name="--direction",
        default="vertical",
        choices=list(DIRECTIONS),
        help="Direction of the gradient across the text.",
    )  # pyright: ignore[reportAssignmentType]
    "typing.Literal['vertical', 'horizontal', 'radial', 'diagonal'] : Direction of the gradient across the text."


class PaintIterator(BaseEffectIterator[PaintConfig]):
    """Produce the frames of the Paint effect."""

    def __init__(self, effect: Paint) -> None:
        """Give every character a scene that fades it to its color, and start it."""
        super().__init__(effect)
        canvas = self.terminal.canvas
        gradient = Gradient(Color("#ff0080"), Color("#ffd000"), Color("#00d0ff"), steps=12)
        color_mapping = gradient.build_coordinate_color_mapping(
            canvas.text_bottom,
            canvas.text_top,
            canvas.text_left,
            canvas.text_right,
            DIRECTIONS[self.config.direction],
        )
        dynamic = self.terminal.config.existing_color_handling == "dynamic"
        for character in self.terminal.get_characters():
            color = color_mapping[character.input_coord]
            if dynamic and character.animation.input_fg_color:
                color = character.animation.input_fg_color

            scene = character.animation.new_scene()
            fade = Gradient(Color("#303030"), color, steps=20)
            scene.apply_gradient_to_symbols(character.input_symbol, 3, fg_gradient=fade)
            character.animation.activate_scene(scene)

            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Advance every character one tick and return the frame."""
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class Paint(BaseEffect[PaintConfig]):
    """The text fades in from dark gray to a color gradient across it."""

    @property
    def _config_cls(self) -> type[PaintConfig]:
        return PaintConfig

    @property
    def _iterator_cls(self) -> type[PaintIterator]:
        return PaintIterator
