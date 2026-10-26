"""Texture: a grid pattern, or the input text, wrapped over a cube and a sphere.

An Effect Guide example for the Texture Mapping chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Textured
from terminaltexteffects.engine.shapes import Cube, Sphere
from terminaltexteffects.utils import argutils

# Four columns and two rows repeat over each face: a cell with a + at one corner and lines along two edges.
GRID = "+---\n|   "


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "texture", Texture, TextureConfig


@dataclass
class TextureConfig(BaseConfig):
    """Configuration for the Texture effect."""

    parser_spec = argutils.ParserSpec(
        name="texture",
        help="A grid pattern, or the input text, wrapped over a cube and a sphere.",
        description="texture | A grid pattern, or the input text, wrapped over a cube and a sphere.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c texture --text",
    )
    text: bool = argutils.ArgSpec(
        name="--text",
        default=False,
        action="store_true",
        help="Wrap the input text instead of the grid.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Wrap the input text instead of the grid."


class TextureIterator(BaseEffectIterator[TextureConfig]):
    """Produce the frames of the Texture effect."""

    def __init__(self, effect: Texture) -> None:
        """Wrap the texture over both shapes and spin them."""
        super().__init__(effect)
        self.world = self.terminal.world
        look = Textured() if self.config.text else Textured(GRID)  # Textured() wraps the input text.
        cube = self.world.body(Cube(22), at=(-20, 0, 0)).draw(look)
        sphere = self.world.body(Sphere(13, segments=32, rings=16), at=(20, 0, 0)).draw(look)
        for body in (cube, sphere):
            body.rotate("x", 20)
            body.spin("y", turns=1, frames=360, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Spin the shapes, then swap them for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            for body in self.world.bodies:
                body.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Texture(BaseEffect[TextureConfig]):
    """A grid pattern, or the input text, wrapped over a cube and a sphere."""

    @property
    def _config_cls(self) -> type[TextureConfig]:
        return TextureConfig

    @property
    def _iterator_cls(self) -> type[TextureIterator]:
        return TextureIterator
