"""Wireframes: the regular solids tumble as edge drawings.

An Effect Guide recipe.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.looks import Wireframe
from terminaltexteffects.shapes import Cube, Icosahedron, Octahedron, Tetrahedron
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "wireframes", Wireframes, WireframesConfig


@dataclass
class WireframesConfig(BaseConfig):
    """Configuration for the Wireframes effect."""

    parser_spec = argutils.ParserSpec(
        name="wireframes",
        help="The regular solids tumble as edge drawings.",
        description="wireframes | The regular solids tumble as edge drawings.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c wireframes",
    )


class WireframesIterator(BaseEffectIterator[WireframesConfig]):
    """Produce the frames of the Wireframes effect."""

    def __init__(self, effect: Wireframes) -> None:
        """Line up four solids and tumble each one differently."""
        super().__init__(effect)
        self.world = self.terminal.world
        solids = (Tetrahedron(11), Cube(14), Octahedron(10), Icosahedron(10))
        colors = ("#ff5fd7", "#00D1FF", "#5fff87", "#ffd75f")
        for index, (shape, color) in enumerate(zip(solids, colors)):
            look = Wireframe(color=Color(color), hidden_color=Color("#55556a"))
            body = self.world.body(shape, at=(-30 + 20 * index, 0, 0)).draw(look)
            body.spin("y", turns=1 + index % 2, frames=420, ease=easing.in_out_sine)
            body.spin("x", turns=1 - index % 2 * 0.5, frames=420, ease=easing.in_out_sine, together=True)
        self.text_shown = False

    def __next__(self) -> str:
        """Tumble the solids, then swap them for the text."""
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


class Wireframes(BaseEffect[WireframesConfig]):
    """The regular solids tumble as edge drawings."""

    @property
    def _config_cls(self) -> type[WireframesConfig]:
        return WireframesConfig

    @property
    def _iterator_cls(self) -> type[WireframesIterator]:
        return WireframesIterator
