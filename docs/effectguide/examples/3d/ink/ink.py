"""Ink: the input text drawn over solid, lit shapes, in one color on a cube and a gradient across the text on a sphere.

An Effect Guide example for the Texture Mapping chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, Gradient, Ink, Textured, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.shapes import Cube, Sphere
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "ink", InkDemo, InkConfig


@dataclass
class InkConfig(BaseConfig):
    """Configuration for the Ink effect."""

    parser_spec = argutils.ParserSpec(
        name="ink",
        help="The input text drawn over solid, lit shapes.",
        description="ink | The input text drawn over solid, lit shapes.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c ink --light 1",
    )
    light: float = argutils.ArgSpec(
        name="--light",
        type=argutils.NonNegativeRatio.type_parser,
        default=0.0,
        metavar=argutils.NonNegativeRatio.METAVAR,
        help="How much shadow darkens the text: 0 glows, 1 darkens it as much as the shape.",
    )  # pyright: ignore[reportAssignmentType]
    "float : How much shadow darkens the text: 0 glows, 1 darkens it as much as the shape."


class InkIterator(BaseEffectIterator[InkConfig]):
    """Produce the frames of the Ink effect."""

    def __init__(self, effect: InkDemo) -> None:
        """Draw the text over a filled cube and sphere, and spin them."""
        super().__init__(effect)
        self.world = self.terminal.world
        light = self.config.light
        # The fill is each cell's background, lit from dark to bright like a Solid look.
        purple = Gradient(Color("#1a0020"), Color("#8A008A"), steps=12)
        navy = Gradient(Color("#001018"), Color("#006080"), steps=12)
        # One color on the cube. On the sphere, a gradient spread across the text keeps its colors on their letters.
        white = Ink(Color("#ffffff"), light=light)
        spread = Ink(
            Gradient(Color("#00D1FF"), Color("#ffffff"), Color("#ffd000"), steps=12),
            spread=Gradient.Direction.HORIZONTAL,
            light=light,
        )
        cube = self.world.body(Cube(22), at=(-20, 0, 0)).draw(Textured(ink=white, background=purple))
        sphere = self.world.body(Sphere(13, segments=32, rings=16), at=(20, 0, 0))
        sphere.draw(Textured(ink=spread, background=navy, repeat=False))
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


class InkDemo(BaseEffect[InkConfig]):
    """The input text drawn over solid, lit shapes."""

    @property
    def _config_cls(self) -> type[InkConfig]:
        return InkConfig

    @property
    def _iterator_cls(self) -> type[InkIterator]:
        return InkIterator
